"""Maintenance policies evaluated by the replay harness. All policies see identical predictions."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Policy:
    name: str
    kind: str            # "point" | "margin" | "lower" | "cost" (cost = point kind with a cost-chosen threshold)
    threshold: float
    margin: float = 0.0

    def describe(self) -> str:
        if self.kind == "point" or self.kind == "cost":
            return f"{self.name}: order when point RUL <= {self.threshold:g}"
        if self.kind == "margin":
            return f"{self.name}: order when point RUL - {self.margin:g} <= {self.threshold:g}"
        return f"{self.name}: order when interval lower bound <= {self.threshold:g}"


def trigger_series(p: Policy, df: pd.DataFrame) -> np.ndarray:
    if p.kind in ("point", "cost"):
        return (df["point"].to_numpy() <= p.threshold)
    if p.kind == "margin":
        return (df["point"].to_numpy() - p.margin <= p.threshold)
    if p.kind == "lower":
        return (df["lower"].to_numpy() <= p.threshold)
    raise ValueError(f"unknown policy kind {p.kind!r}")


def first_order_cycle(p: Policy, df: pd.DataFrame) -> int | None:
    """First cycle (of a single engine's trajectory) at which the policy triggers, or None."""
    df = df.sort_values("cycle")
    trig = trigger_series(p, df)
    if not trig.any():
        return None
    return int(df["cycle"].to_numpy()[int(np.argmax(trig))])
