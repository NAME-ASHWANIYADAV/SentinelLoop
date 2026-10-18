"""REST API: authentication, roles, idempotency, error mapping, rate limiting, size limits (tests written before the code)."""
import pytest
from fastapi.testclient import TestClient

from sentinelloop.app import api, db as dbmod, policy as policymod, registry, security
from conftest import ROOT
from test_app_foundation import KEY, pump, pump_type


@pytest.fixture
def ctx(tmp_path):
    d = dbmod.Database(tmp_path / "plant.db", audit_key=KEY, audit_key_id="test")
    d.migrate()
    registry.create_site(d, "site1", "Plant 1", "UTC", actor="admin")
    registry.create_asset_type(d, pump_type(), actor="admin")
    registry.create_asset(d, pump("P-101"), actor="admin")
    keys = {}
    for uid, role in (("ada", "admin"), ("pat", "planner"), ("rea", "reliability_engineer"), ("tom", "technician"), ("vic", "viewer"), ("svc", "integration")):
        security.create_user(d, uid, uid.title(), role, actor="bootstrap")
        keys[role] = security.issue_api_key(d, uid, actor="bootstrap")
    app = api.create_app(d, policymod.load(ROOT / "configs" / "platform.yaml"), rate_limit=(1000, 1000.0))
    return {"db": d, "client": TestClient(app), "keys": keys, "app": app}


def H(ctx, role, **extra):
    return {"Authorization": f"Bearer {ctx['keys'][role]}", **extra}


def test_health_is_public_and_ready_reports_schema_and_key_status(ctx):
    c = ctx["client"]
    assert c.get("/api/v1/health").json()["status"] == "ok"
    r = c.get("/api/v1/ready").json()
    assert r["database"] == "ok" and r["schema_version"] >= 4 and r["audit_key"] == "configured"


def test_missing_or_wrong_credentials_are_401_and_api_keys_are_stored_hashed(ctx):
    c = ctx["client"]
    assert c.get("/api/v1/assets").status_code == 401
    assert c.get("/api/v1/assets", headers={"Authorization": "Bearer slk_not-a-key"}).status_code == 401
    with ctx["db"].connect() as conn:
        stored = [r[0] for r in conn.execute("SELECT api_key_hash FROM users")]
    assert all(ctx["keys"][k] not in stored for k in ctx["keys"])
    assert c.get("/api/v1/assets", headers=H(ctx, "viewer")).status_code == 200


def test_roles_are_enforced_with_403(ctx):
    c = ctx["client"]
    body = {"asset_id": "P-101", "job_type": "inspect", "priority_class": "P2", "title": "Inspect P-101"}
    assert c.post("/api/v1/work-orders", json=body, headers=H(ctx, "viewer", **{"Idempotency-Key": "a"})).status_code == 403
    r = c.post("/api/v1/work-orders", json=body, headers=H(ctx, "planner", **{"Idempotency-Key": "a"}))
    assert r.status_code == 201
    wo_id = r.json()["wo_id"]
    assert c.post(f"/api/v1/work-orders/{wo_id}/transitions", json={"action": "submit"}, headers=H(ctx, "planner")).status_code == 200
    r = c.post(f"/api/v1/work-orders/{wo_id}/transitions", json={"action": "approve"}, headers=H(ctx, "technician"))
    assert r.status_code == 403 and "may not" in r.json()["error"]
    assert c.get("/api/v1/audit/verify", headers=H(ctx, "planner")).status_code == 403
    v = c.get("/api/v1/audit/verify", headers=H(ctx, "admin")).json()
    assert v["valid"] is True and v["n"] > 0


def test_work_order_creation_requires_and_honours_idempotency_keys(ctx):
    c = ctx["client"]
    body = {"asset_id": "P-101", "job_type": "inspect", "priority_class": "P2", "title": "Inspect P-101"}
    assert c.post("/api/v1/work-orders", json=body, headers=H(ctx, "planner")).status_code == 400
    a = c.post("/api/v1/work-orders", json=body, headers=H(ctx, "planner", **{"Idempotency-Key": "k-1"}))
    b = c.post("/api/v1/work-orders", json=body, headers=H(ctx, "planner", **{"Idempotency-Key": "k-1"}))
    assert a.json()["wo_id"] == b.json()["wo_id"]
    conflict = c.post("/api/v1/work-orders", json={**body, "title": "other"}, headers=H(ctx, "planner", **{"Idempotency-Key": "k-1"}))
    assert conflict.status_code == 409


