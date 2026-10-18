"""Regression tests for the defects confirmed by the Phase 9 adversarial review (product/ADVERSARIAL_REVIEW.md).

Each test names the finding it covers. They were written before the fixes and failed against commit b3248ec.
"""
import json

import pytest
from fastapi.testclient import TestClient

from sentinelloop.app import api, db as dbmod, decision, health, ingest, policy as policymod, registry, security, states, workorders as wo
from sentinelloop.app.adapters import wind
from sentinelloop.app.states import AssetState, Classification, HealthState as H, Thresholds
from sentinelloop.app.timeutil import DAY_MS, HOUR_MS, iso, now_ms, parse_ts
from conftest import ROOT
from test_app_foundation import KEY, pump, pump_type

POL = policymod.load(ROOT / "configs" / "platform.yaml")
SCHED = {"start": "2026-10-20T06:00:00Z", "end": "2026-10-20T12:00:00Z", "technicians": ["tech1"]}
INSPECTED = {"findings_code": "no_fault_found", "failure_confirmed": "no", "actions_taken": "inspected, nothing found", "downtime_hours": 1}


@pytest.fixture
def plant(tmp_path):
    d = dbmod.Database(tmp_path / "r.db", audit_key=KEY, audit_key_id="test")
    d.migrate()
    registry.create_site(d, "site1", "Plant 1", "UTC", actor="admin")
    from sentinelloop.app.models import JobSpec
    t = pump_type()
    registry.create_asset_type(d, pump_type(jobs={**t.jobs, "instrument_check": JobSpec(duration_h=1.0, skill="instrument")}), actor="admin")
    for t in ("P-101", "P-102"):
        registry.create_asset(d, pump(t), actor="admin")
    return d


def latch(d, asset="P-101", state=H.URGENT_REVIEW, at_ms=None):
    s = states.advance(AssetState(), Classification(state, ["test latch"]), Thresholds(), now_ms=at_ms)
    with d.tx() as c:
        health._store_state(c, asset, s, None)
    return s


def order(d, key, job="inspect", pc="P1", start=True):
    o = wo.create(d, asset_id="P-101", job_type=job, priority_class=pc, title=f"{job} P-101", origin="system", actor="sys", role="system",
                  idempotency_key=key)
    wo.transition(d, o["wo_id"], "submit", actor="sys", role="system")
    wo.transition(d, o["wo_id"], "approve", actor="pat", role="planner")
    wo.transition(d, o["wo_id"], "schedule", actor="pat", role="planner", data=SCHED)
    if start:
        wo.transition(d, o["wo_id"], "start", actor="tom", role="technician")
    return o["wo_id"]


# -- latch integrity (technician-1, safety-1, safety-2, technician-2, security-1, om_manager-5) --------------------------
def test_a_not_inspected_completion_keeps_the_urgent_latch(plant):
    latch(plant)
    w = order(plant, "a1")
    out = wo.complete(plant, w, actor="tom", role="technician",
                      outcome={"findings_code": "not_inspected", "failure_confirmed": "unknown", "actions_taken": "could not climb: wind above limit",
                               "downtime_hours": 0})
    s = health.asset_state(plant, "P-101")
    assert s.latched_risk == "URGENT" and s.effective == H.URGENT_REVIEW
    assert "latch_kept" in out["outcome"]["flags"]


def test_an_order_created_before_the_latch_does_not_clear_it(plant):
    w = order(plant, "a2", pc="P2")                                  # an inspection already under way ...
    latch(plant, at_ms=now_ms() + 1000)                              # ... then the condition becomes urgent
    wo.complete(plant, w, actor="tom", role="technician", outcome=INSPECTED)
    assert health.asset_state(plant, "P-101").latched_risk == "URGENT"


def test_an_instrument_check_does_not_clear_an_equipment_latch(plant):
    latch(plant)
    w = order(plant, "a3", job="instrument_check", pc="P2")
    wo.complete(plant, w, actor="tom", role="technician", outcome={**INSPECTED, "actions_taken": "sensor recalibrated"})
    assert health.asset_state(plant, "P-101").latched_risk == "URGENT"


def test_a_machine_credential_completion_does_not_clear_a_latch(plant):
    latch(plant)
    w = order(plant, "a4")
    wo.complete(plant, w, actor="svc", role="integration", outcome=INSPECTED)
    assert health.asset_state(plant, "P-101").latched_risk == "URGENT"


