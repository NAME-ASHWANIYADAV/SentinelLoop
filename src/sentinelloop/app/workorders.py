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
from .errors import PermissionDenied
from .models import Strict
from .timeutil import iso, now_iso, parse_ts

APPROVERS = {"planner", "reliability_engineer", "admin"}
CREATORS = APPROVERS | {"technician", "system", "integration"}
TERMINAL = {"CLOSED", "REJECTED", "CANCELLED"}
CLASS_ORDER = {"P1": 1, "P2": 2, "P3": 3}
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
    # the crew could not do the job (weather, access, sickness): back to the planner with a reason, schedule cleared
    "hand_back": ({"SCHEDULED", "IN_PROGRESS"}, "APPROVED", {"technician", "planner", "admin"}, True),
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


class RolePermissionError(WorkflowError, PermissionDenied):
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
        raise RolePermissionError(f"role {role!r} may not create work orders")
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
        raise RolePermissionError(f"role {role!r} may not {action} work orders")
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
        site = c.execute("SELECT site_id FROM assets WHERE asset_id = ?", (o["asset_id"],)).fetchone()["site_id"]
        known = {r[0] for r in c.execute("SELECT tech_id FROM technicians WHERE site_id = ? AND active = 1", (site,))}
        if known and not set(techs) <= known:        # sites with a recorded crew list: only registered, active technicians
            raise WorkflowError(f"unknown or inactive technicians for site {site}: {sorted(set(techs) - known)}")
        sets.update({"scheduled_start_ms": s, "scheduled_end_ms": e, "assigned_json": json.dumps(techs)})
    if action in ("unschedule", "hand_back"):
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


CLEARING_FINDINGS = {"degradation_found", "failure_found", "no_fault_found"}     # an inspection actually took place
NON_CLEARING_JOBS = {"instrument_check", "desk_review"}                          # they do not address the equipment
HUMAN_CLEARERS = {"technician", "planner", "reliability_engineer", "admin"}


def clears_latches(o, extra_non_clearing=()) -> bool:
    """Whether the order's job addresses the equipment. Data and review jobs never do, whatever a site calls them: the
    shipped names, the data and review jobs recorded in a system order's explanation (the decision config it was raised
    under), and any the caller names (the site's decision config, `recorded_non_clearing_jobs`)."""
    ex = o["explanation"] if "explanation" in o.keys() else json.loads(o["explanation_json"] or "{}")
    pol = (ex or {}).get("policy") or {}
    recorded = {pol.get(k) for k in ("data_job", "review_job")} - {None}
    return o["job_type"] not in NON_CLEARING_JOBS | recorded | set(extra_non_clearing or ())


def recorded_non_clearing_jobs(c) -> set:
    """The data and review jobs of every decision config the engine has applied in this database (each system order's
    explanation records its policy). Completion uses them for every order, manual and external ones too, so a site's
    renamed data or review job never clears a latch whichever path completes it (fail closed: names are never dropped)."""
    rows = c.execute("SELECT DISTINCT json_extract(explanation_json, '$.policy.data_job'), json_extract(explanation_json, '$.policy.review_job') "
                     "FROM work_orders WHERE origin = 'system'")
    return {j for r in rows for j in r if isinstance(j, str)}


def addresses_latch(c, o, since_ms: int) -> bool:
    """Whether the order belongs to the latched condition that began at `since_ms`: raised after it began, or linked to
    it by a system escalation recorded after it began. The decision engine escalates an order awaiting approval (or
    deferred, which brings it back for approval) that predates a new or escalated latch in place instead of raising a
    duplicate, but only for the recommended, inspection or urgent job (decision._decide); the escalation event is the
    link. Re-prioritisation by a person, or before the latch began, does not link."""
    if parse_ts(o["created_at"]) >= since_ms:
        return True
    return any(parse_ts(r["ts"]) >= since_ms for r in c.execute(
        "SELECT ts FROM work_order_events WHERE wo_id = ? AND action = 'reprioritise' AND role = 'system'", (o["wo_id"],)))


def _latch_keep_reasons(c, o, out: "Outcome", role: str, s, extra_non_clearing=()) -> list[str]:
    """Why completing this order must NOT clear the asset's latched risk (empty list: it may)."""
    keep = []
    if out.findings_code not in CLEARING_FINDINGS:
        keep.append(f"outcome '{out.findings_code}' does not record an inspection")
    if not clears_latches(o, extra_non_clearing):
        keep.append(f"a {o['job_type']} does not address a latched equipment risk")
    if role not in HUMAN_CLEARERS:
        keep.append(f"completed by the '{role}' role, not by a person")
    if s.latched_since_ms is None:                     # fail closed: an unknown start cannot be shown to precede the order
        keep.append("the start of the latched condition is unknown; dismiss it with a reason or let a new assessment decide")
    elif not addresses_latch(c, o, s.latched_since_ms):
        keep.append("the order was raised before the recorded start of the latched condition (on a database upgraded to schema 7 that start "
                    "may be an upper bound backfilled at upgrade); raise a new order, or dismiss the warning with a reason")
    return keep


