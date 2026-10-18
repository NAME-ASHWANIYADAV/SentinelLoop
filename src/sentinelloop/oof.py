"""Out-of-fold (OOF) predictions over complete run-to-failure training trajectories.

Every training engine is predicted by a CQR model (and an anomaly detector) fit on the OTHER folds'
engines, with the conformal calibration split taken inside those folds. The result is a leakage-free
cycle-by-cycle prediction table with the known failure cycle, which is what the policy replay needs.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import anomaly, conformal, evaluate, models


def oof_cqr_predictions(train_f: pd.DataFrame, columns: list[str], n_folds: int, alpha: float, calib_frac: float, seed: int = 42,
                        max_iter: int = 400, learning_rate: float = 0.05, max_leaf_nodes: int = 31, truncations_per_engine: int = 5,
                        healthy_frac: float = 0.4, threshold_pct: float = 99.0, sustain: int = 3, warmup: int = 20, log=None,
                        with_baselines: bool = False, rf_trees: int = 150, top_k: int = 3):
    """`with_baselines=True` adds point_naive, point_rf and point_hgbr_all (HGBR on all of the fold's
    training engines, i.e. without the conformal calibration hold-out) for model comparisons (E5)."""
    parts = []
    folds: dict[int, dict] = {}
    for k, (tr_idx, va_idx) in enumerate(evaluate.engine_folds(train_f, n_folds=n_folds, seed=seed)):
        tr = train_f.iloc[tr_idx]
        va = train_f.iloc[va_idx].copy()
        cqr = conformal.fit_cqr(tr, columns, alpha=alpha, calib_frac=calib_frac, seed=seed + k, truncations_per_engine=truncations_per_engine,
                                max_iter=max_iter, learning_rate=learning_rate, max_leaf_nodes=max_leaf_nodes)
        det = anomaly.AnomalyDetector.fit(tr, columns, healthy_frac=healthy_frac, threshold_pct=threshold_pct, seed=seed, warmup=warmup, top_k=top_k)
        point, lower, upper = cqr.predict(va[columns])
        va["point"], va["lower"], va["upper"] = point, lower, upper
        if with_baselines:
            y_tr = tr["rul"].to_numpy()
            va["point_naive"] = models.NaiveMean().fit(y_tr).predict(va[columns])
            va["point_rf"] = models.train_random_forest(tr[columns], y_tr, n_estimators=rf_trees, seed=seed + k).predict(va[columns])
            va["point_hgbr_all"] = models.train_point_model(tr[columns], y_tr, max_iter=max_iter, learning_rate=learning_rate, max_leaf_nodes=max_leaf_nodes, seed=seed + k).predict(va[columns])
        va["anomaly_score"] = det.score(va[columns])
        va["anomaly_exceed"] = va["anomaly_score"] > det.threshold
        va["anomaly_flag"] = anomaly.sustained_per_unit(va, "anomaly_exceed", sustain)
        va["fold"] = k
        va["failure_cycle"] = va["cycle"] + va["rul_raw"]
        va["max_width"] = cqr.suggested_max_width
        keep = ["unit", "cycle", "rul", "rul_raw", "point", "lower", "upper", "fold", "anomaly_score", "anomaly_flag", "failure_cycle", "max_width"]
        keep += [c for c in ("n_imputed", "point_naive", "point_rf", "point_hgbr_all") if c in va.columns]
        parts.append(va[keep])
        folds[k] = {"train_units": list(cqr.training_units), "calib_units": list(cqr.calibration_units), "val_units": sorted(int(u) for u in va["unit"].unique()),
                    "qhat": float(cqr.qhat), "suggested_max_width": float(cqr.suggested_max_width)}
        if log:
            log(f"  fold {k + 1}/{n_folds}: {len(folds[k]['val_units'])} engines predicted out of fold (qhat {cqr.qhat:.2f})")
    out = pd.concat(parts, ignore_index=True).sort_values(["unit", "cycle"]).reset_index(drop=True)
    return out, folds
