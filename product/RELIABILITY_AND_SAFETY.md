# Reliability and safety

Status 2026-10-18. This document covers how SentinelLoop behaves when its inputs, models or own components fail, how its states change, how well-calibrated its uncertainty is, and how to recover. **All evidence is on SIMULATED (C-MAPSS) or SYNTHETIC (wind) data, plus software tests. Nothing here is field-validated** (`VALIDATION_LADDER.md`).

## 1. Safety position

1. **Advisory only.** SentinelLoop has no connection to control systems. It cannot start, stop or reconfigure equipment, and it never executes maintenance. Every recommendation becomes a work order that a named person approves, defers or rejects (principle 8).
2. **Plant safety must not depend on it.** Turbine protection systems, alarm handling and the operator's procedures remain in charge. A missing or wrong SentinelLoop recommendation must never be the only barrier against a hazard.
3. **Fail visible, not silent.** When data, scope or the model fail, the asset shows *why* there is no assessment: DATA_QUALITY_FAILURE, MODEL_OUT_OF_SCOPE or MODEL_UNAVAILABLE. These states are never shown as healthy, and they never produce a number.
4. **Warnings do not disappear by themselves.** URGENT_REVIEW and INSPECTION_RECOMMENDED latch until completed maintenance or a reasoned dismissal by an allowed role. A later benign reading, bad data or a model outage does not clear them (PD-08).
5. **No invented numbers.** Anomaly-only models (wind) produce no failure probability or remaining life. Decisions then use stated policy defaults (PD-11).

## 2. States and transitions

**Definitions:** `src/sentinelloop/app/states.py`, module docstring.

**Classification precedence for one assessment:**
1. Model unavailable.
2. Data-quality failure.
3. Out of scope.
4. Risk (or anomaly).

| from (effective) | event | to | rule | test |
|---|---|---|---|---|
| any | assessment URGENT | URGENT_REVIEW (latched) | latch | `test_urgent_latches_until_maintenance_or_dismissal` |
| URGENT_REVIEW | any later assessment | URGENT_REVIEW | stays; a note explains the latch | same; `test_data_failure_never_hides_an_urgent_condition`; `test_a_latched_urgent_state_survives_a_model_outage_and_a_restart` |
| URGENT_REVIEW / INSPECTION | maintenance_completed (technician and up) or dismissed with a reason (reliability engineer, planner, admin) | the state of the latest assessment | clear | `test_maintenance_completion_clears_the_latched_risk` |
| INSPECTION_RECOMMENDED | assessment URGENT | URGENT_REVIEW | upgrade, never a silent downgrade | `test_inspection_upgrades_to_urgent_but_never_silently_downgrades` |
| any | assessment DATA_QUALITY_FAILURE | DATA_QUALITY_FAILURE, unless urgent is latched | | `test_classification_precedence` |
| DATA_QUALITY_FAILURE | `dq_clear_after` (2) consecutive good assessments | latest state | hysteresis | `test_data_quality_failure_needs_consecutive_good_assessments_to_clear` |
| none latched | MODEL_OUT_OF_SCOPE / MODEL_UNAVAILABLE | shown as such | | `test_out_of_scope_and_model_unavailable_show_through_when_no_risk_is_latched` |
| any | an order awaits approval | + HUMAN_APPROVAL_REQUIRED flag | independent of health | `test_approval_flag_is_independent_of_the_health_state` |

Every entry of the transition table is exercised by `test_every_transition_in_the_table_is_exercised`. Work-order transitions (10 states) are role-checked and tested in `tests/test_app_workorders.py`.

## 3. Failure modes and responses