def _audit_asset(db, c, actor, action, asset_id, payload):
    """Latch changes belong to the asset's own audit history (entity 'asset'), like dismissals."""
    auditlog.append(c, actor=actor, action=action, entity="asset", entity_id=asset_id, payload=payload, key=db.audit_key, key_id=db.audit_key_id)


def complete(db, wo_id: str, actor: str, role: str, outcome: dict, expected_version: int | None = None, idempotency_key: str | None = None,
             non_clearing_jobs=None) -> dict:
    """`non_clearing_jobs`: the site's data and review job names (decision.non_clearing_jobs), which never clear a latch.
    Those recorded by the engine in this database (`recorded_non_clearing_jobs`) apply whether or not the caller passes them."""
    out = Outcome(**outcome)
    if out.returned_to_service_at:
        parse_ts(out.returned_to_service_at)
    with db.tx() as c:
        o = c.execute("SELECT * FROM work_orders WHERE wo_id = ?", (wo_id,)).fetchone()
        if o is None:
            raise WorkflowError(f"unknown work order {wo_id}")
        if idempotency_key:
            ev = c.execute("SELECT action FROM work_order_events WHERE wo_id = ? AND idempotency_key = ?", (wo_id, idempotency_key)).fetchone()
            if ev is not None:
                if ev["action"] != "complete":
                    raise IdempotencyConflict(f"idempotency key {idempotency_key!r} was used for {ev['action']}, not complete")
                return _row(o, c)
        if expected_version is not None and int(expected_version) != o["version"]:
            raise ConcurrencyConflict(f"work order {wo_id} is at version {o['version']}, request expected {expected_version}")
        flags = _flags(o, out)
        s = health._state_from_conn(c, o["asset_id"])
        nc = set(non_clearing_jobs or ()) | recorded_non_clearing_jobs(c)
        keep = _latch_keep_reasons(c, o, out, role, s, nc) if s is not None and s.latched_risk != "NONE" else []
        if keep:
            flags.append("latch_kept")
        _apply(db, c, o, "complete", actor, role, "", {"outcome": out.model_dump(), "flags": flags}, idempotency_key)
        ts = now_iso()
        c.execute("INSERT INTO outcomes (wo_id, recorded_by, recorded_at, findings_code, failure_confirmed, root_cause, actions_taken, parts_used_json, "
                  "downtime_hours, returned_to_service_at, notes, flags_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                  (wo_id, actor, ts, out.findings_code, out.failure_confirmed, out.root_cause, out.actions_taken, json.dumps(out.parts_used),
                   out.downtime_hours, out.returned_to_service_at, out.notes, json.dumps(flags)))
        c.execute("UPDATE assets SET last_maintenance_at = ?, updated_at = ? WHERE asset_id = ?", (ts, ts, o["asset_id"]))
        if s is not None and s.latched_risk != "NONE" and keep:
            kept = states.replace(s, notes=tuple(list(s.notes) + [f"latch kept after {wo_id} completed: " + "; ".join(keep)]))
            health._store_state(c, o["asset_id"], kept, None)
            _audit_asset(db, c, actor, "asset_state.latch_kept", o["asset_id"], {"wo_id": wo_id, "role": role, "reasons": keep, "state": s.labels()})
        elif s is not None and s.latched_risk != "NONE":
            new = states.clear_risk(s, event="maintenance_completed", actor=actor, role=role,
                                    reason=f"{wo_id} completed: {out.findings_code}; {out.actions_taken}")
            health._store_state(c, o["asset_id"], new, None)
            _audit_asset(db, c, actor, "asset_state.maintenance_completed", o["asset_id"],
                         {"wo_id": wo_id, "role": role, "before": s.labels(), "after": new.labels()})
        return _row(c.execute("SELECT * FROM work_orders WHERE wo_id = ?", (wo_id,)).fetchone(), c)


REPRIORITISERS = APPROVERS | {"system"}
REPRIORITISABLE = {"DRAFT", "PENDING_APPROVAL", "APPROVED", "SCHEDULED", "DEFERRED"}


