"""S1 - Maintenance policy comparison in the fleet simulator (SIMULATED evidence).

    .venv/Scripts/python.exe product/experiments/s1_scheduling.py [--seeds 8] [--days 120] [--workers 6] [--quick]

Every (policy, scenario, seed) run gets the same fleet, trajectory sequence, starting ages and resources for that
seed and scenario. Outputs (product/evidence/scheduling/): runs.csv (one row per run), summary.json and summary.md
(means, standard deviations and paired differences against the fixed-threshold baseline), sensitivity.csv (policy
ranking when the true costs differ from the costs the policies assumed), run.log.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, replace
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from sentinelloop.app import sim  # noqa: E402

OUT = ROOT / "product" / "evidence" / "scheduling"
OOF = [ROOT / "experiments" / "results" / "oof" / "FD001_full.csv", ROOT / "experiments" / "results" / "oof" / "FD003_full.csv"]
METRICS = ["total_cost", "failures", "failures_A", "unplanned_downtime_h", "preventive_repairs", "early_repairs", "inspections", "inspections_no_fault",
           "late_jobs", "parts_blocked", "schedule_violations", "mean_discarded_life_h", "utilisation", "plan_change_rate", "approvals_per_day",
           "milp_non_optimal_plans", "failure_cost"]
BASELINE = "THRESHOLD_EDD"


def _one(args):
    policy, scenario, seed, days = args
    tr = sim.load_trajectories(OOF)
    cfg = replace(sim.scenario_config(scenario), days=days)
    t = time.time()
    r = sim.run(tr, cfg, policy, seed=seed, scenario=scenario)
    row = {"policy": policy, "scenario": scenario, "seed": seed, "runtime_s": round(time.time() - t, 2)}
    row.update({k: r.metrics.get(k) for k in METRICS})
    row.update({k: r.metrics.get(k) for k in ("preventive_repairs", "inspections", "failures_B", "failures_C", "corrective_repairs")})
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=8)
    ap.add_argument("--days", type=int, default=120)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--quick", action="store_true", help="2 seeds, 30 days (smoke check)")
    a = ap.parse_args()
    seeds, days = (2, 30) if a.quick else (a.seeds, a.days)
    OUT.mkdir(parents=True, exist_ok=True)
    log = open(OUT / "run.log", "w", encoding="utf-8")
    jobs = [(p, s, seed, days) for s in sim.SCENARIOS for p in sim.POLICIES for seed in range(seeds)]
    print(f"S1: {len(jobs)} runs ({len(sim.POLICIES)} policies x {len(sim.SCENARIOS)} scenarios x {seeds} seeds, {days} days)", file=log, flush=True)
    t0, rows = time.time(), []
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(_one, j): j for j in jobs}
        for f in as_completed(futs):
            row = f.result()
            rows.append(row)
            print(f"{len(rows)}/{len(jobs)} {row['scenario']} {row['policy']} seed {row['seed']}: cost {row['total_cost']:.1f} failures {row['failures']} "
                  f"violations {row['schedule_violations']} ({row['runtime_s']} s)", file=log, flush=True)
    df = pd.DataFrame(rows).sort_values(["scenario", "policy", "seed"]).reset_index(drop=True)
    df.to_csv(OUT / "runs.csv", index=False)

    summary = {"config": asdict(sim.SimConfig()), "scenarios": {k: {kk: (list(v) if isinstance(v, tuple) else v) for kk, v in d.items()} for k, d in sim.SCENARIOS.items()},
               "policies": {k: list(v) for k, v in sim.POLICIES.items()}, "seeds": seeds, "days": days, "trajectories": [str(p.relative_to(ROOT)) for p in OOF],
               "runtime_min": round((time.time() - t0) / 60, 1), "results": {}, "paired_vs_baseline": {}}
    for (sc, pol), g in df.groupby(["scenario", "policy"]):
        summary["results"].setdefault(sc, {})[pol] = {m: {"mean": float(g[m].mean()), "sd": float(g[m].std(ddof=1)) if len(g) > 1 else 0.0}
                                                      for m in METRICS if g[m].notna().any()}
    for sc, g in df.groupby("scenario"):
        base = g[g.policy == BASELINE].set_index("seed")
        for pol, gp in g.groupby("policy"):
            gp = gp.set_index("seed")
            d = {}
            for m in ("total_cost", "failures", "unplanned_downtime_h", "late_jobs", "plan_change_rate"):
                diff = (gp[m] - base[m]).dropna()
                d[m] = {"mean_diff": float(diff.mean()), "min_diff": float(diff.min()), "max_diff": float(diff.max()),
                        "seeds_better": int((diff < 0).sum()), "seeds_worse": int((diff > 0).sum()), "n": int(len(diff))}
            summary["paired_vs_baseline"].setdefault(sc, {})[pol] = d
    # cost sensitivity: true costs differ from the costs the policies assumed (decisions unchanged)
    sens = []
    for fm in (0.25, 0.5, 1.0, 2.0, 4.0):
        for ic in (0.05, 0.1, 0.3):
            for rc in (0.5, 1.0, 2.0):
                cost = fm * df["failure_cost"] + rc * df["preventive_repairs"] + ic * df["inspections"]
                tmp = df.assign(cost=cost).groupby(["scenario", "policy"])["cost"].mean().reset_index()
                for sc, g in tmp.groupby("scenario"):
                    best = g.sort_values("cost").iloc[0]
                    sens.append({"failure_cost_x": fm, "inspection_cost": ic, "repair_cost": rc, "scenario": sc, "best_policy": best["policy"],
                                 "best_cost": float(best["cost"]), "ranking": " > ".join(g.sort_values("cost")["policy"])})
    pd.DataFrame(sens).to_csv(OUT / "sensitivity.csv", index=False)
    summary["sensitivity_best_policy_counts"] = pd.DataFrame(sens).groupby(["scenario", "best_policy"]).size().unstack(fill_value=0).to_dict(orient="index")
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")

    lines = ["# S1 policy comparison (generated; SIMULATED)", "", f"{len(jobs)} runs, {seeds} seeds, {days} days, runtime {summary['runtime_min']} min.", ""]
    for sc in sim.SCENARIOS:
        lines += [f"## {sc}", "", "| policy | total cost | failures | A failures | unplanned downtime h | preventive repairs | early repairs | inspections (no fault) | late jobs | violations | plan change rate | approvals/day |",
                  "|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for pol in sim.POLICIES:
            r = summary["results"][sc][pol]
            f = lambda m, d=1: f"{r[m]['mean']:.{d}f} ± {r[m]['sd']:.{d}f}" if m in r else "n/a"
            lines.append(f"| {pol} | {f('total_cost')} | {f('failures')} | {f('failures_A')} | {f('unplanned_downtime_h', 0)} | {f('preventive_repairs')} | "
                         f"{f('early_repairs')} | {f('inspections')} ({f('inspections_no_fault')}) | {f('late_jobs')} | {f('schedule_violations', 0)} | "
                         f"{f('plan_change_rate', 2)} | {f('approvals_per_day', 2)} |")
        lines += ["", f"Paired against {BASELINE} (same seeds): total cost difference mean [min, max], seeds better / worse", ""]
        for pol in sim.POLICIES:
            d = summary["paired_vs_baseline"][sc][pol]["total_cost"]
            lines.append(f"- {pol}: {d['mean_diff']:+.1f} [{d['min_diff']:+.1f}, {d['max_diff']:+.1f}], better on {d['seeds_better']}/{d['n']}, worse on {d['seeds_worse']}/{d['n']}")
        lines.append("")
    lines += ["## Cost sensitivity (best policy per scenario across 45 cost settings)", "", "```", json.dumps(summary["sensitivity_best_policy_counts"], indent=1), "```"]
    (OUT / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"done in {summary['runtime_min']} min", file=log, flush=True)
    log.close()


if __name__ == "__main__":
    main()
