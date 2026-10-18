"""E7 — Ablations on FD001 and FD004: regime normalisation, rolling features, EMA denoising, anomaly
input to the agent, interval vs point policy. Reports official test RMSE/PICP and holdout decision
metrics (20% of training engines held out, one split)."""
from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd

from common import ROOT, log, markdown_table, save, thresholds
from sentinelloop import agent, clean, config, conformal, data, evaluate, features, metrics, policy, replay, targets

MIN_LEAD = 5


def variant(subset: str, name: str, n_regimes: int | None, rolling: bool, ema: float, fast: bool, asymmetric: bool = False) -> dict:
    cfg = config.load(subset, ROOT / "configs")
    seed = int(cfg["seed"]); cap = int(cfg["rul_cap"]); window = int(cfg["features"]["window"])
    mcfg = dict(cfg["model"]); mcfg["max_iter"] = 60 if fast else mcfg["max_iter"]
    ds = data.load_subset(subset, ROOT / "data" / "raw")
    tr, te = clean.impute(ds.train), clean.impute(ds.test)
    if ema:
        tr, te = clean.ema_denoise(tr, ema, data.SENSORS), clean.ema_denoise(te, ema, data.SENSORS)
    nreg = int(cfg["clean"]["n_regimes"]) if n_regimes is None else n_regimes
    state = clean.CleanState.fit(tr, n_regimes=nreg, std_threshold=float(cfg["clean"]["drop_sensor_std_threshold"]), seed=seed)
    a, b = state.transform(tr), state.transform(te)
    if rolling:
        fa, fb = features.build_features(a, state.kept_sensors, window), features.build_features(b, state.kept_sensors, window)
    else:
        fa, fb = a.copy(), b.copy()
    fa = targets.add_train_rul(fa, cap)
    cols = features.feature_manifest(fa)
    units = np.array(sorted(fa["unit"].unique())); rng = np.random.default_rng(seed); rng.shuffle(units)
    hold = sorted(units[: int(round(0.2 * len(units)))].tolist())
    fit_f, hold_f = fa[~fa.unit.isin(hold)], fa[fa.unit.isin(hold)].copy()
    ccfg = cfg["conformal"]
    cqr = conformal.fit_cqr(fit_f, cols, alpha=float(ccfg["alpha"]), calib_frac=float(ccfg["calib_frac"]), seed=seed, truncations_per_engine=int(ccfg["truncations_per_engine"]), asymmetric=asymmetric, **mcfg)
    last = evaluate.last_cycle_rows(fb)
    tc, trw = targets.test_truth(ds.rul, cap)
    p, lo, hi = cqr.predict(last[cols])
    hold_f["point"], hold_f["lower"], hold_f["upper"] = cqr.predict(hold_f[cols])
    hold_f["rul_true_raw"] = hold_f["rul_raw"]
    thr = thresholds(cfg)
    mA = replay.decision_metrics(replay.replay_policy(hold_f, policy.Policy("A", "point", thr.t_high), min_lead=MIN_LEAD))
    mC = replay.decision_metrics(replay.replay_policy(hold_f, policy.Policy("C", "lower", thr.t_high), min_lead=MIN_LEAD))
    return {"subset": subset, "variant": name, "n_features": len(cols), "test_rmse_capped": metrics.rmse(tc, p), "test_rmse_raw": metrics.rmse(trw, p), "test_picp": metrics.picp(tc, lo, hi), "test_mpiw": metrics.mpiw(lo, hi),
            "holdout_late_rate_point": mA["late_rate"], "holdout_discarded_point": mA["mean_discarded_life"], "holdout_late_rate_lower": mC["late_rate"], "holdout_discarded_lower": mC["mean_discarded_life"]}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--subsets", nargs="*", default=["FD001", "FD004"]); ap.add_argument("--fast", action="store_true")
    args = ap.parse_args()
    rows = []
    for s in args.subsets:
        log(f"=== E7 {s} ===")
        rows.append(variant(s, "full", None, True, 0.0, args.fast))
        if s in ("FD002", "FD004"):
            rows.append(variant(s, "no_regime_normalisation", 1, True, 0.0, args.fast))
        rows.append(variant(s, "raw_sensors_only_no_rolling", None, False, 0.0, args.fast))
        rows.append(variant(s, "with_ema_0.3", None, True, 0.3, args.fast))
        rows.append(variant(s, "asymmetric_cqr", None, True, 0.0, args.fast, asymmetric=True))
    tab = pd.DataFrame(rows)
    conclusion = "Ablation table: each row removes or adds one component; compare with 'full'. The point-vs-lower-bound columns are the policy ablation."
    save("e7_ablation", {"table": tab.to_dict(orient="records"), "conclusion": conclusion, "fast": args.fast}, "# E7 — Ablations\n\n" + markdown_table(tab) + "\n\n" + conclusion + "\n", {"e7_table.csv": tab})
    log(conclusion)


if __name__ == "__main__":
    main()
