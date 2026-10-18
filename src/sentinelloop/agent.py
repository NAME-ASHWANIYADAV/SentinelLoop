"""The Triage Agent: deterministic, rule-based, no LLM (case-study ground rule).

Severity is decided from the LOWER bound of the RUL prediction interval, so uncertainty is part of the
decision. Escalation to a human happens when the evidence is not trustworthy: interval too wide,
input quality bad, drift active while a serious order is due, or conflicting signals. Every decision
carries its inputs, thresholds and the rule ids that fired, so it can be re-derived from the audit log.
"""
from __future__ import annotations

import dataclasses
import time
from dataclasses import dataclass, field

SEVERITY_ORDER = {"NONE": 0, "WATCH": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
ACTIONS = {"CRITICAL": "STOP_AND_REPAIR", "HIGH": "SCHEDULE_MAINTENANCE", "MEDIUM": "PLAN_MAINTENANCE", "WATCH": "MONITOR", "NONE": "NONE"}
ORDER_SEVERITIES = ("HIGH", "CRITICAL")


@dataclass(frozen=True)
class Thresholds:
    t_critical: float = 10.0
    t_high: float = 25.0
    t_medium: float = 50.0
    max_width: float = 60.0
    quality_max_imputed_frac: float = 0.10   # same as configs/default.yaml (D15)
    conflict_factor: float = 2.0

    @classmethod
    def from_config(cls, cfg: dict, auto_max_width: float | None = None) -> "Thresholds":
        """`max_width: auto` in the config takes the model's calibrated width (`auto_max_width`)."""
        a = cfg["agent"]
        mw = a["max_width"]
        if isinstance(mw, str) and mw.lower() == "auto":
            if auto_max_width is None:
                raise ValueError("agent.max_width is 'auto' but no calibrated width was supplied")
            mw = float(auto_max_width)
        return cls(t_critical=float(a["t_critical"]), t_high=float(a["t_high"]), t_medium=float(a["t_medium"]),
                   max_width=float(mw), quality_max_imputed_frac=float(a["quality_max_imputed_frac"]),
                   conflict_factor=float(a.get("conflict_factor", 2.0)))


@dataclass
class Observation:
    unit: int
    cycle: int
    rul_point: float
    rul_lower: float
    rul_upper: float
    anomaly_flag: bool
    anomaly_score: float
    drift_flag: bool
    imputed_frac: float
    missing_sensors: int
    model_version: str
    subset: str = ""
    quality_flag: bool = False   # window-level input-quality monitor (missing, imputed or out-of-range values)
    top_sensors: list[str] = field(default_factory=list)   # features with the largest healthy-baseline deviation (explainability)


@dataclass
class Decision:
    unit: int
    cycle: int
    severity: str
    action: str
    escalate_to_human: bool
    escalation_reasons: list[str]
    rules_fired: list[str]
    inputs: dict
    thresholds: dict
    model_version: str
    interval_width: float
    subset: str = ""

    def to_record(self) -> dict:
        return dataclasses.asdict(self)


def triage(obs: Observation, thr: Thresholds) -> Decision:
    rules: list[str] = []
    reasons: list[str] = []
    width = float(obs.rul_upper - obs.rul_lower)

    if obs.rul_lower <= thr.t_critical:
        severity = "CRITICAL"; rules.append("R_CRITICAL")
    elif obs.rul_lower <= thr.t_high:
        severity = "HIGH"; rules.append("R_HIGH")
    elif obs.rul_lower <= thr.t_medium:
        severity = "MEDIUM"; rules.append("R_MEDIUM")
    elif obs.anomaly_flag:
        severity = "WATCH"; rules.append("R_ANOMALY_WATCH")
    else:
        severity = "NONE"; rules.append("R_NONE")

    if obs.quality_flag or obs.imputed_frac > thr.quality_max_imputed_frac or obs.missing_sensors > 0:
        reasons.append("data_quality"); rules.append("R_ESC_QUALITY")
    if width > thr.max_width and severity in ("MEDIUM", "HIGH", "CRITICAL"):
        reasons.append("insufficient_evidence"); rules.append("R_ESC_WIDTH")
    if obs.drift_flag and severity in ("HIGH", "CRITICAL"):
        reasons.append("drift_active"); rules.append("R_ESC_DRIFT")
    if obs.anomaly_flag and obs.rul_lower > thr.conflict_factor * thr.t_medium:
        reasons.append("conflicting_evidence"); rules.append("R_ESC_CONFLICT")

    escalate = bool(reasons)
    action = "INSPECT" if escalate else ACTIONS[severity]
    inputs = {k: v for k, v in dataclasses.asdict(obs).items() if k not in ("model_version", "subset")}
    return Decision(unit=obs.unit, cycle=obs.cycle, severity=severity, action=action, escalate_to_human=escalate,
                    escalation_reasons=reasons, rules_fired=rules, inputs=inputs, thresholds=dataclasses.asdict(thr),
                    model_version=obs.model_version, interval_width=width, subset=obs.subset)


class WorkOrderBook:
    """Keeps at most one open order per unit; upgrades severity; never duplicates."""

    def __init__(self):
        self.orders: dict[int, dict] = {}
        self.history: list[dict] = []
        self._next_id = 1

    def apply(self, d: Decision) -> dict:
        wants_order = d.escalate_to_human or d.severity in ORDER_SEVERITIES
        if not wants_order:
            return {"event": "none", "order": None}
        order_type = "INSPECTION" if d.escalate_to_human else "MAINTENANCE"
        inp = d.inputs or {}
        lower = float(inp.get("rul_lower", float("nan")))
        due = int(d.cycle + max(0.0, lower)) if lower == lower else None
        content = {"action": d.action, "rul_point": inp.get("rul_point"), "rul_lower": inp.get("rul_lower"), "rul_upper": inp.get("rul_upper"),
                   "top_sensors": list(inp.get("top_sensors", []) or []), "anomaly_score": inp.get("anomaly_score"), "reasons": list(d.escalation_reasons),
                   "rules_fired": list(d.rules_fired), "model_version": d.model_version, "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}
        existing = self.orders.get(d.unit)
        if existing is None:
            order = {"id": self._next_id, "unit": d.unit, "type": order_type, "severity": d.severity, "status": "OPEN",
                     "created_cycle": d.cycle, "updated_cycle": d.cycle, "due_by_cycle": due, "n_decisions": 1, **content}
            self._next_id += 1
            self.orders[d.unit] = order
            self.history.append({"event": "created", **order})
            return {"event": "created", "order": dict(order)}
        existing["n_decisions"] += 1
        existing["updated_cycle"] = d.cycle
        upgraded = SEVERITY_ORDER[d.severity] > SEVERITY_ORDER[existing["severity"]]
        if upgraded or d.severity == existing["severity"]:
            # same or higher severity: the order carries the latest estimate; the due-by cycle only ever moves earlier
            existing.update(content)
            if due is not None:
                existing["due_by_cycle"] = due if existing.get("due_by_cycle") is None else min(existing["due_by_cycle"], due)
        if upgraded:
            existing["severity"] = d.severity
            existing["type"] = order_type
            self.history.append({"event": "upgraded", **existing})
            return {"event": "upgraded", "order": dict(existing)}
        return {"event": "unchanged", "order": dict(existing)}

    def close(self, unit: int, cycle: int | None = None) -> dict | None:
        order = self.orders.pop(unit, None)
        if order is not None:
            order["status"] = "CLOSED"
            order["closed_cycle"] = cycle
            self.history.append({"event": "closed", **order})
        return order

    def open_orders(self) -> list[dict]:
        return [dict(o) for o in self.orders.values()]
