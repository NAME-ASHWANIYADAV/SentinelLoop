"""Cycle-by-cycle replay of maintenance policies over engine trajectories, with decision-level metrics.

Replay assumption (stated in the deck): the first order is acted on immediately, so the useful life
discarded equals the true RUL at the first order. An order is LATE when the true RUL at that cycle is
below `min_lead` (not enough time to act) or when no order was issued before the due cycle. An engine
whose observation ends before its due cycle without an order is PENDING (not evaluable), which happens
for official test engines because their trajectories are truncated before failure.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import policy as policy_mod


def _failure_cycle(g: pd.DataFrame) -> int:
    if "failure_cycle" in g.columns:
        return int(g["failure_cycle"].iloc[0])
    last = g.sort_values("cycle").iloc[-1]
    return int(last["cycle"] + last["rul_true_raw"])


def replay_policy(df: pd.DataFrame, p: policy_mod.Policy, min_lead: int = 5) -> pd.DataFrame:
    rows = []
    for unit, g in df.groupby("unit", sort=True):
        g = g.sort_values("cycle")
        failure = _failure_cycle(g)
        observed_until = int(g["cycle"].max())
        due = failure - min_lead
        c = policy_mod.first_order_cycle(p, g)
        if c is not None:
            true_rul = failure - c
            rows.append(dict(unit=unit, policy=p.name, ordered=True, first_order_cycle=c, true_rul_at_order=float(true_rul),
                             late=bool(true_rul < min_lead), pending=False, failure_cycle=failure, observed_until=observed_until))
        else:
            pending = observed_until < due
            rows.append(dict(unit=unit, policy=p.name, ordered=False, first_order_cycle=None, true_rul_at_order=np.nan,
                             late=bool(not pending), pending=bool(pending), failure_cycle=failure, observed_until=observed_until))
    return pd.DataFrame(rows)


def decision_metrics(out: pd.DataFrame, early_limit: float = 60.0) -> dict:
    n = len(out)
    pending = out["pending"].sum()
    evaluable = out[~out["pending"]]
    ordered = out[out["ordered"]]
    on_time = ordered[~ordered["late"]]
    m = {
        "n_engines": int(n),
        "n_pending": int(pending),
        "n_evaluable": int(len(evaluable)),
        "order_rate": float(ordered.shape[0] / n) if n else float("nan"),
        "late_rate": float(evaluable["late"].mean()) if len(evaluable) else float("nan"),
        "mean_discarded_life": float(on_time["true_rul_at_order"].mean()) if len(on_time) else float("nan"),
        "median_discarded_life": float(on_time["true_rul_at_order"].median()) if len(on_time) else float("nan"),
        "mean_lead_time": float(ordered["true_rul_at_order"].mean()) if len(ordered) else float("nan"),
        "early_rate": float((ordered["true_rul_at_order"] > early_limit).mean()) if len(ordered) else float("nan"),
        "n_late": int(evaluable["late"].sum()) if len(evaluable) else 0,
    }
    return m


def tune_threshold(df: pd.DataFrame, kind: str, target_late_rate: float, grid, min_lead: int = 5, margin: float = 0.0, name: str = "tune") -> float:
    """Smallest threshold on the grid whose late rate on these (tuning) engines meets the target.
    Smaller threshold = later orders = less discarded life, so this is the least conservative safe setting."""
    best = None
    for t in sorted(float(x) for x in grid):
        out = replay_policy(df, policy_mod.Policy(name, kind, t, margin=margin), min_lead=min_lead)
        if decision_metrics(out)["late_rate"] <= target_late_rate:
            best = t
            break
    if best is None:
        best = float(max(grid))
    return best


def tune_margin(df: pd.DataFrame, threshold: float, target_late_rate: float, grid, min_lead: int = 5) -> float:
    best = None
    for mrg in sorted(float(x) for x in grid):
        out = replay_policy(df, policy_mod.Policy("tune", "margin", threshold, margin=mrg), min_lead=min_lead)
        if decision_metrics(out)["late_rate"] <= target_late_rate:
            best = mrg
            break
    return float(max(grid)) if best is None else best


def churn(severities) -> int:
    s = list(severities)
    return int(sum(1 for a, b in zip(s[:-1], s[1:]) if a != b))


def expected_cost(metrics: dict, cost_ratio: float, cost_per_cycle: float = 1.0) -> float:
    """Assumed cost model for the sensitivity sweep: cost_ratio x (late rate) + discarded life per engine.
    This is an ASSUMPTION for comparing policies, never a real-world saving claim."""
    late = metrics["late_rate"] if metrics["late_rate"] == metrics["late_rate"] else 0.0
    discarded = metrics["mean_discarded_life"] if metrics["mean_discarded_life"] == metrics["mean_discarded_life"] else 0.0
    return float(cost_ratio * late + cost_per_cycle * discarded)
