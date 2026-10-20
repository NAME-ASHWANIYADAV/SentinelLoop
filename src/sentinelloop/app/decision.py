"""Decision engine: from an asset's state and latest assessment to a recommended job, a priority, a due date and an
explanation. Deterministic and inspectable; no learned component decides priorities.

Rules (all thresholds in DecisionConfig, recorded in every explanation):
- URGENT_REVIEW -> the asset type's repair job, P1.
- INSPECTION_RECOMMENDED -> inspection, P2; P1 if the asset has a safety impact and P(failure before the decision
  horizon) >= p_safety.
- NORMAL_MONITORING on a safety-impact asset with p_safety <= P < p_inspect -> inspection, P2 ("safety-critical asset").
- DATA_QUALITY_FAILURE -> instrument check (or inspection if the type has none), P2 for criticality A/B, P3 for C;
  none for a whole-feed delay.
- MODEL_OUT_OF_SCOPE / MODEL_UNAVAILABLE -> for criticality A only, a P3 manual review: no valid prediction exists, so
  the asset falls back to people, never to "healthy".
- A latched inspection hidden by a data, scope or model failure keeps its inspection (P2), in addition to any data job.
Due date (latest start): with a prediction, the time t* at which P(RUL <= t*) reaches p_accept, minus the job
duration; without one, a policy default per priority class. Score (used only to order work within a class): expected
loss avoided per technician-hour = P(failure before horizon) x consequence / (duration x crew). Without a prediction
there is no score; no probability is invented.
"""
from __future__ import annotations

import functools
import math
from dataclasses import asdict, dataclass, field

from . import health, registry, workorders
from .states import HealthState as H
from .timeutil import HOUR_MS, iso, now_ms as _now_ms, parse_ts

CLASS_RANK = {"P1": 1, "P2": 2, "P3": 3}
MAX_HOURS = 8760.0          # a sanity bound on configured due dates and suppression periods: one year
CLOSED_STATES = ("COMPLETED", "CLOSED", "REJECTED", "CANCELLED")


@dataclass(frozen=True)
class DecisionConfig:
    p_accept: float = 0.05
    p_safety: float = 0.05
    labour_cost_per_h: float = 1.0
    downtime_cost_per_h: float = 0.0
    default_due_h: dict = field(default_factory=lambda: {"P1": 24, "P2": 168, "P3": 720})
    urgent_job: str = "repair"
    review_job: str = "desk_review"       # out of scope / unavailable on a criticality-A asset, when the type defines it
    inspection_job: str = "inspect"
    data_job: str = "instrument_check"
    # after a reasoned rejection, the same condition (same asset and job, not more urgent; the same latch episode while a
    # latch is active, otherwise the same state) is not re-raised for:
    reject_suppress_h: dict = field(default_factory=lambda: {"P1": 24, "P2": 168, "P3": 720})
    version: int = 2
    site_configured: bool = False         # True only when loaded from a site's decision config file


def _number(key: str, v) -> float:
    """A finite real number; booleans, strings and null are refused, not coerced."""
    try:
        ok = not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v)
    except OverflowError:                       # an integer beyond the float range
        ok = False
    if not ok:
        raise ValueError(f"{key} must be a finite number, got {v!r}")
    return float(v)


def non_clearing_jobs(cfg: "DecisionConfig") -> set:
    """Jobs that never address the equipment, so never clear a latch: the shipped names and the site's data and review jobs."""
    return set(workorders.NON_CLEARING_JOBS) | {cfg.data_job, cfg.review_job}


