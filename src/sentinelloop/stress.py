"""Deterministic fault injectors for stress tests. Each returns (corrupted_copy, mask)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .data import OS_COLS


def _row_mask(df: pd.DataFrame, units, from_cycle: int) -> pd.Series:
    m = df["cycle"] >= from_cycle
    if units is not None:
        m &= df["unit"].isin(list(units))
    return m


def inject_missing(df: pd.DataFrame, frac: float, columns: list[str], seed: int = 0, units=None, from_cycle: int = 1):
    rng = np.random.default_rng(seed)
    out = df.copy()
    rows = _row_mask(df, units, from_cycle)
    mask = pd.DataFrame(False, index=df.index, columns=columns)
    rand = rng.random((int(rows.sum()), len(columns))) < frac
    mask.loc[rows, columns] = rand
    vals = out[columns].to_numpy(dtype=float)
    vals[mask.to_numpy()] = np.nan
    out[columns] = vals
    return out, mask


def inject_noise(df: pd.DataFrame, sigma_mult: float, columns: list[str], units=None, from_cycle: int = 1, seed: int = 0):
    rng = np.random.default_rng(seed)
    out = df.copy()
    mask = _row_mask(df, units, from_cycle)
    for c in columns:
        sd = float(df[c].std()) or 1.0
        noise = rng.normal(0.0, sigma_mult * sd, int(mask.sum()))
        out.loc[mask, c] = out.loc[mask, c].to_numpy(dtype=float) + noise
    return out, mask


def inject_bias(df: pd.DataFrame, sensor: str, k_std: float, from_cycle: int, units=None):
    out = df.copy()
    mask = _row_mask(df, units, from_cycle)
    sd = float(df[sensor].std()) or 1.0
    out.loc[mask, sensor] = out.loc[mask, sensor].to_numpy(dtype=float) + k_std * sd
    return out, mask


def inject_regime_shift(df: pd.DataFrame, settings: tuple[float, float, float], units=None, from_cycle: int = 1):
    out = df.copy()
    mask = _row_mask(df, units, from_cycle)
    for c, v in zip(OS_COLS, settings):
        out.loc[mask, c] = v
    return out, mask
