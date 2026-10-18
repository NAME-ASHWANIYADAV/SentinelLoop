"""Regression tests for the assessment, state, wind-model and migration defects confirmed by the re-review of the Phase 9
fixes (product/evidence/adversarial/rereview.json). Each test names the finding it covers. They were written before the
fixes and failed then. All wind data here are SYNTHETIC (sentinelloop.app.synthetic_wind): these tests check behaviour,
not field accuracy.
"""
import copy
import hashlib
import json
import shutil

import numpy as np
import pytest
from fastapi.testclient import TestClient

from sentinelloop.app import api, db as dbmod, decision, health, ingest, modelreg, nbm, policy as policymod, registry, security, states
from sentinelloop.app import synthetic_wind as sw, workorders as wo
from sentinelloop.app.adapters import wind
from sentinelloop.app.states import AssetState, Classification, HealthState as H, Thresholds
from sentinelloop.app.timeutil import DAY_MS, HOUR_MS, iso, now_iso, now_ms, parse_ts
from conftest import ROOT
from test_app_foundation import KEY, pump, pump_type

POL = policymod.load(ROOT / "configs" / "platform.yaml")
WIND_POL = POL.for_type(wind.ASSET_TYPE_ID)
STEP = 600_000                                     # 10-minute SCADA
FAULT = sw.Fault(turbine="WT01", component="hss_bearing", start_day=20.0, fail_day=34.0)
STUCK = sw.SensorFault("WT01", "gearbox_bearing_temp", "stuck", start_day=25.0, end_day=26.0)
ALARMS = ("INSPECTION_RECOMMENDED", "URGENT_REVIEW")
INSPECTED = {"findings_code": "no_fault_found", "failure_confirmed": "no", "actions_taken": "inspected, nothing found", "downtime_hours": 1}


# -- fixtures ----------------------------------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def bundle_dir(tmp_path_factory):
    train = sw.generate(sw.FleetSpec(n_turbines=4, days=45, seed=3)).scada         # the training fleet of tests/test_app_wind.py
    return nbm.package_wind_nbm(train, tmp_path_factory.mktemp("models"), scope_key="wind:synthetic", data_class="SYNTHETIC",
                                source="synthetic_wind seed 3, 4 turbines x 45 days", seed=0)


@pytest.fixture(scope="module")
def fault_fleet():
    return sw.generate(sw.FleetSpec(n_turbines=1, days=36, seed=11, faults=(FAULT,)))


@pytest.fixture(scope="module")
def stuck_fleet():
    return sw.generate(sw.FleetSpec(n_turbines=2, days=28, seed=12, sensor_faults=(STUCK,)))


@pytest.fixture(scope="module")
def healthy_fleet():
    return sw.generate(sw.FleetSpec(n_turbines=1, days=20, seed=21))


@pytest.fixture
def farm(tmp_path, bundle_dir):
    bdir = tmp_path / "bundle"
    shutil.copytree(bundle_dir, bdir)                    # each test may break its own copy
    d = dbmod.Database(tmp_path / "w.db", audit_key=KEY, audit_key_id="test")
    d.migrate()
    wind.ensure_site_and_type(d, actor="admin")
    d.model_id = modelreg.register(d, bdir, actor="rea")
    modelreg.decide(d, d.model_id, "approved", actor="rea", role="reliability_engineer", reason="synthetic behaviour test")
    d.bundle_dir = bdir
    health._BUNDLE_CACHE.clear()
    return d


@pytest.fixture
def pumps(tmp_path):
    d = dbmod.Database(tmp_path / "p.db", audit_key=KEY, audit_key_id="test")
    d.migrate()
    registry.create_site(d, "site1", "Plant 1", "UTC", actor="admin")
    registry.create_asset_type(d, pump_type(), actor="admin")
    registry.create_asset(d, pump("P-101"), actor="admin")
    registry.create_asset(d, pump("P-103", tag="TAG-103"), actor="admin")
    return d


def _load(d, frame, turbine, t0, t1, mutate=None):
    s = frame[(frame.turbine == turbine) & (frame.ts_ms > t0) & (frame.ts_ms <= t1)].copy()
    if mutate:
        s = mutate(s)
    r = ingest.ingest_records(d, wind.records(s), source="synthetic-scada", actor="svc", now_ms=int(t1) + 60_000)
    assert r.rows_rejected == 0, r.to_dict()["errors"][:3]


def _commissioned(d, fleet, turbine="WT01", crit="B"):
    """A turbine with days 0.5-6.5 ingested and commissioned on days 1-6 (synthetic: no fault before day 20)."""
    st = fleet.meta["start_ms"]
    wind.create_turbine(d, turbine, criticality=crit, actor="admin")
    _load(d, fleet.scada, turbine, st + int(0.5 * DAY_MS), st + int(6.5 * DAY_MS))
    nbm.commission(d, turbine, d.model_id, st + DAY_MS, st + 6 * DAY_MS, actor="rea", role="reliability_engineer",
                   reason="days 1-6 declared healthy (synthetic)")
    return st


def _feed(d, asset, end_ms, n=40):
    recs = [{"asset": asset, "timestamp": iso(end_ms - k * STEP), "signal": s, "value": v, "unit": u}
            for k in range(n) for s, v, u in (("bearing_temp", 60.0 + k * 0.01, "degC"), ("vibration_rms", 2.0 + k * 0.001, "mm/s"))]
    ingest.ingest_records(d, recs, source="t", actor="svc")


def _n_assessments(d, asset_id):
    with d.connect() as c:
        return c.execute("SELECT COUNT(*) FROM assessments WHERE asset_id = ?", (asset_id,)).fetchone()[0]


