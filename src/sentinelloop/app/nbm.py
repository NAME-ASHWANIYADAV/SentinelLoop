"""Normal-behaviour model (NBM) for wind-turbine drivetrain temperatures - an anomaly model, not a failure-time model.

For each target temperature (gearbox HSS bearing, gearbox oil, generator bearing) a ridge regression learned on
healthy operation predicts the temperature from load history (exponentially smoothed power at three time constants),
ambient and nacelle temperature, wind and rotor speed. The residual, standardised by its healthy spread, is averaged
over the last `window` operating points; a target is anomalous when that average stays above its threshold at each of
the last `sustain` operating points (idle rows in between add no evidence). Thresholds come from held-out healthy data
(the last 25% of each training turbine's record): inspect = 1.25 x the largest healthy rolling score, urgent = 3 x the
inspect threshold. Both are policy choices recorded in the manifest, not calibrated failure probabilities.

Commissioning: turbines of one type still differ (sensor placement, cooling, wear), so a fleet model leaves each
turbine with a standing residual offset that a fixed threshold would read as an anomaly. Each turbine is therefore
commissioned on a period a reliability engineer declares healthy: its mean standardised residual per target is
stored (audited) on the asset and subtracted before thresholds apply. A turbine without a baseline for the approved
model is MODEL_OUT_OF_SCOPE. A baseline taken while a fault is already developing would hide that fault - the
declaration is a human judgement and is recorded as one.

What this model does NOT do: estimate remaining life or a probability of failure. Assessments built on it carry no
RUL and no risk numbers; the state machine maps sustained deviations to INSPECTION_RECOMMENDED and severe sustained
deviations to URGENT_REVIEW, and the decision engine then uses policy default due dates.

Scope and data checks (used by the assessment service in the same order as for the C-MAPSS family):
- applicability: share of operating points (power > 5% of rated) in the scoring window; ambient, nacelle and wind
  speed inside the training envelope (with tolerance);
- quality: stuck temperature or wind sensors (a constant run longer than any seen in training, at the end of the window
  or anywhere in the rows the score uses: readings rejected as stuck are never scored) and generator/rotor speed
  disagreement with the learned gear relation.
"""
from __future__ import annotations

import hashlib
import json
import pickle
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.signal import lfilter

from .adapters.wind import ASSET_TYPE_ID, OPTIONAL_SIGNALS, RATED_KW, SIGNAL_META, SIGNALS, TARGETS
from .modelpack import BUNDLE_FILE, MANIFEST_FILE, ModelIntegrityError, _git_commit, _max_constant_run, load_bundle, read_manifest  # noqa: F401
from .timeutil import iso, now_iso

FAMILY = "wind_nbm_ridge"
TAUS = (3.0, 9.0, 18.0)                 # EWMA time constants in 10-min steps (30 min, 90 min, 3 h)
WARMUP, WINDOW, SUSTAIN = 54, 36, 18    # points: EWMA warm-up (3 x the longest tau), rolling score (6 h), sustain (18 operating points = 3 h of operation; W3, PD-15)
OP_FRAC = 0.05                          # operating = power above 5% of rated
STUCK_SIGNALS = ["wind_speed", "ambient_temp", "nacelle_temp"] + TARGETS
ENVELOPE_SIGNALS = ["ambient_temp", "nacelle_temp", "wind_speed"]
INSPECT_MARGIN, URGENT_MULT = 1.25, 3.0
MIN_BASELINE_POINTS = 288               # two days of operating 10-minute points
COMMISSIONERS = {"reliability_engineer", "admin"}


class CommissionError(ValueError):
    pass


def _ewma(x: np.ndarray, tau: float) -> np.ndarray:
    a = float(np.exp(-1.0 / tau))
    x0 = x[0] if len(x) else 0.0
    y, _ = lfilter([1 - a], [1, -a], x, zi=[a * x0])
    return y


MODEL_SIGNALS = ["wind_speed", "active_power", "rotor_speed", "generator_speed", "ambient_temp", "nacelle_temp"] + TARGETS


