"""E1 — Maintenance-policy replay (hypothesis H1).

Policies on identical out-of-fold predictions over complete training trajectories:
  A point-threshold, B point-minus-margin (NOTE: B is the same family as A, since point - m <= T is
  point <= T + m; it is kept because it was pre-registered, and reported as such), C interval-lower-bound,
  D cost-tuned point threshold for assumed failure costs of 25/50/100/200/500 cycles of discarded life.
Primary (pre-registered) tests: (i) late rate C < A at the same threshold; (ii) at a matched late rate
(tuned to <= 5% on tuning engines) C discards no more life than B.
Secondary (added after the fast smoke run showed zero late orders at T=25 for both policies, so (i)
was uninformative there): the late-rate / discarded-life FRONTIER of the A-family vs the C-family,
obtained by tuning each family on the tuning engines to late-rate targets 0%, 2.5%, 5%, 10% and
evaluating on the eval engines. Labelled as secondary in the results.
"""
from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd

from common import ARTIFACTS, SUBSETS, log, markdown_table, oof_table, prepared, save, severities_for_engine, thresholds, tune_eval_split
from sentinelloop import config, policy, replay, targets

MIN_LEAD = 5
TARGET_LATE = 0.05
COST_RATIOS = [25, 50, 100, 200, 500]
FRONTIER_TARGETS = [0.0, 0.025, 0.05, 0.10]


def churn_for_policy(df_eval: pd.DataFrame, thr, kind: str) -> float:
    """Mean number of severity changes before the first HIGH/CRITICAL decision (C-family: the agent on
    the lower bound; A-family: the same thresholds on the point estimate)."""
    vals = []
    for u, g in df_eval.groupby("unit"):
        g = g.sort_values("cycle")
        if kind == "lower":
            sev = [d.severity for d in severities_for_engine(g, thr)]
        else:
            lb = g["point"].to_numpy()
            sev = ["CRITICAL" if x <= thr.t_critical else "HIGH" if x <= thr.t_high else "MEDIUM" if x <= thr.t_medium else "NONE" for x in lb]
        first = next((i for i, s in enumerate(sev) if s in ("HIGH", "CRITICAL")), len(sev) - 1)
        vals.append(replay.churn(sev[: first + 1]))
    return float(np.mean(vals)) if vals else float("nan")


