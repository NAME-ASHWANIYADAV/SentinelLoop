"""Assessment service: one asset, one instant -> data-quality verdict, model scope, prediction (only when both pass),
risk, health state, and the updated asset state. Every assessment is stored with its inputs reference, the model
version and checksum, and the resolved policy, and is audited in the same transaction.

Order of checks: generic data quality (required signals present and fresh, missing and suspect shares), then model
selection (approved, checksum-verified), then scope (history length, operating envelope, regime), then model-specific
data quality (stuck sensors, conflicting redundant sensors), then scoring. A prediction is exposed only when data
quality and scope pass; otherwise the state says why and the RUL fields stay empty.
"""
from __future__ import annotations

import json
import uuid

import numpy as np
import pandas as pd

from . import auditlog, modelpack, modelreg, registry, risk as riskmod, states
from .adapters.cmapss import ms_to_cycle
from .states import AssetState, HealthState as H
from .timeutil import HOUR_MS, iso, now_iso, now_ms, parse_ts


class AssessmentError(ValueError):
    pass


_BUNDLE_CACHE: dict[str, object] = {}


def _load(model: dict):
    key = f"{model['model_id']}:{model['artifact_sha256']}"
    if key not in _BUNDLE_CACHE:
        _BUNDLE_CACHE[key] = modelpack.load_bundle(model["artifact_path"], expected_sha256=model["artifact_sha256"])
    return _BUNDLE_CACHE[key]


def _window(db, asset_id: str, as_of: int, n_points: int, signals: list[str]) -> pd.DataFrame:
    with db.connect() as c:
        ts = [r[0] for r in c.execute("SELECT DISTINCT ts_ms FROM readings WHERE asset_id = ? AND ts_ms <= ? ORDER BY ts_ms DESC LIMIT ?",
                                      (asset_id, as_of, n_points))]
        if not ts:
            return pd.DataFrame(columns=["ts_ms"] + signals)
        rows = c.execute(f"SELECT ts_ms, signal, value, quality FROM readings WHERE asset_id = ? AND ts_ms BETWEEN ? AND ? "
                         f"AND signal IN ({','.join('?' * len(signals))})", (asset_id, min(ts), max(ts), *signals)).fetchall()
    df = pd.DataFrame([tuple(r) for r in rows], columns=["ts_ms", "signal", "value", "quality"])
    wide = df.pivot_table(index="ts_ms", columns="signal", values="value", aggfunc="first").reindex(columns=signals)
    suspect = df.assign(s=(df["quality"] != "good").astype(int)).pivot_table(index="ts_ms", columns="signal", values="s", aggfunc="max")
    wide = wide.sort_index()
    wide.attrs["suspect"] = suspect.reindex(index=wide.index, columns=signals).fillna(0)
    return wide.reset_index()


def _last_seen(db, asset_id: str, as_of: int) -> dict:
    with db.connect() as c:
        return {r["signal"]: r["last"] for r in c.execute("SELECT signal, MAX(ts_ms) AS last FROM readings WHERE asset_id = ? AND ts_ms <= ? GROUP BY signal",
                                                          (asset_id, as_of))}


def _default_as_of(db, asset, atype) -> int:
    if atype.time_basis == "cycle_index":            # replayed simulation: "now" is the asset's latest reading
        with db.connect() as c:
            r = c.execute("SELECT MAX(ts_ms) FROM readings WHERE asset_id = ?", (asset.asset_id,)).fetchone()[0]
        if r is None:
            raise AssessmentError(f"asset {asset.asset_id} has no readings")
        return int(r)
    return now_ms()


