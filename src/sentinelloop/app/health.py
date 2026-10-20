"""Assessment service: one asset, one instant -> data-quality verdict, model scope, prediction (only when both pass),
risk, health state, and the updated asset state. Every assessment is stored with its inputs reference, the model
version and checksum, and the resolved policy, and is audited in the same transaction.

Order of checks: generic data quality (required signals present and fresh, missing and suspect shares), then model
selection (approved, checksum-verified), then scope (history length, operating envelope, regime), then model-specific
data quality (stuck sensors, conflicting redundant sensors), then scoring. A prediction is exposed only when data
quality and scope pass; otherwise the state says why and the RUL fields stay empty. Model checks that do not depend on
the regime run even out of scope (no model in scope, or no commissioned baseline), so a data failure takes precedence.

Instants: an assessment instant later than now (plus a small clock skew), earlier than MIN_AS_OF_MS (2000-01-01T00:00Z)
or earlier than the asset's first reading (minus the same skew) is refused; `assess_range` checks every instant before it
applies any. An assessment for an instant at or before the last one applied to the asset is stored as a historical replay
(applied_to_state = 0): it never moves the live state, and `latest_assessment` ignores it. Replays therefore cannot
silence recommendations or clear a data failure; a forward replay after a data gap (oldest instant first) is applied
normally. Latching is monotone toward more risk, so a replay that is URGENT_REVIEW or INSPECTION_RECOMMENDED still
raises the latched risk (states.escalate), and says so in its reasons and in the audit log; unless an earlier assessment
for the same instant already had that finding, which a person has cleared since (the scheduled job on an export-fed site
assesses the same latest reading until the next export, and must not undo a dismissal or a completed inspection).
"""
from __future__ import annotations

import json
import logging
import uuid

import numpy as np
import pandas as pd

from . import auditlog, modelpack, modelreg, registry, risk as riskmod, states
from .adapters.cmapss import ms_to_cycle
from .states import AssetState, HealthState as H
from .timeutil import HOUR_MS, iso, now_iso, now_ms, parse_ts


class AssessmentError(ValueError):
    pass


log = logging.getLogger("sentinelloop.health")
MAX_FUTURE_SKEW_MS = 5 * 60 * 1000
MIN_AS_OF_MS = parse_ts("2000-01-01T00:00:00Z")     # no monitored record predates it; also keeps every instant displayable
MAX_RANGE_STEPS = 2000
DQ_CODES = ("missing_signal", "stale_data", "excessive_missing", "out_of_range", "stuck_signal", "conflicting_readings", "data_delivery_delay")


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


def _default_as_of(db, asset, atype, pol=None) -> int:
    latest = pol is not None and pol.assessment.get("assess_at", "now") == "latest_reading"
    if atype.time_basis == "cycle_index" or latest:   # replayed simulation, or a site that delivers periodic exports
        with db.connect() as c:
            r = c.execute("SELECT MAX(ts_ms) FROM readings WHERE asset_id = ?", (asset.asset_id,)).fetchone()[0]
        if r is None:
            raise AssessmentError(f"asset {asset.asset_id} has no readings")
        return int(r)
    return now_ms()


def _check_instants(db, asset, instants) -> None:
    """Refuse instants no assessment can be for: later than now plus the clock skew, before MIN_AS_OF_MS, or before the
    asset's first reading (no window can hold any of its data) by more than the same skew, which ingest also allows for
    device clocks (a new asset whose first readings are a little ahead can still be assessed now). Raises before anything
    is stored."""
    with db.connect() as c:
        first = c.execute("SELECT MIN(ts_ms) FROM readings WHERE asset_id = ?", (asset.asset_id,)).fetchone()[0]
    latest = now_ms() + MAX_FUTURE_SKEW_MS
    for t in instants:
        if t > latest:
            raise AssessmentError(f"assessment instant {iso(t)} is in the future; assessments are for now or the past")
        if t < MIN_AS_OF_MS:
            raise AssessmentError(f"assessment instant {iso(t)} is before {iso(MIN_AS_OF_MS)}, the earliest instant the platform assesses")
        if first is not None and t < first - MAX_FUTURE_SKEW_MS:
            raise AssessmentError(f"assessment instant {iso(t)} is before the first reading of {asset.asset_id} ({iso(first)}); "
                                  f"no window can hold its data")


