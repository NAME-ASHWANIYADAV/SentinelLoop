"""Regression tests for the re-review of the Phase 9 fixes: decision engine and work-order lifecycle.

Each test names the re-review finding it covers (decision-lifecycle-*, latching-states-03/04, api-security-console-4/5).
They were written before the fixes and failed against them for the reason named in the finding.
"""
import itertools
import json
import uuid

import pytest
from fastapi.testclient import TestClient

from sentinelloop.app import api, db as dbmod, decision, health, policy as policymod, registry, security, states, workorders as wo
from sentinelloop.app.models import JobSpec
from sentinelloop.app.states import AssetState, Classification, HealthState as H, Thresholds
from sentinelloop.app.timeutil import DAY_MS, HOUR_MS, iso, now_ms, parse_ts
from conftest import ROOT
from test_app_foundation import KEY, pump, pump_type

POL = policymod.load(ROOT / "configs" / "platform.yaml")
CFG = decision.DecisionConfig()
SCHED = {"start": "2026-10-20T06:00:00Z", "end": "2026-10-20T12:00:00Z", "technicians": ["tech1"]}
INSPECTED = {"findings_code": "no_fault_found", "failure_confirmed": "no", "actions_taken": "inspected, nothing found", "downtime_hours": 1}
FOUND = {"findings_code": "degradation_found", "failure_confirmed": "no", "actions_taken": "bearing inspected, wear found", "downtime_hours": 1}
_SEQ = itertools.count(1)


def _type(**extra_jobs):
    t = pump_type()
    jobs = {**t.jobs, "instrument_check": JobSpec(duration_h=1.0, skill="instrument"), "desk_review": JobSpec(duration_h=0.5, skill="reliability")}
    return pump_type(jobs={**jobs, **extra_jobs})


def _plant(path, asset_type=None):
    d = dbmod.Database(path, audit_key=KEY, audit_key_id="test")
    d.migrate()
    registry.create_site(d, "site1", "Plant 1", "UTC", actor="admin")
    registry.create_asset_type(d, asset_type or _type(), actor="admin")
    for aid, crit in (("P-101", "A"), ("P-102", "A"), ("P-103", "C")):
        registry.create_asset(d, pump(aid, criticality=crit), actor="admin")
    return d


@pytest.fixture
def plant(tmp_path):
    return _plant(tmp_path / "rr.db")


def advance(d, asset, state, at_ms=None):
    """Apply one classification to the asset's stored state (what health.assess does), at wall-clock time by default."""
    prev = health.asset_state(d, asset) or AssetState()
    s = states.advance(prev, Classification(state, ["test"]), Thresholds(), now_ms=at_ms if at_ms is not None else now_ms())
    with d.tx() as c:
        health._store_state(c, asset, s, None)
    return s


def assess(d, asset, state, reasons=None, risk=None, rul=None, anomaly=None):
    """Store an applied assessment record; the decision engine reads the latest one."""
    aid = f"A-{uuid.uuid4().hex[:16]}"
    lo, pt, up = rul or (None, None, None)
    with d.tx() as c:
        c.execute("INSERT INTO assessments (assessment_id, asset_id, as_of_ms, created_at, model_id, health_state, reasons_json, data_quality_json, "
                  "applicability_json, risk_json, top_deviations_json, inputs_json, policy_json, rul_lower_hours, rul_point_hours, rul_upper_hours, "
                  "interval_level, anomaly_score) VALUES (?,?,?,?,NULL,?,?,'{}','{}',?,'[]','{}','{}',?,?,?,?,?)",
                  (aid, asset, now_ms() + next(_SEQ), iso(now_ms()), state, json.dumps(reasons or ["test"]), json.dumps(risk or {}), lo, pt, up,
                   0.9 if rul else None, anomaly))
    return aid


def gen(d, cfg=CFG, asset="P-101", now=None):
    return [x for x in decision.generate(d, cfg, actor="sys", now_ms=now) if x.get("asset_id") == asset]


def orders(d, asset="P-101"):
    return [(o["wo_id"], o["job_type"], o["priority_class"], o["state"]) for o in wo.list_orders(d, asset_id=asset)]


def to_progress(d, w):
    wo.transition(d, w, "approve", actor="pat", role="planner")
    wo.transition(d, w, "schedule", actor="pat", role="planner", data=SCHED)
    wo.transition(d, w, "start", actor="tom", role="technician")


def backdate(d, w, ms=60_000):
    """The order was raised a minute earlier: 'raised before the latch began' then does not depend on clock resolution."""
    with d.tx() as c:
        r = c.execute("SELECT created_at FROM work_orders WHERE wo_id = ?", (w,)).fetchone()
        c.execute("UPDATE work_orders SET created_at = ? WHERE wo_id = ?", (iso(parse_ts(r["created_at"]) - ms), w))


def errors_audited(d):
    with d.connect() as c:
        return c.execute("SELECT COUNT(*) FROM audit_events WHERE action = 'decision.error'").fetchone()[0]


# -- open-order matching (decision-lifecycle-01, latching-states-04) ----------------------------------------------------
def test_a_desk_review_never_stands_in_for_an_urgent_job(plant):
    """decision-lifecycle-01 (A): an out-of-scope desk review was escalated to P1 in place of the urgent job."""
    advance(plant, "P-101", H.MODEL_OUT_OF_SCOPE)
    assess(plant, "P-101", "MODEL_OUT_OF_SCOPE")
    assert [(x["action"], x["priority_class"]) for x in gen(plant)] == [("created", "P3")]
    advance(plant, "P-101", H.URGENT_REVIEW)
    assess(plant, "P-101", "URGENT_REVIEW")
    out = gen(plant)
    assert [(x["action"], x["priority_class"]) for x in out] == [("created", "P1")], out
    assert wo.get(plant, out[0]["wo_id"])["job_type"] == "repair"
    assess(plant, "P-101", "URGENT_REVIEW")
    assert [x["action"] for x in gen(plant)] == ["unchanged"]                         # no duplicate for the same latched condition
    assert sorted((j, pc, s) for _, j, pc, s in orders(plant)) == [("desk_review", "P3", "PENDING_APPROVAL"), ("repair", "P1", "PENDING_APPROVAL")]