def load_config_text(text: str) -> "DecisionConfig":
    """A site's decision parameters from YAML. Refused (ValueError): unknown keys; p_accept or p_safety not a number in
    [0, 1); a negative cost; default_due_h or reject_suppress_h without exactly the keys P1, P2 and P3 (a partial map is
    refused, not merged), or with hours outside (0, 8760] (due dates) or [0, 8760] (suppression); empty job names, and
    an urgent or inspection job that is a data or review job. Values must be finite numbers, never booleans or strings."""
    import yaml
    raw = yaml.safe_load(text) or {}
    if not isinstance(raw, dict):
        raise ValueError("decision config must be a mapping")
    known = set(DecisionConfig.__dataclass_fields__) - {"version", "site_configured"}
    bad = sorted(set(raw) - known)
    if bad:
        raise ValueError(f"unknown decision config keys {bad}; allowed: {sorted(known)}")
    for k in ("p_accept", "p_safety"):            # p = 1 would disable the safety rule or put due dates past the interval
        if k in raw and not 0.0 <= _number(k, raw[k]) < 1.0:
            raise ValueError(f"{k} must be a probability in [0, 1), got {raw[k]!r}")
    for k in ("labour_cost_per_h", "downtime_cost_per_h"):
        if k in raw and _number(k, raw[k]) < 0:
            raise ValueError(f"{k} must be >= 0")
    for k, zero_ok in (("default_due_h", False), ("reject_suppress_h", True)):
        if k not in raw:
            continue
        v = raw[k]
        if not isinstance(v, dict) or set(v) != set(CLASS_RANK):
            got = sorted(map(str, v)) if isinstance(v, dict) else v
            raise ValueError(f"{k} must give hours for exactly P1, P2 and P3, got {got!r}")
        for pc, h in v.items():
            h = _number(f"{k}.{pc}", h)
            if h < 0 or (h == 0 and not zero_ok) or h > MAX_HOURS:
                raise ValueError(f"{k}.{pc} must be {'>= 0' if zero_ok else '> 0'} and at most {MAX_HOURS:.0f} hours, got {v[pc]!r}")
    for k in ("urgent_job", "review_job", "inspection_job", "data_job"):
        if k in raw and (not isinstance(raw[k], str) or not raw[k].strip()):
            raise ValueError(f"{k} must be a job name, got {raw[k]!r}")
    cfg = DecisionConfig(**raw, site_configured=True)
    side = non_clearing_jobs(cfg)
    for k in ("urgent_job", "inspection_job"):     # an equipment job named like a data or review job would never clear a latch
        if getattr(cfg, k) in side:
            raise ValueError(f"{k} {getattr(cfg, k)!r} is a data or review job ({sorted(side)}); it must be a job that addresses the equipment")
    return cfg


def load_config(path) -> "DecisionConfig":
    from pathlib import Path
    return load_config_text(Path(path).read_text(encoding="utf-8"))


@dataclass
class Recommendation:
    asset_id: str
    job_type: str
    priority_class: str
    priority_score: float | None
    due_by_ms: int
    explanation: dict
    assessment_id: str | None


def inverse_cdf(p: float, lower: float, point: float, upper: float, level: float) -> float:
    """Smallest t with P(RUL <= t) >= p on the piecewise-linear CDF used by risk.p_fail_before."""
    point = min(max(point, lower), upper)
    a = (1.0 - level) / 2.0
    dl, du = point - lower, upper - point
    knots = [(lower - dl, 0.0), (lower, a), (point, 0.5), (upper, 1.0 - a), (upper + du, 1.0)]
    p = min(max(p, 0.0), 1.0)
    for (x0, y0), (x1, y1) in zip(knots, knots[1:]):
        if p <= y1:
            return x0 if y1 == y0 else x0 + (x1 - x0) * (p - y0) / (y1 - y0)
    return knots[-1][0]


def recommend(asset, asset_type, assessment: dict | None, state, cfg: DecisionConfig, now_ms: int | None = None) -> Recommendation | None:
    """The main recommendation for the asset (the first of `recommendations`), or None."""
    recs = recommendations(asset, asset_type, assessment, state, cfg, now_ms=now_ms)
    return recs[0] if recs else None


def recommendations(asset, asset_type, assessment: dict | None, state, cfg: DecisionConfig, now_ms: int | None = None) -> list[Recommendation]:
    """Every job the asset's state calls for, the main one first. Usually one; a latched inspection hidden by a data
    failure gets its inspection (PD-18) and, unless the whole feed is late, the data job as well."""
    now = int(now_ms if now_ms is not None else _now_ms())
    return [build() for _, build in _planned(asset, asset_type, assessment, state, cfg, now)]


