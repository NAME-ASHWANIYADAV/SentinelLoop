"""The integration scenario against a REAL Odoo Community sandbox (opt-in; see sandbox/odoo/README.md).

Skipped unless SENTINELLOOP_ODOO_URL, SENTINELLOOP_ODOO_KEY and SENTINELLOOP_ODOO_DB are set. The connector itself
only searches, creates and writes maintenance requests; this test additionally uses raw JSON-2 calls to seed one
equipment record and to read back what the connector wrote.
"""
import os
import uuid

import httpx
import pytest

from sentinelloop.app import db as dbmod, integration, registry, workorders
from sentinelloop.app.timeutil import parse_ts
from test_app_foundation import KEY, pump, pump_type

URL, APIKEY, DB = (os.environ.get(k) for k in ("SENTINELLOOP_ODOO_URL", "SENTINELLOOP_ODOO_KEY", "SENTINELLOOP_ODOO_DB"))
pytestmark = pytest.mark.skipif(not (URL and APIKEY and DB), reason="Odoo sandbox not configured (sandbox/odoo/README.md)")


def raw(model, method, body):
    r = httpx.post(f"{URL}/json/2/{model}/{method}", json=body, timeout=30,
                   headers={"Authorization": f"bearer {APIKEY}", "X-Odoo-Database": DB, "Content-Type": "application/json"})
    r.raise_for_status()
    return r.json()


def test_connector_against_real_odoo(tmp_path, monkeypatch):
    run = uuid.uuid4().hex[:8]
    serial = f"SL-{run}"
    eq_id = raw("maintenance.equipment", "create", {"vals_list": [{"name": f"Sandbox pump {run}", "serial_no": serial}]})[0]
    monkeypatch.setenv("SENTINELLOOP_INTEGRATION_HOSTS", "localhost")
    monkeypatch.setenv("SENTINELLOOP_CRED_SANDBOX", APIKEY)
    d = dbmod.Database(tmp_path / "s.db", audit_key=KEY, audit_key_id="test")
    d.migrate()
    registry.create_site(d, "site1", "Plant 1", "UTC", actor="admin")
    registry.create_asset_type(d, pump_type(), actor="admin")
    registry.create_asset(d, pump("P-101"), actor="admin")
    registry.update_asset(d, "P-101", {"config": {"cmms_equipment_ref": serial}}, actor="admin", reason="sandbox mapping")
    integration.register_target(d, "odoo", "odoo_json2", URL, {"database": DB, "api_key_env": "SENTINELLOOP_CRED_SANDBOX"}, actor="ada", role="admin")

    o = workorders.create(d, asset_id="P-101", job_type="inspect", priority_class="P1", title=f"Inspect P-101 ({run})", origin="system",
                          actor="sys", role="system", idempotency_key=f"sb-{run}")
    workorders.transition(d, o["wo_id"], "submit", actor="pat", role="planner")
    workorders.transition(d, o["wo_id"], "approve", actor="pat", role="planner")
    now = parse_ts("2026-10-18T00:00:00Z")

    integration.dispatch(d, "odoo", now_ms=now)                                # shadow: nothing written
    assert raw("maintenance.request", "search_read", {"domain": [["description", "ilike", integration.marker(o["wo_id"])]], "fields": ["id"]}) == []

    integration.set_mode(d, "odoo", "draft_requests", actor="ada", role="admin", reason="sandbox test")
    r = integration.dispatch(d, "odoo", now_ms=now + 1000)
    assert r["sent"] == 1, r
    ext = integration.items(d, "odoo")[0]["external_id"]
    rec = raw("maintenance.request", "read", {"ids": [int(ext)], "fields": ["name", "priority", "equipment_id", "maintenance_type", "description"]})[0]
    assert rec["name"].startswith("[SentinelLoop]") and rec["priority"] == "3" and rec["equipment_id"][0] == eq_id
    assert rec["maintenance_type"] == "preventive" and integration.marker(o["wo_id"]) in rec["description"]

    workorders.transition(d, o["wo_id"], "schedule", actor="pat", role="planner",
                          data={"start": "2026-10-19T08:00:00Z", "end": "2026-10-19T12:00:00Z", "technicians": ["T1"]})
    integration._forget_external_id(d, "odoo", o["wo_id"])                    # lost mapping: must not create a duplicate
    integration.dispatch(d, "odoo", now_ms=now + 2000)
    found = raw("maintenance.request", "search_read", {"domain": [["description", "ilike", integration.marker(o["wo_id"])]],
                                                       "fields": ["id", "schedule_date"]})
    assert len(found) == 1 and found[0]["schedule_date"].startswith("2026-10-19 08:00")

    monkeypatch.setenv("SENTINELLOOP_CRED_SANDBOX", "wrong-key")                          # a rejected credential becomes a dead letter
    workorders.reprioritise(d, o["wo_id"], "P2", None, None, {}, actor="sys", role="system", reason="sandbox")
    integration.dispatch(d, "odoo", now_ms=now + 3000)
    it = integration.items(d, "odoo")[0]
    assert it["status"] == "dead" and "401" in it["last_error"] and "Traceback" not in it["last_error"]