def test_state_conflicts_and_stale_versions_are_409(ctx):
    c = ctx["client"]
    wo_id = c.post("/api/v1/work-orders", json={"asset_id": "P-101", "job_type": "inspect", "priority_class": "P2", "title": "x"},
                   headers=H(ctx, "planner", **{"Idempotency-Key": "k-2"})).json()["wo_id"]
    assert c.post(f"/api/v1/work-orders/{wo_id}/transitions", json={"action": "start"}, headers=H(ctx, "planner")).status_code == 409
    assert c.post(f"/api/v1/work-orders/{wo_id}/transitions", json={"action": "submit", "expected_version": 99}, headers=H(ctx, "planner")).status_code == 409


def test_ingest_accepts_contract_rows_for_integration_users_only(ctx):
    c = ctx["client"]
    rows = [{"asset": "P-101", "timestamp": "2026-10-17T10:00:00Z", "signal": "bearing_temp", "value": 61.0, "unit": "degC"},
            {"asset": "P-101", "timestamp": "2026-10-17T10:00:00Z", "signal": "bearing_temp", "value": 61.0, "unit": "degF"}]
    assert c.post("/api/v1/ingest/readings", json={"records": rows, "source": "historian"}, headers=H(ctx, "viewer")).status_code == 403
    r = c.post("/api/v1/ingest/readings", json={"records": rows, "source": "historian"}, headers=H(ctx, "integration"))
    assert r.status_code == 200 and r.json()["rows_accepted"] == 1 and r.json()["errors"][0]["reason"] == "unit_mismatch"


def test_validation_errors_are_422_without_internal_details(ctx):
    c = ctx["client"]
    r = c.post("/api/v1/work-orders", json={"asset_id": "P-101"}, headers=H(ctx, "planner", **{"Idempotency-Key": "z"}))
    assert r.status_code == 422 and "request_id" in r.json()
    r = c.post("/api/v1/work-orders", json={"asset_id": "NOPE", "job_type": "inspect", "priority_class": "P2", "title": "x"},
               headers=H(ctx, "planner", **{"Idempotency-Key": "y"}))
    assert r.status_code in (404, 422) and "Traceback" not in r.text


def test_rate_limit_returns_429_with_retry_after(tmp_path):
    d = dbmod.Database(tmp_path / "rl.db", audit_key=KEY, audit_key_id="test")
    d.migrate()
    security.create_user(d, "vic", "Vic", "viewer", actor="bootstrap")
    key = security.issue_api_key(d, "vic", actor="bootstrap")
    c = TestClient(api.create_app(d, policymod.load(ROOT / "configs" / "platform.yaml"), rate_limit=(3, 0.001)))
    codes = [c.get("/api/v1/assets", headers={"Authorization": f"Bearer {key}"}).status_code for _ in range(5)]
    assert codes[:3] == [200, 200, 200] and codes[3] == 429


def test_oversized_bodies_are_rejected(ctx):
    big = "x" * (11 * 1024 * 1024)
    r = ctx["client"].post("/api/v1/ingest/csv?source=x", content=big, headers=H(ctx, "integration", **{"Content-Type": "text/csv"}))
    assert r.status_code == 413


def test_every_response_carries_a_request_id(ctx):
    r = ctx["client"].get("/api/v1/health", headers={"X-Request-ID": "abc-123"})
    assert r.headers["X-Request-ID"] == "abc-123"
    assert ctx["client"].get("/api/v1/health").headers["X-Request-ID"]


def test_password_hashing_uses_scrypt_and_rejects_short_passwords(ctx):
    with pytest.raises(security.SecurityError):
        security.set_password(ctx["db"], "tom", "short", actor="ada")
    security.set_password(ctx["db"], "tom", "a-long-enough-passphrase", actor="ada")
    assert security.verify_password(ctx["db"], "tom", "a-long-enough-passphrase")["role"] == "technician"
    assert security.verify_password(ctx["db"], "tom", "wrong-passphrase-xx") is None
    with ctx["db"].connect() as c:
        assert c.execute("SELECT password_hash FROM users WHERE user_id = 'tom'").fetchone()[0].startswith("scrypt$")


def test_audit_history_of_sensitive_entities_needs_audit_permission(ctx):
    c = ctx["client"]
    assert c.get("/api/v1/audit/user/tom", headers=H(ctx, "viewer")).status_code == 403
    assert c.get("/api/v1/audit/asset/P-101", headers=H(ctx, "viewer")).status_code == 200
    assert c.get("/api/v1/audit/user/tom", headers=H(ctx, "admin")).status_code == 200