def generic_quality(window: pd.DataFrame, last_seen: dict, required: list[str], as_of: int, pol: dict) -> dict:
    reasons, detail = [], {"missing_frac": {}, "suspect_frac": {}, "age_hours": {}}
    n = len(window)
    limit = float(pol["max_data_age_hours"])
    ages = {s: (as_of - last_seen[s]) / HOUR_MS for s in required if last_seen.get(s) is not None}
    if required and len(ages) == len(required) and all(a > limit for a in ages.values()):
        # every required signal stopped together: the feed is late, not the sensors (a data-path problem, not a site job)
        detail["age_hours"] = {s: round(a, 3) for s, a in ages.items()}
        return {"ok": False, "reasons": [f"data_delivery_delay: no reading for any required signal in the last {min(ages.values()):.1f} h before the "
                                         f"assessment instant (limit {limit} h); check the data feed, not the asset"], "detail": detail}
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
    as_of = int(as_of_ms) if as_of_ms is not None else _default_as_of(db, asset, atype, pol)
    _check_instants(db, asset, [as_of])
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
                log.warning("model %s unavailable: %s", m["model_id"], e)      # details (paths) stay in the server log
                failures.append(m["model_id"])
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
        if failures:            # an integrity failure is always reported, whatever the other models' scope (precedence: model first)
            reasons += [f"model_unavailable: {f}: artefact missing or failed its integrity check (details in the server log)" for f in failures]
        if bundle is None:
            if failures:
                model_ok = False
            in_scope = False
        elif dq_generic["ok"] and (in_scope or getattr(bundle, "quality_independent_of_scope", False)):
            # model data checks come before the no-baseline scope decision (PD-13): a stuck sensor on an uncommissioned turbine
            # is a data failure, not a scope statement
            dq_model = bundle.quality(raw, int(pol.assessment["stuck_min_run"]), float(pol.assessment["max_conflict_frac"]))
            if dq_model["ok"] and in_scope:
                sens = b.applicability(raw, float(pol.assessment["envelope_tolerance"]), float(pol.assessment["max_out_of_envelope_frac"]), sensors=True)
                if not sens["in_scope"]:
                    in_scope, app = False, {"in_scope": False, "reasons": [f"{chosen['model_id']}: {r}" for r in sens["reasons"]], "detail": sens["detail"]}
            if dq_model["ok"] and in_scope:
                try:
                    scored = bundle.score(raw, baseline=baseline["offsets"]) if baseline is not None else bundle.score(raw)
                except Exception as e:                      # a failed model service never produces a number
                    model_ok, scored = False, None
                    log.exception("scoring failed for %s with %s", asset.asset_id, chosen["model_id"])
                    reasons.append(f"model_unavailable: scoring failed ({type(e).__name__}); details in the server log")
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
        prev = _state_from_conn(c, asset.asset_id) or AssetState()
        applied = prev.last_applied_as_of_ms is None or as_of > prev.last_applied_as_of_ms
        record["applied_to_state"] = applied
        escalated = None
        if not applied:
            record["reasons"] = record["reasons"] + [f"historical replay: stored, not applied to the live state (an assessment for "
                                                     f"{iso(prev.last_applied_as_of_ms)} is already applied)"]
            # latching is monotone toward more risk: a replayed urgent or inspection finding still raises the latch
            note = (f"latch escalated by a historical replay: the assessment for {iso(as_of)} is {cl.state.value}; nothing else in the "
                    f"live state changed")
            recorded = [r[0] for r in c.execute("SELECT DISTINCT health_state FROM assessments WHERE asset_id = ? AND as_of_ms = ?",
                                                (asset.asset_id, as_of))]
            escalated = states.escalate(prev, cl, note=note, now_ms=now_ms(), recorded=recorded)
            if escalated is prev:
                escalated = None
                if states.escalate(prev, cl, note=note) is not prev:      # held back only by the earlier finding for this instant
                    record["reasons"] = record["reasons"] + [f"latch not raised: an earlier assessment for {iso(as_of)} already had this "
                                                             f"finding, and it was cleared by a person since"]
            else:
                record["reasons"] = record["reasons"] + [f"{note} (latched risk {prev.latched_risk} -> {escalated.latched_risk})"]
        record["latch_escalated"] = escalated is not None
        c.execute("INSERT INTO assessments (assessment_id, asset_id, as_of_ms, created_at, model_id, health_state, reasons_json, data_quality_json, "
                  "applicability_json, rul_unit, rul_point, rul_lower, rul_upper, interval_level, rul_point_hours, rul_lower_hours, rul_upper_hours, "
                  "risk_json, anomaly_score, anomaly_flag, top_deviations_json, inputs_json, policy_json, applied_to_state) "
                  "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  (record["assessment_id"], record["asset_id"], as_of, record["created_at"], record["model_id"], record["health_state"],
                   json.dumps(record["reasons"]), json.dumps(record["data_quality"], default=str), json.dumps(record["applicability"], default=str),
                   record["rul_unit"], record["rul_point"], record["rul_lower"], record["rul_upper"], record["interval_level"], record["rul_point_hours"],
                   record["rul_lower_hours"], record["rul_upper_hours"], json.dumps(record["risk"]), record["anomaly_score"],
                   None if record["anomaly_flag"] is None else int(record["anomaly_flag"]), json.dumps(record["top_deviations"]),
                   json.dumps(inputs), json.dumps(record["policy"]), int(applied)))
        if applied:
            t = now_ms()
            new = states.advance(prev, cl, pol.states, now_ms=t)
            new = states.replace(new, last_applied_as_of_ms=as_of, last_applied_at_ms=t)
            _store_state(c, asset.asset_id, new, record["assessment_id"])
        elif escalated is not None:
            new = escalated
            _store_state(c, asset.asset_id, new, None)           # the last applied assessment stays the one of record
            auditlog.append(c, actor=actor, action="asset_state.escalated_by_replay", entity="asset", entity_id=asset.asset_id,
                            payload={"assessment_id": record["assessment_id"], "as_of": iso(as_of), "health_state": record["health_state"],
                                     "before": prev.labels(), "after": new.labels(), "latched_risk": new.latched_risk,
                                     "latched_since": iso(new.latched_since_ms)}, key=db.audit_key, key_id=db.audit_key_id)
        else:
            new = prev
        auditlog.append(c, actor=actor, action="assessment.created", entity="assessment", entity_id=record["assessment_id"],
                        payload={"asset_id": asset.asset_id, "as_of": iso(as_of), "health_state": record["health_state"], "model_id": record["model_id"],
                                 "rul": [record["rul_lower"], record["rul_point"], record["rul_upper"]], "p_fail_decision_horizon": p_fail,
                                 "reasons": record["reasons"], "feature_sha256": inputs.get("feature_sha256"), "policy_sha256": pol.sha256,
                                 "asset_state": new.labels(), "applied_to_state": applied, "latch_escalated": record["latch_escalated"]},
                        key=db.audit_key, key_id=db.audit_key_id)
    record["asset_state"] = new.labels()
    return record