def _latest_reading_policy():
    raw = copy.deepcopy(POL.raw)
    raw["asset_types"][wind.ASSET_TYPE_ID]["assessment"]["assess_at"] = "latest_reading"
    return policymod.PolicySet(raw, source="test: export-fed wind site")


# -- wind-eval-migrations-01: a recovered stuck sensor is not scored ------------------------------------------------------
def test_a_recovered_stuck_sensor_stays_a_data_failure_until_its_readings_leave_the_scoring_window(farm, stuck_fleet):
    st = _commissioned(farm, stuck_fleet)
    _load(farm, stuck_fleet.scada, "WT01", st + 24 * DAY_MS, st + int(26.6 * DAY_MS))
    a = health.assess(farm, "WT01", POL, as_of_ms=st + int(25.5 * DAY_MS), actor="svc")
    assert a["health_state"] == "DATA_QUALITY_FAILURE" and any("stuck_signal:gearbox_bearing_temp" in r for r in a["reasons"])
    seen = []
    for k in range(13):                                   # hourly, from the sensor's recovery (day 26.0) to 12 h after
        a = health.assess(farm, "WT01", POL, as_of_ms=st + 26 * DAY_MS + k * HOUR_MS, actor="svc")
        seen.append((k, a["health_state"], a["anomaly_score"], [r[:60] for r in a["reasons"]][:1]))
    assert not [x for x in seen if x[1] in ALARMS], seen  # the rejected readings never produce an alarm
    span_h = (nbm.WINDOW + nbm.SUSTAIN) // 6               # the rows the score uses (window + sustain), in hours
    assert all(x[1] == "DATA_QUALITY_FAILURE" and "stuck_signal" in x[3][0] for x in seen[:span_h]), seen   # still inside the scored span
    assert seen[-1][1] == "NORMAL_MONITORING", seen       # once they have left it (and the hysteresis has passed), normal again
    assert health.asset_state(farm, "WT01").labels() == ["NORMAL_MONITORING"] and health.asset_state(farm, "WT01").latched_risk == "NONE"


def test_the_harness_also_refuses_a_window_whose_scored_span_holds_a_stuck_run(bundle_dir, stuck_fleet):
    b = nbm.load(bundle_dir)
    x = stuck_fleet.scada[stuck_fleet.scada.turbine == "WT01"].reset_index(drop=True)
    i = 26 * 144 + 12                                      # two hours after the sensor recovered
    w = x.iloc[i - b.history_points + 1: i + 1]
    assert nbm.gate(b, w, stuck_min_run=WIND_POL.assessment["stuck_min_run"]) == "data_quality"
    q = b.quality(w, WIND_POL.assessment["stuck_min_run"], WIND_POL.assessment["max_conflict_frac"])
    assert q["detail"]["stuck"]["gearbox_bearing_temp"] >= 80 and "stuck_signal:gearbox_bearing_temp" in q["reasons"][0]
    clean = x.iloc[i + 60 - b.history_points + 1: i + 61]  # 12 h after recovery the stuck rows are in the warm-up part only
    assert b.quality(clean, 6, 0.2)["ok"]


# -- wind-eval-migrations-05: sustain counts operating points -----------------------------------------------------------
def _spike_then_idle(b, x, target="gearbox_bearing_temp"):
    """One hot operating reading, then the turbine stops for the rest of the sustain span (sustain - 1 rows)."""
    hp, S = b.history_points, b.sustain
    i = next(i for i in range(10 * 144, len(x)) if (x.active_power.iloc[i - hp + 1: i - S + 2] / wind.RATED_KW > nbm.OP_FRAC).mean() > 0.95)
    y = x.iloc[: i + 1].copy()
    y.loc[y.index[-(S - 1):], ["active_power", "rotor_speed", "generator_speed"]] = 0.0
    off, _ = b.baseline_offsets(y.iloc[144: 6 * 144])
    for bump in np.arange(0.5, 60, 0.5):                  # the smallest rise of ONE operating reading that crosses the threshold
        z = y.copy()
        z.loc[z.index[-S], target] += bump
        sc, op, _ = b.scores(z.iloc[-hp:], off)
        if sc[target][-S] > b.thr_inspect[target]:
            return y, z, off, bump
    raise AssertionError("no crossing found")


def test_one_hot_reading_followed_by_an_idle_spell_is_not_a_sustained_deviation(bundle_dir, healthy_fleet):
    b = nbm.load(bundle_dir)
    t = "gearbox_bearing_temp"
    y, z, off, bump = _spike_then_idle(b, healthy_fleet.scada[healthy_fleet.scada.turbine == "WT01"].reset_index(drop=True), t)
    w, S = z.iloc[-b.history_points:], b.sustain
    sc, op, _ = b.scores(w, off)
    assert int(op[-S:].sum()) == 1 and np.all(sc[t][-S:] > b.thr_inspect[t])       # S rows "above", from ONE operating point
    assert b.score(w, off)["anomaly_sustained"] is False
    # control: the same rise held for the last S operating points is still a sustained deviation
    held = y.copy()
    ops = np.flatnonzero(held.active_power.to_numpy() / wind.RATED_KW > nbm.OP_FRAC)[-S:]
    held.loc[held.index[ops], t] += bump * 2
    assert b.score(held.iloc[-b.history_points:], off)["anomaly_sustained"] is True