| # | failure | how it is detected | system response | resulting state | evidence |
|---|---|---|---|---|---|
| F1 | required signal missing | generic data quality | no prediction; reason `missing_signal` | DATA_QUALITY_FAILURE | `test_missing_signal_stale_data_and_stuck_sensor_are_data_quality_failures` |
| F2 | data delayed or stale | age of the latest reading against `max_data_age_hours` (1 h for wind) | as F1, reason `stale_data`; staleness report | DATA_QUALITY_FAILURE | same; `test_staleness_report_flags_silent_signals` |
| F3 | stuck sensor | trailing constant run longer than any seen in training (and at least `stuck_min_run`) | as F1; reported even when the turbine is idle (PD-13) | DATA_QUALITY_FAILURE | `test_stuck_temperature_sensor_is_a_data_quality_failure_not_an_anomaly[18/12]` |
| F4 | conflicting readings | learned redundant relation (C-MAPSS s8/s13, s9/s14; wind generator vs rotor speed) | as F1, reason `conflicting_readings` | DATA_QUALITY_FAILURE | `test_conflicting_redundant_sensors_are_a_data_quality_failure`, `test_generator_and_rotor_speed_disagreement_is_a_data_quality_failure` |
| F5 | implausible values | type's plausible range at ingestion | stored and flagged `suspect_out_of_range`; above `max_suspect_frac` → data failure | DATA_QUALITY_FAILURE | `test_out_of_range_values_are_kept_but_marked_suspect` |
| F6 | wrong units or malformed rows | ingestion contract | row rejected with a reason code; batch partially accepted | — | `test_each_contract_violation_is_rejected_with_a_reason` |
| F7 | unexpected operating conditions (envelope, regime, climate) | model scope checks | no prediction; reason `operating_envelope` or `unknown_operating_regime` | MODEL_OUT_OF_SCOPE | `test_an_engine_from_another_operating_envelope_is_out_of_scope`, `test_ambient_temperature_outside_training_range_is_out_of_scope` |
| F8 | turbine idle or stopped | operating share in the scoring window | `insufficient_operation`; not "healthy" | MODEL_OUT_OF_SCOPE | `test_stopped_turbine_is_out_of_scope_rather_than_healthy` |
| F9 | turbine not commissioned | missing baseline | `no_baseline` | MODEL_OUT_OF_SCOPE | `test_uncommissioned_turbine_is_out_of_scope` |
| F10 | model artefact tampered or missing | checksum against the registry; file present | model refused | MODEL_UNAVAILABLE | `test_tampered_model_artifact_makes_the_model_unavailable`, `test_a_model_file_deleted_after_approval_gives_model_unavailable` |
| F11 | model crashes while scoring | exception during scoring | no number; reason quoted | MODEL_UNAVAILABLE | `test_a_model_that_crashes_while_scoring_gives_model_unavailable_and_no_numbers` |
| F12 | one asset breaks decision generation | per-asset isolation | the error is audited; the other assets proceed | — | `test_one_bad_asset_never_stops_generation_for_the_others` |
| F13 | concurrent writers | SQLite `BEGIN IMMEDIATE`, unique keys | no lost or doubled rows; audit chain intact | — | `test_concurrent_ingestion_loses_nothing_and_double_counts_nothing` |
| F14 | process restart | state lives in the database | latched states persist | — | `test_a_latched_urgent_state_survives_a_model_outage_and_a_restart` |
| F15 | unexpected server error | exception handler | JSON 500 with a request id, no internals | — | `test_an_unexpected_server_error_is_a_json_500_with_a_request_id_and_no_internals` |
| F16 | audit trail edited, truncated or verified with the wrong key | HMAC chain and anchor | `verify-audit` fails, exit 1 | — | `test_backup_restore_round_trip_and_audit_verification`, `test_wrong_key_fails_audit_verification` |
| F17 | stale schedule proposal | order versions at apply time | apply refused; re-plan | — | `tests/test_app_planning.py` |
| F18 | slow sensor drift (no redundant sensor) | **not distinguishable** from a heating component | alarms, i.e. an inspection is recommended | INSPECTION_RECOMMENDED | `evidence/wind_synthetic/w1.md`: 193–293 alarm-hours per drifting sensor. **Known limitation** |
| F19 | plausible but false data from a compromised source | **not detectable** by the platform | — | — | residual risk, `THREAT_MODEL.md` T1 |