def generic_quality(window: pd.DataFrame, last_seen: dict, required: list[str], as_of: int, pol: dict) -> dict:
    reasons, detail = [], {"missing_frac": {}, "suspect_frac": {}, "age_hours": {}}
    n = len(window)
    for s in required:
        last = last_seen.get(s)
        if last is None:
            reasons.append(f"missing_signal:{s} has no readings")
            continue
        age_h = (as_of - last) / HOUR_MS
        detail["age_hours"][s] = round(age_h, 3)
        if age_h > float(pol["max_data_age_hours"]):
            reasons.append(f"stale_data:{s} last reading {age_h:.1f} h before the assessment instant (limit {pol['max_data_age_hours']} h)")
        if n:
            miss = float(window[s].isna().mean())
            detail["missing_frac"][s] = round(miss, 4)
            if miss > float(pol["max_missing_frac"]):
                reasons.append(f"excessive_missing:{s} missing in {miss:.0%} of the window (limit {pol['max_missing_frac']:.0%})")
            sus = float(window.attrs["suspect"][s].mean()) if "suspect" in window.attrs else 0.0
            detail["suspect_frac"][s] = round(sus, 4)
            if sus > float(pol["max_suspect_frac"]):
                reasons.append(f"out_of_range:{s} implausible values in {sus:.0%} of the window")
    return {"ok": not reasons, "reasons": reasons, "detail": detail}


