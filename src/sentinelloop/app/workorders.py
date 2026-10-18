"""Work-order workflow: explicit states, role-checked transitions, idempotency, optimistic concurrency, outcomes.

States: DRAFT -> PENDING_APPROVAL -> APPROVED -> SCHEDULED -> IN_PROGRESS -> COMPLETED -> CLOSED, with REJECTED,
DEFERRED (-> PENDING_APPROVAL on reactivation) and CANCELLED. System-generated orders start in PENDING_APPROVAL and
set the asset's HUMAN_APPROVAL_REQUIRED flag; nothing is scheduled, sent to another system or executed until an
authorised person approves. Completing requires an outcome; the outcome is checked against the recommendation and the
job plan, and contradictions are stored as flags rather than silently accepted. A completed order clears the asset's
latched risk (state machine event `maintenance_completed`) because a person has now looked at the asset.
"""
from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import Field

from . import auditlog, health, registry, states
from .models import Strict
from .timeutil import iso, now_iso, parse_ts

APPROVERS = {"planner", "reliability_engineer", "admin"}
CREATORS = APPROVERS | {"technician", "system", "integration"}
TERMINAL = {"CLOSED", "REJECTED", "CANCELLED"}
NON_TERMINAL = {"DRAFT", "PENDING_APPROVAL", "APPROVED", "SCHEDULED", "IN_PROGRESS", "COMPLETED", "DEFERRED"}

# action: (allowed from-states, to-state, roles, reason required)
TRANSITIONS = {
    "submit": ({"DRAFT"}, "PENDING_APPROVAL", APPROVERS | {"technician", "system", "integration"}, False),
    "approve": ({"PENDING_APPROVAL"}, "APPROVED", APPROVERS, False),
    "reject": ({"PENDING_APPROVAL"}, "REJECTED", APPROVERS, True),
    "defer": ({"PENDING_APPROVAL", "APPROVED"}, "DEFERRED", APPROVERS, True),
    "reactivate": ({"DEFERRED"}, "PENDING_APPROVAL", APPROVERS | {"system"}, True),
    "schedule": ({"APPROVED", "SCHEDULED"}, "SCHEDULED", {"planner", "admin"}, False),
    "unschedule": ({"SCHEDULED"}, "APPROVED", {"planner", "admin"}, True),
    "start": ({"SCHEDULED"}, "IN_PROGRESS", {"technician", "planner", "admin"}, False),
    "complete": ({"IN_PROGRESS"}, "COMPLETED", {"technician", "planner", "admin", "integration"}, False),
    "close": ({"COMPLETED"}, "CLOSED", APPROVERS, False),
    "cancel": (NON_TERMINAL - {"COMPLETED"}, "CANCELLED", APPROVERS, True),
}


class WorkflowError(ValueError):
    pass


class IdempotencyConflict(WorkflowError):
    pass


class ConcurrencyConflict(WorkflowError):
    pass


class Outcome(Strict):
    findings_code: Literal["no_fault_found", "degradation_found", "failure_found", "not_inspected", "other"]
    failure_confirmed: Literal["yes", "no", "unknown"]
    root_cause: str = ""
    actions_taken: str = Field(min_length=1)
    parts_used: dict[str, int] = Field(default_factory=dict)
    downtime_hours: float = Field(ge=0)
    returned_to_service_at: str | None = None
    notes: str = ""


def _audit(db, c, actor, action, wo_id, payload):
    auditlog.append(c, actor=actor, action=action, entity="work_order", entity_id=wo_id, payload=payload, key=db.audit_key, key_id=db.audit_key_id)


def _row(r, c=None) -> dict:
    d = dict(r)
    d["parts"] = json.loads(d.pop("parts_json"))
    d["assigned"] = json.loads(d.pop("assigned_json"))
    d["explanation"] = json.loads(d.pop("explanation_json"))
    d["due_by"] = iso(d["due_by_ms"])
    d["scheduled_start"], d["scheduled_end"] = iso(d["scheduled_start_ms"]), iso(d["scheduled_end_ms"])
    d["deferred_until"] = iso(d["deferred_until_ms"])
    if c is not None:
        o = c.execute("SELECT * FROM outcomes WHERE wo_id = ?", (d["wo_id"],)).fetchone()
        if o is not None:
            od = dict(o)
            od["parts_used"] = json.loads(od.pop("parts_used_json"))
            od["flags"] = json.loads(od.pop("flags_json"))
            d["outcome"] = od
        else:
            d["outcome"] = None
    return d


