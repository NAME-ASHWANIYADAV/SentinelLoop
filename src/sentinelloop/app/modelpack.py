"""Model bundles: everything needed to score one asset type, packaged with a manifest and a checksum.

A bundle directory holds `bundle.pkl` (the fitted objects) and `manifest.json` (what the model is, what it was
trained on, its scope and its benchmark evaluation, and the SHA-256 of bundle.pkl). `load_bundle` refuses a bundle
whose bytes do not match the manifest (and, when given, the checksum recorded in the registry) before unpickling.
Pickles are produced by this package and loaded only after that check; never load a bundle from an untrusted source.

The C-MAPSS family wraps the competition's fitted pipeline (train-only cleaning, causal rolling features, gradient
boosting with a conformalised quantile interval, healthy-baseline health index) and adds what a product needs around
it: the operating envelope and regime distance used for scope checks, the longest constant run per sensor seen in
training (stuck-sensor detection), and learned relations between redundant sensors (conflict detection).
"""
from __future__ import annotations

import hashlib
import json
import pickle
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from .. import anomaly, baseline, clean, config, conformal, data, evaluate, features, metrics, targets
from .timeutil import now_iso

FAMILY = "cmapss_hgbr_cqr"
BUNDLE_FILE, MANIFEST_FILE = "bundle.pkl", "manifest.json"
REDUNDANT_PAIRS = [("s8", "s13"), ("s9", "s14")]     # physical vs corrected fan speed, physical vs corrected core speed


class ModelIntegrityError(RuntimeError):
    pass


def _max_constant_run(values: np.ndarray) -> int:
    if len(values) == 0:
        return 0
    best = run = 1
    for a, b in zip(values[:-1], values[1:]):
        run = run + 1 if a == b else 1
        best = max(best, run)
    return best