def assess(db, asset_id: str, policy, as_of_ms: int | None = None, actor: str = "system") -> dict:
    asset = registry.get_asset(db, asset_id)
    if asset is None:
        raise AssessmentError(f"unknown asset {asset_id}")
    atype = registry.get_asset_type(db, asset.asset_type_id)
    pol = policy.for_type(atype.asset_type_id)
    as_of = int(as_of_ms) if as_of_ms is not None else _default_as_of(db, asset, atype)
    required = [s.name for s in atype.signals if s.required]
    model_ok, in_scope, reasons = True, True, []
    dq_generic = {"ok": True, "reasons": [], "detail": {}}
    dq_model = {"ok": True, "reasons": [], "detail": {}}
    app = {"in_scope": True, "reasons": [], "detail": {}}
    chosen, bundle, scored, inputs = None, None, None, {"time_basis": atype.time_basis}

    approved = modelreg.approved_models(db, atype.asset_type_id)
    n_points = max([pol.assessment["min_history_points"]] + [m["manifest"].get("history_points", 1) for m in approved])
    win = _window(db, asset.asset_id, as_of, int(n_points), [s.name for s in atype.signals])
    dq_generic = generic_quality(win, _last_seen(db, asset.asset_id, as_of), required, as_of, pol.assessment)
    inputs.update({"window_start": iso(int(win["ts_ms"].min())) if len(win) else None, "window_end": iso(int(win["ts_ms"].max())) if len(win) else None,
                   "n_points": int(len(win)), "as_of": iso(as_of)})

    if not approved:
        in_scope, app = False, {"in_scope": False, "reasons": ["no_approved_model: no approved model covers this asset type"], "detail": {}}
    else:
        raw = win.copy()
        if atype.time_basis == "cycle_index":
            if not asset.installed_at:
                app = {"in_scope": False, "reasons": ["unknown_age: installed_at is required to derive the cycle count"], "detail": {}}
            raw["cycle"] = [ms_to_cycle(parse_ts(asset.installed_at), int(t), atype.usage_hours_per_cycle) for t in raw["ts_ms"]] if asset.installed_at else 0
        raw["unit"] = 0
        failures, candidate = [], None
        for m in approved:
            try:
                b = _load(m)
            except modelpack.ModelIntegrityError as e:
                failures.append(f"{m['model_id']}: {e}")
                continue
            if len(raw) < int(pol.assessment["min_history_points"]):
                a = {"in_scope": False, "reasons": [f"insufficient_history: {len(raw)} points, the policy requires {pol.assessment['min_history_points']}"],
                     "detail": {}}
            elif app.get("reasons"):
                a = app
            else:
                a = b.applicability(raw, float(pol.assessment["envelope_tolerance"]), float(pol.assessment["max_out_of_envelope_frac"]), sensors=False)
            if a["in_scope"]:
                chosen, bundle, app = m, b, a
                break
            candidate = candidate or b
            app = {"in_scope": False, "reasons": [f"{m['model_id']}: {r}" for r in a["reasons"]], "detail": a.get("detail", {})}
        baseline = None
        if bundle is not None and getattr(bundle, "needs_baseline", False):
            baseline = ((asset.config or {}).get("nbm_baselines") or {}).get(chosen["model_id"])
            if baseline is None:
                in_scope = False
                app = {"in_scope": False, "reasons": [f"{chosen['model_id']}: no_baseline: this asset has no commissioned healthy baseline for "
                                                      f"the approved model; commission one before its scores mean anything"], "detail": {}}
        if bundle is None and candidate is not None and dq_generic["ok"] and getattr(candidate, "quality_independent_of_scope", False):
            # checks that hold whatever the operating regime (e.g. a stuck temperature on an idle turbine) are still reported
            dq_model = candidate.quality(raw, int(pol.assessment["stuck_min_run"]), float(pol.assessment["max_conflict_frac"]))
        if bundle is None:
            if failures and not any(r for r in app.get("reasons", []) if "insufficient_history" in r or "operating_envelope" in r or "regime" in r):
                model_ok = False
                reasons += [f"model_unavailable: {f}" for f in failures]
            in_scope = False
        elif dq_generic["ok"] and in_scope:
            dq_model = bundle.quality(raw, int(pol.assessment["stuck_min_run"]), float(pol.assessment["max_conflict_frac"]))
            if dq_model["ok"]:
                sens = b.applicability(raw, float(pol.assessment["envelope_tolerance"]), float(pol.assessment["max_out_of_envelope_frac"]), sensors=True)
                if not sens["in_scope"]:
                    in_scope, app = False, {"in_scope": False, "reasons": [f"{chosen['model_id']}: {r}" for r in sens["reasons"]], "detail": sens["detail"]}
            if dq_model["ok"] and in_scope:
                try:
                    scored = bundle.score(raw, baseline=baseline["offsets"]) if baseline is not None else bundle.score(raw)
                except Exception as e:                      # a failed model service never produces a number
                    model_ok, scored = False, None
                    reasons.append(f"model_unavailable: scoring failed ({type(e).__name__}: {e})")
    data_ok = dq_generic["ok"] and dq_model["ok"]
    reasons += dq_generic["reasons"] + dq_model["reasons"] + ([] if in_scope else app.get("reasons", []))

    record = {"assessment_id": f"A-{uuid.uuid4().hex[:16]}", "asset_id": asset.asset_id, "as_of_ms": as_of, "created_at": now_iso(),
              "model_id": chosen["model_id"] if chosen else None, "rul_unit": None, "rul_point": None, "rul_lower": None, "rul_upper": None,
              "interval_level": None, "rul_point_hours": None, "rul_lower_hours": None, "rul_upper_hours": None, "risk": {},
              "anomaly_score": None, "anomaly_flag": None, "top_deviations": []}
    p_fail = None
    anomaly_only = bundle is not None and getattr(bundle, "prediction_kind", "rul") == "anomaly"
    if bundle is not None:
        inputs["prediction_kind"] = getattr(bundle, "prediction_kind", "rul")
    if scored is not None and data_ok and in_scope and model_ok and anomaly_only:
        record.update({"anomaly_score": scored["anomaly_score"], "anomaly_flag": scored["anomaly_sustained"], "top_deviations": scored["top_deviations"]})
        inputs["feature_sha256"] = scored["feature_sha256"]
        inputs["n_imputed_cells"] = scored["n_imputed_cells"]
    elif scored is not None and data_ok and in_scope and model_ok:
        hpc = atype.usage_hours_per_cycle if atype.time_basis == "cycle_index" else None
        conv = (lambda v: v * hpc) if hpc else (lambda v: v)
        record.update({"rul_unit": "cycles" if hpc else "hours", "rul_point": scored["point"], "rul_lower": scored["lower"], "rul_upper": scored["upper"],
                       "interval_level": bundle.interval_level, "rul_point_hours": conv(scored["point"]), "rul_lower_hours": conv(scored["lower"]),
                       "rul_upper_hours": conv(scored["upper"]), "anomaly_score": scored["anomaly_score"], "anomaly_flag": scored["anomaly_sustained"],
                       "top_deviations": scored["top_deviations"]})
        horizons = sorted(set([float(h) for h in pol.risk["horizons_hours"]] + [float(pol.risk["decision_horizon_hours"])]))
        r = riskmod.summarise(record["rul_lower_hours"], record["rul_point_hours"], record["rul_upper_hours"], bundle.interval_level,
                              conv(bundle.rul_cap), horizons)
        r["p_fail_before"] = {str(k): v for k, v in r["p_fail_before"].items()}
        r["decision_horizon_hours"] = float(pol.risk["decision_horizon_hours"])
        p_fail = r["p_fail_before"][str(float(pol.risk["decision_horizon_hours"]))]
        r["p_fail_decision_horizon"] = p_fail
        if record["rul_upper"] is not None and chosen["manifest"].get("max_width") and record["rul_upper"] - record["rul_lower"] > chosen["manifest"]["max_width"]:
            r["low_confidence"] = f"interval width {record['rul_upper'] - record['rul_lower']:.1f} exceeds the calibrated limit {chosen['manifest']['max_width']:.1f}"
        record["risk"] = r
        inputs["feature_sha256"] = scored["feature_sha256"]
        inputs["n_imputed_cells"] = scored["n_imputed_cells"]
    if chosen:
        inputs["model_artifact_sha256"] = chosen["artifact_sha256"]
    cl = states.classify(model_ok=model_ok, data_ok=data_ok, in_scope=in_scope, p_fail=p_fail,
                         sustained_anomaly=bool(record["anomaly_flag"]), thr=pol.states, reasons=reasons, anomaly_only=anomaly_only,
                         severe_anomaly=bool(scored and scored.get("anomaly_severe")))
    record.update({"health_state": cl.state.value, "reasons": list(cl.reasons), "data_quality": {"generic": dq_generic, "model": dq_model},
                   "applicability": app, "inputs": inputs, "policy": pol.to_record()})

    with db.tx() as c:
        c.execute("INSERT INTO assessments (assessment_id, asset_id, as_of_ms, created_at, model_id, health_state, reasons_json, data_quality_json, "
                  "applicability_json, rul_unit, rul_point, rul_lower, rul_upper, interval_level, rul_point_hours, rul_lower_hours, rul_upper_hours, "
                  "risk_json, anomaly_score, anomaly_flag, top_deviations_json, inputs_json, policy_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  (record["assessment_id"], record["asset_id"], as_of, record["created_at"], record["model_id"], record["health_state"],
                   json.dumps(record["reasons"]), json.dumps(record["data_quality"], default=str), json.dumps(record["applicability"], default=str),
                   record["rul_unit"], record["rul_point"], record["rul_lower"], record["rul_upper"], record["interval_level"], record["rul_point_hours"],
                   record["rul_lower_hours"], record["rul_upper_hours"], json.dumps(record["risk"]), record["anomaly_score"],
                   None if record["anomaly_flag"] is None else int(record["anomaly_flag"]), json.dumps(record["top_deviations"]),
                   json.dumps(inputs), json.dumps(record["policy"])))
        prev = _state_from_conn(c, asset.asset_id) or AssetState()
        new = states.advance(prev, cl, pol.states)
        _store_state(c, asset.asset_id, new, record["assessment_id"])
        auditlog.append(c, actor=actor, action="assessment.created", entity="assessment", entity_id=record["assessment_id"],
                        payload={"asset_id": asset.asset_id, "as_of": iso(as_of), "health_state": record["health_state"], "model_id": record["model_id"],
                                 "rul": [record["rul_lower"], record["rul_point"], record["rul_upper"]], "p_fail_decision_horizon": p_fail,
                                 "reasons": record["reasons"], "feature_sha256": inputs.get("feature_sha256"), "policy_sha256": pol.sha256,
                                 "asset_state": new.labels()}, key=db.audit_key, key_id=db.audit_key_id)
    record["asset_state"] = new.labels()
    return record