def get(db, wo_id: str) -> dict | None:
    with db.connect() as c:
        r = c.execute("SELECT * FROM work_orders WHERE wo_id = ?", (wo_id,)).fetchone()
        return _row(r, c) if r else None


def list_orders(db, states_in=None, asset_id: str | None = None) -> list[dict]:
    q, a = "SELECT * FROM work_orders WHERE 1=1", []
    if states_in:
        q += f" AND state IN ({','.join('?' * len(states_in))})"
        a += list(states_in)
    if asset_id:
        q, a = q + " AND asset_id = ?", a + [asset_id]
    with db.connect() as c:
        return [_row(r, c) for r in c.execute(q + " ORDER BY priority_class, due_by_ms IS NULL, due_by_ms, wo_id", a)]


def history(db, wo_id: str) -> list[dict]:
    with db.connect() as c:
        return [dict(r) | {"data": json.loads(r["data_json"])} for r in c.execute("SELECT * FROM work_order_events WHERE wo_id = ? ORDER BY event_id", (wo_id,))]


def _refresh_approval_flag(c, asset_id: str):
    pending = c.execute("SELECT COUNT(*) FROM work_orders WHERE asset_id = ? AND state = 'PENDING_APPROVAL'", (asset_id,)).fetchone()[0] > 0
    s = health._state_from_conn(c, asset_id)
    if s is not None or pending:
        health._store_state(c, asset_id, states.set_approval_pending(s or states.AssetState(), pending), None)


def create(db, asset_id: str, job_type: str, priority_class: str, title: str, origin: str, actor: str, role: str, idempotency_key: str,
           due_by: str | None = None, description: str = "", initial_state: str = "DRAFT", priority_score: float | None = None,
           explanation: dict | None = None, assessment_id: str | None = None) -> dict:
    if role not in CREATORS:
        raise WorkflowError(f"role {role!r} may not create work orders")
    if initial_state not in ("DRAFT", "PENDING_APPROVAL"):
        raise WorkflowError("new work orders start as DRAFT or PENDING_APPROVAL")
    if priority_class not in ("P1", "P2", "P3"):
        raise WorkflowError("priority_class must be P1, P2 or P3")
    if not idempotency_key:
        raise WorkflowError("an idempotency key is required")
    asset = registry.get_asset(db, asset_id)
    if asset is None:
        raise WorkflowError(f"unknown asset {asset_id}")
    job = registry.get_asset_type(db, asset.asset_type_id).jobs.get(job_type)
    if job is None:
        raise WorkflowError(f"job type {job_type!r} is not defined for asset type {asset.asset_type_id}")
    due_ms = parse_ts(due_by) if due_by else None
    payload = {"asset_id": asset.asset_id, "job_type": job_type, "priority_class": priority_class, "title": title, "origin": origin, "due_by_ms": due_ms,
               "description": description, "initial_state": initial_state, "assessment_id": assessment_id}
    sha = hashlib.sha256(auditlog.canonical(payload).encode()).hexdigest()
    ts = now_iso()
    with db.tx() as c:
        existing = c.execute("SELECT * FROM work_orders WHERE idempotency_key = ?", (idempotency_key,)).fetchone()
        if existing is not None:
            if existing["payload_sha256"] != sha:
                raise IdempotencyConflict(f"idempotency key {idempotency_key!r} was already used for a different request ({existing['wo_id']})")
            return _row(existing, c)
        n = c.execute("SELECT COUNT(*) FROM work_orders").fetchone()[0] + 1
        wo_id = f"WO-{n:06d}"
        c.execute("INSERT INTO work_orders (wo_id, asset_id, origin, assessment_id, job_type, title, description, priority_class, priority_score, "
                  "explanation_json, due_by_ms, duration_h, crew_size, required_skill, parts_json, state, version, idempotency_key, payload_sha256, "
                  "created_by, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,?,?,?,?,?)",
                  (wo_id, asset.asset_id, origin, assessment_id, job_type, title, description, priority_class, priority_score, json.dumps(explanation or {}),
                   due_ms, job.duration_h, job.crew_size, job.skill, json.dumps(job.parts), initial_state, idempotency_key, sha, actor, ts, ts))
        c.execute("INSERT INTO work_order_events (wo_id, ts, actor, role, action, from_state, to_state, reason, data_json, idempotency_key) "
                  "VALUES (?,?,?,?,'create',NULL,?,'',?,?)", (wo_id, ts, actor, role, initial_state, json.dumps(payload), idempotency_key))
        _audit(db, c, actor, "work_order.created", wo_id, {**payload, "role": role, "explanation": explanation or {}})
        if initial_state == "PENDING_APPROVAL":
            _refresh_approval_flag(c, asset.asset_id)
        return _row(c.execute("SELECT * FROM work_orders WHERE wo_id = ?", (wo_id,)).fetchone(), c)


