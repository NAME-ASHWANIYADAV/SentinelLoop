"""E4 — Drift-triggered, gated retraining (hypothesis H4).

Per subset: engines are split into validation (20%, never trained on), champion data (50%) and new
data (30%). Scenario A (accept): challenger trained on champion + new data. Scenario B (reject):
challenger trained on champion + corrupted new data (+3 sigma bias on two sensors). Gates: validation
RMSE within tolerance, PICP >= min, late-order rate not worse by > max increase. Scenario C: the
drift monitor fit on training features is checked on 20 clean test windows (false alarms) and on
regime-shifted and sensor-biased windows (true positives). Every outcome is logged to MLflow and to
artifacts/<subset>/retrain_log.json (read by the dashboard).

After the red-team review (D22): the late-rate gate is evaluated with the lower-bound policy at the CRITICAL
threshold (where late orders can occur; at the HIGH threshold nobody is late), every scenario is gated against
the SAME champion, and the registry alias is handed back to the champion after a promoting scenario, so the
scenarios are independent hypotheticals and the registry never ends on a scenario challenger.
"""
from __future__ import annotations

import argparse
import json
import time

import numpy as np
import pandas as pd

from common import ARTIFACTS, ROOT, SUBSETS, log, markdown_table, prepared, save, thresholds
from sentinelloop import agent, config, conformal, data, drift, evaluate, metrics, policy, replay, retrain, stress, tracking

MIN_LEAD = 5
SHIFT_SETTINGS = {"FD001": (35.0, 0.84, 100.0), "FD003": (35.0, 0.84, 100.0), "FD002": (50.0, 0.90, 80.0), "FD004": (50.0, 0.90, 80.0)}


split_units = retrain.split_units   # one definition, shared with the `retrain` CLI command


VAL_ROWS = 5          # rows per validation engine for the RMSE/PICP gate metrics (pre-registered: 5; secondary run: 20)
LABEL_CORRUPTION = False   # secondary scenario B2: new engines arrive with systematically wrong RUL labels (+40 cycles)
OUT_NAME = "e4_retrain_gate"


def validation_metrics(cqr, val_f: pd.DataFrame, cols, thr: agent.Thresholds, seed: int) -> dict:
    return retrain.validation_metrics(cqr, val_f, cols, thr, seed, rows_per_engine=VAL_ROWS, min_lead=MIN_LEAD)


