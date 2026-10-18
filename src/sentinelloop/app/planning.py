"""Planning service: build a scheduling problem from approved work orders and recorded resources, store the proposal,
and let a planner apply it. A proposal never changes anything by itself; applying it schedules each order through the
work-order workflow, and a proposal whose orders changed since planning is refused as stale.
"""
from __future__ import annotations

import hashlib
import json
import uuid

from . import auditlog, registry, resources, scheduler as S, workorders
from .errors import PermissionDenied
from .timeutil import HOUR_MS, iso, now_iso, now_ms

PLANNERS = {"planner", "admin"}


class PlanningError(ValueError):
    pass


class PlanningPermissionError(PlanningError, PermissionDenied):
    pass


def build_problem(db, site_id: str, t0: int, horizon_h: float, slot_h: float) -> tuple[S.Problem, dict]:
    end = t0 + int(horizon_h * HOUR_MS)
    orders = [o for o in workorders.list_orders(db, states_in=["APPROVED", "SCHEDULED", "IN_PROGRESS"])
              if registry.get_asset(db, o["asset_id"]).site_id == site_id]
    versions, jobs, frozen = {}, [], []
    with db.connect() as c:
        as_of = {r["assessment_id"]: r["as_of_ms"] for r in c.execute("SELECT assessment_id, as_of_ms FROM assessments")}
    for o in orders:
        a = registry.get_asset(db, o["asset_id"])
        if o["state"] in ("SCHEDULED", "IN_PROGRESS"):
            if o["scheduled_start_ms"] is not None and o["scheduled_end_ms"] > t0 and o["scheduled_start_ms"] < end:
                frozen.append(S.Assignment(o["wo_id"], o["asset_id"], o["scheduled_start_ms"], o["scheduled_end_ms"], list(o["assigned"])))
            continue
        versions[o["wo_id"]] = o["version"]
        ex = o.get("explanation") or {}
        rh = ex.get("rul_hours")
        risk = None
        if rh and None not in rh and ex.get("interval_level") and o.get("assessment_id") in as_of:
            risk = (float(rh[0]), float(rh[1]), float(rh[2]), float(ex["interval_level"]), int(as_of[o["assessment_id"]]))
        jobs.append(S.Job(job_id=o["wo_id"], asset_id=o["asset_id"], skill=o["required_skill"], crew=int(o["crew_size"]), duration_h=float(o["duration_h"]),
                          parts=dict(o["parts"]), windows=[(w.start_ms, w.end_ms) for w in a.maintenance_windows], release_ms=t0, due_ms=o["due_by_ms"],
                          priority_class=o["priority_class"], criticality=a.criticality,
                          failure_cost=float(a.consequence.cost_per_failure) or 1.0, risk=risk, score=o["priority_score"]))
    techs = [S.Tech(t["tech_id"], frozenset(t["skills"]), tuple((s, e) for s, e in t["shifts"] if e > t0 and s < end)) for t in resources.technicians(db, site_id)]
    stock = {p["part_id"]: S.PartStock(p["part_id"], int(p["on_hand"]), float(p["lead_time_h"]),
                                       arrivals=tuple((eta, q) for eta, q in p["deliveries"] if eta > t0), orderable=bool(p["orderable"]))
             for p in resources.parts(db, site_id)}
    return S.Problem(t0_ms=t0, horizon_h=horizon_h, slot_h=slot_h, jobs=jobs, techs=techs, parts=stock, frozen=frozen), versions


