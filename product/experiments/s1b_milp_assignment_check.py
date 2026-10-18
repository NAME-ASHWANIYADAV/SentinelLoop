"""S1b: how often does the MILP's exact technician-assignment pass drop a job the aggregated model placed? (SIMULATED)

S1 did not record this. Same simulator and scenarios as S1, MILP policies only, seeds 0-3, 120 days.
Output: product/evidence/scheduling/milp_assignment_check.csv and .md.
"""
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from sentinelloop.app import sim  # noqa: E402

OUT = ROOT / "product" / "evidence" / "scheduling"
OOF = [ROOT / "experiments" / "results" / "oof" / "FD001_full.csv", ROOT / "experiments" / "results" / "oof" / "FD003_full.csv"]


def _one(args):
    policy, scenario, seed = args
    tr = sim.load_trajectories(OOF)
    cfg = replace(sim.scenario_config(scenario), days=120)
    t = time.time()
    m = sim.run(tr, cfg, policy, seed=seed, scenario=scenario).metrics
    return {"policy": policy, "scenario": scenario, "seed": seed, "plans": m["plans"], "milp_non_optimal_plans": m["milp_non_optimal_plans"],
            "milp_dropped_in_assignment": m["milp_dropped_in_assignment"], "unscheduled_job_days": m["unscheduled_job_days"],
            "total_cost": m["total_cost"], "runtime_s": round(time.time() - t, 1)}


def main():
    tasks = [(p, sc, s) for p in ("RISK_MILP", "RISK_MILP_STABLE") for sc in sim.SCENARIOS for s in range(4)]
    if "--from-csv" in sys.argv:
        df = pd.read_csv(OUT / "milp_assignment_check.csv")
    else:
        with ProcessPoolExecutor() as ex:
            rows = list(ex.map(_one, tasks))
        df = pd.DataFrame(rows)
        df.to_csv(OUT / "milp_assignment_check.csv", index=False)
    g = df.groupby(["policy", "scenario"])[["plans", "milp_non_optimal_plans", "milp_dropped_in_assignment", "unscheduled_job_days"]].sum()
    text = ["# S1b MILP assignment check (generated; SIMULATED; seeds 0-3, 120 days)", "",
            "Sums over seeds. `plans` = rolling-horizon planning calls; `milp_dropped_in_assignment` = jobs the aggregated MILP "
            "placed that no specific technician crew could take; `unscheduled_job_days` = job x planning-call pairs left unscheduled for any reason.", "",
            "| policy | scenario | plans | non-optimal | dropped in assignment | unscheduled job-days |", "|---|---|---|---|---|---|"]
    text += [f"| {pol} | {sc} | {r.plans} | {r.milp_non_optimal_plans} | {r.milp_dropped_in_assignment} | {r.unscheduled_job_days} |"
             for (pol, sc), r in g.iterrows()]
    (OUT / "milp_assignment_check.md").write_text("\n".join(text) + "\n", encoding="utf-8")
    print("\n".join(text))


if __name__ == "__main__":
    main()
