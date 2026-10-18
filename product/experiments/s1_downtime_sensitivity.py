"""Re-price the S1 runs with a cost per hour of unplanned downtime (decisions unchanged; SIMULATED).

The S1 total cost counts failures, preventive repairs and inspections but not how long a failed asset stays down.
This script adds d x unplanned_downtime_h for a grid of d and reports which policy is cheapest per scenario, and the
break-even d at which RISK_MILP_STABLE becomes cheaper than RISK_GREEDY (paired over the same seeds).
Input: product/evidence/scheduling/runs.csv. Output: product/evidence/scheduling/downtime_sensitivity.{csv,md}.
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "product" / "evidence" / "scheduling"
GRID = [0.0, 0.0005, 0.001, 0.002, 0.005, 0.01, 0.02]


def main():
    runs = pd.read_csv(OUT / "runs.csv")
    rows = []
    for d in GRID:
        runs["priced"] = runs["total_cost"] + d * runs["unplanned_downtime_h"]
        g = runs.groupby(["scenario", "policy"])["priced"].mean().reset_index()
        for sc, gg in g.groupby("scenario"):
            gg = gg.sort_values("priced")
            rows.append({"downtime_cost_per_h": d, "scenario": sc, "best_policy": gg.iloc[0]["policy"], "best_cost": round(gg.iloc[0]["priced"], 1),
                         "ranking": " > ".join(gg["policy"])})
    sens = pd.DataFrame(rows)
    sens.to_csv(OUT / "downtime_sensitivity.csv", index=False)
    lines = ["# Downtime-price sensitivity (generated; SIMULATED; decisions unchanged, outcomes re-priced)", "",
             "Cheapest policy by mean re-priced cost (total cost + d x unplanned downtime hours). Cost units as in S1 (failure A = 10).", "",
             "| scenario | " + " | ".join(f"d={d}" for d in GRID) + " |", "|---|" + "---|" * len(GRID)]
    for sc in sorted(sens["scenario"].unique()):
        s = sens[sens["scenario"] == sc].set_index("downtime_cost_per_h")
        lines.append(f"| {sc} | " + " | ".join(s.loc[d, "best_policy"] for d in GRID) + " |")
    lines += ["", "Break-even d at which RISK_MILP_STABLE's paired mean cost falls below RISK_GREEDY's:", ""]
    for sc in sorted(runs["scenario"].unique()):
        a = runs[(runs.scenario == sc) & (runs.policy == "RISK_MILP_STABLE")].set_index("seed")
        b = runs[(runs.scenario == sc) & (runs.policy == "RISK_GREEDY")].set_index("seed")
        dc = (a["total_cost"] - b["total_cost"]).mean()          # extra failure/repair cost of MILP
        dd = (b["unplanned_downtime_h"] - a["unplanned_downtime_h"]).mean()   # downtime hours MILP saves
        if dd <= 0:
            msg = "never (MILP_STABLE does not reduce downtime)" if dc > 0 else "always (cheaper and less downtime)"
        elif dc <= 0:
            msg = "always (already cheaper at d = 0)"
        else:
            msg = f"d > {dc / dd:.4f} per hour (MILP_STABLE costs {dc:+.1f} more but saves {dd:.0f} downtime hours on average)"
        lines.append(f"- {sc}: {msg}")
    (OUT / "downtime_sensitivity.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
