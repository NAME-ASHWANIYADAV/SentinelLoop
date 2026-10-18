"""S2: the scheduling evaluation corrected after the Phase 9 adversarial review (SIMULATED).

Corrections over S1-S1e:
- data_scientist-1: downtime of assets still failed at the end of a run is counted (unplanned_downtime_total_h), and
  fleet availability and the number of assets failed at the end are reported.
- data_scientist-2: a scenario where more than 30% of the fleet ends failed is reported as COLLAPSE, not ranked; a
  sustainable parts scenario (parts_tight: 6 kits, 96 h lead time) is added.
- data_scientist-9: tuning and evaluation use DISJOINT engines: tune on FD001 trajectories (seeds 100-107), evaluate on
  FD003 trajectories (seeds 0-7). Two tuning objectives: total cost as before (downtime unpriced) and total cost +
  0.005 x total unplanned downtime hours (downtime priced; one A failure = 10 units = 2,000 downtime hours).
Part A re-runs the S1 grid (hand-set parameters, FD001+FD003 as before) with the corrected metrics.
Output: product/evidence/scheduling_v2/{partA_runs.csv, partB_tuning.csv, partB_eval.csv, summary.md, summary.json, run.log}.
"""
import ast
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from sentinelloop.app import sim  # noqa: E402

OUT = ROOT / "product" / "evidence" / "scheduling_v2"
OOF_DIR = ROOT / "experiments" / "results" / "oof"
BOTH = [OOF_DIR / "FD001_full.csv", OOF_DIR / "FD003_full.csv"]
TUNE_OOF, EVAL_OOF = [OOF_DIR / "FD001_full.csv"], [OOF_DIR / "FD003_full.csv"]
SCEN = dict(sim.SCENARIOS)
SCEN["parts_tight"] = {"kit_stock": 6, "kit_lead_h": 96.0}
SCENARIOS = ["base", "tight_labour", "parts_tight", "parts_shortage", "degraded_predictions", "approval_delay", "adverse"]
POL_A = list(sim.POLICIES) + ["RISK_EDD"]
D_PRICE = 0.005
WORKERS = 5                    # a full pool ran out of memory on the 15 GB test laptop
RISK_GRID = [{"decision_horizon_h": h, "p_inspect": a, "p_urgent": b} for h in (60.0, 100.0, 150.0)
             for a, b in ((0.01, 0.05), (0.03, 0.15), (0.05, 0.2), (0.1, 0.3))]
GRID = {"THRESHOLD_EDD": [{"threshold_h": float(h)} for h in (60, 100, 130, 160, 200, 250, 300, 400)],
        "FIXED_INTERVAL": [{"interval_age_cycles": a} for a in (70, 80, 90, 100, 115, 130)],
        "RISK_GREEDY": RISK_GRID, "RISK_EDD": RISK_GRID}
KEYS = ["total_cost", "failures", "failures_A", "unplanned_downtime_h", "unplanned_downtime_total_h", "availability", "assets_failed_at_end",
        "preventive_repairs", "inspections", "late_jobs", "schedule_violations", "plan_change_rate"]
_TRAJ = {}


def _cfg(scenario, params):
    base = sim.SimConfig()
    for k, v in SCEN[scenario].items():
        base = replace(base, **{k: v})
    return replace(base, days=120, **params)


