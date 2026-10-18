"""Health states of an asset, how one assessment is classified, and how the asset's state evolves.

Operational definitions (an assessment is one evaluation of one asset at one instant):

NORMAL_MONITORING       data passed every quality check, an approved model is in scope, P(failure before the
                        decision horizon) < p_inspect and no sustained anomaly. Nothing is recommended.
INSPECTION_RECOMMENDED  data and model as above, and p_inspect <= P < p_urgent, or a sustained anomaly while
                        the predicted risk is low (conflicting evidence). A low-cost inspection is recommended.
URGENT_REVIEW           data and model as above and P >= p_urgent: the asset may fail before the earliest
                        feasible intervention. A named person must review it promptly.
DATA_QUALITY_FAILURE    a required signal is missing or stale, imputed beyond the limit, stuck, or out of its
                        plausible range beyond the limit. No prediction from this window is used.
MODEL_OUT_OF_SCOPE      no approved model covers the asset, or the operating conditions/history are outside the
                        model's validated envelope. No prediction is used; this is NOT a statement that the
                        asset is healthy.
MODEL_UNAVAILABLE       the approved model could not be loaded (missing or integrity failure) or failed while
                        scoring. No prediction is used.
HUMAN_APPROVAL_REQUIRED a flag, shown next to the state, set while a system recommendation for the asset waits
                        for an authorised person to approve, defer or reject it. Nothing is executed before that.

Evolution rules (tested exhaustively in tests/test_app_states.py):
- URGENT_REVIEW latches: later assessments, however benign, do not clear it. Only completed maintenance or a
  dismissal with a written reason by an authorised role clears it. Bad data or a model problem never hides it.
- INSPECTION_RECOMMENDED latches the same way and upgrades to URGENT_REVIEW when the risk grows.
- DATA_QUALITY_FAILURE clears only after `dq_clear_after` consecutive assessments without a data failure.
A warning, an escalation or a cleared state is information for people; none of them makes a machine safe.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum


class HealthState(str, Enum):
    NORMAL_MONITORING = "NORMAL_MONITORING"
    INSPECTION_RECOMMENDED = "INSPECTION_RECOMMENDED"
    URGENT_REVIEW = "URGENT_REVIEW"
    DATA_QUALITY_FAILURE = "DATA_QUALITY_FAILURE"
    MODEL_OUT_OF_SCOPE = "MODEL_OUT_OF_SCOPE"
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"


APPROVAL_LABEL = "HUMAN_APPROVAL_REQUIRED"
NOT_ASSESSED_LABEL = "NOT_ASSESSED"
CLEAR_EVENTS = {
    "dismissed": {"reliability_engineer", "planner", "admin"},
    "maintenance_completed": {"technician", "planner", "reliability_engineer", "admin", "integration"},
}


class TransitionError(ValueError):
    pass


from .errors import PermissionDenied  # noqa: E402


class StateRolePermissionError(TransitionError, PermissionDenied):
    pass


@dataclass(frozen=True)
class Thresholds:
    p_inspect: float = 0.10
    p_urgent: float = 0.30
    dq_clear_after: int = 2

    def __post_init__(self):
        if not 0 < self.p_inspect < self.p_urgent < 1:
            raise ValueError("thresholds must satisfy 0 < p_inspect < p_urgent < 1")
        if self.dq_clear_after < 1:
            raise ValueError("dq_clear_after must be at least 1")


@dataclass(frozen=True)
class Classification:
    state: HealthState
    reasons: list = field(default_factory=list)


def classify(model_ok: bool, data_ok: bool, in_scope: bool, p_fail: float | None, sustained_anomaly: bool, thr: Thresholds,
             reasons: list | None = None, anomaly_only: bool = False, severe_anomaly: bool = False) -> Classification:
    """One assessment -> one state. Precedence: model failure, data failure, scope, then risk.

    `anomaly_only`: the approved model detects abnormal behaviour but estimates no failure time (for example the wind
    normal-behaviour model). Then no probability exists and none is invented: a sustained deviation is an inspection,
    a severe sustained deviation an urgent review, anything else normal monitoring."""
    reasons = list(reasons or [])
    if not model_ok:
        return Classification(HealthState.MODEL_UNAVAILABLE, reasons)
    if not data_ok:
        return Classification(HealthState.DATA_QUALITY_FAILURE, reasons)
    if not in_scope:
        return Classification(HealthState.MODEL_OUT_OF_SCOPE, reasons)
    if p_fail is None:
        if not anomaly_only:
            raise ValueError("an in-scope assessment with good data must carry a failure probability")
        if sustained_anomaly and severe_anomaly:
            return Classification(HealthState.URGENT_REVIEW, reasons + ["severe sustained deviation from normal behaviour (no failure-time estimate)"])
        if sustained_anomaly:
            return Classification(HealthState.INSPECTION_RECOMMENDED, reasons + ["sustained deviation from normal behaviour (no failure-time estimate)"])
        return Classification(HealthState.NORMAL_MONITORING, reasons)
    if p_fail >= thr.p_urgent:
        return Classification(HealthState.URGENT_REVIEW, reasons + [f"P(failure before horizon) {p_fail:.2f} >= urgent threshold {thr.p_urgent}"])
    if p_fail >= thr.p_inspect:
        return Classification(HealthState.INSPECTION_RECOMMENDED, reasons + [f"P(failure before horizon) {p_fail:.2f} >= inspection threshold {thr.p_inspect}"])
    if sustained_anomaly:
        return Classification(HealthState.INSPECTION_RECOMMENDED, reasons + ["sustained anomaly while predicted risk is low (conflicting evidence)"])
    return Classification(HealthState.NORMAL_MONITORING, reasons)


@dataclass(frozen=True)
class AssetState:
    effective: HealthState = HealthState.NORMAL_MONITORING
    latched_risk: str = "NONE"                 # NONE | INSPECTION | URGENT
    dq_failure_active: bool = False
    dq_ok_streak: int = 0
    last_health: HealthState | None = None
    approval_pending: bool = False
    notes: tuple = ()

    def labels(self) -> list[str]:
        # a state record can exist before any assessment (e.g. an order created by hand awaits approval); that is not health
        never = self.last_health is None and self.latched_risk == "NONE" and not self.dq_failure_active
        return [NOT_ASSESSED_LABEL if never else self.effective.value] + ([APPROVAL_LABEL] if self.approval_pending else [])


def _effective(latched: str, dq_active: bool, last: HealthState | None) -> tuple[HealthState, list[str]]:
    notes = []
    if latched == "URGENT":
        if last is not None and last != HealthState.URGENT_REVIEW:
            notes.append(f"latched: latest assessment is {last.value}; urgent review stays until maintenance or a reasoned dismissal")
        return HealthState.URGENT_REVIEW, notes
    if dq_active:
        if last != HealthState.DATA_QUALITY_FAILURE:
            notes.append("data quality recovering: waiting for consecutive good assessments")
        if latched == "INSPECTION":
            notes.append("inspection recommendation still pending")
        return HealthState.DATA_QUALITY_FAILURE, notes
    if last in (HealthState.MODEL_UNAVAILABLE, HealthState.MODEL_OUT_OF_SCOPE):
        if latched == "INSPECTION":
            notes.append("inspection recommendation still pending")
        return last, notes
    if latched == "INSPECTION":
        if last is not None and last != HealthState.INSPECTION_RECOMMENDED:
            notes.append(f"latched: latest assessment is {last.value}; inspection stays recommended until done or dismissed")
        return HealthState.INSPECTION_RECOMMENDED, notes
    return HealthState.NORMAL_MONITORING, notes


def advance(s: AssetState, cl: Classification, thr: Thresholds) -> AssetState:
    latched = s.latched_risk
    if cl.state == HealthState.URGENT_REVIEW:
        latched = "URGENT"
    elif cl.state == HealthState.INSPECTION_RECOMMENDED and latched == "NONE":
        latched = "INSPECTION"
    if cl.state == HealthState.DATA_QUALITY_FAILURE:
        dq_active, streak = True, 0
    else:
        streak = s.dq_ok_streak + 1
        dq_active = s.dq_failure_active and streak < thr.dq_clear_after
    eff, notes = _effective(latched, dq_active, cl.state)
    return replace(s, effective=eff, latched_risk=latched, dq_failure_active=dq_active, dq_ok_streak=min(streak, 10_000),
                   last_health=cl.state, notes=tuple(notes + list(cl.reasons)))


def clear_risk(s: AssetState, event: str, actor: str, role: str, reason: str) -> AssetState:
    if event not in CLEAR_EVENTS:
        raise TransitionError(f"unknown clearing event {event!r}; allowed: {sorted(CLEAR_EVENTS)}")
    if role not in CLEAR_EVENTS[event]:
        raise StateRolePermissionError(f"role {role!r} may not record {event!r}")
    if not reason or not reason.strip():
        raise TransitionError("a written reason is required to clear a latched risk")
    if s.latched_risk == "NONE":
        raise TransitionError("there is no latched risk to clear")
    last = s.last_health if s.last_health not in (HealthState.URGENT_REVIEW, HealthState.INSPECTION_RECOMMENDED) else None
    eff, notes = _effective("NONE", s.dq_failure_active, last)
    return replace(s, effective=eff, latched_risk="NONE", notes=tuple(notes + [f"{s.latched_risk.lower()} cleared by {actor} ({event}): {reason}"]))


def set_approval_pending(s: AssetState, pending: bool) -> AssetState:
    return replace(s, approval_pending=bool(pending))
