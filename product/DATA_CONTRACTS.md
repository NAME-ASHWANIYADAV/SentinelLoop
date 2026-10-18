# Data contracts

What SentinelLoop accepts, what it refuses, and what it promises about stored data. Every rule below is implemented and tested unless it is marked PLANNED, "known gap" or "no dedicated test".
- Code: `src/sentinelloop/app/ingest.py`, `health.py`, `states.py`, `registry.py`, `models.py`, `workorders.py`, `adapters/wind.py`, migrations in `src/sentinelloop/app/migrations/`.
- Tests: `tests/test_app_ingest.py`, `tests/test_app_foundation.py`, `tests/test_app_workorders.py`, `tests/test_app_health.py`, `tests/test_app_remediation.py`, `tests/test_app_remediation_security.py`, `tests/test_app_rereview_health.py`, `tests/test_app_rereview_api.py`, `tests/test_app_rereview_decision.py`, `tests/test_app_rereview_wiring.py`, `tests/test_app_api.py`.

## 1. Readings contract v1

**Shape: long format, one reading per row.**

| field | type | rule |
|---|---|---|
| `asset` | string | the asset's id or tag. Ids and tags share one namespace, so a key that could mean two assets is rejected (`ambiguous_asset`) |
| `timestamp` | ISO-8601 | must carry a UTC offset (`Z` or `+05:30`). A naive timestamp is accepted only if the batch declares `default_tz`; otherwise it is rejected (`naive_timestamp`). A `default_tz` that is not a known IANA time zone refuses the whole batch (422 at the API) and nothing is recorded (`test_an_unknown_batch_time_zone_is_a_client_error`). Stored as integer epoch milliseconds, UTC |
| `signal` | string | a signal name defined by the asset's type (`unknown_signal` otherwise). Names are the platform's canonical names (wind signal set below) |
| `value` | number | finite. Empty means missing and is not stored. `NaN`/`inf` → `non_finite_value`; text → `non_numeric_value` |
| `unit` | string | must equal the type's unit for that signal exactly. **There is no silent conversion**: `degF` for a `degC` signal is `unit_mismatch` |

**Wide CSV** (one column per signal) is accepted only when the caller states the unit of every signal column (`wide_units`, a JSON object of column → unit; anything else refuses the request with 422, `test_wide_units_must_be_an_object_of_unit_names`). A missing unit gives `missing_units`; required columns that are absent give `missing_columns`.

**Wind signal set** (`adapters/wind.py`, type `wind_turbine_geared`):
- **Required:** `wind_speed`, `active_power`, `rotor_speed`, `generator_speed`, `ambient_temp`, `nacelle_temp`, `gearbox_oil_temp`, `gearbox_bearing_temp`, `generator_bearing_temp`. A turbine that never delivers one is a DATA_QUALITY_FAILURE (`missing_signal`).
- **Optional:** `pitch_angle` (`OPTIONAL_SIGNALS`). The model does not read it (`nbm.MODEL_SIGNALS`), so its absence is not a data failure (`test_pitch_angle_is_not_required_by_the_wind_contract` checks the flag), and the staleness report skips it (no dedicated test).
- **Not in the contract:** turbine status codes, alarm codes, and curtailment or derating setpoints. They are rejected as `unknown_signal` (`KNOWN_LIMITATIONS.md` M3); operating-state signals per site are PLANNED.
- **No per-site tag mapping** (FR-B3, PLANNED; `KNOWN_LIMITATIONS.md` P12). An operator's export must be renamed to these names and converted to these units before ingestion.

**Reason codes.** Each rejected row is stored with its row number, raw values and reason:

`missing_fields`, `unknown_asset`, `ambiguous_asset`, `inactive_asset`, `unknown_signal`, `unit_mismatch`, `non_numeric_value`, `non_finite_value`, `naive_timestamp`, `unparseable_timestamp`, `future_timestamp`, `conflicting_value`, `missing_columns`, `missing_units`.

**Quality flags on stored rows.**
- `good`.
- `suspect_out_of_range`: the value lies outside the type's plausible min/max. It is stored, never silently dropped, and counted against `max_suspect_frac` at assessment time.