def _one(args):
    tag, policy, scenario, params, seed, oof = args
    key = tuple(str(p) for p in oof)
    if key not in _TRAJ:
        _TRAJ[key] = sim.load_trajectories(oof)
    t = time.time()
    m = sim.run(_TRAJ[key], _cfg(scenario, params), policy, seed=seed, scenario=scenario).metrics
    return {"part": tag, "policy": policy, "scenario": scenario, "params": repr(params), "seed": seed, "runtime_s": round(time.time() - t, 2),
            **{k: m.get(k) for k in KEYS}}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    log = open(OUT / "run.log", "a", encoding="utf-8")
    t0 = time.time()
    if "--resume" in sys.argv and (OUT / "partA_runs.csv").exists() and (OUT / "partB_tuning.csv").exists():
        A, T = pd.read_csv(OUT / "partA_runs.csv"), pd.read_csv(OUT / "partB_tuning.csv")      # stage 1 already done (deterministic)
        print(f"resumed parts A + B-tune from saved runs ({len(A) + len(T)})", file=log, flush=True)
    else:
        a_tasks = [("A", p, sc, {}, s, BOTH) for sc in SCENARIOS for p in POL_A for s in range(8)]
        b_tasks = [("Btune", p, sc, prm, s, TUNE_OOF) for sc in SCENARIOS for p, g in GRID.items() for prm in g for s in range(100, 108)]
        with ProcessPoolExecutor(max_workers=WORKERS) as ex:
            rows = list(ex.map(_one, a_tasks + b_tasks, chunksize=4))
        print(f"parts A + B-tune done: {len(rows)} runs in {(time.time() - t0) / 60:.1f} min", file=log, flush=True)
        df = pd.DataFrame(rows)
        A = df[df.part == "A"].copy()
        T = df[df.part == "Btune"].copy()
        A.to_csv(OUT / "partA_runs.csv", index=False)
        T.to_csv(OUT / "partB_tuning.csv", index=False)
    T["priced"] = T["total_cost"] + D_PRICE * T["unplanned_downtime_total_h"]
    best = {}
    for obj in ("total_cost", "priced"):
        g = T.groupby(["scenario", "policy", "params"])[obj].mean().reset_index().sort_values(obj).groupby(["scenario", "policy"]).head(1)
        for r in g.itertuples():
            best[(obj, r.scenario, r.policy)] = ast.literal_eval(r.params)       # repr() of our own parameter dicts
    risk_base = {o: best[(o, "base", "RISK_GREEDY")] for o in ("total_cost", "priced")}
    e_tasks = []
    for obj in ("total_cost", "priced"):
        for sc in SCENARIOS:
            for pol in GRID:
                e_tasks += [(f"E:{obj}:in_scenario", pol, sc, best[(obj, sc, pol)], s, EVAL_OOF) for s in range(8)]
                e_tasks += [(f"E:{obj}:in_base", pol, sc, best[(obj, "base", pol)], s, EVAL_OOF) for s in range(8)]
            e_tasks += [(f"E:{obj}:in_base", "RISK_MILP", sc, risk_base[obj], s, EVAL_OOF) for s in range(8)]
    e_tasks += [("E:none", "RUN_TO_FAILURE", sc, {}, s, EVAL_OOF) for sc in SCENARIOS for s in range(8)]
    with ProcessPoolExecutor(max_workers=WORKERS) as ex:
        E = pd.DataFrame(list(ex.map(_one, e_tasks, chunksize=2)))
    E.to_csv(OUT / "partB_eval.csv", index=False)
    print(f"part B eval done: {len(E)} runs; total {(time.time() - t0) / 60:.1f} min", file=log, flush=True)
    write_summary(A, E, best)


def _fmt(x, d=1):
    return "n/a" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.{d}f}"


