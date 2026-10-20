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
Every create is logged as attempted before it is sent, so a create whose answer was lost is also found by its marker
on the next attempt instead of being created again. A create that certainly created nothing (refused with a 4xx, or no
connection made) is logged as refused and is no such evidence. A create whose answer was lost may also commit after the
next attempt searched: an order recovered after one is searched by marker once more (`VERIFY_DELAY_MS`), and a second
request carrying its marker makes a dead letter instead of an orphan.

One dispatcher per target at a time: a run holds the target's lease (events in `integration_log`), and a second run
reports `busy` and sends nothing. Before every external call and every recorded result the run checks that it still
holds the lease and that the target's mode has not changed, and stops otherwise. A run whose lease lapsed records a
failure only if no other run has written the order since; otherwise the newer result stands.

Failures:
- Transient (timeouts, connection errors, 408, 429, 5xx, an unreadable answer to a create or write): retried with exponential
  backoff, up to `max_attempts`.
- Permanent (other 4xx, an unexpected answer), or attempts exhausted: the item becomes a dead letter. It waits for an
  admin to requeue it, with a reason. Any other error on one order is a dead letter for that order; the run goes on.

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
import logging
import math
import os
import re
import uuid
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
MAX_ATTEMPTS_LIMIT, MAX_TIMEOUT_S = 100, 120
# the lease is renewed before every external call, and an order needs at most three calls of at most MAX_TIMEOUT_S each,
# so only a dispatcher that hung or crashed lets its lease lapse; it then blocks the target for LEASE_MS at most
LEASE_MS = 600_000
# a create whose answer was lost may still commit after a later attempt found nothing by marker and created again; an order
# recovered after such a create is searched by marker again at its first dispatch this long after (and at every send before)
VERIFY_DELAY_MS = 3_600_000
WEBHOOK_TOLERANCE_S = 300
CRED_PREFIX = "SENTINELLOOP_CRED_"
CRED_KEYS = {"odoo_json2": "api_key_env", "webhook": "secret_env"}
DEFAULT_PORTS = {"http": 80, "https": 443}
STOPPED = {"busy": "a dispatch of this target is already running; this one sent nothing",
           "lease": "the dispatch lease lapsed (another dispatch may have taken over); stopped before the next call",
           "mode": "the target's mode was changed (or the target disabled) during the run; stopped before the next call"}
log = logging.getLogger("sentinelloop.integration")


class IntegrationError(ValueError):
    pass


class IntegrationPermissionError(IntegrationError, PermissionDenied):
    pass


class TransientError(RuntimeError):
    pass


class NotSent(TransientError):
    """No connection was made, so the request was never sent: the CMMS cannot have acted on it."""


class PermanentError(RuntimeError):
    pass


class DuplicateRequests(PermanentError):
    """Besides the request SentinelLoop knows, another CMMS request carries the order's marker."""


# -- targets -----------------------------------------------------------------------------------------------------------
def _allowed_hosts() -> set[str]:
    return {h.strip().lower() for h in os.environ.get("SENTINELLOOP_INTEGRATION_HOSTS", "").split(",") if h.strip()}


def _is_local(host: str) -> bool:
    return host in LOCAL_HOSTS or host.endswith(LOCAL_SUFFIXES)


def check_url(base_url: str):
    if not isinstance(base_url, str) or any(ch <= " " or ch == "\x7f" for ch in base_url) or "\\" in base_url:
        raise IntegrationError("target URLs may not contain spaces, control characters or backslashes")
    u = urlparse(base_url)
    host = (u.hostname or "").lower()
    if u.scheme not in ("http", "https") or not host:
        raise IntegrationError(f"{base_url!r} is not an http(s) URL")
    if "@" in u.netloc or u.query or u.fragment:
        raise IntegrationError("target URLs may not carry credentials, a query string or a fragment")
    try:                                         # httpx, which sends the request, must see the same host and port as this check
        port, hx = u.port, httpx.URL(base_url)
    except (ValueError, httpx.InvalidURL):
        raise IntegrationError(f"{base_url!r} is not a valid URL (check the port)") from None
    if port == 0 or (hx.host or "").lower() != host or (hx.port or DEFAULT_PORTS[u.scheme]) != (port or DEFAULT_PORTS[u.scheme]):
        raise IntegrationError(f"{base_url!r} is not a valid URL (check the host and port)")
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
    check_config(kind, config)
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