def test_the_service_does_not_latch_on_one_hot_reading_before_a_stop(farm, bundle_dir, healthy_fleet):
    b = nbm.load(bundle_dir)
    x = healthy_fleet.scada[healthy_fleet.scada.turbine == "WT01"].reset_index(drop=True)
    _, z, _, _ = _spike_then_idle(b, x)
    st = _commissioned(farm, healthy_fleet)
    tail = z[z.ts_ms > st + int(6.5 * DAY_MS)]
    _load(farm, tail.assign(turbine="WT01"), "WT01", int(tail.ts_ms.min()) - 1, int(tail.ts_ms.max()))
    a = health.assess(farm, "WT01", POL, as_of_ms=int(z.ts_ms.iloc[-1]), actor="svc")
    assert a["health_state"] == "NORMAL_MONITORING", (a["health_state"], a["top_deviations"], a["reasons"])
    assert health.asset_state(farm, "WT01").latched_risk == "NONE"


# -- wind-eval-migrations-08: model data checks run before the no-baseline scope decision ----------------------------------
def test_a_stuck_sensor_on_an_uncommissioned_turbine_is_a_data_failure(farm, healthy_fleet):
    st = healthy_fleet.meta["start_ms"]
    t = st + 18 * DAY_MS
    wind.create_turbine(farm, "WT01", criticality="A", actor="admin")

    def stick(s):
        s.loc[s.ts_ms > t - 8 * HOUR_MS, "gearbox_oil_temp"] = 51.3
        return s
    _load(farm, healthy_fleet.scada, "WT01", t - 24 * HOUR_MS, t, mutate=stick)
    a = health.assess(farm, "WT01", POL, as_of_ms=t, actor="svc")
    assert a["health_state"] == "DATA_QUALITY_FAILURE", a["reasons"]
    assert any("stuck_signal:gearbox_oil_temp" in r for r in a["reasons"]) and any("no_baseline" in r for r in a["reasons"])


# -- latching-states-01: a replay can only raise a latch ------------------------------------------------------------------
def test_replay_escalation_is_monotone_toward_more_risk():
    thr = Thresholds()
    base = states.advance(AssetState(), Classification(H.NORMAL_MONITORING, []), thr, now_ms=1_000)
    up = states.escalate(base, Classification(H.INSPECTION_RECOMMENDED, []), note="replay of t1", now_ms=2_000)
    assert (up.latched_risk, up.latched_since_ms, up.effective, up.last_health) == ("INSPECTION", 2_000, H.INSPECTION_RECOMMENDED, H.NORMAL_MONITORING)
    assert "replay of t1" in up.notes and (up.dq_ok_streak, up.dq_failure_active) == (base.dq_ok_streak, base.dq_failure_active)
    top = states.escalate(up, Classification(H.URGENT_REVIEW, []), note="replay of t2", now_ms=3_000)
    assert (top.latched_risk, top.latched_since_ms, top.effective) == ("URGENT", 3_000, H.URGENT_REVIEW)
    assert states.escalate(top, Classification(H.INSPECTION_RECOMMENDED, []), note="x", now_ms=4_000) == top
    for st in (H.NORMAL_MONITORING, H.DATA_QUALITY_FAILURE, H.MODEL_OUT_OF_SCOPE, H.MODEL_UNAVAILABLE):
        assert states.escalate(up, Classification(st, []), note="x", now_ms=5_000) == up
    dq = states.advance(AssetState(), Classification(H.DATA_QUALITY_FAILURE, []), thr)
    assert states.escalate(dq, Classification(H.INSPECTION_RECOMMENDED, []), note="x", now_ms=6_000).labels() == ["DATA_QUALITY_FAILURE", "INSPECTION_PENDING"]


def test_an_urgent_replay_escalates_the_latch_and_changes_nothing_else(farm, fault_fleet):
    st = _commissioned(farm, fault_fleet, crit="A")
    _load(farm, fault_fleet.scada, "WT01", st + 30 * DAY_MS, st + int(32.5 * DAY_MS))
    live = health.assess(farm, "WT01", POL, actor="svc")        # shipped default instant (now): the export is months old
    assert live["applied_to_state"] and any(r.startswith("data_delivery_delay") for r in live["reasons"])
    before, t_wall = health.asset_state(farm, "WT01"), now_ms()
    out = health.assess_range(farm, "WT01", POL, st + 31 * DAY_MS, st + 32 * DAY_MS, HOUR_MS, actor="svc")     # the export replayed
    assert out["assessments"] == 25 and out["applied"] == 0 and out["states"].get("URGENT_REVIEW", 0) >= 1, out
    assert 1 <= out["replays_escalated"] <= 2, out          # NONE -> (INSPECTION ->) URGENT; later urgent replays find it latched
    s = health.asset_state(farm, "WT01")
    assert s.latched_risk == "URGENT" and s.labels()[0] == "URGENT_REVIEW" and s.latched_since_ms >= t_wall
    assert (s.last_health, s.dq_failure_active, s.dq_ok_streak, s.last_applied_as_of_ms, s.last_applied_at_ms) == \
        (before.last_health, before.dq_failure_active, before.dq_ok_streak, before.last_applied_as_of_ms, before.last_applied_at_ms)
    with farm.connect() as c:
        rows = c.execute("SELECT as_of_ms, applied_to_state, reasons_json FROM assessments WHERE asset_id = 'WT01' AND assessment_id != ? "
                         "ORDER BY as_of_ms", (live["assessment_id"],)).fetchall()
        ev = [json.loads(r["payload_json"]) for r in c.execute("SELECT payload_json FROM audit_events WHERE action = 'asset_state.escalated_by_replay'")]
    assert len(rows) == 25 and all(r["applied_to_state"] == 0 for r in rows)
    noted = [r for r in rows if any("escalat" in x for x in json.loads(r["reasons_json"]))]
    assert len(noted) == out["replays_escalated"] and all(iso(r["as_of_ms"]) in " ".join(json.loads(r["reasons_json"])) for r in noted)
    assert len(ev) == out["replays_escalated"] and ev[-1]["after"][0] == "URGENT_REVIEW" and ev[-1]["as_of"] == iso(noted[-1]["as_of_ms"])
    assert health.latest_assessment(farm, "WT01")["assessment_id"] == live["assessment_id"]
    made = [x for x in decision.generate(farm, decision.DecisionConfig(), actor="svc") if x["asset_id"] == "WT01"]
    assert made and made[0]["action"] == "created" and made[0]["priority_class"] == "P1", made