def _fill(df: pd.DataFrame, cols: list) -> tuple[pd.DataFrame, int]:
    sub = df[cols].astype(float)
    n_missing = int(sub.isna().sum().sum())
    return sub.ffill().bfill(), n_missing


def design(df: pd.DataFrame, rated_kw: float = RATED_KW) -> tuple[np.ndarray, np.ndarray, int]:
    """Feature matrix for time-ordered rows of ONE turbine (causal: row i uses rows <= i). Returns (X, operating, n_imputed)."""
    f, n_imp = _fill(df, MODEL_SIGNALS)
    p = f["active_power"].to_numpy() / rated_kw
    cols = [np.ones(len(f)), p, p ** 2] + [_ewma(np.clip(p, 0, None), t) for t in TAUS]
    cols += [f["ambient_temp"].to_numpy(), f["nacelle_temp"].to_numpy(), f["wind_speed"].to_numpy(), f["rotor_speed"].to_numpy() / 16.8]
    return np.column_stack(cols), p > OP_FRAC, n_imp


def _rolling_mean_operating(z: np.ndarray, op: np.ndarray, window: int) -> np.ndarray:
    """Mean of z over the trailing `window` operating points (NaN until half a window of operation is available)."""
    out = np.full(len(z), np.nan)
    idx = np.flatnonzero(op & np.isfinite(z))
    if len(idx) == 0:
        return out
    vals = z[idx]
    c = np.concatenate([[0.0], np.cumsum(vals)])
    for k, i in enumerate(idx):
        lo = max(0, k + 1 - window)
        if k + 1 - lo >= window // 2:
            out[i] = (c[k + 1] - c[lo]) / (k + 1 - lo)
    # carry the last operating score forward over non-operating points so `sustain` counts operating evidence only
    s = pd.Series(out)
    return s.where(pd.Series(op)).ffill().to_numpy() if op.any() else out


