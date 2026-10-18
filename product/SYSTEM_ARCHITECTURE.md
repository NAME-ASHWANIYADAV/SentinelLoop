# System architecture

**Status:** describes the code on branch `product/platform` as of 2026-10-18. Components marked PLANNED do not exist yet. "Tested" means automated tests on SIMULATED or SYNTHETIC data; nothing has run at a customer site. Decisions: PD-06 (modular monolith), PD-07 to PD-14 (PD-09, the scheduling defaults, is superseded by PD-27), and PD-16 to PD-22, PD-24 and PD-27 (Phase 5–9 changes).

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
| B | Ingestion: contract v1, reason codes, idempotent batches, quality flags, staleness; at most 200,000 readings per request | `ingest.py` | IMPLEMENTED_AND_TESTED | `test_app_ingest.py`, `test_app_remediation_security.py` |
| C | Health and prediction: data-quality gates, scope checks, model scoring, health states with latching; assessment instants, replays and freshness (PD-17) | `health.py`, `states.py`, `risk.py`, `modelpack.py` (C-MAPSS RUL), `nbm.py` (wind anomaly) | IMPLEMENTED_AND_TESTED (SIMULATED/SYNTHETIC data only) | `test_app_states.py`, `test_app_health.py`, `test_app_wind.py`, `test_app_failure_injection.py`, `test_app_remediation.py` |
| D | Decision engine: deterministic priority, due date and explanation; never invents a probability; rejection suppression; site parameters from a YAML file (PD-24) | `decision.py` | IMPLEMENTED_AND_TESTED | `test_app_decision.py`, `test_app_remediation.py` |
| E | Scheduling: technicians, skills, shifts, parts, windows; greedy and MILP; independent validator; proposals applied by a planner | `scheduler.py`, `planning.py`, `resources.py` | IMPLEMENTED_AND_TESTED; value SIMULATED (see `SCHEDULING_EVALUATION.md` (S2)) | `test_app_scheduler.py`, `test_app_planning.py` |
| F | Work-order workflow: 10 states, role-checked transitions, idempotency, optimistic concurrency, re-prioritisation, hand-back, return of deferred orders on their date; latch clearing on a qualifying completion (PD-16, PD-18) | `workorders.py` | IMPLEMENTED_AND_TESTED | `test_app_workorders.py`, `test_app_remediation.py` |
| G | Outcome feedback: outcome records with contradiction flags (including `latch_kept`), missing-outcome list | `workorders.py` | IMPLEMENTED_AND_TESTED; use of outcomes for retraining or threshold review: PLANNED | same |
| H | Model operations: registry (candidate, approved, retired), human approval, rollback, checksum trust anchor (registration refuses a `bundle.pkl` that does not match its manifest), per-asset commissioning | `modelreg.py`, `modelpack.py`, `nbm.py` | IMPLEMENTED_AND_TESTED; drift-triggered retraining for wind: PLANNED. Retraining and drift monitoring exist only in the frozen competition pipeline (`src/sentinelloop/retrain.py`, `drift.py`), not in the platform | `test_app_health.py`, `test_app_wind.py`, `test_app_remediation_security.py` |
| I | Audit: HMAC chain in the same transaction as each change, anchor, verification, history per entity. The chain covers audit events, not the state tables (PD-22) | `auditlog.py`, `db.py`, `admin.py` (`verify-audit` needs an anchor unless `--allow-no-anchor`) | IMPLEMENTED_AND_TESTED | `test_app_foundation.py`, `test_app_admin.py`, `test_app_remediation_security.py` |
| J | Operator console: thin Streamlit client of the REST API. Binds to 127.0.0.1 (`.streamlit/config.toml`); API URL from `SENTINELLOOP_API_URL` on the server, never from the user; API text rendered in code spans (PD-21). Site-local times on the Fleet, Asset and Schedule pages only; the Work queue and Do the work pages show work-order times in UTC, and the return-to-service time is read as UTC although the field says local time (`_tz(None)`) | `src/sentinelloop/console/app.py`, `src/sentinelloop/console/client.py` | IMPLEMENTED_AND_TESTED (headless Streamlit runs against the real API) for the login form and the Fleet, Asset, Work queue and Do the work pages; the Schedule and Audit pages are implemented with no automated test; no operator has used it | `test_console.py` (13 tests), `test_app_remediation_security.py` |
| — | API, security, administration | `api.py`, `security.py`, `admin.py` | IMPLEMENTED_AND_TESTED | `test_app_api.py`, `test_app_admin.py`, `test_app_remediation_security.py` |
| — | Integration with a CMMS: Odoo JSON-2 adapter and signed webhooks, read-only shadow mode by default (PD-20) | `integration.py`, migration `0005_integration.sql` | IMPLEMENTED_AND_TESTED against a contract test double only. Real Odoo sandbox NOT RUN (image download awaiting approval); no customer CMMS | `test_app_integration.py`, `test_app_remediation_security.py`, `test_app_api.py`; `test_app_odoo_sandbox.py` (opt-in, skipped) |