@pytest.mark.parametrize("latch_state,job,pc,defer", [(H.INSPECTION_RECOMMENDED, "inspect", "P2", True), (H.URGENT_REVIEW, "repair", "P1", True),
                                                       (H.URGENT_REVIEW, "repair", "P1", False)])
def test_an_instrument_check_never_covers_a_new_equipment_condition(plant, latch_state, job, pc, defer):
    """decision-lifecycle-01 (B, D) and latching-states-04 (b): an open or deferred instrument check 'covered' a later
    inspection or urgent condition, or was escalated to P1 in its place."""
    advance(plant, "P-101", H.DATA_QUALITY_FAILURE)
    assess(plant, "P-101", "DATA_QUALITY_FAILURE", reasons=["stuck_signal: bearing_temp"])
    w = gen(plant)[0]["wo_id"]
    if defer:
        wo.transition(plant, w, "defer", actor="pat", role="planner", reason="sensor replacement booked", data={"until": iso(now_ms() + 14 * DAY_MS)})
    for _ in range(3):                                   # the data recover (dq_clear_after = 2) and the condition latches
        advance(plant, "P-101", latch_state)
    assess(plant, "P-101", latch_state.value)
    out = gen(plant)
    assert [(x["action"], x["priority_class"]) for x in out] == [("created", pc)], out
    assert wo.get(plant, out[0]["wo_id"])["job_type"] == job
    check = wo.get(plant, w)
    assert check["job_type"] == "instrument_check" and check["priority_class"] == "P2"           # left as it was
    assert check["state"] == ("DEFERRED" if defer else "PENDING_APPROVAL")
    assert "HUMAN_APPROVAL_REQUIRED" in health.asset_state(plant, "P-101").labels()
    assess(plant, "P-101", latch_state.value)
    assert [x["action"] for x in gen(plant)] == ["unchanged"]


def test_an_inspection_escalated_to_p1_for_an_urgent_latch_clears_it_when_done(plant):
    """latching-states-04 (a): the escalated order predates the urgent latch, so its completion kept the latch."""
    advance(plant, "P-101", H.INSPECTION_RECOMMENDED)
    assess(plant, "P-101", "INSPECTION_RECOMMENDED")
    w = gen(plant)[0]["wo_id"]
    backdate(plant, w)
    advance(plant, "P-101", H.URGENT_REVIEW)
    assess(plant, "P-101", "URGENT_REVIEW")
    assert [(x["action"], x["wo_id"], x["priority_class"]) for x in gen(plant)] == [("escalated", w, "P1")]
    assess(plant, "P-101", "URGENT_REVIEW")
    assert [x["action"] for x in gen(plant)] == ["unchanged"] and len(orders(plant)) == 1
    to_progress(plant, w)
    done = wo.complete(plant, w, actor="tom", role="technician", outcome=FOUND)
    assert "latch_kept" not in done["outcome"]["flags"]
    assert health.asset_state(plant, "P-101").latched_risk == "NONE"


def test_an_old_order_left_open_after_a_dismissal_is_linked_to_the_new_latch(plant):
    """latching-states-04 (c): an old P1 repair 'covered' a re-latched inspection, yet completing it kept the latch."""
    advance(plant, "P-101", H.URGENT_REVIEW)
    assess(plant, "P-101", "URGENT_REVIEW")
    w = gen(plant)[0]["wo_id"]
    backdate(plant, w)
    health.clear_latched_risk(plant, "P-101", "dismissed", actor="rea", role="reliability_engineer", reason="vibration route says sensor drift")
    advance(plant, "P-101", H.INSPECTION_RECOMMENDED)
    assess(plant, "P-101", "INSPECTION_RECOMMENDED")
    out = gen(plant)
    assert [(x["action"], x["wo_id"]) for x in out] == [("linked", w)], out
    assert len(orders(plant)) == 1 and wo.get(plant, w)["priority_class"] == "P1"            # the system never lowers a class
    assess(plant, "P-101", "INSPECTION_RECOMMENDED")
    assert [x["action"] for x in gen(plant)] == ["unchanged"]
    to_progress(plant, w)
    done = wo.complete(plant, w, actor="tom", role="technician", outcome={**FOUND, "parts_used": {"bearing_kit": 1}})
    assert "latch_kept" not in done["outcome"]["flags"] and health.asset_state(plant, "P-101").latched_risk == "NONE"


def test_work_in_progress_from_before_the_latch_does_not_stand_in_for_it(plant):
    """latching-states-04: an order that cannot clear the current latch never 'covers' it; the latch gets its own order."""
    advance(plant, "P-101", H.URGENT_REVIEW)
    assess(plant, "P-101", "URGENT_REVIEW")
    w = gen(plant)[0]["wo_id"]
    to_progress(plant, w)
    backdate(plant, w)
    health.clear_latched_risk(plant, "P-101", "dismissed", actor="rea", role="reliability_engineer", reason="vibration route says sensor drift")
    advance(plant, "P-101", H.INSPECTION_RECOMMENDED)
    assess(plant, "P-101", "INSPECTION_RECOMMENDED")
    out = gen(plant)
    assert [(x["action"], x["priority_class"]) for x in out] == [("created", "P2")], out
    assert "in progress" in wo.get(plant, out[0]["wo_id"])["explanation"]["why"]


