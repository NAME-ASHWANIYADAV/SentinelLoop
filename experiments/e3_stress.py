"""E3 — Sensor stress and input quality (hypothesis H3).

Half of the official test engines are corrupted over their last window of cycles (missing 20%,
Gaussian noise 3 sigma, +2 sigma bias on one informative sensor, operating-regime shift); the other
half stay clean. Everything is CHANGE-RELATIVE to the clean run of the same engines, so legitimate
end-of-life anomalies on clean engines are not counted as alarms:
  detection(u)   = window quality flag OR anomaly flag newly raised OR escalation newly raised for
                   data_quality / conflicting_evidence / drift (full agent)
  false alarm(u) = the same signals on CLEAN engines (which, being unchanged, can only come from the
                   quality monitor or a fleet-level drift alarm)
  silent-wrong-order rate = corrupted engines on which an agent issues HIGH/CRITICAL without
                   escalation while the clean-data decision was different; computed for the NAIVE agent
                   (no quality/drift inputs) and the FULL agent.
Uses the artefacts produced by `python -m sentinelloop run` (clean state, CQR model, anomaly
detector, drift monitor, calibrated agent thresholds).
"""
from __future__ import annotations

import argparse
import json
import pickle

import numpy as np
import pandas as pd

from common import ARTIFACTS, ROOT, SUBSETS, log, markdown_table, save
from sentinelloop import agent, anomaly, clean, config, data, drift, evaluate, features, pipeline, stress

FAULTS = ["missing20", "noise3s", "bias2s", "regime_shift", "bias3s"]   # bias3s = SECONDARY row added after the fast FD001 diagnostic showed +2 sigma is below the per-engine floor
PRIMARY_FAULTS = ["missing20", "noise3s", "bias2s", "regime_shift"]
SHIFT_SETTINGS = {"FD001": (35.0, 0.84, 100.0), "FD003": (35.0, 0.84, 100.0), "FD002": (50.0, 0.90, 80.0), "FD004": (50.0, 0.90, 80.0)}


def load_artifacts(subset: str):
    d = ARTIFACTS / subset
    # Pickles produced by this package on this machine (see pipeline.py); never load untrusted pickles.
    with open(d / "clean_state.pkl", "rb") as fh: state = pickle.load(fh)
    with open(d / "model_cqr.pkl", "rb") as fh: cqr = pickle.load(fh)
    with open(d / "anomaly.pkl", "rb") as fh: det = pickle.load(fh)
    with open(d / "drift_monitor.pkl", "rb") as fh: mon = pickle.load(fh)
    cols = json.loads((d / "feature_manifest.json").read_text())
    thr_d = json.loads((d / "agent_thresholds.json").read_text())
    thr = agent.Thresholds(t_critical=thr_d["t_critical"], t_high=thr_d["t_high"], t_medium=thr_d["t_medium"], max_width=thr_d["max_width"], quality_max_imputed_frac=thr_d["quality_max_imputed_frac"])
    return state, cqr, det, mon, cols, thr


def process(raw_test: pd.DataFrame, state, cqr, det, mon, cols, cfg, window: int):
    imp = clean.impute(raw_test)
    alpha = float(cfg["clean"].get("ema_alpha") or 0.0)
    if alpha:
        imp = clean.ema_denoise(imp, alpha, data.SENSORS)
    c = state.transform(imp)
    f = features.build_features(c, state.kept_sensors, window)
    p, lo, hi = cqr.predict(f[cols])
    f["point"], f["lower"], f["upper"] = p, lo, hi
    f["anomaly_score"] = det.score(f[cols])
    f["anomaly_exceed"] = f["anomaly_score"] > det.threshold
    f["anomaly_flag"] = anomaly.sustained_per_unit(f, "anomaly_exceed", int(cfg["anomaly"]["sustain"]))
    last = evaluate.last_cycle_rows(f).set_index("unit")
    mon_cols = [x for x in mon.columns if x in f.columns]
    uq = pipeline.window_quality(f, mon, mon_cols, window, len(state.kept_sensors), cfg)
    early = drift.early_life_rows(f, warmup=window, max_cycle=int(cfg["drift"].get("early_life_max_cycle", 50)))
    return f, last, uq, mon_cols, early


def decide(last: pd.DataFrame, uq: dict, thr, drift_alarm: bool, use_quality: bool, subset: str):
    out = {}
    for u, row in last.iterrows():
        q = uq.get(int(u), {"flag": False, "imputed_frac": 0.0})
        obs = agent.Observation(unit=int(u), cycle=int(row["cycle"]), rul_point=float(row["point"]), rul_lower=float(row["lower"]), rul_upper=float(row["upper"]),
                                anomaly_flag=bool(row["anomaly_flag"]), anomaly_score=float(row["anomaly_score"]), drift_flag=bool(drift_alarm) if use_quality else False,
                                imputed_frac=float(q["imputed_frac"]) if use_quality else 0.0, missing_sensors=0, model_version="e3", subset=subset,
                                quality_flag=bool(q["flag"]) if use_quality else False)
        out[int(u)] = agent.triage(obs, thr)
    return out


