"""Anomaly detection against a healthy-phase baseline.

Default method "zscore": for every feature, the mean and std over the HEALTHY phase of training engines
(first `healthy_frac` of each engine's life) define normal behaviour; the anomaly score of a row is the
root-mean-square of its top-k absolute standardised deviations. It is explainable (the top deviating
sensors are reported) and sensitive to shifts confined to a few sensors. "iforest" (IsolationForest on
the same healthy rows) is kept as an ablation option. Neither sees `cycle`, so they flag abnormal sensor
behaviour rather than age. A flag is "sustained" when it persists for k consecutive cycles of a unit.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest


@dataclass
class AnomalyDetector:
    method: str
    columns: list[str]
    threshold: float
    healthy_frac: float
    threshold_pct: float
    top_k: int = 3
    warmup: int = 20
    healthy_mean: np.ndarray | None = None
    healthy_std: np.ndarray | None = None
    iforest: IsolationForest | None = field(default=None, repr=False)

    @classmethod
    def fit(cls, train_f: pd.DataFrame, columns: list[str], healthy_frac: float = 0.4, threshold_pct: float = 99.0,
            seed: int = 42, method: str = "zscore", top_k: int = 3, warmup: int = 20) -> "AnomalyDetector":
        """`warmup` = rolling-window length: rows before it have unstable rolling features, so they are
        excluded from the healthy baseline and the detector reports score 0 (not armed) for them."""
        cols = [c for c in columns if c != "cycle"]
        max_cycle = train_f.groupby("unit")["cycle"].transform("max")
        healthy = (train_f["cycle"] <= healthy_frac * max_cycle) & (train_f["cycle"] >= warmup)
        if not healthy.any():
            healthy = train_f["cycle"] <= healthy_frac * max_cycle
        H = train_f.loc[healthy, cols].to_numpy(dtype=float)
        det = cls(method=method, columns=cols, threshold=0.0, healthy_frac=healthy_frac, threshold_pct=threshold_pct, top_k=top_k, warmup=warmup)
        if method == "zscore":
            det.healthy_mean = np.nanmean(H, axis=0)
            sd = np.nanstd(H, axis=0)
            det.healthy_std = np.where(sd < 1e-8, 1.0, sd)
        elif method == "iforest":
            det.iforest = IsolationForest(n_estimators=200, random_state=seed).fit(H)
        else:
            raise ValueError(f"unknown anomaly method {method!r}")
        det.threshold = float(np.percentile(det.score(train_f.loc[healthy]), threshold_pct))
        return det

    def _z(self, X: pd.DataFrame) -> np.ndarray:
        return (X[self.columns].to_numpy(dtype=float) - self.healthy_mean) / self.healthy_std

    def score(self, X: pd.DataFrame) -> np.ndarray:
        if self.method == "iforest":
            s = -self.iforest.score_samples(X[self.columns])
        else:
            z2 = np.nan_to_num(np.square(self._z(X)), nan=0.0)
            k = min(self.top_k, z2.shape[1])
            top = np.sort(z2, axis=1)[:, -k:]
            s = np.sqrt(top.mean(axis=1))
        if "cycle" in X.columns and self.warmup > 0:
            s = np.where(X["cycle"].to_numpy() < self.warmup, 0.0, s)  # not armed until the window is full
        return s

    def top_deviations(self, X: pd.DataFrame, n: int = 3) -> list[list[tuple[str, float]]]:
        """Per row: the n features with the largest |z| (explainability for the dashboard and audit)."""
        if self.method != "zscore":
            return [[] for _ in range(len(X))]
        z = np.nan_to_num(self._z(X), nan=0.0)
        out = []
        for row in z:
            idx = np.argsort(-np.abs(row))[:n]
            out.append([(self.columns[i], float(row[i])) for i in idx])
        return out


def sustained(flags: np.ndarray, k: int) -> np.ndarray:
    flags = np.asarray(flags, dtype=bool)
    out = np.zeros(len(flags), dtype=bool)
    run = 0
    for i, f in enumerate(flags):
        run = run + 1 if f else 0
        out[i] = run >= k
    return out


def sustained_per_unit(df: pd.DataFrame, col: str, k: int) -> np.ndarray:
    out = np.zeros(len(df), dtype=bool)
    for _, idx in df.groupby("unit", sort=False).indices.items():
        idx = np.asarray(idx)
        out[idx] = sustained(df[col].to_numpy()[idx], k)
    return out