def test_assess_at_latest_reading_uses_the_last_reading_and_a_later_urgent_replay_still_latches(farm, fault_fleet):
    pol = _latest_reading_policy()
    st = _commissioned(farm, fault_fleet, crit="A")
    end = st + int(32.5 * DAY_MS)

    def stick(s):                                          # the export ends with a stuck sensor: its last instant is a data failure
        s.loc[s.ts_ms > end - 8 * HOUR_MS, "generator_bearing_temp"] = 41.0
        return s
    _load(farm, fault_fleet.scada, "WT01", st + 30 * DAY_MS, end, mutate=stick)
    a = health.assess(farm, "WT01", pol, actor="svc")       # the scheduled job, run before the replay
    assert a["as_of_ms"] == end and a["applied_to_state"] and a["health_state"] == "DATA_QUALITY_FAILURE", a["reasons"]
    out = health.assess_range(farm, "WT01", pol, st + 31 * DAY_MS, st + 32 * DAY_MS, 2 * HOUR_MS, actor="svc")
    assert out["applied"] == 0 and out["replays_escalated"] >= 1, out
    s = health.asset_state(farm, "WT01")
    assert s.latched_risk == "URGENT" and s.last_applied_as_of_ms == end and s.last_health == H.DATA_QUALITY_FAILURE


def test_assess_at_latest_reading_needs_a_reading(farm):
    wind.create_turbine(farm, "WT05", criticality="B", actor="admin")
    with pytest.raises(health.AssessmentError, match="no readings"):
        health.assess(farm, "WT05", _latest_reading_policy(), actor="svc")
    assert _n_assessments(farm, "WT05") == 0


def test_assess_range_run_first_applies_every_step_oldest_first(farm, fault_fleet):
    st = _commissioned(farm, fault_fleet, crit="A")
    _load(farm, fault_fleet.scada, "WT01", st + 30 * DAY_MS, st + int(32.5 * DAY_MS))
    out = health.assess_range(farm, "WT01", POL, st + 31 * DAY_MS, st + 32 * DAY_MS, 6 * HOUR_MS, actor="svc")
    assert (out["assessments"], out["applied"], out["replays_escalated"]) == (5, 5, 0), out
    s = health.asset_state(farm, "WT01")
    assert s.last_applied_as_of_ms == st + 32 * DAY_MS and s.latched_risk == "URGENT"
    again = health.assess_range(farm, "WT01", POL, st + 31 * DAY_MS, st + 32 * DAY_MS, 6 * HOUR_MS, actor="svc")
    assert (again["applied"], again["replays_escalated"]) == (0, 0)                  # already latched: nothing to raise


# -- re-review verify2 r01: a replay of an instant already assessed does not undo a person's clear ---------------------------------
def test_a_replay_does_not_raise_a_finding_already_recorded_for_its_instant():
    thr = Thresholds()
    s = states.advance(AssetState(), Classification(H.URGENT_REVIEW, []), thr, now_ms=1_000)
    s = states.clear_risk(s, "dismissed", actor="rea", role="reliability_engineer", reason="reviewed this assessment")
    urgent, insp = Classification(H.URGENT_REVIEW, []), Classification(H.INSPECTION_RECOMMENDED, [])
    assert states.escalate(s, urgent, note="x", now_ms=2_000, recorded=[H.URGENT_REVIEW]) is s       # the finding the person cleared
    assert states.escalate(s, insp, note="x", now_ms=2_000, recorded=[H.URGENT_REVIEW]) is s
    assert states.escalate(s, urgent, note="x", now_ms=2_000, recorded=[H.INSPECTION_RECOMMENDED]).latched_risk == "URGENT"   # more risk
    for other in ([], [H.NORMAL_MONITORING, H.DATA_QUALITY_FAILURE, H.MODEL_OUT_OF_SCOPE, H.MODEL_UNAVAILABLE]):
        assert states.escalate(s, urgent, note="x", now_ms=2_000, recorded=other).latched_risk == "URGENT"                  # new evidence


def _urgent_export(farm, fleet):
    """An export-fed turbine (assess_at: latest_reading) whose latest reading the scheduled job finds URGENT_REVIEW."""
    pol = _latest_reading_policy()
    st = _commissioned(farm, fleet, crit="A")
    end = st + int(32.5 * DAY_MS)
    _load(farm, fleet.scada, "WT01", st + 30 * DAY_MS, end)
    a = health.assess(farm, "WT01", pol, actor="svc")
    assert (a["as_of_ms"], a["applied_to_state"], a["health_state"]) == (end, True, "URGENT_REVIEW"), a["reasons"]
    return pol, end