**Delivery semantics.**
- **Idempotent.** An exact duplicate (same asset, signal, instant and value) is skipped and counted. Re-sending a byte-identical batch returns the original batch record (`duplicate_batch`).
- **Conflicts.** A different value for an already-stored asset/signal/instant is rejected (`conflicting_value`). Corrections are a deliberate operation, not an overwrite (PLANNED: a correction endpoint with reason and audit).
- **Out of order and late.** Accepted and counted (`rows_out_of_order`, `rows_late`). A row is late when it is more than `lateness_ms` (default 1 h) older than the signal's newest stored reading.
- **Future timestamps.** More than `max_future_skew_ms` (default 5 min) ahead of the server clock → `future_timestamp`.
- **Batches.** Every batch gets an id, the SHA-256 of its content, counts (total, accepted, rejected, duplicate, out of order, late, suspect, missing) and an audit event. Status is `accepted`, `partially_accepted` or `rejected`.
- **Batch size.** At most 200,000 readings per batch (`ingest.MAX_RECORDS_PER_BATCH`).
  - A wide CSV counts rows × signal columns. A larger CSV is refused as a whole, and the message asks for the file to be split (`test_csv_uploads_are_capped_by_record_count` checks the refusal only).
  - The JSON route's `records` has the same limit (`api.py`, `max_length=200_000`; no dedicated test).
  - Both refusals return 422 (`api.py` error handlers; no dedicated test).
  - Request bodies are also capped at 10 MB (413; `api.create_app` `max_body_bytes`, which `serve` does not expose; `test_oversized_bodies_are_rejected`, `test_chunked_bodies_without_content_length_are_capped`). A JSON batch (roughly 115 bytes per record) reaches that cap at about 90,000 readings, well before the reading limit; a long-format CSV reaches it at about the reading limit.
  - CSV uploads are parsed off the API event loop (`run_in_threadpool`), but not streamed (`KNOWN_LIMITATIONS.md` S8; no dedicated test).
- **Staleness.** `GET /api/v1/ingest/staleness` lists the required signals of active assets with no reading newer than `max_age_h` (`test_staleness_report_flags_silent_signals`). `max_age_h` must be above 0 and at most 8,760 h (422 otherwise, `test_staleness_rejects_impossible_ages`). The 6 h default and the skipping of optional signals follow from the code (`api.py`, `ingest.staleness`); no dedicated test.

**Assessment instants and feed delays** (`health.py`, `states.py`, PD-17, PD-28):
- **Future instants.** An assessment instant more than 5 minutes after the server clock is refused (`test_future_assessment_instants_are_refused`).
- **Early instants.** An instant earlier than 2000-01-01T00:00Z (`health.MIN_AS_OF_MS`), or more than 5 minutes before the asset's first stored reading, is refused; nothing is stored, and the API answers 422 (`test_implausibly_early_instants_are_refused`, `test_an_instant_before_the_assets_first_reading_is_refused`, `test_the_api_refuses_a_year_one_instant_with_422_and_stores_nothing`). The 5 minutes match the clock skew ingestion allows, so a new asset whose first readings are slightly ahead of the server can still be assessed now (`test_a_first_reading_slightly_ahead_of_the_server_clock_does_not_block_the_live_assessment`).
- **Replays never lower or move the live state.** An assessment for an instant at or before the last applied instant is stored as a historical replay (`applied_to_state = 0`). It never lowers a latch or changes the rest of the live state, and the latest-assessment read ignores it (`test_back_dated_assessments_are_stored_but_never_move_the_live_state`).
- **Replays can raise a latch.** A replay that is URGENT_REVIEW or INSPECTION_RECOMMENDED, above the latched risk, raises the latch (`states.escalate`). The latch starts at the wall-clock time; the last health, the data-quality streak and the last applied instant stay as they were. The assessment carries `latch_escalated = true` and a reason, and the asset's audit history gets `asset_state.escalated_by_replay` (`test_an_urgent_replay_escalates_the_latch_and_changes_nothing_else`).
  - A replay raises nothing when an earlier assessment for the same instant already had that finding: a person has cleared it since, so the scheduled job re-assessing the same latest reading does not undo a dismissal or a completed inspection (`test_a_dismissal_is_not_undone_by_the_next_run_on_the_same_latest_reading`, `test_a_completed_inspection_is_not_undone_by_the_next_run_on_the_same_latest_reading`).
  - New data for an instant already assessed can still raise it (`test_a_new_finding_for_an_instant_already_applied_still_raises_the_latch`).
  - The order raised afterwards cites the latest applied assessment, not the replay (KNOWN_LIMITATIONS M10).
