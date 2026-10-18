"""S1d: wider tuning grids, and robustness when parameters tuned in the base scenario meet shifted conditions. (SIMULATED)

S1c tuned each family per scenario on seeds 100-107; two grids ended at their edge. S1d widens both grids and asks
the deployment question: a site tunes once on its normal conditions (base), then labour, parts or prediction
quality change. Both "tuned in base" and "tuned in the scenario itself" settings are evaluated on seeds 0-7.
Output: product/evidence/scheduling/robust_tuning.{csv,md}.
"""
import ast
import sys
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from sentinelloop.app import sim  # noqa: E402

OUT = ROOT / "product" / "evidence" / "scheduling"
OOF = [ROOT / "experiments" / "results" / "oof" / "FD001_full.csv", ROOT / "experiments" / "results" / "oof" / "FD003_full.csv"]
SCENARIOS = ["base", "tight_labour", "parts_shortage", "degraded_predictions", "approval_delay", "adverse"]
RISK_GRID = [{"decision_horizon_h": h, "p_inspect": a, "p_urgent": b} for h in (60.0, 100.0, 150.0)
             for a, b in ((0.01, 0.05), (0.03, 0.15), (0.05, 0.2), (0.1, 0.3))]
GRID = {
    "THRESHOLD_EDD": [{"threshold_h": float(h)} for h in (60, 100, 130, 160, 200, 250, 300)],
    "FIXED_INTERVAL": [{"interval_age_cycles": a} for a in (80, 90, 100, 115, 130)],
    "RISK_GREEDY": RISK_GRID,
    "RISK_GREEDY_STABLE": RISK_GRID,
}
TUNE_SEEDS, EVAL_SEEDS = range(100, 108), range(8)


def _one(args):
    policy, scenario, params, seed = args
    tr = sim.load_trajectories(OOF)
    cfg = replace(sim.scenario_config(scenario), days=120, **params)
    m = sim.run(tr, cfg, policy, seed=seed, scenario=scenario).metrics
    return {"policy": policy, "scenario": scenario, "params": repr(params), "seed": seed, "total_cost": m["total_cost"], "failures": m["failures"],
            "failures_A": m["failures_A"], "unplanned_downtime_h": m["unplanned_downtime_h"], "preventive_repairs": m["preventive_repairs"],
            "early_repairs": m["early_repairs"]}


def main():
    tune = [(p, sc, prm, s) for sc in SCENARIOS for p, grid in GRID.items() for prm in grid for s in TUNE_SEEDS]
    with ProcessPoolExecutor() as ex:
        t = pd.DataFrame(list(ex.map(_one, tune, chunksize=4)))
    t.to_csv(OUT / "robust_tuning_tuning.csv", index=False)
    means = t.groupby(["scenario", "policy", "params"])["total_cost"].mean().reset_index()
    best = means.sort_values("total_cost").groupby(["scenario", "policy"]).head(1).set_index(["scenario", "policy"])["params"].to_dict()
    ev = []
    for sc in SCENARIOS:
        for pol in GRID:
            for mode, src in (("tuned_in_base", "base"), ("tuned_in_scenario", sc)):
                if mode == "tuned_in_scenario" and sc == "base":
                    continue
                ev += [(pol, sc, ast.literal_eval(best[(src, pol)]), s, mode) for s in EVAL_SEEDS]
    with ProcessPoolExecutor() as ex:
        rows = list(ex.map(_one, [x[:4] for x in ev], chunksize=4))
    e = pd.DataFrame(rows)
    e["mode"] = [x[4] for x in ev]
    e.to_csv(OUT / "robust_tuning.csv", index=False)
    edge = []
    for (sc, pol), prm in best.items():
        grid = [repr(g) for g in GRID[pol]]
        if pol.startswith("THRESHOLD") or pol.startswith("FIXED"):
            if prm in (grid[0], grid[-1]):
                edge.append(f"{sc}/{pol} -> {prm}")
    lines = ["# S1d robust tuning (generated; SIMULATED)", "",
             "Grids: threshold_h 60-300 h; interval 80-130 cycles; risk decision horizon {60,100,150} h x (p_inspect, p_urgent) "
             "{(0.01,0.05),(0.03,0.15),(0.05,0.2),(0.1,0.3)}. Tuned on seeds 100-107 by mean total cost; evaluated on seeds 0-7.", "",
             "Settings at a grid edge (the optimum may lie outside the grid): " + ("; ".join(edge) if edge else "none"), ""]
    for mode in ("tuned_in_base", "tuned_in_scenario"):
        lines += [f"## {mode}", "", "| scenario | " + " | ".join(GRID) + " | best |", "|---|" + "---|" * (len(GRID) + 1)]
        for sc in SCENARIOS:
            g = e[(e.scenario == sc) & (e["mode"] == (mode if not (sc == "base") else "tuned_in_base"))]
            if g.empty:
                continue
            m = g.groupby("policy")["total_cost"].agg(["mean", "std"])
            cells = [f"{m.loc[p, 'mean']:.1f} ± {m.loc[p, 'std']:.1f}" for p in GRID]
            lines.append(f"| {sc} | " + " | ".join(cells) + f" | {m['mean'].idxmin()} |")
        lines.append("")
        lines += ["Paired RISK_GREEDY minus THRESHOLD_EDD (eval seeds): mean [min, max], risk better / worse", ""]
        for sc in SCENARIOS:
            md = "tuned_in_base" if sc == "base" else mode
            a = e[(e.scenario == sc) & (e["mode"] == md) & (e.policy == "RISK_GREEDY")].set_index("seed")["total_cost"]
            b = e[(e.scenario == sc) & (e["mode"] == md) & (e.policy == "THRESHOLD_EDD")].set_index("seed")["total_cost"]
            d = a - b
            lines.append(f"- {sc}: {d.mean():+.1f} [{d.min():+.1f}, {d.max():+.1f}], {int((d < 0).sum())}/8 better, {int((d > 0).sum())}/8 worse")
        lines.append("")
    lines += ["## Tuned settings", ""] + [f"- {sc} / {pol}: {prm}" for (sc, pol), prm in sorted(best.items())]
    (OUT / "robust_tuning.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
