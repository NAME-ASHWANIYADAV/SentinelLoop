"""Evaluation protocol helpers.

Official protocol: predict at the LAST observed cycle of each test unit and compare with RUL_FD00x.txt.
Validation on training engines uses engine-level folds; because training engines run to failure,
their last cycle always has RUL = 0, so "last cycle of a held-out training engine" is a leakage-prone
protocol. The honest proxy is a random truncation point per engine.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def last_cycle_rows(df: pd.DataFrame) -> pd.DataFrame:
    idx = df.groupby("unit")["cycle"].idxmax()
    return df.loc[idx].sort_values("unit").reset_index(drop=True)


def engine_folds(df: pd.DataFrame, n_folds: int, seed: int = 42):
    """Yield (train_positions, val_positions) with every unit in exactly one validation fold."""
    units = np.sort(df["unit"].unique())
    rng = np.random.default_rng(seed)
    rng.shuffle(units)
    unit_arr = df["unit"].to_numpy()
    for fold_units in np.array_split(units, n_folds):
        val_mask = np.isin(unit_arr, fold_units)
        yield np.where(~val_mask)[0], np.where(val_mask)[0]


def random_truncate(df: pd.DataFrame, n_per_engine: int, seed: int = 42, min_cycles: int = 5) -> pd.DataFrame:
    """For each unit draw n_per_engine prefix lengths uniformly in [min_cycles, length]."""
    rng = np.random.default_rng(seed)
    parts = []
    for unit, g in df.sort_values(["unit", "cycle"]).groupby("unit", sort=True):
        length = len(g)
        lo = min(min_cycles, length)
        for k in range(n_per_engine):
            n = int(rng.integers(lo, length + 1))
            part = g.head(n).copy()
            part["trunc_id"] = k
            parts.append(part)
    return pd.concat(parts, ignore_index=True)


def random_rows_per_engine(df: pd.DataFrame, n_per_engine: int, seed: int = 42, min_cycle: int = 5) -> pd.DataFrame:
    """Equivalent to random truncation when features are causal: sample evaluation cycles per unit."""
    rng = np.random.default_rng(seed)
    parts = []
    for unit, g in df.groupby("unit", sort=True):
        eligible = g[g["cycle"] >= min(min_cycle, g["cycle"].max())]
        take = rng.choice(eligible.index.to_numpy(), size=min(n_per_engine, len(eligible)), replace=False)
        parts.append(df.loc[take])
    return pd.concat(parts).sort_values(["unit", "cycle"])


def decision_outcomes(dec: pd.DataFrame, t_critical: float, t_high: float, t_medium: float) -> dict:
    """Agent decisions against the true RUL of the official test engines: severity x true-RUL band counts and the
    rates a maintenance manager asks about (orders on healthy engines, serious engines missed, optimistic lower bounds)."""
    tc, th, tm = int(t_critical), int(t_high), int(t_medium)
    bands = [(f"<={tc}", lambda r: r <= t_critical), (f"{tc + 1}-{th}", lambda r: (r > t_critical) & (r <= t_high)),
             (f"{th + 1}-{tm}", lambda r: (r > t_high) & (r <= t_medium)), (f">{tm}", lambda r: r > t_medium)]
    truth = dec["rul_true_capped"].to_numpy(dtype=float)
    sev = dec["severity"].astype(str).to_numpy()
    esc = dec["escalate"].astype(bool).to_numpy() if "escalate" in dec.columns else np.zeros(len(dec), dtype=bool)
    counts = {s: {name: int(((sev == s) & fn(truth)).sum()) for name, fn in bands} for s in ["CRITICAL", "HIGH", "MEDIUM", "WATCH", "NONE"]}
    n = max(1, len(dec))
    serious = sev == "HIGH"
    serious |= sev == "CRITICAL"
    confident_order = serious & ~esc
    out = {"n": int(len(dec)), "bands": [b for b, _ in bands], "counts": counts,
           "lower_bound_above_truth_rate": float((dec["rul_lower"].to_numpy(dtype=float) > truth).mean()) if "rul_lower" in dec.columns else None,
           "serious_truth_missed_rate": float(((truth <= t_high) & ~serious).sum() / max(1, (truth <= t_high).sum())),
           "confident_order_on_healthy_rate": float((confident_order & (truth > t_medium)).sum() / n),
           "confident_order_on_healthy_count": int((confident_order & (truth > t_medium)).sum())}
    if "anomaly_flag" in dec.columns:
        af = dec["anomaly_flag"].astype(bool).to_numpy()
        ab = {f"<={th}": truth <= t_high, f"{th + 1}-{tm}": (truth > t_high) & (truth <= t_medium), f">{tm}": truth > t_medium}
        out["anomaly_flag_rate_by_band"] = {k: (float(af[mask].mean()) if mask.any() else None) for k, mask in ab.items()}
    return out