@dataclass
class WindNBMBundle:
    targets: list
    coef: dict                    # target -> weights (len = n features)
    resid_mu: dict
    resid_sd: dict
    thr_inspect: dict
    thr_urgent: dict
    envelope: dict                # signal -> [lo, hi] seen in training
    max_constant_run: dict
    speed_slope: float
    speed_threshold: float
    rated_kw: float = RATED_KW
    min_operating_frac: float = 0.5
    window: int = WINDOW
    sustain: int = SUSTAIN
    warmup: int = WARMUP
    extra: dict = field(default_factory=dict)

    family = FAMILY
    prediction_kind = "anomaly"
    needs_baseline = True
    quality_independent_of_scope = True        # stuck sensors and the gear relation (operating points only) do not depend on regime
    interval_level = None
    rul_cap = None

    @property
    def required_signals(self) -> list[str]:
        return list(MODEL_SIGNALS)

    @property
    def history_points(self) -> int:
        return self.warmup + self.window + self.sustain - 1

    # -- scope -----------------------------------------------------------------------------------
    def applicability(self, raw: pd.DataFrame, tolerance: float, max_out_frac: float, sensors: bool = True) -> dict:
        reasons, detail = [], {}
        tail = raw.tail(self.window + self.sustain)
        pw = tail["active_power"].to_numpy(dtype=float)
        op = float(np.mean(np.nan_to_num(pw, nan=0.0) / self.rated_kw > OP_FRAC)) if len(pw) else 0.0
        detail["operating_frac"] = op
        if op < self.min_operating_frac:
            reasons.append(f"insufficient_operation: the turbine produced power in {op:.0%} of the scoring window (the model needs "
                           f"{self.min_operating_frac:.0%}); no statement about its health is possible")
        out = {}
        for s in ENVELOPE_SIGNALS:
            lo, hi = self.envelope[s]
            tol = (hi - lo) * max(tolerance, 0.05)
            v = tail[s].to_numpy(dtype=float)
            v = v[np.isfinite(v)]
            frac = float(((v < lo - tol) | (v > hi + tol)).mean()) if len(v) else 0.0
            if frac > max_out_frac:
                out[s] = frac
        detail["outside_training_envelope"] = out
        if out:
            reasons.append("operating_envelope: " + ", ".join(f"{s} outside the training range on {f:.0%} of points" for s, f in out.items()))
        return {"in_scope": not reasons, "reasons": reasons, "detail": detail}

    # -- model-specific data quality ---------------------------------------------------------------
    def scored_from(self, raw: pd.DataFrame) -> int:
        """First row of `raw` whose readings can enter the score: the rolling means at the last `sustain` operating points
        each average `window` operating points, all after the EWMA warm-up."""
        p = raw["active_power"].astype(float).ffill().bfill().to_numpy() / self.rated_kw          # the operating mask of `design`
        op = np.flatnonzero(np.nan_to_num(p, nan=0.0) > OP_FRAC)
        op = op[op >= self.warmup]
        n = self.window + self.sustain - 1
        return int(op[-n]) if len(op) >= n else min(self.warmup, len(raw))

    def quality(self, raw: pd.DataFrame, stuck_min_run: int, max_conflict_frac: float) -> dict:
        reasons, detail = [], {"stuck": {}, "conflicts": {}}
        start = self.scored_from(raw)
        for s in STUCK_SIGNALS:
            col = raw[s].to_numpy(dtype=float)
            idx = np.flatnonzero(np.isfinite(col))                      # a gap does not end a constant run
            if len(idx) < 2:
                continue
            v = col[idx]
            ends = np.concatenate([np.flatnonzero(v[1:] != v[:-1]) + 1, [len(v)]])
            runs = np.diff(np.concatenate([[0], ends]))
            limit = max(stuck_min_run, int(self.max_constant_run.get(s, 0)))
            # a run longer than the limit is rejected data at the end of the window and anywhere in the rows the score uses
            # (after a stuck sensor recovers, its readings stay in the rolling means for hours)
            bad = [k for k in range(len(runs)) if runs[k] > limit and (k == len(runs) - 1 or idx[ends[k] - 1] >= start)]
            if not bad:
                continue
            k = bad[-1] if bad[-1] == len(runs) - 1 else max(bad, key=lambda j: runs[j])
            run = int(runs[k])
            detail["stuck"][s] = run
            if k == len(runs) - 1:
                reasons.append(f"stuck_signal:{s} constant for the last {run} points (longest run in training {self.max_constant_run.get(s, 0)})")
            else:
                gap = len(raw) - 1 - int(idx[ends[k] - 1])
                reasons.append(f"stuck_signal:{s} constant for {run} points ending {gap} point{'s' if gap != 1 else ''} before the "
                               f"assessment instant, inside the span the model scores (longest run in training {self.max_constant_run.get(s, 0)}); "
                               f"no score until those readings have left it")
        tail = raw.tail(self.window)
        r, g = tail["rotor_speed"].to_numpy(dtype=float), tail["generator_speed"].to_numpy(dtype=float)
        pw = np.nan_to_num(tail["active_power"].to_numpy(dtype=float), nan=0.0) / self.rated_kw
        m = np.isfinite(r) & np.isfinite(g) & (pw > OP_FRAC)
        if m.sum() >= 3:
            frac = float((np.abs(g[m] - self.speed_slope * r[m]) > self.speed_threshold).mean())
            detail["conflicts"]["rotor_speed/generator_speed"] = frac
            if frac > max_conflict_frac:
                reasons.append(f"conflicting_readings:rotor_speed/generator_speed disagree with the learned gear relation on {frac:.0%} of recent points")
        return {"ok": not reasons, "reasons": reasons, "detail": detail}

    # -- scoring ----------------------------------------------------------------------------------
    def z(self, raw: pd.DataFrame) -> tuple[dict, np.ndarray, int]:
        """Standardised residual per target and row (NaN during EWMA warm-up), operating mask, imputed cells."""
        X, op, n_imp = design(raw, self.rated_kw)
        f, _ = _fill(raw, self.targets)
        out = {}
        for t in self.targets:
            z = (f[t].to_numpy() - X @ np.asarray(self.coef[t]) - self.resid_mu[t]) / self.resid_sd[t]
            z[: self.warmup] = np.nan                                   # EWMA features not yet settled
            out[t] = z
        return out, op, n_imp

    def baseline_offsets(self, raw: pd.DataFrame) -> tuple[dict, int]:
        """Mean standardised residual per target over the operating points of a period declared healthy."""
        z, op, _ = self.z(raw)
        n = int(min(np.sum(op & np.isfinite(z[t])) for t in self.targets))
        if n < MIN_BASELINE_POINTS:
            raise CommissionError(f"only {n} operating points in the baseline period; at least {MIN_BASELINE_POINTS} are needed")
        return {t: float(np.nanmean(np.where(op, z[t], np.nan))) for t in self.targets}, n

    def scores(self, raw: pd.DataFrame, offsets: dict | None = None) -> tuple[dict, np.ndarray, int]:
        z, op, n_imp = self.z(raw)
        return {t: _rolling_mean_operating(z[t] - (offsets or {}).get(t, 0.0), op, self.window) for t in self.targets}, op, n_imp

    def score(self, raw: pd.DataFrame, baseline: dict | None = None) -> dict:
        sc, op, n_imp = self.scores(raw, baseline)
        ratio, sustained, severe = {}, [], []
        ops = np.flatnonzero(op)[-self.sustain:]          # sustain counts operating points: idle rows only carry a score forward
        for t, s in sc.items():
            r = float(s[-1] / self.thr_inspect[t]) if len(s) and np.isfinite(s[-1]) else float("nan")
            ratio[t] = r
            last = s[ops]
            if len(last) == self.sustain and np.all(np.isfinite(last)) and np.all(last > self.thr_inspect[t]):
                sustained.append(t)
                if last[-1] > self.thr_urgent[t]:
                    severe.append(t)
        finite = {t: r for t, r in ratio.items() if np.isfinite(r)}
        top = sorted(finite.items(), key=lambda kv: -kv[1])
        vec = np.ascontiguousarray([sc[t][-1] for t in self.targets], dtype=float)
        return {"point": None, "lower": None, "upper": None,
                "anomaly_score": float(top[0][1]) if top else None,             # in units of the inspect threshold
                "anomaly_sustained": bool(sustained), "anomaly_severe": bool(severe),
                "top_deviations": [[t, round(float(r), 3)] for t, r in top[:3]],
                "feature_sha256": hashlib.sha256(vec.tobytes()).hexdigest(), "n_imputed_cells": int(n_imp)}