def run_subset(subset: str, fast: bool, cfg_dir) -> tuple[list[dict], dict, pd.DataFrame, list[dict]]:
    cfg = config.load(subset, cfg_dir)
    thr = thresholds(cfg)
    T = thr.t_high
    oof_df, meta = oof_table(subset, fast=fast)
    oof_df["rul_true_raw"] = oof_df["rul_raw"]
    tune_units, eval_units = tune_eval_split(oof_df["unit"].unique(), seed=int(cfg["seed"]))
    tune = oof_df[oof_df.unit.isin(tune_units)]
    ev = oof_df[oof_df.unit.isin(eval_units)]
    grid = np.arange(0, 126, 1.0)

    pols = {"A_point_T": policy.Policy("A", "point", T), "C_lower_T": policy.Policy("C", "lower", T)}
    tC = replay.tune_threshold(tune, "lower", TARGET_LATE, grid, min_lead=MIN_LEAD)
    mB = replay.tune_margin(tune, T, TARGET_LATE, np.arange(0, 80, 1.0), min_lead=MIN_LEAD)
    tA = replay.tune_threshold(tune, "point", TARGET_LATE, grid, min_lead=MIN_LEAD)
    pols["A_point_matched"] = policy.Policy("A*", "point", tA)
    pols["B_margin_matched"] = policy.Policy("B*", "margin", T, margin=mB)
    pols["C_lower_matched"] = policy.Policy("C*", "lower", tC)
    for r in COST_RATIOS:
        best_t, best_c = None, None
        for t in grid:
            m = replay.decision_metrics(replay.replay_policy(tune, policy.Policy("D", "point", t), min_lead=MIN_LEAD))
            c = replay.expected_cost(m, cost_ratio=float(r))
            if best_c is None or c < best_c:
                best_c, best_t = c, t
        pols[f"D_cost_{r}"] = policy.Policy(f"D{r}", "cost", float(best_t))

    rows, per_engine = [], []
    for name, p in pols.items():
        out = replay.replay_policy(ev, p, min_lead=MIN_LEAD)
        out["policy_id"] = name
        per_engine.append(out)
        m = replay.decision_metrics(out)
        rows.append({"subset": subset, "policy": name, "rule": p.describe(), "threshold": p.threshold, "margin": p.margin,
                     **{k: m[k] for k in ["n_engines", "n_evaluable", "late_rate", "mean_discarded_life", "median_discarded_life", "order_rate", "early_rate", "n_late"]},
                     "churn": churn_for_policy(ev, thr, "lower" if p.kind == "lower" else "point") if name in ("A_point_T", "C_lower_T") else np.nan})
    tab = pd.DataFrame(rows)
    get = lambda n, k: float(tab.loc[tab.policy == n, k].iloc[0])

    # secondary: frontier at matched late-rate targets (tuned on tuning engines, evaluated on eval engines)
    frontier = []
    for tgt in FRONTIER_TARGETS:
        ta = replay.tune_threshold(tune, "point", tgt, grid, min_lead=MIN_LEAD)
        tc = replay.tune_threshold(tune, "lower", tgt, grid, min_lead=MIN_LEAD)
        ma = replay.decision_metrics(replay.replay_policy(ev, policy.Policy("A", "point", ta), min_lead=MIN_LEAD))
        mc = replay.decision_metrics(replay.replay_policy(ev, policy.Policy("C", "lower", tc), min_lead=MIN_LEAD))
        frontier.append({"subset": subset, "target_late_rate": tgt, "A_threshold": ta, "A_late_eval": ma["late_rate"], "A_discarded_eval": ma["mean_discarded_life"],
                         "C_threshold": tc, "C_late_eval": mc["late_rate"], "C_discarded_eval": mc["mean_discarded_life"],
                         "C_better_or_equal": bool(mc["late_rate"] <= ma["late_rate"] + 1e-9 and mc["mean_discarded_life"] <= ma["mean_discarded_life"] + 1e-9),
                         "C_dominated": bool(mc["late_rate"] > ma["late_rate"] + 1e-9 and mc["mean_discarded_life"] > ma["mean_discarded_life"] + 1e-9)})

    verdict = {
        "H1_i_late_rate_C_lt_A_equal_threshold": bool(get("C_lower_T", "late_rate") < get("A_point_T", "late_rate")),
        "H1_i_informative": bool(get("A_point_T", "late_rate") > 0 or get("C_lower_T", "late_rate") > 0),
        "late_A_T": get("A_point_T", "late_rate"), "late_C_T": get("C_lower_T", "late_rate"),
        "discarded_A_T": get("A_point_T", "mean_discarded_life"), "discarded_C_T": get("C_lower_T", "mean_discarded_life"),
        "H1_ii_discarded_C_le_B_matched": bool(get("C_lower_matched", "mean_discarded_life") <= get("B_margin_matched", "mean_discarded_life")),
        "discarded_B_matched": get("B_margin_matched", "mean_discarded_life"), "discarded_C_matched": get("C_lower_matched", "mean_discarded_life"),
        "late_B_matched_eval": get("B_margin_matched", "late_rate"), "late_C_matched_eval": get("C_lower_matched", "late_rate"),
        "tuned": {"tC": tC, "mB": mB, "tA": tA}, "n_tune": len(tune_units), "n_eval": len(eval_units),
        "frontier_C_better_or_equal_count": int(sum(f["C_better_or_equal"] for f in frontier)), "frontier_C_dominated_count": int(sum(f["C_dominated"] for f in frontier)),
        "note": "B (point minus margin) is the same policy family as A; reported because it was pre-registered.",
    }

    cfg2, ds, state, train_f, test_f, cols = prepared(subset, cfg)
    test_view = {}
    pred_path = ARTIFACTS / subset / "predictions_test_all_cycles.csv"
    if pred_path.exists():
        pt = pd.read_csv(pred_path)
        last = pt.groupby("unit")["cycle"].max()
        cap_truth, raw_truth = targets.test_truth(ds.rul, int(cfg["rul_cap"]))
        fail = {u: int(last[u] + raw_truth[i]) for i, u in enumerate(sorted(last.index))}
        pt["failure_cycle"] = pt["unit"].map(fail)
        for name in ("A_point_T", "C_lower_T"):
            o = replay.replay_policy(pt, pols[name], min_lead=MIN_LEAD)
            m = replay.decision_metrics(o)
            test_view[name] = {k: m[k] for k in ["n_engines", "n_pending", "n_evaluable", "late_rate", "order_rate", "mean_discarded_life"]}
    verdict["test_engine_view"] = test_view
    return rows, verdict, pd.concat(per_engine, ignore_index=True), frontier


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--subsets", nargs="*", default=SUBSETS)
    ap.add_argument("--fast", action="store_true")
    args = ap.parse_args()
    from common import ROOT
    all_rows, verdicts, tables, fronts = [], {}, {}, []
    for s in args.subsets:
        log(f"=== E1 {s} ===")
        rows, v, pe, fr = run_subset(s, args.fast, ROOT / "configs")
        all_rows += rows
        verdicts[s] = v
        tables[f"e1_{s}_per_engine.csv"] = pe
        fronts += fr
    tab = pd.DataFrame(all_rows)
    ftab = pd.DataFrame(fronts)
    tables["e1_frontier.csv"] = ftab
    n = len(verdicts)
    n_i = sum(v["H1_i_late_rate_C_lt_A_equal_threshold"] for v in verdicts.values())
    n_i_inf = sum(v["H1_i_informative"] for v in verdicts.values())
    n_ii = sum(v["H1_ii_discarded_C_le_B_matched"] for v in verdicts.values())
    fr_better = int(ftab["C_better_or_equal"].sum()); fr_dom = int(ftab["C_dominated"].sum()); fr_n = len(ftab)
    supported = (n_i >= min(3, n)) and (n_ii >= min(3, n))
    conclusion = (f"H1 primary (pre-registered): (i) late rate C<A at equal threshold on {n_i}/{n} subsets (informative, i.e. any late orders at T=25, on {n_i_inf}/{n}); "
                  f"(ii) discarded life C<=B at matched late rate on {n_ii}/{n} subsets; criterion (>=3/4 on both): {'SUPPORTED' if supported else 'NOT SUPPORTED'}. "
                  f"Secondary frontier (A-family vs C-family at matched late-rate targets {FRONTIER_TARGETS}): C better-or-equal on both metrics in {fr_better}/{fr_n} target points, C dominated in {fr_dom}/{fr_n}.")
    readme = ("# E1 — Maintenance-policy replay (H1)\n\nProtocol: out-of-fold CQR predictions over complete training trajectories (5 engine folds, inner 30% calibration split); "
              f"tune/eval engine split 30/70; min lead {MIN_LEAD} cycles; target late rate {TARGET_LATE:.0%} for the pre-registered matched comparison; cost ratios are ASSUMED failure costs in cycles of discarded life ({COST_RATIOS}).\n\n"
              "Note: policy B (point minus margin) is the same family as policy A (a shifted threshold); it is reported because it was pre-registered. The informative comparison is the A-family vs the C-family (lower bound) frontier below (secondary analysis, added after the fast smoke run showed zero late orders at T=25).\n\n## Pre-registered table\n"
              + markdown_table(tab.drop(columns=["rule"])) + "\n\n## Secondary: late-rate / discarded-life frontier (tuned on tuning engines, evaluated on eval engines)\n" + markdown_table(ftab)
              + "\n\n## Verdict\n" + conclusion + "\n\n```json\n" + json.dumps(verdicts, indent=1, default=str) + "\n```\n")
    save("e1_policy_replay", {"hypothesis": "H1", "table": tab.to_dict(orient="records"), "frontier": ftab.to_dict(orient="records"), "verdicts": verdicts, "conclusion": conclusion, "fast": args.fast}, readme, tables)
    log(conclusion)


if __name__ == "__main__":
    main()
