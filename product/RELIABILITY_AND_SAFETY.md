# Reliability and safety

Status 2026-10-18, after the Phase 9 adversarial review (`ADVERSARIAL_REVIEW.md`) and its fixes. This document covers how SentinelLoop behaves when its inputs, models or own components fail, how its states change, how well-calibrated its uncertainty is, and how to recover. **All evidence is on SIMULATED (C-MAPSS) or SYNTHETIC (wind) data, plus software tests. Nothing here is field-validated** (`VALIDATION_LADDER.md`).

## 1. Safety position

1. **Advisory only.** SentinelLoop has no connection to control systems. It cannot start, stop or reconfigure equipment, and it never executes maintenance. Every recommendation becomes a work order that a named person approves, defers or rejects (principle 8).
2. **Not a safety function.** SentinelLoop is not part of any safety function or safety instrumented function. It claims no SIL, takes no credit as a protection layer, and must not be counted as a barrier or safeguard in any hazard analysis (HAZOP, LOPA, bow-tie or similar). It has not been assessed or certified against IEC 61508, IEC 61511 or IEC 62443 (wording from `research/R5_integration_standards.md`; finding safety-12). Turbine protection systems, alarm handling and the operator's procedures stay in charge, and plant safety must be complete without SentinelLoop. The console's sign-in page says "Not part of any safety function" (`src/sentinelloop/console/app.py`).
3. **Fail visible, not silent.** When data, scope or the model fail, the asset shows *why* there is no assessment: DATA_QUALITY_FAILURE, MODEL_OUT_OF_SCOPE or MODEL_UNAVAILABLE. These states are never shown as healthy, and they never produce a number. An asset that was never assessed shows NOT_ASSESSED, and one whose assessments have stopped shows ASSESSMENT_OVERDUE (§2).
4. **Warnings do not disappear by themselves.** URGENT_REVIEW and INSPECTION_RECOMMENDED latch. They clear only when a person completes a work order, raised after the warning began, whose outcome records an inspection of the equipment (the platform cannot check that the inspection took place), or when a planner, reliability engineer or admin dismisses them with a written reason (PD-16, refining PD-08). A later benign reading, bad data, a model outage or a back-dated assessment does not clear them.
5. **No invented numbers.** Anomaly-only models (wind) produce no failure probability or remaining life. Decisions then use stated policy defaults (PD-11). The RUL model's P(failure) is not calibrated (§4). Only the console's explanation line on work-order cards labels it "model-implied ... not calibrated"; assessment reasons, decision "why" text and the CMMS request description show the same number without that caveat (§4).

## 2. States and transitions

**Definitions:** `src/sentinelloop/app/states.py`, module docstring.

**Classification precedence for one assessment:**
1. Model unavailable.
2. Data-quality failure.
3. Out of scope.
4. Risk (or anomaly).

**Labels** shown with or instead of the state (`AssetState.labels`, `health.asset_view`):
- NOT_ASSESSED: no assessment has been applied yet. Never shown as NORMAL_MONITORING.
- AWAITING_ASSESSMENT: a latch was cleared; shown until the next applied assessment.
- INSPECTION_PENDING: a latched inspection is hidden behind a data, scope or model state.
- ASSESSMENT_OVERDUE: the last applied assessment is older than `max_assessment_age_hours` (6 h by default, 26 h for wind; `configs/platform.yaml`).
- HUMAN_APPROVAL_REQUIRED: an order for the asset waits for approval.

**Latching and clearing (PD-16).**
- An URGENT or INSPECTION assessment latches the asset and records the wall-clock time the latch began. An escalation from INSPECTION to URGENT restarts the latch (`states.advance`), so an order raised for the earlier inspection cannot clear the urgent one (code only: no test asserts the new start).
- A latch is cleared in exactly two ways:
  1. **Completing a work order** that meets all four conditions (`workorders._latch_keep_reasons`):
     - it was raised after the latch began;
     - its job addresses the equipment: not `instrument_check` or `desk_review`;
     - its outcome records an inspection: `degradation_found`, `failure_found` or `no_fault_found` (not `not_inspected` or `other`);
     - it was completed by a person (technician, planner or admin), not by the `integration` machine role. `HUMAN_CLEARERS` also names the reliability engineer, but that role cannot complete orders (`workorders.TRANSITIONS["complete"]`).
  2. **A dismissal with a written reason**: `POST /assets/{id}/clear-risk` with `event: dismissed`, by a planner, reliability engineer or admin. `clear-risk` refuses `maintenance_completed` (422) and refuses technicians (403). This restriction is in the API route only (`api.py`, `clear_risk`). The services behind it (`health.clear_latched_risk`, `states.clear_risk`) still accept `maintenance_completed`, with free text and no work order, from technicians, planners, reliability engineers and admins (`states.CLEAR_EVENTS`). A script or new route that calls them directly bypasses PD-16 (`THREAT_MODEL.md` E1).
