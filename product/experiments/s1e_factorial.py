"""S1e: trigger x scheduler factorial with the base-tuned settings from S1d (SIMULATED).

Separates what the probabilistic trigger contributes from what the scheduler contributes:
  trigger effect   = RISK_EDD - THRESHOLD_EDD        (same scheduler)
  scheduler effect = RISK_GREEDY - RISK_EDD          (same trigger), THRESHOLD_CRITICALITY_FIRST / THRESHOLD_MILP - THRESHOLD_EDD
Parameters: threshold 100 h; risk decision horizon 60 h, p_inspect 0.05, p_urgent 0.2 (the S1d base-tuned values).
Seeds 0-7, 120 days, all S1 scenarios. Output: product/evidence/scheduling/factorial.{csv,md}.
THRESHOLD_GREEDY (added after the first factorial run showed the queue ranking, not the trigger, carried the gain):
threshold trigger, queue ranked by P(failure before the decision horizon) x failure cost / crew-hours.
"""
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
PARAMS = {"threshold_h": 100.0, "decision_horizon_h": 60.0, "p_inspect": 0.05, "p_urgent": 0.2}
POLS = ["THRESHOLD_EDD", "THRESHOLD_CRITICALITY_FIRST", "THRESHOLD_MILP", "THRESHOLD_GREEDY", "RISK_EDD", "RISK_GREEDY", "RISK_MILP"]


def _one(args):
    policy, scenario, seed = args
    tr = sim.load_trajectories(OOF)
    cfg = replace(sim.scenario_config(scenario), days=120, **PARAMS)
    m = sim.run(tr, cfg, policy, seed=seed, scenario=scenario).metrics
    return {"policy": policy, "scenario": scenario, "seed": seed, **{k: m[k] for k in ("total_cost", "failures", "failures_A", "unplanned_downtime_h",
                                                                                       "preventive_repairs", "inspections", "late_jobs")}}


def main():
    tasks = [(p, sc, s) for sc in sim.SCENARIOS for p in POLS for s in range(8)]
    with ProcessPoolExecutor() as ex:
        df = pd.DataFrame(list(ex.map(_one, tasks, chunksize=2)))
    df.to_csv(OUT / "factorial.csv", index=False)
    piv = df.pivot_table(index=["scenario", "seed"], columns="policy", values="total_cost")

    def eff(a, b):
        d = piv[a] - piv[b]
        g = d.groupby(level=0)
        return g.mean(), g.min(), g.max(), g.apply(lambda x: int((x < 0).sum()))
    lines = ["# S1e trigger x scheduler factorial (generated; SIMULATED)", "", f"Parameters (S1d base-tuned): {PARAMS}. Seeds 0-7, 120 days.", "",
             "| scenario | " + " | ".join(POLS) + " |", "|---|" + "---|" * len(POLS)]
    m = df.groupby(["scenario", "policy"])["total_cost"].mean().unstack()
    for sc in sim.SCENARIOS:
        lines.append(f"| {sc} | " + " | ".join(f"{m.loc[sc, p]:.1f}" for p in POLS) + " |")
    lines += ["", "Paired effects (mean [min, max] over seeds; n better of 8; negative = cheaper):", ""]
    for name, a, b in (("trigger effect (RISK_EDD - THRESHOLD_EDD)", "RISK_EDD", "THRESHOLD_EDD"),
                       ("risk scheduler given risk trigger (RISK_GREEDY - RISK_EDD)", "RISK_GREEDY", "RISK_EDD"),
                       ("MILP scheduler given risk trigger (RISK_MILP - RISK_EDD)", "RISK_MILP", "RISK_EDD"),
                       ("criticality-first scheduler given threshold (THRESHOLD_CRITICALITY_FIRST - THRESHOLD_EDD)", "THRESHOLD_CRITICALITY_FIRST", "THRESHOLD_EDD"),
                       ("MILP scheduler given threshold (THRESHOLD_MILP - THRESHOLD_EDD)", "THRESHOLD_MILP", "THRESHOLD_EDD"),
                       ("risk-ranked queue given threshold (THRESHOLD_GREEDY - THRESHOLD_EDD)", "THRESHOLD_GREEDY", "THRESHOLD_EDD"),
                       ("THRESHOLD_GREEDY - RISK_GREEDY", "THRESHOLD_GREEDY", "RISK_GREEDY")):
        mean, lo, hi, nb = eff(a, b)
        lines.append(f"- {name}: " + "; ".join(f"{sc} {mean[sc]:+.1f} [{lo[sc]:+.1f}, {hi[sc]:+.1f}] {nb[sc]}/8" for sc in sim.SCENARIOS))
    (OUT / "factorial.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