def _planned(asset, asset_type, assessment, state, cfg, now) -> list:
    """The jobs the state calls for, each as (job, function building its Recommendation): generate builds and decides
    each on its own, so one that cannot be built (a configured job the asset type lacks) never loses the others."""
    if state is None or assessment is None:
        return []
    eff = state.effective
    risk = assessment.get("risk") or {}
    p = risk.get("p_fail_decision_horizon")
    safety = bool(asset.consequence.safety_impact)
    plan = []                                   # (job, priority class, why)
    if eff == H.DATA_QUALITY_FAILURE:
        if state.latched_risk == "INSPECTION":
            plan.append((cfg.inspection_job, "P2", [f"{eff.value}, but an inspection recommended earlier is still pending; it is not cancelled "
                                                    "by the data failure"]))
        dq = [r for r in (assessment.get("reasons") or []) if r.split(":")[0] in health.DQ_CODES]
        if not (dq and all(r.startswith("data_delivery_delay") for r in dq)):    # a late feed: a data-path alert, not a job at the asset
            job = cfg.data_job if cfg.data_job in asset_type.jobs else cfg.inspection_job
            if job not in [j for j, _, _ in plan]:
                plan.append((job, "P2" if asset.criticality in ("A", "B") else "P3",
                             ["data quality failure: the readings cannot support a prediction; check the instrumentation"]))
    else:
        one = _plan_one(asset, asset_type, eff, state, cfg, p, safety)
        if one is not None:
            plan.append(one)
    return [(job, functools.partial(_build, asset, asset_type, assessment, state, cfg, now, eff, risk, p, job, pc, why)) for job, pc, why in plan]


def _plan_one(asset, asset_type, eff, state, cfg, p, safety):
    why = []
    if eff == H.URGENT_REVIEW:
        job, pc = cfg.urgent_job, "P1"
        if p is not None:
            why.append("urgent review: the asset may fail before the earliest feasible intervention")
        else:          # anomaly-only model or no valid prediction: no failure-time claim (PD-11)
            why.append("urgent review: severe sustained deviation from normal behaviour (a policy threshold, not a failure-time prediction); "
                       "inspect promptly")
        if job not in asset_type.jobs:
            job = cfg.inspection_job
            why.append(f"asset type defines no {cfg.urgent_job!r} job (the model cannot say which repair is needed): urgent inspection")
    elif eff == H.INSPECTION_RECOMMENDED:
        job, pc = cfg.inspection_job, "P2"
        why.append("inspection recommended by the assessment")
        if safety and p is not None and p >= cfg.p_safety:
            pc = "P1"
            why.append(f"safety-impact asset with P(failure) {p:.2f} (model-implied, not calibrated) >= safety limit {cfg.p_safety}")
    elif eff in (H.MODEL_OUT_OF_SCOPE, H.MODEL_UNAVAILABLE) and state.latched_risk == "INSPECTION":
        job, pc = cfg.inspection_job, "P2"
        why.append(f"{eff.value}, but an inspection recommended earlier is still pending; it is not cancelled by the model's silence")
    elif eff in (H.MODEL_OUT_OF_SCOPE, H.MODEL_UNAVAILABLE):
        if asset.criticality != "A":
            return None
        job = cfg.review_job if cfg.review_job in asset_type.jobs else cfg.inspection_job
        pc = "P3"
        why.append(f"{eff.value}: no valid prediction for a criticality-A asset; a person reviews it instead of assuming health")
    elif eff == H.NORMAL_MONITORING and safety and p is not None and p >= cfg.p_safety:
        job, pc = cfg.inspection_job, "P2"
        why.append(f"safety-critical asset: P(failure) {p:.2f} (model-implied, not calibrated) >= safety limit {cfg.p_safety} "
                   "although below the inspection threshold")
    else:
        return None
    return job, pc, why