def write_summary(A, E, best):
    out, lines = {}, ["# S2 corrected scheduling evaluation (generated; SIMULATED)", "",
                      "Corrections: terminal downtime counted; collapse flagged; tuning on FD001 engines, evaluation on FD003 engines; "
                      f"two tuning objectives (total cost; total cost + {D_PRICE} x total unplanned downtime h). 120 days, 30 assets, 8 seeds.", ""]
    lines += ["## Part A: S1 grid with corrected metrics (hand-set parameters, FD001+FD003)", "",
              "| scenario | policy | total cost | failures | assets failed at end | unplanned downtime total h (counted only) | availability |",
              "|---|---|---|---|---|---|---|"]
    collapse = {}
    for sc in SCENARIOS:
        g = A[A.scenario == sc]
        frac = g["assets_failed_at_end"].mean() / 30.0
        collapse[sc] = bool(frac > 0.3)
        for pol, gg in g.groupby("policy"):
            lines.append(f"| {sc}{' (COLLAPSE)' if collapse[sc] else ''} | {pol} | {_fmt(gg.total_cost.mean())} | {_fmt(gg.failures.mean())} | "
                         f"{_fmt(gg.assets_failed_at_end.mean())} | {_fmt(gg.unplanned_downtime_total_h.mean(), 0)} ({_fmt(gg.unplanned_downtime_h.mean(), 0)}) | "
                         f"{_fmt(gg.availability.mean(), 3)} |")
    out["collapse"] = collapse
    lines += ["", "MILP vs RISK_GREEDY, total unplanned downtime (corrected), paired over seeds: mean difference [min, max]", ""]
    for sc in SCENARIOS:
        a = A[(A.scenario == sc) & (A.policy == "RISK_MILP")].set_index("seed")["unplanned_downtime_total_h"]
        b = A[(A.scenario == sc) & (A.policy == "RISK_GREEDY")].set_index("seed")["unplanned_downtime_total_h"]
        d = a - b
        lines.append(f"- {sc}: {d.mean():+.0f} h [{d.min():+.0f}, {d.max():+.0f}], MILP lower on {int((d < 0).sum())}/8")
    for obj in ("total_cost", "priced"):
        lines += ["", f"## Part B ({'downtime unpriced' if obj == 'total_cost' else f'downtime priced at {D_PRICE}/h'}): tuned on FD001, evaluated on FD003", ""]
        metric = "total_cost" if obj == "total_cost" else None
        for mode in ("in_base", "in_scenario"):
            tag = f"E:{obj}:{mode}"
            lines += [f"### tuned {mode.replace('_', ' ')}", "", "| scenario | " + " | ".join(list(GRID) + ["RISK_MILP", "RUN_TO_FAILURE"]) + " | cheapest |",
                      "|---|" + "---|" * (len(GRID) + 3)]
            for sc in SCENARIOS:
                g = pd.concat([E[(E.part == tag) & (E.scenario == sc)], E[(E.part == "E:none") & (E.scenario == sc)]])
                if mode == "in_scenario":
                    g = g[g.policy != "RISK_MILP"]
                val = g.assign(v=g.total_cost if metric else g.total_cost + D_PRICE * g.unplanned_downtime_total_h).groupby("policy")["v"].mean()
                cells = [_fmt(val.get(p)) for p in list(GRID) + ["RISK_MILP", "RUN_TO_FAILURE"]]
                lines.append(f"| {sc}{' (COLLAPSE)' if collapse[sc] else ''} | " + " | ".join(cells) + f" | {val.idxmin()} |")
            lines.append("")
            rows = []
            for sc in SCENARIOS:
                g = E[(E.part == tag) & (E.scenario == sc)]
                v = (g.total_cost if metric else g.total_cost + D_PRICE * g.unplanned_downtime_total_h)
                g = g.assign(v=v)
                r = g[g.policy == "RISK_GREEDY"].set_index("seed")["v"] - g[g.policy == "THRESHOLD_EDD"].set_index("seed")["v"]
                rows.append(f"- {sc}: RISK_GREEDY - THRESHOLD_EDD {r.mean():+.1f} [{r.min():+.1f}, {r.max():+.1f}], risk cheaper on {int((r < 0).sum())}/8")
            lines += [f"Paired (tuned {mode.replace('_', ' ')}):", ""] + rows + [""]
    lines += ["## Tuned settings (on FD001)", ""] + [f"- {o} / {sc} / {p}: {prm}" for (o, sc, p), prm in sorted(best.items())]
    (OUT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (OUT / "summary.json").write_text(json.dumps({"collapse": collapse, "best": {f"{k[0]}|{k[1]}|{k[2]}": v for k, v in best.items()}}, indent=1),
                                      encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