def assess_range(db, asset_id: str, policy, start_ms: int, end_ms: int, step_ms: int, actor: str = "system") -> dict:
    """Assess at every step from start to end (oldest first), e.g. after a periodic export arrives. Bounded. Every instant is
    checked before any is assessed, so a refused range stores nothing. `replays_escalated` counts the replays that raised
    the latched risk (they are not counted in `applied`)."""
    if step_ms < 60_000 or end_ms < start_ms:
        raise AssessmentError("assess_range needs end >= start and a step of at least one minute")
    n = (end_ms - start_ms) // step_ms + 1
    if n > MAX_RANGE_STEPS:
        raise AssessmentError(f"{n} steps requested; at most {MAX_RANGE_STEPS} per call")
    asset = registry.get_asset(db, asset_id)
    if asset is None:
        raise AssessmentError(f"unknown asset {asset_id}")
    instants = [start_ms + k * step_ms for k in range(int(n))]
    _check_instants(db, asset, instants)
    counts, applied, escalated = {}, 0, 0
    for t in instants:
        r = assess(db, asset.asset_id, policy, as_of_ms=t, actor=actor)
        counts[r["health_state"]] = counts.get(r["health_state"], 0) + 1
        applied += int(r["applied_to_state"])
        escalated += int(r["latch_escalated"])
    return {"asset_id": asset.asset_id, "assessments": int(n), "applied": applied, "replays_escalated": escalated, "states": counts,
            "asset_state": asset_state(db, asset.asset_id).labels()}