def _build(asset, asset_type, assessment, state, cfg, now, eff, risk, p, job, pc, why) -> Recommendation:
    cons = asset.consequence
    safety = bool(cons.safety_impact)
    spec = asset_type.jobs.get(job)
    if spec is None:
        raise ValueError(f"asset type {asset_type.asset_type_id} has no job {job!r}")
    consequence = cons.cost_per_failure + cons.downtime_hours * cfg.downtime_cost_per_h
    lower, point, upper, level = (assessment.get("rul_lower_hours"), assessment.get("rul_point_hours"), assessment.get("rul_upper_hours"),
                                  assessment.get("interval_level"))
    if lower is not None and p is not None:
        t_star = inverse_cdf(cfg.p_accept, lower, point, upper, level)
        due = now + int(round(max(0.0, t_star - spec.duration_h) * HOUR_MS))
        due_rule = (f"latest start keeping P(failure before the job ends) <= {cfg.p_accept}: t* = {t_star:.1f} h from the interval, "
                    f"minus the {spec.duration_h} h job")
        score = p * consequence / (spec.duration_h * spec.crew_size)
        expected_loss = p * consequence
    else:
        due = now + int(cfg.default_due_h[pc] * HOUR_MS)
        due_rule = f"no valid prediction: policy default of {cfg.default_due_h[pc]} h for {pc}"
        score, expected_loss = None, None
        a_score = assessment.get("anomaly_score")
        if a_score is not None and eff in (H.URGENT_REVIEW, H.INSPECTION_RECOMMENDED):
            score = max(float(a_score), 0.0) * consequence / (spec.duration_h * spec.crew_size)
    explanation = {"state": eff.value, "labels": state.labels(), "reasons": list(assessment.get("reasons") or []), "why": "; ".join(why),
                   "rul_hours": [lower, point, upper] if lower is not None else None, "interval_level": level,
                   "p_fail_decision_horizon": p, "decision_horizon_hours": risk.get("decision_horizon_hours"),
                   "consequence": {"cost_per_failure": cons.cost_per_failure, "downtime_hours": cons.downtime_hours, "safety_impact": safety,
                                   "environmental_impact": cons.environmental_impact, "cost_unit": cons.cost_unit, "criticality": asset.criticality},
                   "expected_loss": expected_loss, "intervention_cost": spec.duration_h * spec.crew_size * cfg.labour_cost_per_h,
                   "score_rule": ("P(failure before horizon) x consequence / (duration x crew)" if p is not None else
                                  "anomaly-ranked: deviation ratio x consequence / (duration x crew); not a probability" if score is not None else
                                  "no score without a prediction"),
                   "due_by": iso(due), "due_by_rule": due_rule, "job": {"type": job, "duration_h": spec.duration_h, "crew": spec.crew_size,
                                                                         "skill": spec.skill, "parts": spec.parts},
                   "assessment_id": assessment.get("assessment_id"), "policy": asdict(cfg)}
    return Recommendation(asset.asset_id, job, pc, score, due, explanation, assessment.get("assessment_id"))


def generate(db, cfg: DecisionConfig, actor: str = "system", now_ms: int | None = None, site_id: str | None = None) -> list[dict]:
    """Turn every active asset's latest state into the work orders it calls for, one per recommended job: usually one
    per asset, two when a data failure hides a latched inspection. New system orders start PENDING_APPROVAL.

    - An open order stands in for a recommendation only if completing it could satisfy it (`_decide`); otherwise the
      needed order is raised in addition. A condition has one open order, with one exception: while lower-class work on
      it is in progress, a more urgent recommendation gets its own, separate order (PD-18); otherwise work in progress is
      left alone (`unchanged`). A higher-priority recommendation escalates the order that stands in for it, which keeps
      its state unless it was deferred (a deferred order escalated to P1, or linked to a new latched condition, comes
      back for approval). Only an order awaiting approval, or deferred, is linked to a latch that began after it.
    - A recommendation from an assessment that already produced an order for that job (even one a person rejected) is
      not re-raised (`already_decided`): a new order needs a new assessment. A reasoned rejection suppresses the same
      condition for a policy period (`suppressed`).
    - Each asset, each recommended job and each deferred order that comes back is handled independently: an error is
      recorded (`error`) and audited, and the run continues, so one bad record can never suppress the other
      recommendations for the asset or the rest of the fleet."""
    now = int(now_ms if now_ms is not None else _now_ms())
    out = []
    types = {t.asset_type_id: t for t in registry.list_asset_types(db)}
    assets = registry.list_assets(db, site_id=site_id, status="active")
    for r in workorders.reactivate_due(db, now, actor=actor, asset_ids={a.asset_id for a in assets}):
        out.append(r)
        if r["action"] == "error":
            _audit_error(db, actor, r["asset_id"], {"wo_id": r["wo_id"], "error": r["note"]})
    for a in assets:
        done = []                                              # kept even if a later recommendation for the asset fails
        try:
            _generate_one(db, a, types, cfg, actor, now, done)
        except Exception as e:                                 # isolate the failure; never fail open for the other assets
            done.append({"asset_id": a.asset_id, "action": "error", "note": f"{type(e).__name__}: {e}"})
            _audit_error(db, actor, a.asset_id, {"error": f"{type(e).__name__}: {e}"})
        out.extend(done)
    return out