- **Periodic exports.** The policy key `assess_at` is `now` by default (`configs/platform.yaml`). With `latest_reading`, an assessment without an explicit instant is made at the asset's newest stored reading, and is refused when the asset has none (`test_assess_at_latest_reading_uses_the_last_reading_and_a_later_urgent_replay_still_latches`, `test_assess_at_latest_reading_needs_a_reading`).
  - `POST /api/v1/assets/{id}/assess-range` (start, end, step 1 min to 24 h) assesses each step oldest first, each on its own.
  - **Steps per call.** At most 2,000 in the library (`health.MAX_RANGE_STEPS`). Through the API a call also costs one rate-limit token per 10 steps, so with the shipped limiter (a bucket of 120) at most 1,200 steps (`test_a_range_the_bucket_can_never_pay_is_refused_without_work`; KNOWN_LIMITATIONS P13).
  - **All or nothing.** Every instant is checked before any is assessed, so a refused range stores nothing (`test_a_range_ending_in_the_future_is_refused_before_any_step_is_applied`, `test_a_range_starting_before_the_first_reading_is_refused_whole`).
  - Steps at or before the last applied instant are stored as replays, which may raise the latch (above); later steps are applied in order. The result counts `assessments`, `applied` and `replays_escalated`, and the states (`test_assess_range_run_first_applies_every_step_oldest_first`).
- **Whole-feed delay.** When every required signal of an asset is older than `max_data_age_hours` (1 h for wind) at the assessment instant, the assessment reports `data_delivery_delay` instead of per-signal `stale_data`. The state is DATA_QUALITY_FAILURE. Decision generation while the delay lasts raises no instrument check at the asset (`test_a_feed_delay_is_a_data_path_problem_not_an_instrument_check`). An inspection latched before the delay still gets its P2 inspection order (`test_a_latched_inspection_hidden_by_a_data_failure_gets_its_inspection_order`).
  - **Known gap: the recovery can raise an instrument check.** A data-quality failure clears only after `dq_clear_after` (2) consecutive good assessments (`states.advance`, `configs/platform.yaml`). A MODEL_UNAVAILABLE assessment whose data checks failed is not one of them (`test_a_model_outage_with_failing_data_does_not_count_toward_clearing_a_data_failure`). After the first good assessment the asset is still DATA_QUALITY_FAILURE, but that assessment's reasons carry no data-quality code. `decision._planned` (behind `decision.recommend`) checks only those reasons, so it does not recognise the delay and raises an `instrument_check` order (P2 for criticality A or B) if decision generation runs before the second good assessment. This follows from the code and was reproduced on a test asset again after the re-review fixes; no test covers it, and the fix (in `decision._planned`) is not made.
  - With `assess_at: latest_reading` the default instant follows the data, so a stopped export does not produce `data_delivery_delay`. Repeat assessments at the same instant are replays. The asset shows ASSESSMENT_OVERDUE once its last applied assessment is older than `max_assessment_age_hours` (26 h for wind), and the staleness report lists its signals. This follows from the code; no dedicated test.
- **Upgraded databases** (migration `0008_upgrade_backfill.sql`). State rows written before migration 0006 had no last applied instant or time. Migration 0008 backfills both from the asset's applied assessments: the latest instant, counted at most up to the time it was stored plus 5 minutes (so a mistyped future instant cannot freeze the live state), and the time the latest one was stored. Back-dated assessments on an upgraded asset therefore stay replays, and ASSESSMENT_OVERDUE appears when assessments stop. A state row with a result but no assessment rows counts every instant up to its last write as applied, and shows ASSESSMENT_OVERDUE until an assessment is applied (`test_an_upgraded_database_keeps_replays_out_of_the_live_state_and_reports_overdue`).

## 2. Asset registry contract

| object | required | notes |
|---|---|---|
| site | id, name, IANA time zone | |
| asset type | id, name, `time_basis` (`timestamp` or `cycle_index`), signals (name, unit, optional plausible range, required flag), jobs (`inspect` is mandatory; duration, skill, parts, crew) | `cycle_index` also requires a declared `usage_hours_per_cycle` |
| asset | id, tag, name, type, site, criticality A/B/C, consequence (downtime hours, cost per failure, safety and environmental impact, cost unit) | optional: maintenance windows (UTC-aware, end after start), operating context, config, installed date |

- Identity, type and site of an asset cannot change in place. Any other change needs a written reason and is audited with old and new values.
- **Wind commissioning baseline:** `asset.config.nbm_baselines[model_id]`. It holds the offsets, the period, the number of operating points, who set it, when, and why. It is written only through `nbm.commission` by a reliability engineer or admin.

## 3. Work-order and outcome contract

