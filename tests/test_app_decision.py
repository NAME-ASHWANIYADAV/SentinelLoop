"""Decision engine: priority, due date and explanation from an assessment (tests written before the code)."""
import json

import pytest

from sentinelloop.app import db as dbmod, decision, health, registry, risk, states, workorders as wo
from sentinelloop.app.states import AssetState, Classification, HealthState as H, Thresholds
from sentinelloop.app.timeutil import HOUR_MS, parse_ts
from test_app_foundation import KEY, pump, pump_type

NOW = parse_ts("2026-10-18T06:00:00Z")
CFG = decision.DecisionConfig()


def assessment(state, lower=None, point=None, upper=None, p=None, horizon=72.0):
    a = {"assessment_id": "A-1", "as_of_ms": NOW, "health_state": state.value, "reasons": ["test"], "rul_lower_hours": lower, "rul_point_hours": point,
         "rul_upper_hours": upper, "interval_level": 0.9 if lower is not None else None, "risk": {}}
    if p is not None:
        a["risk"] = {"p_fail_decision_horizon": p, "decision_horizon_hours": horizon}
    return a


def st(effective):
    return AssetState(effective=effective, latched_risk={"URGENT_REVIEW": "URGENT", "INSPECTION_RECOMMENDED": "INSPECTION"}.get(effective.value, "NONE"),
                      last_health=effective)


@pytest.fixture
def plant(tmp_path):
    d = dbmod.Database(tmp_path / "plant.db", audit_key=KEY, audit_key_id="test")
    d.migrate()
    registry.create_site(d, "site1", "Plant 1", "UTC", actor="admin")
    registry.create_asset_type(d, pump_type(), actor="admin")
    registry.create_asset(d, pump("P-101", criticality="A"), actor="admin")
    registry.create_asset(d, pump("P-102", criticality="C"), actor="admin")
    return d


def test_inverse_cdf_is_the_inverse_of_the_risk_curve():
    for p in (0.01, 0.05, 0.3, 0.5, 0.9):
        t = decision.inverse_cdf(p, lower=20, point=60, upper=150, level=0.9)
        assert risk.p_fail_before(t, 20, 60, 150, 0.9) == pytest.approx(p, abs=1e-9)


def test_urgent_state_gives_p1_repair_due_before_the_acceptable_risk_is_reached(plant):
    a, t = registry.get_asset(plant, "P-101"), registry.get_asset_type(plant, "centrifugal_pump")
    rec = decision.recommend(a, t, assessment(H.URGENT_REVIEW, 30, 80, 200, p=0.35), st(H.URGENT_REVIEW), CFG, now_ms=NOW)
    assert rec.job_type == "repair" and rec.priority_class == "P1"
    t_star = decision.inverse_cdf(CFG.p_accept, 30, 80, 200, 0.9)
    assert rec.due_by_ms == NOW + int(round((t_star - 6.0) * HOUR_MS))          # latest start keeps P(failure before the job ends) <= p_accept
    ex = rec.explanation
    for k in ("state", "reasons", "rul_hours", "p_fail_decision_horizon", "consequence", "expected_loss", "due_by_rule", "job", "policy"):
        assert k in ex, k


def test_no_prediction_states_use_policy_default_due_dates_and_no_invented_probability(plant):
    a, t = registry.get_asset(plant, "P-101"), registry.get_asset_type(plant, "centrifugal_pump")
    rec = decision.recommend(a, t, assessment(H.DATA_QUALITY_FAILURE), st(H.DATA_QUALITY_FAILURE), CFG, now_ms=NOW)
    assert rec.job_type == "inspect" and rec.priority_class == "P2" and rec.priority_score is None
    assert rec.due_by_ms == NOW + CFG.default_due_h["P2"] * HOUR_MS
    c = registry.get_asset(plant, "P-102")
    assert decision.recommend(c, t, assessment(H.DATA_QUALITY_FAILURE), st(H.DATA_QUALITY_FAILURE), CFG, now_ms=NOW).priority_class == "P3"
    assert decision.recommend(c, t, assessment(H.MODEL_OUT_OF_SCOPE), st(H.MODEL_OUT_OF_SCOPE), CFG, now_ms=NOW) is None      # only A assets get a manual review
    rec = decision.recommend(a, t, assessment(H.MODEL_OUT_OF_SCOPE), st(H.MODEL_OUT_OF_SCOPE), CFG, now_ms=NOW)
    assert rec.priority_class == "P3" and "no valid prediction" in rec.explanation["why"]


def test_normal_assets_get_nothing_unless_safety_critical_risk_exceeds_the_safety_limit(plant):
    a, t = registry.get_asset(plant, "P-101"), registry.get_asset_type(plant, "centrifugal_pump")
    assert decision.recommend(a, t, assessment(H.NORMAL_MONITORING, 200, 400, 600, p=0.0), st(H.NORMAL_MONITORING), CFG, now_ms=NOW) is None
    registry.update_asset(plant, "P-101", {"consequence": {"downtime_hours": 8, "cost_per_failure": 50000, "safety_impact": True, "environmental_impact": False}},
                          actor="re1", reason="hazardous fluid")
    a = registry.get_asset(plant, "P-101")
    rec = decision.recommend(a, t, assessment(H.NORMAL_MONITORING, 60, 300, 600, p=0.07), st(H.NORMAL_MONITORING), CFG, now_ms=NOW)
    assert rec is not None and rec.job_type == "inspect" and "safety" in rec.explanation["why"]


