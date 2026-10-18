"""CMMS integration: shadow mode by default, idempotent upsert, retries with backoff, dead letters, host allowlist,
signed webhooks (tests first).

The CMMS here is a TEST DOUBLE: an in-process fake of Odoo's JSON-2 API (`POST /json/2/<model>/<method>`, bearer API
key, body = {"ids", "context", method parameters}), written from Odoo 19's documentation
(odoo/documentation 19.0, content/developer/reference/external_api.rst, read 2026-10-18). Each request is checked
against that documented shape (contract test). The same scenario runs against a real Odoo Community sandbox in
tests/test_app_odoo_sandbox.py when SENTINELLOOP_ODOO_URL is set.
"""
import json

import httpx
import pytest

from sentinelloop.app import auditlog, db as dbmod, integration, registry, workorders
from sentinelloop.app.timeutil import HOUR_MS, iso, parse_ts
from test_app_foundation import KEY, pump, pump_type

ODOO = "http://localhost:8069"
API_KEY = "test-odoo-key-not-secret"


class FakeOdoo:
    """Minimal maintenance.request / maintenance.equipment store behind the documented JSON-2 surface."""
    ALLOWED = {("maintenance.request", "search_read"), ("maintenance.request", "create"), ("maintenance.request", "write"),
               ("maintenance.request", "read"), ("maintenance.equipment", "search_read")}

    def __init__(self):
        self.requests, self.equipment, self.calls, self.fail_next = {}, {7: {"id": 7, "name": "P-101 pump", "serial_no": "P-101"}}, [], []
        self.next_id = 100

    def __call__(self, request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.headers["authorization"].lower().startswith("bearer ")
        assert request.headers["content-type"].startswith("application/json")
        parts = request.url.path.split("/")
        assert parts[1] == "json" and parts[2] == "2" and len(parts) == 5, request.url.path
        model, method = parts[3], parts[4]
        body = json.loads(request.content)
        assert isinstance(body, dict)
        self.calls.append((model, method, body))
        if self.fail_next:
            kind = self.fail_next.pop(0)
            if kind == "timeout":
                raise httpx.ReadTimeout("simulated timeout", request=request)
            return httpx.Response(kind, json={"name": "werkzeug.exceptions.X", "message": f"simulated {kind}", "arguments": [], "context": {},
                                              "debug": "Traceback ... SECRET_INTERNAL_PATH"})
        if request.headers["authorization"] != f"bearer {API_KEY}":
            return httpx.Response(401, json={"name": "werkzeug.exceptions.Unauthorized", "message": "Invalid apikey", "arguments": ["Invalid apikey", 401],
                                             "context": {}, "debug": "Traceback ... SECRET_INTERNAL_PATH"})
        assert (model, method) in self.ALLOWED, f"unexpected call {model}.{method}"
        if method == "search_read":
            store = self.requests if model == "maintenance.request" else self.equipment
            out = [r for r in store.values() if all(self._match(r, f, op, v) for f, op, v in body.get("domain", []))]
            return httpx.Response(200, json=[{k: r.get(k) for k in body.get("fields", list(r))} | {"id": r["id"]} for r in out])
        if method == "create":
            ids = []
            for vals in body["vals_list"]:
                assert "name" in vals
                self.next_id += 1
                self.requests[self.next_id] = {"id": self.next_id, **vals}
                ids.append(self.next_id)
            return httpx.Response(200, json=ids)
        if method == "write":
            for i in body["ids"]:
                self.requests[i].update(body["vals"])
            return httpx.Response(200, json=True)
        if method == "read":
            return httpx.Response(200, json=[self.requests[i] for i in body["ids"]])
        raise AssertionError(method)

    @staticmethod
    def _match(r, f, op, v):
        x = r.get(f)
        if op == "=":
            return x == v
        if op == "ilike":
            return x is not None and v.strip("%").lower() in str(x).lower()
        raise AssertionError(op)


@pytest.fixture
def ctx(tmp_path, monkeypatch):
    monkeypatch.setenv("SENTINELLOOP_INTEGRATION_HOSTS", "localhost,cmms.example.com")
    monkeypatch.setenv("SENTINELLOOP_CRED_ODOO_TEST", API_KEY)
    d = dbmod.Database(tmp_path / "i.db", audit_key=KEY, audit_key_id="test")
    d.migrate()
    registry.create_site(d, "site1", "Plant 1", "UTC", actor="admin")
    registry.create_asset_type(d, pump_type(), actor="admin")
    a = pump("P-101")
    registry.create_asset(d, a, actor="admin")
    registry.update_asset(d, "P-101", {"config": {"cmms_equipment_ref": "P-101"}}, actor="admin", reason="CMMS equipment mapping")
    fake = FakeOdoo()
    return {"db": d, "fake": fake, "transport": httpx.MockTransport(fake)}


def _approved_order(d, key="k1", title="Inspect P-101"):
    o = workorders.create(d, asset_id="P-101", job_type="inspect", priority_class="P1", title=title, origin="system", actor="sys", role="system",
                          idempotency_key=key)
    workorders.transition(d, o["wo_id"], "submit", actor="pat", role="planner")
    workorders.transition(d, o["wo_id"], "approve", actor="pat", role="planner")
    return workorders.get(d, o["wo_id"])


def _target(ctx, mode=None, **kw):
    cfg = {"database": "sandbox", "api_key_env": "SENTINELLOOP_CRED_ODOO_TEST", **kw}
    args = dict(target_id="odoo", kind="odoo_json2", base_url=ODOO, config=cfg, actor="ada", role="admin")
    if mode:
        args["mode"] = mode
        args["reason"] = "sandbox test"
    return integration.register_target(ctx["db"], **args)


def test_targets_default_to_read_only_shadow_mode_and_shadow_never_calls_the_cmms(ctx):
    t = _target(ctx)
    assert t["mode"] == "shadow"
    wo = _approved_order(ctx["db"])
    res = integration.dispatch(ctx["db"], "odoo", now_ms=parse_ts("2026-10-18T00:00:00Z"), transport=ctx["transport"])
    assert ctx["fake"].calls == []                                    # nothing left the system
    assert res["shadow"] == 1 and res["sent"] == 0
    item = integration.items(ctx["db"], "odoo")[0]
    assert item["wo_id"] == wo["wo_id"] and item["status"] == "shadow"
    assert item["payload"]["name"].startswith("[SentinelLoop]") and f"[SentinelLoop-Ref:{wo['wo_id']}]" in item["payload"]["description"]


def test_switching_to_draft_requests_needs_an_admin_and_a_reason_and_is_audited(ctx):
    _target(ctx)
    with pytest.raises(integration.IntegrationPermissionError):
        integration.set_mode(ctx["db"], "odoo", "draft_requests", actor="pat", role="planner", reason="x")
    with pytest.raises(integration.IntegrationError):
        integration.set_mode(ctx["db"], "odoo", "draft_requests", actor="ada", role="admin", reason=" ")
    integration.set_mode(ctx["db"], "odoo", "draft_requests", actor="ada", role="admin", reason="sandbox test")
    with ctx["db"].connect() as c:
        acts = [r["action"] for r in c.execute("SELECT action FROM audit_events WHERE entity = 'integration_target'")]
    assert "integration.mode_changed" in acts


def test_draft_mode_creates_once_updates_on_change_and_never_duplicates(ctx):
    _target(ctx, mode="draft_requests")
    d, f, tr = ctx["db"], ctx["fake"], ctx["transport"]
    wo = _approved_order(d)
    now = parse_ts("2026-10-18T00:00:00Z")
    integration.dispatch(d, "odoo", now_ms=now, transport=tr)
    creates = [c for c in f.calls if c[1] == "create"]
    assert len(creates) == 1
    vals = creates[0][2]["vals_list"][0]
    assert vals["priority"] == "3" and vals["equipment_id"] == 7 and vals["maintenance_type"] == "preventive"
    assert set(vals) <= integration.ODOO_WRITABLE_FIELDS                     # never stages, closing or deletion
    n = len(f.calls)
    integration.dispatch(d, "odoo", now_ms=now + 60_000, transport=tr)        # nothing changed: no call
    assert len(f.calls) == n
    workorders.transition(d, wo["wo_id"], "schedule", actor="pat", role="planner",
                          data={"start": "2026-10-19T08:00:00Z", "end": "2026-10-19T12:00:00Z", "technicians": ["T1"]})
    integration.dispatch(d, "odoo", now_ms=now + 120_000, transport=tr)
    writes = [c for c in f.calls if c[1] == "write"]
    assert len(writes) == 1 and writes[0][2]["vals"]["schedule_date"] == "2026-10-19 08:00:00"
    assert len(f.requests) == 1
    # the local mapping is lost: the marker in the description finds the existing request instead of creating a second
    integration._forget_external_id(d, "odoo", wo["wo_id"])
    workorders.reprioritise(d, wo["wo_id"], "P2", None, None, {}, actor="sys", role="system", reason="test")
    integration.dispatch(d, "odoo", now_ms=now + 180_000, transport=tr)
    assert len(f.requests) == 1


def test_unapproved_work_never_leaves_the_system(ctx):
    _target(ctx, mode="draft_requests")
    d = ctx["db"]
    o = workorders.create(d, asset_id="P-101", job_type="inspect", priority_class="P2", title="pending", origin="system", actor="sys", role="system",
                          idempotency_key="k-pending")
    workorders.transition(d, o["wo_id"], "submit", actor="pat", role="planner")
    res = integration.dispatch(d, "odoo", now_ms=parse_ts("2026-10-18T00:00:00Z"), transport=ctx["transport"])
    assert ctx["fake"].calls == [] and res["sent"] == 0 and integration.items(d, "odoo") == []


def test_transient_failures_are_retried_with_backoff_then_delivered(ctx):
    _target(ctx, mode="draft_requests")
    d, f, tr = ctx["db"], ctx["fake"], ctx["transport"]
    _approved_order(d)
    f.fail_next = [503, "timeout"]
    now = parse_ts("2026-10-18T00:00:00Z")
    integration.dispatch(d, "odoo", now_ms=now, transport=tr)
    it = integration.items(d, "odoo")[0]
    assert it["status"] == "retry" and it["attempts"] == 1 and it["next_attempt_ms"] > now
    integration.dispatch(d, "odoo", now_ms=now + 1000, transport=tr)            # too early: nothing attempted
    assert integration.items(d, "odoo")[0]["attempts"] == 1
    integration.dispatch(d, "odoo", now_ms=it["next_attempt_ms"], transport=tr)  # timeout
    it2 = integration.items(d, "odoo")[0]
    assert it2["status"] == "retry" and it2["attempts"] == 2 and (it2["next_attempt_ms"] - it["next_attempt_ms"]) > (it["next_attempt_ms"] - now)
    integration.dispatch(d, "odoo", now_ms=it2["next_attempt_ms"], transport=tr)
    assert integration.items(d, "odoo")[0]["status"] == "synced" and len(f.requests) == 1


def test_permanent_errors_go_to_dead_letters_without_leaking_server_internals_and_can_be_requeued(ctx, monkeypatch):
    _target(ctx, mode="draft_requests")
    d, f, tr = ctx["db"], ctx["fake"], ctx["transport"]
    wo = _approved_order(d)
    monkeypatch.setenv("SENTINELLOOP_CRED_ODOO_TEST", "wrong-key")
    integration.dispatch(d, "odoo", now_ms=parse_ts("2026-10-18T00:00:00Z"), transport=tr)
    it = integration.items(d, "odoo")[0]
    assert it["status"] == "dead" and "401" in it["last_error"] and "Invalid apikey" in it["last_error"]
    assert "SECRET_INTERNAL_PATH" not in it["last_error"] and "wrong-key" not in it["last_error"]
    monkeypatch.setenv("SENTINELLOOP_CRED_ODOO_TEST", API_KEY)
    integration.dispatch(d, "odoo", now_ms=parse_ts("2026-10-18T01:00:00Z"), transport=tr)
    assert integration.items(d, "odoo")[0]["status"] == "dead"                 # dead letters wait for a person
    with pytest.raises(integration.IntegrationPermissionError):
        integration.requeue(d, "odoo", wo["wo_id"], actor="pat", role="planner", reason="fixed")
    integration.requeue(d, "odoo", wo["wo_id"], actor="ada", role="admin", reason="API key corrected")
    integration.dispatch(d, "odoo", now_ms=parse_ts("2026-10-18T02:00:00Z"), transport=tr)
    assert integration.items(d, "odoo")[0]["status"] == "synced"


def test_retries_stop_after_the_attempt_limit(ctx):
    _target(ctx, mode="draft_requests", max_attempts=3)
    d, f, tr = ctx["db"], ctx["fake"], ctx["transport"]
    _approved_order(d)
    f.fail_next = [503] * 10
    t = parse_ts("2026-10-18T00:00:00Z")
    for _ in range(5):
        integration.dispatch(d, "odoo", now_ms=t, transport=tr)
        it = integration.items(d, "odoo")[0]
        t = (it["next_attempt_ms"] or t) + 1
    assert it["status"] == "dead" and it["attempts"] == 3


def test_targets_must_be_on_the_host_allowlist_and_use_https_unless_local(ctx):
    with pytest.raises(integration.IntegrationError):
        integration.register_target(ctx["db"], target_id="evil", kind="odoo_json2", base_url="https://attacker.example.net",
                                    config={"api_key_env": "SENTINELLOOP_CRED_X"}, actor="ada", role="admin")
    with pytest.raises(integration.IntegrationError):
        integration.register_target(ctx["db"], target_id="plain", kind="odoo_json2", base_url="http://cmms.example.com",
                                    config={"api_key_env": "SENTINELLOOP_CRED_X"}, actor="ada", role="admin")
    with pytest.raises(integration.IntegrationPermissionError):
        integration.register_target(ctx["db"], target_id="x", kind="odoo_json2", base_url="https://cmms.example.com",
                                    config={"api_key_env": "SENTINELLOOP_CRED_X"}, actor="pat", role="planner")
    t = integration.register_target(ctx["db"], target_id="ok", kind="odoo_json2", base_url="https://cmms.example.com",
                                    config={"api_key_env": "SENTINELLOOP_CRED_X"}, actor="ada", role="admin")
    assert t["mode"] == "shadow"


def test_secrets_are_never_stored_in_the_database(ctx):
    _target(ctx, mode="draft_requests")
    _approved_order(ctx["db"])
    integration.dispatch(ctx["db"], "odoo", now_ms=parse_ts("2026-10-18T00:00:00Z"), transport=ctx["transport"])
    raw = ctx["db"].path.read_bytes()
    assert API_KEY.encode() not in raw


def test_webhook_signatures_verify_and_reject_tampering_and_replays():
    body = json.dumps({"event": "work_order.approved", "wo_id": "WO-1"}).encode()
    ts = 1_760_000_000
    sig = integration.sign_webhook(b"s" * 32, ts, body)
    assert integration.verify_webhook(b"s" * 32, ts, body, sig, now_s=ts + 10)
    assert not integration.verify_webhook(b"s" * 32, ts, body + b" ", sig, now_s=ts + 10)
    assert not integration.verify_webhook(b"t" * 32, ts, body, sig, now_s=ts + 10)
    assert not integration.verify_webhook(b"s" * 32, ts, body, sig, now_s=ts + 3600)        # outside the replay window


def test_credential_variables_must_use_the_dedicated_prefix(ctx):
    with pytest.raises(integration.IntegrationError):            # an admin cannot point the connector at the audit key
        integration.register_target(ctx["db"], target_id="x1", kind="odoo_json2", base_url=ODOO, config={"api_key_env": "SENTINELLOOP_AUDIT_KEY"},
                                    actor="ada", role="admin")
    with pytest.raises(integration.IntegrationError):
        integration.register_target(ctx["db"], target_id="x2", kind="webhook", base_url=ODOO + "/hook", config={"secret_env": "PATH"},
                                    actor="ada", role="admin")


def test_every_value_in_the_cmms_description_is_html_escaped(ctx):
    d = ctx["db"]
    registry.update_asset(d, "P-101", {"name": "x"}, actor="admin", reason="noop")
    wo = _approved_order(d, title="<img src=x onerror=alert(1)>")
    asset = registry.get_asset(d, "P-101")
    asset = asset.model_copy(update={"tag": "<script>alert(1)</script>"})
    p = integration.odoo_payload({**wo, "job_type": "<b>j</b>", "explanation": {"why": "<i>w</i>", "due_by": "<u>d</u>"}}, asset, None)
    assert "<script>" not in p["description"] and "<b>j</b>" not in p["description"] and "<i>w</i>" not in p["description"]
    assert "&lt;script&gt;" in p["description"]


def test_a_lost_mapping_adopts_only_the_exactly_marked_request_and_refuses_ambiguity(ctx):
    _target(ctx, mode="draft_requests")
    d, f, tr = ctx["db"], ctx["fake"], ctx["transport"]
    wo = _approved_order(d)
    other = wo["wo_id"] + "0"                                      # a different order whose id extends this one
    f.requests[900] = {"id": 900, "name": "[SentinelLoop] other", "description": f"<p>{integration.marker(other)}</p>"}
    integration.dispatch(d, "odoo", now_ms=parse_ts("2026-10-18T00:00:00Z"), transport=tr)
    ext = integration.items(d, "odoo")[0]["external_id"]
    assert ext != "900" and f.requests[900]["name"] == "[SentinelLoop] other"        # the look-alike was not adopted
    f.requests[901] = {"id": 901, "name": "[SentinelLoop] copy", "description": f"<p>{integration.marker(wo['wo_id'])}</p>"}
    integration._forget_external_id(d, "odoo", wo["wo_id"])
    workorders.reprioritise(d, wo["wo_id"], "P2", None, None, {}, actor="sys", role="system", reason="test")
    integration.dispatch(d, "odoo", now_ms=parse_ts("2026-10-18T01:00:00Z"), transport=tr)
    it = integration.items(d, "odoo")[0]
    assert it["status"] == "dead" and "more than one" in it["last_error"]           # two candidates: a person decides