def test_chunked_bodies_without_content_length_are_capped(ctx, tmp_path):
    from sentinelloop.app import api as apimod
    small = TestClient(apimod.create_app(ctx["db"], policymod.load(ROOT / "configs" / "platform.yaml"), rate_limit=(1000, 1000.0), max_body_bytes=1000))
    def gen():
        for _ in range(50):
            yield b"x" * 100
    r = small.post("/api/v1/ingest/csv?source=x", content=gen(), headers=H(ctx, "integration", **{"Content-Type": "text/csv"}))
    assert r.status_code == 413
    rows = [{"asset": "P-101", "timestamp": "2026-10-17T10:00:00Z", "signal": "bearing_temp", "value": 61.0, "unit": "degC"}] * 40
    payload = __import__("json").dumps({"records": rows, "source": "historian"}).encode()
    def gen_json():
        for i in range(0, len(payload), 100):
            yield payload[i:i + 100]
    r = small.post("/api/v1/ingest/readings", content=gen_json(), headers=H(ctx, "integration", **{"Content-Type": "application/json"}))
    assert r.status_code == 413                 # JSON endpoints are capped while streaming too, not only the CSV upload


def test_rate_limit_is_per_user_not_per_credential_string_and_buckets_are_bounded(tmp_path):
    lim = security.RateLimiter(capacity=2, refill_per_s=0.0001, max_buckets=3)
    for k in ("a", "b", "c", "d", "e"):
        lim.allow(k)
    assert len(lim._b) <= 3
    d = dbmod.Database(tmp_path / "rl2.db", audit_key=KEY, audit_key_id="test")
    d.migrate()
    security.create_user(d, "vic", "Vic", "viewer", actor="bootstrap")
    key = security.issue_api_key(d, "vic", actor="bootstrap")
    c = TestClient(api.create_app(d, policymod.load(ROOT / "configs" / "platform.yaml"), rate_limit=(2, 0.0001)))
    codes = [c.get("/api/v1/assets", headers=hdr).status_code for hdr in ({"Authorization": f"Bearer {key}"}, {"X-API-Key": key}, {"Authorization": f"bearer  {key}"})]
    assert codes[2] == 429                      # the same user cannot dodge the limit by changing how the key is presented


def test_csv_export_neutralises_spreadsheet_formulas(ctx):
    c = ctx["client"]
    c.post("/api/v1/work-orders", json={"asset_id": "P-101", "job_type": "inspect", "priority_class": "P2", "title": "=HYPERLINK(\"http://x\")"},
           headers=H(ctx, "planner", **{"Idempotency-Key": "csv-1"}))
    text = c.get("/api/v1/export/work-orders.csv", headers=H(ctx, "viewer")).text
    assert "'=HYPERLINK" in text and ",=HYPERLINK" not in text


def test_every_route_except_health_and_docs_requires_credentials(ctx):
    """Guards against a new endpoint shipping without authentication."""
    open_paths = {"/api/v1/health", "/api/v1/ready", "/api/v1/docs", "/api/v1/openapi.json", "/api/v1/docs/oauth2-redirect"}
    c = ctx["client"]
    checked = 0
    for r in ctx["app"].routes:
        path = getattr(r, "path", "")
        if not path.startswith("/api/v1") or path in open_paths:
            continue
        url = path.replace("{entity}", "asset").replace("{entity_id}", "P-101").replace("{asset_id}", "P-101").replace("{wo_id}", "WO-x") \
                  .replace("{run_id}", "SR-x").replace("{model_id}", "m").replace("{batch_id}", "b").replace("{site_id}", "site1") \
                  .replace("{tech_id}", "T1").replace("{part_id}", "K1").replace("{user_id}", "vic").replace("{target_id}", "odoo")
        for m in r.methods - {"HEAD", "OPTIONS"}:
            resp = c.request(m, url, json={})
            assert resp.status_code == 401, (m, path, resp.status_code)
            checked += 1
    assert checked >= 30


