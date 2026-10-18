# System architecture

**Status:** describes the code on branch `product/platform` as of 2026-10-18. Components marked PLANNED do not exist yet. "Tested" means automated tests on SIMULATED or SYNTHETIC data; nothing has run at a customer site. Decisions: PD-06 (modular monolith), PD-07 to PD-14 (PD-09, the scheduling defaults, is superseded by PD-27), PD-15 (wind alarm persistence, set by W3), PD-16 to PD-22, PD-24 and PD-27 (Phase 5–9 changes), and PD-28 (the rules from the re-review of the Phase 9 fixes).

## 1. Shape

A **modular monolith**: one Python package (`sentinelloop.app`), one SQLite database, one REST process, one operator console, and a CLI for administration. There are no microservices, no message broker and no deep-learning service (principles 4–5). Everything is designed to run on one site server or VM; so far it has run only on one development laptop (`DEPLOYMENT_GUIDE.md`).

The console (`sentinelloop.console`) is a separate Streamlit process, but it holds no data and never opens the database: it is a thin client of the REST API, and every call carries the signed-in user's own API key (PD-21). The CMMS connector is a module inside the same package and runs when an admin or the integration role calls its dispatch route. Neither changes the one-process, one-database position.

```
  SCADA / historian exports        Operators (browser)               CMMS: Odoo JSON-2, or a signed webhook
  (CSV or JSON, export job)                |                         shadow by default; tested only against a
          |                                v                         contract test double; real Odoo NOT RUN
          |                    +------------------------+                           ^
          |                    | Operator console       |                           | approved work only
          |                    | Streamlit thin client  |                 +---------+----------+
          |                    | 127.0.0.1, user's key  |                 | Integration        |
          |                    +-----------+------------+                 | dispatcher         |
          v                                v                              | (targets, sync     |
  +--------------------------------------------------------------+        |  items, retries,   |
  | REST API /api/v1 (api.py): authentication, roles, limits;    |        |  dead letters)     |
  | its routes reach every module below                          |        +---------+----------+
  +--------------------------------------------------------------+                  ^
          |                                                                         |
          v                                                                         |
  +---------------+   +---------------+   +--------------+   +------------+         |
  | Readings store|-->|  Assessment   |-->|  Decision    |-->| Work-order |---------+
  | (quality flags|   |  (DQ, scope,  |   |  engine      |   | workflow   |
  |  batches)     |   |  model, state)|   | (rules, site |   | (approval, |
  +---------------+   +-------+-------+   |  parameters) |   |  lifecycle)|
                              |           +--------------+   +-----+------+
                      +-------v-------+                    +-------v------+
                      | Model registry|                    |  Planning /  |
                      | + bundles     |                    |  scheduler   |
                      | (checksummed) |                    | (proposals)  |
                      +---------------+                    +--------------+
          all writes ---> HMAC-chained audit log (same transaction) ---> exportable anchor
```

## 2. Responsibilities A–J and where they live

Modules are in `src/sentinelloop/app/` unless a path is given; tests are in `tests/`.