# -- training and packaging ---------------------------------------------------------------------------------------
def _per_turbine(df: pd.DataFrame):
    for t, g in df.sort_values(["turbine", "ts_ms"]).groupby("turbine"):
        yield t, g.reset_index(drop=True)


def fit(train: pd.DataFrame, rated_kw: float = RATED_KW, ridge: float = 1e-3, val_frac: float = 0.25) -> tuple[WindNBMBundle, dict]:
    """`train`: healthy wide SCADA (turbine, ts_ms, SIGNALS). The last `val_frac` of each turbine's record is held out."""
    Xtr, Ytr, parts = [], {t: [] for t in TARGETS}, []
    for tid, g in _per_turbine(train):
        X, op, _ = design(g, rated_kw)
        f, _ = _fill(g, TARGETS)
        n_val = int(len(g) * val_frac)
        cut = len(g) - n_val
        keep = op.copy()
        keep[: WARMUP] = False
        tr = keep.copy()
        tr[cut:] = False
        Xtr.append(X[tr])
        for t in TARGETS:
            Ytr[t].append(f[t].to_numpy()[tr])
        parts.append((tid, g, cut))
    Xtr = np.vstack(Xtr)
    if len(Xtr) < 500:
        raise ValueError(f"only {len(Xtr)} healthy operating training points; need at least 500")
    lam = ridge * len(Xtr)
    A = Xtr.T @ Xtr + lam * np.diag([0.0] + [1.0] * (Xtr.shape[1] - 1))
    coef, mu, sd = {}, {}, {}
    for t in TARGETS:
        y = np.concatenate(Ytr[t])
        w = np.linalg.solve(A, Xtr.T @ y)
        r = y - Xtr @ w
        coef[t], mu[t], sd[t] = w.tolist(), float(r.mean()), float(max(r.std(), 1e-3))
    env = {s: [float(np.nanmin(train[s])), float(np.nanmax(train[s]))] for s in ENVELOPE_SIGNALS}
    runs = {s: int(max(_max_constant_run(g[s].dropna().to_numpy()) for _, g in _per_turbine(train))) for s in STUCK_SIGNALS}
    ops = train[train["active_power"] / rated_kw > OP_FRAC]
    slope = float((ops["rotor_speed"] * ops["generator_speed"]).sum() / max((ops["rotor_speed"] ** 2).sum(), 1e-9))
    sres = np.abs(ops["generator_speed"] - slope * ops["rotor_speed"])
    sthr = float(np.quantile(sres, 0.999) * 1.5 + 1e-6)
    probe = WindNBMBundle(TARGETS, coef, mu, sd, {t: 1.0 for t in TARGETS}, {t: 1.0 for t in TARGETS}, env, runs, slope, sthr, rated_kw)
    val_max, n_val_pts, train_offsets = {t: 0.0 for t in TARGETS}, 0, {}
    for tid, g, cut in parts:
        off, _ = probe.baseline_offsets(g.iloc[:cut])           # commissioned on its own training part, as in deployment
        train_offsets[tid] = off
        sc, op, _ = probe.scores(g, off)
        for t in TARGETS:
            v = sc[t][cut:]
            v = v[np.isfinite(v)]
            if len(v):
                val_max[t] = max(val_max[t], float(np.max(v)))
        n_val_pts += len(g) - cut
    thr_i = {t: max(val_max[t] * INSPECT_MARGIN, 0.5) for t in TARGETS}
    thr_u = {t: thr_i[t] * URGENT_MULT for t in TARGETS}
    bundle = WindNBMBundle(TARGETS, coef, mu, sd, thr_i, thr_u, env, runs, slope, sthr, rated_kw)
    info = {"n_train_points": int(len(Xtr)), "n_validation_points": int(n_val_pts), "healthy_validation_max_score": val_max,
            "residual_sd_degC": sd, "training_turbine_offsets_z": train_offsets}
    return bundle, info


