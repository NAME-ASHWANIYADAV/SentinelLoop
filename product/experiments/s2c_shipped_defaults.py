"""S2 part C: the platform's shipped RUL trigger settings on the S2 evaluation engines (SIMULATED).

The platform ships the probabilistic trigger at the S1 hand-set values (configs/platform.yaml, C-MAPSS type: decision
horizon 60 h, p_inspect 0.10, p_urgent 0.30; review finding data_scientist-3). S2 part B evaluated only tuned settings.
This runs RISK_GREEDY at the shipped values, and THRESHOLD_EDD at the simulator's default threshold (60 h), on the same
FD003 engines and seeds 0-7 as S2 part B, so the shipped defaults can be compared with the FD001-tuned settings.
Output: product/evidence/scheduling_v2/partC_shipped.{csv,md}.
"""
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import s2_corrected as s2  # noqa: E402

SHIPPED = {"decision_horizon_h": 60.0, "p_inspect": 0.10, "p_urgent": 0.30}


def main():
    tasks = [("C:shipped", "RISK_GREEDY", sc, SHIPPED, s, s2.EVAL_OOF) for sc in s2.SCENARIOS for s in range(8)]
    tasks += [("C:sim_default", "THRESHOLD_EDD", sc, {"threshold_h": 60.0}, s, s2.EVAL_OOF) for sc in s2.SCENARIOS for s in range(8)]
    with ProcessPoolExecutor(max_workers=4) as ex:
        C = pd.DataFrame(list(ex.map(s2._one, tasks, chunksize=2)))
    C.to_csv(s2.OUT / "partC_shipped.csv", index=False)
    E = pd.read_csv(s2.OUT / "partB_eval.csv")
    lines = ["# S2 part C: shipped RUL trigger settings on the S2 evaluation engines (generated; SIMULATED)", "",
             f"RISK_GREEDY at the shipped values {SHIPPED} vs RISK_GREEDY tuned on FD001 (S2 part B, tuned in base, downtime unpriced). "
             "FD003 engines, seeds 0-7, 120 days, 30 assets. Total cost, mean over seeds; paired difference shipped - tuned [min, max].", "",
             "| scenario | shipped | tuned in base | shipped - tuned | shipped worse on | THRESHOLD_EDD at 60 h (untuned) | THRESHOLD_EDD tuned in base |",
             "|---|---|---|---|---|---|---|"]
    for sc in s2.SCENARIOS:
        a = C[(C.part == "C:shipped") & (C.scenario == sc)].set_index("seed")["total_cost"]
        b = E[(E.part == "E:total_cost:in_base") & (E.scenario == sc) & (E.policy == "RISK_GREEDY")].set_index("seed")["total_cost"]
        t0 = C[(C.part == "C:sim_default") & (C.scenario == sc)]["total_cost"].mean()
        t1 = E[(E.part == "E:total_cost:in_base") & (E.scenario == sc) & (E.policy == "THRESHOLD_EDD")]["total_cost"].mean()
        d = a - b
        lines.append(f"| {sc} | {a.mean():.1f} | {b.mean():.1f} | {d.mean():+.1f} [{d.min():+.1f}, {d.max():+.1f}] | {int((d > 0).sum())}/8 | {t0:.1f} | {t1:.1f} |")
    (s2.OUT / "partC_shipped.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