- A latch whose start is unknown fails closed: no completion clears it, only a reasoned dismissal. Migration 0007 backfills the start of latches that existed before migration 0006 with the time their state row was last written, which is at or after the true start.
- A completion that fails any condition keeps the latch. The outcome gets the flag `latch_kept`, the asset gets a note with the reasons, and the audit log records `asset_state.latch_kept`.
- After either kind of clearing the asset shows AWAITING_ASSESSMENT, never NORMAL_MONITORING, until it is assessed again.

| from (effective) | event | to | rule | test |
|---|---|---|---|---|
| any | assessment URGENT | URGENT_REVIEW (latched; start recorded) | latch | `test_urgent_latches_until_maintenance_or_dismissal`, `test_advance_never_records_a_zero_latch_start` |
| URGENT_REVIEW | any later assessment | URGENT_REVIEW | stays; a note explains the latch | same; `test_data_failure_never_hides_an_urgent_condition`; `test_a_latched_urgent_state_survives_a_model_outage_and_a_restart` |
| INSPECTION_RECOMMENDED | assessment URGENT | URGENT_REVIEW | upgrade (the latch restarts), never a silent downgrade | `test_inspection_upgrades_to_urgent_but_never_silently_downgrades` (the upgrade only). The latch restart: code only (`states.advance`) |
| URGENT_REVIEW / INSPECTION | completion meeting all four conditions | AWAITING_ASSESSMENT | clear | `test_a_relevant_inspected_completion_clears_and_awaits_reassessment` |
| URGENT_REVIEW / INSPECTION | completion as `not_inspected`; of an order raised before the latch; of an `instrument_check`; by the `integration` role; with an unknown latch start | unchanged; outcome flag `latch_kept` | fail closed | `test_a_not_inspected_completion_keeps_the_urgent_latch`, `test_an_order_created_before_the_latch_does_not_clear_it`, `test_an_instrument_check_does_not_clear_an_equipment_latch`, `test_a_machine_credential_completion_does_not_clear_a_latch`, `test_an_unknown_latch_start_fails_closed`, `test_migration_backfills_the_start_of_existing_latches`. A `desk_review` completion: code only (`NON_CLEARING_JOBS`), no test |
| URGENT_REVIEW / INSPECTION | dismissal with a written reason (planner, reliability engineer, admin) | AWAITING_ASSESSMENT | clear | `test_urgent_latches_until_maintenance_or_dismissal` (technician and empty reason refused), `test_maintenance_cannot_be_recorded_through_clear_risk` (API: technician 403, `maintenance_completed` 422, dismissal 200). Neither test asserts the AWAITING_ASSESSMENT label after a dismissal: code only (`states.clear_risk`, `AssetState.labels`) |
| AWAITING_ASSESSMENT | next applied assessment | the state of that assessment | | code only (`states.advance` resets `awaiting_assessment`). `test_urgent_latches_until_maintenance_or_dismissal` checks the next effective state but not the label, and in that test `clear_risk` has already set the effective state to NORMAL_MONITORING |
| any | assessment DATA_QUALITY_FAILURE | DATA_QUALITY_FAILURE, unless urgent is latched | | `test_data_quality_failure_needs_consecutive_good_assessments_to_clear`, `test_data_failure_never_hides_an_urgent_condition`; precedence of one assessment: `test_classification_precedence` |
| DATA_QUALITY_FAILURE | `dq_clear_after` (2) consecutive assessments without a data failure | latest state | hysteresis | `test_data_quality_failure_needs_consecutive_good_assessments_to_clear` |
| none latched | MODEL_OUT_OF_SCOPE / MODEL_UNAVAILABLE | shown as such | | `test_out_of_scope_and_model_unavailable_show_through_when_no_risk_is_latched` |
| INSPECTION latched | data, scope or model failure | that state + INSPECTION_PENDING. A scope or model failure also raises an inspection order (P2); a data failure raises its data-quality order (none for a whole-feed delay) | the pending inspection is not cancelled by the model's silence | `test_a_latched_inspection_hidden_by_scope_still_gets_an_inspection_and_a_label` (scope case). Data and model cases: code only (`states.AssetState.labels`, `decision.recommend`) |
| any | assessment for an instant at or before the last applied one | unchanged; stored as a replay (`applied_to_state = 0`) | replays never move the state | `test_back_dated_assessments_are_stored_but_never_move_the_live_state` |
| any | assessment instant more than 5 min in the future | refused | | `test_future_assessment_instants_are_refused` |
| no assessment applied | — | NOT_ASSESSED | never shown as healthy | `test_a_never_assessed_asset_is_never_labelled_normal` |
| any | no applied assessment within `max_assessment_age_hours` | + ASSESSMENT_OVERDUE | a stopped assessment job is visible | `test_assets_report_when_they_were_last_assessed_and_flag_overdue` |
| any | an order awaits approval | + HUMAN_APPROVAL_REQUIRED flag | independent of health | `test_approval_flag_is_independent_of_the_health_state` |