def test_only_a_system_escalation_links_an_older_order_to_the_current_latch(plant):
    """Guard on the linking rule: a person re-prioritising an order raised before the latch does not make it clear it."""
    o = wo.create(plant, asset_id="P-101", job_type="inspect", priority_class="P2", title="routine", origin="manual", actor="pat", role="planner",
                  idempotency_key="m1")
    wo.transition(plant, o["wo_id"], "submit", actor="pat", role="planner")
    backdate(plant, o["wo_id"])
    advance(plant, "P-101", H.URGENT_REVIEW)
    wo.reprioritise(plant, o["wo_id"], "P1", None, None, {}, actor="pat", role="planner", reason="bearing noise reported")
    to_progress(plant, o["wo_id"])
    done = wo.complete(plant, o["wo_id"], actor="tom", role="technician", outcome=FOUND)
    assert "latch_kept" in done["outcome"]["flags"] and health.asset_state(plant, "P-101").latched_risk == "URGENT"


def test_a_deferred_order_escalated_by_a_new_latch_comes_back_for_approval(plant):
    """decision-lifecycle-10 (B): reported 'escalated' while the order stayed DEFERRED, with no approval flag."""
    o = wo.create(plant, asset_id="P-103", job_type="inspect", priority_class="P3", title="routine", origin="manual", actor="pat", role="planner",
                  idempotency_key="m2")
    wo.transition(plant, o["wo_id"], "submit", actor="pat", role="planner")
    wo.transition(plant, o["wo_id"], "defer", actor="pat", role="planner", reason="crane", data={"until": iso(now_ms() + 60 * DAY_MS)})
    backdate(plant, o["wo_id"])
    advance(plant, "P-103", H.INSPECTION_RECOMMENDED)
    assess(plant, "P-103", "INSPECTION_RECOMMENDED")
    out = gen(plant, asset="P-103")
    assert [(x["action"], x["wo_id"], x["priority_class"]) for x in out] == [("escalated", o["wo_id"], "P2")]
    assert wo.get(plant, o["wo_id"])["state"] == "PENDING_APPROVAL"
    assert "HUMAN_APPROVAL_REQUIRED" in health.asset_state(plant, "P-103").labels()


# -- configured job names (decision-lifecycle-02) ---------------------------------------------------------------------
def test_a_renamed_data_job_never_clears_a_latched_inspection(tmp_path):
    """decision-lifecycle-02: with data_job renamed, a completed sensor check cleared a latched INSPECTION."""
    t = pump_type()
    d = _plant(tmp_path / "dj.db", asset_type=pump_type(jobs={**t.jobs, "sensor_check": JobSpec(duration_h=1.0, skill="instrument")}))
    cfg = decision.load_config_text("data_job: sensor_check\n")
    advance(d, "P-101", H.INSPECTION_RECOMMENDED)
    advance(d, "P-101", H.DATA_QUALITY_FAILURE)
    assess(d, "P-101", "DATA_QUALITY_FAILURE", reasons=["stuck_signal: bearing_temp"])
    gen(d, cfg)
    w = [o["wo_id"] for o in wo.list_orders(d, asset_id="P-101") if o["job_type"] == "sensor_check"][0]
    to_progress(d, w)
    done = wo.complete(d, w, actor="tom", role="technician", outcome={**INSPECTED, "actions_taken": "sensor reseated, reading plausible"})
    assert "latch_kept" in done["outcome"]["flags"]
    assert health.asset_state(d, "P-101").latched_risk == "INSPECTION"


def test_completion_honours_the_sites_non_clearing_jobs_for_manual_orders(tmp_path):
    """decision-lifecycle-02: the clearing rule follows the configured data and review jobs, not only the shipped names."""
    t = pump_type()
    d = _plant(tmp_path / "dj2.db", asset_type=pump_type(jobs={**t.jobs, "sensor_check": JobSpec(duration_h=1.0, skill="instrument")}))
    advance(d, "P-101", H.URGENT_REVIEW, at_ms=now_ms() - 60_000)
    o = wo.create(d, asset_id="P-101", job_type="sensor_check", priority_class="P2", title="sensor", origin="manual", actor="pat", role="planner",
                  idempotency_key="m3")
    wo.transition(d, o["wo_id"], "submit", actor="pat", role="planner")
    to_progress(d, o["wo_id"])
    cfg = decision.load_config_text("data_job: sensor_check\n")
    done = wo.complete(d, o["wo_id"], actor="tom", role="technician", outcome=INSPECTED, non_clearing_jobs=decision.non_clearing_jobs(cfg))
    assert "latch_kept" in done["outcome"]["flags"] and health.asset_state(d, "P-101").latched_risk == "URGENT"


@pytest.mark.parametrize("text", ["urgent_job: desk_review\n", "urgent_job: instrument_check\n", "inspection_job: instrument_check\n",
                                  "inspection_job: desk_review\n", "data_job: inspect\n", "review_job: repair\n", "data_job: sensor_check\nurgent_job: sensor_check\n",
                                  "review_job: walkdown\ninspection_job: walkdown\n", "inspection_job: ''\n", "urgent_job: 5\n", "data_job: null\n"])
def test_job_names_that_would_turn_an_equipment_job_into_a_check_are_refused(text):
    """decision-lifecycle-02: urgent_job: desk_review gave a P1 desk review; inspection_job: instrument_check meant no inspection."""
    with pytest.raises(ValueError):
        decision.load_config_text(text)


