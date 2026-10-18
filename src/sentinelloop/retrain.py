"""Guarded retraining: a challenger is promoted only if every gate passes. Rejections are logged with
reasons so the 'reject' path is as visible as the 'accept' path.

`run_retrain` is the retraining flow "when new data arrives": a C-MAPSS-format file of new run-to-failure
engines (or, for a demo, engines of the training file the champion has never seen) is appended to the
champion's data, a challenger is trained, gated on held-out validation engines and promoted or rejected,
and the outcome is written to MLflow and `artifacts/<subset>/retrain_log.json`.
"""
from __future__ import annotations

import json
import pickle
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from . import agent, baseline, clean, config, conformal, data, evaluate, features, metrics, policy, replay, targets


@dataclass
class GateResult:
    passed: bool
    reasons: list[str]
    checks: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"passed": self.passed, "reasons": list(self.reasons), "checks": dict(self.checks)}


def evaluate_gate(champion: dict, challenger: dict, gate_cfg: dict) -> GateResult:
    reasons: list[str] = []
    checks: dict = {}
    tol = float(gate_cfg.get("rmse_tol", 0.02))
    rmse_limit = champion["rmse"] * (1 + tol)
    checks["rmse"] = {"champion": champion["rmse"], "challenger": challenger["rmse"], "limit": rmse_limit, "ok": challenger["rmse"] <= rmse_limit}
    if not checks["rmse"]["ok"]:
        reasons.append(f"rmse {challenger['rmse']:.3f} > {rmse_limit:.3f} (champion {champion['rmse']:.3f} + {tol:.0%})")
    min_picp = float(gate_cfg.get("min_picp", 0.85))
    checks["picp"] = {"challenger": challenger["picp"], "min": min_picp, "ok": challenger["picp"] >= min_picp}
    if not checks["picp"]["ok"]:
        reasons.append(f"picp {challenger['picp']:.3f} < {min_picp:.2f}")
    max_inc = float(gate_cfg.get("max_late_rate_increase", 0.02))
    late_limit = champion["late_rate"] + max_inc
    checks["late_rate"] = {"champion": champion["late_rate"], "challenger": challenger["late_rate"], "limit": late_limit, "ok": challenger["late_rate"] <= late_limit,
                           "threshold": champion.get("late_threshold")}
    if not checks["late_rate"]["ok"]:
        reasons.append(f"late_rate {challenger['late_rate']:.3f} > {late_limit:.3f} (champion {champion['late_rate']:.3f} + {max_inc:.2f})")
    return GateResult(passed=not reasons, reasons=reasons, checks=checks)


def split_units(units, seed: int, val_frac: float = 0.2, champ_frac: float = 0.5) -> tuple[list[int], list[int], list[int]]:
    """Deterministic engine split: validation (never trained on), champion data, 'new' data."""
    arr = np.array(sorted(int(u) for u in set(units)))
    rng = np.random.default_rng(seed)
    rng.shuffle(arr)
    n = len(arr)
    nv, nc = int(round(val_frac * n)), int(round(champ_frac * n))
    return sorted(arr[:nv].tolist()), sorted(arr[nv:nv + nc].tolist()), sorted(arr[nv + nc:].tolist())


def validation_metrics(cqr, val_f: pd.DataFrame, cols: list[str], thr: agent.Thresholds, seed: int, rows_per_engine: int = 5, min_lead: int = 5) -> dict:
    """Gate metrics on validation engines: RMSE and coverage on random cycles; late-order rate of the lower-bound
    policy at the CRITICAL threshold (where late orders can occur) and, for reference, at the HIGH threshold."""
    rows = evaluate.random_rows_per_engine(val_f, n_per_engine=rows_per_engine, seed=seed)
    p, lo, hi = cqr.predict(rows[cols])
    full = val_f.copy()
    full["point"], full["lower"], full["upper"] = cqr.predict(full[cols])
    full["rul_true_raw"] = full["rul_raw"]
    late_c = replay.decision_metrics(replay.replay_policy(full, policy.Policy("C", "lower", thr.t_critical), min_lead=min_lead))["late_rate"]
    late_h = replay.decision_metrics(replay.replay_policy(full, policy.Policy("C", "lower", thr.t_high), min_lead=min_lead))["late_rate"]
    return {"rmse": metrics.rmse(rows["rul"], p), "picp": metrics.picp(rows["rul"], lo, hi), "mpiw": metrics.mpiw(lo, hi),
            "late_rate": float(late_c), "late_rate_high": float(late_h), "late_threshold": thr.t_critical, "n_validation_rows": int(len(rows))}


