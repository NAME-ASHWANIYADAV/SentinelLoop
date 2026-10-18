"""Stream mode: process one row at a time with the same cleaning and feature definitions as batch.

CleanStream keeps per-unit state for forward-fill and EMA; FeatureStream keeps a trailing window per
unit per column and reproduces the batch rolling mean/std/slope exactly (tested).
"""
from __future__ import annotations

from collections import defaultdict, deque

import numpy as np
import pandas as pd

from .clean import CleanState
from .data import OS_COLS, SENSORS


class CleanStream:
    def __init__(self, state: CleanState, ema_alpha: float = 0.0):
        self.state = state
        self.alpha = ema_alpha or 0.0
        self.last_valid: dict[int, dict[str, float]] = defaultdict(dict)
        self.ema: dict[int, dict[str, float]] = defaultdict(dict)

    def update(self, row: pd.Series) -> pd.Series:
        unit = int(row["unit"])
        out = row.copy()
        n_imputed = 0
        for c in OS_COLS + SENSORS:
            v = out.get(c, np.nan)
            if v is None or (isinstance(v, float) and np.isnan(v)):
                if c in self.last_valid[unit]:
                    out[c] = self.last_valid[unit][c]
                    n_imputed += 1
            else:
                self.last_valid[unit][c] = float(v)
        if self.alpha:
            for c in SENSORS:
                v = out.get(c, np.nan)
                if v is None or (isinstance(v, float) and np.isnan(v)):
                    continue
                prev = self.ema[unit].get(c)
                out[c] = float(v) if prev is None else (1 - self.alpha) * prev + self.alpha * float(v)
                self.ema[unit][c] = float(out[c])
        out["n_imputed"] = n_imputed
        one = self.state.transform(pd.DataFrame([out]))
        return one.iloc[0]


class FeatureStream:
    def __init__(self, columns: list[str], window: int):
        self.columns = list(columns)
        self.window = window
        self.buf: dict[int, dict[str, deque]] = defaultdict(lambda: {c: deque(maxlen=window) for c in self.columns})

    def update(self, row: pd.Series) -> dict:
        unit = int(row["unit"])
        out = {k: row[k] for k in row.index}
        for c in self.columns:
            d = self.buf[unit][c]
            d.append(float(row[c]))
            y = np.asarray(d, dtype=float)
            n = len(y)
            out[f"{c}_rm"] = float(y.mean())
            out[f"{c}_rs"] = float(y.std(ddof=1)) if n > 1 else 0.0
            if n > 1:
                t = np.arange(n, dtype=float)
                out[f"{c}_slope"] = float(((t - t.mean()) * (y - y.mean())).sum() / ((t - t.mean()) ** 2).sum())
            else:
                out[f"{c}_slope"] = 0.0
        return out
