"""Cleaning: imputation with quality flags, causal EMA denoising, train-only drop list and
operating-regime normalisation. Nothing in this module is ever fit on test data.

CleanState is pickled as a project artefact (artifacts/<subset>/clean_state.pkl). Pickle is used only
for artefacts produced by this package on the same machine; never load pickles from untrusted sources.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans

from .data import OS_COLS, SENSORS


def impute(df: pd.DataFrame) -> pd.DataFrame:
    """Per-unit forward fill then backward fill of sensor and operating-setting columns.

    Adds `n_imputed`: number of originally-missing values in the row that were filled. Values that
    cannot be filled (a sensor missing for an entire unit) stay NaN and are not counted.
    """
    out = df.sort_values(["unit", "cycle"]).reset_index(drop=True).copy()
    cols = [c for c in OS_COLS + SENSORS if c in out.columns]
    was_na = out[cols].isna()
    out[cols] = out.groupby("unit")[cols].ffill()
    out[cols] = out.groupby("unit")[cols].bfill()
    filled = was_na & out[cols].notna()
    out["n_imputed"] = filled.sum(axis=1).astype(int)
    return out


def ema_denoise(df: pd.DataFrame, alpha: float, columns: list[str]) -> pd.DataFrame:
    """Causal exponential moving average per unit: y_t = (1-alpha) y_{t-1} + alpha x_t, y_0 = x_0."""
    out = df.sort_values(["unit", "cycle"]).reset_index(drop=True).copy()
    if not alpha:
        return out
    for c in columns:
        out[c] = out.groupby("unit")[c].transform(lambda s: s.ewm(alpha=alpha, adjust=False).mean())
    return out


@dataclass
class CleanState:
    n_regimes: int
    os_mean: np.ndarray
    os_std: np.ndarray
    kmeans: KMeans | None
    dropped_sensors: list[str]
    kept_sensors: list[str]
    regime_mean: dict[int, np.ndarray] = field(default_factory=dict)
    regime_std: dict[int, np.ndarray] = field(default_factory=dict)
    seed: int = 42

    @classmethod
    def fit(cls, train: pd.DataFrame, n_regimes: int = 1, std_threshold: float = 1e-3, seed: int = 42) -> "CleanState":
        train = train.sort_values(["unit", "cycle"]).reset_index(drop=True)
        os_vals = train[OS_COLS].to_numpy(dtype=float)
        os_mean = os_vals.mean(axis=0)
        os_std = np.where(os_vals.std(axis=0) < 1e-12, 1.0, os_vals.std(axis=0))
        kmeans = None
        if n_regimes > 1:
            kmeans = KMeans(n_clusters=n_regimes, n_init=10, random_state=seed)
            kmeans.fit((os_vals - os_mean) / os_std)
        state = cls(n_regimes=n_regimes, os_mean=os_mean, os_std=os_std, kmeans=kmeans,
                    dropped_sensors=[], kept_sensors=list(SENSORS), seed=seed)
        regime = state.assign_regime(train)
        sens = train[SENSORS].to_numpy(dtype=float)
        max_std = np.zeros(len(SENSORS))
        means: dict[int, np.ndarray] = {}
        stds: dict[int, np.ndarray] = {}
        for r in range(n_regimes):
            m = regime == r
            if not m.any():
                continue
            mu = np.nanmean(sens[m], axis=0)
            sd = np.nanstd(sens[m], axis=0)
            means[r], stds[r] = mu, sd
            max_std = np.maximum(max_std, np.nan_to_num(sd))
        dropped = [s for s, v in zip(SENSORS, max_std) if v < std_threshold]
        kept = [s for s in SENSORS if s not in dropped]
        keep_idx = [SENSORS.index(s) for s in kept]
        state.dropped_sensors = dropped
        state.kept_sensors = kept
        state.regime_mean = {r: means[r][keep_idx] for r in means}
        state.regime_std = {r: np.where(stds[r][keep_idx] < 1e-8, 1.0, stds[r][keep_idx]) for r in stds}
        return state

    def assign_regime(self, df: pd.DataFrame) -> np.ndarray:
        if self.kmeans is None:
            return np.zeros(len(df), dtype=int)
        os_vals = df[OS_COLS].to_numpy(dtype=float)
        return self.kmeans.predict((os_vals - self.os_mean) / self.os_std).astype(int)

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.sort_values(["unit", "cycle"]).reset_index(drop=True).copy()
        out["regime"] = self.assign_regime(out)
        vals = out[self.kept_sensors].to_numpy(dtype=float)
        for r, mu in self.regime_mean.items():
            m = (out["regime"] == r).to_numpy()
            vals[m] = (vals[m] - mu) / self.regime_std[r]
        out[self.kept_sensors] = vals
        out = out.drop(columns=[c for c in self.dropped_sensors if c in out.columns])
        front = ["unit", "cycle"] + OS_COLS + ["regime"]
        rest = [c for c in out.columns if c not in front]
        return out[front + rest]