# -- decision config validation (decision-lifecycle-04, -05, -03) -------------------------------------------------------
BAD_CONFIGS = [
    "default_due_h: {P1: 12}\n", "default_due_h: {}\n", "reject_suppress_h: {P1: 12}\n", "default_due_h: null\n", "default_due_h: [24, 168, 720]\n",
    "default_due_h: {P1: 24, P2: 168, P3: 720, P4: 1}\n", "default_due_h: {P1: 0, P2: 168, P3: 720}\n", "default_due_h: {P1: -1, P2: 168, P3: 720}\n",
    "default_due_h: {P1: '24', P2: 168, P3: 720}\n", "default_due_h: {P1: true, P2: 168, P3: 720}\n", "default_due_h: {P1: .inf, P2: 168, P3: 720}\n",
    "default_due_h: {P1: .nan, P2: 168, P3: 720}\n", "default_due_h: {P1: 10000000, P2: 168, P3: 720}\n",
    "reject_suppress_h: {P1: .inf, P2: 168, P3: 720}\n", "reject_suppress_h: {P1: -1, P2: 168, P3: 720}\n", "reject_suppress_h: {P1: 87600, P2: 168, P3: 720}\n",
    "reject_suppress_h: {P1: null, P2: 168, P3: 720}\n",
    "p_safety: 5\n", "p_safety: .nan\n", "p_safety: true\n", "p_safety: 1\n", "p_safety: -0.1\n", "p_safety: '0.05'\n", "p_safety: null\n",
    "p_accept: 1.5\n", "p_accept: .nan\n", "p_accept: 1.0\n", "p_accept: [1]\n", "p_accept: .inf\n",
    "labour_cost_per_h: -1\n", "labour_cost_per_h: .nan\n", "downtime_cost_per_h: .inf\n", "downtime_cost_per_h: true\n", "downtime_cost_per_h: null\n",
]


@pytest.mark.parametrize("text", BAD_CONFIGS)
def test_unsafe_decision_config_values_are_refused_at_load(text):
    """decision-lifecycle-04/05 (and -03's unbounded window): partial P-key maps raised KeyError at use; NaN, inf, booleans,
    strings and probabilities >= 1 were accepted and silently disabled the safety rule or moved due dates."""
    with pytest.raises(ValueError):
        decision.load_config_text(text)


def test_valid_decision_configs_still_load():
    cfg = decision.load_config((ROOT / "configs" / "decision.example.yaml"))
    assert cfg.site_configured and cfg.default_due_h == {"P1": 24, "P2": 168, "P3": 720}
    cfg = decision.load_config_text("default_due_h: {P1: 12, P2: 120.5, P3: 720}\nreject_suppress_h: {P1: 0, P2: 0, P3: 0}\np_accept: 0.1\np_safety: 0\n"
                                    "labour_cost_per_h: 0\ndowntime_cost_per_h: 0.004\nreview_job: walkdown\n")
    assert cfg.default_due_h["P2"] == 120.5 and cfg.reject_suppress_h["P1"] == 0 and cfg.p_accept == 0.1 and cfg.review_job == "walkdown"
    assert decision.load_config_text("").site_configured


# -- a data failure hiding a latched inspection (decision-lifecycle-06, latching-states-03) -----------------------------
@pytest.mark.parametrize("asset,reasons,expected", [
    ("P-101", ["stuck_signal: bearing_temp"], [("inspect", "P2"), ("instrument_check", "P2")]),
    ("P-103", ["stuck_signal: bearing_temp"], [("inspect", "P2"), ("instrument_check", "P3")]),
    ("P-101", ["data_delivery_delay: newest reading 12.0 h old"], [("inspect", "P2")]),
    ("P-103", ["data_delivery_delay: newest reading 12.0 h old"], [("inspect", "P2")])])
def test_a_latched_inspection_hidden_by_a_data_failure_gets_its_inspection_order(plant, asset, reasons, expected):
    """decision-lifecycle-06, latching-states-03: only an instrument check (or nothing for a feed delay) was raised."""
    advance(plant, asset, H.INSPECTION_RECOMMENDED)
    advance(plant, asset, H.DATA_QUALITY_FAILURE)
    assess(plant, asset, "DATA_QUALITY_FAILURE", reasons=reasons)
    assert "INSPECTION_PENDING" in health.asset_state(plant, asset).labels()
    out = gen(plant, asset=asset)
    assert [x["action"] for x in out] == ["created"] * len(expected), out
    assert sorted((j, pc) for _, j, pc, _ in orders(plant, asset)) == expected
    assert [x["action"] for x in gen(plant, asset=asset)] == ["unchanged"] * len(expected)


# -- rejection suppression (decision-lifecycle-08, -09, -03) -------------------------------------------------------------
def test_a_rejected_separate_p1_during_work_in_progress_stays_suppressed(plant):
    """decision-lifecycle-08 (and -07 B): the separate-P1 path skipped suppression, and re-running on the same assessment
    after the rejection reported 'error'."""
    advance(plant, "P-101", H.INSPECTION_RECOMMENDED)
    assess(plant, "P-101", "INSPECTION_RECOMMENDED")
    w = gen(plant)[0]["wo_id"]
    to_progress(plant, w)
    advance(plant, "P-101", H.URGENT_REVIEW)
    assess(plant, "P-101", "URGENT_REVIEW")
    p1 = gen(plant)
    assert [(x["action"], x["priority_class"]) for x in p1] == [("created", "P1")]
    wo.transition(plant, p1[0]["wo_id"], "reject", actor="pat", role="planner", reason="the crew on site is already covering the bearing; known issue")
    assert [x["action"] for x in gen(plant)] == ["already_decided"]
    for _ in range(2):
        assess(plant, "P-101", "URGENT_REVIEW")                              # the next assessments, same condition
        again = gen(plant)
        assert [x["action"] for x in again] == ["suppressed"] and "known issue" in again[0]["note"], again
    assert sorted(s for *_, s in orders(plant)) == ["IN_PROGRESS", "REJECTED"] and errors_audited(plant) == 0


def test_a_rejection_holds_for_the_latched_condition_whatever_the_displayed_state(plant):
    """decision-lifecycle-09: a scope or model flip re-raised a rejected inspection, and flipping back raised it again."""
    advance(plant, "P-101", H.INSPECTION_RECOMMENDED)
    assess(plant, "P-101", "INSPECTION_RECOMMENDED")
    w = gen(plant)[0]["wo_id"]
    wo.transition(plant, w, "reject", actor="pat", role="planner", reason="known issue: exchange booked next month")
    for st in (H.INSPECTION_RECOMMENDED, H.MODEL_OUT_OF_SCOPE, H.INSPECTION_RECOMMENDED, H.MODEL_UNAVAILABLE, H.INSPECTION_RECOMMENDED):
        advance(plant, "P-101", st)
        assess(plant, "P-101", st.value)
        out = gen(plant)
        assert [x["action"] for x in out] == ["suppressed"], (st, out)
    assert len(orders(plant)) == 1


