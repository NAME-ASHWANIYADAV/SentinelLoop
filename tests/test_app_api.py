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