@dataclass
class CmapssBundle:
    subset: str
    clean_state: clean.CleanState
    cqr: conformal.CQRModel
    detector: anomaly.AnomalyDetector
    columns: list
    window: int
    sustain: int
    rul_cap: int
    interval_level: float
    os_envelope: dict
    sensor_envelope: dict
    regime_max_dist: float
    max_constant_run: dict
    consistency: list = field(default_factory=list)

    family = FAMILY

    @property
    def required_signals(self) -> list[str]:
        return list(data.OS_COLS) + list(self.clean_state.kept_sensors)

    @property
    def history_points(self) -> int:
        return self.window + self.sustain - 1

    # -- scope ---------------------------------------------------------------------------------
    def regime_distance(self, os_vals: np.ndarray) -> np.ndarray:
        z = (np.asarray(os_vals, dtype=float) - self.clean_state.os_mean) / self.clean_state.os_std
        if self.clean_state.kmeans is None:
            return np.linalg.norm(z, axis=1)
        return np.min(self.clean_state.kmeans.transform(z), axis=1)

    def applicability(self, raw: pd.DataFrame, tolerance: float, max_out_frac: float, sensors: bool = True) -> dict:
        """Operating settings and regime (always) and, when `sensors`, the sensors' training ranges. The health service checks
        sensor ranges only after the sensor-consistency checks pass, so a faulty sensor is reported as a data problem rather
        than as an unfamiliar operating condition."""
        reasons, detail = [], {}
        os_vals = raw[data.OS_COLS].to_numpy(dtype=float)
        out = np.zeros(len(raw), dtype=bool)
        for i, c in enumerate(data.OS_COLS):
            lo, hi = self.os_envelope[c]
            tol = max((hi - lo) * tolerance, 1e-3 * max(1.0, abs(hi)))
            col = os_vals[:, i]
            out |= np.isfinite(col) & ((col < lo - tol) | (col > hi + tol))
        detail["out_of_operating_envelope_frac"] = float(out.mean()) if len(out) else 0.0
        if detail["out_of_operating_envelope_frac"] > max_out_frac:
            reasons.append(f"operating_envelope: {detail['out_of_operating_envelope_frac']:.0%} of window rows outside the model's operating settings")
        finite = np.isfinite(os_vals).all(axis=1)
        dist = self.regime_distance(os_vals[finite]) if finite.any() else np.array([])
        unknown = float((dist > self.regime_max_dist).mean()) if len(dist) else 0.0
        detail["unknown_regime_frac"] = unknown
        if unknown > max_out_frac:
            reasons.append(f"unknown_operating_regime: {unknown:.0%} of window rows far from every training regime")
        s_out = []
        for s in (self.clean_state.kept_sensors if sensors else []):
            lo, hi = self.sensor_envelope[s]
            tol = (hi - lo) * max(tolerance, 0.10)
            v = raw[s].to_numpy(dtype=float)
            v = v[np.isfinite(v)]
            if len(v) and float(((v < lo - tol) | (v > hi + tol)).mean()) > max_out_frac:
                s_out.append(s)
        detail["sensors_outside_training_range"] = s_out
        if s_out:
            reasons.append(f"sensor_envelope: {', '.join(s_out)} outside the range seen in training")
        return {"in_scope": not reasons, "reasons": reasons, "detail": detail}

    # -- model-specific data quality -------------------------------------------------------------
    def quality(self, raw: pd.DataFrame, stuck_min_run: int, max_conflict_frac: float) -> dict:
        reasons, detail = [], {"stuck": {}, "conflicts": {}}
        for s in self.clean_state.kept_sensors:
            v = raw[s].to_numpy(dtype=float)
            v = v[np.isfinite(v)]
            if len(v) < 2:
                continue
            run = 1
            for a, b in zip(v[::-1][1:], v[::-1][:-1]):
                if a != b:
                    break
                run += 1
            limit = max(stuck_min_run, int(self.max_constant_run.get(s, 0)))
            if run > limit:
                detail["stuck"][s] = run
                reasons.append(f"stuck_signal:{s} constant for the last {run} points (longest run in training {self.max_constant_run.get(s, 0)})")
        if self.consistency:
            c = self.clean_state.transform(clean.impute(raw))
            for rel in self.consistency:
                a, b = rel["a"], rel["b"]
                if a not in c.columns or b not in c.columns:
                    continue
                tail = c.tail(self.window)
                resid = tail[b].to_numpy(dtype=float) - (rel["intercept"] + rel["slope"] * tail[a].to_numpy(dtype=float))
                resid = resid[np.isfinite(resid)]
                frac = float((np.abs(resid) > rel["threshold"]).mean()) if len(resid) else 0.0
                detail["conflicts"][f"{a}/{b}"] = frac
                if frac > max_conflict_frac:
                    reasons.append(f"conflicting_readings:{a}/{b} disagree with their learned relation on {frac:.0%} of recent points")
        return {"ok": not reasons, "reasons": reasons, "detail": detail}

    # -- scoring ---------------------------------------------------------------------------------
    def score(self, raw: pd.DataFrame) -> dict:
        """`raw`: one engine's rows (columns unit, cycle, os1-3, s1-21), cycle-ordered, last row = the instant scored."""
        imp = clean.impute(raw)
        c = self.clean_state.transform(imp)
        f = features.build_features(c, self.clean_state.kept_sensors, self.window)
        X = f[self.columns]
        p, lo, hi = self.cqr.predict(X.iloc[[-1]])
        sc = self.detector.score(X.tail(self.sustain))
        flags = sc > self.detector.threshold
        top = self.detector.top_deviations(X.iloc[[-1]], n=3)[0]
        vec = np.ascontiguousarray(X.iloc[-1].to_numpy(dtype=float))
        return {"point": float(p[0]), "lower": float(lo[0]), "upper": float(hi[0]), "anomaly_score": float(sc[-1]),
                "anomaly_sustained": bool(len(flags) >= self.sustain and flags.all()), "top_deviations": [[n, float(z)] for n, z in top],
                "feature_sha256": hashlib.sha256(vec.tobytes()).hexdigest(), "n_imputed_cells": int(imp["n_imputed"].sum())}


def _git_commit() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=10, cwd=Path(__file__).parent).stdout.strip() or None
    except Exception:
        return None