def run_subset(subset: str, seed: int = 42) -> tuple[list[dict], dict]:
    cfg = config.load(subset, ROOT / "configs")
    window = int(cfg["features"]["window"])
    state, cqr, det, mon, cols, thr = load_artifacts(subset)
    ds = data.load_subset(subset, ROOT / "data" / "raw")
    raw = ds.test
    units = sorted(int(u) for u in raw["unit"].unique())
    rng = np.random.default_rng(seed)
    corrupted_units = sorted(int(u) for u in rng.choice(units, size=len(units) // 2, replace=False))
    clean_units = [u for u in units if u not in corrupted_units]
    last_cycle = raw.groupby("unit")["cycle"].max()
    from_cycle = {u: int(max(1, last_cycle[u] - window + 1)) for u in corrupted_units}

    f0, last0, uq0, mon_cols, early0 = process(raw, state, cqr, det, mon, cols, cfg, window)
    base_full = decide(last0, uq0, thr, drift_alarm=False, use_quality=True, subset=subset)
    base_naive = decide(last0, uq0, thr, drift_alarm=False, use_quality=False, subset=subset)
    rows, details = [], {}
    for fault in FAULTS:
        parts = []
        for u in corrupted_units:
            sub = raw[raw.unit == u]
            if fault == "missing20":
                out, _ = stress.inject_missing(sub, frac=0.20, columns=data.SENSORS, seed=seed + u, from_cycle=from_cycle[u])
            elif fault == "noise3s":
                out, _ = stress.inject_noise(sub, sigma_mult=3.0, columns=state.kept_sensors, from_cycle=from_cycle[u], seed=seed + u)
            elif fault in ("bias2s", "bias3s"):
                sensor = state.kept_sensors[(u * 7) % len(state.kept_sensors)]
                out, _ = stress.inject_bias(sub, sensor=sensor, k_std=2.0 if fault == "bias2s" else 3.0, from_cycle=from_cycle[u])
            else:
                out, _ = stress.inject_regime_shift(sub, settings=SHIFT_SETTINGS[subset], from_cycle=from_cycle[u])
            parts.append(out)
        corrupted = pd.concat(parts + [raw[raw.unit.isin(clean_units)]]).sort_values(["unit", "cycle"]).reset_index(drop=True)
        f1, last1, uq1, _, early1 = process(corrupted, state, cqr, det, mon, cols, cfg, window)
        # fleet-level drift as a real monitor would see it: the trailing window of ALL engines (clean + corrupted mix).
        # It is a fleet signal and is reported separately; per-engine detection never uses it.
        tail_all = f1[f1["cycle"] > f1.groupby("unit")["cycle"].transform("max") - window]
        rep_fleet_tail = mon.check(tail_all[mon_cols])
        rep_clean_early = mon.check(early1[early1.unit.isin(clean_units)][mon_cols])
        full = decide(last1, uq1, thr, drift_alarm=rep_fleet_tail.alarm, use_quality=True, subset=subset)
        naive = decide(last1, uq1, thr, drift_alarm=False, use_quality=False, subset=subset)
        full_no_fleet = decide(last1, uq1, thr, drift_alarm=False, use_quality=True, subset=subset)   # quality rules only: what per-engine evidence alone achieves

        def newly(u, decs, base):
            a_new = bool(last1.loc[u, "anomaly_flag"]) and not bool(last0.loc[u, "anomaly_flag"])
            esc_new = any(r in decs[u].escalation_reasons and r not in base[u].escalation_reasons for r in ("data_quality", "conflicting_evidence"))
            return bool(uq1[u]["flag"] or a_new or esc_new)

        det_rate = float(np.mean([newly(u, full, base_full) for u in corrupted_units]))
        fa_rate = float(np.mean([newly(u, full, base_full) for u in clean_units]))
        q_rate = float(np.mean([uq1[u]["flag"] for u in corrupted_units]))
        a_rate = float(np.mean([bool(last1.loc[u, "anomaly_flag"]) and not bool(last0.loc[u, "anomaly_flag"]) for u in corrupted_units]))

        def silent_wrong(decs, base):
            return float(np.mean([decs[u].severity in ("HIGH", "CRITICAL") and not decs[u].escalate_to_human and decs[u].severity != base[u].severity for u in corrupted_units]))

        def changed(decs, base):
            return float(np.mean([decs[u].severity != base[u].severity for u in corrupted_units]))

        rows.append({"subset": subset, "fault": fault, "n_corrupted": len(corrupted_units), "n_clean": len(clean_units), "detection_rate": det_rate, "false_alarm_rate": fa_rate,
                     "detect_by_quality": q_rate, "detect_by_new_anomaly": a_rate, "severity_changed_rate_naive": changed(naive, base_naive),
                     "silent_wrong_order_naive": silent_wrong(naive, base_naive), "silent_wrong_order_full": silent_wrong(full, base_full),
                     "escalation_share_full_corrupted": float(np.mean([full[u].escalate_to_human for u in corrupted_units])),
                     # the fleet-level rule escalates every HIGH/CRITICAL decision while the fleet alarm is active: its cost on the CLEAN engines and
                     # what the per-engine quality rules achieve without it are reported so the headline zero is not mistaken for per-engine detection
                     "escalation_share_full_clean": float(np.mean([full[u].escalate_to_human for u in clean_units])),
                     "escalation_share_base_clean": float(np.mean([base_full[u].escalate_to_human for u in clean_units])),
                     "silent_wrong_order_full_no_fleet_rule": silent_wrong(full_no_fleet, base_full),
                     "fleet_drift_alarm_mixed_tail": bool(rep_fleet_tail.alarm), "fleet_drift_alarm_clean_early": bool(rep_clean_early.alarm),
                     "fleet_drift_reasons": ",".join(rep_fleet_tail.reasons),
                     "rmse_shift_point_corrupted": float(np.sqrt(np.mean((last1.loc[corrupted_units, "point"] - last0.loc[corrupted_units, "point"]) ** 2)))})
        details[fault] = {"escalation_reasons_full": pd.Series([r for u in corrupted_units for r in full[u].escalation_reasons]).value_counts().to_dict()}
    return rows, details


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--subsets", nargs="*", default=SUBSETS)
    args = ap.parse_args()
    all_rows, det = [], {}
    for s in args.subsets:
        log(f"=== E3 {s} ===")
        rows, d = run_subset(s)
        all_rows += rows
        det[s] = d
    tab = pd.DataFrame(all_rows)
    tab["reduction_silent_wrong"] = np.where(tab["silent_wrong_order_naive"] > 0, 1 - tab["silent_wrong_order_full"] / tab["silent_wrong_order_naive"], np.nan)
    tab["H3_detect_ok"] = tab["detection_rate"] >= 0.90
    tab["H3_fa_ok"] = tab["false_alarm_rate"] <= 0.05
    tab["H3_swo_ok"] = (tab["reduction_silent_wrong"] >= 0.5) | (tab["silent_wrong_order_naive"] == 0)
    by_fault = tab.groupby("fault")[["H3_detect_ok", "H3_fa_ok", "H3_swo_ok"]].all()
    prim = by_fault.loc[[f for f in PRIMARY_FAULTS if f in by_fault.index]]
    n_ok = int(prim.all(axis=1).sum())
    conclusion = (f"H3 pre-registered faults fully passing (detect>=0.90, false-alarm<=0.05, silent-wrong-order reduced>=50%): {n_ok}/{len(prim)}. Per fault: "
                  + "; ".join(f"{f}: detect {'ok' if r.H3_detect_ok else 'FAIL'}, false-alarm {'ok' if r.H3_fa_ok else 'FAIL'}, silent-wrong-order {'ok' if r.H3_swo_ok else 'FAIL'}" for f, r in by_fault.iterrows())
                  + ". bias3s is a secondary row (added after the fast diagnostic). Fleet-level drift alarms are reported separately.")
    readme = ("# E3 — Sensor stress and input quality (H3)\n\nHalf of the official test engines are corrupted over their last 20 cycles; the other half stay clean. All signals are change-relative to the clean run of the same engines. "
              "Detection = window quality flag OR newly raised sustained anomaly OR newly raised escalation (data_quality / conflicting_evidence / drift). Silent-wrong-order = HIGH/CRITICAL issued without escalation that differs from the clean decision; 'naive' agent ignores quality/drift inputs, 'full' agent uses them.\n\n"
              + markdown_table(tab) + "\n\n## Verdict\n" + conclusion + "\n\nEscalation reasons on corrupted engines (full agent):\n```json\n" + json.dumps(det, indent=1) + "\n```\n")
    save("e3_stress", {"hypothesis": "H3", "table": tab.to_dict(orient="records"), "by_fault": by_fault.reset_index().to_dict(orient="records"), "reasons": det, "conclusion": conclusion}, readme, {"e3_table.csv": tab})
    log(conclusion)


if __name__ == "__main__":
    main()