@pytest.mark.parametrize("clear_by", ["dismissal", "inspection"])
def test_a_rejection_does_not_suppress_a_new_latch_episode(plant, clear_by):
    """decision-lifecycle-03 / rule 5: a P1 rejected before a dismissal or a completed inspection suppressed a NEW urgent latch."""
    advance(plant, "P-101", H.URGENT_REVIEW)
    assess(plant, "P-101", "URGENT_REVIEW")
    first = gen(plant)[0]["wo_id"]
    wo.transition(plant, first, "reject", actor="pat", role="planner", reason="sensor artefact, vibration route says fine")
    backdate(plant, first)
    if clear_by == "dismissal":
        health.clear_latched_risk(plant, "P-101", "dismissed", actor="rea", role="reliability_engineer", reason="sensor artefact confirmed")
    else:
        m = wo.create(plant, asset_id="P-101", job_type="inspect", priority_class="P1", title="manual", origin="manual", actor="pat", role="planner",
                      idempotency_key="m4")
        wo.transition(plant, m["wo_id"], "submit", actor="pat", role="planner")
        to_progress(plant, m["wo_id"])
        wo.complete(plant, m["wo_id"], actor="tom", role="technician", outcome=INSPECTED)
    assert health.asset_state(plant, "P-101").latched_risk == "NONE"
    advance(plant, "P-101", H.NORMAL_MONITORING)
    assess(plant, "P-101", "NORMAL_MONITORING")
    advance(plant, "P-101", H.URGENT_REVIEW)                                   # a genuinely new urgent condition
    assess(plant, "P-101", "URGENT_REVIEW")
    out = gen(plant, now=now_ms() + 2 * HOUR_MS)
    assert [(x["action"], x["priority_class"]) for x in out] == [("created", "P1")], out


# -- re-prioritisation (decision-lifecycle-12, api-security-console-4) ----------------------------------------------------
def test_an_escalation_never_postpones_an_earlier_due_date(plant):
    """decision-lifecycle-12 (A): a system escalation moved a manual 'check noise today' order a week later."""
    o = wo.create(plant, asset_id="P-101", job_type="inspect", priority_class="P3", title="check noise today", origin="manual", actor="pat",
                  role="planner", idempotency_key="m5", due_by=iso(now_ms() + 2 * HOUR_MS))
    wo.transition(plant, o["wo_id"], "submit", actor="pat", role="planner")
    due = wo.get(plant, o["wo_id"])["due_by_ms"]
    advance(plant, "P-101", H.INSPECTION_RECOMMENDED)
    assess(plant, "P-101", "INSPECTION_RECOMMENDED", anomaly=1.6)              # anomaly-only: the policy default would be 168 h
    out = gen(plant)
    assert [(x["action"], x["priority_class"]) for x in out] == [("escalated", "P2")]
    after = wo.get(plant, o["wo_id"])
    assert after["due_by_ms"] == due and after["explanation"]["due_by"] == after["due_by"]
    # the system path through workorders.reprioritise directly
    wo.reprioritise(plant, o["wo_id"], "P2", None, due + 7 * DAY_MS, {}, actor="sys", role="system", reason="later rule")
    assert wo.get(plant, o["wo_id"])["due_by_ms"] == due


def _api(d, cfg=None):
    keys = {}
    for uid, role in (("pat", "planner"), ("tom", "technician"), ("vic", "viewer")):
        security.create_user(d, uid, uid.title(), role, actor="bootstrap")
        keys[role] = {"Authorization": f"Bearer {security.issue_api_key(d, uid, actor='bootstrap')}"}
    return TestClient(api.create_app(d, POL, decision_cfg=cfg, rate_limit=(10000, 1000.0))), keys


def test_a_manual_reprioritisation_keeps_the_score_and_records_only_what_changed(plant):
    """decision-lifecycle-12 (B, C), api-security-console-4: the route wiped the risk score, left the explanation's old due
    date, and recorded the nested reactivation as role 'system'."""
    http, keys = _api(plant)
    advance(plant, "P-101", H.URGENT_REVIEW)
    assess(plant, "P-101", "URGENT_REVIEW", anomaly=4.0)
    w = gen(plant)[0]["wo_id"]
    before = wo.get(plant, w)
    assert before["priority_score"] is not None
    new_due = before["due_by_ms"] - 4 * HOUR_MS
    r = http.post(f"/api/v1/work-orders/{w}/reprioritise", json={"priority_class": "P1", "reason": "ops wants it before the shift change",
                                                                 "due_by": iso(new_due)}, headers=keys["planner"])
    assert r.status_code == 200, r.text
    after = wo.get(plant, w)
    assert after["priority_score"] == before["priority_score"] and after["due_by_ms"] == new_due
    assert after["explanation"]["due_by"] == after["due_by"] and "shift change" in after["explanation"]["due_by_rule"]
    ev = [h for h in wo.history(plant, w) if h["action"] == "reprioritise"][-1]
    assert new_due in ev["data"]["to"].values() and "priority_score" not in json.dumps(ev["data"])       # only what changed
    # a planner escalating a deferred order: the reactivation is the planner's, not the system's
    o = wo.create(plant, asset_id="P-102", job_type="replace", priority_class="P3", title="t", origin="manual", actor="pat", role="planner",
                  idempotency_key="m6")
    wo.transition(plant, o["wo_id"], "submit", actor="pat", role="planner")
    wo.transition(plant, o["wo_id"], "defer", actor="pat", role="planner", reason="later", data={"until": iso(now_ms() + 30 * DAY_MS)})
    r = http.post(f"/api/v1/work-orders/{o['wo_id']}/reprioritise", json={"priority_class": "P1", "reason": "leak seen"}, headers=keys["planner"])
    assert r.status_code == 200 and r.json()["state"] == "PENDING_APPROVAL"
    assert [(e["action"], e["actor"], e["role"]) for e in wo.history(plant, o["wo_id"])][-1] == ("reactivate", "pat", "planner")