def package_cmapss(subset: str, out_root, data_dir="data/raw", config_dir="configs", fast: bool = False, seed: int | None = None) -> Path:
    from .adapters.cmapss import ASSET_TYPE_ID
    cfg = config.load(subset, config_dir)
    if seed is not None:
        cfg["seed"] = int(seed)
    seed = int(cfg["seed"])
    mcfg = dict(cfg["model"])
    if fast:
        mcfg["max_iter"] = 60
    ds = data.load_subset(subset, data_dir)
    state, train_f, test_f, cols = baseline.prepare_frames(ds, cfg)
    ccfg, acfg = cfg["conformal"], cfg["anomaly"]
    window = int(cfg["features"]["window"])
    cqr = conformal.fit_cqr(train_f, cols, alpha=float(ccfg["alpha"]), calib_frac=float(ccfg["calib_frac"]), seed=seed,
                            truncations_per_engine=int(ccfg["truncations_per_engine"]), **mcfg)
    det = anomaly.AnomalyDetector.fit(train_f, cols, healthy_frac=float(acfg["healthy_frac"]), threshold_pct=float(acfg["threshold_pct"]),
                                      seed=seed, warmup=window, top_k=int(acfg.get("top_k", 3)))
    raw = ds.train
    os_env = {c: [float(raw[c].min()), float(raw[c].max())] for c in data.OS_COLS}
    sens_env = {s: [float(raw[s].min()), float(raw[s].max())] for s in state.kept_sensors}
    tmp = CmapssBundle(subset, state, cqr, det, list(cols), window, int(acfg["sustain"]), int(cfg["rul_cap"]), 1 - float(ccfg["alpha"]),
                       os_env, sens_env, 0.0, {})
    dist = tmp.regime_distance(raw[data.OS_COLS].to_numpy(dtype=float))
    regime_max = float(np.max(dist)) * 1.5 + 1e-6
    runs = {s: int(max(_max_constant_run(g[s].to_numpy()) for _, g in raw.groupby("unit"))) for s in state.kept_sensors}
    consistency = []
    for a, b in REDUNDANT_PAIRS:
        if a in state.kept_sensors and b in state.kept_sensors:
            x, y = train_f[a].to_numpy(dtype=float), train_f[b].to_numpy(dtype=float)
            slope = float(np.cov(x, y, bias=True)[0, 1] / np.var(x)) if np.var(x) > 0 else 0.0
            intercept = float(y.mean() - slope * x.mean())
            resid = y - (intercept + slope * x)
            r2 = float(1 - resid.var() / y.var()) if y.var() > 0 else 0.0
            if r2 >= 0.5:
                consistency.append({"a": a, "b": b, "slope": slope, "intercept": intercept, "r2": r2,
                                    "threshold": float(np.quantile(np.abs(resid), 0.999) * 1.5)})
    bundle = CmapssBundle(subset, state, cqr, det, list(cols), window, int(acfg["sustain"]), int(cfg["rul_cap"]), 1 - float(ccfg["alpha"]),
                          os_env, sens_env, regime_max, runs, consistency)
    # benchmark evaluation on the official test protocol (simulated data; recorded, not a field claim)
    last = evaluate.last_cycle_rows(test_f)
    p, lo, hi = cqr.predict(last[cols])
    cap = int(cfg["rul_cap"])
    t_cap, t_raw = targets.test_truth(ds.rul, cap)
    evaluation = {"protocol": "official last-cycle test, NASA C-MAPSS (simulated)", "n_test_engines": int(len(t_raw)),
                  "rmse_capped": metrics.rmse(t_cap, p), "rmse_raw": metrics.rmse(t_raw, p), "picp_capped": metrics.picp(t_cap, lo, hi),
                  "mpiw": metrics.mpiw(lo, hi)}
    blob = pickle.dumps(bundle, protocol=pickle.HIGHEST_PROTOCOL)
    sha = hashlib.sha256(blob).hexdigest()
    model_id = f"cmapss-{subset.lower()}-{sha[:10]}"
    out = Path(out_root) / model_id
    out.mkdir(parents=True, exist_ok=True)
    (out / BUNDLE_FILE).write_bytes(blob)
    manifest = {"model_id": model_id, "family": FAMILY, "version": "1", "asset_type_id": ASSET_TYPE_ID, "scope_key": f"cmapss:{subset}",
                "artifact_sha256": sha, "created_at": now_iso(), "code_commit": _git_commit(), "fast": bool(fast), "seed": seed,
                "trained_on": {"dataset": "NASA C-MAPSS (simulated turbofan engines)", "subset": subset, "split": "train",
                               "file_sha256": data.file_hashes(subset, data_dir)},
                "config_hash": config.config_hash(cfg), "rul_unit": "cycles", "rul_cap": cap, "interval_level": bundle.interval_level,
                "window": window, "history_points": bundle.history_points, "required_signals": bundle.required_signals,
                "os_envelope": os_env, "regime_max_dist": regime_max, "consistency_relations": consistency, "max_width": float(cqr.suggested_max_width),
                "evaluation": evaluation,
                "limitations": ["trained and evaluated only on simulated C-MAPSS engines", "scope checks cover operating settings and sensor ranges, "
                                "not failure modes absent from training", "interval coverage is marginal over engines and subset-dependent",
                                f"RUL is capped at {cap} cycles: predictions cannot exceed the cap"]}
    (out / MANIFEST_FILE).write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    return out


def read_manifest(bundle_dir) -> dict:
    return json.loads((Path(bundle_dir) / MANIFEST_FILE).read_text(encoding="utf-8"))


def load_bundle(bundle_dir, expected_sha256: str | None = None):
    d = Path(bundle_dir)
    try:
        manifest = read_manifest(d)
        blob = (d / BUNDLE_FILE).read_bytes()
    except FileNotFoundError as e:
        raise ModelIntegrityError(f"model artefact missing: {e}") from e
    sha = hashlib.sha256(blob).hexdigest()
    if sha != manifest.get("artifact_sha256") or (expected_sha256 and sha != expected_sha256):
        raise ModelIntegrityError(f"model artefact checksum mismatch in {d} (got {sha[:12]}..., manifest {str(manifest.get('artifact_sha256'))[:12]}...)")
    return pickle.loads(blob)      # checksum verified above; artefacts are produced by this package only
