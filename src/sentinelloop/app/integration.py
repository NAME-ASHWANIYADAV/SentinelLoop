"""Integration with a CMMS (and signed outbound webhooks): read-only shadow mode by default.

Model. A target is an external system: an Odoo instance (JSON-2 API) or a webhook endpoint.
- **shadow** (the default): the dispatcher computes exactly what it would send and records it. It makes **no**
  external call.
- **draft_requests**: approved work (APPROVED, SCHEDULED, IN_PROGRESS) is upserted into the CMMS as maintenance
  requests marked `[SentinelLoop]`. A request is updated when the local work order changes.

What the integration never does: send unapproved work, change CMMS stages, close or delete CMMS records, or write
any field outside `ODOO_WRITABLE_FIELDS`.

Delivery is state-based. A work order is sent when its version differs from the version last delivered, so no
event is lost when a write fails. Idempotency comes from the stored external id. If that mapping is lost, a marker
`SentinelLoop-Ref:<wo_id>` in the request description finds the existing request instead of creating a duplicate.

Failures:
- Transient (timeouts, connection errors, 408, 429, 5xx): retried with exponential backoff, up to `max_attempts`.
- Permanent (other 4xx), or attempts exhausted: the item becomes a dead letter. It waits for an admin to requeue it,
  with a reason.

Error text stored or logged keeps the HTTP status and the server's `message`. It never keeps the server's `debug`
traceback or any credential.

Security:
- Target hosts must be in `SENTINELLOOP_INTEGRATION_HOSTS` (comma-separated).
- https is required except for local hosts (localhost, 127.0.0.1, ::1, *.localhost, *.test).
- Credentials are read from an environment variable named in the target's config. They are never stored. The
  name must start with `SENTINELLOOP_CRED_`, so a target cannot be pointed at another secret (for example the
  audit key) and send it to an allowlisted host.
- Only admins register targets, change modes or requeue dead letters. Each such change needs a reason and is
  audited.

Odoo JSON-2 contract (Odoo 19 documentation, external_api.rst):
- `POST {base}/json/2/<model>/<method>`
- headers `Authorization: bearer <key>`, `Content-Type: application/json`, optional `X-Odoo-Database`
- body `{"ids": [...], "context": {...}, <method parameters by name>}`
- 200 with the JSON return value; 4xx/5xx with `{name, message, arguments, context, debug}`.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx

from . import auditlog, registry, workorders
from .errors import PermissionDenied
from .timeutil import iso, now_iso, now_ms as _now_ms

ADMINS = {"admin"}
DISPATCHERS = {"admin", "integration"}
SENT_STATES = ("APPROVED", "SCHEDULED", "IN_PROGRESS")
# once a request exists in the CMMS, later local states are mirrored onto it (name and description, priority lowered)
FOLLOW_STATES = ("CANCELLED", "REJECTED", "DEFERRED", "COMPLETED", "CLOSED")
CONFIG_KEYS = {"database", "api_key_env", "secret_env", "timeout_s", "max_attempts"}
ODOO_WRITABLE_FIELDS = {"name", "description", "priority", "maintenance_type", "schedule_date", "schedule_end", "duration", "equipment_id",
                        "request_date"}
PRIORITY = {"P1": "3", "P2": "2", "P3": "1"}
LOCAL_SUFFIXES = (".localhost", ".test")
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
DEFAULT_MAX_ATTEMPTS, BACKOFF_BASE_S, BACKOFF_CAP_S = 8, 30, 3600
WEBHOOK_TOLERANCE_S = 300
CRED_PREFIX = "SENTINELLOOP_CRED_"
CRED_KEYS = {"odoo_json2": "api_key_env", "webhook": "secret_env"}


class IntegrationError(ValueError):
    pass


class IntegrationPermissionError(IntegrationError, PermissionDenied):
    pass


class TransientError(RuntimeError):
    pass


class PermanentError(RuntimeError):
    pass


# -- targets -----------------------------------------------------------------------------------------------------------
def _allowed_hosts() -> set[str]:
    return {h.strip().lower() for h in os.environ.get("SENTINELLOOP_INTEGRATION_HOSTS", "").split(",") if h.strip()}


def _is_local(host: str) -> bool:
    return host in LOCAL_HOSTS or host.endswith(LOCAL_SUFFIXES)


def check_url(base_url: str):
    u = urlparse(base_url)
    host = (u.hostname or "").lower()
    if u.scheme not in ("http", "https") or not host:
        raise IntegrationError(f"{base_url!r} is not an http(s) URL")
    if u.username or u.password or u.query or u.fragment:
        raise IntegrationError("target URLs may not carry credentials, a query string or a fragment")
    if u.scheme == "http" and not _is_local(host):
        raise IntegrationError(f"{host} is not local: https is required")
    if host not in _allowed_hosts():
        raise IntegrationError(f"host {host} is not in SENTINELLOOP_INTEGRATION_HOSTS")


def _audit(db, c, actor, action, target_id, payload):
    auditlog.append(c, actor=actor, action=action, entity="integration_target", entity_id=target_id, payload=payload, key=db.audit_key,
                    key_id=db.audit_key_id)


def register_target(db, target_id: str, kind: str, base_url: str, config: dict, actor: str, role: str, mode: str = "shadow",
                    reason: str | None = None) -> dict:
    if role not in ADMINS:
        raise IntegrationPermissionError(f"role {role!r} may not register integration targets")
    if kind not in ("odoo_json2", "webhook"):
        raise IntegrationError(f"unknown target kind {kind!r}")
    if mode not in ("shadow", "draft_requests"):
        raise IntegrationError(f"unknown mode {mode!r}")
    if mode != "shadow" and not (reason and reason.strip()):
        raise IntegrationError("a target may start outside shadow mode only with a written reason")
    check_url(base_url)
    if any(k.lower() in ("api_key", "password", "secret", "token") for k in config):
        raise IntegrationError("secrets may not be stored in target config; name an environment variable instead (api_key_env / secret_env)")
    unknown = sorted(set(config) - CONFIG_KEYS)
    if unknown:
        raise IntegrationError(f"unknown config keys {unknown}; allowed: {sorted(CONFIG_KEYS)}")
    _check_cred_name(config.get(CRED_KEYS[kind]), CRED_KEYS[kind])
    now = now_iso()
    with db.tx() as c:
        if c.execute("SELECT 1 FROM integration_targets WHERE target_id = ?", (target_id,)).fetchone():
            raise IntegrationError(f"target {target_id} exists")
        c.execute("INSERT INTO integration_targets (target_id, kind, base_url, mode, config_json, enabled, created_by, created_at, updated_at) "
                  "VALUES (?,?,?,?,?,1,?,?,?)", (target_id, kind, base_url.rstrip("/"), mode, json.dumps(config), actor, now, now))
        _audit(db, c, actor, "integration.target_registered", target_id, {"kind": kind, "base_url": base_url, "mode": mode, "reason": reason,
                                                                         "config_keys": sorted(config)})
    return get_target(db, target_id)


def _check_cred_name(name, key: str):
    if not name or not str(name).startswith(CRED_PREFIX) or not str(name)[len(CRED_PREFIX):].replace("_", "").isalnum():
        raise IntegrationError(f"config '{key}' must name an environment variable starting with {CRED_PREFIX} (letters, digits, '_')")


def get_target(db, target_id: str) -> dict | None:
    with db.connect() as c:
        r = c.execute("SELECT * FROM integration_targets WHERE target_id = ?", (target_id,)).fetchone()
    if r is None:
        return None
    d = dict(r)
    d["config"] = json.loads(d.pop("config_json"))
    d["enabled"] = bool(d["enabled"])
    return d


def list_targets(db) -> list[dict]:
    with db.connect() as c:
        ids = [r[0] for r in c.execute("SELECT target_id FROM integration_targets ORDER BY target_id")]
    return [get_target(db, i) for i in ids]


def set_mode(db, target_id: str, mode: str, actor: str, role: str, reason: str) -> dict:
    if role not in ADMINS:
        raise IntegrationPermissionError(f"role {role!r} may not change integration modes")
    if mode not in ("shadow", "draft_requests"):
        raise IntegrationError(f"unknown mode {mode!r}")
    if not reason or not reason.strip():
        raise IntegrationError("a written reason is required to change an integration mode")
    t = get_target(db, target_id)
    if t is None:
        raise IntegrationError(f"unknown target {target_id}")
    with db.tx() as c:
        c.execute("UPDATE integration_targets SET mode = ?, updated_at = ? WHERE target_id = ?", (mode, now_iso(), target_id))
        if mode == "draft_requests":     # shadow records were never delivered: send the current versions for real
            c.execute("UPDATE sync_items SET synced_version = NULL WHERE target_id = ? AND status = 'shadow'", (target_id,))
        _audit(db, c, actor, "integration.mode_changed", target_id, {"from": t["mode"], "to": mode, "reason": reason})
    return get_target(db, target_id)


# -- mapping ------------------------------------------------------------------------------------------------------------
def _odoo_dt(ms: int | None) -> str | None:
    if ms is None:
        return None
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")      # Odoo Datetime: UTC, naive text


def marker(wo_id: str) -> str:
    """Delimited so that the marker of WO-1 is not a substring of the marker of WO-10."""
    return f"[SentinelLoop-Ref:{wo_id}]"


def odoo_payload(wo: dict, asset, equipment_id: int | None) -> dict:
    ex = wo.get("explanation") or {}
    e = _html
    lines = [f"<p><b>SentinelLoop recommendation</b> ({e(marker(wo['wo_id']))})</p>",
             f"<p>Asset {e(asset.tag)}; job {e(wo['job_type'])}; priority {e(wo['priority_class'])}; state in SentinelLoop {e(wo['state'])}.</p>"]
    if ex.get("why"):
        lines.append(f"<p>Why: {_html(ex['why'])}</p>")
    if ex.get("due_by"):
        lines.append(f"<p>Due by (UTC): {_html(ex['due_by'])} ({_html(ex.get('due_by_rule', ''))})</p>")
    if ex.get("p_fail_decision_horizon") is not None:
        lines.append(f"<p>P(failure before {e(ex.get('decision_horizon_hours'))} h): {float(ex['p_fail_decision_horizon']):.2f}</p>")
    lines.append("<p>Advisory only: created by SentinelLoop for review; it does not authorise work by itself.</p>")
    p = {"name": f"[SentinelLoop] {wo['title']}"[:250], "description": "".join(lines), "priority": PRIORITY[wo["priority_class"]],
         "maintenance_type": "preventive", "duration": float(wo["duration_h"])}
    if wo.get("scheduled_start_ms"):
        p["schedule_date"] = _odoo_dt(wo["scheduled_start_ms"])
        p["schedule_end"] = _odoo_dt(wo["scheduled_end_ms"])
    if equipment_id is not None:
        p["equipment_id"] = equipment_id
    if wo["state"] in FOLLOW_STATES:
        label = {"CANCELLED": "WITHDRAWN", "REJECTED": "WITHDRAWN", "DEFERRED": f"DEFERRED until {wo.get('deferred_until') or '?'}",
                 "COMPLETED": "COMPLETED", "CLOSED": "COMPLETED"}[wo["state"]]
        p["name"] = f"[SentinelLoop {label}] {wo['title']}"[:250]
        p["description"] = (f"<p><b>SentinelLoop: this recommendation is now {e(wo['state'].lower())} ({e(label.lower())}).</b> "
                            f"Do not act on it unless your own process says so.</p>" + p["description"])
        p["priority"] = "0" if wo["state"] in ("CANCELLED", "REJECTED", "DEFERRED") else p["priority"]
    return filter_fields(p)


def filter_fields(p: dict) -> dict:
    """The connector writes only these request fields; anything else is a programming error, refused explicitly."""
    bad = sorted(set(p) - ODOO_WRITABLE_FIELDS)
    if bad:
        raise IntegrationError(f"refusing to write CMMS fields outside the allowlist: {bad}")
    return p


def _html(s) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#x27;")


# -- adapters -------------------------------------------------------------------------------------------------------
class OdooJson2:
    def __init__(self, base_url: str, api_key: str, database: str | None = None, transport=None, timeout_s: float = 15.0):
        h = {"Authorization": f"bearer {api_key}", "Content-Type": "application/json; charset=utf-8", "User-Agent": "SentinelLoop/1"}
        if database:
            h["X-Odoo-Database"] = database
        self.client = httpx.Client(base_url=f"{base_url}/json/2", headers=h, timeout=timeout_s, transport=transport)

    def call(self, model: str, method: str, body: dict):
        try:
            r = self.client.post(f"/{model}/{method}", content=json.dumps(body))
        except (httpx.TimeoutException, httpx.TransportError) as e:
            raise TransientError(f"{type(e).__name__} calling {model}.{method}") from None
        if r.status_code == 200:
            return r.json()
        try:
            msg = str(r.json().get("message", ""))[:300]
        except Exception:
            msg = ""
        text = f"HTTP {r.status_code} from {model}.{method}: {msg}"
        if r.status_code in (408, 429) or r.status_code >= 500:
            raise TransientError(text)
        raise PermanentError(text)

    def find_equipment(self, ref: str) -> int | None:
        rows = self.call("maintenance.equipment", "search_read", {"domain": [["serial_no", "=", ref]], "fields": ["id", "name"]})
        return rows[0]["id"] if rows else None

    def upsert(self, wo_id: str, payload: dict, external_id: str | None, recover: bool = False) -> str:
        """`recover`: the local mapping may have been lost after an earlier send; only then is the marker searched, so a
        first send can never adopt a record someone planted with a predictable marker."""
        if external_id is None and recover:
            m = _html(marker(wo_id))
            rows = self.call("maintenance.request", "search_read", {"domain": [["description", "ilike", m]], "fields": ["id", "name", "description"]})
            rows = [r for r in rows if m in str(r.get("description") or "") and str(r.get("name") or "").startswith("[SentinelLoop]")]
            if len(rows) > 1:
                raise PermanentError(f"more than one CMMS request carries the marker for {wo_id} (ids {sorted(r['id'] for r in rows)}); "
                                     f"a person must decide which one is SentinelLoop's")
            if rows:
                external_id = str(rows[0]["id"])
        if external_id is not None:
            self.call("maintenance.request", "write", {"ids": [int(external_id)], "vals": payload})
            return external_id
        ids = self.call("maintenance.request", "create", {"vals_list": [payload]})
        return str(ids[0])

    def close(self):
        self.client.close()


def sign_webhook(secret: bytes, ts_s: int, body: bytes) -> str:
    return "sha256=" + hmac.new(secret, f"{ts_s}.".encode() + body, hashlib.sha256).hexdigest()


def verify_webhook(secret: bytes, ts_s: int, body: bytes, signature: str, now_s: int, tolerance_s: int = WEBHOOK_TOLERANCE_S) -> bool:
    """Receiver side: constant-time signature check plus a replay window on the signed timestamp."""
    if abs(now_s - int(ts_s)) > tolerance_s:
        return False
    return hmac.compare_digest(sign_webhook(secret, ts_s, body), signature or "")


class Webhook:
    def __init__(self, url: str, secret: bytes, transport=None, timeout_s: float = 10.0):
        self.url, self.secret = url, secret
        self.client = httpx.Client(timeout=timeout_s, transport=transport)

    def upsert(self, wo_id: str, payload: dict, external_id: str | None, recover: bool = False) -> str:
        body = json.dumps({"event": "work_order.upsert", "wo_id": wo_id, "payload": payload}, sort_keys=True).encode()
        ts = int(_now_ms() / 1000)
        try:
            r = self.client.post(self.url, content=body, headers={"Content-Type": "application/json", "X-SentinelLoop-Timestamp": str(ts),
                                                                  "X-SentinelLoop-Signature": sign_webhook(self.secret, ts, body)})
        except (httpx.TimeoutException, httpx.TransportError) as e:
            raise TransientError(f"{type(e).__name__} posting webhook") from None
        if 200 <= r.status_code < 300:
            return external_id or wo_id
        if r.status_code in (408, 429) or r.status_code >= 500:
            raise TransientError(f"HTTP {r.status_code} from webhook")
        raise PermanentError(f"HTTP {r.status_code} from webhook")

    def find_equipment(self, ref):
        return None

    def close(self):
        self.client.close()


def _adapter(t: dict, transport=None):
    cfg = t["config"]
    try:
        _check_cred_name(cfg.get(CRED_KEYS[t["kind"]]), CRED_KEYS[t["kind"]])
        check_url(t["base_url"])                       # the allowlist is checked at every dispatch, not only at registration
    except IntegrationError as e:
        raise PermanentError(str(e)) from None
    if t["kind"] == "odoo_json2":
        env = cfg.get("api_key_env")
        key = os.environ.get(env or "")
        if not key:
            raise PermanentError(f"credential environment variable {env!r} is not set")
        return OdooJson2(t["base_url"], key, cfg.get("database"), transport=transport, timeout_s=float(cfg.get("timeout_s", 15)))
    env = cfg.get("secret_env")
    secret = os.environ.get(env or "")
    if not secret or len(secret) < 32:
        raise PermanentError(f"webhook secret environment variable {env!r} is not set or shorter than 32 characters")
    return Webhook(t["base_url"], secret.encode(), transport=transport)


# -- dispatch ----------------------------------------------------------------------------------------------------------
def _backoff_s(attempts: int, wo_id: str) -> int:
    base = min(BACKOFF_CAP_S, BACKOFF_BASE_S * 2 ** (attempts - 1))
    jitter = int(hashlib.sha256(f"{wo_id}:{attempts}".encode()).hexdigest()[:4], 16) / 0xFFFF      # deterministic 0..1
    return int(base * (1 + 0.2 * jitter))


def _log(c, target_id, wo_id, action, outcome, detail):
    c.execute("INSERT INTO integration_log (ts, target_id, wo_id, action, outcome, detail_json) VALUES (?,?,?,?,?,?)",
              (now_iso(), target_id, wo_id, action, outcome, json.dumps(detail, default=str)))


def items(db, target_id: str, status: str | None = None) -> list[dict]:
    q, a = "SELECT * FROM sync_items WHERE target_id = ?", [target_id]
    if status:
        q, a = q + " AND status = ?", a + [status]
    with db.connect() as c:
        out = []
        for r in c.execute(q + " ORDER BY wo_id", a):
            d = dict(r)
            d["payload"] = json.loads(d.pop("payload_json")) if d.get("payload_json") else None
            out.append(d)
    return out


def _forget_external_id(db, target_id: str, wo_id: str):
    """Test and repair helper: simulate a lost local mapping."""
    with db.tx() as c:
        c.execute("UPDATE sync_items SET external_id = NULL WHERE target_id = ? AND wo_id = ?", (target_id, wo_id))


def requeue(db, target_id: str, wo_id: str, actor: str, role: str, reason: str):
    if role not in ADMINS:
        raise IntegrationPermissionError(f"role {role!r} may not requeue dead letters")
    if not reason or not reason.strip():
        raise IntegrationError("a written reason is required to requeue")
    with db.tx() as c:
        n = c.execute("UPDATE sync_items SET status = 'retry', attempts = 0, next_attempt_ms = 0, synced_version = NULL, updated_at = ? "
                      "WHERE target_id = ? AND wo_id = ? AND status = 'dead'", (now_iso(), target_id, wo_id)).rowcount
        if n != 1:
            raise IntegrationError(f"{wo_id} is not a dead letter for {target_id}")
        _audit(db, c, actor, "integration.requeued", target_id, {"wo_id": wo_id, "reason": reason})


def dispatch(db, target_id: str, now_ms: int | None = None, transport=None, max_items: int = 200, actor: str = "integration",
             role: str = "integration") -> dict:
    if role not in DISPATCHERS:
        raise IntegrationPermissionError(f"role {role!r} may not dispatch")
    now = int(now_ms if now_ms is not None else _now_ms())
    t = get_target(db, target_id)
    if t is None:
        raise IntegrationError(f"unknown target {target_id}")
    res = {"target_id": target_id, "mode": t["mode"], "considered": 0, "shadow": 0, "sent": 0, "retry": 0, "dead": 0, "skipped": 0}
    if not t["enabled"]:
        return res
    state = {i["wo_id"]: i for i in items(db, target_id)}
    due = []
    candidates = workorders.list_orders(db, states_in=list(SENT_STATES))
    candidates += [w for w in workorders.list_orders(db, states_in=list(FOLLOW_STATES)) if state.get(w["wo_id"])]
    for wo in candidates:
        it = state.get(wo["wo_id"])
        if it and it["status"] == "dead":
            res["skipped"] += 1
            continue
        if it and it["synced_version"] == wo["version"]:
            continue
        if it and it["status"] == "retry" and (it["next_attempt_ms"] or 0) > now:
            continue
        due.append((wo, it))
    due = due[:max_items]
    res["considered"] = len(due)
    if not due:
        return res
    adapter, adapter_error = None, None
    if t["mode"] != "shadow":
        try:
            adapter = _adapter(t, transport)
        except PermanentError as e:
            adapter_error = str(e)
    max_attempts = int(t["config"].get("max_attempts", DEFAULT_MAX_ATTEMPTS))
    equipment_cache: dict = {}
    try:
        for wo, it in due:
            asset = registry.get_asset(db, wo["asset_id"])
            ref = (asset.config or {}).get("cmms_equipment_ref")
            eq, outcome, err, ext, payload = None, None, None, (it or {}).get("external_id"), None
            attempts = (it or {}).get("attempts", 0)
            try:
                if adapter_error:
                    raise PermanentError(adapter_error)
                if adapter is not None and ref:
                    if ref not in equipment_cache:
                        equipment_cache[ref] = adapter.find_equipment(ref)
                    eq = equipment_cache[ref]
                payload = odoo_payload(wo, asset, eq)
                if t["mode"] == "shadow":
                    outcome = "shadow"
                else:
                    ext = adapter.upsert(wo["wo_id"], payload, ext, recover=it is not None)
                    outcome = "synced"
            except TransientError as e:
                attempts += 1
                outcome, err = ("dead" if attempts >= max_attempts else "retry"), str(e)
            except PermanentError as e:
                attempts += 1
                outcome, err = "dead", str(e)
            nxt = now + _backoff_s(attempts, wo["wo_id"]) * 1000 if outcome == "retry" else None
            synced = wo["version"] if outcome in ("shadow", "synced") else (it or {}).get("synced_version")
            pj = json.dumps(payload, sort_keys=True) if payload is not None else None
            with db.tx() as c:
                c.execute("INSERT INTO sync_items (target_id, wo_id, synced_version, pending_version, external_id, status, attempts, next_attempt_ms, "
                          "last_error, payload_json, payload_sha256, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(target_id, wo_id) DO UPDATE SET "
                          "synced_version = excluded.synced_version, pending_version = excluded.pending_version, external_id = excluded.external_id, "
                          "status = excluded.status, attempts = excluded.attempts, next_attempt_ms = excluded.next_attempt_ms, last_error = excluded.last_error, "
                          "payload_json = excluded.payload_json, payload_sha256 = excluded.payload_sha256, updated_at = excluded.updated_at",
                          (target_id, wo["wo_id"], synced, wo["version"], ext, outcome, 0 if outcome in ("shadow", "synced") else attempts, nxt, err, pj,
                           hashlib.sha256(pj.encode()).hexdigest() if pj else None, now_iso()))
                _log(c, target_id, wo["wo_id"], "upsert" if t["mode"] != "shadow" else "would_upsert", outcome,
                     {"version": wo["version"], "external_id": ext, "error": err, "attempts": attempts})
                if outcome in ("synced", "dead"):
                    auditlog.append(c, actor=actor, action=f"integration.{outcome}", entity="work_order", entity_id=wo["wo_id"],
                                    payload={"target_id": target_id, "version": wo["version"], "external_id": ext, "error": err},
                                    key=db.audit_key, key_id=db.audit_key_id)
            res[outcome if outcome != "synced" else "sent"] += 1
    finally:
        if adapter is not None:
            adapter.close()
    return res
