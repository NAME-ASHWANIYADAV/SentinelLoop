"""Residual items from the re-review fixes that cross module owners (tests first): API wiring of the site's non-clearing
jobs and of the reprioritise version check, reserved idempotency keys, a truthful kept-latch reason, the console's count
of linked orders, browser error details, falsy audit anchors, and a decision config whose jobs the site lacks."""
import tomllib

import pytest
from fastapi.testclient import TestClient

from sentinelloop.app import admin, api, auditlog, db as dbmod, decision, health, policy as policymod, registry, security, workorders as wo
from sentinelloop.app.models import JobSpec
from sentinelloop.app.states import HealthState as H
from sentinelloop.app.timeutil import now_ms
from conftest import ROOT
from test_app_foundation import KEY, pump, pump_type
from test_app_rereview_decision import INSPECTED, advance, to_progress

POL = policymod.load(ROOT / "configs" / "platform.yaml")


def _plant(tmp_path, asset_type=None):
    d = dbmod.Database(tmp_path / "w.db", audit_key=KEY, audit_key_id="test")
    d.migrate()
    registry.create_site(d, "site1", "Plant 1", "UTC", actor="admin")
    registry.create_asset_type(d, asset_type or pump_type(), actor="admin")
    registry.create_asset(d, pump("P-101"), actor="admin")
    return d


def _http(d, cfg=None):
    keys = {}
    for uid, role in (("pat", "planner"), ("tom", "technician")):
        security.create_user(d, uid, uid.title(), role, actor="bootstrap")
        keys[role] = {"Authorization": f"Bearer {security.issue_api_key(d, uid, actor='bootstrap')}"}
    return TestClient(api.create_app(d, POL, decision_cfg=cfg, rate_limit=(10000, 1000.0)), raise_server_exceptions=False), keys


def _latch(d, risk, at_ms):
    advance(d, "P-101", H.URGENT_REVIEW if risk == "URGENT" else H.INSPECTION_RECOMMENDED, at_ms=at_ms)


def _in_progress(d, http, keys, job_type, key):
    o = wo.create(d, asset_id="P-101", job_type=job_type, priority_class="P2", title=job_type, origin="manual", actor="pat", role="planner",
                  idempotency_key=key)
    wo.transition(d, o["wo_id"], "submit", actor="pat", role="planner")
    to_progress(d, o["wo_id"])
    return o["wo_id"]


def test_the_api_complete_route_applies_the_sites_non_clearing_jobs(tmp_path):
    """A manual order for the site's renamed data job, completed through the API on a database where the engine has not yet
    run, must not clear a latch: the route passes the served decision config's non-clearing jobs."""
    t = pump_type()
    d = _plant(tmp_path, pump_type(jobs={**t.jobs, "sensor_check": JobSpec(duration_h=1.0, skill="instrument")}))
    cfg = decision.load_config_text("data_job: sensor_check\n")
    http, keys = _http(d, cfg)
    _latch(d, "URGENT", now_ms() - 60_000)
    w = _in_progress(d, http, keys, "sensor_check", "k1")
    r = http.post(f"/api/v1/work-orders/{w}/complete", json={"outcome": INSPECTED}, headers=keys["technician"])
    assert r.status_code == 200, r.text
    assert "latch_kept" in r.json()["outcome"]["flags"] and health.asset_state(d, "P-101").latched_risk == "URGENT"


def test_the_reprioritise_route_refuses_a_stale_version(tmp_path):
    d = _plant(tmp_path)
    http, keys = _http(d)
    o = wo.create(d, asset_id="P-101", job_type="inspect", priority_class="P3", title="look", origin="manual", actor="pat", role="planner",
                  idempotency_key="k2")
    body = {"priority_class": "P2", "reason": "bring forward", "expected_version": o["version"] + 5}
    assert http.post(f"/api/v1/work-orders/{o['wo_id']}/reprioritise", json=body, headers=keys["planner"]).status_code == 409
    body["expected_version"] = o["version"]
    assert http.post(f"/api/v1/work-orders/{o['wo_id']}/reprioritise", json=body, headers=keys["planner"]).status_code == 200