def check_config(kind: str, config, ranges: bool = True) -> None:
    """Keys and values at registration, so a bad value is refused up front instead of failing every dispatch of the
    target. At every live dispatch (`ranges=False`) the keys, the credential names and the database name (sent as a
    header) are checked again; `_settings` only coerces the numbers, so a target stored by an earlier version keeps
    working."""
    if not isinstance(config, dict):
        raise IntegrationError("target config must be an object")
    if any(str(k).lower() in ("api_key", "password", "secret", "token") for k in config):
        raise IntegrationError("secrets may not be stored in target config; name an environment variable instead (api_key_env / secret_env)")
    unknown = sorted(set(config) - CONFIG_KEYS)
    if unknown:
        raise IntegrationError(f"unknown config keys {unknown}; allowed: {sorted(CONFIG_KEYS)}")
    for key in sorted(CONFIG_KEYS & set(CRED_KEYS.values())):
        if key == CRED_KEYS[kind] or key in config:
            _check_cred_name(config.get(key), key)
    db_name = config.get("database")
    if "database" in config and not (isinstance(db_name, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", db_name)):
        raise IntegrationError("config 'database' must be an Odoo database name (letters, digits, '_', '.', '-')")     # it is sent as a header
    if not ranges:
        return
    t = config.get("timeout_s")
    if "timeout_s" in config and not (isinstance(t, (int, float)) and not isinstance(t, bool) and math.isfinite(t) and 0 < t <= MAX_TIMEOUT_S):
        raise IntegrationError(f"config 'timeout_s' must be a number of seconds above 0 and at most {MAX_TIMEOUT_S}")
    m = config.get("max_attempts")
    if "max_attempts" in config and not (type(m) is int and 1 <= m <= MAX_ATTEMPTS_LIMIT):
        raise IntegrationError(f"config 'max_attempts' must be a whole number from 1 to {MAX_ATTEMPTS_LIMIT}")


def _settings(config: dict) -> tuple[float, int]:
    """(timeout_s, max_attempts) for a live dispatch. Values an earlier version stored and used (timeout_s 300 or "15",
    max_attempts 8.0 or 500) are coerced as it did, not refused; the timeout is clamped to MAX_TIMEOUT_S, which the
    lease relies on. Only a value that cannot be used at all is refused."""
    try:
        timeout_s, max_attempts = float(config.get("timeout_s", 15)), int(config.get("max_attempts", DEFAULT_MAX_ATTEMPTS))
    except (TypeError, ValueError, OverflowError):
        raise IntegrationError("config 'timeout_s' and 'max_attempts' must be numbers") from None
    if not (math.isfinite(timeout_s) and timeout_s > 0):
        raise IntegrationError("config 'timeout_s' must be a number of seconds above 0")
    return min(timeout_s, MAX_TIMEOUT_S), max_attempts


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
        lines.append(f"<p>P(failure before {e(ex.get('decision_horizon_hours'))} h): {float(ex['p_fail_decision_horizon']):.2f} "
                     "(model-implied, not calibrated; see SentinelLoop KNOWN_LIMITATIONS E6)</p>")
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
        except (httpx.ConnectError, httpx.ConnectTimeout) as e:      # no connection was made: the request was never sent
            raise NotSent(f"{type(e).__name__} calling {model}.{method}") from None
        except httpx.RequestError as e:                  # timeouts, connection and decoding errors
            raise TransientError(f"{type(e).__name__} calling {model}.{method}") from None
        if r.status_code == 200:
            try:
                return r.json()
            except ValueError:
                # a sign-in or proxy page, or a damaged body, not Odoo's answer. A create or write may still have been
                # committed: it is retried (a create's retry looks for the request by its marker first); a read is refused
                raise (TransientError if method in ("create", "write") else PermanentError)(
                    f"HTTP 200 from {model}.{method} with a body that is not JSON (a sign-in or proxy page?)") from None
        try:
            msg = str(r.json().get("message", ""))[:300]
        except Exception:
            msg = ""
        text = f"HTTP {r.status_code} from {model}.{method}: {msg}"
        if r.status_code in (408, 429) or r.status_code >= 500:
            raise TransientError(text)
        raise PermanentError(text)

    def find_equipment(self, ref: str) -> int | None:
        rows = _records(self.call("maintenance.equipment", "search_read", {"domain": [["serial_no", "=", ref]], "fields": ["id", "name"]}),
                        "maintenance.equipment.search_read")
        return rows[0]["id"] if rows else None

    def upsert(self, wo_id: str, payload: dict, external_id: str | None, recover: bool = False, exclude=frozenset(),
               verify: bool = False, before_send=None) -> str:
        """Without an external id the exact delimited marker is searched first, whatever the request is now named
        (mirroring renames it).
        - `recover` (the log shows an earlier delivery, or a create attempt whose answer may have been lost): the one
          request carrying the marker, other than those in `exclude`, is adopted; two or more make a dead letter.
        - otherwise (a first send) nothing is adopted, so a record planted with a predictable marker never is. The ids
          found go to `before_send`, which records them, so a later recovery never adopts them either.
        - `verify` (with an external id: an earlier create may have committed late): the marker is searched too. The
          known request is written all the same, and any other one carrying the marker (not in `exclude`) makes a
          dead letter that names it.
        `before_send(creating, seen)` runs just before the create or write, and may stop it by raising."""
        seen, others = [], []
        if external_id is None or verify:
            m = _html(marker(wo_id))
            rows = _records(self.call("maintenance.request", "search_read", {"domain": [["description", "ilike", m]], "fields": ["id", "description"]}),
                            "maintenance.request.search_read")
            seen = sorted(r["id"] for r in rows if m in str(r.get("description") or ""))
            found = [i for i in seen if i not in exclude]
            if external_id is not None:
                others = [i for i in found if str(i) != external_id]
            elif recover and len(found) > 1:
                raise PermanentError(f"more than one CMMS request carries the marker for {wo_id} (ids {found}); "
                                     f"a person must decide which one is SentinelLoop's")
            elif recover and found:
                external_id = str(found[0])
        if before_send is not None:
            before_send(external_id is None, seen)
        if external_id is not None:
            self.call("maintenance.request", "write", {"ids": [int(external_id)], "vals": payload})
            if others:         # SentinelLoop's own request is kept up to date (a withdrawal reaches it); a person decides the rest
                raise DuplicateRequests(f"CMMS requests {others} also carry the marker for {wo_id}; SentinelLoop's request is {external_id} "
                                        f"(updated). A create whose answer was lost may have committed late: a person must decide which "
                                        f"to keep, then requeue")
            return external_id
        ids = self.call("maintenance.request", "create", {"vals_list": [payload]})
        if not (isinstance(ids, list) and len(ids) == 1 and type(ids[0]) is int):
            raise TransientError("unexpected answer to maintenance.request.create; the next attempt looks for the request by marker before creating")
        return str(ids[0])

    def close(self):
        self.client.close()


def _records(rows, what: str) -> list[dict]:
    """A search_read answer must be a list of records with integer ids; anything else is refused, never indexed blindly."""
    if not isinstance(rows, list) or not all(isinstance(r, dict) and type(r.get("id")) is int for r in rows):
        raise PermanentError(f"unexpected answer to {what}")
    return rows


def sign_webhook(secret: bytes, ts_s: int, body: bytes) -> str:
    return "sha256=" + hmac.new(secret, f"{ts_s}.".encode() + body, hashlib.sha256).hexdigest()


def verify_webhook(secret: bytes, ts_s, body: bytes, signature, now_s: int, tolerance_s: int = WEBHOOK_TOLERANCE_S) -> bool:
    """Receiver side: constant-time signature check plus a replay window on the signed timestamp. `ts_s` and
    `signature` may be the raw header values; anything malformed is rejected (False), never raised."""
    ts = str(ts_s) if type(ts_s) is int else ts_s
    if not isinstance(ts, str) or not re.fullmatch(r"[0-9]{1,15}", ts) or not isinstance(signature, str) or not signature.isascii():
        return False
    if abs(now_s - int(ts)) > tolerance_s:
        return False
    return hmac.compare_digest(sign_webhook(secret, ts, body), signature)


class Webhook:
    def __init__(self, url: str, secret: bytes, transport=None, timeout_s: float = 10.0):
        self.url, self.secret = url, secret
        self.client = httpx.Client(timeout=timeout_s, transport=transport)

    def upsert(self, wo_id: str, payload: dict, external_id: str | None, recover: bool = False, exclude=frozenset(),
               verify: bool = False, before_send=None) -> str:
        body = json.dumps({"event": "work_order.upsert", "wo_id": wo_id, "payload": payload}, sort_keys=True).encode()
        ts = int(_now_ms() / 1000)
        if before_send is not None:
            before_send(False, [])
        try:
            r = self.client.post(self.url, content=body, headers={"Content-Type": "application/json", "X-SentinelLoop-Timestamp": str(ts),
                                                                  "X-SentinelLoop-Signature": sign_webhook(self.secret, ts, body)})
        except httpx.RequestError as e:
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
    """(the adapter for a live dispatch, the target's max_attempts)."""
    cfg = t["config"]
    try:
        check_config(t["kind"], cfg, ranges=False)     # a target stored before values were checked gives dead letters, not a crash
        timeout_s, max_attempts = _settings(cfg)
        check_url(t["base_url"])                       # the allowlist is checked at every dispatch, not only at registration
    except IntegrationError as e:
        raise PermanentError(str(e)) from None
    try:
        if t["kind"] == "odoo_json2":
            env = cfg.get("api_key_env")
            key = os.environ.get(env or "")
            if not key:
                raise PermanentError(f"credential environment variable {env!r} is not set")
            return OdooJson2(t["base_url"], key, cfg.get("database"), transport=transport, timeout_s=timeout_s), max_attempts
        env = cfg.get("secret_env")
        secret = os.environ.get(env or "")
        if not secret or len(secret) < 32:
            raise PermanentError(f"webhook secret environment variable {env!r} is not set or shorter than 32 characters")
        return Webhook(t["base_url"], secret.encode(), transport=transport), max_attempts
    except (TypeError, ValueError, httpx.InvalidURL) as e:
        raise PermanentError(f"the target cannot be reached as configured ({type(e).__name__})") from None


# -- dispatch ----------------------------------------------------------------------------------------------------------
def _backoff_s(attempts: int, wo_id: str) -> int:
    base = min(BACKOFF_CAP_S, BACKOFF_BASE_S * 2 ** (attempts - 1))
    jitter = int(hashlib.sha256(f"{wo_id}:{attempts}".encode()).hexdigest()[:4], 16) / 0xFFFF      # deterministic 0..1
    return int(base * (1 + 0.2 * jitter))


def _log(c, target_id, wo_id, action, outcome, detail) -> int:
    return c.execute("INSERT INTO integration_log (ts, target_id, wo_id, action, outcome, detail_json) VALUES (?,?,?,?,?,?)",
                     (now_iso(), target_id, wo_id, action, outcome, json.dumps(detail, default=str))).lastrowid


def _recovery_evidence(db, target_id: str, wo_id: str) -> tuple[bool, set[int], bool]:
    """Whether SentinelLoop itself may have created a CMMS request for this order earlier: a successful real upsert, or
    a create attempt (logged before the call) whose answer may have been lost. An attempt later logged as refused (a
    4xx, or no connection made) created nothing and is no evidence. Only then may a request be recovered by marker;
    shadow items never delivered anything. Also returns the ids that carried the marker before one of SentinelLoop's
    creates (none of them is SentinelLoop's, so none is ever adopted), and whether such an attempt is unresolved (its
    create may still commit)."""
    with db.connect() as c:
        rows = c.execute("SELECT id, action, outcome, detail_json FROM integration_log WHERE target_id = ? AND wo_id = ? AND "
                         "((action = 'upsert' AND outcome = 'synced') OR action = 'create_attempt')", (target_id, wo_id)).fetchall()
    detail = {r["id"]: json.loads(r["detail_json"]) for r in rows}
    refused = {detail[r["id"]].get("attempt") for r in rows if r["action"] == "create_attempt" and r["outcome"] == "refused"}
    attempts = [r["id"] for r in rows if r["action"] == "create_attempt" and r["outcome"] == "attempted"]
    seen = {int(i) for a in attempts for i in detail[a].get("seen_with_marker", [])}
    unsure = any(a not in refused for a in attempts)
    return unsure or any(r["action"] == "upsert" for r in rows), seen, unsure


# -- one dispatcher per target: a lease kept as events in integration_log ------------------------------------------------
def _lease(c, target_id: str) -> tuple[str | None, int]:
    """(owner, expiry in wall-clock ms) of the target's dispatch lease; (None, 0) once released."""
    r = c.execute("SELECT outcome, detail_json FROM integration_log WHERE target_id = ? AND action = 'dispatch_lease' ORDER BY id DESC LIMIT 1",
                  (target_id,)).fetchone()
    if r is None or r["outcome"] != "held":
        return None, 0
    d = json.loads(r["detail_json"])
    return d.get("owner"), int(d.get("expires_ms") or 0)


def _claim_lease(db, target_id: str, owner: str, wall_ms: int | None = None) -> bool:
    """Take the lease in one IMMEDIATE transaction; False while another owner holds one that has not expired."""
    wall = _now_ms() if wall_ms is None else int(wall_ms)
    with db.tx() as c:
        holder, expires = _lease(c, target_id)
        if holder not in (None, owner) and expires > wall:
            return False
        _log(c, target_id, None, "dispatch_lease", "held", {"owner": owner, "expires_ms": wall + LEASE_MS})
    return True


def _hold_lease(c, target_id: str, owner: str) -> bool:
    """Inside a write transaction: whether `owner` still holds an unexpired lease, renewing it once half has run out."""
    wall = _now_ms()
    holder, expires = _lease(c, target_id)
    if holder != owner or expires <= wall:
        return False
    if expires - wall < LEASE_MS // 2:
        _log(c, target_id, None, "dispatch_lease", "held", {"owner": owner, "expires_ms": wall + LEASE_MS})
    return True


def _release_lease(db, target_id: str, owner: str):
    with db.tx() as c:
        if _lease(c, target_id)[0] == owner:
            _log(c, target_id, None, "dispatch_lease", "released", {"owner": owner})


def _run_check(c, target_id: str, owner: str, mode: str) -> str | None:
    """Inside a write transaction, before every external call and every recorded result: why the run must stop (its
    lease lapsed, or the target's mode or enabled flag changed since the run started), or None."""
    if not _hold_lease(c, target_id, owner):
        return "lease"
    r = c.execute("SELECT mode, enabled FROM integration_targets WHERE target_id = ?", (target_id,)).fetchone()
    return None if r is not None and r["mode"] == mode and r["enabled"] else "mode"


class _Stop(Exception):
    pass


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


def _due(db, target_id: str, now: int, max_items: int, live: bool) -> tuple[list, int]:
    """The orders to deliver now, and the number skipped as dead letters. Live, an unchanged order is due too once its
    marker search is (`verify_after_ms`)."""
    state = {i["wo_id"]: i for i in items(db, target_id)}
    due, skipped = [], 0
    candidates = workorders.list_orders(db, states_in=list(SENT_STATES))
    candidates += [w for w in workorders.list_orders(db, states_in=list(FOLLOW_STATES)) if state.get(w["wo_id"])]
    for wo in candidates:
        it = state.get(wo["wo_id"])
        if it and it["status"] == "dead":
            skipped += 1
            continue
        if it and it["synced_version"] == wo["version"] and not (live and it.get("verify_after_ms") is not None and it["verify_after_ms"] <= now):
            continue
        if it and it["status"] == "retry" and (it["next_attempt_ms"] or 0) > now:
            continue
        due.append((wo, it))
    return due[:max_items], skipped


def dispatch(db, target_id: str, now_ms: int | None = None, transport=None, max_items: int = 200, actor: str = "integration",
             role: str = "integration") -> dict:
    """One run per target at a time: the run holds the target's lease, and a run that finds it held reports `busy` and
    sends nothing. A run stops before its next external call when its lease lapsed or the target's mode changed;
    `stopped` says why."""
    if role not in DISPATCHERS:
        raise IntegrationPermissionError(f"role {role!r} may not dispatch")
    now = int(now_ms if now_ms is not None else _now_ms())
    t = get_target(db, target_id)
    if t is None:
        raise IntegrationError(f"unknown target {target_id}")
    res = {"target_id": target_id, "mode": t["mode"], "considered": 0, "shadow": 0, "sent": 0, "retry": 0, "dead": 0, "skipped": 0,
           "busy": False, "stopped": None}
    if not t["enabled"]:
        return res
    due, res["skipped"] = _due(db, target_id, now, max_items, t["mode"] != "shadow")
    res["considered"] = len(due)
    if not due:
        return res
    owner = uuid.uuid4().hex
    if not _claim_lease(db, target_id, owner):
        return {**res, "considered": 0, "busy": True, "stopped": STOPPED["busy"]}
    try:
        t = get_target(db, target_id)                  # read again under the lease: another run may have finished meanwhile
        due, res["skipped"] = _due(db, target_id, now, max_items, t["mode"] != "shadow")
        res.update(mode=t["mode"], considered=len(due))
        if t["enabled"] and due:
            _run(db, t, due, now, transport, actor, owner, res)
    finally:
        _release_lease(db, target_id, owner)
    return res


def _run(db, t: dict, due: list, now: int, transport, actor: str, owner: str, res: dict):
    target_id, mode = t["target_id"], t["mode"]
    adapter, adapter_error, max_attempts = None, None, DEFAULT_MAX_ATTEMPTS
    if mode != "shadow":
        try:
            adapter, max_attempts = _adapter(t, transport)
        except PermanentError as e:
            adapter_error = str(e)
    equipment_cache: dict = {}
    try:
        for wo, it in due:
            with db.tx() as c:
                why = _run_check(c, target_id, owner, mode)
            if why:
                res["stopped"] = STOPPED[why]
                break
            eq, outcome, err, ext, payload = None, None, None, (it or {}).get("external_id"), None
            verify = ext is not None and (it or {}).get("verify_after_ms") is not None     # an earlier create may have committed late
            attempt, unsure, check, definite = {}, False, None, False

            def before_send(creating: bool, seen: list, wo=wo, attempt=attempt):
                with db.tx() as c:
                    why = _run_check(c, target_id, owner, mode)
                    if why:
                        raise _Stop(why)
                    if creating:       # logged before the call: if its answer is lost, the next attempt searches by marker first
                        attempt["id"] = _log(c, target_id, wo["wo_id"], "create_attempt", "attempted",
                                             {"version": wo["version"], "seen_with_marker": seen})
            try:
                if adapter_error:
                    raise PermanentError(adapter_error)
                asset = registry.get_asset(db, wo["asset_id"])
                ref = (asset.config or {}).get("cmms_equipment_ref")
                if adapter is not None and ref:
                    if ref not in equipment_cache:
                        equipment_cache[ref] = adapter.find_equipment(ref)
                    eq = equipment_cache[ref]
                payload = odoo_payload(wo, asset, eq)
                if mode == "shadow":
                    outcome = "shadow"
                else:
                    recover, seen, unsure = _recovery_evidence(db, target_id, wo["wo_id"]) if ext is None or verify else (False, set(), False)
                    unsure = unsure and ext is None        # recovered while an earlier create may still commit: search again later
                    ext = adapter.upsert(wo["wo_id"], payload, ext, recover=recover, exclude=seen, verify=verify, before_send=before_send)
                    outcome, check = "synced", ("clean" if verify else None)
            except _Stop as e:
                res["stopped"] = STOPPED[str(e)]
                break
            except TransientError as e:        # NotSent: certainly nothing happened in the CMMS
                outcome, err, definite = "retry", str(e), isinstance(e, NotSent)
            except DuplicateRequests as e:
                outcome, err, check = "dead", str(e), "duplicate"
            except PermanentError as e:        # a refusal (4xx), a bad config or a read refused: nothing changed in the CMMS
                outcome, err, definite = "dead", str(e), True
            except Exception as e:             # anything unexpected stays with this order: a recorded dead letter, and the run goes on
                log.exception("unexpected error delivering %s to %s", wo["wo_id"], target_id)
                outcome, err = "dead", f"unexpected {type(e).__name__} while delivering this order (details in the server log)"
            outcome, why = _record(db, t, wo, it, owner, outcome, err, ext, payload, now, max_attempts, actor,
                                   refused_attempt=attempt.get("id") if definite else None, created=bool(attempt), definite=definite,
                                   unsure=unsure, check=check)
            if outcome is not None:
                res[outcome if outcome != "synced" else "sent"] += 1
            if why:
                res["stopped"] = STOPPED[why]
                break
    finally:
        if adapter is not None:
            adapter.close()


def _changed(cur: dict, it: dict | None) -> bool:
    """Whether the stored item differs from what the run read under its lease: another run has written it since."""
    return any(cur.get(k) != (it or {}).get(k) for k in ("status", "external_id", "synced_version", "attempts", "updated_at"))


def _record(db, t: dict, wo: dict, it: dict | None, owner: str, outcome: str, err, ext, payload, now: int, max_attempts: int, actor: str,
            refused_attempt: int | None = None, created: bool = False, definite: bool = False, unsure: bool = False, check: str | None = None):
    """Record one order's result in one transaction, against the item as it is now (`it`: as the run read it). Returns
    (outcome, why the run must stop or None); the outcome is None when nothing was recorded.
    - `refused_attempt`: this run's create attempt, which certainly created nothing; logged so it is no recovery evidence.
    - `created`: this run attempted a create; `definite`: its failure certainly changed nothing in the CMMS.
    - `unsure`: the order was recovered while an earlier create may still commit, so it is searched by marker again later.
    - `check`: this send searched for a second request carrying the marker ('clean': none; 'duplicate': one, reported)."""
    target_id, mode, wo_id = t["target_id"], t["mode"], wo["wo_id"]
    pj = json.dumps(payload, sort_keys=True) if payload is not None else None
    with db.tx() as c:
        if refused_attempt is not None:
            _log(c, target_id, wo_id, "create_attempt", "refused", {"attempt": refused_attempt, "error": err})
        why = _run_check(c, target_id, owner, mode)
        if why and outcome == "shadow":
            return None, why       # recorded after going live, a shadow result would keep the order from the live run
        cur = c.execute("SELECT * FROM sync_items WHERE target_id = ? AND wo_id = ?", (target_id, wo_id)).fetchone()
        cur = dict(cur) if cur else {}
        if why == "lease" and outcome in ("retry", "dead") and _changed(cur, it):
            # another run has written this order since this run's lease lapsed: its result stands. Unless this run's
            # failure certainly changed nothing, the order is sent again, after a create searching by marker first
            if not definite:
                c.execute("UPDATE sync_items SET synced_version = NULL, verify_after_ms = ? WHERE target_id = ? AND wo_id = ?",
                          (now + VERIFY_DELAY_MS if created else cur.get("verify_after_ms"), target_id, wo_id))
            _log(c, target_id, wo_id, "upsert", outcome, {"version": wo["version"], "error": err, "stopped": why, "recorded": False})
            return None, why
        conflict = ext is not None and cur.get("external_id") not in (None, ext)
        if conflict:
            # never replace one CMMS id with another: the order now has two requests, which a person must sort out
            outcome, err = "dead", (f"two CMMS requests belong to {wo_id}: {cur['external_id']} (stored) and {ext} (from a dispatch whose lease "
                                    f"had lapsed); a person must decide which one to keep")
        ext = cur.get("external_id") or ext
        verify_after = cur.get("verify_after_ms")
        if conflict or check == "duplicate" or (check == "clean" and verify_after is not None and verify_after <= now):
            verify_after = None    # searched after the delay, or a second request was found and reported: a person now has it
        if outcome == "synced" and unsure:
            verify_after = now + VERIFY_DELAY_MS
        attempts = (cur.get("attempts") or 0) + 1 if outcome in ("retry", "dead") else 0
        if outcome == "retry" and attempts >= max_attempts:
            outcome = "dead"
        nxt = now + _backoff_s(attempts, wo_id) * 1000 if outcome == "retry" else None
        if outcome in ("shadow", "synced"):
            synced = None if why == "lease" else wo["version"]        # after a lapse another run may have written newer data: send again
        else:
            synced = cur.get("synced_version")
        c.execute("INSERT INTO sync_items (target_id, wo_id, synced_version, pending_version, external_id, status, attempts, next_attempt_ms, "
                  "last_error, payload_json, payload_sha256, updated_at, verify_after_ms) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?) "
                  "ON CONFLICT(target_id, wo_id) DO UPDATE SET "
                  "synced_version = excluded.synced_version, pending_version = excluded.pending_version, external_id = excluded.external_id, "
                  "status = excluded.status, attempts = excluded.attempts, next_attempt_ms = excluded.next_attempt_ms, last_error = excluded.last_error, "
                  "payload_json = excluded.payload_json, payload_sha256 = excluded.payload_sha256, updated_at = excluded.updated_at, "
                  "verify_after_ms = excluded.verify_after_ms",
                  (target_id, wo_id, synced, wo["version"], ext, outcome, attempts, nxt, err, pj, hashlib.sha256(pj.encode()).hexdigest() if pj else None,
                   now_iso(), verify_after))
        detail = {"version": wo["version"], "external_id": ext, "error": err, "attempts": attempts}
        _log(c, target_id, wo_id, "upsert" if mode != "shadow" else "would_upsert", outcome, {**detail, "stopped": why} if why else detail)
        if outcome in ("synced", "dead"):
            auditlog.append(c, actor=actor, action=f"integration.{outcome}", entity="work_order", entity_id=wo_id,
                            payload={"target_id": target_id, "version": wo["version"], "external_id": ext, "error": err},
                            key=db.audit_key, key_id=db.audit_key_id)
    return outcome, why