def _audit_error(db, actor, asset_id, payload):
    from . import auditlog
    try:
        with db.tx() as c:
            auditlog.append(c, actor=actor, action="decision.error", entity="asset", entity_id=asset_id, payload=payload,
                            key=db.audit_key, key_id=db.audit_key_id)
    except Exception:
        pass


def _generate_one(db, a, types, cfg, actor, now, out: list) -> list[dict]:
    st = health.asset_state(db, a.asset_id)
    for job, build in _planned(a, types[a.asset_type_id], health.latest_assessment(db, a.asset_id), st, cfg, now):
        try:                                                   # one job that fails never loses the asset's other jobs
            out.extend(_decide(db, a, st, build(), cfg, actor, now))
        except Exception as e:
            out.append({"asset_id": a.asset_id, "action": "error", "job_type": job, "note": f"{type(e).__name__}: {e}"})
            _audit_error(db, actor, a.asset_id, {"job_type": job, "error": f"{type(e).__name__}: {e}"})
    return out


def _latch_start(st) -> int | None:
    return st.latched_since_ms if st is not None and st.latched_risk != "NONE" else None


def _rank(o):
    return CLASS_RANK[o["priority_class"]], o["due_by_ms"] if o["due_by_ms"] is not None else float("inf")


def _higher(rec, o) -> bool:
    return CLASS_RANK[rec.priority_class] < CLASS_RANK[o["priority_class"]] or (
        o["due_by_ms"] is not None and rec.due_by_ms < o["due_by_ms"] and rec.priority_class == o["priority_class"])


LINKABLE = ("PENDING_APPROVAL", "DEFERRED")       # a linked order is, or comes back, up for approval for its new purpose


def _site_non_clearing(db, cfg) -> set:
    with db.connect() as c:
        return non_clearing_jobs(cfg) | workorders.recorded_non_clearing_jobs(c)


def _stand_in_jobs(rec, cfg) -> set:
    """Jobs whose order may stand in for an equipment recommendation: the recommended job, the inspection and the urgent job."""
    return {rec.job_type, cfg.inspection_job, cfg.urgent_job}


def _decide(db, a, st, rec, cfg, actor, now) -> list[dict]:
    """One recommendation against the asset's open orders (PD-16, PD-18; re-review decision-lifecycle-01, latching-states-04).

    An open order stands in for the recommendation only if completing it could satisfy it. A DRAFT never does: nobody
    has asked for it to be approved.
    - A data or review job (instrument check, desk review, as the site names them) is matched by an open order for that
      same job. It never stands in for an equipment job. An open equipment order covers a review (a person is already
      going to look at the asset) but never a data job.
    - An equipment job (inspection, repair) is matched by an open order for the recommended, inspection or urgent job
      (`_stand_in_jobs`; a routine job such as a lubrication never stands in) that, while a latch is active, could clear
      the CURRENT latch (`workorders.addresses_latch`): raised after the latch began, or linked to it by a system
      escalation recorded after it began.
    Such an order that predates the latch (an inspection when the latch escalates to URGENT, an order left open across a
    dismissal and a re-latch) is LINKED only while it awaits approval or is deferred: it is escalated in place (its class
    and due date only ever move earlier; a deferred one comes back for approval), so a planner approves it for its new
    purpose, and that escalation event lets a qualifying completion clear the latch. One already approved, scheduled or
    in progress is superseded: the latch gets its own order, as an urgent condition during lower-priority work always
    did. A latch whose start is unknown cannot be cleared by any order (fail closed), so any qualifying order stands in
    for it rather than adding orders that could not clear it either."""
    nc = _site_non_clearing(db, cfg)
    open_ = [o for o in workorders.list_orders(db, asset_id=a.asset_id) if o["state"] not in CLOSED_STATES and o["state"] != "DRAFT"]
    since = _latch_start(st)
    if rec.job_type in nc:
        cands, covering = [o for o in open_ if o["job_type"] == rec.job_type], None
        eq = sorted((o for o in open_ if workorders.clears_latches(o, nc)), key=_rank)
        if not cands and eq and rec.job_type == cfg.review_job:
            return [{"asset_id": a.asset_id, "action": "unchanged", "wo_id": eq[0]["wo_id"], "priority_class": eq[0]["priority_class"],
                     "note": f"open {eq[0]['job_type']} order covers it: a person is already going to look at the asset"}]
    else:
        cands = [o for o in open_ if o["job_type"] in _stand_in_jobs(rec, cfg) and workorders.clears_latches(o, nc)]
        with db.connect() as c:
            covering = None if since is None else {o["wo_id"] for o in cands if workorders.addresses_latch(c, o, since)}
    covers = [o for o in cands if covering is None or o["wo_id"] in covering]
    ready = sorted((o for o in covers if o["state"] in workorders.REPRIORITISABLE), key=_rank)
    busy = sorted((o for o in covers if o["state"] not in workorders.REPRIORITISABLE), key=_rank)
    if ready:
        o = ready[0]
        if _higher(rec, o):
            return _escalate(db, a, rec, o, actor, link=False)
        return [{"asset_id": a.asset_id, "action": "unchanged", "wo_id": o["wo_id"], "priority_class": o["priority_class"],
                 "note": "open order covers it" + (f" (deferred until {o['deferred_until']})" if o["state"] == "DEFERRED" else "")}]
    if busy:
        o = busy[0]
        if CLASS_RANK[rec.priority_class] >= CLASS_RANK[o["priority_class"]]:
            return [{"asset_id": a.asset_id, "action": "unchanged", "wo_id": o["wo_id"], "priority_class": o["priority_class"],
                     "note": f"order {o['state'].lower().replace('_', ' ')}; the work is under way"}]
        rec.explanation["why"] += f"; raised although {o['wo_id']} ({o['priority_class']}) is in progress: the condition became more urgent"
        return _create_checked(db, a, st, rec, cfg, actor, now)
    linkable = sorted((o for o in cands if o["state"] in LINKABLE), key=_rank)
    if linkable:
        return _escalate(db, a, rec, linkable[0], actor, link=True)
    other = sorted(cands, key=_rank)
    if other:
        o = other[0]
        rec.explanation["why"] += (f"; raised although {o['wo_id']} ({o['job_type']} {o['priority_class']}) is {o['state'].lower().replace('_', ' ')}: "
                                   "it was raised before the current latched condition began and was not up for approval to link to it, "
                                   "so completing it cannot clear it")
    return _create_checked(db, a, st, rec, cfg, actor, now)


