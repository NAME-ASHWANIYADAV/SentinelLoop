"""Shared helpers for the experiment scripts (paths, caching of out-of-fold predictions, saving)."""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sentinelloop import agent, baseline, config, data, oof  # noqa: E402

RESULTS = ROOT / "experiments" / "results"
ARTIFACTS = ROOT / "artifacts"
SUBSETS = list(config.SUBSETS)
SEEDS = [42, 43, 44, 45, 46]


def log(msg: str) -> None:
    print(msg, flush=True)


def save(exp: str, summary: dict, readme: str, tables: dict[str, pd.DataFrame] | None = None) -> Path:
    d = RESULTS / exp
    d.mkdir(parents=True, exist_ok=True)
    summary = dict(summary)
    summary["generated"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    # provenance: the configuration every subset ran under (seed included in the hash) and the package location
    try:
        summary["config_hashes"] = {s: config.config_hash(config.load(s, ROOT / "configs")) for s in SUBSETS}
        summary["seed"] = int(config.load(SUBSETS[0], ROOT / "configs")["seed"])
    except Exception as e:  # never let provenance break an experiment
        summary["config_hashes"] = {"error": str(e)}
    (d / "summary.json").write_text(json.dumps(summary, indent=1, default=_json_default), encoding="utf-8")
    (d / "README.md").write_text(readme, encoding="utf-8")
    for name, df in (tables or {}).items():
        df.to_csv(d / name, index=False)
    log(f"saved {d}")
    return d


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)


def prepared(subset: str, cfg: dict | None = None):
    cfg = cfg or config.load(subset, ROOT / "configs")
    ds = data.load_subset(subset, ROOT / "data" / "raw")
    state, train_f, test_f, cols = baseline.prepare_frames(ds, cfg)
    return cfg, ds, state, train_f, test_f, cols


def oof_table(subset: str, fast: bool = False, with_baselines: bool = False, force: bool = False):
    """Cached out-of-fold predictions over all training engines (expensive; shared by E1, E2, E5)."""
    d = RESULTS / "oof"
    d.mkdir(parents=True, exist_ok=True)
    tag = "fast" if fast else "full"
    path = d / f"{subset}_{tag}{'_bl' if with_baselines else ''}.csv"
    meta = d / f"{subset}_{tag}{'_bl' if with_baselines else ''}_folds.json"
    if path.exists() and meta.exists() and not force:
        return pd.read_csv(path), json.loads(meta.read_text(encoding="utf-8"))
    cfg, ds, state, train_f, test_f, cols = prepared(subset)
    mcfg = dict(cfg["model"])
    if fast:
        mcfg["max_iter"] = 60
    t0 = time.time()
    log(f"[{subset}] computing out-of-fold CQR predictions ({cfg['cv']['n_folds']} folds, {'fast' if fast else 'full'})")
    out, folds = oof.oof_cqr_predictions(train_f, cols, n_folds=int(cfg["cv"]["n_folds"]), alpha=float(cfg["conformal"]["alpha"]),
                                         calib_frac=float(cfg["conformal"]["calib_frac"]), seed=int(cfg["seed"]), max_iter=mcfg["max_iter"],
                                         learning_rate=mcfg["learning_rate"], max_leaf_nodes=mcfg["max_leaf_nodes"],
                                         truncations_per_engine=int(cfg["conformal"]["truncations_per_engine"]),
                                         healthy_frac=float(cfg["anomaly"]["healthy_frac"]), threshold_pct=float(cfg["anomaly"]["threshold_pct"]),
                                         sustain=int(cfg["anomaly"]["sustain"]), warmup=int(cfg["features"]["window"]), log=log,
                                         with_baselines=with_baselines, rf_trees=50 if fast else 150, top_k=int(cfg["anomaly"].get("top_k", 3)))
    out.to_csv(path, index=False)
    meta.write_text(json.dumps({"folds": folds, "elapsed_s": round(time.time() - t0, 1), "config_hash": config.config_hash(cfg)}, indent=1), encoding="utf-8")
    log(f"[{subset}] OOF done in {time.time() - t0:.0f} s -> {path}")
    return out, json.loads(meta.read_text(encoding="utf-8"))


def tune_eval_split(units, seed: int = 42, tune_frac: float = 0.3):
    units = np.array(sorted(int(u) for u in set(units)))
    rng = np.random.default_rng(seed)
    rng.shuffle(units)
    n = max(1, int(round(tune_frac * len(units))))
    return sorted(int(u) for u in units[:n]), sorted(int(u) for u in units[n:])


def severities_for_engine(g: pd.DataFrame, thr: agent.Thresholds, model_version: str = "oof", use_quality: bool = True, drift_flag: bool = False):
    """Run the Triage Agent cycle by cycle on one engine's OOF rows; returns a list of Decisions.
    If the rows carry a per-fold `max_width` (calibrated on that fold's model), it overrides thr.max_width."""
    decisions = []
    n_imp = g["n_imputed"].to_numpy() if ("n_imputed" in g.columns and use_quality) else np.zeros(len(g))
    n_sensors = len([c for c in g.columns if re.fullmatch(r"s\d+", str(c))]) or 14   # kept sensors present in the table (17 on FD002/FD004)
    mw = g["max_width"].to_numpy() if "max_width" in g.columns else np.full(len(g), thr.max_width)
    cache: dict[float, agent.Thresholds] = {}
    for row, imp, w in zip(g.itertuples(index=False), n_imp, mw):
        t = cache.get(float(w))
        if t is None:
            t = agent.Thresholds(t_critical=thr.t_critical, t_high=thr.t_high, t_medium=thr.t_medium, max_width=float(w),
                                 quality_max_imputed_frac=thr.quality_max_imputed_frac, conflict_factor=thr.conflict_factor)
            cache[float(w)] = t
        obs = agent.Observation(unit=int(row.unit), cycle=int(row.cycle), rul_point=float(row.point), rul_lower=float(row.lower), rul_upper=float(row.upper),
                                anomaly_flag=bool(row.anomaly_flag), anomaly_score=float(row.anomaly_score), drift_flag=drift_flag,
                                imputed_frac=float(imp) / n_sensors, missing_sensors=0, model_version=model_version)
        decisions.append(agent.triage(obs, t))
    return decisions


def thresholds(cfg: dict) -> agent.Thresholds:
    """Thresholds for experiments; 'auto' width is replaced per fold from the OOF table, so any finite fallback works here."""
    return agent.Thresholds.from_config(cfg, auto_max_width=60.0)


def markdown_table(df: pd.DataFrame, floatfmt: str = "{:.3f}") -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(str(c) for c in cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, r in df.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            cells.append(floatfmt.format(v) if isinstance(v, (float, np.floating)) and not pd.isna(v) else str(v))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)