## 4. Calibration (RUL intervals; SIMULATED)

**C1 audit** (`product/evidence/calibration/c1.md`, out-of-fold predictions on C-MAPSS FD001–FD004):
- Overall coverage of the nominal 90% interval is 0.904–0.931.
- **Coverage is not uniform over life.**
  - In the healthy band (true RUL 100–125, most rows) it is 0.94–0.97.
  - In the decision-relevant band (true RUL 25–50) it is **0.81–0.87 in every subset**.
  - In the last 25 cycles it is 0.86–0.94.
- Coverage across the six operating regimes of FD002/FD004 is even (0.91–0.92). The weakness lies in the life stage, not in the regime.

**Alternative methods** (engine-level split; descriptive, since rows within an engine are dependent):
- A global conformal re-correction narrows the intervals and lowers late-life coverage.
- Mondrian re-correction by predicted-RUL band raises 25–50 coverage in three of four subsets (FD001 0.814 → 0.874, FD004 0.829 → 0.865, FD002 0.833 → 0.840; FD003 unchanged at 0.869), at width changes of −1.6 to +1.3 cycles.
- **No method tested reaches 90% in the late-life bands.**

**Consequences:**
1. The intervals are described as marginally calibrated over a fleet's life, never as a conditional guarantee near failure (claim P2 stays NOT_SUPPORTED).
2. For RUL models the default trigger is a threshold on the point prediction (PD-09), which does not rely on interval calibration.
3. Mondrian recalibration by predicted band is the recommended upgrade if an RUL model family is put into use (PLANNED; not implemented in the bundle).

**Stress evidence carried over from the competition** (INJECTED faults on C-MAPSS): detection of missing values, noise and regime shift at 98–100% with zero per-engine false alarms, with a single-sensor bias as the detection floor on two subsets (`experiments/results/e3_stress/`, claim P4).

## 5. Recovery and rollback procedures

These are the procedures. The operations runbook carries the commands.

| situation | procedure | tested by |
|---|---|---|
| a newly approved model misbehaves | `POST /models/rollback` (reliability engineer, reason) restores the previous approved version; assessments then use it | `test_model_rollback_restores_the_previous_approved_version` |
| a model file is lost or corrupted | assets go MODEL_UNAVAILABLE (visible, no numbers). Re-deploy the bundle from its source, or roll back. Latched warnings remain | F10, F11, F14 |
| fleet-wide MODEL_UNAVAILABLE or OUT_OF_SCOPE | fall back to the site's existing inspection programme (fixed-interval or route-based). SentinelLoop must never be the only schedule (SCHEDULING_EVALUATION: fixed-interval is the safer default when predictions fail) | procedure only |
| database lost or corrupted | `admin restore --from <backup> --db <new path>`, then `admin verify-audit` against the backup's anchor. Restore never overwrites in place without `--force` | `test_backup_restore_round_trip_and_audit_verification` |
| audit verification fails | treat as a security incident: freeze changes, keep the database and anchor copies, compare with the last good backup (runbook) | F16 |
| a turbine had a drivetrain component replaced | re-commission it on a new healthy period (`POST /assets/{id}/baseline`); until then its old baseline may mis-score | procedure; automatic prompt PLANNED |
| a site's data feed stops | staleness report, then DATA_QUALITY_FAILURE. Fix the feed; the state clears after two good assessments | F2 |

## 6. Residual risks (also in `KNOWN_LIMITATIONS.md`)

- Real-data detection performance is unknown until G0 (rung 3) and a customer back-test (rung 4).
- Slow sensor drift raises false inspections (F18).
- Commissioning on a period that already contains a developing fault hides that fault (PD-12).
- RUL intervals under-cover in late life (§4).
- The in-process rate limit and the single SQLite file suit one site; scale is measured in Phase 7.