def _escalate(db, a, rec, o, actor, link: bool) -> list[dict]:
    """Escalate (and, with `link`, link to the current latch) an open order that stands in for `rec`. The system never
    lowers a class; workorders.reprioritise keeps the earlier due date, and the score when the recommendation has none."""
    pc = min(rec.priority_class, o["priority_class"], key=CLASS_RANK.get)
    rose = CLASS_RANK[pc] < CLASS_RANK[o["priority_class"]]
    earlier = o["due_by_ms"] is None or rec.due_by_ms < o["due_by_ms"]
    ex = dict(rec.explanation)
    if o["job_type"] != rec.job_type:      # say which job the order really is; the recommended one is kept for the reader
        ex["recommended_job"], ex["job"] = ex["job"], {"type": o["job_type"], "duration_h": o["duration_h"], "crew": o["crew_size"],
                                                       "skill": o["required_skill"], "parts": o["parts"]}
        ex["why"] += f"; {o['wo_id']} ({o['job_type']}) stands in for the recommended {rec.job_type}"
    if link:
        ex["why"] += f"; {o['wo_id']} was raised before the current latched condition began and is linked to it by this escalation"
    w = workorders.reprioritise(db, o["wo_id"], pc, rec.priority_score, rec.due_by_ms, ex, actor=actor, role="system", bring_back=rose or link,
                                reason=f"new assessment {rec.assessment_id}: {ex['why']}; recommended job {rec.job_type}")
    r = {"asset_id": a.asset_id, "action": "escalated" if rose or earlier else "linked", "wo_id": o["wo_id"], "priority_class": pc}
    if link:
        r["note"] = "raised before the current latched condition began; linked to it, so completing it can clear it"
    if w["state"] == "DEFERRED":
        r["note"] = f"still deferred until {w['deferred_until']}"
    return [r]


def _create_checked(db, a, st, rec, cfg, actor, now) -> list[dict]:
    """Every creation path: not twice for one assessment and job, and not against a reasoned rejection of the same condition."""
    key = f"rec:{rec.assessment_id}:{rec.job_type}"
    with db.connect() as c:
        prior = c.execute("SELECT wo_id, state FROM work_orders WHERE idempotency_key = ? OR (assessment_id = ? AND origin = 'system' AND job_type = ?)",
                          (key, rec.assessment_id, rec.job_type)).fetchone()
    if prior is not None:
        return [{"asset_id": a.asset_id, "action": "already_decided", "wo_id": prior["wo_id"],
                 "note": f"assessment {rec.assessment_id} already produced {prior['wo_id']} ({prior['state']}); a new order needs a new assessment"}]
    sup = _suppressed_by_rejection(db, a, st, rec, cfg, now)
    if sup is not None:
        return [sup]
    return _create(db, a, rec, key, actor)