def reprioritise(db, wo_id: str, priority_class: str, priority_score: float | None, due_by_ms: int | None, explanation: dict, actor: str, role: str,
                 reason: str, bring_back: bool = False, expected_version: int | None = None) -> dict:
    """Change an open order's priority and due date (no state change), with an event and an audit record.

    - A score of None keeps the order's score: a manual re-prioritisation does not recompute the evidence.
    - A system escalation never postpones work: the earlier of the two due dates is kept. A person may set any date.
    - An empty explanation keeps the order's explanation; its due date is kept in step with the order's.
    - The event records only the fields that changed.
    A deferred order escalated to P1, or with `bring_back` (the decision engine: a higher class, or a new latched
    condition), comes back for approval under the caller's role: a deferral must not hide a newly urgent condition."""
    if role not in REPRIORITISERS:
        raise RolePermissionError(f"role {role!r} may not re-prioritise work orders")
    if priority_class not in CLASS_ORDER:
        raise WorkflowError("priority_class must be P1, P2 or P3")
    if not (reason or "").strip():
        raise WorkflowError("a reason is required to re-prioritise")
    with db.tx() as c:
        o = c.execute("SELECT * FROM work_orders WHERE wo_id = ?", (wo_id,)).fetchone()
        if o is None:
            raise WorkflowError(f"unknown work order {wo_id}")
        if o["state"] not in REPRIORITISABLE:
            raise WorkflowError(f"cannot re-prioritise a work order in state {o['state']}")
        if expected_version is not None and int(expected_version) != o["version"]:
            raise ConcurrencyConflict(f"work order {wo_id} is at version {o['version']}, request expected {expected_version}")
        ts = now_iso()
        due = o["due_by_ms"] if due_by_ms is None else int(due_by_ms)
        if role == "system" and o["due_by_ms"] is not None:
            due = min(due, o["due_by_ms"])
        score = o["priority_score"] if priority_score is None else priority_score
        ex = dict(explanation) if explanation else json.loads(o["explanation_json"] or "{}")
        if due is not None and ex.get("due_by") is not None and ex["due_by"] != iso(due):
            ex["due_by_rule"] = (f"the earlier due date of {wo_id} was kept (this assessment's rule gave {ex['due_by']}: {ex.get('due_by_rule', '')})"
                                 if role == "system" else f"set by {actor} ({role}): {reason}")
            ex["due_by"] = iso(due)
        old = {"priority_class": o["priority_class"], "due_by_ms": o["due_by_ms"], "priority_score": o["priority_score"]}
        new = {"priority_class": priority_class, "due_by_ms": due, "priority_score": score}
        changed = [k for k in old if old[k] != new[k]]
        data = {"from": {k: old[k] for k in changed}, "to": {k: new[k] for k in changed}}
        c.execute("UPDATE work_orders SET priority_class = ?, priority_score = ?, due_by_ms = ?, explanation_json = ?, version = version + 1, "
                  "updated_at = ? WHERE wo_id = ?", (priority_class, score, due, json.dumps(ex), ts, wo_id))
        c.execute("INSERT INTO work_order_events (wo_id, ts, actor, role, action, from_state, to_state, reason, data_json) VALUES (?,?,?,?,'reprioritise',?,?,?,?)",
                  (wo_id, ts, actor, role, o["state"], o["state"], reason, json.dumps(data)))
        _audit(db, c, actor, "work_order.reprioritise", wo_id, {**data, "role": role, "reason": reason})
        if o["state"] == "DEFERRED" and (priority_class == "P1" or bring_back):
            o2 = c.execute("SELECT * FROM work_orders WHERE wo_id = ?", (wo_id,)).fetchone()
            _apply(db, c, o2, "reactivate", actor, role, f"escalated to {priority_class} while deferred: {reason}", {}, None)
        return _row(c.execute("SELECT * FROM work_orders WHERE wo_id = ?", (wo_id,)).fetchone(), c)


def reactivate_due(db, now_ms: int, actor: str = "system", asset_ids: set | None = None) -> list[dict]:
    """Deferred orders whose 'back for approval' date has passed return to PENDING_APPROVAL (audited). Each order is
    handled on its own: a failure is reported (`error`, with the order) and the others still come back."""
    out = []
    with db.connect() as c:
        due = [(r["wo_id"], r["asset_id"]) for r in c.execute("SELECT wo_id, asset_id FROM work_orders WHERE state = 'DEFERRED' AND deferred_until_ms "
                                                               "IS NOT NULL AND deferred_until_ms <= ?", (int(now_ms),))
               if asset_ids is None or r["asset_id"] in asset_ids]
    for w, asset_id in due:
        try:
            o = transition(db, w, "reactivate", actor=actor, role="system", reason="deferral period ended; back for approval",
                           idempotency_key=f"reactivate:{w}:{int(now_ms) // 60000}")
        except Exception as e:                                 # e.g. a state change since the query, or a key already used
            out.append({"asset_id": asset_id, "action": "error", "wo_id": w, "note": f"reactivation failed: {type(e).__name__}: {e}"})
            continue
        out.append({"asset_id": o["asset_id"], "action": "reactivated", "wo_id": w, "priority_class": o["priority_class"]})
    return out


def missing_outcomes(db) -> list[dict]:
    with db.connect() as c:
        rows = c.execute("SELECT w.* FROM work_orders w LEFT JOIN outcomes o ON o.wo_id = w.wo_id WHERE w.state IN ('COMPLETED', 'CLOSED') "
                         "AND o.wo_id IS NULL ORDER BY w.wo_id").fetchall()
        return [_row(r) for r in rows]