def test_resources_can_be_managed_by_planners_only(ctx):
    c = ctx["client"]
    body = {"tech_id": "T1", "display_name": "Tech One", "skills": ["mech"]}
    assert c.post("/api/v1/sites/site1/technicians", json=body, headers=H(ctx, "viewer")).status_code == 403
    assert c.post("/api/v1/sites/site1/technicians", json=body, headers=H(ctx, "planner")).status_code == 200
    r = c.put("/api/v1/technicians/T1/shifts", json={"shifts": [["2026-10-20T06:00:00Z", "2026-10-20T14:00:00Z"]]}, headers=H(ctx, "planner"))
    assert r.status_code == 200
    assert c.get("/api/v1/sites/site1/technicians", headers=H(ctx, "viewer")).status_code == 403     # names and shifts are personal data
    techs = c.get("/api/v1/sites/site1/technicians", headers=H(ctx, "planner")).json()
    assert techs[0]["tech_id"] == "T1" and len(techs[0]["shifts"]) == 1
    assert c.post("/api/v1/sites/site1/parts", json={"part_id": "K1", "name": "Kit", "on_hand": 2, "lead_time_h": 72}, headers=H(ctx, "planner")).status_code == 200
    assert c.post("/api/v1/sites/site1/parts/K1/deliveries", json={"qty": 3, "eta": "2026-10-25T00:00:00Z", "reference": "PO-1"},
                  headers=H(ctx, "planner")).status_code == 200
    parts = c.get("/api/v1/sites/site1/parts", headers=H(ctx, "viewer")).json()
    assert parts[0]["on_hand"] == 2 and parts[0]["deliveries"]


def test_user_administration_is_admin_only_and_keys_are_shown_once(ctx):
    c = ctx["client"]
    assert c.post("/api/v1/users", json={"user_id": "nina", "display_name": "Nina", "role": "planner"}, headers=H(ctx, "planner")).status_code == 403
    assert c.post("/api/v1/users", json={"user_id": "nina", "display_name": "Nina", "role": "planner"}, headers=H(ctx, "admin")).status_code == 201
    k = c.post("/api/v1/users/nina/api-key", headers=H(ctx, "admin")).json()["api_key"]
    assert c.get("/api/v1/me", headers={"Authorization": f"Bearer {k}"}).json()["user_id"] == "nina"
    users = c.get("/api/v1/users", headers=H(ctx, "admin")).json()
    assert all("api_key" not in u and "api_key_hash" not in u and "password_hash" not in u for u in users)
    assert c.post("/api/v1/users/nina/deactivate", json={"reason": "left the team"}, headers=H(ctx, "admin")).status_code == 200
    assert c.get("/api/v1/me", headers={"Authorization": f"Bearer {k}"}).status_code == 401


def test_commissioning_endpoint_is_restricted_to_reliability_roles(ctx):
    c = ctx["client"]
    body = {"model_id": "wind-nbm-unknown", "start": "2026-10-01T00:00:00Z", "end": "2026-10-05T00:00:00Z", "reason": "declared healthy"}
    assert c.post("/api/v1/assets/P-101/baseline", json=body, headers=H(ctx, "technician")).status_code == 403
    r = c.post("/api/v1/assets/P-101/baseline", json=body, headers=H(ctx, "reliability_engineer"))
    assert r.status_code == 404 and "unknown model" in r.json()["error"]


def test_integration_targets_through_the_api_start_in_shadow_and_only_admins_manage_them(ctx, monkeypatch):
    monkeypatch.setenv("SENTINELLOOP_INTEGRATION_HOSTS", "localhost")
    c = ctx["client"]
    body = {"target_id": "odoo", "kind": "odoo_json2", "base_url": "http://localhost:8069", "config": {"api_key_env": "SENTINELLOOP_CRED_ODOO", "database": "x"}}
    assert c.post("/api/v1/integrations", json=body, headers=H(ctx, "planner")).status_code == 403
    r = c.post("/api/v1/integrations", json=body, headers=H(ctx, "admin"))
    assert r.status_code == 201 and r.json()["mode"] == "shadow"
    assert c.post("/api/v1/integrations", json={**body, "target_id": "bad", "config": {"api_key": "inline-secret"}},
                  headers=H(ctx, "admin")).status_code == 422
    assert c.post("/api/v1/integrations/odoo/dispatch", headers=H(ctx, "viewer")).status_code == 403
    d = c.post("/api/v1/integrations/odoo/dispatch", headers=H(ctx, "integration")).json()
    assert d["mode"] == "shadow" and d["sent"] == 0
    assert c.get("/api/v1/integrations/odoo/items", headers=H(ctx, "planner")).status_code == 200
    assert c.post("/api/v1/integrations/odoo/mode", json={"mode": "draft_requests", "reason": "go"}, headers=H(ctx, "integration")).status_code == 403