def test_a_relevant_inspected_completion_clears_and_awaits_reassessment(plant):
    latch(plant)
    w = order(plant, "a5")
    wo.complete(plant, w, actor="tom", role="technician", outcome=INSPECTED)
    s = health.asset_state(plant, "P-101")
    assert s.latched_risk == "NONE" and s.labels() == ["AWAITING_ASSESSMENT"]          # not shown as healthy until reassessed


def test_maintenance_cannot_be_recorded_through_clear_risk(plant):
    latch(plant)
    security.create_user(plant, "tom", "Tom", "technician", actor="b")
    security.create_user(plant, "rea", "Rea", "reliability_engineer", actor="b")
    k_t, k_r = security.issue_api_key(plant, "tom", actor="b"), security.issue_api_key(plant, "rea", actor="b")
    c = TestClient(api.create_app(plant, POL, rate_limit=(1000, 1000.0)))
    r = c.post("/api/v1/assets/P-101/clear-risk", json={"event": "maintenance_completed", "reason": "x"}, headers={"Authorization": f"Bearer {k_t}"})
    assert r.status_code == 403
    r = c.post("/api/v1/assets/P-101/clear-risk", json={"event": "maintenance_completed", "reason": "done"}, headers={"Authorization": f"Bearer {k_r}"})
    assert r.status_code == 422 and "complet" in r.json()["error"]
    assert health.asset_state(plant, "P-101").latched_risk == "URGENT"
    r = c.post("/api/v1/assets/P-101/clear-risk", json={"event": "dismissed", "reason": "sensor fault confirmed by vibration route"},
               headers={"Authorization": f"Bearer {k_r}"})
    assert r.status_code == 200 and health.asset_state(plant, "P-101").latched_risk == "NONE"


def test_an_urgent_condition_during_lower_priority_work_raises_its_own_p1(plant):
    w = order(plant, "a6", pc="P2")
    a = _assessment(plant, "URGENT_REVIEW")
    latch(plant)
    out = decision.generate(plant, decision.DecisionConfig(), actor="sys")
    mine = [x for x in out if x["asset_id"] == "P-101"]
    assert mine and mine[0]["action"] == "created" and mine[0]["priority_class"] == "P1", out
    assert w != mine[0]["wo_id"]