def _suppressed_by_rejection(db, a, st, rec, cfg, now) -> dict | None:
    """A planner's reasoned 'no' holds for the same condition for a policy period; escalation or a new condition re-raises.

    For an equipment job while a latch is active, the condition is the latch episode, whatever state is displayed (a
    scope or model flip does not re-raise it). The rejected order may be any order, of any origin, that stood in or
    could stand in for the recommendation (`_stand_in_jobs`: an inspection escalated for an urgent latch, a manual order
    the engine brought back for approval), and it must have belonged to the current latch (raised or linked after it
    began), so a new latch after a dismissal or a completed inspection is raised again. When the latch's start is
    unknown (an upgraded record), a rejection belongs to it unless a latch on the asset was dismissed or cleared by a
    completed order after the rejection. Otherwise the condition is the system's own order for the same job and
    displayed state. Every rejection within its period is considered, the newest first."""
    import json as _json
    with db.connect() as c:
        nc = non_clearing_jobs(cfg) | workorders.recorded_non_clearing_jobs(c)
        latched = rec.job_type not in nc and st is not None and st.latched_risk != "NONE"
        since = _latch_start(st)
        rows = c.execute("SELECT w.*, e.ts AS rejected_at, e.reason AS rejected_reason, e.actor AS rejected_by FROM work_orders w "
                         "JOIN work_order_events e ON e.wo_id = w.wo_id AND e.action = 'reject' WHERE w.asset_id = ? ORDER BY e.event_id DESC",
                         (a.asset_id,)).fetchall()
        for r in rows:
            hours = float(cfg.reject_suppress_h.get(r["priority_class"], 0))      # a class without a period: no suppression
            if now - parse_ts(r["rejected_at"]) > hours * HOUR_MS or CLASS_RANK[rec.priority_class] < CLASS_RANK[r["priority_class"]]:
                continue                                                           # expired, or the condition escalated
            if latched:
                same = r["job_type"] in _stand_in_jobs(rec, cfg) and workorders.clears_latches(r, nc) and (
                    workorders.addresses_latch(c, r, since) if since is not None else not _cleared_after(c, a.asset_id, r["rejected_at"]))
            else:
                same = (r["job_type"] == rec.job_type and r["origin"] == "system"
                        and _json.loads(r["explanation_json"] or "{}").get("state") == rec.explanation.get("state"))
            if same:
                return {"asset_id": a.asset_id, "action": "suppressed", "wo_id": r["wo_id"], "priority_class": rec.priority_class,
                        "note": f"{r['wo_id']} was rejected by {r['rejected_by']} on {r['rejected_at']} ({r['rejected_reason']}); the same "
                                f"condition is re-raised only if it escalates or after {hours:.0f} h"}
    return None


def _cleared_after(c, asset_id: str, ts: str) -> bool:
    """Whether a latch on the asset was dismissed, or cleared by a completed order, at or after `ts` (older completions
    were filed under the work order, with the asset's id)."""
    t = parse_ts(ts)
    return any(parse_ts(r[0]) >= t for r in c.execute("SELECT ts FROM audit_events WHERE entity IN ('asset', 'work_order') AND entity_id = ? "
                                                       "AND action IN ('asset_state.dismissed', 'asset_state.maintenance_completed')", (asset_id,)))


def _create(db, a, rec, key, actor) -> list[dict]:
    w = workorders.create(db, asset_id=a.asset_id, job_type=rec.job_type, priority_class=rec.priority_class,
                          title=f"{rec.job_type.replace('_', ' ').capitalize()} {a.tag} ({rec.explanation['state']})", origin="system", actor=actor, role="system",
                          idempotency_key=key, due_by=iso(rec.due_by_ms), initial_state="PENDING_APPROVAL",
                          priority_score=rec.priority_score, explanation=rec.explanation, assessment_id=rec.assessment_id)
    return [{"asset_id": a.asset_id, "action": "created", "wo_id": w["wo_id"], "priority_class": rec.priority_class}]