- **States:** DRAFT, PENDING_APPROVAL, APPROVED, SCHEDULED, IN_PROGRESS, COMPLETED, CLOSED, REJECTED, DEFERRED, CANCELLED.
  - Transitions are role-checked.
  - Rejecting, deferring, reactivating, unscheduling, handing back (`hand_back`: a scheduled or started job returns to APPROVED), cancelling and dismissing require a reason (`workorders.TRANSITIONS`).
  - Creation requires an idempotency key, which is stored with a payload hash: the same key with a different payload is a conflict (`workorders.create`). Transitions and completion accept a key but do not require one; re-prioritisation takes none. Every change, re-prioritisation included, is checked against `expected_version` when the caller passes it. Keys starting `rec:`, `reactivate:` or `apply:` belong to the platform, and the API refuses them from clients (400, `test_clients_cannot_use_the_engines_reserved_idempotency_keys`).
  - **Re-prioritisation** (`workorders.reprioritise`). A system escalation never moves a due date later; a person may set any date. Without a new score the order keeps its own, so a manual change through the API (which passes none) keeps it. The event records only the fields that changed (`test_an_escalation_never_postpones_an_earlier_due_date`, `test_a_manual_reprioritisation_keeps_the_score_and_records_only_what_changed`).
- **Outcome on completion** (`workorders.Outcome`):
  - `findings_code`: `no_fault_found`, `degradation_found`, `failure_found`, `not_inspected` or `other`;
  - `failure_confirmed`: `yes`, `no` or `unknown`;
  - `root_cause` (text);
  - `actions_taken` (required);
  - `parts_used` (part → quantity);
  - `downtime_hours`;
  - `returned_to_service_at` (optional, UTC-aware);
  - `notes`.
  - Contradictions are flagged rather than rejected. Example: `no_fault_found` together with parts used.
  - **Effect on a latched warning (PD-16, refined by PD-28).** A completion clears a latched URGENT_REVIEW or INSPECTION_RECOMMENDED only if all of these hold (`workorders._latch_keep_reasons`):
    - a person completed it (technician, planner or admin). A reliability engineer cannot complete an order (`workorders.TRANSITIONS`), and a completion by the `integration` role never clears;
    - the order was raised after the latch began, or was linked to it by a system escalation recorded after it began (`workorders.addresses_latch`); an unknown latch start fails closed;
    - the job addresses the equipment (`workorders.clears_latches`): not `instrument_check` or `desk_review`, nor a data or review job named in the site's decision config or recorded in any system order's explanation, whichever route completes it (`test_a_renamed_data_job_never_clears_a_latch_through_the_api`);
    - the findings are `degradation_found`, `failure_found` or `no_fault_found`; `not_inspected` and `other` keep the latch.
  - A kept latch adds `latch_kept` to the outcome's flags and its reasons to the asset's notes. A completion that clears or keeps a latch is recorded in the asset's audit history (`asset_state.maintenance_completed`, `asset_state.latch_kept`, `test_latch_changes_on_completion_are_in_the_assets_audit_history`).
- **Export.** `GET /api/v1/export/work-orders.csv`. Formula-leading cells are neutralised (PD-14).

## 4. Model artefact contract

A bundle directory contains `bundle.pkl` and `manifest.json`. The manifest records:
- model id, family, version, asset type and scope key;
- the prediction kind: `rul` or `anomaly`;
- the SHA-256 of the artefact;
- what the model was trained on, including its **data class**: SYNTHETIC, SIMULATED, PUBLIC_REAL_FIELD or REAL_FIELD;
- its evaluation and its limitations;
- the history points and required signals it needs.

At registration the registry hashes `bundle.pkl` and refuses a bundle whose bytes do not match the checksum in its own manifest (`test_registration_refuses_an_artefact_that_does_not_match_its_manifest`). It stores that checksum, and scoring refuses an artefact whose bytes differ from it. Manifests are not signed (`KNOWN_LIMITATIONS.md` S3).

## 5. External dataset mapping (PLANNED for G0)

Public datasets name their signals differently: CARE to Compare anonymises them as numbered features with text descriptions. Each farm gets a committed mapping file (`product/evidence/g0/feature_mapping_<farm>.json`) from source feature to canonical signal and role (input or target). The file is written from the descriptions alone, before any labels are read (`product/evidence/g0/PREREGISTRATION.md` §2). Amendment 1 (§10.1) fixes the adapter rules:
- required inputs: active power, wind speed and ambient temperature; nacelle temperature and rotor (or generator) speed are optional, and an absent column is omitted, not imputed;
- rated power: the 99.5th percentile of normal-status active power in the training part;
- for temperature columns, an exact 0.0 is treated as missing.

No mapping file exists yet: no CARE data have been downloaded.

## 6. Data classes (labels used in every document and manifest)

| class | meaning | examples here |
|---|---|---|
| SIMULATED | produced by a physics or system simulator built by others | NASA C-MAPSS |
| SYNTHETIC | produced or corrupted by our own code | `synthetic_wind.py`; injected sensor faults |
| PUBLIC REAL FIELD | measured on operating assets, published | CARE to Compare, Kelmarsh, Penmanshiel, Hill of Towie (not yet downloaded) |
| CUSTOMER REAL FIELD | a customer's own data under an agreement | none |