def _assessment(d, state, as_of=None):
    """Store a minimal applied assessment record (the decision engine reads the latest one)."""
    import uuid
    aid = f"A-{uuid.uuid4().hex[:16]}"
    with d.tx() as c:
        c.execute("INSERT INTO assessments (assessment_id, asset_id, as_of_ms, created_at, model_id, health_state, reasons_json, data_quality_json, "
                  "applicability_json, risk_json, top_deviations_json, inputs_json, policy_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  (aid, "P-101", as_of or now_ms(), iso(now_ms()), None, state, json.dumps(["test"]), "{}", "{}", "{}", "[]", "{}", "{}"))
    return aid


# -- assessment instants (security-2, safety-3) --------------------------------------------------------------------
def test_future_assessment_instants_are_refused(plant):
    with pytest.raises(health.AssessmentError):
        health.assess(plant, "P-101", POL, as_of_ms=parse_ts("2099-01-01T00:00:00Z"))


def test_back_dated_assessments_are_stored_but_never_move_the_live_state(plant):
    t = now_ms()
    a1 = health.assess(plant, "P-101", POL, as_of_ms=t)                     # no data at all: a data-quality failure now
    assert health.asset_state(plant, "P-101").effective == H.DATA_QUALITY_FAILURE
    recs = [{"asset": "P-101", "timestamp": iso(t - 5 * DAY_MS + k * 600_000), "signal": s, "value": v, "unit": u}
            for k in range(40) for s, v, u in (("bearing_temp", 60.0 + k * 0.01, "degC"), ("vibration_rms", 2.0 + k * 0.001, "mm/s"))]
    ingest.ingest_records(plant, recs, source="t", actor="svc")
    for back in (t - 5 * DAY_MS + 30 * 600_000, t - 5 * DAY_MS + 39 * 600_000):
        b = health.assess(plant, "P-101", POL, as_of_ms=back)
        assert b["applied_to_state"] is False
    assert health.asset_state(plant, "P-101").effective == H.DATA_QUALITY_FAILURE
    assert health.latest_assessment(plant, "P-101")["assessment_id"] == a1["assessment_id"]


# -- deferral and rejection (om_manager-6, technician-3, safety-6, technician-4) ------------------------------------
def test_a_deferred_order_returns_for_approval_when_its_date_passes(plant):
    o = wo.create(plant, asset_id="P-101", job_type="inspect", priority_class="P2", title="t", origin="system", actor="s", role="system",
                  idempotency_key="d1")
    wo.transition(plant, o["wo_id"], "submit", actor="s", role="system")
    wo.transition(plant, o["wo_id"], "defer", actor="pat", role="planner", reason="crane booked", data={"until": iso(now_ms() + DAY_MS)})
    decision.generate(plant, decision.DecisionConfig(), actor="sys", now_ms=now_ms())
    assert wo.get(plant, o["wo_id"])["state"] == "DEFERRED"
    out = decision.generate(plant, decision.DecisionConfig(), actor="sys", now_ms=now_ms() + 2 * DAY_MS)
    assert wo.get(plant, o["wo_id"])["state"] == "PENDING_APPROVAL"
    assert any(x.get("action") == "reactivated" and x["wo_id"] == o["wo_id"] for x in out)


def test_a_reasoned_rejection_is_not_re_raised_for_the_same_condition(plant):
    _assessment(plant, "INSPECTION_RECOMMENDED")
    latch(plant, state=H.INSPECTION_RECOMMENDED)
    first = [x for x in decision.generate(plant, decision.DecisionConfig(), actor="sys") if x["asset_id"] == "P-101"][0]
    wo.transition(plant, first["wo_id"], "reject", actor="pat", role="planner", reason="known issue: exchange booked next month")
    _assessment(plant, "INSPECTION_RECOMMENDED")                           # a new assessment, same condition
    again = [x for x in decision.generate(plant, decision.DecisionConfig(), actor="sys") if x["asset_id"] == "P-101"][0]
    assert again["action"] == "suppressed" and "known issue" in again["note"]
    _assessment(plant, "URGENT_REVIEW")                                    # the condition escalates: raised again
    latch(plant)
    esc = [x for x in decision.generate(plant, decision.DecisionConfig(), actor="sys") if x["asset_id"] == "P-101"][0]
    assert esc["action"] == "created" and esc["priority_class"] == "P1"


# -- work-order workflow gaps (technician-7, security-5) -------------------------------------------------------------
def test_a_technician_can_hand_back_a_job_with_a_reason(plant):
    w = order(plant, "h1")
    with pytest.raises(wo.WorkflowError):
        wo.transition(plant, w, "hand_back", actor="tom", role="technician")
    wo.transition(plant, w, "hand_back", actor="tom", role="technician", reason="wind above climbing limit")
    o = wo.get(plant, w)
    assert o["state"] == "APPROVED" and o["assigned"] == [] and o["scheduled_start_ms"] is None


def test_schedule_technicians_must_be_registered_when_the_site_has_a_crew_list(plant):
    from sentinelloop.app import resources
    resources.upsert_technician(plant, "T1", "Tech One", "site1", ["mech"], actor="pat")
    o = wo.create(plant, asset_id="P-101", job_type="inspect", priority_class="P2", title="t", origin="manual", actor="pat", role="planner",
                  idempotency_key="s1")
    wo.transition(plant, o["wo_id"], "submit", actor="pat", role="planner")
    wo.transition(plant, o["wo_id"], "approve", actor="pat", role="planner")
    with pytest.raises(wo.WorkflowError):
        wo.transition(plant, o["wo_id"], "schedule", actor="pat", role="planner", data={**SCHED, "technicians": ["ghost"]})
    wo.transition(plant, o["wo_id"], "schedule", actor="pat", role="planner", data={**SCHED, "technicians": ["T1"]})


# -- decision content for anomaly-only models (om_manager-7, technician-6, om_manager-9, om_manager-2, safety-5) -------
def wind_asset_spec(crit):
    from sentinelloop.app.models import AssetSpec
    return AssetSpec(asset_id="WT09", tag="w:WT09", name="WT09", asset_type_id=wind.ASSET_TYPE_ID, site_id="w", criticality=crit,
                     consequence=wind.CONSEQUENCE[crit])


def _rec(state, latched="NONE", crit="A", anomaly_score=None, reasons=None):
    from sentinelloop.app.models import Asset
    t = wind.asset_type_spec()
    a = Asset(**wind_asset_spec(crit).model_dump(), status="active", created_at=iso(0), updated_at=iso(0))
    st = AssetState(effective=state, latched_risk=latched, last_health=state)
    asm = {"assessment_id": "A-1", "risk": {}, "reasons": reasons or ["x"], "anomaly_score": anomaly_score, "rul_lower_hours": None}
    return decision.recommend(a, t, asm, st, decision.DecisionConfig(), now_ms=0)


def test_anomaly_urgent_wording_makes_no_failure_time_claim():
    r = _rec(H.URGENT_REVIEW, "URGENT", anomaly_score=4.0)
    assert "fail before" not in r.explanation["why"] and "not a failure-time prediction" in r.explanation["why"]


def test_anomaly_orders_are_ranked_by_deviation_and_consequence_not_creation_time():
    big, small = _rec(H.INSPECTION_RECOMMENDED, "INSPECTION", "A", 3.0), _rec(H.INSPECTION_RECOMMENDED, "INSPECTION", "C", 1.1)
    assert big.priority_score > small.priority_score > 0
    assert big.explanation["p_fail_decision_horizon"] is None and "not a probability" in big.explanation["score_rule"]


def test_out_of_scope_criticality_a_turbines_get_a_desk_review_not_a_climb():
    r = _rec(H.MODEL_OUT_OF_SCOPE, crit="A")
    assert r.job_type == "desk_review"


def test_a_latched_inspection_hidden_by_scope_still_gets_an_inspection_and_a_label():
    r = _rec(H.MODEL_OUT_OF_SCOPE, latched="INSPECTION", crit="C")
    assert r is not None and r.job_type == "inspect"
    s = AssetState(effective=H.MODEL_OUT_OF_SCOPE, latched_risk="INSPECTION", last_health=H.MODEL_OUT_OF_SCOPE)
    assert "INSPECTION_PENDING" in s.labels()


# -- data path (om_manager-1, om_manager-11) ---------------------------------------------------------------------------
def test_a_feed_delay_is_a_data_path_problem_not_an_instrument_check(plant):
    t = now_ms()
    recs = [{"asset": "P-101", "timestamp": iso(t - 12 * HOUR_MS - k * 600_000), "signal": s, "value": v, "unit": u}
            for k in range(40) for s, v, u in (("bearing_temp", 60.0 + k * 0.01, "degC"), ("vibration_rms", 2.0 + k * 0.001, "mm/s"))]
    ingest.ingest_records(plant, recs, source="t", actor="svc")
    a = health.assess(plant, "P-101", POL, as_of_ms=t)
    assert a["health_state"] == "DATA_QUALITY_FAILURE" and any(r.startswith("data_delivery_delay") for r in a["reasons"])
    assert not any(r.startswith("stale_data") for r in a["reasons"])
    out = [x for x in decision.generate(plant, decision.DecisionConfig(), actor="sys") if x["asset_id"] == "P-101"]
    assert out == []                                                         # no order to the asset for a late feed


def test_pitch_angle_is_not_required_by_the_wind_contract():
    spec = {s.name: s for s in wind.asset_type_spec().signals}
    assert spec["pitch_angle"].required is False


# -- assessment freshness (safety-7, technician-13) ------------------------------------------------------------------
def test_assets_report_when_they_were_last_assessed_and_flag_overdue(plant):
    security.create_user(plant, "vic", "Vic", "viewer", actor="b")
    k = security.issue_api_key(plant, "vic", actor="b")
    health.assess(plant, "P-101", POL, as_of_ms=now_ms())
    with plant.tx() as c:                                                    # pretend the assessment job stopped 3 days ago
        c.execute("UPDATE asset_states SET last_applied_at_ms = ? WHERE asset_id = 'P-101'", (now_ms() - 3 * DAY_MS,))
    c = TestClient(api.create_app(plant, POL, rate_limit=(1000, 1000.0)))
    rows = {a["asset_id"]: a for a in c.get("/api/v1/assets", headers={"Authorization": f"Bearer {k}"}).json()}
    assert rows["P-101"]["last_assessed_at"] is not None and "ASSESSMENT_OVERDUE" in rows["P-101"]["state"]
    assert rows["P-102"]["last_assessed_at"] is None and rows["P-102"]["state"] == ["NOT_ASSESSED"]


# -- missing coverage named in RELIABILITY_AND_SAFETY (safety-8) --------------------------------------------------------
def test_a_failing_asset_is_isolated_and_the_error_audited(plant, monkeypatch):
    real = decision._generate_one

    def boom(db, a, *rest):
        if a.asset_id == "P-101":
            raise RuntimeError("injected")
        return real(db, a, *rest)
    monkeypatch.setattr(decision, "_generate_one", boom)
    out = decision.generate(plant, decision.DecisionConfig(), actor="sys")
    assert any(x["asset_id"] == "P-101" and x["action"] == "error" for x in out)
    with plant.connect() as c:
        assert c.execute("SELECT COUNT(*) FROM audit_events WHERE action = 'decision.error' AND entity_id = 'P-101'").fetchone()[0] == 1


def test_suspect_values_above_the_limit_make_a_data_quality_failure(plant):
    t = now_ms()
    recs = [{"asset": "P-101", "timestamp": iso(t - k * 600_000), "signal": s, "value": v, "unit": u}
            for k in range(30) for s, v, u in (("bearing_temp", 999.0, "degC"), ("vibration_rms", 2.0 + k * 0.001, "mm/s"))]
    r = ingest.ingest_records(plant, recs, source="t", actor="svc")
    assert r.rows_suspect == 30
    a = health.assess(plant, "P-101", POL, as_of_ms=t)
    assert a["health_state"] == "DATA_QUALITY_FAILURE" and any(x.startswith("out_of_range:bearing_temp") for x in a["reasons"])


def test_an_unknown_latch_start_fails_closed(plant):
    """Follow-up security review: a latch whose start time is unknown (e.g. latched before migration 0006) is kept."""
    s = states.replace(latch(plant), latched_since_ms=None)
    with plant.tx() as c:
        health._store_state(c, "P-101", s, None)
    w = order(plant, "u1")
    wo.complete(plant, w, actor="tom", role="technician", outcome=INSPECTED)
    assert health.asset_state(plant, "P-101").latched_risk == "URGENT"


def test_advance_never_records_a_zero_latch_start():
    s = states.advance(AssetState(), Classification(H.URGENT_REVIEW, []), Thresholds())
    assert s.latched_since_ms is not None and s.latched_since_ms > 0


def test_migration_backfills_the_start_of_existing_latches(plant):
    """Migration 0007: latched rows without a start get their last-update time (at or after the true start: fail closed)."""
    latch(plant)
    with plant.tx() as c:
        c.execute("UPDATE asset_states SET latched_since_ms = NULL, updated_at = '2026-10-01T12:00:00Z' WHERE asset_id = 'P-101'")
        c.execute((ROOT / "src" / "sentinelloop" / "app" / "migrations" / "0007_backfill_latch_start.sql").read_text(encoding="utf-8"))
    assert health.asset_state(plant, "P-101").latched_since_ms == parse_ts("2026-10-01T12:00:00Z")


def test_decision_parameters_can_be_site_configured_and_ready_says_which(tmp_path, plant):
    """Review buyer-6: downtime cost is 'required' (PD-09) but could not be set in a deployed server."""
    cfg_file = tmp_path / "decision.yaml"
    cfg_file.write_text("downtime_cost_per_h: 0.004\nlabour_cost_per_h: 1.0\ndefault_due_h: {P1: 12, P2: 120, P3: 720}\n", encoding="utf-8")
    dcfg = decision.load_config(cfg_file)
    assert dcfg.downtime_cost_per_h == 0.004 and dcfg.default_due_h["P1"] == 12
    with pytest.raises(ValueError):
        decision.load_config_text("downtime_cost_per_h: -1\n")
    with pytest.raises(ValueError):
        decision.load_config_text("unknown_key: 1\n")
    c = TestClient(api.create_app(plant, POL, decision_cfg=dcfg))
    assert c.get("/api/v1/ready").json()["decision_config"] == "site-configured"
    c2 = TestClient(api.create_app(plant, POL))
    assert c2.get("/api/v1/ready").json()["decision_config"].startswith("placeholder defaults")