| | responsibility | module(s) | status | tests |
|---|---|---|---|---|
| A | Asset registry: sites, types (signals, jobs), assets (criticality, consequence, windows, config). Sites and asset types have no API route (KNOWN_LIMITATIONS P4) | `registry.py`, `models.py` | IMPLEMENTED_AND_TESTED | `test_app_foundation.py` |
| B | Ingestion: contract v1, reason codes, idempotent batches, quality flags, staleness; at most 200,000 readings per request | `ingest.py` | IMPLEMENTED_AND_TESTED | `test_app_ingest.py`, `test_app_remediation_security.py`, `test_app_rereview_api.py` |
| C | Health and prediction: data-quality gates, scope checks, model scoring, health states with latching; assessment instants, replays (which may only raise a latch) and freshness (PD-17, PD-28) | `health.py`, `states.py`, `risk.py`, `modelpack.py` (C-MAPSS RUL), `nbm.py` (wind anomaly) | IMPLEMENTED_AND_TESTED (SIMULATED/SYNTHETIC data only) | `test_app_states.py`, `test_app_health.py`, `test_app_wind.py`, `test_app_failure_injection.py`, `test_app_remediation.py`, `test_app_rereview_health.py` |
| D | Decision engine: deterministic priority, due date and explanation; never invents a probability; which open order stands in for a recommendation; rejection suppression; site parameters from a validated YAML file (PD-24, PD-28) | `decision.py` | IMPLEMENTED_AND_TESTED | `test_app_decision.py`, `test_app_remediation.py`, `test_app_rereview_decision.py` |
| E | Scheduling: technicians, skills, shifts, parts, windows; greedy and MILP; independent validator; proposals applied by a planner | `scheduler.py`, `planning.py`, `resources.py` | IMPLEMENTED_AND_TESTED; value SIMULATED (see `SCHEDULING_EVALUATION.md` (S2)). Building the MILP ignores its time limit; the API bounds its size instead (KNOWN_LIMITATIONS P14) | `test_app_scheduler.py`, `test_app_planning.py`, `test_app_rereview_api.py` |
| F | Work-order workflow: 10 states, role-checked transitions, idempotency, optimistic concurrency, re-prioritisation, hand-back, return of deferred orders on their date; latch clearing on a qualifying completion (PD-16, PD-18, PD-28) | `workorders.py` | IMPLEMENTED_AND_TESTED | `test_app_workorders.py`, `test_app_remediation.py`, `test_app_rereview_decision.py`, `test_app_rereview_wiring.py` |
| G | Outcome feedback: outcome records with contradiction flags (including `latch_kept`), missing-outcome list | `workorders.py` | IMPLEMENTED_AND_TESTED; use of outcomes for retraining or threshold review: PLANNED | same |
| H | Model operations: registry (candidate, approved, retired), human approval, rollback, checksum trust anchor (registration refuses a `bundle.pkl` that does not match its manifest), per-asset commissioning | `modelreg.py`, `modelpack.py`, `nbm.py` | IMPLEMENTED_AND_TESTED; drift-triggered retraining for wind: PLANNED. Retraining and drift monitoring exist only in the frozen competition pipeline (`src/sentinelloop/retrain.py`, `drift.py`), not in the platform | `test_app_health.py`, `test_app_wind.py`, `test_app_remediation_security.py` |
| I | Audit: HMAC chain in the same transaction as each change, anchor, verification, history per entity. Verification reports whether an anchor was checked (`anchor_checked`), and a malformed anchor is an error, never "no anchor". The chain covers audit events, not the state tables (PD-22) | `auditlog.py`, `db.py`, `admin.py` (`verify-audit` needs an anchor unless `--allow-no-anchor`) | IMPLEMENTED_AND_TESTED | `test_app_foundation.py`, `test_app_admin.py`, `test_app_remediation_security.py`, `test_app_rereview_api.py`, `test_app_rereview_wiring.py` |
| J | Operator console: thin Streamlit client of the REST API. Binds to 127.0.0.1 (`.streamlit/config.toml`, which also turns browser error details off); API URL from `SENTINELLOOP_API_URL` on the server, never from the user; API text rendered in code spans, and as plain text in tables (PD-21). Times are shown, and work-order dates and times entered, in the local time of the asset's site on every page except Audit, which lists event times in UTC | `src/sentinelloop/console/app.py`, `src/sentinelloop/console/client.py` | IMPLEMENTED_AND_TESTED (headless Streamlit runs against the real API) for the login form and the Fleet, Asset, Work queue and Do the work pages; the Schedule page is tested for proposing a plan, not for applying one, and the Audit page only for chain verification; no operator has used it | `test_console.py` (20 test functions), `test_app_remediation_security.py`, `test_app_rereview_wiring.py` |
| — | API, security, administration | `api.py`, `security.py`, `admin.py` | IMPLEMENTED_AND_TESTED | `test_app_api.py`, `test_app_admin.py`, `test_app_remediation_security.py`, `test_app_rereview_api.py`, `test_app_rereview_wiring.py` |
| — | Integration with a CMMS: Odoo JSON-2 adapter and signed webhooks, read-only shadow mode by default (PD-20, PD-28) | `integration.py`, migrations `0005_integration.sql` and `0009_integration_dispatch.sql` | IMPLEMENTED_AND_TESTED against a contract test double only. Real Odoo sandbox NOT RUN (image download awaiting approval); no customer CMMS | `test_app_integration.py`, `test_app_remediation_security.py`, `test_app_rereview_integration.py`, `test_app_api.py`; `test_app_odoo_sandbox.py` (opt-in, skipped) |

