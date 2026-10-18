"""S1c: are the risk policies still better when every baseline is tuned? (SIMULATED)

S1 used one hand-set parameter per policy family (threshold 60 h, interval 140 cycles, p_inspect/p_urgent 0.10/0.30).
Here each family's parameter is tuned on SEPARATE seeds (100-107) per scenario by mean total cost, then the tuned
setting is evaluated on the S1 seeds (0-7) and compared paired against the tuned threshold baseline.
MILP policies are not tuned (runtime); RUN_TO_FAILURE has no parameter.
Output: product/evidence/scheduling/tuned_baselines.{csv,md}.
"""
import ast
import sys
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from sentinelloop.app import sim  # noqa: E402

OUT = ROOT / "product" / "evidence" / "scheduling"
OOF = [ROOT / "experiments" / "results" / "oof" / "FD001_full.csv", ROOT / "experiments" / "results" / "oof" / "FD003_full.csv"]
SCENARIOS = ["base", "tight_labour", "parts_shortage", "degraded_predictions", "adverse"]
GRID = {
    "THRESHOLD_EDD": [{"threshold_h": h} for h in (30, 45, 60, 80, 100, 130, 160)],
    "FIXED_INTERVAL": [{"interval_age_cycles": a} for a in (100, 115, 130, 140, 150, 165, 180)],
    "RISK_GREEDY": [{"p_inspect": a, "p_urgent": b} for a, b in ((0.03, 0.15), (0.05, 0.2), (0.1, 0.3), (0.15, 0.4), (0.2, 0.5))],
    "RISK_CRITICALITY_FIRST": [{"p_inspect": a, "p_urgent": b} for a, b in ((0.03, 0.15), (0.05, 0.2), (0.1, 0.3), (0.15, 0.4), (0.2, 0.5))],
}
TUNE_SEEDS, EVAL_SEEDS = range(100, 108), range(8)


def _one(args):
    policy, scenario, params, seed = args
    tr = sim.load_trajectories(OOF)
    cfg = replace(sim.scenario_config(scenario), days=120, **params)
    m = sim.run(tr, cfg, policy, seed=seed, scenario=scenario).metrics
    return {"policy": policy, "scenario": scenario, "params": repr(params), "seed": seed, "total_cost": m["total_cost"], "failures": m["failures"],
            "failures_A": m["failures_A"], "unplanned_downtime_h": m["unplanned_downtime_h"]}


def main():
    tune = [(p, sc, prm, s) for sc in SCENARIOS for p, grid in GRID.items() for prm in grid for s in TUNE_SEEDS]
    with ProcessPoolExecutor() as ex:
        t = pd.DataFrame(list(ex.map(_one, tune, chunksize=4)))
    t.to_csv(OUT / "tuned_baselines_tuning.csv", index=False)
    best = t.groupby(["scenario", "policy", "params"])["total_cost"].mean().reset_index().sort_values("total_cost").groupby(["scenario", "policy"]).head(1)
    ev = [(r.policy, r.scenario, ast.literal_eval(r.params), s) for r in best.itertuples() for s in EVAL_SEEDS]
    ev += [("RUN_TO_FAILURE", sc, {}, s) for sc in SCENARIOS for s in EVAL_SEEDS]
    with ProcessPoolExecutor() as ex:
        e = pd.DataFrame(list(ex.map(_one, ev, chunksize=4)))
    e.to_csv(OUT / "tuned_baselines.csv", index=False)
    lines = ["# S1c tuned baselines (generated; SIMULATED)", "",
             "Each family's parameter tuned on seeds 100-107 per scenario (mean total cost), evaluated on seeds 0-7 (the S1 seeds).", ""]
    for sc in SCENARIOS:
        lines += [f"## {sc}", "", "| policy | tuned setting | total cost (eval) | failures | A failures | unplanned downtime h |", "|---|---|---|---|---|---|"]
        g = e[e.scenario == sc]
        for pol, gg in sorted(g.groupby("policy"), key=lambda z: z[1]["total_cost"].mean()):
            lines.append(f"| {pol} | {gg['params'].iloc[0]} | {gg.total_cost.mean():.1f} ± {gg.total_cost.std():.1f} | {gg.failures.mean():.1f} | "
                         f"{gg.failures_A.mean():.1f} | {gg.unplanned_downtime_h.mean():.0f} |")
        base = g[g.policy == "THRESHOLD_EDD"].set_index("seed")["total_cost"]
        lines += ["", "Paired against the tuned THRESHOLD_EDD (eval seeds): mean [min, max], seeds better/worse", ""]
        for pol, gg in g.groupby("policy"):
            if pol == "THRESHOLD_EDD":
                continue
            d = gg.set_index("seed")["total_cost"] - base
            lines.append(f"- {pol}: {d.mean():+.1f} [{d.min():+.1f}, {d.max():+.1f}], better {int((d < 0).sum())}/8, worse {int((d > 0).sum())}/8")
        lines.append("")
    (OUT / "tuned_baselines.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
