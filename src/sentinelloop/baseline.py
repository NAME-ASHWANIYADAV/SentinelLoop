"""E0: reproducible baseline (naive mean, RandomForest, HistGradientBoosting) with the official
last-cycle protocol, the leakage demonstration and artefacts saved per subset."""
from __future__ import annotations

import json
import pickle
import platform
import time
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn

from . import clean, config, data, evaluate, features, metrics, models, targets


def prepare_frames(ds: data.Dataset, cfg: dict):
    """Fit the cleaning state on TRAIN only, transform train and test, build causal features."""
    ccfg = cfg["clean"]
    train_i = clean.impute(ds.train)
    test_i = clean.impute(ds.test)
    alpha = ccfg.get("ema_alpha") or 0.0
    if alpha:
        train_i = clean.ema_denoise(train_i, alpha, data.SENSORS)
        test_i = clean.ema_denoise(test_i, alpha, data.SENSORS)
    state = clean.CleanState.fit(train_i, n_regimes=int(ccfg["n_regimes"]), std_threshold=float(ccfg["drop_sensor_std_threshold"]), seed=int(cfg["seed"]))
    train_c = state.transform(train_i)
    test_c = state.transform(test_i)
    w = int(cfg["features"]["window"])
    train_f = targets.add_train_rul(features.build_features(train_c, state.kept_sensors, w), cap=int(cfg["rul_cap"]))
    test_f = features.build_features(test_c, state.kept_sensors, w)
    cols = features.feature_manifest(train_f)
    return state, train_f, test_f, cols


def run_baseline(subset: str, data_dir="data/raw", out_dir="artifacts", config_dir="configs", fast: bool = False, seed: int | None = None) -> dict:
    t0 = time.time()
    cfg = config.load(subset, config_dir)
    if seed is not None:
        cfg["seed"] = int(seed)
    mcfg = dict(cfg["model"])
    n_folds = int(cfg["cv"]["n_folds"])
    rf_trees = 200
    if fast:
        mcfg["max_iter"] = 60
        n_folds = 3
        rf_trees = 50
    ds = data.load_subset(subset, data_dir)
    state, train_f, test_f, cols = prepare_frames(ds, cfg)
    cap = int(cfg["rul_cap"])
    y = train_f["rul"].to_numpy()

    # ---- engine-level cross-validation: honest (random cycle) vs leakage-prone (last cycle) protocol
    cv_all, cv_last, cv_rand = [], [], []
    for tr_idx, va_idx in evaluate.engine_folds(train_f, n_folds=n_folds, seed=int(cfg["seed"])):
        m = models.train_point_model(train_f.iloc[tr_idx][cols], y[tr_idx], seed=int(cfg["seed"]), **mcfg)
        va = train_f.iloc[va_idx]
        p = m.predict(va[cols])
        cv_all.append(metrics.rmse(va["rul"], p))
        last = va.groupby("unit")["cycle"].transform("max") == va["cycle"]
        cv_last.append(metrics.rmse(va.loc[last, "rul"], p[last.to_numpy()]))
        rand = evaluate.random_rows_per_engine(va, n_per_engine=5, seed=int(cfg["seed"]))
        cv_rand.append(metrics.rmse(rand["rul"], m.predict(rand[cols])))

    # ---- final models on all training engines
    hgbr = models.train_point_model(train_f[cols], y, seed=int(cfg["seed"]), **mcfg)
    rf = models.train_random_forest(train_f[cols], y, n_estimators=rf_trees, seed=int(cfg["seed"]))
    naive = models.NaiveMean().fit(y)

    last_test = evaluate.last_cycle_rows(test_f)
    truth_capped, truth_raw = targets.test_truth(ds.rul, cap)
    pred = {"hgbr": hgbr.predict(last_test[cols]), "rf": rf.predict(last_test[cols]), "naive": naive.predict(last_test[cols])}
    m: dict = {
        "subset": subset, "n_test_units": int(len(truth_raw)), "rul_cap": cap, "fast": fast,
        "cv_rmse_all_rows": float(np.mean(cv_all)),
        "cv_rmse_last_cycle_naive_protocol": float(np.mean(cv_last)),
        "cv_rmse_random_truncation_protocol": float(np.mean(cv_rand)),
    }
    for name, p in pred.items():
        m[f"{name}_rmse_capped"] = metrics.rmse(truth_capped, p)
        m[f"{name}_rmse_raw"] = metrics.rmse(truth_raw, p)
        m[f"{name}_mae_capped"] = metrics.mae(truth_capped, p)
        m[f"{name}_phm08"] = metrics.phm08_score(truth_capped, p)
    m["phm08_convention"] = metrics.PHM08_CONVENTION
    m["data_hashes"] = data.file_hashes(subset, data_dir)
    m["dropped_sensors"] = state.dropped_sensors
    m["n_features"] = len(cols)
    m["config_hash"] = config.config_hash(cfg)
    m["versions"] = {"python": platform.python_version(), "sklearn": sklearn.__version__, "pandas": pd.__version__, "numpy": np.__version__}
    m["elapsed_s"] = round(time.time() - t0, 1)

    out = Path(out_dir) / "baseline" / subset   # never overwrites the pipeline artefacts of the same subset
    out.mkdir(parents=True, exist_ok=True)
    (out / "metrics.json").write_text(json.dumps(m, indent=1), encoding="utf-8")
    preds = last_test[["unit", "cycle"]].copy()
    preds["rul_true_capped"] = truth_capped
    preds["rul_true_raw"] = truth_raw
    for name, p in pred.items():
        preds[f"pred_{name}"] = p
    preds.to_csv(out / "predictions_test.csv", index=False)
    (out / "feature_manifest.json").write_text(json.dumps(cols, indent=1), encoding="utf-8")
    # Pickled artefacts are produced and consumed only by this package on this machine.
    with open(out / "clean_state.pkl", "wb") as fh:
        pickle.dump(state, fh)
    with open(out / "model_point.pkl", "wb") as fh:
        pickle.dump(hgbr, fh)
    return {"metrics": m, "state": state, "model": hgbr, "columns": cols, "train": train_f, "test": test_f, "dataset": ds, "config": cfg}