## 3. Key flows

**Assessment** (`health.assess`). For one asset at one instant:
- **The instant.** By default `now`, or the latest reading when the asset type's policy says `assess_at: latest_reading` (periodic exports). An instant more than 5 minutes in the future, earlier than 2000-01-01T00:00Z, or more than 5 minutes before the asset's first reading is refused before anything is stored (`health._check_instants`).
- **Checks**, in this order:
  1. Generic data quality: required signals present and fresh; missing and suspect shares. When every required signal is late together, the single reason is `data_delivery_delay` (a late feed, not a sensor fault).
  2. Selection of an approved model. Its checksum is verified against the registry. An integrity failure is always reported, whatever the other models' scope.
  3. Operating scope: history, envelope, regime, idle turbine; for wind, a commissioned baseline.
  4. Model-specific data quality: stuck sensors, conflicting relations. Regime-independent checks run even out of scope, including on an uncommissioned turbine, so a data failure takes precedence (PD-13). For wind, a stuck run anywhere in the span the model scores is a data failure, so the model never scores readings the check rejected. The rotor/generator relation is checked on the last window only (KNOWN_LIMITATIONS M11).
  5. Sensor-range scope.
  6. Scoring. For wind, a deviation is sustained only when it holds at each of the last `sustain` operating points; idle rows add no evidence. A bundle takes `sustain` (18 operating points, 3 h of operation, `nbm.SUSTAIN`) and the inspect margin (1.25, `nbm.INSPECT_MARGIN`) when it is fitted; both were chosen on SYNTHETIC fleets by W3's pre-stated rule (PD-15; `test_app_wind.py::test_shipped_inspection_threshold_is_the_one_w3_chose` ties them to `w3.json`). On fresh held-out SYNTHETIC fleets 60–65 they gave 0.44 healthy alarm episodes per turbine-year (1 in 2.27 turbine-years; 95% interval up to about 2.45, which does not exclude the proposed pilot ceiling of 2); drifting sensors still gave 39 alarm episodes (KNOWN_LIMITATIONS M1) and 1 alarm came before fault onset on those fleets. The generator shares the model's assumptions, so the real rate is unknown until G0 (KNOWN_LIMITATIONS E3, E7). An earlier run's setting (W2 run 2, sustain 6) gave 5.74 per turbine-year on its own held-out fleets 20–25 (`product/evidence/wind_synthetic/w3.md`, `w2.md`; interval: PD-15).
- **Storing.** The result is stored with its inputs reference, model checksum and resolved policy (with its SHA-256), in the same transaction as the audit event. A prediction is exposed only when every gate passes.
- **Live state or replay.** The asset state advances only when the instant is later than the last applied one. An assessment for an earlier or equal instant is stored as a replay (`applied_to_state = 0`), and `latest_assessment` ignores it.
  - A replay never lowers a latch or moves the rest of the live state. Latching is monotone toward more risk (`states.escalate`, PD-28): an URGENT_REVIEW or INSPECTION_RECOMMENDED replay above the latched risk raises the latch, starting at the wall-clock time, and is audited on the asset (`asset_state.escalated_by_replay`).
  - It raises nothing when an earlier assessment for the same instant already had that finding, so re-assessing the same latest reading cannot undo a dismissal or a completed inspection.