## 3. Key flows

**Assessment** (`health.assess`). For one asset at one instant:
- **The instant.** By default `now`, or the latest reading when the asset type's policy says `assess_at: latest_reading` (periodic exports). An instant more than 5 minutes in the future is refused.
- **Checks**, in this order:
  1. Generic data quality: required signals present and fresh; missing and suspect shares. When every required signal is late together, the single reason is `data_delivery_delay` (a late feed, not a sensor fault).
  2. Selection of an approved model. Its checksum is verified against the registry. An integrity failure is always reported, whatever the other models' scope.
  3. Operating scope: history, envelope, regime, idle turbine; for wind, a commissioned baseline.
  4. Model-specific data quality: stuck sensors, conflicting relations. Regime-independent checks run even out of scope (PD-13).
  5. Sensor-range scope.
  6. Scoring.
- **Storing.** The result is stored with its inputs reference, model checksum and resolved policy (with its SHA-256), in the same transaction as the audit event. A prediction is exposed only when every gate passes.
- **Live state or replay.** The asset state advances only when the instant is later than the last applied one. An assessment for an earlier or equal instant is stored as a replay (`applied_to_state = 0`): it never moves the live state, and `latest_assessment` ignores it. `health.assess_range` (`POST /assets/{id}/assess-range`) assesses every step of a period, oldest first and at most 2,000 steps per call, to catch up after a periodic export (PD-17).

**Freshness** (`health.asset_view`). Every asset listing carries `last_assessed_at` (wall-clock time of the last applied assessment) and the last assessment instant. When the last applied assessment is older than `max_assessment_age_hours` (6 h by default, 26 h for wind, `configs/platform.yaml`), the label ASSESSMENT_OVERDUE is added, so a stopped assessment job never leaves a fleet looking healthy. The labels an asset can show are its state, NOT_ASSESSED, AWAITING_ASSESSMENT, INSPECTION_PENDING, ASSESSMENT_OVERDUE and HUMAN_APPROVAL_REQUIRED.

**Decision** (`decision.generate`, per asset, errors isolated and audited):
- **Deferred orders first.** Deferred orders whose date has passed return to PENDING_APPROVAL (`workorders.reactivate_due`).
- **State → recommendation.**
  - URGENT_REVIEW → P1 repair, or P1 inspection when the type defines no repair job (wind). For an anomaly model the wording makes no failure-time claim.
  - INSPECTION_RECOMMENDED → P2 inspection; P1 on a safety-impact asset when P(failure) ≥ `p_safety`.
  - DATA_QUALITY_FAILURE → instrument check, or an inspection if the type has none (P2 for criticality A/B, P3 for C), also while an inspection is latched (the asset then also shows INSPECTION_PENDING). No order when every data reason is `data_delivery_delay`.
  - Out of scope or unavailable while an inspection is latched → P2 inspection; the asset also shows INSPECTION_PENDING.
  - Out of scope or unavailable otherwise → P3 desk review (an inspection if the type has no desk-review job), for criticality-A assets only.
  - NORMAL_MONITORING on a safety-impact asset with `p_safety` ≤ P(failure) < `p_inspect` → P2 inspection.