Tests are in `tests/test_app_states.py`, `tests/test_app_remediation.py` and `tests/test_app_failure_injection.py`. `test_every_transition_in_the_table_is_exercised` is narrower than its name (finding safety-8). It only feeds every classification to every state reachable in four steps and checks that the result is a valid state and that a latched URGENT always shows URGENT_REVIEW. It does not exercise the clearing, replay, label or approval rows; the tests named in those rows do, except for the parts marked code only.

**Work-order rules that bear on safety** (PD-18; tests in `tests/test_app_remediation.py` unless stated):
- Work orders have 10 states, and every transition is role-checked (`workorders.TRANSITIONS`; `tests/test_app_workorders.py`).
- An urgent condition that arises while lower-priority work is in progress raises its own P1 order (`test_an_urgent_condition_during_lower_priority_work_raises_its_own_p1`).
- A deferred order returns to PENDING_APPROVAL once its date has passed, the next time `POST /decisions/generate` runs (`workorders.reactivate_due`; `test_a_deferred_order_returns_for_approval_when_its_date_passes`). A deferred order escalated to P1 comes back at once (`workorders.reprioritise`; code only).
- A reasoned rejection holds back the same condition (same asset, job and state, not more urgent) for 24 h, 168 h or 720 h (P1, P2, P3; `DecisionConfig.reject_suppress_h`). An escalation is raised at once (`test_a_reasoned_rejection_is_not_re_raised_for_the_same_condition`).
- `hand_back` returns a scheduled or started job to APPROVED, with a reason, and clears its schedule (`test_a_technician_can_hand_back_a_job_with_a_reason`).
- An out-of-scope or unavailable criticality-A turbine gets a `desk_review`, not a climb (`test_out_of_scope_criticality_a_turbines_get_a_desk_review_not_a_climb`). A desk review never clears a latch.
- Wind urgent orders say "a policy threshold, not a failure-time prediction" and make no failure-time claim (`test_anomaly_urgent_wording_makes_no_failure_time_claim`).

## 3. Failure modes and responses

Each evidence entry names the test that exercises the behaviour. Where a test covers only part of a row, the row says so (finding safety-8).

