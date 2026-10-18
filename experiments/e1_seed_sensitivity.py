"""E1 seed sensitivity (added after the red-team review, finding ML-6): the pre-registered protocol promised five seeds
where randomness exists, and the main run used one (seed 42). This script repeats the core E1 comparison (policy A on the
point estimate vs policy C on the conformal lower bound, generic threshold 25 and tuned C threshold) on FD001 for
several seeds. Each seed changes the engine folds, the conformal calibration split and the tune/eval split.

    .venv/Scripts/python.exe experiments/e1_seed_sensitivity.py [--subsets FD001] [--seeds 42 43 44] [--fast]
"""
from __future__ import annotations

import argparse
import time

import numpy as np
import pandas as pd

from common import ROOT, log, markdown_table, prepared, save, thresholds, tune_eval_split
from sentinelloop import config, oof, policy, replay

MIN_LEAD = 5
TARGET_LATE = 0.05


def run_seed(subset: str, seed: int, fast: bool) -> dict:
    cfg = config.load(subset, ROOT / "configs")
    cfg["seed"] = int(seed)
    cfg, ds, state, train_f, test_f, cols = prepared(subset, cfg)
    mcfg = dict(cfg["model"])
    if fast:
        mcfg["max_iter"] = 60
    t0 = time.time()
    df, folds = oof.oof_cqr_predictions(train_f, cols, n_folds=int(cfg["cv"]["n_folds"]), alpha=float(cfg["conformal"]["alpha"]),
                                        calib_frac=float(cfg["conformal"]["calib_frac"]), seed=seed, max_iter=mcfg["max_iter"],
                                        learning_rate=mcfg["learning_rate"], max_leaf_nodes=mcfg["max_leaf_nodes"],
                                        truncations_per_engine=int(cfg["conformal"]["truncations_per_engine"]),
                                        healthy_frac=float(cfg["anomaly"]["healthy_frac"]), threshold_pct=float(cfg["anomaly"]["threshold_pct"]),
                                        sustain=int(cfg["anomaly"]["sustain"]), warmup=int(cfg["features"]["window"]), log=lambda m: None,
                                        top_k=int(cfg["anomaly"].get("top_k", 3)))
    df["rul_true_raw"] = df["rul_raw"]
    thr = thresholds(cfg)
    T = thr.t_high
    tune_units, eval_units = tune_eval_split(df["unit"].unique(), seed=seed)
    tune, ev = df[df.unit.isin(tune_units)], df[df.unit.isin(eval_units)]
    grid = np.arange(0, 126, 1.0)
    out = {"subset": subset, "seed": seed, "n_eval_engines": int(ev["unit"].nunique()), "oof_s": round(time.time() - t0, 1)}
    for name, pol in (("A_point_T", policy.Policy("A", "point", T)), ("C_lower_T", policy.Policy("C", "lower", T))):
        m = replay.decision_metrics(replay.replay_policy(ev, pol, min_lead=MIN_LEAD))
        out[f"{name}_late"], out[f"{name}_discarded"] = m["late_rate"], m["mean_discarded_life"]
    tC = replay.tune_threshold(tune, "lower", TARGET_LATE, grid, min_lead=MIN_LEAD)
    tA = replay.tune_threshold(tune, "point", TARGET_LATE, grid, min_lead=MIN_LEAD)
    for name, kind, th in (("C_lower_tuned", "lower", tC), ("A_point_tuned", "point", tA)):
        m = replay.decision_metrics(replay.replay_policy(ev, policy.Policy(name, kind, th), min_lead=MIN_LEAD))
        out[f"{name}_threshold"], out[f"{name}_late"], out[f"{name}_discarded"] = float(th), m["late_rate"], m["mean_discarded_life"]
    out["gap_discarded_C_minus_A_at_T"] = out["C_lower_T_discarded"] - out["A_point_T_discarded"]
    log(f"[{subset}] seed {seed}: A@25 late {out['A_point_T_late']:.3f} disc {out['A_point_T_discarded']:.1f} | C@25 late {out['C_lower_T_late']:.3f} disc {out['C_lower_T_discarded']:.1f} "
        f"| tuned C {tC:.0f}: late {out['C_lower_tuned_late']:.3f} disc {out['C_lower_tuned_discarded']:.1f} | tuned A {tA:.0f}: late {out['A_point_tuned_late']:.3f} disc {out['A_point_tuned_discarded']:.1f} ({out['oof_s']} s)")
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--subsets", nargs="*", default=["FD001"]); ap.add_argument("--seeds", nargs="*", type=int, default=[42, 43, 44])
    ap.add_argument("--fast", action="store_true")
    args = ap.parse_args()
    rows = [run_seed(s, seed, args.fast) for s in args.subsets for seed in args.seeds]
    tab = pd.DataFrame(rows)
    summary = {}
    for s, g in tab.groupby("subset"):
        summary[s] = {c: {"mean": float(g[c].mean()), "std": float(g[c].std(ddof=1)) if len(g) > 1 else 0.0, "min": float(g[c].min()), "max": float(g[c].max())}
                      for c in ["A_point_T_late", "C_lower_T_late", "A_point_T_discarded", "C_lower_T_discarded", "gap_discarded_C_minus_A_at_T",
                                "C_lower_tuned_threshold", "C_lower_tuned_late", "C_lower_tuned_discarded", "A_point_tuned_threshold", "A_point_tuned_late", "A_point_tuned_discarded"]}
    conclusion = "; ".join(f"{s}: over {len(tab[tab.subset == s])} seeds the lower-bound policy discards {v['gap_discarded_C_minus_A_at_T']['min']:.1f}-{v['gap_discarded_C_minus_A_at_T']['max']:.1f} more cycles than the point policy at T=25 "
                           f"(late rates A {v['A_point_T_late']['min']:.3f}-{v['A_point_T_late']['max']:.3f}, C {v['C_lower_T_late']['min']:.3f}-{v['C_lower_T_late']['max']:.3f}); tuned C thresholds {v['C_lower_tuned_threshold']['min']:.0f}-{v['C_lower_tuned_threshold']['max']:.0f}"
                           for s, v in summary.items())
    readme = "# E1 seed sensitivity (post hoc; finding ML-6)\n\n" + markdown_table(tab) + "\n\n## Summary\n" + conclusion + "\n"
    save("e1_seed_sensitivity", {"hypothesis": "H1 (seed sensitivity)", "table": tab.to_dict(orient="records"), "summary": summary, "conclusion": conclusion, "fast": args.fast, "seeds": args.seeds}, readme, {"e1_seed_table.csv": tab})
    log(conclusion)


if __name__ == "__main__":
    main()