def test_reprioritise_can_refuse_a_stale_version(plant):
    """api-security-console-4: re-prioritisation had no optimistic-concurrency check (the route can now pass one)."""
    o = wo.create(plant, asset_id="P-101", job_type="inspect", priority_class="P3", title="t", origin="manual", actor="pat", role="planner",
                  idempotency_key="m8")
    o = wo.transition(plant, o["wo_id"], "submit", actor="pat", role="planner")
    wo.reprioritise(plant, o["wo_id"], "P2", None, None, {}, actor="pat", role="planner", reason="first", expected_version=o["version"])
    with pytest.raises(wo.ConcurrencyConflict):
        wo.reprioritise(plant, o["wo_id"], "P1", None, None, {}, actor="rea", role="reliability_engineer", reason="second", expected_version=o["version"])
    assert wo.get(plant, o["wo_id"])["priority_class"] == "P2"


# -- work in progress (decision-lifecycle-07) ----------------------------------------------------------------------------
def test_work_in_progress_with_an_earlier_due_date_is_unchanged_not_an_error(plant):
    """decision-lifecycle-07 (A): the same class with an earlier due date reached reprioritise on an IN_PROGRESS order."""
    advance(plant, "P-101", H.INSPECTION_RECOMMENDED)
    assess(plant, "P-101", "INSPECTION_RECOMMENDED", risk={"p_fail_decision_horizon": 0.15, "decision_horizon_hours": 60}, rul=(100, 200, 300))
    w = gen(plant)[0]["wo_id"]
    to_progress(plant, w)
    assess(plant, "P-101", "INSPECTION_RECOMMENDED", risk={"p_fail_decision_horizon": 0.2, "decision_horizon_hours": 60}, rul=(50, 100, 150))
    for _ in range(2):
        out = gen(plant)
        assert [(x["action"], x["wo_id"]) for x in out] == [("unchanged", w)], out
    assert errors_audited(plant) == 0


# -- fleet isolation (decision-lifecycle-11) -------------------------------------------------------------------------------
def test_one_failing_reactivation_does_not_abort_the_fleet_run(plant):
    """decision-lifecycle-11: a reactivation failure (here an Idempotency-Key that pre-empts the system's) aborted generate."""
    t = now_ms()
    o = wo.create(plant, asset_id="P-101", job_type="inspect", priority_class="P3", title="routine", origin="manual", actor="pat", role="planner",
                  idempotency_key="m7")
    wo.transition(plant, o["wo_id"], "submit", actor="pat", role="planner")
    wo.transition(plant, o["wo_id"], "defer", actor="pat", role="planner", reason="later", data={"until": iso(t - 1000)},
                  idempotency_key=f"reactivate:{o['wo_id']}:{t // 60000}")
    advance(plant, "P-102", H.URGENT_REVIEW)
    assess(plant, "P-102", "URGENT_REVIEW")
    out = decision.generate(plant, CFG, actor="sys", now_ms=t)
    assert any(x["asset_id"] == "P-101" and x["action"] == "error" and x.get("wo_id") == o["wo_id"] for x in out), out
    assert [(x["action"], x["priority_class"]) for x in out if x["asset_id"] == "P-102"] == [("created", "P1")]
    assert errors_audited(plant) == 1


# -- audit of latch changes (api-security-console-5) ----------------------------------------------------------------------
def test_latch_changes_on_completion_are_in_the_assets_audit_history(plant):
    """api-security-console-5: asset_state.* events from a completion were filed as entity 'work_order' with the asset id."""
    http, keys = _api(plant)
    out = {}
    for asset, job in (("P-101", "inspect"), ("P-102", "instrument_check")):
        advance(plant, asset, H.URGENT_REVIEW, at_ms=now_ms() - 60_000)
        o = wo.create(plant, asset_id=asset, job_type=job, priority_class="P1", title=f"{job} {asset}", origin="manual", actor="pat", role="planner",
                      idempotency_key=f"a-{asset}")
        wo.transition(plant, o["wo_id"], "submit", actor="pat", role="planner")
        to_progress(plant, o["wo_id"])
        r = http.post(f"/api/v1/work-orders/{o['wo_id']}/complete", json={"outcome": INSPECTED}, headers=keys["technician"])
        assert r.status_code == 200, r.text
        rows = http.get(f"/api/v1/audit/asset/{asset}", headers=keys["viewer"]).json()
        latch_events = [x for x in rows if x["action"].startswith("asset_state.")]
        assert latch_events and latch_events[-1]["payload"]["wo_id"] == o["wo_id"], rows
        out[asset] = latch_events[-1]["action"]
    assert out["P-101"] == "asset_state.maintenance_completed" and health.asset_state(plant, "P-101").latched_risk == "NONE"
    assert out["P-102"] == "asset_state.latch_kept" and health.asset_state(plant, "P-102").latched_risk == "URGENT"


