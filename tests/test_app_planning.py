"""Resources and the planning service that schedules approved work orders from the database (tests first)."""
import pytest

from sentinelloop.app import db as dbmod, planning, registry, resources, workorders as wo
from sentinelloop.app.timeutil import parse_ts
from test_app_foundation import KEY, pump, pump_type

T0 = parse_ts("2026-10-20T00:00:00Z")


@pytest.fixture
def plant(tmp_path):
    d = dbmod.Database(tmp_path / "plant.db", audit_key=KEY, audit_key_id="test")
    d.migrate()
    registry.create_site(d, "site1", "Plant 1", "UTC", actor="admin")
    registry.create_asset_type(d, pump_type(), actor="admin")
    for i, crit in ((1, "A"), (2, "B"), (3, "C")):
        registry.create_asset(d, pump(f"P-10{i}", criticality=crit, maintenance_windows=[{"start": "2026-10-20T06:00:00Z", "end": "2026-10-20T18:00:00Z"}]),
                              actor="admin")
    resources.upsert_technician(d, "tech1", "Asha", "site1", ["mechanical"], actor="admin")
    resources.upsert_technician(d, "tech2", "Ravi", "site1", ["electrical"], actor="admin")
    resources.set_shifts(d, "tech1", [("2026-10-20T06:00:00Z", "2026-10-20T14:00:00Z")], actor="admin")
    resources.set_shifts(d, "tech2", [("2026-10-20T06:00:00Z", "2026-10-20T14:00:00Z")], actor="admin")
    resources.upsert_part(d, "bearing_kit", "site1", "Bearing kit", on_hand=1, lead_time_h=48, actor="admin")
    return d


def approved(d, asset, key, job="repair", pc="P2"):
    o = wo.create(d, asset_id=asset, job_type=job, priority_class=pc, title=f"{job} {asset}", origin="manual", actor="planner1", role="planner",
                  idempotency_key=key, due_by="2026-10-21T00:00:00Z")
    wo.transition(d, o["wo_id"], "submit", actor="planner1", role="planner")
    return wo.transition(d, o["wo_id"], "approve", actor="re1", role="reliability_engineer", reason="ok")


def test_resource_changes_are_validated_and_audited(plant):
    with pytest.raises(resources.ResourceError):
        resources.set_shifts(plant, "tech1", [("2026-10-20T14:00:00Z", "2026-10-20T06:00:00Z")], actor="admin")
    with pytest.raises(resources.ResourceError):
        resources.upsert_part(plant, "x", "site1", "x", on_hand=-1, lead_time_h=1, actor="admin")
    resources.add_delivery(plant, "bearing_kit", "site1", qty=2, eta="2026-10-20T10:00:00Z", reference="PO-7", actor="planner1")
    with plant.connect() as c:
        actions = {r[0] for r in c.execute("SELECT action FROM audit_events")}
    assert {"technician.upserted", "shifts.set", "part.upserted", "part.delivery_added"} <= actions


def test_plan_uses_only_approved_orders_and_explains_what_it_cannot_schedule(plant):
    a = approved(plant, "P-101", "k1")                         # mechanical, needs 1 bearing kit (1 on hand)
    b = approved(plant, "P-102", "k2")                         # needs a second kit: none arrives within the horizon
    draft = wo.create(plant, asset_id="P-103", job_type="inspect", priority_class="P3", title="draft", origin="manual", actor="planner1",
                      role="planner", idempotency_key="k3")     # not approved: must not be planned
    run = planning.plan(plant, "site1", policy="risk_greedy", t0=T0, horizon_h=24, slot_h=1, actor="planner1", role="planner")
    assert run["violations"] == [] and run["status"] == "proposed"
    planned = {x["wo_id"] for x in run["assignments"]}
    assert a["wo_id"] in planned and draft["wo_id"] not in planned and draft["wo_id"] not in run["unscheduled"]
    assert b["wo_id"] in run["unscheduled"] and "part" in run["unscheduled"][b["wo_id"]]


def test_applying_a_proposal_schedules_orders_and_is_idempotent(plant):
    a = approved(plant, "P-101", "k1")
    run = planning.plan(plant, "site1", policy="milp", t0=T0, horizon_h=24, slot_h=1, actor="planner1", role="planner")
    out = planning.apply(plant, run["run_id"], actor="planner1", role="planner")
    assert wo.get(plant, a["wo_id"])["state"] == "SCHEDULED" and out["scheduled"] == [a["wo_id"]]
    again = planning.apply(plant, run["run_id"], actor="planner1", role="planner")
    assert again["already_applied"] is True
    with pytest.raises(planning.PlanningError):
        planning.apply(plant, run["run_id"], actor="tech1", role="technician")


def test_stale_proposal_is_refused_when_orders_changed(plant):
    a = approved(plant, "P-101", "k1")
    run = planning.plan(plant, "site1", policy="edd", t0=T0, horizon_h=24, slot_h=1, actor="planner1", role="planner")
    wo.transition(plant, a["wo_id"], "cancel", actor="planner1", role="planner", reason="pump replaced by operations")
    with pytest.raises(planning.PlanningError):
        planning.apply(plant, run["run_id"], actor="planner1", role="planner")


def test_assets_without_windows_or_technicians_without_shifts_are_never_assumed_available(plant):
    registry.update_asset(plant, "P-101", {"maintenance_windows": []}, actor="admin", reason="no window agreed with operations yet")
    a = approved(plant, "P-101", "k1")
    run = planning.plan(plant, "site1", policy="edd", t0=T0, horizon_h=24, slot_h=1, actor="planner1", role="planner")
    assert "no maintenance window" in run["unscheduled"][a["wo_id"]]