def _next_runs_change_nothing(farm, pol, end):
    for _ in range(2):                                   # the scheduled job before the next export: the same latest reading
        a = health.assess(farm, "WT01", pol, actor="svc")
        assert (a["as_of_ms"], a["applied_to_state"], a["health_state"], a["latch_escalated"]) == (end, False, "URGENT_REVIEW", False)
        assert any("already had this finding" in r for r in a["reasons"]), a["reasons"]
    s = health.asset_state(farm, "WT01")
    assert s.labels() == ["AWAITING_ASSESSMENT"] and (s.latched_risk, s.latched_since_ms) == ("NONE", None)
    assert [x for x in decision.generate(farm, decision.DecisionConfig(), actor="svc") if x["asset_id"] == "WT01"] == []


def test_a_dismissal_is_not_undone_by_the_next_run_on_the_same_latest_reading(farm, fault_fleet):
    pol, end = _urgent_export(farm, fault_fleet)
    health.clear_latched_risk(farm, "WT01", "dismissed", actor="rea", role="reliability_engineer",
                              reason="reviewed this assessment: a known sensor drift, not the bearing")
    _next_runs_change_nothing(farm, pol, end)


def test_a_completed_inspection_is_not_undone_by_the_next_run_on_the_same_latest_reading(farm, fault_fleet):
    pol, end = _urgent_export(farm, fault_fleet)
    made = [x for x in decision.generate(farm, decision.DecisionConfig(), actor="svc") if x["asset_id"] == "WT01"]
    assert made and made[0]["action"] == "created", made
    w, t = made[0]["wo_id"], now_ms()
    wo.transition(farm, w, "approve", actor="pat", role="planner")
    wo.transition(farm, w, "schedule", actor="pat", role="planner",
                  data={"start": iso(t + DAY_MS), "end": iso(t + DAY_MS + 6 * HOUR_MS), "technicians": ["tech1"]})
    wo.transition(farm, w, "start", actor="tom", role="technician")
    done = wo.complete(farm, w, actor="tom", role="technician", outcome=INSPECTED)
    assert "latch_kept" not in done["outcome"]["flags"] and health.asset_state(farm, "WT01").labels() == ["AWAITING_ASSESSMENT"]
    _next_runs_change_nothing(farm, pol, end)


def test_a_new_finding_for_an_instant_already_applied_still_raises_the_latch(farm, fault_fleet):
    pol = _latest_reading_policy()
    st = _commissioned(farm, fault_fleet, crit="A")
    end, late = st + int(32.5 * DAY_MS), "gearbox_bearing_temp"
    cut = lambda s: s.assign(**{late: s[late].where(s.ts_ms <= end - 3 * HOUR_MS)})      # one signal's file arrives later
    _load(farm, fault_fleet.scada, "WT01", st + 30 * DAY_MS, end, mutate=cut)
    a = health.assess(farm, "WT01", pol, actor="svc")
    assert (a["as_of_ms"], a["applied_to_state"], a["health_state"]) == (end, True, "DATA_QUALITY_FAILURE"), a["reasons"]
    only = lambda s: s.assign(**{c: np.nan for c in wind.SIGNALS if c != late})
    _load(farm, fault_fleet.scada, "WT01", end - 3 * HOUR_MS, end, mutate=only)
    a = health.assess(farm, "WT01", pol, actor="svc")                                  # same instant, new data in its window
    assert (a["as_of_ms"], a["applied_to_state"], a["health_state"], a["latch_escalated"]) == (end, False, "URGENT_REVIEW", True), a["reasons"]
    assert health.asset_state(farm, "WT01").latched_risk == "URGENT"


# -- latching-states-06: a model outage with failing data does not clear a data failure --------------------------------------
def test_a_model_outage_with_failing_data_does_not_count_toward_clearing_a_data_failure():
    thr = Thresholds()
    s = states.advance(AssetState(), Classification(H.DATA_QUALITY_FAILURE, []), thr)
    outage = states.classify(model_ok=False, data_ok=False, in_scope=False, p_fail=None, sustained_anomaly=False, thr=thr)
    assert outage.state == H.MODEL_UNAVAILABLE
    for _ in range(3):
        s = states.advance(s, outage, thr)
    assert s.dq_failure_active and s.dq_ok_streak == 0 and s.labels()[0] == "DATA_QUALITY_FAILURE"
    good = states.classify(True, True, True, None, False, thr, anomaly_only=True)
    s = states.advance(s, good, thr)
    assert s.dq_failure_active                                                      # one good assessment is not enough
    s = states.advance(s, good, thr)
    assert not s.dq_failure_active and s.effective == H.NORMAL_MONITORING
    ok_data = states.classify(model_ok=False, data_ok=True, in_scope=False, p_fail=None, sustained_anomaly=False, thr=thr)
    s = states.advance(states.advance(AssetState(), Classification(H.DATA_QUALITY_FAILURE, []), thr), ok_data, thr)
    assert s.dq_ok_streak == 1                              # an outage with good data still counts


