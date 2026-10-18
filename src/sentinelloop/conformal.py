"""Conformalized quantile regression (CQR) for RUL prediction intervals.

Protocol: a fraction of TRAINING ENGINES is held out as the calibration set (engine-level split).
Point and quantile models are fit on the remaining engines. Conformity scores are computed on
randomly sampled cycles of the calibration engines (mimicking the test protocol, where each engine is
observed up to an unknown truncation point). The interval [q_lo - qhat, q_hi + qhat] then has marginal
coverage >= 1 - alpha over engines under the exchangeability assumption between calibration
truncations and test truncations (Romano, Patterson & Candes, 2019). We report MEASURED coverage; the
assumption is stated, not claimed as a guarantee.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import evaluate, models


@dataclass
class CQRModel:
    point: models.ClippedRegressor
    q_lo: models.ClippedRegressor
    q_hi: models.ClippedRegressor
    alpha: float
    qhat: float
    columns: list[str]
    training_units: list[int]
    calibration_units: list[int]
    n_calibration_rows: int
    truncations_per_engine: int
    seed: int
    calibration_scores: list[float] = field(default_factory=list, repr=False)
    suggested_max_width: float = float("nan")
    serious_lower_max: float = 50.0
    asymmetric: bool = False
    qhat_lo: float = float("nan")
    qhat_hi: float = float("nan")

    def __post_init__(self):
        if np.isnan(self.qhat_lo):
            self.qhat_lo = self.qhat
        if np.isnan(self.qhat_hi):
            self.qhat_hi = self.qhat

    def predict(self, X) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        point = self.point.predict(X)
        lo = np.clip(self.q_lo.predict(X) - self.qhat_lo, 0.0, None)
        hi = self.q_hi.predict(X) + self.qhat_hi
        hi = np.maximum(hi, lo)
        return point, lo, hi

    def metadata(self) -> dict:
        return {
            "alpha": self.alpha,
            "qhat": float(self.qhat),
            "training_units": [int(u) for u in self.training_units],
            "calibration_units": [int(u) for u in self.calibration_units],
            "n_calibration_rows": int(self.n_calibration_rows),
            "truncations_per_engine": int(self.truncations_per_engine),
            "seed": int(self.seed),
            "columns": list(self.columns),
            "suggested_max_width": float(self.suggested_max_width),
            "serious_lower_max": float(self.serious_lower_max),
            "asymmetric": bool(self.asymmetric),
            "qhat_lo": float(self.qhat_lo),
            "qhat_hi": float(self.qhat_hi),
            "assumption": "exchangeability of calibration truncation points and test truncation points; coverage is marginal over engines",
        }


def split_engines(units: np.ndarray, calib_frac: float, seed: int) -> tuple[list[int], list[int]]:
    units = np.array(sorted(set(int(u) for u in units)))
    rng = np.random.default_rng(seed)
    rng.shuffle(units)
    n_cal = max(1, int(round(calib_frac * len(units))))
    return [int(u) for u in units[n_cal:]], [int(u) for u in units[:n_cal]]


def conformity_scores(y: np.ndarray, lo: np.ndarray, hi: np.ndarray) -> np.ndarray:
    return np.maximum(lo - y, y - hi)


def conformal_quantile(scores: np.ndarray, alpha: float) -> float:
    n = len(scores)
    level = min(1.0, np.ceil((n + 1) * (1 - alpha)) / n)
    return float(np.quantile(scores, level, method="higher"))


def fit_cqr(train_f: pd.DataFrame, columns: list[str], alpha: float, calib_frac: float, seed: int = 42,
            truncations_per_engine: int = 5, max_iter: int = 400, learning_rate: float = 0.05, max_leaf_nodes: int = 31,
            serious_lower_max: float = 50.0, width_percentile: float = 75.0, asymmetric: bool = False) -> CQRModel:
    """`suggested_max_width`: the `width_percentile` of interval widths over ALL calibration rows whose
    lower bound is at or below `serious_lower_max` (i.e. rows where the agent would act). The agent's
    'insufficient evidence' escalation uses it, so by construction at most ~25% of serious decisions
    escalate for width on data like the calibration set.
    `asymmetric=True`: separate corrections for the lower and upper bound, each at level 1 - alpha/2
    (one-sided conformal quantiles), which still gives marginal coverage >= 1 - alpha by a union bound and
    adapts to skewed errors (Romano et al. 2019, asymmetric variant; used by Robinson, IJPHM 2026)."""
    train_units, calib_units = split_engines(train_f["unit"].unique(), calib_frac, seed)
    fit_rows = train_f[train_f["unit"].isin(train_units)]
    cal_rows = train_f[train_f["unit"].isin(calib_units)]
    kw = dict(max_iter=max_iter, learning_rate=learning_rate, max_leaf_nodes=max_leaf_nodes, seed=seed)
    point = models.train_point_model(fit_rows[columns], fit_rows["rul"], **kw)
    q_lo = models.train_quantile_model(fit_rows[columns], fit_rows["rul"], quantile=alpha / 2, **kw)
    q_hi = models.train_quantile_model(fit_rows[columns], fit_rows["rul"], quantile=1 - alpha / 2, **kw)
    cal = evaluate.random_rows_per_engine(cal_rows, n_per_engine=truncations_per_engine, seed=seed)
    scores = conformity_scores(cal["rul"].to_numpy(dtype=float), q_lo.predict(cal[columns]), q_hi.predict(cal[columns]))
    qhat = conformal_quantile(scores, alpha)
    if asymmetric:
        y_cal = cal["rul"].to_numpy(dtype=float)
        qhat_lo = conformal_quantile(q_lo.predict(cal[columns]) - y_cal, alpha / 2)
        qhat_hi = conformal_quantile(y_cal - q_hi.predict(cal[columns]), alpha / 2)
    else:
        qhat_lo = qhat_hi = qhat
    model = CQRModel(point=point, q_lo=q_lo, q_hi=q_hi, alpha=alpha, qhat=qhat, columns=list(columns),
                     training_units=train_units, calibration_units=calib_units, n_calibration_rows=int(len(cal)),
                     truncations_per_engine=truncations_per_engine, seed=seed, calibration_scores=[float(s) for s in scores],
                     serious_lower_max=float(serious_lower_max), asymmetric=bool(asymmetric), qhat_lo=float(qhat_lo), qhat_hi=float(qhat_hi))
    _, lo_all, hi_all = model.predict(cal_rows[columns])
    serious = lo_all <= serious_lower_max
    widths = (hi_all - lo_all)[serious] if serious.any() else (hi_all - lo_all)
    model.suggested_max_width = float(np.percentile(widths, width_percentile))
    return model