def _apply(db, c, o, action: str, actor: str, role: str, reason: str, data: dict, idempotency_key: str | None, extra_sets: dict | None = None):
    frm, to, roles, need_reason = TRANSITIONS[action]
    if o["state"] not in frm:
        raise WorkflowError(f"cannot {action} a work order in state {o['state']}")
    if role not in roles:
        raise WorkflowError(f"role {role!r} may not {action} work orders")
    if need_reason and not (reason or "").strip():
        raise WorkflowError(f"a reason is required to {action}")
    sets = dict(extra_sets or {})
    if action == "defer":
        if not data.get("until"):
            raise WorkflowError("defer needs data.until (when the order comes back for approval)")
        sets["deferred_until_ms"] = parse_ts(data["until"])
    if action == "schedule":
        try:
            s, e = parse_ts(data["start"]), parse_ts(data["end"])
        except KeyError as ex:
            raise WorkflowError("schedule needs data.start, data.end and data.technicians") from ex
        techs = list(data.get("technicians") or [])
        if e <= s or not techs:
            raise WorkflowError("schedule needs end > start and at least one technician")
        sets.update({"scheduled_start_ms": s, "scheduled_end_ms": e, "assigned_json": json.dumps(techs)})
    if action == "unschedule":
        sets.update({"scheduled_start_ms": None, "scheduled_end_ms": None, "assigned_json": "[]"})
    ts = now_iso()
    sets.update({"state": to, "version": o["version"] + 1, "updated_at": ts})
    c.execute("UPDATE work_orders SET " + ", ".join(f"{k} = ?" for k in sets) + " WHERE wo_id = ? AND version = ?",
              (*sets.values(), o["wo_id"], o["version"]))
    c.execute("INSERT INTO work_order_events (wo_id, ts, actor, role, action, from_state, to_state, reason, data_json, idempotency_key) VALUES (?,?,?,?,?,?,?,?,?,?)",
              (o["wo_id"], ts, actor, role, action, o["state"], to, reason or "", json.dumps(data or {}), idempotency_key))
    _audit(db, c, actor, f"work_order.{action}", o["wo_id"], {"from": o["state"], "to": to, "role": role, "reason": reason or "", "data": data or {}})
    if "PENDING_APPROVAL" in (o["state"], to):
        _refresh_approval_flag(c, o["asset_id"])


def transition(db, wo_id: str, action: str, actor: str, role: str, reason: str | None = None, data: dict | None = None,
               expected_version: int | None = None, idempotency_key: str | None = None) -> dict:
    if action not in TRANSITIONS:
        raise WorkflowError(f"unknown action {action!r}")
    if action == "complete":
        raise WorkflowError("use complete() with an outcome: a work order cannot be completed without one")
    with db.tx() as c:
        o = c.execute("SELECT * FROM work_orders WHERE wo_id = ?", (wo_id,)).fetchone()
        if o is None:
            raise WorkflowError(f"unknown work order {wo_id}")
        if idempotency_key:
            ev = c.execute("SELECT action FROM work_order_events WHERE wo_id = ? AND idempotency_key = ?", (wo_id, idempotency_key)).fetchone()
            if ev is not None:
                if ev["action"] != action:
                    raise IdempotencyConflict(f"idempotency key {idempotency_key!r} was used for {ev['action']}, not {action}")
                return _row(o, c)
        if expected_version is not None and int(expected_version) != o["version"]:
            raise ConcurrencyConflict(f"work order {wo_id} is at version {o['version']}, request expected {expected_version}")
        _apply(db, c, o, action, actor, role, reason, data or {}, idempotency_key)
        return _row(c.execute("SELECT * FROM work_orders WHERE wo_id = ?", (wo_id,)).fetchone(), c)


