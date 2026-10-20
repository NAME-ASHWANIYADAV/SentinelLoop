"""Pure formatting helpers for the dashboard: numbers, identifiers and plain-language explanations of rule-table output.

They translate what `agent.triage` already recorded (severity, rule ids, escalation reasons, thresholds) into words.
They never re-decide anything: an explanation is built only from the rules that actually fired.
"""
from __future__ import annotations

import math

import pandas as pd

from .theme import SEVERITY, SEVERITY_RANK

SUBSETS = {
    "FD001": "100 test engines, one operating condition, one fault mode (HPC degradation)",
    "FD002": "259 test engines, six operating conditions, one fault mode (HPC degradation)",
    "FD003": "100 test engines, one operating condition, two fault modes (HPC and fan degradation)",
    "FD004": "248 test engines, six operating conditions, two fault modes (HPC and fan degradation)",
}

ACTIONS = {
    "STOP_AND_REPAIR": "Stop and repair",
    "SCHEDULE_MAINTENANCE": "Schedule maintenance",
    "PLAN_MAINTENANCE": "Plan maintenance",
    "MONITOR": "Keep monitoring",
    "INSPECT": "Human inspection",
    "NONE": "No action",
}

REASONS = {
    "data_quality": "Input data unreliable",
    "insufficient_evidence": "Prediction interval too wide",
    "drift_active": "Fleet data drift active",
    "conflicting_evidence": "Anomaly conflicts with the life estimate",
}


def is_missing(v) -> bool:
    return v is None or (isinstance(v, float) and math.isnan(v)) or (isinstance(v, str) and v.strip() in ("", "nan", "None"))


def fmt_num(v, digits: int = 1, unit: str = "") -> str:
    """A number with fixed precision and an optional unit; an en dash when the value is missing."""
    if is_missing(v):
        return "–"
    try:
        s = f"{float(v):,.{digits}f}"
    except (TypeError, ValueError):
        return str(v)
    return f"{s} {unit}".strip()


def fmt_pct(v, digits: int = 0) -> str:
    if is_missing(v):
        return "–"
    return f"{float(v) * 100:.{digits}f}%"


def short_id(v, n: int = 8) -> str:
    """A long run id or hash shortened for display (the full value goes in a details section)."""
    s = "" if is_missing(v) else str(v)
    return s if len(s) <= n else s[:n]


def split_list(v) -> list[str]:
    """Rule ids, reasons and sensors are stored as lists in JSON and as '|'-joined strings in CSV."""
    if isinstance(v, (list, tuple)):
        return [str(x) for x in v if not is_missing(x)]
    if is_missing(v):
        return []
    return [x for x in str(v).replace(",", "|").split("|") if x.strip()]


def severity_label(sev) -> str:
    return SEVERITY.get(str(sev), {"label": str(sev)})["label"]


def action_label(action) -> str:
    return ACTIONS.get(str(action), str(action).replace("_", " ").capitalize())


def reason_label(reason) -> str:
    return REASONS.get(str(reason), str(reason).replace("_", " "))


def rule_sentence(rule: str, thr: dict) -> str:
    """One plain sentence per rule id of `agent.triage`, with the thresholds that were in force."""
    t = {k: thr.get(k) for k in ("t_critical", "t_high", "t_medium", "max_width")}
    sentences = {
        "R_CRITICAL": f"Lower bound of remaining life is at or below {fmt_num(t['t_critical'], 0)} cycles (critical threshold).",
        "R_HIGH": f"Lower bound of remaining life is at or below {fmt_num(t['t_high'], 0)} cycles (high threshold).",
        "R_MEDIUM": f"Lower bound of remaining life is at or below {fmt_num(t['t_medium'], 0)} cycles (planning threshold).",
        "R_ANOMALY_WATCH": "Sensor behaviour departs from the healthy baseline while the life estimate is still comfortable.",
        "R_NONE": "No severity rule fired: the lower bound is above every threshold and no anomaly is sustained.",
        "R_ESC_QUALITY": "Escalated: the input window has missing, imputed or out-of-range values.",
        "R_ESC_WIDTH": f"Escalated: the prediction interval is wider than the calibrated limit of {fmt_num(t['max_width'], 0)} cycles.",
        "R_ESC_DRIFT": "Escalated: a fleet-level drift alarm is active while serious work is due.",
        "R_ESC_CONFLICT": "Escalated: an anomaly is flagged although the life estimate is long, so the signals disagree.",
    }
    return sentences.get(rule, rule)


def explain(rules, thr: dict) -> list[tuple[str, str]]:
    """[(rule id, sentence)] for the rules that fired, severity rule first."""
    rs = split_list(rules)
    rs.sort(key=lambda r: (r.startswith("R_ESC"), r))
    return [(r, rule_sentence(r, thr)) for r in rs]


def priority_table(fleet: pd.DataFrame) -> pd.DataFrame:
    """Engines that need attention (any severity above healthy, or escalated), most urgent first, in display form."""
    if fleet is None or fleet.empty:
        return pd.DataFrame(columns=["Engine", "Priority", "Recommended action", "Life lower bound", "Life estimate",
                                     "Interval width", "Human review", "Why"])
    f = fleet.copy()
    esc = f["escalate"].astype(str).str.lower().isin(["true", "1"]) if "escalate" in f.columns else pd.Series(False, index=f.index)
    keep = f["severity"].isin(["CRITICAL", "HIGH", "MEDIUM", "WATCH"]) | esc
    f, esc = f[keep], esc[keep]
    width = (f["rul_upper"] - f["rul_lower"]) if {"rul_upper", "rul_lower"} <= set(f.columns) else pd.Series(float("nan"), index=f.index)
    why = []
    for _, r in f.iterrows():
        parts = [reason_label(x) for x in split_list(r.get("reasons"))]
        sev = str(r["severity"])
        if not parts:
            parts = ["Sustained anomaly" if sev == "WATCH" else f"Lower bound in the {severity_label(sev).lower()} band"]
        why.append("; ".join(parts))
    out = pd.DataFrame({
        "Engine": f["unit"].astype(int).values,
        "Priority": [f"{SEVERITY.get(s, {}).get('glyph', '')} {severity_label(s)}".strip() for s in f["severity"]],
        "Recommended action": [action_label(a) for a in f.get("action", pd.Series("", index=f.index))],
        "Life lower bound": f["rul_lower"].round(1).values,
        "Life estimate": f["rul_point"].round(1).values,
        "Interval width": width.round(1).values,
        "Human review": ["Yes" if e else "No" for e in esc],
        "Why": why,
    })
    out["_rank"] = [SEVERITY_RANK.get(s, 0) for s in f["severity"]]
    out["_esc"] = esc.values
    out = out.sort_values(["_rank", "_esc", "Life lower bound"], ascending=[False, False, True]).drop(columns=["_rank", "_esc"])
    return out.reset_index(drop=True)


def verdict(conclusion: str) -> str:
    """Pre-registered verdict as written in an experiment's conclusion: 'Not supported', 'Supported' or 'No verdict stated'."""
    c = (conclusion or "").upper()
    if "NOT SUPPORTED" in c:
        return "Not supported"
    if "SUPPORTED" in c:
        return "Supported"
    return "No verdict stated"