def package_wind_nbm(train: pd.DataFrame, out_root, scope_key: str, data_class: str, source: str, seed: int = 0,
                     rated_kw: float = RATED_KW) -> Path:
    if data_class not in ("SYNTHETIC", "REAL_FIELD", "PUBLIC_REAL_FIELD", "SIMULATED"):
        raise ValueError(f"data_class {data_class!r} must say what the training data are")
    bundle, info = fit(train, rated_kw)
    val_eval = evaluate(bundle, train, labels=[], step_points=6, only_last_frac=0.25, baseline_days=None, baseline_frac=0.75)
    blob = pickle.dumps(bundle, protocol=pickle.HIGHEST_PROTOCOL)
    sha = hashlib.sha256(blob).hexdigest()
    model_id = f"wind-nbm-{sha[:10]}"
    out = Path(out_root) / model_id
    out.mkdir(parents=True, exist_ok=True)
    (out / BUNDLE_FILE).write_bytes(blob)
    manifest = {"model_id": model_id, "family": FAMILY, "version": "1", "asset_type_id": ASSET_TYPE_ID, "scope_key": scope_key,
                "prediction_kind": "anomaly", "artifact_sha256": sha, "created_at": now_iso(), "code_commit": _git_commit(), "seed": seed,
                "trained_on": {"data_class": data_class, "source": source, "n_turbines": int(train["turbine"].nunique()), "rows": int(len(train)),
                               "start": iso(int(train["ts_ms"].min())), "end": iso(int(train["ts_ms"].max()))},
                "history_points": bundle.history_points, "required_signals": bundle.required_signals, "targets": TARGETS,
                "thresholds": {"inspect": bundle.thr_inspect, "urgent": bundle.thr_urgent,
                               "rule": f"inspect = {INSPECT_MARGIN} x max healthy rolling score on the held-out last 25% of each turbine; "
                                       f"urgent = {URGENT_MULT} x inspect (policy choices, not calibrated probabilities)"},
                "envelope": bundle.envelope, "speed_relation": {"slope": bundle.speed_slope, "threshold": bundle.speed_threshold},
                "commissioning": {"required": True, "min_baseline_points": MIN_BASELINE_POINTS,
                                  "rule": "per-turbine mean standardised residual over a declared-healthy period, subtracted before thresholds"},
                "evaluation": {"protocol": "held-out healthy tail of the training turbines, each commissioned on its own training part (the "
                                           "thresholds were set on these points, so this is a consistency check, not an independent false-alarm estimate)",
                               "healthy_validation_alarm_rate": val_eval["summary"]["alarm_rate_healthy"], **info},
                "limitations": ["anomaly model: no remaining-life or failure-probability estimate",
                                "trained only on the data class named in trained_on; field performance unknown until evaluated on real data",
                                "thresholds are set from healthy data only; detection lead time depends on how the fault heats the measured component",
                                "curtailment, derating and icing are not modelled separately"]}
    (out / MANIFEST_FILE).write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    return out