# -- second re-review of the fixes (verify2: still broken and regressions) ------------------------------------------------
def test_a_renamed_data_job_never_clears_a_latch_through_the_api(tmp_path):
    """Still broken (decision-lifecycle-02): the API complete route passes no non_clearing_jobs, so a manual sensor check
    (the site's data job) completed through it cleared an URGENT latch."""
    t = pump_type()
    d = _plant(tmp_path / "dj3.db", asset_type=pump_type(jobs={**t.jobs, "sensor_check": JobSpec(duration_h=1.0, skill="instrument")}))
    cfg = decision.load_config_text("data_job: sensor_check\n")
    advance(d, "P-102", H.DATA_QUALITY_FAILURE)                                # the engine has run under the site's config
    assess(d, "P-102", "DATA_QUALITY_FAILURE", reasons=["stuck_signal: bearing_temp"])
    assert [x["action"] for x in gen(d, cfg, asset="P-102")] == ["created"]
    http, keys = _api(d, cfg)
    advance(d, "P-101", H.URGENT_REVIEW, at_ms=now_ms() - 60_000)
    o = wo.create(d, asset_id="P-101", job_type="sensor_check", priority_class="P2", title="sensor", origin="manual", actor="pat", role="planner",
                  idempotency_key="m9")
    wo.transition(d, o["wo_id"], "submit", actor="pat", role="planner")
    to_progress(d, o["wo_id"])
    r = http.post(f"/api/v1/work-orders/{o['wo_id']}/complete", json={"outcome": INSPECTED}, headers=keys["technician"])
    assert r.status_code == 200, r.text
    assert "latch_kept" in r.json()["outcome"]["flags"] and health.asset_state(d, "P-101").latched_risk == "URGENT"


def test_a_rejected_stand_in_holds_for_the_latched_condition(plant):
    """Still broken (decision-lifecycle-09/-08, G1): the inspection escalated to P1 for an URGENT latch was rejected, and the
    next run on the same assessment raised a P1 repair at once (suppression looked only at system orders of the same job)."""
    advance(plant, "P-101", H.INSPECTION_RECOMMENDED)
    assess(plant, "P-101", "INSPECTION_RECOMMENDED")
    w = gen(plant)[0]["wo_id"]
    backdate(plant, w)
    advance(plant, "P-101", H.URGENT_REVIEW)
    assess(plant, "P-101", "URGENT_REVIEW")
    assert [(x["action"], x["wo_id"], x["priority_class"]) for x in gen(plant)] == [("escalated", w, "P1")]
    wo.transition(plant, w, "reject", actor="pat", role="planner", reason="known issue: vibration from the coupling, exchange booked; not urgent")
    assert [x["action"] for x in gen(plant)] == ["suppressed"]                 # the same assessment
    assess(plant, "P-101", "URGENT_REVIEW")
    again = gen(plant)
    assert [x["action"] for x in again] == ["suppressed"] and "coupling" in again[0]["note"], again
    assert len(orders(plant)) == 1


def test_a_rejected_order_the_engine_brought_back_holds_for_the_latched_condition(plant):
    """Regression (G6): a deferred manual inspection linked to a new latch came back for approval; the planner rejected it,
    and the next run raised a system inspection at once."""
    o = wo.create(plant, asset_id="P-101", job_type="inspect", priority_class="P3", title="routine", origin="manual", actor="pat", role="planner",
                  idempotency_key="g6")
    wo.transition(plant, o["wo_id"], "submit", actor="pat", role="planner")
    wo.transition(plant, o["wo_id"], "defer", actor="pat", role="planner", reason="crane", data={"until": iso(now_ms() + 30 * DAY_MS)})
    backdate(plant, o["wo_id"])
    advance(plant, "P-101", H.INSPECTION_RECOMMENDED)
    assess(plant, "P-101", "INSPECTION_RECOMMENDED")
    assert [(x["action"], x["wo_id"]) for x in gen(plant)] == [("escalated", o["wo_id"])]
    assert wo.get(plant, o["wo_id"])["state"] == "PENDING_APPROVAL"
    wo.transition(plant, o["wo_id"], "reject", actor="pat", role="planner", reason="known issue: exchange booked next month; do not inspect")
    assert [x["action"] for x in gen(plant)] == ["suppressed"]
    assess(plant, "P-101", "INSPECTION_RECOMMENDED")
    assert [x["action"] for x in gen(plant)] == ["suppressed"]
    assert len(orders(plant)) == 1


def _unknown_start_urgent(d):
    with d.tx() as c:                                          # a latch recorded before its start was (an upgraded database)
        health._store_state(c, "P-101", AssetState(effective=H.URGENT_REVIEW, latched_risk="URGENT", latched_since_ms=None,
                                                   last_health=H.URGENT_REVIEW), None)


def test_a_rejection_still_suppresses_a_latch_whose_start_is_unknown(plant):
    """Regression (g3 c): with latched_since_ms unknown, suppression was off and a rejected P1 came back on every assessment.
    A clearing event after the rejection still starts a new episode."""
    _unknown_start_urgent(plant)
    assess(plant, "P-101", "URGENT_REVIEW")
    out = gen(plant)
    assert [(x["action"], x["priority_class"]) for x in out] == [("created", "P1")]
    wo.transition(plant, out[0]["wo_id"], "reject", actor="pat", role="planner", reason="known issue: migrated asset, already reviewed")
    for _ in range(2):
        assess(plant, "P-101", "URGENT_REVIEW")
        assert [x["action"] for x in gen(plant)] == ["suppressed"]
    health.clear_latched_risk(plant, "P-101", "dismissed", actor="rea", role="reliability_engineer", reason="sensor artefact confirmed")
    _unknown_start_urgent(plant)
    assess(plant, "P-101", "URGENT_REVIEW")
    assert [(x["action"], x["priority_class"]) for x in gen(plant)] == [("created", "P1")]