| # | failure | how it is detected | system response | resulting state | evidence |
|---|---|---|---|---|---|
| F1 | one required signal missing, stopped or gappy | generic data quality per signal | no prediction; the reason names the signal (`missing_signal`, `stale_data` or `excessive_missing`) | DATA_QUALITY_FAILURE | `test_missing_signal_stale_data_and_stuck_sensor_are_data_quality_failures` (a signal that stops while the others continue; the test asserts a reason naming it). The `missing_signal` case (no readings at all) is not asserted by any test |
| F2 | the whole feed delayed | every required signal older than `max_data_age_hours` (1 h for wind) at once | reason `data_delivery_delay`: a data-path problem, so **no work order** is raised at the asset; staleness report | DATA_QUALITY_FAILURE | same test (late feed); `test_a_feed_delay_is_a_data_path_problem_not_an_instrument_check`; `test_staleness_report_flags_silent_signals` |
| F3 | stuck sensor | trailing constant run longer than any seen in training (and at least `stuck_min_run`) | as F1; reported even when the turbine is idle (PD-13) | DATA_QUALITY_FAILURE | `test_stuck_temperature_sensor_is_a_data_quality_failure_not_an_anomaly[18/12]` (day 12 is calm, the turbine mostly idle) |
| F4 | conflicting readings | learned redundant relation (C-MAPSS s8/s13, s9/s14; wind generator vs rotor speed) | as F1, reason `conflicting_readings` | DATA_QUALITY_FAILURE | `test_conflicting_redundant_sensors_are_a_data_quality_failure`, `test_generator_and_rotor_speed_disagreement_is_a_data_quality_failure` |
| F5 | implausible values | type's plausible range at ingestion | stored and flagged `suspect_out_of_range`; above `max_suspect_frac` in the window → data failure, reason `out_of_range:<signal>` | DATA_QUALITY_FAILURE | `test_out_of_range_values_are_kept_but_marked_suspect` (flagging), `test_suspect_values_above_the_limit_make_a_data_quality_failure` (the state) |
| F6 | wrong units or malformed rows | ingestion contract | row rejected with a reason code; the rest of the batch is accepted | — | `test_each_contract_violation_is_rejected_with_a_reason` (every reason code), `test_within_batch_conflict_and_exact_duplicate` (one row accepted, one rejected) |
| F7 | unexpected operating conditions (envelope, regime, climate) | model scope checks | no prediction; reason `operating_envelope` or `unknown_operating_regime` | MODEL_OUT_OF_SCOPE | `test_an_engine_from_another_operating_envelope_is_out_of_scope`, `test_ambient_temperature_outside_training_range_is_out_of_scope` |
| F8 | turbine idle or stopped | operating share in the scoring window | `insufficient_operation`; not "healthy" | MODEL_OUT_OF_SCOPE | `test_stopped_turbine_is_out_of_scope_rather_than_healthy` |
| F9 | turbine not commissioned | missing baseline | `no_baseline` | MODEL_OUT_OF_SCOPE | `test_uncommissioned_turbine_is_out_of_scope` |
| F10 | model artefact tampered or missing | SHA-256 against the registry value when the bundle is loaded; file present | model refused; the reason says `model_unavailable` and the details (paths) go to the server log (the API's stderr) | MODEL_UNAVAILABLE | `test_tampered_model_artifact_makes_the_model_unavailable` (the loader refuses a tampered file; it does not run an assessment), `test_a_model_file_deleted_after_approval_gives_model_unavailable` (assessment level). A loaded bundle is cached per process, so a file changed or deleted while the API runs is detected at the next restart. Registration refuses a pickle that does not match its manifest (`test_registration_refuses_an_artefact_that_does_not_match_its_manifest`) |
| F11 | model crashes while scoring | exception during scoring | no number; the reason gives the exception type only | MODEL_UNAVAILABLE | `test_a_model_that_crashes_while_scoring_gives_model_unavailable_and_no_numbers` |
| F12 | one asset breaks decision generation | per-asset isolation | the error is audited (`decision.error`); the other assets proceed | — | `test_a_failing_asset_is_isolated_and_the_error_audited` (injected exception). `test_one_bad_asset_never_stops_generation_for_the_others` covers in-progress and rejected orders |
| F13 | concurrent writers | SQLite `BEGIN IMMEDIATE`, unique keys | no lost or doubled rows; audit chain intact | — | `test_concurrent_ingestion_loses_nothing_and_double_counts_nothing` |
| F14 | process restart | state lives in the database | latched states persist | — | `test_a_latched_urgent_state_survives_a_model_outage_and_a_restart` |
| F15 | unexpected server error | exception handler | JSON 500 with a request id, no internals | — | `test_an_unexpected_server_error_is_a_json_500_with_a_request_id_and_no_internals` |
| F16 | audit trail edited, truncated or verified with the wrong key | HMAC chain; anchor (seq, hash) kept off the host | `verify-audit` fails, exit 1; it refuses to run without an anchor unless `--allow-no-anchor` is given. Truncation is detected only for events up to the anchor used. Direct edits of state tables (assets, states, work orders, users) are **not** detected (PD-22). `GET /api/v1/audit/verify` without `anchor_seq` and `anchor_hash`, and the console's "Verify the audit chain" button (which sends none), check internal consistency only: a truncated chain still verifies as `valid: True` | — | edit: `test_backup_restore_round_trip_and_audit_verification`; wrong key: `test_wrong_key_fails_audit_verification`; truncation against an anchor: `test_audit_anchor_detects_truncation` and recovery drill R1; missing anchor: `test_verify_audit_requires_an_anchor_unless_explicitly_waived` |
| F17 | stale schedule proposal | order versions at apply time | apply refused; re-plan | — | `test_stale_proposal_is_refused_when_orders_changed` (`tests/test_app_planning.py`) |
| F18 | slow sensor drift (no redundant sensor) | **not distinguishable** from a heating component | alarms, i.e. an inspection is recommended | INSPECTION_RECOMMENDED | W2 (SYNTHETIC): 37 drifting-sensor alarm episodes on the held-out W1 fleets at the shipped setting (`evidence/wind_synthetic/w2.md`). **Known limitation** (KNOWN_LIMITATIONS M1) |
| F19 | plausible but false data from a compromised source | **not detectable** by the platform | — | — | residual risk, `THREAT_MODEL.md` T1 |
| F20 | the assessment job stops | last applied assessment older than `max_assessment_age_hours` | label ASSESSMENT_OVERDUE; the last known state stays visible with its time (`last_assessed_at`) | + ASSESSMENT_OVERDUE | `test_assets_report_when_they_were_last_assessed_and_flag_overdue` |
| F21 | back-dated or future assessment instants (late exports, a misused `as_of`) | the instant against now and against the last applied instant | more than 5 min ahead: refused. At or before the last applied instant: stored as a replay that never moves the live state | unchanged | `test_future_assessment_instants_are_refused`, `test_back_dated_assessments_are_stored_but_never_move_the_live_state` |

## 4. Calibration (RUL model; SIMULATED)

**C1 interval audit** (`product/evidence/calibration/c1.md`, out-of-fold predictions on C-MAPSS FD001–FD004):
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

**C2 probability audit** (`product/evidence/calibration/c2.md`; P(failure before 60 h) read from the same out-of-fold intervals, 3 h per cycle):
- **P(failure) is not calibrated.** In the most populated high bin (shown 0.50–0.70), the mean shown is 0.54–0.57 while 0.89–0.94 of those rows fail within 60 h, in all four subsets.
- **The due-date rule fails more often than it states.** The latest-start rule targets P(failure before the job ends) ≤ 0.05. In the last 50 cycles of life (true RUL 0–50) the true failure came first in 9–18% of rows (FD001 0.148 and 0.184; FD004 0.160 and 0.171), and in 9.5–15.8% at true RUL 50–100.
- Isotonic recalibration on an engine split lowers the Brier score by 37–50% (FD001 0.0287 → 0.0158, FD002 0.0286 → 0.0163, FD003 0.0220 → 0.0110, FD004 0.0271 → 0.0171). It is **not shipped**: it needs a held-out calibration set from the customer's assets (PD-19). OPEN.
- The console's explanation line on work-order cards shows the number as "Model-implied P(failure ...) (not calibrated ...)" (`console/client.py`, `explanation_lines`). The same number appears **without** that caveat in:
  - the assessment reasons ("P(failure before horizon) 0.xx >= urgent threshold ...", `states.classify`), which the console's Asset page and the cards' "Assessment reasons" line show;
  - the decision "why" text for safety-impact assets ("P(failure) 0.xx >= safety limit", `decision.recommend`);
  - the CMMS request description ("P(failure before <horizon> h): 0.xx", `integration.odoo_payload`), which field crews read.
- The wind vertical shows no probability at all (PD-11).

**Consequences:**
1. The intervals are described as marginally calibrated over a fleet's life, never as a conditional guarantee near failure (claim P2 stays NOT_SUPPORTED).
2. **The platform ships the probabilistic trigger for RUL models, not a threshold on the point prediction** (finding data_scientist-3). The state comes from P(failure before the decision horizon), read from the interval (`health.assess`, `risk.summarise`), against `p_inspect` 0.10 and `p_urgent` 0.30 with a 60 h horizon for C-MAPSS (`states.classify`, `configs/platform.yaml`). These are the untuned S1 settings; tuning in the base scenario chose 0.05 and 0.20 instead, in both S1d and S2. In S2 (SIMULATED; `SCHEDULING_EVALUATION.md` conclusion 7 and §4.3) the shipped settings come within 2 units of base-tuned RISK_GREEDY in the `base`, `tight_labour` and `parts_tight` scenarios, but cost 20.3 more under degraded (biased) predictions (worse on 8/8 seeds) and 8.4 more under approval delay (7/8). The trigger and the due date depend on exactly the calibration that C1 and C2 show is weakest in late life. A per-site tuned point-threshold trigger is PLANNED (PD-27; KNOWN_LIMITATIONS M7). This path runs only on SIMULATED C-MAPSS data; no pilot depends on it.
3. Mondrian recalibration of the intervals by predicted band, and isotonic recalibration of P(failure), are the upgrades to make if an RUL model family is put into use (PLANNED; neither is in the bundle).

**Stress evidence carried over from the competition** (INJECTED faults on C-MAPSS): detection of missing values, noise and regime shift at 98–100% with zero per-engine false alarms, with a single-sensor bias as the detection floor on two subsets (`experiments/results/e3_stress/`, claim P4).

## 5. Recovery and rollback procedures

These are the procedures. The operations runbook carries the commands.

| situation | procedure | tested by |
|---|---|---|
| a newly approved model misbehaves | `POST /models/rollback` (reliability engineer, reason) restores the previous approved version; assessments use whichever model is approved (`modelreg.approved_models` in `health.assess`) | `test_model_rollback_restores_the_previous_approved_version` (registry statuses) |
| a model file is lost or corrupted | assets go MODEL_UNAVAILABLE (visible, no numbers) when the bundle is next loaded: at once if it was not yet loaded, after an API restart if it was cached. Re-deploy the bundle from its source, or roll back. Latched warnings remain | F10, F11, F14 |
| fleet-wide MODEL_UNAVAILABLE or OUT_OF_SCOPE | fall back to the site's existing inspection programme (fixed-interval or route-based). The reason is that SentinelLoop must never be the only schedule. This is not a claim that fixed-interval is safer or cheaper: in S2 (SIMULATED) it is the most expensive policy other than run-to-failure in every sustainable scenario, and in the collapse scenarios except parts shortage, where the base-tuned MILP costs more. Whether it is a safer fallback when predictions fail through noise, per-asset bias or drift was not tested (`SCHEDULING_EVALUATION.md` conclusion 5; PD-27 (f)) | procedure only |
| database lost or corrupted | `admin restore --from <backup> --db <new path>` (it copies the backup's anchor), then `admin verify-audit`. To detect truncation before that backup, verify against an older anchor kept off the host. Restore never overwrites in place without `--force` | `test_backup_restore_round_trip_and_audit_verification`; R1 (`product/evidence/recovery/r1.md`) |
| audit verification fails | treat as a security incident: freeze changes, keep the database and anchor copies, compare with the last good backup (runbook) | F16 |
| a turbine had a drivetrain component replaced | re-commission it on a new healthy period (`POST /assets/{id}/baseline`); until then its old baseline may mis-score | procedure; automatic prompt PLANNED |
| a site's data feed stops | staleness report, then DATA_QUALITY_FAILURE with `data_delivery_delay` and no work order. Fix the feed. For export-fed sites, replay the delivered export with `assess-range`, oldest instant first. The state clears after two good assessments | F2, F21 |
| the assessment job stops | ASSESSMENT_OVERDUE on every affected asset. Restart the job; the label goes at the next applied assessment | F20 |

## 6. Residual risks (also in `KNOWN_LIMITATIONS.md`)

- Real-data detection performance is unknown until G0 (rung 3) and a customer back-test (rung 4).
- On synthetic data the shipped wind setting still gives 2.65 healthy alarm episodes per turbine-year on the held-out fleets, above the proposed pilot ceiling of 2 (E7).
- Slow sensor drift raises false inspections (F18).
- Commissioning on a period that already contains a developing fault hides that fault (PD-12).
- RUL intervals under-cover in late life, and the RUL model's P(failure) is not calibrated (§4).
- Direct edits of state tables in the database file are not detected by the audit chain (PD-22).
- The in-process rate limit and the single SQLite file suit one site (load test L1).
