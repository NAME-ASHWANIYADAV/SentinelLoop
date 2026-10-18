"""E5 — Decision metrics vs RMSE (hypothesis H5): does RMSE order models the way decision metrics do?

Models from the out-of-fold table: naive mean, RandomForest, HGBR (all training engines of the fold),
HGBR 70%-engine point model (the CQR point model), and HGBR+CQR lower bound (policy C). RMSE on random
truncation rows of the eval engines; late rate and discarded life from the replay at the same threshold.
"""
from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from common import ROOT, SUBSETS, log, markdown_table, oof_table, save, thresholds, tune_eval_split
from sentinelloop import agent, config, evaluate, metrics, policy, replay

MIN_LEAD = 5


def run_subset(subset: str, fast: bool) -> list[dict]:
    cfg = config.load(subset, ROOT / "configs")
    thr = thresholds(cfg)
    T = thr.t_high
    oof_df, _ = oof_table(subset, fast=fast, with_baselines=True)
    _, eval_units = tune_eval_split(oof_df["unit"].unique(), seed=int(cfg["seed"]))
    ev = oof_df[oof_df.unit.isin(eval_units)].copy()
    ev["rul_true_raw"] = ev["rul_raw"]
    rows_eval = evaluate.random_rows_per_engine(ev, n_per_engine=5, seed=int(cfg["seed"]))
    models = {"naive_mean": ("point_naive", "point"), "random_forest": ("point_rf", "point"), "hgbr_all_fold_engines": ("point_hgbr_all", "point"),
              "hgbr_70pct_point": ("point", "point"), "hgbr_cqr_lower_bound": ("lower", "lower")}
    out = []
    for name, (col, kind) in models.items():
        df = ev.copy()
        if kind == "point":
            df["point"] = df[col]
        rmse = metrics.rmse(rows_eval["rul"], rows_eval[col] if kind == "point" else rows_eval["point"])
        rep = replay.decision_metrics(replay.replay_policy(df, policy.Policy(name, kind, T), min_lead=MIN_LEAD))
        out.append({"subset": subset, "model": name, "rmse_eval_random_truncation": rmse, "late_rate": rep["late_rate"], "mean_discarded_life": rep["mean_discarded_life"], "early_rate": rep["early_rate"]})
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--subsets", nargs="*", default=SUBSETS); ap.add_argument("--fast", action="store_true")
    args = ap.parse_args()
    rows = []
    for s in args.subsets:
        log(f"=== E5 {s} ===")
        rows += run_subset(s, args.fast)
    tab = pd.DataFrame(rows)
    verdicts = {}
    for s, g in tab.groupby("subset"):
        g = g.sort_values("rmse_eval_random_truncation")
        rho_late = spearmanr(g["rmse_eval_random_truncation"], g["late_rate"]).correlation if g["late_rate"].nunique() > 1 else float("nan")
        inversions = []
        for i in range(len(g)):
            for j in range(i + 1, len(g)):
                a, b = g.iloc[i], g.iloc[j]  # a has lower RMSE than b
                if a["late_rate"] > b["late_rate"] + 1e-9 or a["mean_discarded_life"] > b["mean_discarded_life"] + 1e-9:
                    inversions.append(f"{a['model']} (rmse {a['rmse_eval_random_truncation']:.2f}) vs {b['model']} (rmse {b['rmse_eval_random_truncation']:.2f}): late {a['late_rate']:.3f} vs {b['late_rate']:.3f}, discarded {a['mean_discarded_life']:.1f} vs {b['mean_discarded_life']:.1f}")
        verdicts[s] = {"spearman_rmse_vs_late": None if rho_late != rho_late else float(rho_late), "inversions": inversions}
    any_inv = any(v["inversions"] for v in verdicts.values())
    conclusion = f"H5: an RMSE-vs-decision-metric inversion exists on {sum(bool(v['inversions']) for v in verdicts.values())}/{len(verdicts)} subsets. Pre-registered criterion (at least one): {'SUPPORTED' if any_inv else 'NOT SUPPORTED'}."
    readme = "# E5 — Decision metrics vs RMSE (H5)\n\n" + markdown_table(tab) + "\n\n## Verdict\n" + conclusion + "\n\n```json\n" + json.dumps(verdicts, indent=1) + "\n```\n"
    save("e5_decision_vs_rmse", {"hypothesis": "H5", "table": tab.to_dict(orient="records"), "verdicts": verdicts, "conclusion": conclusion, "fast": args.fast}, readme, {"e5_table.csv": tab})
    log(conclusion)


if __name__ == "__main__":
    main()