def asset_view(db, asset, policy, now: int | None = None) -> dict:
    """What a person should see for an asset: its labels, when it was last assessed, and ASSESSMENT_OVERDUE when the
    assessment job has not run within the policy limit (a stopped job must never leave a fleet looking healthy), or when
    the state shows a result but no time of assessment is on record (e.g. a row restored without its assessments)."""
    s = asset_state(db, asset.asset_id)
    now = int(now if now is not None else now_ms())
    labels = s.labels() if s else ["NOT_ASSESSED"]
    last_at = s.last_applied_at_ms if s else None
    if last_at is None and s is not None and s.last_health is not None:
        labels = labels + ["ASSESSMENT_OVERDUE"]
    elif last_at is not None:
        limit_h = float(policy.for_type(asset.asset_type_id).assessment.get("max_assessment_age_hours", 6.0))
        if now - last_at > limit_h * HOUR_MS:
            labels = labels + ["ASSESSMENT_OVERDUE"]
    return {"state": labels, "last_assessed_at": iso(last_at) if last_at else None,
            "last_assessment_instant": iso(s.last_applied_as_of_ms) if s and s.last_applied_as_of_ms else None}


# -- asset state persistence -------------------------------------------------------------------------------------
def _state_from_conn(c, asset_id: str) -> AssetState | None:
    r = c.execute("SELECT * FROM asset_states WHERE asset_id = ?", (asset_id,)).fetchone()
    if r is None:
        return None
    return AssetState(effective=H(r["effective"]), latched_risk=r["latched_risk"], dq_failure_active=bool(r["dq_failure_active"]),
                      dq_ok_streak=int(r["dq_ok_streak"]), last_health=H(r["last_health"]) if r["last_health"] else None,
                      approval_pending=bool(r["approval_pending"]), notes=tuple(json.loads(r["notes_json"])),
                      latched_since_ms=r["latched_since_ms"], awaiting_assessment=bool(r["awaiting_assessment"]),
                      last_applied_as_of_ms=r["last_applied_as_of_ms"], last_applied_at_ms=r["last_applied_at_ms"])


def _store_state(c, asset_id: str, s: AssetState, assessment_id: str | None):
    c.execute("INSERT INTO asset_states (asset_id, effective, latched_risk, dq_failure_active, dq_ok_streak, last_health, approval_pending, notes_json, "
              "last_assessment_id, updated_at, latched_since_ms, awaiting_assessment, last_applied_as_of_ms, last_applied_at_ms) "
              "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(asset_id) DO UPDATE SET effective = excluded.effective, "
              "latched_risk = excluded.latched_risk, dq_failure_active = excluded.dq_failure_active, dq_ok_streak = excluded.dq_ok_streak, "
              "last_health = excluded.last_health, approval_pending = excluded.approval_pending, notes_json = excluded.notes_json, "
              "last_assessment_id = COALESCE(excluded.last_assessment_id, asset_states.last_assessment_id), updated_at = excluded.updated_at, "
              "latched_since_ms = excluded.latched_since_ms, awaiting_assessment = excluded.awaiting_assessment, "
              "last_applied_as_of_ms = excluded.last_applied_as_of_ms, last_applied_at_ms = excluded.last_applied_at_ms",
              (asset_id, s.effective.value, s.latched_risk, int(s.dq_failure_active), s.dq_ok_streak, s.last_health.value if s.last_health else None,
               int(s.approval_pending), json.dumps(list(s.notes)), assessment_id, now_iso(), s.latched_since_ms, int(s.awaiting_assessment),
               s.last_applied_as_of_ms, s.last_applied_at_ms))


def asset_state(db, asset_id: str) -> AssetState | None:
    with db.connect() as c:
        return _state_from_conn(c, asset_id)


def clear_latched_risk(db, asset_id: str, event: str, actor: str, role: str, reason: str) -> AssetState:
    """A reasoned dismissal of a latched warning. Maintenance clears a latch only through its completed work order
    (workorders.complete), so no caller of this service may record 'maintenance_completed' (PD-16)."""
    if event != "dismissed":
        raise states.TransitionError(f"only a reasoned dismissal can be recorded here, not {event!r}: maintenance clears a latch "
                                     "only through its completed work order")
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
        r = c.execute("SELECT * FROM assessments WHERE asset_id = ? AND applied_to_state = 1 ORDER BY as_of_ms DESC, created_at DESC LIMIT 1",
                      (asset_id,)).fetchone()
    if r is None:
        return None
    d = dict(r)
    for k in ("reasons", "data_quality", "applicability", "risk", "top_deviations", "inputs", "policy"):
        d[k] = json.loads(d.pop(f"{k}_json"))
    return d