- **Due date.** From the prediction interval when there is one, keeping P(failure before the job ends) ≤ `p_accept`. That probability is not calibrated: on SIMULATED data the nominal 5% rule was violated 9–18% of the time in late life (C2, `product/evidence/calibration/c2.md`). Otherwise the policy default per priority class.
- **Ranking within a class.** P(failure) × consequence per technician-hour. For anomaly models, the deviation ratio × consequence per technician-hour, which is not a probability.
- **The work order.** It is created awaiting approval, escalated, or left unchanged. A recommendation is not re-raised:
  - for an assessment that already produced an order (`already_decided`);
  - for the same condition within 24/168/720 h (P1/P2/P3) of a reasoned rejection, unless it escalates (`suppressed`).
  Escalating a deferred order to P1 brings it back for approval. When every open order on the asset is IN_PROGRESS, the recommendation outranks them, and its assessment has not already produced an order, a separate order is created at the recommended priority (P1 when the condition is urgent). The order is **never executed** by the system.

**Completion and latches** (`workorders.complete`, PD-16). An outcome is required. The latch is cleared only when all of these hold:
- the order was created after the latch began;
- its job is not `instrument_check` or `desk_review`;
- the findings are `degradation_found`, `failure_found` or `no_fault_found`;
- the role is technician, planner or admin. The integration role can complete an order but never clears a latch; reliability engineers cannot complete orders (`TRANSITIONS["complete"]`).

Otherwise the latch is kept, the outcome carries the `latch_kept` flag and the reasons are noted on the asset. An unknown latch start keeps the latch. A cleared asset shows AWAITING_ASSESSMENT until its next assessment. `POST /assets/{id}/clear-risk` records only dismissals with a reason, by planners, reliability engineers and admins.

**Planning**. `planning.plan` builds a problem from approved orders and the recorded technicians, shifts, parts and windows. It stores a proposal with any violations and changes nothing. `planning.apply` (a planner) schedules each order through the workflow and refuses a stale or infeasible proposal. Where a site has a recorded crew list, only its registered, active technicians can be assigned. A crew that cannot do a job hands it back (`hand_back`): the order returns to APPROVED with its schedule cleared.

**Integration dispatch** (`integration.dispatch`, PD-20). Called by the admin or integration role through `POST /integrations/{id}/dispatch`, normally from a scheduler.
- **What is sent.** Only APPROVED, SCHEDULED and IN_PROGRESS orders. Once an order has been sent (or recorded in shadow mode), its later CANCELLED, REJECTED, DEFERRED, COMPLETED and CLOSED states are mirrored onto the request as text, with a lower priority for withdrawn and deferred work. Only the cancelled and deferred cases have automated tests (`test_app_remediation_security.py::test_cancelled_or_deferred_orders_are_marked_in_the_cmms`); rejected, completed and closed have none.
- **Modes.** In shadow mode (the default) the dispatcher records what it would send and makes no external call. In `draft_requests` mode it upserts maintenance requests marked `[SentinelLoop]`, writing only allowlisted fields. It never changes stages, closes or deletes CMMS records.
- **Checks at every dispatch.** The host must be in `SENTINELLOOP_INTEGRATION_HOSTS`. URLs may not carry credentials, a query or a fragment. Credentials come only from `SENTINELLOOP_CRED_*` variables.
- **Failures.** Transient failures are retried with backoff; permanent ones become dead letters that an admin requeues with a reason.
- **Lost mappings.** A first send never adopts an existing record. A lost mapping is recovered by marker only after a logged earlier delivery.

