"""Target construction. Training trajectories run to failure, so RUL = last_cycle - cycle.

The cap (default 125) is the piecewise-linear convention used across the C-MAPSS literature:
early-life RUL is clipped because degradation is not observable yet. Every metric states whether
it is computed against the capped or the raw truth.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def add_train_rul(df: pd.DataFrame, cap: int) -> pd.DataFrame:
    out = df.copy()
    max_cycle = out.groupby("unit")["cycle"].transform("max")
    out["rul_raw"] = (max_cycle - out["cycle"]).astype(int)
    out["rul"] = np.minimum(out["rul_raw"], cap).astype(int)
    return out


def test_truth(rul: np.ndarray, cap: int) -> tuple[np.ndarray, np.ndarray]:
    rul = np.asarray(rul).astype(int)
    return np.minimum(rul, cap), rul