- **Data-failure recovery.** A DATA_QUALITY_FAILURE clears only after `dq_clear_after` consecutive assessments without a data failure; a MODEL_UNAVAILABLE assessment whose data checks failed is not one of them (`states.advance`).
- **Ranges.** `health.assess_range` (`POST /assets/{id}/assess-range`) assesses every step of a period, oldest first, to catch up after a periodic export (PD-17). It checks every instant before it assesses any, takes at most 2,000 steps (`MAX_RANGE_STEPS`), and reports `replays_escalated`. The API also charges one rate-limit token per 10 steps (at most 1,200 steps per call with the shipped limiter) and runs one range per user and two per server, so ranges never hold every worker thread (KNOWN_LIMITATIONS P13).

**Freshness** (`health.asset_view`). Every asset listing carries `last_assessed_at` (wall-clock time of the last applied assessment) and the last assessment instant. When the last applied assessment is older than `max_assessment_age_hours` (6 h by default, 26 h for wind, `configs/platform.yaml`), or the state shows a result with no assessment time on record, the label ASSESSMENT_OVERDUE is added, so a stopped assessment job never leaves a fleet looking healthy. The labels an asset can show are its state, NOT_ASSESSED, AWAITING_ASSESSMENT, INSPECTION_PENDING, ASSESSMENT_OVERDUE and HUMAN_APPROVAL_REQUIRED.

**Decision** (`decision.generate`; each deferred order, asset and recommended job is handled on its own, and an error is reported as `error` and audited without stopping the run):
- **Deferred orders first.** Deferred orders whose date has passed return to PENDING_APPROVAL (`workorders.reactivate_due`).
- **State → recommendations** (usually one per asset).
  - URGENT_REVIEW → P1 repair, or P1 inspection when the type defines no repair job (wind). For an anomaly model the wording makes no failure-time claim.
  - INSPECTION_RECOMMENDED → P2 inspection; P1 on a safety-impact asset when P(failure) ≥ `p_safety`.
  - DATA_QUALITY_FAILURE → instrument check, or an inspection if the type has none (P2 for criticality A/B, P3 for C). No instrument check when every data reason is `data_delivery_delay`. While an inspection is latched (the asset also shows INSPECTION_PENDING) its P2 inspection is recommended as well, also during a feed delay (PD-28).
  - Out of scope or unavailable while an inspection is latched → P2 inspection; the asset also shows INSPECTION_PENDING.
  - Out of scope or unavailable otherwise → P3 desk review (an inspection if the type has no desk-review job), for criticality-A assets only.
  - NORMAL_MONITORING on a safety-impact asset with `p_safety` ≤ P(failure) < `p_inspect` → P2 inspection.
- **Due date.** From the prediction interval when there is one, keeping P(failure before the job ends) ≤ `p_accept`. That probability is not calibrated: on SIMULATED data the nominal 5% rule was violated 9–18% of the time in late life (C2, `product/evidence/calibration/c2.md`). Otherwise the policy default per priority class.
- **Ranking within a class.** P(failure) × consequence per technician-hour. For anomaly models, the deviation ratio × consequence per technician-hour, which is not a probability.
- **Which open order stands in** (`decision._decide`, PD-28). A DRAFT never does.
  - A data or review job (as the site names them) is matched only by an open order for that job, and never stands in for an equipment job. An open equipment order covers a desk review, but never an instrument check.
  - An equipment job is matched by an open order for the recommended, inspection or urgent job that, while a latch is active, belongs to the current latch: raised after it began, or linked to it (`workorders.addresses_latch`). A routine job such as a lubrication never stands in.
  - Such an order from before the latch is **linked** only while it awaits approval or is deferred: it is escalated in place (class and due date only move earlier) and is up for approval again. The system escalation event is the link. An older one that is approved, scheduled or in progress is **superseded**: a new order is raised whose explanation names it.