@pytest.mark.parametrize("latch_state,job,pc", [(H.URGENT_REVIEW, "repair", "P1"), (H.INSPECTION_RECOMMENDED, "inspect", "P2")])
def test_a_routine_order_approved_before_the_latch_never_stands_in_for_it(tmp_path, latch_state, job, pc):
    """Regression (high, g3 b, G2): an APPROVED lubrication planned before the latch was linked to it without a new
    approval; no urgent order was raised, and completing the lubrication cleared the latch."""
    d = _plant(tmp_path / "lub.db", asset_type=_type(lubricate=JobSpec(duration_h=0.5, skill="mechanical")))
    lub = wo.create(d, asset_id="P-101", job_type="lubricate", priority_class="P3", title="monthly lube", origin="manual", actor="pat", role="planner",
                    idempotency_key="lub1")["wo_id"]
    wo.transition(d, lub, "submit", actor="pat", role="planner")
    wo.transition(d, lub, "approve", actor="pat", role="planner")
    backdate(d, lub)
    advance(d, "P-101", latch_state)
    assess(d, "P-101", latch_state.value)
    out = gen(d)
    assert [(x["action"], x["priority_class"]) for x in out] == [("created", pc)], out
    assert wo.get(d, out[0]["wo_id"])["job_type"] == job
    assert (wo.get(d, lub)["priority_class"], wo.get(d, lub)["state"]) == ("P3", "APPROVED")               # left as it was
    assert "HUMAN_APPROVAL_REQUIRED" in health.asset_state(d, "P-101").labels()
    assess(d, "P-101", latch_state.value)
    assert [x["action"] for x in gen(d)] == ["unchanged"]
    wo.transition(d, out[0]["wo_id"], "reject", actor="pat", role="planner", reason="known issue: exchange booked next month")
    assess(d, "P-101", latch_state.value)
    assert [x["action"] for x in gen(d)] == ["suppressed"]
    wo.transition(d, lub, "schedule", actor="pat", role="planner", data=SCHED)
    wo.transition(d, lub, "start", actor="tom", role="technician")
    done = wo.complete(d, lub, actor="tom", role="technician", outcome={**INSPECTED, "actions_taken": "greased bearings"})
    assert "latch_kept" in done["outcome"]["flags"] and health.asset_state(d, "P-101").latched_risk != "NONE"


@pytest.mark.parametrize("state", ["DRAFT", "APPROVED", "SCHEDULED"])
def test_an_inspection_not_awaiting_approval_from_before_the_latch_is_superseded(plant, state):
    """Regression (high, g3 a): a never-submitted DRAFT (or an order approved before the latch) was linked as the P1 for an
    URGENT latch: no approval flag, no system order. Only an order awaiting approval, or deferred, is linked."""
    o = wo.create(plant, asset_id="P-101", job_type="inspect", priority_class="P3", title="tech note: noisy?", origin="manual", actor="tom",
                  role="technician", idempotency_key="dr1")["wo_id"]
    if state != "DRAFT":
        wo.transition(plant, o, "submit", actor="pat", role="planner")
        wo.transition(plant, o, "approve", actor="pat", role="planner")
    if state == "SCHEDULED":
        wo.transition(plant, o, "schedule", actor="pat", role="planner", data=SCHED)
    backdate(plant, o)
    advance(plant, "P-101", H.URGENT_REVIEW)
    assess(plant, "P-101", "URGENT_REVIEW")
    out = gen(plant)
    assert [(x["action"], x["priority_class"]) for x in out] == [("created", "P1")], out
    new = wo.get(plant, out[0]["wo_id"])
    assert new["job_type"] == "repair"
    assert (wo.get(plant, o)["priority_class"], wo.get(plant, o)["state"]) == ("P3", state)
    assert "HUMAN_APPROVAL_REQUIRED" in health.asset_state(plant, "P-101").labels()


def test_a_draft_raised_during_the_latch_never_stands_in_for_it(plant):
    """Regression (g3 a): a DRAFT is not submitted for approval, so it must not hold back the system's order."""
    advance(plant, "P-101", H.URGENT_REVIEW)
    o = wo.create(plant, asset_id="P-101", job_type="repair", priority_class="P1", title="tech note", origin="manual", actor="tom", role="technician",
                  idempotency_key="dr2")["wo_id"]
    assess(plant, "P-101", "URGENT_REVIEW")
    out = gen(plant)
    assert [(x["action"], x["priority_class"]) for x in out] == [("created", "P1")] and out[0]["wo_id"] != o, out
    assert "HUMAN_APPROVAL_REQUIRED" in health.asset_state(plant, "P-101").labels()


def test_a_failing_recommendation_does_not_lose_the_assets_other_recommendations(plant):
    """Regression (low, g3 e): with an inspection_job the asset type lacks, the instrument check was lost too."""
    cfg = decision.load_config_text("inspection_job: survey\n")
    advance(plant, "P-101", H.INSPECTION_RECOMMENDED)
    advance(plant, "P-101", H.DATA_QUALITY_FAILURE)
    assess(plant, "P-101", "DATA_QUALITY_FAILURE", reasons=["stuck_signal: bearing_temp"])
    out = gen(plant, cfg)
    assert sorted(x["action"] for x in out) == ["created", "error"], out
    assert "survey" in [x for x in out if x["action"] == "error"][0]["note"]
    assert [(j, pc) for _, j, pc, _ in orders(plant)] == [("instrument_check", "P2")] and errors_audited(plant) == 1


@pytest.mark.parametrize("state,expected", [("PENDING_APPROVAL", "unchanged"), ("DRAFT", "created")])
def test_an_open_equipment_order_covers_a_desk_review(plant, state, expected):
    """Regression (low, g3 d): an open inspection no longer covered a desk review, so an out-of-scope criticality-A asset got
    a desk review in the approval queue as well, though a person was already going to look at it. A DRAFT does not cover it."""
    o = wo.create(plant, asset_id="P-101", job_type="inspect", priority_class="P2", title="manual", origin="manual", actor="pat", role="planner",
                  idempotency_key="d1")["wo_id"]
    if state == "PENDING_APPROVAL":
        wo.transition(plant, o, "submit", actor="pat", role="planner")
    advance(plant, "P-101", H.MODEL_OUT_OF_SCOPE)
    assess(plant, "P-101", "MODEL_OUT_OF_SCOPE")
    out = gen(plant)
    assert [x["action"] for x in out] == [expected], out
    if expected == "unchanged":
        assert out[0]["wo_id"] == o and len(orders(plant)) == 1
    else:
        assert wo.get(plant, out[0]["wo_id"])["job_type"] == "desk_review"
