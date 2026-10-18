"""E2 — Abstention / escalation (hypothesis H2).

Full agent (escalation on wide interval, bad quality, drift, conflicting evidence) vs the same agent
with escalation disabled, on the E1 eval engines. Error = late (true RUL at first serious order < min
lead, or never) or too early (> 60 cycles of life discarded).
"""
from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd

from common import ROOT, SUBSETS, log, markdown_table, oof_table, save, severities_for_engine, thresholds, tune_eval_split
from sentinelloop import agent, config

MIN_LEAD = 5
EARLY_LIMIT = 60.0


def first_serious(decisions, require_not_escalated: bool):
    for i, d in enumerate(decisions):
        if d.severity in ("HIGH", "CRITICAL") and (not require_not_escalated or not d.escalate_to_human):
            return i, d
    return None, None


def run_subset(subset: str, fast: bool) -> tuple[dict, pd.DataFrame]:
    cfg = config.load(subset, ROOT / "configs")
    thr = thresholds(cfg)
    oof_df, _ = oof_table(subset, fast=fast)
    _, eval_units = tune_eval_split(oof_df["unit"].unique(), seed=int(cfg["seed"]))
    ev = oof_df[oof_df.unit.isin(eval_units)]
    rows = []
    reason_counts: dict[str, int] = {}
    for u, g in ev.groupby("unit"):
        g = g.sort_values("cycle")
        failure = int(g["failure_cycle"].iloc[0])
        decs = severities_for_engine(g, thr)
        # without abstention: every HIGH/CRITICAL decision counts as an order, escalated or not
        i_all, d_all = first_serious(decs, require_not_escalated=False)
        # with abstention: escalated decisions go to a human; the first NON-escalated serious decision is the order
        i_act, d_act = first_serious(decs, require_not_escalated=True)
        escalated_first = bool(d_all is not None and d_all.escalate_to_human)
        if d_all is not None:
            for r in d_all.escalation_reasons:
                reason_counts[r] = reason_counts.get(r, 0) + 1

        def outcome(i):
            if i is None:
                return {"ordered": False, "true_rul": np.nan, "late": True, "early": False, "error": True}
            tr = failure - int(g["cycle"].iloc[i])
            late = tr < MIN_LEAD
            early = tr > EARLY_LIMIT
            return {"ordered": True, "true_rul": float(tr), "late": late, "early": early, "error": bool(late or early)}

        o_all, o_act = outcome(i_all), outcome(i_act)
        rows.append({"subset": subset, "unit": u, "failure_cycle": failure, "first_serious_escalated": escalated_first,
                     "noabst_true_rul": o_all["true_rul"], "noabst_error": o_all["error"], "noabst_late": o_all["late"], "noabst_early": o_all["early"],
                     "abst_acted": not escalated_first, "abst_true_rul": o_act["true_rul"], "abst_error": o_act["error"], "abst_late": o_act["late"], "abst_early": o_act["early"]})
    pe = pd.DataFrame(rows)
    acted = pe[~pe.first_serious_escalated]
    err_all = float(pe["noabst_error"].mean())
    err_acted = float(acted["noabst_error"].mean()) if len(acted) else float("nan")  # the same decisions, restricted to non-escalated engines
    err_escalated = float(pe.loc[pe.first_serious_escalated, "noabst_error"].mean()) if pe.first_serious_escalated.any() else float("nan")
    escalation_share = float(pe["first_serious_escalated"].mean())
    rel = (err_all - err_acted) / err_all if err_all > 0 else float("nan")
    verdict = {"n_eval": int(len(pe)), "error_rate_all_decisions": err_all, "error_rate_acted_upon": err_acted, "error_rate_among_escalated": err_escalated,
               "relative_reduction": rel, "escalation_share": escalation_share, "reasons": reason_counts,
               "H2_supported_subset": bool(rel >= 0.20 and escalation_share <= 0.25)}
    return verdict, pe


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--subsets", nargs="*", default=SUBSETS); ap.add_argument("--fast", action="store_true")
    args = ap.parse_args()
    verdicts, tables, rows = {}, {}, []
    for s in args.subsets:
        log(f"=== E2 {s} ===")
        v, pe = run_subset(s, args.fast)
        verdicts[s] = v
        tables[f"e2_{s}_per_engine.csv"] = pe
        rows.append({"subset": s, **{k: v[k] for k in ["n_eval", "error_rate_all_decisions", "error_rate_acted_upon", "error_rate_among_escalated", "relative_reduction", "escalation_share", "H2_supported_subset"]}})
    tab = pd.DataFrame(rows)
    n_ok = int(tab["H2_supported_subset"].sum()); n = len(tab)
    conclusion = f"H2: error rate among acted-upon engines is >=20% lower than among all engines with escalation share <=25% on {n_ok}/{n} subsets. Pre-registered criterion (>=3/4): {'SUPPORTED' if n_ok >= min(3, n) else 'NOT SUPPORTED'}."
    readme = ("# E2 — Abstention / escalation (H2)\n\nSame OOF replay and eval engines as E1. 'Error' = first serious (HIGH/CRITICAL) order is late (< 5 cycles of true life) or never, or too early (> 60 cycles discarded). "
              "'Acted-upon' engines are those whose first serious decision was NOT escalated to a human.\n\n" + markdown_table(tab) + "\n\n## Verdict\n" + conclusion + "\n\n```json\n" + json.dumps(verdicts, indent=1, default=str) + "\n```\n")
    save("e2_abstention", {"hypothesis": "H2", "table": tab.to_dict(orient="records"), "verdicts": verdicts, "conclusion": conclusion, "fast": args.fast}, readme, tables)
    log(conclusion)


if __name__ == "__main__":
    main()