# -- asset state persistence -------------------------------------------------------------------------------------
def _state_from_conn(c, asset_id: str) -> AssetState | None:
    r = c.execute("SELECT * FROM asset_states WHERE asset_id = ?", (asset_id,)).fetchone()
    if r is None:
        return None
    return AssetState(effective=H(r["effective"]), latched_risk=r["latched_risk"], dq_failure_active=bool(r["dq_failure_active"]),
                      dq_ok_streak=int(r["dq_ok_streak"]), last_health=H(r["last_health"]) if r["last_health"] else None,
                      approval_pending=bool(r["approval_pending"]), notes=tuple(json.loads(r["notes_json"])))


def _store_state(c, asset_id: str, s: AssetState, assessment_id: str | None):
    c.execute("INSERT INTO asset_states (asset_id, effective, latched_risk, dq_failure_active, dq_ok_streak, last_health, approval_pending, notes_json, "
              "last_assessment_id, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?) ON CONFLICT(asset_id) DO UPDATE SET effective = excluded.effective, "
              "latched_risk = excluded.latched_risk, dq_failure_active = excluded.dq_failure_active, dq_ok_streak = excluded.dq_ok_streak, "
              "last_health = excluded.last_health, approval_pending = excluded.approval_pending, notes_json = excluded.notes_json, "
              "last_assessment_id = COALESCE(excluded.last_assessment_id, asset_states.last_assessment_id), updated_at = excluded.updated_at",
              (asset_id, s.effective.value, s.latched_risk, int(s.dq_failure_active), s.dq_ok_streak, s.last_health.value if s.last_health else None,
               int(s.approval_pending), json.dumps(list(s.notes)), assessment_id, now_iso()))


