"""Work-order workflow, idempotency, outcomes and contradiction checks (tests written before the code)."""
import pytest

from sentinelloop.app import db as dbmod, health, registry, workorders as wo
from sentinelloop.app.states import AssetState, Classification, HealthState as H, Thresholds
from sentinelloop.app import states
from sentinelloop.app.timeutil import parse_ts
from test_app_foundation import KEY, pump, pump_type


@pytest.fixture
def plant(tmp_path):
    d = dbmod.Database(tmp_path / "plant.db", audit_key=KEY, audit_key_id="test")
    d.migrate()
    registry.create_site(d, "site1", "Plant 1", "UTC", actor="admin")
    registry.create_asset_type(d, pump_type(), actor="admin")
    registry.create_asset(d, pump("P-101"), actor="admin")
    return d


def new_order(d, key="k1", **kw):
    base = dict(asset_id="P-101", job_type="repair", priority_class="P2", title="Replace bearing", origin="manual", actor="planner1", role="planner",
                idempotency_key=key, due_by="2026-10-25T00:00:00Z")
    base.update(kw)
    return wo.create(d, **base)


def test_create_takes_duration_skill_and_parts_from_the_asset_type(plant):
    o = new_order(plant)
    assert o["state"] == "DRAFT" and o["duration_h"] == 6.0 and o["required_skill"] == "mechanical" and o["parts"] == {"bearing_kit": 1}


def test_create_is_idempotent_and_detects_key_reuse(plant):
    a = new_order(plant)
    b = new_order(plant)
    assert a["wo_id"] == b["wo_id"]
    with pytest.raises(wo.IdempotencyConflict):
        new_order(plant, title="Something else")


def test_happy_path_with_roles_and_reasons(plant):
    o = new_order(plant)
    o = wo.transition(plant, o["wo_id"], "submit", actor="planner1", role="planner")
    with pytest.raises(wo.WorkflowError):
        wo.transition(plant, o["wo_id"], "approve", actor="tech1", role="technician")          # technicians cannot approve
    o = wo.transition(plant, o["wo_id"], "approve", actor="re1", role="reliability_engineer", reason="bearing temperature trend confirmed")
    o = wo.transition(plant, o["wo_id"], "schedule", actor="planner1", role="planner",
                      data={"start": "2026-10-20T06:00:00Z", "end": "2026-10-20T12:00:00Z", "technicians": ["tech1"]})
    o = wo.transition(plant, o["wo_id"], "start", actor="tech1", role="technician")
    with pytest.raises(wo.WorkflowError):
        wo.transition(plant, o["wo_id"], "complete", actor="tech1", role="technician")           # an outcome is required to complete
    o = wo.complete(plant, o["wo_id"], actor="tech1", role="technician",
                    outcome={"findings_code": "degradation_found", "failure_confirmed": "no", "actions_taken": "bearing replaced",
                             "parts_used": {"bearing_kit": 1}, "downtime_hours": 5.5})
    assert o["state"] == "COMPLETED"
    o = wo.transition(plant, o["wo_id"], "close", actor="planner1", role="planner")
    assert o["state"] == "CLOSED"
    hist = wo.history(plant, o["wo_id"])
    assert [h["action"] for h in hist] == ["create", "submit", "approve", "schedule", "start", "complete", "close"]


def test_illegal_transitions_and_missing_reasons_are_refused(plant):
    o = new_order(plant)
    with pytest.raises(wo.WorkflowError):
        wo.transition(plant, o["wo_id"], "start", actor="tech1", role="technician")               # DRAFT cannot start
    wo.transition(plant, o["wo_id"], "submit", actor="planner1", role="planner")
    with pytest.raises(wo.WorkflowError):
        wo.transition(plant, o["wo_id"], "reject", actor="planner1", role="planner", reason="")   # reason mandatory
    with pytest.raises(wo.WorkflowError):
        wo.transition(plant, o["wo_id"], "defer", actor="planner1", role="planner", reason="no window")  # defer needs an until date
    o = wo.transition(plant, o["wo_id"], "defer", actor="planner1", role="planner", reason="shutdown next week", data={"until": "2026-10-27T00:00:00Z"})
    assert o["state"] == "DEFERRED"
    o = wo.transition(plant, o["wo_id"], "reactivate", actor="planner1", role="planner", reason="shutdown moved")
    assert o["state"] == "PENDING_APPROVAL"
    o = wo.transition(plant, o["wo_id"], "cancel", actor="planner1", role="planner", reason="duplicate of WO raised by operations")
    with pytest.raises(wo.WorkflowError):
        wo.transition(plant, o["wo_id"], "reactivate", actor="planner1", role="planner", reason="x")   # terminal state


def test_stale_version_is_rejected_for_concurrent_edits(plant):
    o = new_order(plant)
    wo.transition(plant, o["wo_id"], "submit", actor="planner1", role="planner", expected_version=o["version"])
    with pytest.raises(wo.ConcurrencyConflict):
        wo.transition(plant, o["wo_id"], "approve", actor="re1", role="reliability_engineer", reason="ok", expected_version=o["version"])


def test_transition_idempotency_key_replays_without_a_second_event(plant):
    o = new_order(plant)
    a = wo.transition(plant, o["wo_id"], "submit", actor="planner1", role="planner", idempotency_key="t-1")
    b = wo.transition(plant, o["wo_id"], "submit", actor="planner1", role="planner", idempotency_key="t-1")
    assert a["version"] == b["version"] and len(wo.history(plant, o["wo_id"])) == 2


