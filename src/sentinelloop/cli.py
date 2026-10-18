"""CLI. Commands print what they did and where artefacts went."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import config, data


def cmd_doctor(args: argparse.Namespace) -> int:
    import numpy, pandas, sklearn, scipy, mlflow, streamlit, plotly, yaml  # noqa: F401
    ok = True
    print(f"python {sys.version.split()[0]}  numpy {numpy.__version__}  pandas {pandas.__version__}  scikit-learn {sklearn.__version__}  mlflow {mlflow.__version__}  streamlit {streamlit.__version__}")
    if sys.version_info < (3, 11):
        print("FAIL: Python >= 3.11 required"); ok = False
    if not pandas.__version__.startswith("2."):
        print("FAIL: pandas 2.x required (3.x untested)"); ok = False
    d = Path(args.data_dir)
    missing = [f for s in config.SUBSETS for f in (f"train_{s}.txt", f"test_{s}.txt", f"RUL_{s}.txt") if not (d / f).exists()]
    if missing:
        print(f"WARN: {len(missing)} data files missing in {d}; run: python -m sentinelloop data --download"); ok = False
    else:
        print(f"data: all 12 C-MAPSS files present in {d}")
    for name, good in data.verify_archive(d).items():
        print(f"archive {name}: {'checksum OK' if good else 'CHECKSUM MISMATCH'}")
        ok = ok and good
    print("doctor:", "OK" if ok else "PROBLEMS FOUND")
    return 0 if ok else 1


def cmd_data(args: argparse.Namespace) -> int:
    if args.download:
        data.download(args.data_dir)
        print(f"downloaded and verified into {args.data_dir}")
    for s in (config.SUBSETS if args.subset == "all" else [args.subset]):
        ds = data.load_subset(s, args.data_dir)
        print(f"{s}: train {ds.train.shape} units {ds.train.unit.nunique()} | test {ds.test.shape} units {ds.test.unit.nunique()} | RUL {len(ds.rul)}")
        print("  sha256:", json.dumps(data.file_hashes(s, args.data_dir)))
    return 0


def _subsets(arg: str) -> list[str]:
    return list(config.SUBSETS) if arg == "all" else [arg]


def cmd_baseline(args: argparse.Namespace) -> int:
    from . import baseline
    for s in _subsets(args.subset):
        m = baseline.run_baseline(s, data_dir=args.data_dir, out_dir=args.out_dir, config_dir=args.config_dir, fast=args.fast, seed=args.seed)["metrics"]
        print(f"[{s}] HGBR RMSE capped {m['hgbr_rmse_capped']:.2f} raw {m['hgbr_rmse_raw']:.2f} PHM08 {m['hgbr_phm08']:.1f} | RF {m['rf_rmse_capped']:.2f} | naive {m['naive_rmse_capped']:.2f} | "
              f"CV all-rows {m['cv_rmse_all_rows']:.2f} random-trunc {m['cv_rmse_random_truncation_protocol']:.2f} last-cycle(leaky) {m['cv_rmse_last_cycle_naive_protocol']:.2f} | {m['elapsed_s']} s", flush=True)
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    from . import pipeline
    for s in _subsets(args.subset):
        pipeline.run(s, data_dir=args.data_dir, out_dir=args.out_dir, config_dir=args.config_dir, fast=args.fast, stream_units=args.stream_units,
                     mlflow=not args.no_mlflow, seed=args.seed, log=lambda msg: print(msg, flush=True))
    print(f"artefacts in {args.out_dir}/<subset>/ ; audit logs {args.out_dir}/audit/decisions_<subset>.jsonl ; SQLite {args.out_dir}/sentinelloop.db ; MLflow sqlite:///{args.out_dir}/mlflow.db (paths are relative to the current directory: run from the project root)")
    return 0


def cmd_retrain(args: argparse.Namespace) -> int:
    from . import retrain
    res = retrain.run_retrain(args.subset, data_dir=args.data_dir, out_dir=args.out_dir, config_dir=args.config_dir, new_data=args.new_data,
                              simulate_new_data=args.simulate_new_data, fast=args.fast, seed=args.seed, only_if_drift=args.only_if_drift,
                              mlflow=not args.no_mlflow, log=lambda msg: print(msg, flush=True))
    print(json.dumps({k: res.get(k) for k in ("subset", "decision", "reasons", "promoted", "champion_metrics", "challenger_metrics", "mlflow_run_id", "log_path")}, indent=1, default=str))
    return 0 if res["decision"] != "SKIPPED" else 2


def cmd_audit(args: argparse.Namespace) -> int:
    from . import audit
    rep = audit.replay_check_all(args.out_dir)
    print(json.dumps(rep, indent=1))
    return 0 if rep["mismatches"] == 0 and rep["chain_valid"] else 1


def cmd_dashboard(args: argparse.Namespace) -> int:
    import subprocess
    app = Path(__file__).with_name("dashboard.py")
    return subprocess.call([sys.executable, "-m", "streamlit", "run", str(app), "--server.headless", "true", "--browser.gatherUsageStats", "false", "--", "--out-dir", args.out_dir])


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sentinelloop", description="SentinelLoop prognostics loop (C-MAPSS)")
    p.add_argument("--data-dir", default="data/raw")
    p.add_argument("--out-dir", default="artifacts")
    p.add_argument("--config-dir", default="configs")
    sub = p.add_subparsers(dest="command", required=True)

    def common(sp):
        # the same options are accepted after the subcommand (argparse only binds parent options placed before it)
        for name in ("--data-dir", "--out-dir", "--config-dir"):
            sp.add_argument(name, default=argparse.SUPPRESS)
        return sp
    common(sub.add_parser("doctor", help="check environment and data")).set_defaults(func=cmd_doctor)
    d = common(sub.add_parser("data", help="verify or download the dataset")); d.add_argument("--subset", default="all"); d.add_argument("--download", action="store_true"); d.set_defaults(func=cmd_data)
    b = common(sub.add_parser("baseline", help="E0 reproducible baseline")); b.add_argument("--subset", default="FD001"); b.add_argument("--fast", action="store_true"); b.add_argument("--seed", type=int, default=None); b.set_defaults(func=cmd_baseline)
    r = common(sub.add_parser("run", help="end-to-end pipeline: models, intervals, anomaly, drift, agent, work orders, audit, MLflow"))
    r.add_argument("--subset", default="FD001"); r.add_argument("--fast", action="store_true"); r.add_argument("--stream-units", type=int, default=5)
    r.add_argument("--no-mlflow", action="store_true"); r.add_argument("--seed", type=int, default=None); r.set_defaults(func=cmd_run)
    rt = common(sub.add_parser("retrain", help="retraining flow when new data arrives: challenger on champion data + new engines, gated, promoted or rejected, logged"))
    rt.add_argument("--subset", default="FD001"); rt.add_argument("--new-data", default=None, help="C-MAPSS-format run-to-failure file of new engines")
    rt.add_argument("--simulate-new-data", action="store_true", help="demo: use training engines the champion has never seen and write them to <out-dir>/incoming/")
    rt.add_argument("--only-if-drift", action="store_true", help="retrain only if the last pipeline run recorded a drift alarm")
    rt.add_argument("--fast", action="store_true"); rt.add_argument("--seed", type=int, default=None); rt.add_argument("--no-mlflow", action="store_true")
    rt.set_defaults(func=cmd_retrain)
    common(sub.add_parser("audit", help="verify the audit chain and re-derive every decision")).set_defaults(func=cmd_audit)
    common(sub.add_parser("dashboard", help="launch the Streamlit dashboard")).set_defaults(func=cmd_dashboard)
    return p


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    sys.exit(args.func(args))