@pytest.mark.parametrize("key", ["rec:A-123:inspect", "reactivate:WO-000001:29000000", "apply:R-1:WO-000001"])
def test_clients_cannot_use_the_engines_reserved_idempotency_keys(tmp_path, key):
    """The engine's own keys (recommendations, deferral reactivation, schedule application) are reserved: a client that
    pre-claimed one could make the engine's later action a silent replay."""
    d = _plant(tmp_path)
    http, keys = _http(d)
    r = http.post("/api/v1/work-orders", json={"asset_id": "P-101", "job_type": "inspect", "priority_class": "P3", "title": "x"},
                  headers={**keys["planner"], "Idempotency-Key": key})
    assert r.status_code == 400 and "reserved" in r.json()["error"]
    o = wo.create(d, asset_id="P-101", job_type="inspect", priority_class="P3", title="look", origin="manual", actor="pat", role="planner",
                  idempotency_key="k3")
    r = http.post(f"/api/v1/work-orders/{o['wo_id']}/transitions", json={"action": "submit"}, headers={**keys["planner"], "Idempotency-Key": key})
    assert r.status_code == 400 and "reserved" in r.json()["error"]
    r = http.post(f"/api/v1/work-orders/{o['wo_id']}/complete", json={"outcome": INSPECTED}, headers={**keys["technician"], "Idempotency-Key": key})
    assert r.status_code == 400 and "reserved" in r.json()["error"]


def test_the_kept_latch_reason_does_not_claim_the_order_predates_the_condition_itself(tmp_path):
    """wind-eval-migrations-09: after migration 0007 the recorded start may be a backfilled upper bound, so the reason must
    speak of the recorded start, not of when the condition began."""
    d = _plant(tmp_path)
    http, keys = _http(d)
    w = _in_progress(d, http, keys, "inspect", "k4")
    _latch(d, "URGENT", now_ms() + 1_000)
    done = wo.complete(d, w, actor="tom", role="technician", outcome=INSPECTED)
    reasons = " ".join(health.asset_state(d, "P-101").notes)
    assert "latch_kept" in done["outcome"]["flags"]
    assert "recorded start" in reasons and "before the latched condition began" not in reasons


def test_the_console_counts_linked_orders_after_generating():
    # read, never import: importing the console module runs the Streamlit app and leaves script-run state behind
    src = (ROOT / "src" / "sentinelloop" / "console" / "app.py").read_text(encoding="utf-8")
    assert '"linked"' in src and "linked to" in src


def test_the_console_never_shows_error_details_in_the_browser():
    cfg = tomllib.loads((ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8"))
    assert cfg["client"]["showErrorDetails"] == "none"


@pytest.mark.parametrize("anchor", [{}, [], {"seq": 1}, {"hash": "ab"}])
def test_a_malformed_audit_anchor_is_refused_not_treated_as_absent(tmp_path, anchor):
    d = _plant(tmp_path)
    with d.connect() as c, pytest.raises(ValueError):
        auditlog.verify(c, KEY, anchor=anchor)


def test_serve_refuses_a_decision_config_naming_a_job_the_sites_asset_types_lack(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("SENTINELLOOP_AUDIT_KEY", KEY.hex())
    d = _plant(tmp_path)
    cfgfile = tmp_path / "decision.yaml"
    cfgfile.write_text("inspection_job: survey\n", encoding="utf-8")
    import uvicorn
    monkeypatch.setattr(uvicorn, "run", lambda *a, **k: (_ for _ in ()).throw(AssertionError("server started")))
    rc = admin.main(["serve", "--db", str(d.path), "--decision-config", str(cfgfile)])
    assert rc != 0 and "survey" in capsys.readouterr().err