def run_subset(subset: str, fast: bool) -> tuple[list[dict], dict]:
    cfg, ds, state, train_f, test_f, cols = prepared(subset)
    seed = int(cfg["seed"])
    thr = thresholds(cfg)
    mcfg = dict(cfg["model"])
    if fast:
        mcfg["max_iter"] = 60
    ccfg = cfg["conformal"]
    gate_cfg = cfg["gate"]
    val_u, champ_u, new_u = split_units(train_f["unit"].unique(), seed)
    val_f = train_f[train_f.unit.isin(val_u)]
    champ_f = train_f[train_f.unit.isin(champ_u)]
    new_f = train_f[train_f.unit.isin(new_u)]
    kw = dict(alpha=float(ccfg["alpha"]), calib_frac=float(ccfg["calib_frac"]), seed=seed, truncations_per_engine=int(ccfg["truncations_per_engine"]), **mcfg)

    tr = tracking.Tracker(f"sqlite:///{(ARTIFACTS / 'mlflow.db').resolve().as_posix()}", ARTIFACTS / "mlruns", experiment="sentinelloop-retrain")
    name = f"sentinelloop-{subset}-gated"
    log(f"[{subset}] champion on {len(champ_u)} engines; validation {len(val_u)}; new data {len(new_u)}")
    champ = conformal.fit_cqr(champ_f, cols, **kw)
    cm = validation_metrics(champ, val_f, cols, thr, seed)
    champ_run = tr.log_run(params={"subset": subset, "role": "champion", "n_engines": len(champ_u)}, metrics=cm, model=champ.point, model_name=name, alias="champion", tags={"subset": subset, "scenario": "champion"}, run_name=f"{subset}-champion")
    champ_version = tr.version_for_alias(name, "champion")
    rows, logbook = [], []

    def scenario(label: str, new_frame: pd.DataFrame, expect: str):
        chall = conformal.fit_cqr(pd.concat([champ_f, new_frame]), cols, **kw)
        m = validation_metrics(chall, val_f, cols, thr, seed)
        g = retrain.evaluate_gate(cm, m, gate_cfg)
        run_id = tr.log_run(params={"subset": subset, "role": "challenger", "scenario": label, "n_engines": len(champ_u) + new_frame["unit"].nunique()}, metrics={**m, "gate_passed": float(g.passed)},
                            model=chall.point, model_name=name, alias="challenger", tags={"subset": subset, "scenario": label, "gate": "PROMOTE" if g.passed else "REJECT", "reasons": "; ".join(g.reasons)}, run_name=f"{subset}-{label}")
        decision = "PROMOTE" if g.passed else "REJECT"
        if g.passed:
            tr.promote(name, tr.version_for_alias(name, "challenger"))
        promoted_version = tr.version_for_alias(name, "champion")
        entry = {"subset": subset, "scenario": label, "expected": expect, "decision": decision, "as_expected": decision == expect, "champion_rmse": cm["rmse"], "challenger_rmse": m["rmse"],
                 "champion_picp": cm["picp"], "challenger_picp": m["picp"], "champion_late_rate": cm["late_rate"], "challenger_late_rate": m["late_rate"], "reasons": "; ".join(g.reasons),
                 "champion_late_rate_high": cm["late_rate_high"], "challenger_late_rate_high": m["late_rate_high"], "late_threshold": cm["late_threshold"],
                 "mlflow_run_id": run_id, "champion_alias_version": promoted_version, "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}
        rows.append(entry)
        logbook.append({**entry, "checks": g.checks})
        log(f"[{subset}] {label}: {decision} (expected {expect}) rmse {cm['rmse']:.2f}->{m['rmse']:.2f} picp {cm['picp']:.3f}->{m['picp']:.3f} "
            f"late@{cm['late_threshold']:.0f} {cm['late_rate']:.3f}->{m['late_rate']:.3f} {g.reasons}")
        if g.passed:
            # every scenario is a hypothetical against the same champion: hand the alias back so the registry never ends on a scenario challenger
            tr.promote(name, champ_version)

    scenario("A_accept_more_data", new_f, "PROMOTE")
    # corrupted new data: +3 sigma bias on two informative sensors in the STANDARDISED feature space of the new engines
    bad = new_f.copy()
    for s in state.kept_sensors[:2]:
        bad[s] = bad[s] + 3.0
        for suffix in ("_rm",):
            if s + suffix in bad.columns:
                bad[s + suffix] = bad[s + suffix] + 3.0
    scenario("B_reject_corrupted_data", bad, "REJECT")
    if LABEL_CORRUPTION:
        # B2 (secondary): the new engines' RUL labels are systematically optimistic by 40 cycles (e.g. failure timestamps recorded late),
        # capped as usual; a challenger trained on them should predict too much life and be rejected by the RMSE or late-rate gate.
        bad2 = new_f.copy()
        bad2["rul"] = np.minimum(bad2["rul_raw"] + 40, int(cfg["rul_cap"]))
        scenario("B2_reject_label_corruption", bad2, "REJECT")

    # Scenario C: drift trigger, AGE-MATCHED (early-life rows of the fleet vs early-life rows of training engines; `cycle` is never monitored)
    window = int(cfg["features"]["window"])
    early_max = int(cfg["drift"].get("early_life_max_cycle", 50))
    mon_cols = [c for c in cols if c != "cycle"] + list(data.OS_COLS)
    ref_rows = drift.early_life_rows(train_f, warmup=window, max_cycle=early_max)
    mon = drift.DriftMonitor.fit(ref_rows[mon_cols], psi_threshold=float(cfg["drift"]["psi_threshold"]), share_threshold=float(cfg["drift"]["share_threshold"]), seed=seed,
                                 critical_columns=list(data.OS_COLS), severe_psi_threshold=float(cfg["drift"].get("severe_psi_threshold", 1.0)))
    pool = drift.early_life_rows(test_f, warmup=window, max_cycle=early_max)
    win = min(int(cfg["drift"]["window"]), len(pool))
    rng = np.random.default_rng(seed)
    idx = np.arange(len(pool))
    false_alarms = 0
    for k in range(20):
        sample = pool.iloc[np.sort(rng.choice(idx, size=win, replace=False))]
        false_alarms += int(mon.check(sample[mon_cols]).alarm)
    shifted = pool.iloc[np.sort(rng.choice(idx, size=win, replace=False))].copy()
    for c, v in zip(data.OS_COLS, SHIFT_SETTINGS[subset]):
        shifted[c] = v
    rep_shift = mon.check(shifted[mon_cols])
    biased = pool.iloc[np.sort(rng.choice(idx, size=win, replace=False))].copy()
    for s in state.kept_sensors[:2]:
        biased[s] = biased[s] + 3.0
        if s + "_rm" in biased.columns:
            biased[s + "_rm"] = biased[s + "_rm"] + 3.0
    rep_bias = mon.check(biased[mon_cols])
    drift_summary = {"false_alarms_in_20_clean_windows": false_alarms, "regime_shift_alarm": bool(rep_shift.alarm), "regime_shift_critical": rep_shift.critical_drift,
                     "bias_alarm": bool(rep_bias.alarm), "bias_severe": getattr(rep_bias, "severe_drift", []), "bias_share": rep_bias.drift_share}
    log(f"[{subset}] drift: false alarms {false_alarms}/20, regime-shift alarm {rep_shift.alarm}, bias alarm {rep_bias.alarm}")
    (ARTIFACTS / subset).mkdir(parents=True, exist_ok=True)
    # the retraining log keeps the rows of every named run (primary, secondary); re-running a run replaces only its own rows
    retrain.append_retrain_log(ARTIFACTS / subset / "retrain_log.json", OUT_NAME, logbook + [{"subset": subset, "scenario": "C_drift_trigger", **drift_summary}])
    return rows, {"champion_run": champ_run, "champion_metrics": cm, "drift": drift_summary, "splits": {"validation": val_u, "champion": champ_u, "new": new_u}}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--subsets", nargs="*", default=SUBSETS); ap.add_argument("--fast", action="store_true")
    ap.add_argument("--val-rows", type=int, default=5); ap.add_argument("--label-corruption", action="store_true"); ap.add_argument("--out", default="e4_retrain_gate")
    args = ap.parse_args()
    global VAL_ROWS, LABEL_CORRUPTION, OUT_NAME
    VAL_ROWS, LABEL_CORRUPTION, OUT_NAME = args.val_rows, args.label_corruption, args.out
    all_rows, info = [], {}
    for s in args.subsets:
        log(f"=== E4 {s} ===")
        rows, i = run_subset(s, args.fast)
        all_rows += rows
        info[s] = i
    tab = pd.DataFrame(all_rows)
    ok_gate = bool(tab["as_expected"].all())
    ok_drift = all(v["drift"]["false_alarms_in_20_clean_windows"] <= 1 and v["drift"]["regime_shift_alarm"] and v["drift"]["bias_alarm"] for v in info.values())
    conclusion = (f"H4 gates: {int(tab['as_expected'].sum())}/{len(tab)} scenario outcomes as expected (accept on more data, reject on corrupted data). "
                  f"Drift trigger: regime-shift and bias alarms fired and <=1 false alarm in 20 clean windows on all subsets: {ok_drift}. Pre-registered criterion: {'SUPPORTED' if ok_gate and ok_drift else 'NOT SUPPORTED'}.")
    readme = ("# E4 — Drift-triggered, gated retraining (H4)\n\nValidation engines 20% (never trained on), champion data 50%, new data 30%. Gates from configs/default.yaml: RMSE tolerance 2%, PICP >= 0.85, late-rate increase <= 0.02. "
              "Every champion/challenger is a registered MLflow model version (sqlite backend) with aliases; promotion moves the `champion` alias.\n\n" + markdown_table(tab.drop(columns=["ts"])) + "\n\n## Drift trigger\n```json\n"
              + json.dumps({s: v["drift"] for s, v in info.items()}, indent=1) + "\n```\n\n## Verdict\n" + conclusion + "\n")
    save(OUT_NAME, {"hypothesis": "H4", "table": tab.to_dict(orient="records"), "drift": {s: v["drift"] for s, v in info.items()}, "champion_metrics": {s: v["champion_metrics"] for s, v in info.items()},
                    "conclusion": conclusion, "fast": args.fast, "val_rows_per_engine": VAL_ROWS, "label_corruption_scenario": LABEL_CORRUPTION}, readme, {"e4_table.csv": tab})
    log(conclusion)


if __name__ == "__main__":
    main()