def test_higher_consequence_and_risk_give_higher_score_per_technician_hour(plant):
    t = registry.get_asset_type(plant, "centrifugal_pump")
    a_hi, a_lo = registry.get_asset(plant, "P-101"), registry.get_asset(plant, "P-102")
    registry.update_asset(plant, "P-102", {"consequence": {"downtime_hours": 2, "cost_per_failure": 5000, "safety_impact": False, "environmental_impact": False}},
                          actor="re1", reason="spare installed")
    a_lo = registry.get_asset(plant, "P-102")
    r1 = decision.recommend(a_hi, t, assessment(H.INSPECTION_RECOMMENDED, 50, 120, 300, p=0.15), st(H.INSPECTION_RECOMMENDED), CFG, now_ms=NOW)
    r2 = decision.recommend(a_lo, t, assessment(H.INSPECTION_RECOMMENDED, 50, 120, 300, p=0.15), st(H.INSPECTION_RECOMMENDED), CFG, now_ms=NOW)
    assert r1.priority_score > r2.priority_score > 0


def _seed_assessed(d, asset_id, state_value, p=None, lower=None, point=None, upper=None, aid=None, as_of=NOW):
    aid = aid or f"A-{asset_id}"
    with d.tx() as c:
        c.execute("INSERT INTO assessments (assessment_id, asset_id, as_of_ms, created_at, model_id, health_state, reasons_json, data_quality_json, "
                  "applicability_json, rul_lower_hours, rul_point_hours, rul_upper_hours, interval_level, risk_json, inputs_json, policy_json) "
                  "VALUES (?,?,?,?,NULL,?,?,'{}','{}',?,?,?,?,?,'{}','{}')",
                  (aid, asset_id, as_of, "2026-10-18T06:00:00Z", state_value, json.dumps(["seeded"]), lower, point, upper,
                   0.9 if lower is not None else None, json.dumps({"p_fail_decision_horizon": p, "decision_horizon_hours": 72.0} if p is not None else {})))
        health._store_state(c, asset_id, states.advance(AssetState(), Classification(H(state_value), []), Thresholds()), aid)


def test_generate_creates_pending_orders_once_and_escalates_priority(plant):
    _seed_assessed(plant, "P-101", "INSPECTION_RECOMMENDED", p=0.15, lower=50, point=120, upper=300)
    out = decision.generate(plant, CFG, actor="system", now_ms=NOW)
    assert [o["action"] for o in out] == ["created"]
    o = wo.get(plant, out[0]["wo_id"])
    assert o["state"] == "PENDING_APPROVAL" and o["origin"] == "system" and o["priority_class"] == "P2" and o["explanation"]["state"] == "INSPECTION_RECOMMENDED"
    assert health.asset_state(plant, "P-101").approval_pending
    assert [x["action"] for x in decision.generate(plant, CFG, actor="system", now_ms=NOW)] == ["unchanged"]       # no duplicate order
    _seed_assessed(plant, "P-101", "URGENT_REVIEW", p=0.40, lower=10, point=60, upper=200, aid="A-P-101-2", as_of=NOW + 1)
    out = decision.generate(plant, CFG, actor="system", now_ms=NOW + 1)
    assert out[0]["action"] == "escalated" and wo.get(plant, out[0]["wo_id"])["priority_class"] == "P1"


def test_one_bad_asset_never_stops_generation_for_the_others(plant):
    registry.create_asset(plant, pump("P-103", criticality="B"), actor="admin")
    _seed_assessed(plant, "P-101", "INSPECTION_RECOMMENDED", p=0.15, lower=50, point=120, upper=300)
    _seed_assessed(plant, "P-103", "INSPECTION_RECOMMENDED", p=0.15, lower=50, point=120, upper=300)
    first = {o["asset_id"]: o for o in decision.generate(plant, CFG, actor="system", now_ms=NOW)}
    # P-101's order is already being worked on; a new urgent assessment must not crash the run
    w = first["P-101"]["wo_id"]
    for act, kw in (("approve", {"reason": "ok"}), ("schedule", {"data": {"start": "2026-10-19T06:00:00Z", "end": "2026-10-19T08:00:00Z", "technicians": ["t1"]}}),
                    ("start", {})):
        wo.transition(plant, w, act, actor="planner1", role="planner", **kw)
    _seed_assessed(plant, "P-101", "URGENT_REVIEW", p=0.40, lower=10, point=60, upper=200, aid="A-P-101-u", as_of=NOW + 1)
    # P-103's order was rejected by a person: the same assessment must not resurrect it
    wo.transition(plant, first["P-103"]["wo_id"], "reject", actor="re1", role="reliability_engineer", reason="known transient after start-up")
    out = {o["asset_id"]: o for o in decision.generate(plant, CFG, actor="system", now_ms=NOW + 3_600_000)}
    # an urgent condition during lower-priority work gets its own P1 (adversarial review safety-1), not "unchanged"
    assert out["P-101"]["action"] == "created" and out["P-101"]["priority_class"] == "P1"
    assert out["P-103"]["action"] == "already_decided"