def _flags(o, out: Outcome) -> list[str]:
    f = []
    if o["origin"] == "system" and o["priority_class"] == "P1" and out.findings_code == "no_fault_found":
        f.append("urgent_recommendation_not_confirmed")
    if out.findings_code == "failure_found" and o["priority_class"] == "P3":
        f.append("risk_underestimated")
    planned = json.loads(o["parts_json"])
    if o["job_type"] in ("repair", "replace") and planned and not out.parts_used:
        f.append("repair_job_without_parts")
    if planned and out.parts_used and out.parts_used != planned:
        f.append("parts_differ_from_plan")
    if out.failure_confirmed == "yes" and out.findings_code == "no_fault_found":
        f.append("contradictory_failure_confirmation")
    if out.findings_code == "not_inspected":
        f.append("asset_not_inspected")
    if out.downtime_hours > 3 * float(o["duration_h"]):
        f.append("downtime_exceeds_three_times_plan")
    return f


def complete(db, wo_id: str, actor: str, role: str, outcome: dict, expected_version: int | None = None, idempotency_key: str | None = None) -> dict:
    out = Outcome(**outcome)
    if out.returned_to_service_at:
        parse_ts(out.returned_to_service_at)
    with db.tx() as c:
        o = c.execute("SELECT * FROM work_orders WHERE wo_id = ?", (wo_id,)).fetchone()
        if o is None:
            raise WorkflowError(f"unknown work order {wo_id}")
        if idempotency_key and c.execute("SELECT 1 FROM work_order_events WHERE wo_id = ? AND idempotency_key = ?", (wo_id, idempotency_key)).fetchone():
            return _row(o, c)
        if expected_version is not None and int(expected_version) != o["version"]:
            raise ConcurrencyConflict(f"work order {wo_id} is at version {o['version']}, request expected {expected_version}")
        flags = _flags(o, out)
        _apply(db, c, o, "complete", actor, role, "", {"outcome": out.model_dump(), "flags": flags}, idempotency_key)
        ts = now_iso()
        c.execute("INSERT INTO outcomes (wo_id, recorded_by, recorded_at, findings_code, failure_confirmed, root_cause, actions_taken, parts_used_json, "
                  "downtime_hours, returned_to_service_at, notes, flags_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                  (wo_id, actor, ts, out.findings_code, out.failure_confirmed, out.root_cause, out.actions_taken, json.dumps(out.parts_used),
                   out.downtime_hours, out.returned_to_service_at, out.notes, json.dumps(flags)))
        c.execute("UPDATE assets SET last_maintenance_at = ?, updated_at = ? WHERE asset_id = ?", (ts, ts, o["asset_id"]))
        s = health._state_from_conn(c, o["asset_id"])
        if s is not None and s.latched_risk != "NONE":
            new = states.clear_risk(s, event="maintenance_completed", actor=actor, role=role if role in states.CLEAR_EVENTS["maintenance_completed"] else "integration",
                                    reason=f"{wo_id} completed: {out.findings_code}; {out.actions_taken}")
            health._store_state(c, o["asset_id"], new, None)
            _audit(db, c, actor, "asset_state.maintenance_completed", o["asset_id"], {"wo_id": wo_id, "before": s.labels(), "after": new.labels()})
        return _row(c.execute("SELECT * FROM work_orders WHERE wo_id = ?", (wo_id,)).fetchone(), c)


def missing_outcomes(db) -> list[dict]:
    with db.connect() as c:
        rows = c.execute("SELECT w.* FROM work_orders w LEFT JOIN outcomes o ON o.wo_id = w.wo_id WHERE w.state IN ('COMPLETED', 'CLOSED') "
                         "AND o.wo_id IS NULL ORDER BY w.wo_id").fetchall()
        return [_row(r) for r in rows]