def append_retrain_log(path: Path, run_name: str, rows: list[dict]) -> None:
    """Keep rows of every named run; a re-run replaces only its own rows."""
    previous = [r for r in (json.loads(path.read_text(encoding="utf-8")) if path.exists() else []) if r.get("run") not in (None, run_name)]
    path.write_text(json.dumps(previous + [{"run": run_name, **r} for r in rows], indent=1, default=str), encoding="utf-8")


NEW_UNIT_OFFSET = 100000   # unit ids of new engines are offset so they never collide with the champion's engines


def _prepare_new_engines(raw_new: pd.DataFrame, state: clean.CleanState, cfg: dict) -> pd.DataFrame:
    new_i = clean.impute(raw_new)
    alpha = cfg["clean"].get("ema_alpha") or 0.0
    if alpha:
        new_i = clean.ema_denoise(new_i, alpha, data.SENSORS)
    new_c = state.transform(new_i)
    new_f = targets.add_train_rul(features.build_features(new_c, state.kept_sensors, int(cfg["features"]["window"])), cap=int(cfg["rul_cap"]))
    new_f["unit"] = new_f["unit"] + NEW_UNIT_OFFSET
    return new_f


def run_retrain(subset: str, data_dir="data/raw", out_dir="artifacts", config_dir="configs", new_data: str | Path | None = None,
                simulate_new_data: bool = False, fast: bool = False, seed: int | None = None, only_if_drift: bool = False,
                mlflow: bool = True, log=print) -> dict:
    cfg = config.load(subset, config_dir)
    if seed is not None:
        cfg["seed"] = int(seed)
    seed = int(cfg["seed"])
    out_root = Path(out_dir)
    out = out_root / subset
    out.mkdir(parents=True, exist_ok=True)
    log_path = out / "retrain_log.json"

    if only_if_drift:
        ref = out / "drift_reference.json"
        alarm = bool(json.loads(ref.read_text(encoding="utf-8")).get("test_window", {}).get("alarm", False)) if ref.exists() else False
        if not alarm:
            msg = f"no drift alarm recorded in {ref} (run `python -m sentinelloop run --subset {subset}` first, or drop --only-if-drift to retrain on new data regardless)"
            log(f"[{subset}] retrain SKIPPED: {msg}")
            return {"decision": "SKIPPED", "reasons": [msg], "subset": subset}

    mcfg = dict(cfg["model"])
    if fast:
        mcfg["max_iter"] = 60
    ccfg = cfg["conformal"]
    kw = dict(alpha=float(ccfg["alpha"]), calib_frac=float(ccfg["calib_frac"]), seed=seed, truncations_per_engine=int(ccfg["truncations_per_engine"]), **mcfg)

    ds = data.load_subset(subset, data_dir)
    state, train_f, _, cols = baseline.prepare_frames(ds, cfg)
    val_u, champ_u, new_u = split_units(train_f["unit"].unique(), seed)
    val_f = train_f[train_f.unit.isin(val_u)]
    # the champion's width calibration gives the agent's "insufficient evidence" limit; any finite value works for the late-rate replay
    thr = agent.Thresholds.from_config(cfg, auto_max_width=60.0)

    # ---- new data: a C-MAPSS-format run-to-failure file, or engines of the training file the champion has never seen (demo)
    if new_data is not None:
        raw_new = data.read_cmapss_txt(new_data)
        new_f = _prepare_new_engines(raw_new, state, cfg)
        source = str(new_data)
    elif simulate_new_data:
        incoming = out_root / "incoming"
        incoming.mkdir(parents=True, exist_ok=True)
        fpath = incoming / f"{subset}_new_engines.txt"
        ds.train[ds.train.unit.isin(new_u)].to_csv(fpath, sep=" ", header=False, index=False)
        new_f = train_f[train_f.unit.isin(new_u)].copy()
        source = f"{fpath} (simulated: {len(new_u)} training engines the champion was never trained on)"
    else:
        raise ValueError("run_retrain needs new_data=<C-MAPSS txt> or simulate_new_data=True")
    n_new = int(new_f["unit"].nunique())

    # ---- champion: stored gated champion if present, else trained on the champion split and stored
    champ_path = out / "gated_champion.pkl"
    tr = None
    name = f"sentinelloop-{subset}-gated"
    if mlflow:
        from . import tracking
        tr = tracking.Tracker(f"sqlite:///{(out_root / 'mlflow.db').resolve().as_posix()}", out_root / "mlruns", experiment="sentinelloop-retrain")
    if champ_path.exists():
        # pickle produced by this package on this machine (the stored gated champion); never load pickles from untrusted sources
        with open(champ_path, "rb") as fh:
            stored = pickle.load(fh)
        champ, champ_units, champ_run = stored["cqr"], list(stored["units"]), stored.get("mlflow_run_id", "local")
        log(f"[{subset}] champion loaded from {champ_path} ({len(champ_units)} engines)")
    else:
        champ_units = list(champ_u)
        log(f"[{subset}] training champion on {len(champ_units)} engines (validation {len(val_u)} engines held out)")
        champ = conformal.fit_cqr(train_f[train_f.unit.isin(champ_units)], cols, **kw)
        champ_run = "local"
        if tr is not None:
            cm0 = validation_metrics(champ, val_f, cols, thr, seed)
            champ_run = tr.log_run(params={"subset": subset, "role": "champion", "n_engines": len(champ_units)}, metrics=cm0, model=champ.point, model_name=name,
                                   alias="champion", tags={"subset": subset, "scenario": "champion", "source": "retrain-cli"}, run_name=f"{subset}-champion")
        with open(champ_path, "wb") as fh:
            pickle.dump({"cqr": champ, "units": champ_units, "mlflow_run_id": champ_run}, fh)
    cm = validation_metrics(champ, val_f, cols, thr, seed)

    # ---- challenger on champion data + new engines, gated against the champion on the validation engines
    log(f"[{subset}] new data: {source}; training challenger on {len(champ_units)} + {n_new} engines")
    base_f = train_f[train_f.unit.isin(champ_units)]
    chall = conformal.fit_cqr(pd.concat([base_f, new_f]), cols, **kw)
    m = validation_metrics(chall, val_f, cols, thr, seed)
    g = evaluate_gate(cm, m, cfg["gate"])
    decision = "PROMOTE" if g.passed else "REJECT"
    run_id = "local"
    version = None
    if tr is not None:
        run_id = tr.log_run(params={"subset": subset, "role": "challenger", "scenario": "new_data", "n_engines": len(champ_units) + n_new, "source": source[:200]},
                            metrics={**m, "gate_passed": float(g.passed)}, model=chall.point, model_name=name, alias="challenger",
                            tags={"subset": subset, "scenario": "new_data", "gate": decision, "reasons": "; ".join(g.reasons), "source": "retrain-cli"}, run_name=f"{subset}-new-data")
        if g.passed:
            tr.promote(name, tr.version_for_alias(name, "challenger"))
        version = tr.version_for_alias(name, "champion")
    if g.passed:
        with open(champ_path, "wb") as fh:
            pickle.dump({"cqr": chall, "units": champ_units + sorted(int(u) for u in new_f["unit"].unique()), "mlflow_run_id": run_id}, fh)
    entry = {"subset": subset, "scenario": "new_data", "source": source, "n_new_engines": n_new, "expected": "", "decision": decision, "as_expected": None,
             "champion_rmse": cm["rmse"], "challenger_rmse": m["rmse"], "champion_picp": cm["picp"], "challenger_picp": m["picp"],
             "champion_late_rate": cm["late_rate"], "challenger_late_rate": m["late_rate"], "late_threshold": cm["late_threshold"],
             "reasons": "; ".join(g.reasons), "checks": g.checks, "mlflow_run_id": run_id, "champion_alias_version": version, "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}
    previous_cli = [r for r in (json.loads(log_path.read_text(encoding="utf-8")) if log_path.exists() else []) if r.get("run") == "cli"]
    append_retrain_log(log_path, "cli", [{k: v for k, v in r.items() if k != "run"} for r in previous_cli] + [entry])
    log(f"[{subset}] challenger {decision}: rmse {cm['rmse']:.2f}->{m['rmse']:.2f} picp {cm['picp']:.3f}->{m['picp']:.3f} "
        f"late@{cm['late_threshold']:.0f} {cm['late_rate']:.3f}->{m['late_rate']:.3f} {g.reasons if g.reasons else '(all gates passed)'}; log {log_path}")
    return {"subset": subset, "decision": decision, "reasons": g.reasons, "checks": g.checks, "champion_metrics": cm, "challenger_metrics": m,
            "promoted": bool(g.passed), "mlflow_run_id": run_id, "log_path": str(log_path), "n_new_engines": n_new, "source": source}