- **The work order.** It is created awaiting approval, escalated, linked, or left unchanged. A recommendation is not re-raised:
  - for an assessment that already produced an order for that job (`already_decided`);
  - after a reasoned rejection, within 24/168/720 h by the rejected order's class (P1/P2/P3), unless the recommendation is of a higher class (`suppressed`). This applies on every creation path. While a latch is active, the condition is the latch episode, and any order that stood in for it counts; a new episode is raised again. When the latch start is unknown, a rejection holds until a dismissal or a clearing completion is audited for the asset. Otherwise the condition is the system's order for the same job and state.
  A deferred order that the engine escalates to a higher class, or links, comes back for approval; a system escalation keeps the earlier due date. A covering order that is awaiting approval, approved, scheduled or deferred is escalated in place first (`workorders.REPRIORITISABLE`). Only when every covering order is IN_PROGRESS and the recommendation outranks it is a separate order created at the recommended priority (P1 when the condition is urgent). The order is **never executed** by the system.

**Completion and latches** (`workorders.complete`, PD-16, refined by PD-28). An outcome is required. The latch is cleared only when all of these hold:
- the order was created after the latch began, or was linked to it by a system escalation recorded after it began;
- its job addresses the equipment (`workorders.clears_latches`): not `instrument_check` or `desk_review`, nor a data or review job named in the served decision config or recorded in a system order's explanation, on every completion path including the API route;
- the findings are `degradation_found`, `failure_found` or `no_fault_found`;
- the role is technician, planner or admin. The integration role can complete an order but never clears a latch; reliability engineers cannot complete orders (`TRANSITIONS["complete"]`).

Otherwise the latch is kept, the outcome carries the `latch_kept` flag and the reasons are noted on the asset. An unknown latch start keeps the latch. An order raised before the recorded start (which migration 0007 may have backfilled later than the true start) is kept with a reason that says so. Both outcomes are audited on the asset entity. A cleared asset shows AWAITING_ASSESSMENT until its next assessment. `POST /assets/{id}/clear-risk` records only dismissals with a reason, by planners, reliability engineers and admins.

**Planning**. `planning.plan` builds a problem from approved orders and the recorded technicians, shifts, parts and windows. It stores a proposal with any violations and changes nothing. The API requires slots of at least 0.25 h and refuses MILP above 5,000 approved orders × slots, because building the MILP ignores its time limit (KNOWN_LIMITATIONS P14). `planning.apply` (a planner) schedules each order through the workflow and refuses a stale or infeasible proposal. Where a site has a recorded crew list, only its registered, active technicians can be assigned. A crew that cannot do a job hands it back (`hand_back`): the order returns to APPROVED with its schedule cleared.

