# Data contracts

What SentinelLoop accepts, what it refuses, and what it promises about stored data. Every rule below is implemented and tested unless it is marked PLANNED. Code: `src/sentinelloop/app/ingest.py`, `registry.py`, `models.py`, `workorders.py`. Tests: `tests/test_app_ingest.py`, `tests/test_app_foundation.py`, `tests/test_app_workorders.py`.

## 1. Readings contract v1

**Shape: long format, one reading per row.**

| field | type | rule |
|---|---|---|
| `asset` | string | the asset's id or tag. Ids and tags share one namespace, so a key that could mean two assets is rejected (`ambiguous_asset`) |
| `timestamp` | ISO-8601 | must carry a UTC offset (`Z` or `+05:30`). A naive timestamp is accepted only if the batch declares `default_tz`; otherwise it is rejected (`naive_timestamp`). Stored as integer epoch milliseconds, UTC |
| `signal` | string | a signal name defined by the asset's type (`unknown_signal` otherwise) |
| `value` | number | finite. Empty means missing and is not stored. `NaN`/`inf` → `non_finite_value`; text → `non_numeric_value` |
| `unit` | string | must equal the type's unit for that signal exactly. **There is no silent conversion**: `degF` for a `degC` signal is `unit_mismatch` |

**Wide CSV** (one column per signal) is accepted only when the caller states the unit of every signal column (`wide_units`). A missing unit gives `missing_units`; required columns that are absent give `missing_columns`.

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
- **Staleness.** `GET /api/v1/ingest/staleness` lists the required signals of active assets with no reading newer than the limit.

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
  - Rejecting, deferring, cancelling and dismissing require a reason.
  - Every change carries an idempotency key (with a payload hash) and is checked against `expected_version`.
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
- **Export.** `GET /api/v1/export/work-orders.csv`. Formula-leading cells are neutralised (PD-14).

## 4. Model artefact contract

A bundle directory contains `bundle.pkl` and `manifest.json`. The manifest records:
- model id, family, version, asset type and scope key;
- the prediction kind: `rul` or `anomaly`;
- the SHA-256 of the artefact;
- what the model was trained on, including its **data class**: SYNTHETIC, SIMULATED, PUBLIC_REAL_FIELD or REAL_FIELD;
- its evaluation and its limitations;
- the history points and required signals it needs.

The registry stores the checksum at registration. Scoring refuses an artefact whose bytes differ from it.

## 5. External dataset mapping (PLANNED for G0)

Public datasets name their signals differently: CARE to Compare anonymises them as numbered features with text descriptions. Each farm gets a committed mapping file (`product/evidence/g0/feature_mapping_<farm>.json`) from source feature to canonical signal and role (input or target). The file is written from the descriptions alone, before any labels are read (`product/evidence/g0/PREREGISTRATION.md` §2).

## 6. Data classes (labels used in every document and manifest)

| class | meaning | examples here |
|---|---|---|
| SIMULATED | produced by a physics or system simulator built by others | NASA C-MAPSS |
| SYNTHETIC | produced or corrupted by our own code | `synthetic_wind.py`; injected sensor faults |
| PUBLIC REAL FIELD | measured on operating assets, published | CARE to Compare, Kelmarsh, Penmanshiel, Hill of Towie (not yet downloaded) |
| CUSTOMER REAL FIELD | a customer's own data under an agreement | none |
