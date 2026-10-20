"""Code items from the final handoff audit (tests first): the CMMS description labels the uncalibrated failure
probability, the service layer refuses a free-standing 'maintenance_completed', `serve` emits its JSON request log, and
`serve` finds its default policy from any working directory."""
import logging

import pytest

from sentinelloop.app import admin, health, integration, registry, states
from sentinelloop.app.states import HealthState as H
from test_app_integration import _approved_order, ctx  # noqa: F401  (fixture)
from test_app_rereview_wiring import _latch, _plant
from test_app_foundation import KEY


def test_the_cmms_description_labels_the_failure_probability_as_not_calibrated(ctx):  # noqa: F811
    d = ctx["db"]
    wo = _approved_order(d)
    asset = registry.get_asset(d, "P-101")
    p = integration.odoo_payload({**wo, "explanation": {"p_fail_decision_horizon": 0.42, "decision_horizon_hours": 60}}, asset, None)
    assert "0.42" in p["description"] and "not calibrated" in p["description"]


@pytest.mark.parametrize("role", ["technician", "planner", "reliability_engineer", "admin"])
def test_the_service_layer_refuses_a_free_standing_maintenance_completed(tmp_path, role):
    """Only a qualifying completed work order may record maintenance (workorders.complete); any other caller of the
    service, not just the API route, must be refused."""
    d = _plant(tmp_path)
    _latch(d, "URGENT", None)
    with pytest.raises(states.TransitionError):
        health.clear_latched_risk(d, "P-101", "maintenance_completed", actor="x", role=role, reason="replaced the bearing")
    assert health.asset_state(d, "P-101").latched_risk == "URGENT"


def _serve(tmp_path, monkeypatch, argv_extra=()):
    monkeypatch.setenv("SENTINELLOOP_AUDIT_KEY", KEY.hex())
    db = str(tmp_path / "s.db")
    assert admin.main(["init", "--db", db]) == 0
    seen = {}
    import uvicorn
    monkeypatch.setattr(uvicorn, "run", lambda app, **k: seen.update(app=app, **k))
    return admin.main(["serve", "--db", db, *argv_extra]), seen


def test_serve_emits_the_json_request_log(tmp_path, monkeypatch):
    for h in list(logging.getLogger("sentinelloop").handlers):
        logging.getLogger("sentinelloop").removeHandler(h)
    rc, seen = _serve(tmp_path, monkeypatch)
    assert rc == 0 and "app" in seen
    lg = logging.getLogger("sentinelloop.api")
    assert lg.isEnabledFor(logging.INFO) and (lg.handlers or logging.getLogger("sentinelloop").handlers)


def test_serve_finds_its_default_policy_from_any_working_directory(tmp_path, monkeypatch):
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    rc, seen = _serve(tmp_path, monkeypatch)
    assert rc == 0 and "app" in seen


# -- the RUL model's failure probability is labelled wherever it is shown (final audit, KNOWN_LIMITATIONS E6) --------------
def test_assessment_reasons_label_the_failure_probability_as_not_calibrated():
    thr = states.Thresholds()
    for p in (0.5, 0.15):
        c = states.classify(True, True, True, p, sustained_anomaly=False, thr=thr)
        assert any("P(failure" in r and "not calibrated" in r for r in c.reasons), c.reasons


def test_the_safety_limit_reason_labels_the_failure_probability_as_not_calibrated(tmp_path):
    from test_app_decision import CFG, NOW, assessment, st
    from sentinelloop.app import decision
    d = _plant(tmp_path)
    registry.update_asset(d, "P-101", {"consequence": {"downtime_hours": 8, "cost_per_failure": 50000, "safety_impact": True,
                                                       "environmental_impact": False}}, actor="re1", reason="hazardous fluid")
    a, t = registry.get_asset(d, "P-101"), registry.get_asset_type(d, "centrifugal_pump")
    for state, p in ((H.NORMAL_MONITORING, 0.07), (H.INSPECTION_RECOMMENDED, 0.15)):
        rec = decision.recommend(a, t, assessment(state, 60, 300, 600, p=p), st(state), CFG, now_ms=NOW)
        assert rec is not None and "safety" in rec.explanation["why"], rec
        assert "not calibrated" in rec.explanation["why"], rec.explanation["why"]