def test_the_service_holds_a_data_failure_through_a_model_outage(farm, healthy_fleet):
    st = _commissioned(farm, healthy_fleet)
    _load(farm, healthy_fleet.scada, "WT01", st + int(6.5 * DAY_MS), st + 9 * DAY_MS)
    t = st + 9 * DAY_MS
    assert health.assess(farm, "WT01", POL, as_of_ms=t + 3 * HOUR_MS, actor="svc")["health_state"] == "DATA_QUALITY_FAILURE"   # feed stopped
    pkl = farm.bundle_dir / "bundle.pkl"
    keep = pkl.read_bytes()
    pkl.unlink()                                           # and the model artefact goes missing
    health._BUNDLE_CACHE.clear()
    for h in (4, 5):
        a = health.assess(farm, "WT01", POL, as_of_ms=t + h * HOUR_MS, actor="svc")
        assert a["health_state"] == "MODEL_UNAVAILABLE" and a["data_quality"]["generic"]["ok"] is False
    s = health.asset_state(farm, "WT01")
    assert s.dq_failure_active and s.dq_ok_streak == 0 and s.labels()[0] == "DATA_QUALITY_FAILURE"
    pkl.write_bytes(keep)                                  # model and feed come back
    health._BUNDLE_CACHE.clear()
    _load(farm, healthy_fleet.scada, "WT01", t, st + 10 * DAY_MS)
    a = health.assess(farm, "WT01", POL, as_of_ms=st + 10 * DAY_MS, actor="svc")
    assert a["data_quality"]["generic"]["ok"] and health.asset_state(farm, "WT01").labels()[0] == "DATA_QUALITY_FAILURE"
    health.assess(farm, "WT01", POL, as_of_ms=st + 10 * DAY_MS + HOUR_MS // 2, actor="svc")
    assert not health.asset_state(farm, "WT01").dq_failure_active


# -- latching-states-02, wind-eval-migrations-03/-04: upgraded databases --------------------------------------------------------
def _database_at(path, version):
    """A database built with only the first `version` migrations: an installation that has not been upgraded yet."""
    d = dbmod.Database(path, audit_key=KEY, audit_key_id="test")
    with d.connect() as c:
        c.execute("CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, name TEXT NOT NULL, checksum TEXT NOT NULL, applied_at TEXT NOT NULL)")
        for v, name, p in dbmod.Database.migration_files()[:version]:
            sql = p.read_text(encoding="utf-8")
            c.executescript(sql)
            c.execute("INSERT INTO schema_migrations VALUES (?, ?, ?, ?)", (v, name, hashlib.sha256(sql.encode("utf-8")).hexdigest(), now_iso()))
    return d


def _old_assessment(c, aid, asset, as_of, created_ms, state):
    c.execute("INSERT INTO assessments (assessment_id, asset_id, as_of_ms, created_at, model_id, health_state, reasons_json, data_quality_json, "
              "applicability_json, risk_json, inputs_json, policy_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
              (aid, asset, as_of, iso(created_ms), None, state, json.dumps(["before the upgrade"]), "{}", "{}", "{}", "{}", "{}"))


def test_an_upgraded_database_keeps_replays_out_of_the_live_state_and_reports_overdue(tmp_path):
    d = _database_at(tmp_path / "old.db", 5)
    assert d.schema_version() == 5
    registry.create_site(d, "site1", "Plant 1", "UTC", actor="admin")
    registry.create_asset_type(d, pump_type(), actor="admin")
    for a in ("P-101", "P-102", "P-103", "P-104"):
        registry.create_asset(d, pump(a), actor="admin")
    t = now_ms()
    live_as_of, live_at = t - 2 * DAY_MS, t - 2 * DAY_MS + 4_321          # the last assessment before the upgrade: a live data failure
    row = ("INSERT INTO asset_states (asset_id, effective, latched_risk, dq_failure_active, dq_ok_streak, last_health, approval_pending, "
           "notes_json, last_assessment_id, updated_at) VALUES (?, ?, 'NONE', ?, 0, ?, ?, '[]', ?, ?)")
    with d.tx() as c:
        _old_assessment(c, "A-old-1", "P-101", t - 3 * DAY_MS, live_at + 1_234, "NORMAL_MONITORING")   # an older instant, stored later
        _old_assessment(c, "A-old-2", "P-101", live_as_of, live_at, "DATA_QUALITY_FAILURE")
        c.execute(row, ("P-101", "DATA_QUALITY_FAILURE", 1, "DATA_QUALITY_FAILURE", 0, "A-old-2", iso(live_at + 1_234)))
        c.execute(row, ("P-102", "NORMAL_MONITORING", 0, None, 1, None, iso(t)))
        # schema-0005 code did not refuse future instants: one for 30 days ahead (a mistyped date), stored an hour ago
        _old_assessment(c, "A-old-3", "P-103", t + 30 * DAY_MS, t - HOUR_MS, "NORMAL_MONITORING")
        c.execute(row, ("P-103", "NORMAL_MONITORING", 0, "NORMAL_MONITORING", 0, "A-old-3", iso(t - HOUR_MS)))
        # a state row with a result but no assessment rows (a partial restore or a hand edit): a live data failure
        c.execute(row, ("P-104", "DATA_QUALITY_FAILURE", 1, "DATA_QUALITY_FAILURE", 0, None, iso(t - 2 * HOUR_MS)))
    applied = d.migrate()
    assert applied == [name for _, name, _ in dbmod.Database.migration_files()[5:]]
    assert d.schema_version() == len(dbmod.Database.migration_files())
    s = health.asset_state(d, "P-101")
    assert (s.last_applied_as_of_ms, s.last_applied_at_ms) == (live_as_of, live_at + 1_234)
    assert health.asset_state(d, "P-102").last_applied_as_of_ms is None              # never assessed: nothing to backfill from
    view = health.asset_view(d, registry.get_asset(d, "P-101"), POL, now=t)
    assert "ASSESSMENT_OVERDUE" in view["state"] and view["last_assessed_at"] == iso(live_at + 1_234)
    _feed(d, "P-101", t - 10 * DAY_MS + 39 * STEP)                                     # readings from 10 days ago, when the data were good
    for back in (t - 10 * DAY_MS + 30 * STEP, t - 10 * DAY_MS + 39 * STEP):
        assert health.assess(d, "P-101", POL, as_of_ms=back)["applied_to_state"] is False
    s = health.asset_state(d, "P-101")
    assert s.effective == H.DATA_QUALITY_FAILURE and s.dq_failure_active and s.last_applied_as_of_ms == live_as_of
    assert health.latest_assessment(d, "P-101")["assessment_id"] == "A-old-2"
    # a pre-upgrade future instant counts only up to the time it was stored (plus the clock skew): the live state is not frozen
    s = health.asset_state(d, "P-103")
    assert (s.last_applied_as_of_ms, s.last_applied_at_ms) == (t - HOUR_MS + health.MAX_FUTURE_SKEW_MS, t - HOUR_MS)
    a = health.assess(d, "P-103", POL)                                                # the scheduled job, now: no readings
    assert a["applied_to_state"] and health.asset_state(d, "P-103").labels() == ["DATA_QUALITY_FAILURE"]
    # no assessment rows: everything up to the row's last write is a replay, and the time of the last assessment is unknown
    s = health.asset_state(d, "P-104")
    assert (s.last_applied_as_of_ms, s.last_applied_at_ms) == (t - 2 * HOUR_MS, None)
    view = health.asset_view(d, registry.get_asset(d, "P-104"), POL, now=t)
    assert view["state"] == ["DATA_QUALITY_FAILURE", "ASSESSMENT_OVERDUE"] and view["last_assessed_at"] is None
    _feed(d, "P-104", t - 5 * DAY_MS + 39 * STEP)                                     # readings from 5 days ago, when the data were good
    for back in (t - 5 * DAY_MS + 30 * STEP, t - 5 * DAY_MS + 39 * STEP):
        assert health.assess(d, "P-104", POL, as_of_ms=back)["applied_to_state"] is False
    s = health.asset_state(d, "P-104")
    assert s.dq_failure_active and s.labels() == ["DATA_QUALITY_FAILURE"] and s.last_applied_as_of_ms == t - 2 * HOUR_MS
    assert health.assess(d, "P-104", POL)["applied_to_state"]                         # a live assessment applies, and is on record
    assert "ASSESSMENT_OVERDUE" not in health.asset_view(d, registry.get_asset(d, "P-104"), POL)["state"]


# -- latching-states-08, api-security-console-10/-11: instants are validated before anything is applied ----------------------
def test_a_range_ending_in_the_future_is_refused_before_any_step_is_applied(pumps):
    t = now_ms()
    with pytest.raises(health.AssessmentError, match="future"):
        health.assess_range(pumps, "P-101", POL, t - 3 * HOUR_MS, t + 2 * HOUR_MS, 30 * 60_000)
    assert _n_assessments(pumps, "P-101") == 0 and health.asset_state(pumps, "P-101") is None


def test_a_range_starting_before_the_first_reading_is_refused_whole(pumps):
    t = now_ms()
    _feed(pumps, "P-101", t - HOUR_MS)
    first = t - HOUR_MS - 39 * STEP
    with pytest.raises(health.AssessmentError, match="first reading"):
        health.assess_range(pumps, "P-101", POL, first - 30 * 60_000, t - HOUR_MS, 30 * 60_000)
    assert _n_assessments(pumps, "P-101") == 0
    out = health.assess_range(pumps, "P-101", POL, first, t - HOUR_MS, 30 * 60_000)
    assert out["assessments"] == out["applied"] == 14


def test_assess_range_resolves_a_tag_like_assess_does(pumps):
    t = now_ms() - 2 * HOUR_MS
    out = health.assess_range(pumps, "TAG-103", POL, t, t + 20 * 60_000, 10 * 60_000)
    assert out["asset_id"] == "P-103" and out["assessments"] == 3 and out["asset_state"] == ["DATA_QUALITY_FAILURE"]
    assert _n_assessments(pumps, "P-103") == 3


@pytest.mark.parametrize("as_of", ["0001-01-01T00:00:00Z", "1999-12-31T23:59:59Z"])
def test_implausibly_early_instants_are_refused(pumps, as_of):
    with pytest.raises(health.AssessmentError, match="2000-01-01"):
        health.assess(pumps, "P-101", POL, as_of_ms=parse_ts(as_of))
    with pytest.raises(health.AssessmentError, match="2000-01-01"):
        health.assess_range(pumps, "P-101", POL, parse_ts(as_of), parse_ts(as_of) + 2 * HOUR_MS, HOUR_MS)
    assert _n_assessments(pumps, "P-101") == 0
    a = health.assess(pumps, "P-101", POL, as_of_ms=parse_ts("2000-01-01T00:00:00Z"))   # the bound itself is valid, and harmless:
    assert a["applied_to_state"] and a["health_state"] == "DATA_QUALITY_FAILURE"        # no data then, so nothing is claimed
    assert health.assess(pumps, "P-101", POL)["applied_to_state"]                       # and the next live assessment still applies


def test_an_instant_before_the_assets_first_reading_is_refused(pumps):
    t = now_ms()
    _feed(pumps, "P-101", t)
    first = t - 39 * STEP
    with pytest.raises(health.AssessmentError, match="first reading"):
        health.assess(pumps, "P-101", POL, as_of_ms=first - health.MAX_FUTURE_SKEW_MS - 1)
    assert health.assess(pumps, "P-101", POL, as_of_ms=first - health.MAX_FUTURE_SKEW_MS)["applied_to_state"]


# -- re-review verify2 r04: ingest accepts readings up to the clock skew ahead of the server; so does the first-reading bound -----
def test_a_first_reading_slightly_ahead_of_the_server_clock_does_not_block_the_live_assessment(pumps):
    t = now_ms()
    recs = [{"asset": "P-101", "timestamp": iso(t + 3 * 60_000), "signal": s, "value": v, "unit": u}
            for s, v, u in (("bearing_temp", 60.0, "degC"), ("vibration_rms", 2.0, "mm/s"))]
    r = ingest.ingest_records(pumps, recs, source="new-gateway", actor="svc")         # a device clock 3 minutes fast
    assert (r.rows_accepted, r.rows_rejected) == (2, 0)
    a = health.assess(pumps, "P-101", POL)                                             # the scheduled default instant: now
    assert a["applied_to_state"] and a["health_state"] == "DATA_QUALITY_FAILURE"


def test_the_api_refuses_a_year_one_instant_with_422_and_stores_nothing(pumps):
    security.create_user(pumps, "svc", "Svc", "integration", actor="bootstrap")
    k = security.issue_api_key(pumps, "svc", actor="bootstrap")
    c = TestClient(api.create_app(pumps, POL, rate_limit=(1000, 1000.0)), raise_server_exceptions=False)
    r = c.post("/api/v1/assets/P-101/assess", json={"as_of": "0001-01-01T00:00:00Z"}, headers={"Authorization": f"Bearer {k}"})
    assert r.status_code == 422, r.text
    assert _n_assessments(pumps, "P-101") == 0 and health.asset_state(pumps, "P-101") is None


# -- wind-eval-migrations-06/-07: the harness gates like the service when given the policy; assessable exposure ------------------
def test_the_harness_applies_the_platform_data_checks_when_given_the_policy(bundle_dir):
    b = nbm.load(bundle_dir)
    g = sw.generate(sw.FleetSpec(n_turbines=1, days=18, seed=77, sensor_faults=(sw.SensorFault("WT01", "gearbox_oil_temp", "dropout", 12.0, 13.0),)))
    plain = nbm.evaluate(b, g.scada, [], step_points=6, baseline_days=7, stuck_min_run=WIND_POL.assessment["stuck_min_run"])
    gated = nbm.evaluate(b, g.scada, [], step_points=6, baseline_days=7, policy=WIND_POL.assessment)
    st = g.meta["start_ms"]
    inside = sum(1 for i in range(max(b.history_points - 1, 7 * 144), len(g.scada), 6)
                 if st + 12 * DAY_MS + 2 * HOUR_MS <= int(g.scada.ts_ms.iloc[i]) < st + 13 * DAY_MS)   # windows ending in the dropout
    assert inside > 10
    assert gated["per_turbine"]["WT01"]["data_quality"] >= plain["per_turbine"]["WT01"]["data_quality"] + inside
    gap = (st + 12 * DAY_MS + 2 * HOUR_MS, st + 13 * DAY_MS + 90 * STEP)     # windows the service refuses (stale, then > 10% missing)
    assert not [t for t in gated["per_turbine"]["WT01"]["alarm_ms"] if gap[0] <= t < gap[1]]
    # the dropout windows (counted above from their time stamps, not from the harness's counters) are not assessable exposure
    s = gated["summary"]
    assert s["healthy_assessable_turbine_years"] <= s["healthy_turbine_years"] - inside * 6 * 10 / (60 * 24 * 365.25) + 1e-4


def test_the_harness_uses_the_policys_stuck_limit_when_given_the_policy(bundle_dir, healthy_fleet):
    b = nbm.load(bundle_dir)
    g = healthy_fleet.scada[healthy_fleet.scada.turbine == "WT01"].reset_index(drop=True).iloc[: 10 * 144].copy()
    g.loc[g.index[-6:], "generator_bearing_temp"] = 40.0                   # constant for exactly the policy's limit (6 points)
    assert b.max_constant_run["generator_bearing_temp"] < 6
    kw = dict(step_points=1, baseline_days=7, only_last_frac=1 / len(g))     # one evaluation, at the last row
    assert nbm.evaluate(b, g, [], **kw)["per_turbine"]["WT01"]["data_quality"] == 1           # pre-registered default limit (5)
    assert nbm.evaluate(b, g, [], policy=WIND_POL.assessment, **kw)["per_turbine"]["WT01"]["data_quality"] == 0


def test_the_harness_reports_exposure_per_assessable_turbine_year(bundle_dir):
    b = nbm.load(bundle_dir)
    healthy = sw.generate(sw.FleetSpec(n_turbines=2, days=30, seed=11)).scada
    s = nbm.evaluate(b, healthy, [], step_points=6, baseline_days=7)["summary"]
    for k in ("alarm_rate_healthy", "healthy_assessments", "healthy_alarm_episodes", "healthy_turbine_years", "healthy_episodes_per_turbine_year",
              "assessable_share"):
        assert k in s                                                         # the calendar figures are kept
    assert 0 < s["healthy_assessable_turbine_years"] <= s["healthy_turbine_years"]
    assert s["healthy_assessable_turbine_years"] == pytest.approx(s["healthy_assessments"] * 6 * 10 / (60 * 24 * 365.25), abs=1e-4)
    assert s["healthy_episodes_per_assessable_turbine_year"] == pytest.approx(s["healthy_alarm_episodes"] / s["healthy_assessable_turbine_years"], abs=0.02)


# -- adapters/wind.py: the docstring must not claim a planned feature -------------------------------------------------------
def test_the_wind_adapter_does_not_claim_a_per_site_tag_mapping():
    assert "site mapping translates" not in wind.__doc__ and "PLANNED" in wind.__doc__ and "P12" in wind.__doc__