**Integration dispatch** (`integration.dispatch`, PD-20, PD-28). Called by the admin or integration role through `POST /integrations/{id}/dispatch`, normally from a scheduler.
- **What is sent.** Only APPROVED, SCHEDULED and IN_PROGRESS orders. Once an order has been sent (or recorded in shadow mode), its later CANCELLED, REJECTED, DEFERRED, COMPLETED and CLOSED states are mirrored onto the request as text, with a lower priority for withdrawn and deferred work. Only the cancelled and deferred cases have automated tests (`test_app_remediation_security.py::test_cancelled_or_deferred_orders_are_marked_in_the_cmms`); rejected, completed and closed have none.
- **Modes.** In shadow mode (the default) the dispatcher records what it would send and makes no external call. In `draft_requests` mode it upserts maintenance requests marked `[SentinelLoop]`, writing only allowlisted fields. It never changes stages, closes or deletes CMMS records.
- **One run per target.** A run holds the target's lease (10 minutes, renewed during the run, kept as events in the integration log). A second run reports `busy` and sends nothing. Before every external call and every recorded result the run checks that it still holds the lease and that the mode has not changed, and stops otherwise (`stopped`). A run whose lease lapsed never records a failure over a newer result and never replaces the stored CMMS id (`integration._record`). If it brings a second id for the order, the item becomes a dead letter for a person, even when the newer run had synced it (`test_a_duplicate_made_by_a_dispatcher_that_lost_its_lease_is_a_dead_letter_not_an_orphan`). A success it records is marked unsynced, so the next run sends the order again.
- **Checks.** At registration the URL and config values are validated. At every dispatch the host must be in `SENTINELLOOP_INTEGRATION_HOSTS`, URLs may not carry credentials, a query or a fragment, the credential names and database name are checked again, and the timeout is clamped to 120 s. Credentials come only from `SENTINELLOOP_CRED_*` variables.
- **Failures.** Transient failures are retried with backoff, up to `max_attempts`; permanent ones become dead letters that an admin requeues with a reason. An unexpected answer to a create or write (a body that is not JSON, or a create answer that is not a single id) is transient: it is retried, and a create's retry searches by marker first (`OdooJson2.call`, `OdooJson2.upsert`; `test_an_unexpected_answer_to_a_create_is_recorded_and_the_create_is_not_repeated`). An unexpected answer to a read (`_records`), or an unexpected error, is a dead letter for that order only (`test_a_sign_in_page_instead_of_the_api_gives_recorded_dead_letters_not_a_crash`, `test_an_unexpected_error_on_one_order_is_a_dead_letter_and_the_run_goes_on`). The run goes on in every case.
- **Lost mappings.** A first send never adopts an existing record. Each create is logged as attempted before it is sent. After an attempt whose answer was lost, the CMMS is searched by the delimited marker in the description (not the mirrored name) before any new create; a definite refusal (a 4xx other than 408 or 429, or a connection never made) is no such evidence. A recovered order is searched once more about an hour later (`verify_after_ms`, migration 0009). A second request carrying the marker makes a dead letter for a person (KNOWN_LIMITATIONS S10).
- **Webhooks.** `verify_webhook` rejects malformed headers. The signed body carries no delivery id or version (KNOWN_LIMITATIONS S9).

**Console** (`sentinelloop.console`). Pages: Fleet, Asset, Work queue, Schedule, Do the work, Audit. Action buttons are shown only to roles the API allows, and the API checks again.
- **What it does.** Show the fleet and an asset's assessment; assess now; generate recommendations (its message counts created, escalated and linked orders); approve, defer or reject; list deferred orders and bring them back early; propose and apply a schedule; start, hand back or complete a job with an outcome; dismiss a latched warning (dismissers only, only while something is latched); read audit histories; verify the audit chain (admin, reliability engineer; an unanchored check is shown as a warning, never as a pass).
- **What it cannot do.** Raise a follow-up job, edit shifts or re-prioritise an order (KNOWN_LIMITATIONS P11). Ingest data, commission turbines, approve models or manage users and integrations. These go through the API or the CMMS.

## 4. Storage

- **SQLite** in WAL mode, with foreign keys on and `BEGIN IMMEDIATE` write transactions.
- **Migrations** `0001`–`0009` are forward-only and checksummed. An edited migration is refused.
  - `0005_integration`: integration targets, sync items and the integration log.
  - `0006_state_integrity`: latch start, awaiting-assessment flag, last applied instant and time on asset states; `applied_to_state` on assessments.
  - `0007_backfill_latch_start`: gives latches that predate 0006 a start equal to their last update, which is at or after the true start, so older work cannot clear them.
  - `0008_upgrade_backfill`: on upgraded databases, backfills the last applied instant and time from the asset's applied assessments. The instant counts at most up to the time each assessment was stored plus 5 minutes, so a mistyped future instant cannot freeze the live state. A state row with a result but no assessments counts every instant up to its last write as applied and shows ASSESSMENT_OVERDUE until an assessment is applied (`test_an_upgraded_database_keeps_replays_out_of_the_live_state_and_reports_overdue`).
  - `0009_integration_dispatch`: `verify_after_ms` on sync items, the time of the marker search that re-checks a recovered order. The dispatch lease needs no table: it is kept as events in the integration log.