def load(bundle_dir) -> WindNBMBundle:
    b = load_bundle(bundle_dir)
    if not isinstance(b, WindNBMBundle):
        raise ModelIntegrityError(f"{bundle_dir} is not a wind NBM bundle")
    return b


def gate(b: WindNBMBundle, w: pd.DataFrame, tolerance: float = 0.05, max_out_frac: float = 0.2, stuck_min_run: int = 5,
         max_conflict_frac: float = 0.2) -> str:
    """The model's gates for one window, in the assessment service's order: regime-independent data checks run even out of
    scope, and a data failure takes precedence over scope (PD-13). The platform's generic data checks, which the service
    runs first, are not part of it (`evaluate(policy=...)` adds them). Returns 'data_quality', 'out_of_scope' or 'ok'."""
    a = b.applicability(w, tolerance, max_out_frac)
    if a["in_scope"] or b.quality_independent_of_scope:
        if not b.quality(w, stuck_min_run, max_conflict_frac)["ok"]:
            return "data_quality"
    return "ok" if a["in_scope"] else "out_of_scope"


def _episodes(idx: list) -> int:
    """Runs of consecutive alarm evaluations (one episode = one sustained alarm that a person would see as one event)."""
    return sum(1 for k, i in enumerate(idx) if k == 0 or i != idx[k - 1] + 1)