def test_outcome_contradictions_are_flagged_not_hidden(plant):
    o = new_order(plant, key="k2", origin="system", priority_class="P1")
    for act, kw in (("submit", {}), ("approve", {"reason": "urgent"}), ("schedule", {"data": {"start": "2026-10-20T06:00:00Z", "end": "2026-10-20T12:00:00Z", "technicians": ["tech1"]}}),
                    ("start", {})):
        wo.transition(plant, o["wo_id"], act, actor="planner1", role="planner", **kw)
    o = wo.complete(plant, o["wo_id"], actor="tech1", role="technician",
                    outcome={"findings_code": "no_fault_found", "failure_confirmed": "no", "actions_taken": "inspected, nothing found", "parts_used": {},
                             "downtime_hours": 2.0})
    flags = wo.get(plant, o["wo_id"])["outcome"]["flags"]
    assert "urgent_recommendation_not_confirmed" in flags and "repair_job_without_parts" in flags


def test_missing_outcomes_report(plant):
    o = new_order(plant)
    assert wo.missing_outcomes(plant) == []
    with plant.tx() as c:
        c.execute("UPDATE work_orders SET state = 'COMPLETED' WHERE wo_id = ?", (o["wo_id"],))    # e.g. closed in the CMMS without an outcome
    assert [m["wo_id"] for m in wo.missing_outcomes(plant)] == [o["wo_id"]]


def test_system_order_sets_and_decision_clears_the_approval_flag(plant):
    with plant.tx() as c:
        health._store_state(c, "P-101", states.advance(AssetState(), Classification(H.URGENT_REVIEW, []), Thresholds()), None)
    o = new_order(plant, key="k3", origin="system", initial_state="PENDING_APPROVAL", priority_class="P1")
    assert health.asset_state(plant, "P-101").labels() == ["URGENT_REVIEW", "HUMAN_APPROVAL_REQUIRED"]
    wo.transition(plant, o["wo_id"], "approve", actor="re1", role="reliability_engineer", reason="confirmed")
    assert health.asset_state(plant, "P-101").labels() == ["URGENT_REVIEW"]


def test_completed_maintenance_clears_the_latched_risk(plant):
    with plant.tx() as c:
        health._store_state(c, "P-101", states.advance(AssetState(), Classification(H.URGENT_REVIEW, []), Thresholds()), None)
    o = new_order(plant, key="k4")
    for act, kw in (("submit", {}), ("approve", {"reason": "ok"}), ("schedule", {"data": {"start": "2026-10-20T06:00:00Z", "end": "2026-10-20T12:00:00Z", "technicians": ["tech1"]}}),
                    ("start", {})):
        wo.transition(plant, o["wo_id"], act, actor="planner1", role="planner", **kw)
    wo.complete(plant, o["wo_id"], actor="tech1", role="technician",
                outcome={"findings_code": "failure_found", "failure_confirmed": "yes", "root_cause": "bearing wear", "actions_taken": "bearing replaced",
                         "parts_used": {"bearing_kit": 1}, "downtime_hours": 6})
    s = health.asset_state(plant, "P-101")
    assert s.latched_risk == "NONE" and s.effective == H.NORMAL_MONITORING
    assert registry.get_asset(plant, "P-101").last_maintenance_at is not None


def test_complete_refuses_an_idempotency_key_used_for_another_action(plant):
    o = new_order(plant, key="k5")
    for act, kw in (("submit", {}), ("approve", {"reason": "ok"}), ("schedule", {"data": {"start": "2026-10-20T06:00:00Z", "end": "2026-10-20T12:00:00Z", "technicians": ["tech1"]}})):
        wo.transition(plant, o["wo_id"], act, actor="planner1", role="planner", **kw)
    wo.transition(plant, o["wo_id"], "start", actor="tech1", role="technician", idempotency_key="same-key")
    with pytest.raises(wo.IdempotencyConflict):
        wo.complete(plant, o["wo_id"], actor="tech1", role="technician", idempotency_key="same-key",
                    outcome={"findings_code": "degradation_found", "failure_confirmed": "no", "actions_taken": "x", "parts_used": {"bearing_kit": 1}, "downtime_hours": 1})
    assert wo.get(plant, o["wo_id"])["state"] == "IN_PROGRESS"


def test_reprioritise_escalates_and_brings_a_deferred_order_back(plant):
    o = new_order(plant, key="k6", priority_class="P3")
    wo.transition(plant, o["wo_id"], "submit", actor="planner1", role="planner")
    wo.transition(plant, o["wo_id"], "defer", actor="planner1", role="planner", reason="next shutdown", data={"until": "2026-11-30T00:00:00Z"})
    o2 = wo.reprioritise(plant, o["wo_id"], "P1", 5.0, parse_ts("2026-10-21T00:00:00Z"), {"why": "urgent"}, actor="system", role="system", reason="new assessment")
    assert o2["priority_class"] == "P1" and o2["state"] == "PENDING_APPROVAL" and o2["due_by"] == "2026-10-21T00:00:00Z"
    with pytest.raises(wo.WorkflowError):
        wo.reprioritise(plant, o["wo_id"], "P1", 5.0, None, {}, actor="tech1", role="technician", reason="x")