- **Instants** are integer epoch milliseconds, UTC.
- **Backups** use the SQLite online backup API, plus an audit-anchor file (`admin backup`). The anchor reveals truncation of the restored chain. Recovery drill R1 (`product/evidence/recovery/r1.md`, one laptop, SYNTHETIC data) restored and verified a database against its anchor.
- **Model bundles** are files on disk. The registry row holds the path and the SHA-256, and loading refuses any mismatch. Pickles are loaded only after that check.
- **Scale assumption**: one site, up to a few hundred assets, 10-minute data. Measured only in the Phase 9 L1 re-run, for 50 SYNTHETIC turbines on one development laptop (`product/evidence/load/l1.md`): whole-fleet assessment 7.2 s with 4 clients against a 600 s interval; a few hundred assets not measured. The migrations are plain SQL so that PostgreSQL is a port, not a redesign.

## 5. Configuration

| item | where | changed by |
|---|---|---|
| data-quality limits, scope tolerances, risk horizons, state thresholds, default assessment instant (`assess_at`), overdue limit (`max_assessment_age_hours`) | `configs/platform.yaml` (per asset type); SHA-256 stored with each assessment | review (policy change) |
| decision rules (`p_accept`, `p_safety`, default due dates, rejection-suppression periods, job types, labour and downtime cost) | `DecisionConfig` placeholder defaults, or a site YAML via `admin serve --decision-config FILE` (example: `configs/decision.example.yaml`). Refused at load: unknown keys, numbers that are not finite, probabilities outside [0, 1), negative costs, due-date or suppression maps without exactly P1, P2 and P3 or with hours beyond one year (or a due date of 0 h), empty job names, and an urgent or inspection job named like a data or review job. `serve` exits with code 2 when a registered asset type lacks the configured `inspection_job`. `/api/v1/ready` reports `decision_config`: site-configured or placeholder defaults | site review, then a restart |
| API rate limit | `admin serve --rate-limit CAPACITY,REFILL` (default 120, 2/s per user or client). The `assess-range` steps allowed per call follow the capacity (10 per token, at most 2,000) | operations, then a restart |
| audit key and key id; database path | environment: `SENTINELLOOP_AUDIT_KEY`, `SENTINELLOOP_AUDIT_KEY_ID`, `SENTINELLOOP_DB` | operations (secret store) |
| users, roles, API keys | database, via `admin create-admin` and `/api/v1/users` | admin |
| CMMS and webhook targets (kind, URL, mode) | database, via `/api/v1/integrations` (registered and switched by admins only; their config, host and error text are shown to admins only; no config-update route, KNOWN_LIMITATIONS S11); allowed hosts in `SENTINELLOOP_INTEGRATION_HOSTS`; credentials only in `SENTINELLOOP_CRED_*` environment variables | admin; operations (secret store) |
| console | API URL from `SENTINELLOOP_API_URL` (server side); bind address 127.0.0.1:8501 and `[client] showErrorDetails = "none"` in `.streamlit/config.toml` | operations |

## 6. Deliberate exclusions

- No write path to control systems or PLCs, and no OT network connection. Data arrive as exports or through a historian API (PLANNED).
- No automatic execution of maintenance work. Every action passes a named person's approval in the workflow (principle 8).
- No learned component decides priorities. The decision engine is a rule table, inspectable and versioned.
- No multi-tenant hosting. One deployment serves one customer.
- No built-in job scheduler. Assessments, decision runs (which also return deferred orders), dispatch and backups are started by an external scheduler such as cron (KNOWN_LIMITATIONS P5).