def evaluate(b: WindNBMBundle, scada: pd.DataFrame, labels: list, step_points: int = 6, only_last_frac: float | None = None,
             baseline_days: float | None = 7.0, baseline_frac: float | None = None, tolerance: float = 0.05, max_out_frac: float = 0.2,
             stuck_min_run: int = 5, max_conflict_frac: float = 0.2, policy: dict | None = None) -> dict:
    """Replay assessments every `step_points` points per turbine in the assessment service's gating order (`gate`) and
    summarise alarms against labels: detection, lead time, and on healthy exposure alarm episodes per turbine-year and
    the share of assessments that could be made at all (assessability).

    `policy`: a resolved assessment policy (e.g. `policy.load(path).for_type(ASSET_TYPE_ID).assessment`). With it the replay
    gates as the service does: the platform's generic data checks (`health.generic_quality`: stale, missing and implausible
    readings, at the policy's limits) run first, and the policy's envelope, stuck and conflict limits replace the arguments.
    Without it only the model's gates run, with the arguments (their defaults are the setting pre-registered for G0).

    Commissioning: each turbine's baseline is taken from its first `baseline_days` (or first `baseline_frac` of its
    record) and scoring starts after it; `baseline_days=None` and `baseline_frac=None` evaluate the fleet model alone.
    A baseline period that overlaps a labelled fault is refused. Healthy exposure = turbines without a labelled fault.
    Exposure is reported per calendar turbine-year (every evaluation after commissioning, including those no statement
    could be made for) and per assessable turbine-year (evaluations that passed the gates); both assume 10-minute rows."""
    from .health import generic_quality
    if policy is not None:
        tolerance, max_out_frac = float(policy["envelope_tolerance"]), float(policy["max_out_of_envelope_frac"])
        stuck_min_run, max_conflict_frac = int(policy["stuck_min_run"]), float(policy["max_conflict_frac"])
    required = [s for s in SIGNALS if s not in OPTIONAL_SIGNALS]
    hp = b.history_points
    lab = {}
    for l in labels:
        lab.setdefault(l["turbine"], []).append(l)
    per, healthy_evals, healthy_alarms, healthy_eps, healthy_years, healthy_years_ok, n_all, n_ok = {}, 0, 0, 0, 0.0, 0.0, 0, 0
    for tid, g in _per_turbine(scada):
        if policy is not None:          # what the service derives from stored readings: last reading per signal, implausible values
            ts_all = g["ts_ms"].to_numpy()
            last_row = {s: pd.Series(np.where(g[s].notna(), np.arange(len(g)), np.nan)).ffill().to_numpy() for s in required}
            suspect = pd.DataFrame({s: ((g[s] < SIGNAL_META[s][1]) | (g[s] > SIGNAL_META[s][2])).astype(int) for s in required})
        offsets, b_end = None, 0
        if baseline_days is not None or baseline_frac is not None:
            ts = g["ts_ms"].to_numpy()
            b_end = int(len(g) * baseline_frac) if baseline_frac is not None else int(np.searchsorted(ts, ts[0] + baseline_days * 86_400_000))
            b_end_ms = int(ts[min(b_end, len(g) - 1)])
            if any(lb["fault_start_ms"] < b_end_ms for lb in lab.get(tid, [])):
                raise ValueError(f"baseline period of {tid} overlaps a labelled fault")
            offsets, _ = b.baseline_offsets(g.iloc[:b_end])
        start = max(hp - 1, b_end) if only_last_frac is None else max(hp - 1, b_end, int(len(g) * (1 - only_last_frac)))
        n_eval = n_scope = n_dq = 0
        alarms, alarm_idx = [], []
        for k, i in enumerate(range(start, len(g), step_points)):
            w = g.iloc[i - hp + 1: i + 1]
            n_eval += 1
            if policy is not None:
                wq = w[required].copy()
                wq.attrs["suspect"] = suspect.iloc[i - hp + 1: i + 1]
                seen = {s: int(ts_all[int(last_row[s][i])]) for s in required if np.isfinite(last_row[s][i])}
                if not generic_quality(wq, seen, required, int(ts_all[i]), policy)["ok"]:
                    n_dq += 1
                    continue
            verdict = gate(b, w, tolerance, max_out_frac, stuck_min_run, max_conflict_frac)
            if verdict == "data_quality":
                n_dq += 1
                continue
            if verdict == "out_of_scope":
                n_scope += 1
                continue
            r = b.score(w, offsets)
            if r["anomaly_sustained"]:
                alarms.append(int(g["ts_ms"].iloc[i]))
                alarm_idx.append(k)
        eps = _episodes(alarm_idx)
        years = (n_eval * step_points * 10) / (60 * 24 * 365.25)
        years_ok = ((n_eval - n_scope - n_dq) * step_points * 10) / (60 * 24 * 365.25)
        per[tid] = {"evaluations": n_eval, "out_of_scope": n_scope, "data_quality": n_dq, "alarm_points": len(alarms), "alarm_episodes": eps,
                    "first_alarm_ms": alarms[0] if alarms else None, "alarm_ms": alarms, "scored_from_ms": int(g["ts_ms"].iloc[min(start, len(g) - 1)]),
                    "scored_to_ms": int(g["ts_ms"].iloc[-1]), "baseline_offsets_z": offsets, "years": round(years, 4),
                    "assessable_years": round(years_ok, 4)}
        n_all += n_eval
        n_ok += n_eval - n_scope - n_dq
        if tid not in lab:
            healthy_evals += n_eval - n_scope - n_dq
            healthy_alarms += len(alarms)
            healthy_eps += eps
            healthy_years += years
            healthy_years_ok += years_ok
    detect = detections(per, labels)
    summary = {"alarm_rate_healthy": healthy_alarms / healthy_evals if healthy_evals else None, "healthy_assessments": healthy_evals,
               "healthy_alarm_episodes": healthy_eps, "healthy_turbine_years": round(healthy_years, 4),
               "healthy_episodes_per_turbine_year": round(healthy_eps / healthy_years, 2) if healthy_years else None,
               "healthy_assessable_turbine_years": round(healthy_years_ok, 4),
               "healthy_episodes_per_assessable_turbine_year": round(healthy_eps / healthy_years_ok, 2) if healthy_years_ok else None,
               "assessable_share": round(n_ok / n_all, 4) if n_all else None,
               "faults": len(detect), "detected": sum(d["detected"] for d in detect)}
    return {"per_turbine": per, "detections": detect, "summary": summary}


