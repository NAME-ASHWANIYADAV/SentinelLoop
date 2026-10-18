"""Decision engine: from an asset's state and latest assessment to a recommended job, a priority, a due date and an
explanation. Deterministic and inspectable; no learned component decides priorities.

Rules (all thresholds in DecisionConfig, recorded in every explanation):
- URGENT_REVIEW -> the asset type's repair job, P1.
- INSPECTION_RECOMMENDED -> inspection, P2; P1 if the asset has a safety impact and P(failure before the decision
  horizon) >= p_safety.
- NORMAL_MONITORING on a safety-impact asset with p_safety <= P < p_inspect -> inspection, P2 ("safety-critical asset").
- DATA_QUALITY_FAILURE -> instrument check (or inspection if the type has none), P2 for criticality A/B, P3 for C.
- MODEL_OUT_OF_SCOPE / MODEL_UNAVAILABLE -> for criticality A only, a P3 manual review: no valid prediction exists, so
  the asset falls back to people, never to "healthy".
Due date (latest start): with a prediction, the time t* at which P(RUL <= t*) reaches p_accept, minus the job
duration; without one, a policy default per priority class. Score (used only to order work within a class): expected
loss avoided per technician-hour = P(failure before horizon) x consequence / (duration x crew). Without a prediction
there is no score; no probability is invented.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from . import health, registry, workorders
from .states import HealthState as H
from .timeutil import HOUR_MS, iso, now_ms as _now_ms, parse_ts

CLASS_RANK = {"P1": 1, "P2": 2, "P3": 3}


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
    # after a reasoned rejection, the same condition (same asset, job and state, not more urgent) is not re-raised for:
    reject_suppress_h: dict = field(default_factory=lambda: {"P1": 24, "P2": 168, "P3": 720})
    version: int = 2
    site_configured: bool = False         # True only when loaded from a site's decision config file


def load_config_text(text: str) -> "DecisionConfig":
    """A site's decision parameters from YAML (only known keys; costs and due dates must be non-negative)."""
    import yaml
    raw = yaml.safe_load(text) or {}
    if not isinstance(raw, dict):
        raise ValueError("decision config must be a mapping")
    known = set(DecisionConfig.__dataclass_fields__) - {"version", "site_configured"}
    bad = sorted(set(raw) - known)
    if bad:
        raise ValueError(f"unknown decision config keys {bad}; allowed: {sorted(known)}")
    for k in ("p_accept", "p_safety", "labour_cost_per_h", "downtime_cost_per_h"):
        if k in raw and float(raw[k]) < 0:
            raise ValueError(f"{k} must be >= 0")
    for k in ("default_due_h", "reject_suppress_h"):
        if k in raw and (set(raw[k]) - {"P1", "P2", "P3"} or any(float(v) < 0 for v in raw[k].values())):
            raise ValueError(f"{k} needs P1/P2/P3 keys with non-negative hours")
    return DecisionConfig(**raw, site_configured=True)


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
    now = int(now_ms if now_ms is not None else _now_ms())
    if state is None or assessment is None:
        return None
    eff = state.effective
    risk = assessment.get("risk") or {}
    p = risk.get("p_fail_decision_horizon")
    cons = asset.consequence
    safety = bool(cons.safety_impact)
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
            why.append(f"safety-impact asset with P(failure) {p:.2f} >= safety limit {cfg.p_safety}")
    elif eff == H.DATA_QUALITY_FAILURE:
        dq = [r for r in (assessment.get("reasons") or []) if r.split(":")[0] in health.DQ_CODES]
        if dq and all(r.startswith("data_delivery_delay") for r in dq):
            return None        # the feed is late: a data-path alert (staleness report, state), not a job at the asset
        job = cfg.data_job if cfg.data_job in asset_type.jobs else cfg.inspection_job
        pc = "P2" if asset.criticality in ("A", "B") else "P3"
        why.append("data quality failure: the readings cannot support a prediction; check the instrumentation")
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
        why.append(f"safety-critical asset: P(failure) {p:.2f} >= safety limit {cfg.p_safety} although below the inspection threshold")
    else:
        return None
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
    """Turn every active asset's latest state into at most one open system work order (PENDING_APPROVAL).

    - An open order is never duplicated: a higher-priority recommendation escalates it (a deferred order escalated to P1
      comes back for approval); an order already in progress is left alone (`unchanged`, the work is under way).
    - A recommendation from an assessment that already produced an order (even one a person rejected) is not re-raised
      (`already_decided`): a new order needs a new assessment.
    - Each asset is handled independently: an error on one asset is recorded (`error`) and audited, and the run continues,
      so one bad record can never suppress recommendations for the rest of the fleet."""
    from . import auditlog

    now = int(now_ms if now_ms is not None else _now_ms())
    out = []
    types = {t.asset_type_id: t for t in registry.list_asset_types(db)}
    assets = registry.list_assets(db, site_id=site_id, status="active")
    out.extend(workorders.reactivate_due(db, now, actor=actor, asset_ids={a.asset_id for a in assets}))
    for a in assets:
        try:
            out.extend(_generate_one(db, a, types, cfg, actor, now))
        except Exception as e:                                 # isolate the failure; never fail open for the other assets
            out.append({"asset_id": a.asset_id, "action": "error", "note": f"{type(e).__name__}: {e}"})
            try:
                with db.tx() as c:
                    auditlog.append(c, actor=actor, action="decision.error", entity="asset", entity_id=a.asset_id,
                                    payload={"error": f"{type(e).__name__}: {e}"}, key=db.audit_key, key_id=db.audit_key_id)
            except Exception:
                pass
    return out


