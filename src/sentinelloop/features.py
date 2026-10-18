"""Causal rolling-window features per unit: mean, std and least-squares slope over the last W cycles.

All windows look backwards only, so the same definitions are valid for batch training and stream replay.
The batch implementation below uses exactly the same numpy arithmetic as `stream.FeatureStream` (window
rows reduced with numpy's row-wise reductions), so batch and stream features are the same bits; a tree
model can otherwise flip a split on a 1e-12 difference and give different predictions for the same cycle.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

NON_FEATURE_COLUMNS = {"unit", "rul", "rul_raw", "n_imputed", "trunc_id", "os1", "os2", "os3"}


def window_stats_1d(y: np.ndarray) -> tuple[float, float, float]:
    """Mean, sample std and OLS slope of one trailing window (the reference arithmetic, shared with the stream)."""
    n = len(y)
    rm = float(y.mean())
    rs = float(y.std(ddof=1)) if n > 1 else 0.0
    if n > 1:
        t = np.arange(n, dtype=float)
        sl = float(((t - t.mean()) * (y - y.mean())).sum() / ((t - t.mean()) ** 2).sum())
    else:
        sl = 0.0
    return rm, rs, sl


def _window_stats(y: np.ndarray, window: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    L = len(y)
    rm, rs, sl = np.empty(L), np.empty(L), np.empty(L)
    head = min(window - 1, L)
    for i in range(head):                      # partial windows at the start of a unit: same code path as the stream
        rm[i], rs[i], sl[i] = window_stats_1d(np.ascontiguousarray(y[: i + 1]))
    if L >= window:
        W = sliding_window_view(y, window)     # row i covers y[i : i + window]; rows are contiguous views
        rm[window - 1:] = W.mean(axis=1)
        rs[window - 1:] = W.std(axis=1, ddof=1)
        t = np.arange(window, dtype=float)
        tc = t - t.mean()
        sl[window - 1:] = (tc * (W - W.mean(axis=1, keepdims=True))).sum(axis=1) / (tc ** 2).sum()
    return rm, rs, sl


def build_features(df: pd.DataFrame, columns: list[str], window: int) -> pd.DataFrame:
    out = df.sort_values(["unit", "cycle"]).reset_index(drop=True).copy()
    g = out.groupby("unit", sort=False)
    new_cols: dict[str, np.ndarray] = {f"{c}_{s}": np.empty(len(out)) for c in columns for s in ("rm", "rs", "slope")}
    for c in columns:
        y_all = out[c].to_numpy(dtype=float)
        for _, idx in g.indices.items():
            idx = np.asarray(idx)
            rm, rs, sl = _window_stats(np.ascontiguousarray(y_all[idx]), window)
            new_cols[f"{c}_rm"][idx], new_cols[f"{c}_rs"][idx], new_cols[f"{c}_slope"][idx] = rm, rs, sl
    out = pd.concat([out, pd.DataFrame(new_cols, index=out.index)], axis=1)
    return out


def feature_manifest(df: pd.DataFrame) -> list[str]:
    """Model input columns: raw kept sensors, rolling features, cycle and regime (never labels or ids)."""
    return [c for c in df.columns if c not in NON_FEATURE_COLUMNS]