def plan(db, site_id: str, policy: str, actor: str, role: str, t0: int | None = None, horizon_h: float = 72.0, slot_h: float = 1.0,
         time_limit_s: float = 30.0) -> dict:
    if role not in PLANNERS:
        raise PlanningPermissionError(f"role {role!r} may not create schedule proposals")
    t0 = int(t0 if t0 is not None else now_ms())
    p, versions = build_problem(db, site_id, t0, horizon_h, slot_h)
    sch = S.plan(p, policy, time_limit_s=time_limit_s)
    violations = S.validate(p, sch)
    assignments = [{"wo_id": x.job_id, "asset_id": x.asset_id, "start": iso(x.start_ms), "end": iso(x.end_ms), "technicians": x.techs,
                    "version": versions.get(x.job_id)} for x in sch.assignments]
    inputs_sha = hashlib.sha256(auditlog.canonical({"versions": versions, "t0": t0, "h": horizon_h, "slot": slot_h, "policy": policy}).encode()).hexdigest()
    run_id = f"SR-{uuid.uuid4().hex[:12]}"
    row = {"run_id": run_id, "site_id": site_id, "policy": policy, "t0": iso(t0), "horizon_h": horizon_h, "slot_h": slot_h, "assignments": assignments,
           "unscheduled": sch.unscheduled, "objective": sch.objective, "stats": sch.stats, "solver": sch.solver, "violations": violations, "status": "proposed"}
    with db.tx() as c:
        c.execute("INSERT INTO schedule_runs (run_id, site_id, policy, t0_ms, horizon_h, slot_h, created_by, created_at, assignments_json, unscheduled_json, "
                  "objective, stats_json, solver_json, violations_json, inputs_sha256, status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'proposed')",
                  (run_id, site_id, policy, t0, horizon_h, slot_h, actor, now_iso(), json.dumps(assignments), json.dumps(sch.unscheduled), sch.objective,
                   json.dumps(sch.stats), json.dumps(sch.solver, default=str), json.dumps(violations), inputs_sha))
        auditlog.append(c, actor=actor, action="schedule.proposed", entity="schedule_run", entity_id=run_id,
                        payload={"policy": policy, "n_assignments": len(assignments), "n_unscheduled": len(sch.unscheduled), "violations": len(violations),
                                 "objective": sch.objective, "inputs_sha256": inputs_sha}, key=db.audit_key, key_id=db.audit_key_id)
    return row


def get(db, run_id: str) -> dict | None:
    with db.connect() as c:
        r = c.execute("SELECT * FROM schedule_runs WHERE run_id = ?", (run_id,)).fetchone()
    if r is None:
        return None
    d = dict(r)
    for k in ("assignments", "unscheduled", "stats", "solver", "violations"):
        d[k] = json.loads(d.pop(f"{k}_json"))
    return d


def apply(db, run_id: str, actor: str, role: str) -> dict:
    if role not in PLANNERS:
        raise PlanningPermissionError(f"role {role!r} may not apply schedule proposals")
    run = get(db, run_id)
    if run is None:
        raise PlanningError(f"unknown schedule run {run_id}")
    if run["status"] == "applied":
        return {"run_id": run_id, "already_applied": True, "scheduled": [a["wo_id"] for a in run["assignments"]]}
    if run["violations"]:
        raise PlanningError(f"proposal {run_id} has {len(run['violations'])} feasibility violations and cannot be applied")
    stale = []
    for a in run["assignments"]:
        o = workorders.get(db, a["wo_id"])
        if o is None or o["state"] != "APPROVED" or o["version"] != a["version"]:
            stale.append(a["wo_id"])
    if stale:
        raise PlanningError(f"proposal {run_id} is stale: {', '.join(stale)} changed since planning; re-plan")
    done = []
    for a in run["assignments"]:
        workorders.transition(db, a["wo_id"], "schedule", actor=actor, role=role, data={"start": a["start"], "end": a["end"], "technicians": a["technicians"]},
                              expected_version=a["version"], idempotency_key=f"apply:{run_id}:{a['wo_id']}")
        done.append(a["wo_id"])
    with db.tx() as c:
        c.execute("UPDATE schedule_runs SET status = 'applied', applied_by = ?, applied_at = ? WHERE run_id = ?", (actor, now_iso(), run_id))
        c.execute("UPDATE schedule_runs SET status = 'superseded' WHERE site_id = ? AND status = 'proposed' AND run_id != ?", (run["site_id"], run_id))
        auditlog.append(c, actor=actor, action="schedule.applied", entity="schedule_run", entity_id=run_id, payload={"scheduled": done},
                        key=db.audit_key, key_id=db.audit_key_id)
    return {"run_id": run_id, "already_applied": False, "scheduled": done}