def detections(per: dict, labels: list) -> list:
    """Per labelled fault: detected if any alarm falls in [onset, failure); lead time from the first such alarm.
    Alarms before onset are counted separately (they are false alarms, not detections)."""
    out = []
    for lb in labels:
        al = per.get(lb["turbine"], {}).get("alarm_ms") or []
        inside = [t for t in al if lb["fault_start_ms"] <= t < lb["failure_ms"]]
        first = inside[0] if inside else None
        out.append({"turbine": lb["turbine"], "component": lb["component"], "detected": first is not None, "first_alarm_in_window_ms": first,
                    "lead_days": round((lb["failure_ms"] - first) / 86_400_000, 2) if first is not None else None,
                    "alarms_before_onset": sum(1 for t in al if t < lb["fault_start_ms"])})
    return out


# -- commissioning in the platform ----------------------------------------------------------------------------------
def commission(db, asset_id: str, model_id: str, start_ms: int, end_ms: int, actor: str, role: str, reason: str) -> dict:
    """Record a turbine's healthy baseline for one model from its stored readings in [start_ms, end_ms] (audited)."""
    from . import modelpack, modelreg, registry
    from .health import _window
    if role not in COMMISSIONERS:
        raise CommissionError(f"role {role!r} may not commission a baseline (allowed: {sorted(COMMISSIONERS)})")
    if not reason or not reason.strip():
        raise CommissionError("a written reason (why this period is believed healthy) is required")
    m = modelreg.get(db, model_id)
    if m is None:
        raise CommissionError(f"unknown model {model_id}")
    if m["family"] != FAMILY:
        raise CommissionError(f"model {model_id} ({m['family']}) does not use per-asset baselines")
    asset = registry.get_asset(db, asset_id)
    if asset is None or asset.asset_type_id != m["asset_type_id"]:
        raise CommissionError(f"asset {asset_id} is not a {m['asset_type_id']}")
    b = modelpack.load_bundle(m["artifact_path"], expected_sha256=m["artifact_sha256"])
    with db.connect() as c:
        n = c.execute("SELECT COUNT(DISTINCT ts_ms) FROM readings WHERE asset_id = ? AND ts_ms BETWEEN ? AND ?",
                      (asset.asset_id, start_ms, end_ms)).fetchone()[0]
    if not n:
        raise CommissionError(f"no readings for {asset_id} between {iso(start_ms)} and {iso(end_ms)}")
    win = _window(db, asset.asset_id, end_ms, int(n), list(SIGNALS))
    win = win[win["ts_ms"] >= start_ms].reset_index(drop=True)
    offsets, n_op = b.baseline_offsets(win)
    baselines = dict((asset.config or {}).get("nbm_baselines") or {})
    baselines[model_id] = {"offsets": offsets, "start": iso(start_ms), "end": iso(end_ms), "n_operating_points": n_op, "set_by": actor,
                           "set_at": now_iso(), "reason": reason}
    registry.update_asset(db, asset.asset_id, {"config": {**(asset.config or {}), "nbm_baselines": baselines}}, actor=actor,
                          reason=f"healthy baseline for {model_id}: {reason}")
    return baselines[model_id]
