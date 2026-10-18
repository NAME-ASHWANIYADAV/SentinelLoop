"""Evaluation metrics with the conventions stated explicitly."""
from __future__ import annotations

import numpy as np

PHM08_CONVENTION = (
    "PHM08 score: d = pred - true; early (d < 0): exp(-d/13) - 1; late (d >= 0): exp(d/10) - 1; "
    "summed over engines (late predictions are penalised more). Saxena et al. 2008: a1=13 (early, d<0), a2=10 (late, d>=0)."
)


def rmse(y_true, y_pred) -> float:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    return float(np.sqrt(np.mean((y_pred - y_true) ** 2)))


def mae(y_true, y_pred) -> float:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    return float(np.mean(np.abs(y_pred - y_true)))


def phm08_score(y_true, y_pred) -> float:
    d = np.asarray(y_pred, dtype=float) - np.asarray(y_true, dtype=float)
    return float(np.sum(np.where(d < 0, np.exp(-d / 13.0) - 1.0, np.exp(d / 10.0) - 1.0)))


def picp(y_true, lower, upper) -> float:
    y_true = np.asarray(y_true, dtype=float)
    return float(np.mean((y_true >= np.asarray(lower)) & (y_true <= np.asarray(upper))))


def mpiw(lower, upper) -> float:
    return float(np.mean(np.asarray(upper, dtype=float) - np.asarray(lower, dtype=float)))