def asset_state(db, asset_id: str) -> AssetState | None:
    with db.connect() as c:
        return _state_from_conn(c, asset_id)


def clear_latched_risk(db, asset_id: str, event: str, actor: str, role: str, reason: str) -> AssetState:
    with db.tx() as c:
        s = _state_from_conn(c, asset_id)
        if s is None:
            raise AssessmentError(f"asset {asset_id} has never been assessed")
        new = states.clear_risk(s, event=event, actor=actor, role=role, reason=reason)
        _store_state(c, asset_id, new, None)
        auditlog.append(c, actor=actor, action=f"asset_state.{event}", entity="asset", entity_id=asset_id,
                        payload={"role": role, "reason": reason, "before": s.labels(), "after": new.labels()}, key=db.audit_key, key_id=db.audit_key_id)
    return new


def set_approval_pending(db, asset_id: str, pending: bool, c=None):
    def _do(conn):
        s = _state_from_conn(conn, asset_id) or AssetState()
        _store_state(conn, asset_id, states.set_approval_pending(s, pending), None)
    if c is not None:
        _do(c)
    else:
        with db.tx() as conn:
            _do(conn)


def latest_assessment(db, asset_id: str) -> dict | None:
    with db.connect() as c:
        r = c.execute("SELECT * FROM assessments WHERE asset_id = ? ORDER BY as_of_ms DESC, created_at DESC LIMIT 1", (asset_id,)).fetchone()
    if r is None:
        return None
    d = dict(r)
    for k in ("reasons", "data_quality", "applicability", "risk", "top_deviations", "inputs", "policy"):
        d[k] = json.loads(d.pop(f"{k}_json"))
    return d
