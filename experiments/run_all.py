"""Run the whole evidence pipeline: end-to-end artefacts for every subset, then experiments E1-E7.

    .venv/Scripts/python.exe experiments/run_all.py [--fast] [--subsets FD001 FD004] [--skip-pipeline]
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

from common import ROOT, SUBSETS, log

PY = sys.executable


def sh(cmd: list[str]) -> None:
    t = time.time()
    log("$ " + " ".join(cmd))
    r = subprocess.run(cmd, cwd=str(ROOT))
    log(f"  -> exit {r.returncode} in {time.time() - t:.0f} s")
    if r.returncode != 0:
        raise SystemExit(f"step failed: {' '.join(cmd)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fast", action="store_true")
    ap.add_argument("--subsets", nargs="*", default=SUBSETS)
    ap.add_argument("--skip-pipeline", action="store_true")
    ap.add_argument("--skip-baseline", action="store_true", help="skip E0 (python -m sentinelloop baseline), ~12 min for all subsets")
    ap.add_argument("--seeds", nargs="*", type=int, default=[42, 43, 44], help="seeds for the E1 seed-sensitivity check (FD001)")
    args = ap.parse_args()
    fast = ["--fast"] if args.fast else []
    t0 = time.time()
    if not args.skip_baseline:
        for s in args.subsets:
            sh([PY, "-m", "sentinelloop", "baseline", "--subset", s] + fast)     # E0 -> artifacts/baseline/<subset>/
        # keep a copy of E0 with the other experiment evidence
        import shutil
        for s in args.subsets:
            src = ROOT / "artifacts" / "baseline" / s
            dst = ROOT / "experiments" / "results" / "e0_baseline"
            dst.mkdir(parents=True, exist_ok=True)
            for f in ("metrics.json", "predictions_test.csv"):
                if (src / f).exists():
                    shutil.copy(src / f, dst / f"{s}_{f}")
    if not args.skip_pipeline:
        for s in args.subsets:
            sh([PY, "-m", "sentinelloop", "run", "--subset", s, "--stream-units", "5"] + fast)
    exp = ROOT / "experiments"
    sh([PY, str(exp / "e1_policy_replay.py"), "--subsets", *args.subsets] + fast)
    sh([PY, str(exp / "e2_abstention.py"), "--subsets", *args.subsets] + fast)
    sh([PY, str(exp / "e5_decision_vs_rmse.py"), "--subsets", *args.subsets] + fast)
    sh([PY, str(exp / "e3_stress.py"), "--subsets", *args.subsets])
    sh([PY, str(exp / "e4_retrain_gate.py"), "--subsets", *args.subsets] + fast)
    # secondary E4 (post hoc, decision D21): 20 validation rows per engine + label-corruption scenario B2
    sh([PY, str(exp / "e4_retrain_gate.py"), "--subsets", *args.subsets, "--val-rows", "20", "--label-corruption", "--out", "e4_retrain_gate_secondary"] + fast)
    sh([PY, str(exp / "e6_audit_check.py")])
    sh([PY, str(exp / "e7_ablation.py"), "--subsets", *[s for s in args.subsets if s in ("FD001", "FD004")]] + fast)
    if "FD001" in args.subsets:
        sh([PY, str(exp / "e1_seed_sensitivity.py"), "--subsets", "FD001", "--seeds", *[str(s) for s in args.seeds]] + fast)
    log(f"ALL DONE in {(time.time() - t0) / 60:.1f} min; summaries under experiments/results/<exp>/summary.json")


if __name__ == "__main__":
    main()