**Console** (`sentinelloop.console`). Pages: Fleet, Asset, Work queue, Schedule, Do the work, Audit. Action buttons are shown only to roles the API allows, and the API checks again.
- **What it does.** Show the fleet and an asset's assessment; assess now; generate recommendations; approve, defer or reject; list deferred orders and bring them back early; propose and apply a schedule; start, hand back or complete a job with an outcome; dismiss a latched warning (dismissers only, only while something is latched); read audit histories; verify the audit chain (admin, reliability engineer).
- **What it cannot do.** Raise a follow-up job, edit shifts or re-prioritise an order (KNOWN_LIMITATIONS P11). Ingest data, commission turbines, approve models or manage users and integrations. These go through the API or the CMMS.

## 4. Storage

- **SQLite** in WAL mode, with foreign keys on and `BEGIN IMMEDIATE` write transactions.
- **Migrations** `0001`–`0007` are forward-only and checksummed. An edited migration is refused.
  - `0005_integration`: integration targets, sync items and the integration log.
  - `0006_state_integrity`: latch start, awaiting-assessment flag, last applied instant and time on asset states; `applied_to_state` on assessments.
  - `0007_backfill_latch_start`: gives latches that predate 0006 a start equal to their last update, which is at or after the true start, so older work cannot clear them.
- **Instants** are integer epoch milliseconds, UTC.
- **Backups** use the SQLite online backup API, plus an audit-anchor file (`admin backup`). The anchor reveals truncation of the restored chain. Recovery drill R1 (`product/evidence/recovery/r1.md`, one laptop, SYNTHETIC data) restored and verified a database against its anchor.
- **Model bundles** are files on disk. The registry row holds the path and the SHA-256, and loading refuses any mismatch. Pickles are loaded only after that check.
- **Scale assumption**: one site, up to a few hundred assets, 10-minute data. Measured only in the Phase 9 L1 re-run, for 50 SYNTHETIC turbines on one development laptop (`product/evidence/load/l1.md`): whole-fleet assessment 7.2 s with 4 clients against a 600 s interval; a few hundred assets not measured. The migrations are plain SQL so that PostgreSQL is a port, not a redesign.

## 5. Configuration

| item | where | changed by |
|---|---|---|
| data-quality limits, scope tolerances, risk horizons, state thresholds, default assessment instant (`assess_at`), overdue limit (`max_assessment_age_hours`) | `configs/platform.yaml` (per asset type); SHA-256 stored with each assessment | review (policy change) |
| decision rules (`p_accept`, `p_safety`, default due dates, rejection-suppression periods, job types, labour and downtime cost) | `DecisionConfig` placeholder defaults, or a site YAML via `admin serve --decision-config FILE` (example: `configs/decision.example.yaml`; unknown keys and negative values refused). `/api/v1/ready` reports `decision_config`: site-configured or placeholder defaults | site review, then a restart |
| audit key and key id; database path | environment: `SENTINELLOOP_AUDIT_KEY`, `SENTINELLOOP_AUDIT_KEY_ID`, `SENTINELLOOP_DB` | operations (secret store) |
| users, roles, API keys | database, via `admin create-admin` and `/api/v1/users` | admin |
| CMMS and webhook targets (kind, URL, mode) | database, via `/api/v1/integrations` (registered and switched by admins only; their config is shown to admins only); allowed hosts in `SENTINELLOOP_INTEGRATION_HOSTS`; credentials only in `SENTINELLOOP_CRED_*` environment variables | admin; operations (secret store) |
| console | API URL from `SENTINELLOOP_API_URL` (server side); bind address 127.0.0.1:8501 in `.streamlit/config.toml` | operations |

## 6. Deliberate exclusions

- No write path to control systems or PLCs, and no OT network connection. Data arrive as exports or through a historian API (PLANNED).
- No automatic execution of maintenance work. Every action passes a named person's approval in the workflow (principle 8).
- No learned component decides priorities. The decision engine is a rule table, inspectable and versioned.
- No multi-tenant hosting. One deployment serves one customer.
- No built-in job scheduler. Assessments, decision runs (which also return deferred orders), dispatch and backups are started by an external scheduler such as cron (KNOWN_LIMITATIONS P5).
