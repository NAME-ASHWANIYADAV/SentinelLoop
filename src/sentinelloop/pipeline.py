"""End-to-end run: data -> clean -> features -> models (point + CQR) -> anomaly -> drift -> agent ->
work orders -> audit -> SQLite -> MLflow -> artefacts. One command, no manual steps."""
from __future__ import annotations

import json
import pickle
import sqlite3
import time
from collections import defaultdict, deque
from pathlib import Path

import numpy as np
import pandas as pd

from . import agent, anomaly, audit, baseline, clean, config, conformal, data, drift, evaluate, features, metrics, models, stream, targets


def _json_dump(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=1, default=str), encoding="utf-8")


def write_sqlite(db_path: Path, subset: str, audit_records: list[dict], orders: list[dict], run_meta: dict) -> None:
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS decisions (seq INTEGER, ts TEXT, subset TEXT, unit INTEGER, cycle INTEGER, severity TEXT, action TEXT,
                   escalate INTEGER, reasons TEXT, rules TEXT, rul_point REAL, rul_lower REAL, rul_upper REAL, anomaly_score REAL, anomaly_flag INTEGER,
                   drift_flag INTEGER, imputed_frac REAL, model_version TEXT, mode TEXT, hash TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS work_orders (id INTEGER, subset TEXT, unit INTEGER, type TEXT, severity TEXT, status TEXT, created_cycle INTEGER,
                   updated_cycle INTEGER, reasons TEXT, model_version TEXT, n_decisions INTEGER, mode TEXT)""")
    cur.execute("CREATE TABLE IF NOT EXISTS runs (subset TEXT, run_id TEXT, ts TEXT, config_hash TEXT, metrics_json TEXT)")
    cur.execute("DELETE FROM decisions WHERE subset=?", (subset,))
    cur.execute("DELETE FROM work_orders WHERE subset=?", (subset,))
    for r in audit_records:
        i = r["inputs"]
        cur.execute("INSERT INTO decisions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (r["seq"], r["ts"], subset, r["unit"], r["cycle"], r["severity"], r["action"], int(r["escalate_to_human"]),
                     ",".join(r["escalation_reasons"]), ",".join(r["rules_fired"]), i["rul_point"], i["rul_lower"], i["rul_upper"],
                     i["anomaly_score"], int(i["anomaly_flag"]), int(i["drift_flag"]), i["imputed_frac"], r["model_version"],
                     (r.get("extra") or {}).get("mode", ""), r["hash"]))
    for o in orders:
        cur.execute("INSERT INTO work_orders VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (o["id"], subset, o["unit"], o["type"], o["severity"], o["status"], o["created_cycle"], o["updated_cycle"],
                     ",".join(o.get("reasons", [])), o.get("model_version", ""), o.get("n_decisions", 1), o.get("mode", "")))
    cur.execute("INSERT INTO runs VALUES (?,?,?,?,?)", (subset, run_meta.get("run_id", ""), run_meta.get("ts", ""), run_meta.get("config_hash", ""), json.dumps(run_meta.get("metrics", {}), default=str)))
    con.commit()
    con.close()


def observation_from_row(row, subset: str, model_version: str, drift_flag: bool, n_sensors: int, quality_flag: bool = False, imputed_frac: float | None = None,
                         top_sensors: list[str] | None = None) -> agent.Observation:
    imp = float(row.get("n_imputed", 0)) / max(1, n_sensors) if imputed_frac is None else float(imputed_frac)
    return agent.Observation(unit=int(row["unit"]), cycle=int(row["cycle"]), rul_point=float(row["point"]), rul_lower=float(row["lower"]),
                             rul_upper=float(row["upper"]), anomaly_flag=bool(row["anomaly_flag"]), anomaly_score=float(row["anomaly_score"]),
                             drift_flag=bool(drift_flag), imputed_frac=imp, missing_sensors=int(row.get("missing_sensors", 0)),
                             model_version=model_version, subset=subset, quality_flag=bool(quality_flag), top_sensors=list(top_sensors or []))


def window_quality(f: pd.DataFrame, mon: "drift.DriftMonitor", mon_cols: list[str], window: int, n_sensors: int, cfg: dict) -> dict[int, dict]:
    """Per-unit input quality over the trailing `window` cycles: imputed fraction, missing/out-of-range fractions, flag."""
    tail = f[f["cycle"] > f.groupby("unit")["cycle"].transform("max") - window]
    a = cfg["agent"]
    out: dict[int, dict] = {}
    for u, g in tail.groupby("unit"):
        q = mon.quality(g[mon_cols])
        imp = float(g["n_imputed"].mean()) / max(1, n_sensors) if "n_imputed" in g.columns else 0.0
        flag = bool(imp > float(a["quality_max_imputed_frac"]) or q["missing_frac"] > float(a["quality_max_imputed_frac"])
                    or q["out_of_range_frac"] > float(a.get("quality_max_out_of_range_frac", 0.05))
                    or q.get("critical_out_of_range_frac", 0.0) > float(a.get("quality_max_critical_out_of_range_frac", 0.5)))
        out[int(u)] = {"imputed_frac": imp, "missing_frac": q["missing_frac"], "out_of_range_frac": q["out_of_range_frac"],
                       "critical_out_of_range_frac": q.get("critical_out_of_range_frac", 0.0), "flag": flag}
    return out


class StreamQuality:
    """Stream-mode counterpart of `window_quality`: per unit, the trailing `window` feature rows are kept and the same
    imputed / missing / out-of-range / critical-setting rules are applied after every cycle."""

    def __init__(self, mon: "drift.DriftMonitor", mon_cols: list[str], window: int, n_sensors: int, cfg: dict):
        self.mon, self.mon_cols, self.window, self.n_sensors, self.a = mon, list(mon_cols), int(window), max(1, int(n_sensors)), cfg["agent"]
        self.buf: dict[int, deque] = defaultdict(lambda: deque(maxlen=self.window))

    def update(self, row: dict) -> dict:
        u = int(row["unit"])
        self.buf[u].append({c: row.get(c, np.nan) for c in self.mon_cols + ["n_imputed"]})
        g = pd.DataFrame(list(self.buf[u]))
        q = self.mon.quality(g[self.mon_cols])
        imp = float(g["n_imputed"].fillna(0).mean()) / self.n_sensors
        flag = bool(imp > float(self.a["quality_max_imputed_frac"]) or q["missing_frac"] > float(self.a["quality_max_imputed_frac"])
                    or q["out_of_range_frac"] > float(self.a.get("quality_max_out_of_range_frac", 0.05))
                    or q.get("critical_out_of_range_frac", 0.0) > float(self.a.get("quality_max_critical_out_of_range_frac", 0.5)))
        return {"imputed_frac": imp, "missing_frac": q["missing_frac"], "out_of_range_frac": q["out_of_range_frac"],
                "critical_out_of_range_frac": q.get("critical_out_of_range_frac", 0.0), "flag": flag}


def run(subset: str, data_dir="data/raw", out_dir="artifacts", config_dir="configs", fast: bool = False, stream_units: int = 5,
        mlflow: bool = True, seed: int | None = None, log=print) -> dict:
    t0 = time.time()
    cfg = config.load(subset, config_dir)
    if seed is not None:
        cfg["seed"] = int(seed)
    seed = int(cfg["seed"])
    mcfg = dict(cfg["model"])
    if fast:
        mcfg["max_iter"] = 60
    out_root = Path(out_dir)
    out = out_root / subset
    out.mkdir(parents=True, exist_ok=True)
    cap = int(cfg["rul_cap"])
    window = int(cfg["features"]["window"])

    log(f"[{subset}] loading and preparing data")
    ds = data.load_subset(subset, data_dir)
    state, train_f, test_f, cols = baseline.prepare_frames(ds, cfg)
    y = train_f["rul"].to_numpy()

    log(f"[{subset}] training point model (all engines) and CQR interval model (70/30 engine split)")
    hgbr_all = models.train_point_model(train_f[cols], y, seed=seed, **mcfg)
    ccfg = cfg["conformal"]
    cqr = conformal.fit_cqr(train_f, cols, alpha=float(ccfg["alpha"]), calib_frac=float(ccfg["calib_frac"]), seed=seed,
                            truncations_per_engine=int(ccfg["truncations_per_engine"]), **mcfg)

    log(f"[{subset}] fitting anomaly detector and drift monitor on training data")
    acfg = cfg["anomaly"]
    det = anomaly.AnomalyDetector.fit(train_f, cols, healthy_frac=float(acfg["healthy_frac"]), threshold_pct=float(acfg["threshold_pct"]), seed=seed, warmup=window,
                                      top_k=int(acfg.get("top_k", 3)))
    dcfg = cfg["drift"]
    # Age-matched drift monitoring: early-life rows of training engines vs early-life rows of the current fleet (never `cycle` itself).
    mon_cols = [c for c in cols if c != "cycle"] + [c for c in data.OS_COLS if c in train_f.columns]
    early_max = int(dcfg.get("early_life_max_cycle", 50))
    ref_rows = drift.early_life_rows(train_f, warmup=window, max_cycle=early_max)
    mon = drift.DriftMonitor.fit(ref_rows[mon_cols], psi_threshold=float(dcfg["psi_threshold"]), share_threshold=float(dcfg["share_threshold"]), seed=seed,
                                 critical_columns=list(data.OS_COLS), severe_psi_threshold=float(dcfg.get("severe_psi_threshold", 1.0)),
                                 range_ref=train_f[mon_cols])

    # ---- predictions on every test row (needed for stream-equivalent batch decisions), metrics at last cycles
    point, lower, upper = cqr.predict(test_f[cols])
    test_f = test_f.copy()
    test_f["point"], test_f["lower"], test_f["upper"] = point, lower, upper
    test_f["point_all_engines"] = hgbr_all.predict(test_f[cols])
    test_f["anomaly_score"] = det.score(test_f[cols])
    test_f["anomaly_exceed"] = test_f["anomaly_score"] > det.threshold
    test_f["anomaly_flag"] = anomaly.sustained_per_unit(test_f, "anomaly_exceed", int(acfg["sustain"]))
    drift_report = mon.check(drift.early_life_rows(test_f, warmup=window, max_cycle=early_max)[mon_cols])
    quality = mon.quality(test_f[mon_cols])
    n_sensors = len(state.kept_sensors)
    unit_quality = window_quality(test_f, mon, mon_cols, window, n_sensors, cfg)
    thr = agent.Thresholds.from_config(cfg, auto_max_width=cqr.suggested_max_width)

    last = evaluate.last_cycle_rows(test_f)
    truth_capped, truth_raw = targets.test_truth(ds.rul, cap)
    m: dict = {"subset": subset, "n_test_units": int(len(truth_raw)), "rul_cap": cap, "fast": fast, "seed": seed}
    for name, p in (("hgbr", last["point_all_engines"].to_numpy()), ("cqr_point", last["point"].to_numpy())):
        m[f"{name}_rmse_capped"] = metrics.rmse(truth_capped, p)
        m[f"{name}_rmse_raw"] = metrics.rmse(truth_raw, p)
        m[f"{name}_phm08"] = metrics.phm08_score(truth_capped, p)
    m["picp_test_capped"] = metrics.picp(truth_capped, last["lower"], last["upper"])
    m["picp_test_raw"] = metrics.picp(truth_raw, last["lower"], last["upper"])
    m["mpiw_test"] = metrics.mpiw(last["lower"], last["upper"])
    m["conformal_qhat"] = float(cqr.qhat)
    m["agent_max_width"] = float(thr.max_width)
    m["agent_thresholds"] = {"t_critical": thr.t_critical, "t_high": thr.t_high, "t_medium": thr.t_medium, "max_width": thr.max_width, "quality_max_imputed_frac": thr.quality_max_imputed_frac}
    m["quality_flag_rate_test"] = float(np.mean([q["flag"] for q in unit_quality.values()])) if unit_quality else 0.0
    m["anomaly_threshold"] = float(det.threshold)
    m["anomaly_flag_rate_test_last_cycle"] = float(last["anomaly_flag"].mean())
    m["drift_share_test"] = float(drift_report.drift_share)
    m["drift_alarm_test"] = bool(drift_report.alarm)
    m["quality_test"] = quality
    m["phm08_convention"] = metrics.PHM08_CONVENTION
    m["data_hashes"] = data.file_hashes(subset, data_dir)
    m["config_hash"] = config.config_hash(cfg)
    m["dropped_sensors"] = state.dropped_sensors
    m["n_features"] = len(cols)

    # ---- MLflow (SQLite backend) first, so decisions can reference the model version
    run_id = "local"
    if mlflow:
        from . import tracking
        tr = tracking.Tracker(f"sqlite:///{(out_root / 'mlflow.db').resolve().as_posix()}", out_root / "mlruns", experiment="sentinelloop")
        numeric = {k: v for k, v in m.items() if isinstance(v, (int, float)) and not isinstance(v, bool)}
        run_id = tr.log_run(params={"subset": subset, "config_hash": m["config_hash"], "rul_cap": cap, "window": window, "alpha": ccfg["alpha"],
                                    "calib_frac": ccfg["calib_frac"], "max_iter": mcfg["max_iter"], "n_features": len(cols), "seed": seed,
                                    "data_sha256_train": m["data_hashes"]["train"][:16]},
                            metrics=numeric, model=cqr.point, model_name=f"sentinelloop-{subset}", alias="champion",
                            tags={"subset": subset, "stage": "pipeline", "fast": str(fast)},
                            artifacts={"feature_manifest.json": json.dumps(cols), "conformal.json": json.dumps(cqr.metadata())}, run_name=f"{subset}-pipeline")
        m["mlflow_run_id"] = run_id
        m["model_alias"] = "champion"
        m["mlflow_tracking_uri"] = tr.tracking_uri
    else:
        m["mlflow_run_id"] = run_id
        m["model_alias"] = "none"

    # ---- agent on the last observed cycle of every test engine (batch decisions)
    log(f"[{subset}] running the Triage Agent on {len(last)} test engines (batch) and {stream_units} engines (stream); max_width {thr.max_width:.1f}")
    audit_path = out_root / "audit" / f"decisions_{subset}.jsonl"   # one chained log per subset; a re-run of a subset starts its log afresh
    if audit_path.exists():
        audit_path.unlink()
    alog = audit.AuditLog(audit_path)
    book = agent.WorkOrderBook()
    dec_rows = []
    top_last = [[name for name, _ in t] for t in det.top_deviations(last[cols], n=3)]   # explainability: the features driving the health index
    for (_, row), tops in zip(last.iterrows(), top_last):
        uq = unit_quality.get(int(row["unit"]), {"flag": False, "imputed_frac": 0.0})
        obs = observation_from_row(row, subset, run_id, drift_report.alarm, n_sensors, quality_flag=uq["flag"], imputed_frac=uq["imputed_frac"], top_sensors=tops)
        d = agent.triage(obs, thr)
        rec = alog.append(d, extra={"mode": "batch"})
        ev = book.apply(d)
        dec_rows.append({"unit": d.unit, "cycle": d.cycle, "severity": d.severity, "action": d.action, "escalate": d.escalate_to_human,
                         "reasons": "|".join(d.escalation_reasons), "rules": "|".join(d.rules_fired), "rul_point": obs.rul_point,
                         "rul_lower": obs.rul_lower, "rul_upper": obs.rul_upper, "rul_true_capped": None, "anomaly_score": obs.anomaly_score,
                         "anomaly_flag": obs.anomaly_flag, "order_event": ev["event"], "seq": rec["seq"],
                         "imputed_frac": obs.imputed_frac, "quality_flag": obs.quality_flag, "drift_flag": obs.drift_flag, "top_sensors": "|".join(tops)})
    dec = pd.DataFrame(dec_rows)
    dec["rul_true_capped"] = truth_capped
    dec["rul_true_raw"] = truth_raw
    dec.to_csv(out / "decisions_test.csv", index=False)
    m["severity_counts_test"] = dec["severity"].value_counts().to_dict()
    m["escalation_share_test"] = float(dec["escalate"].mean())
    m["decision_outcomes_test"] = evaluate.decision_outcomes(dec, thr.t_critical, thr.t_high, thr.t_medium)
    batch_orders = [dict(o, mode="batch") for o in book.open_orders()]

    # ---- stream replay of a few engines, cycle by cycle, through the same cleaning/feature/agent code
    stream_rows = []
    sbook = agent.WorkOrderBook()
    if stream_units > 0:
        units = sorted(ds.test["unit"].unique())[:stream_units]
        raw = ds.test[ds.test["unit"].isin(units)]
        cs = stream.CleanStream(state, ema_alpha=float(cfg["clean"].get("ema_alpha") or 0.0))
        fs = stream.FeatureStream(state.kept_sensors, window)
        sq = StreamQuality(mon, mon_cols, window, n_sensors, cfg)
        run_len: dict[int, int] = {}
        for _, row in raw.sort_values(["cycle", "unit"]).iterrows():
            crow = cs.update(row)
            feat = fs.update(crow)
            X = pd.DataFrame([feat])[cols]
            p_, lo_, hi_ = cqr.predict(X)
            sc = float(det.score(X)[0])
            u = int(feat["unit"])
            run_len[u] = run_len.get(u, 0) + 1 if sc > det.threshold else 0
            flag = run_len[u] >= int(acfg["sustain"])
            srow = {"unit": u, "cycle": int(feat["cycle"]), "point": float(p_[0]), "lower": float(lo_[0]), "upper": float(hi_[0]),
                    "anomaly_score": sc, "anomaly_flag": flag, "n_imputed": int(feat.get("n_imputed", 0))}
            uq = sq.update(feat)
            tops = [name for name, _ in det.top_deviations(X, n=3)[0]]
            # the fleet drift state is the latest fleet-level check (here the batch check of this run); one engine's stream cannot measure fleet drift
            d = agent.triage(observation_from_row(srow, subset, run_id, drift_report.alarm, n_sensors, quality_flag=uq["flag"], imputed_frac=uq["imputed_frac"], top_sensors=tops), thr)
            alog.append(d, extra={"mode": "stream"})
            ev = sbook.apply(d)
            srow.update({"severity": d.severity, "action": d.action, "escalate": d.escalate_to_human, "order_event": ev["event"],
                         "reasons": "|".join(d.escalation_reasons), "imputed_frac": uq["imputed_frac"], "quality_flag": uq["flag"], "drift_flag": bool(drift_report.alarm)})
            stream_rows.append(srow)
        pd.DataFrame(stream_rows).to_csv(out / "decisions_stream.csv", index=False)
    stream_orders = [dict(o, mode="stream") for o in sbook.open_orders()]
    all_orders = batch_orders + stream_orders
    _json_dump(out / "work_orders.json", all_orders)
    m["n_work_orders_batch"] = len(batch_orders)
    m["n_work_orders_stream"] = len(stream_orders)
    m["audit_chain_valid"] = alog.verify_chain()
    m["audit_records"] = alog.n
    m["audit_terminal_hash"] = alog.records()[-1]["hash"] if alog.n else audit.GENESIS   # external anchor: a truncated log no longer ends on this hash

    # ---- artefacts
    m["elapsed_s"] = round(time.time() - t0, 1)
    if mlflow and run_id != "local":
        tr.log_metrics(run_id, {k: m[k] for k in ("escalation_share_test", "quality_flag_rate_test", "n_work_orders_batch", "n_work_orders_stream", "audit_records", "elapsed_s") if k in m})
        tr.set_tags(run_id, {"audit_terminal_hash": m["audit_terminal_hash"], "audit_records": str(m["audit_records"])})
    preds = test_f[["unit", "cycle", "point", "lower", "upper", "point_all_engines", "anomaly_score", "anomaly_flag"]]
    preds.to_csv(out / "predictions_test_all_cycles.csv", index=False)
    lastp = last[["unit", "cycle", "point", "lower", "upper", "point_all_engines", "anomaly_score", "anomaly_flag"]].copy()
    lastp["rul_true_capped"], lastp["rul_true_raw"] = truth_capped, truth_raw
    lastp.to_csv(out / "predictions_test.csv", index=False)
    _json_dump(out / "metrics.json", m)
    _json_dump(out / "conformal.json", cqr.metadata())
    _json_dump(out / "anomaly.json", {"method": det.method, "threshold": det.threshold, "columns": det.columns, "healthy_frac": det.healthy_frac,
                                       "threshold_pct": det.threshold_pct, "top_k": det.top_k, "warmup": det.warmup})
    _json_dump(out / "drift_reference.json", {"test_window": drift_report.to_dict(), "quality": quality, "psi_threshold": mon.psi_threshold, "share_threshold": mon.share_threshold,
                                               "age_matched_window": {"warmup": window, "max_cycle": early_max}, "unit_quality_flag_rate": m["quality_flag_rate_test"]})
    _json_dump(out / "agent_thresholds.json", m["agent_thresholds"])
    _json_dump(out / "feature_manifest.json", cols)
    # Pickled artefacts are produced and consumed only by this package on this machine.
    for name, obj in (("clean_state.pkl", state), ("model_point.pkl", hgbr_all), ("model_cqr.pkl", cqr), ("anomaly.pkl", det), ("drift_monitor.pkl", mon)):
        with open(out / name, "wb") as fh:
            pickle.dump(obj, fh)
    write_sqlite(out_root / "sentinelloop.db", subset, alog.records(), all_orders, {"run_id": run_id, "ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "config_hash": m["config_hash"], "metrics": {k: v for k, v in m.items() if isinstance(v, (int, float, str))}})
    log(f"[{subset}] done in {m['elapsed_s']} s: HGBR RMSE {m['hgbr_rmse_capped']:.2f} capped / {m['hgbr_rmse_raw']:.2f} raw, PICP {m['picp_test_capped']:.3f}, MPIW {m['mpiw_test']:.1f}, orders {len(all_orders)}, escalation share {m['escalation_share_test']:.2f}")
    return {"metrics": m, "state": state, "cqr": cqr, "hgbr": hgbr_all, "detector": det, "monitor": mon, "columns": cols,
            "train": train_f, "test": test_f, "decisions": dec, "orders": all_orders, "config": cfg, "dataset": ds}