def _generate_one(db, a, types, cfg, actor, now) -> list[dict]:
    st = health.asset_state(db, a.asset_id)
    rec = recommend(a, types[a.asset_type_id], health.latest_assessment(db, a.asset_id), st, cfg, now_ms=now)
    if rec is None:
        return []
    key = f"rec:{rec.assessment_id}:{rec.job_type}"
    with db.connect() as c:
        prior = c.execute("SELECT wo_id, state FROM work_orders WHERE idempotency_key = ? OR (assessment_id = ? AND origin = 'system')",
                          (key, rec.assessment_id)).fetchone()
    open_ = [o for o in workorders.list_orders(db, asset_id=a.asset_id) if o["state"] not in ("COMPLETED", "CLOSED", "REJECTED", "CANCELLED")]
    if open_:
        o = sorted(open_, key=lambda x: (x["state"] not in workorders.REPRIORITISABLE, CLASS_RANK[x["priority_class"]]))[0]
        higher = CLASS_RANK[rec.priority_class] < CLASS_RANK[o["priority_class"]] or (
            o["due_by_ms"] is not None and rec.due_by_ms < o["due_by_ms"] and rec.priority_class == o["priority_class"])
        if o["state"] not in workorders.REPRIORITISABLE and not higher:
            return [{"asset_id": a.asset_id, "action": "unchanged", "wo_id": o["wo_id"], "priority_class": o["priority_class"],
                     "note": f"order {o['state'].lower().replace('_', ' ')}; the work is under way" if o["state"] == "IN_PROGRESS" else o["state"]}]
        if o["state"] not in workorders.REPRIORITISABLE and CLASS_RANK[rec.priority_class] < CLASS_RANK[o["priority_class"]] and prior is None:
            rec.explanation["why"] += f"; raised although {o['wo_id']} ({o['priority_class']}) is in progress: the condition became more urgent"
            return _create(db, a, rec, key, actor)
        if higher:
            workorders.reprioritise(db, o["wo_id"], rec.priority_class, rec.priority_score, rec.due_by_ms, rec.explanation, actor=actor, role="system",
                                    reason=f"new assessment {rec.assessment_id}: {rec.explanation['why']}; recommended job {rec.job_type}")
            return [{"asset_id": a.asset_id, "action": "escalated", "wo_id": o["wo_id"], "priority_class": rec.priority_class}]
        return [{"asset_id": a.asset_id, "action": "unchanged", "wo_id": o["wo_id"], "priority_class": o["priority_class"], "note": "open order covers it"}]
    if prior is not None:
        return [{"asset_id": a.asset_id, "action": "already_decided", "wo_id": prior["wo_id"],
                 "note": f"assessment {rec.assessment_id} already produced {prior['wo_id']} ({prior['state']}); a new order needs a new assessment"}]
    sup = _suppressed_by_rejection(db, a, rec, cfg, now)
    if sup is not None:
        return [sup]
    return _create(db, a, rec, key, actor)


def _suppressed_by_rejection(db, a, rec, cfg, now) -> dict | None:
    """A planner's reasoned 'no' holds for the same condition for a policy period; escalation or a new condition re-raises."""
    with db.connect() as c:
        r = c.execute("SELECT w.wo_id, w.priority_class, w.explanation_json, e.ts, e.reason, e.actor FROM work_orders w JOIN work_order_events e "
                      "ON e.wo_id = w.wo_id AND e.action = 'reject' WHERE w.asset_id = ? AND w.job_type = ? AND w.origin = 'system' "
                      "ORDER BY e.ts DESC LIMIT 1", (a.asset_id, rec.job_type)).fetchone()
    if r is None:
        return None
    import json as _json
    rejected_state = (_json.loads(r["explanation_json"] or "{}")).get("state")
    hours = float(cfg.reject_suppress_h.get(r["priority_class"], 0))
    within = now - parse_ts(r["ts"]) <= hours * HOUR_MS
    if within and CLASS_RANK[rec.priority_class] >= CLASS_RANK[r["priority_class"]] and rejected_state == rec.explanation.get("state"):
        return {"asset_id": a.asset_id, "action": "suppressed", "wo_id": r["wo_id"], "priority_class": rec.priority_class,
                "note": f"{r['wo_id']} was rejected by {r['actor']} on {r['ts']} ({r['reason']}); the same condition is re-raised only if it "
                        f"escalates or after {hours:.0f} h"}
    return None


def _create(db, a, rec, key, actor) -> list[dict]:
    w = workorders.create(db, asset_id=a.asset_id, job_type=rec.job_type, priority_class=rec.priority_class,
                          title=f"{rec.job_type.replace('_', ' ').capitalize()} {a.tag} ({rec.explanation['state']})", origin="system", actor=actor, role="system",
                          idempotency_key=key, due_by=iso(rec.due_by_ms), initial_state="PENDING_APPROVAL",
                          priority_score=rec.priority_score, explanation=rec.explanation, assessment_id=rec.assessment_id)
    return [{"asset_id": a.asset_id, "action": "created", "wo_id": w["wo_id"], "priority_class": rec.priority_class}]
