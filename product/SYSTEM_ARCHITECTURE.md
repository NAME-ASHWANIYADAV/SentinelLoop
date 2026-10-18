# System architecture

**Status:** describes the code on branch `product/platform` as of 2026-10-18. Components marked PLANNED do not exist yet. Decisions: PD-06 (modular monolith) and PD-07 to PD-14.

## 1. Shape

A **modular monolith**: one Python package (`sentinelloop.app`), one SQLite database, one REST process, one operator console, and a CLI for administration. There are no microservices, no message broker and no deep-learning service (principles 4–5). Everything runs on one site server or VM.

```
  SCADA / historian exports           Operators (browser)            CMMS (Odoo sandbox; customer CMMS later)
  (CSV, JSON records)                        |                               ^   (PLANNED, Phase 6:
          |                                  v                               |    read-only shadow by default)
          v                         +-----------------+            +-------------------+
  +---------------+   REST /api/v1  |  Operator UI    |            | Integration outbox |
  |  Ingestion    |<----------------|  (PLANNED)      |            | + CMMS adapters    |
  |  contract v1  |                 +-----------------+            +-------------------+
  +-------+-------+                          |                               ^
          v                                  v                               |
  +---------------+   +---------------+   +--------------+   +------------+  |
  | Readings store|-->|  Assessment   |-->|  Decision    |-->| Work-order |--+
  | (quality flags|   |  (DQ, scope,  |   |  engine      |   | workflow   |
  |  batches)     |   |  model, state)|   | (rules)      |   | (approval) |
  +---------------+   +-------+-------+   +--------------+   +-----+------+
                              |                                    |
                      +-------v-------+                    +-------v------+
                      | Model registry|                    |  Planning /  |
                      | + bundles     |                    |  scheduler   |
                      | (checksummed) |                    | (proposals)  |
                      +---------------+                    +--------------+
          all writes ---> HMAC-chained audit log (same transaction) ---> exportable anchor
```

## 2. Responsibilities A–J and where they live

| | responsibility | module(s) | status | tests |
|---|---|---|---|---|
| A | Asset registry: sites, types (signals, jobs), assets (criticality, consequence, windows, config) | `registry.py`, `models.py` | IMPLEMENTED_AND_TESTED | `test_app_foundation.py` |
| B | Ingestion: contract v1, reason codes, idempotent batches, quality flags, staleness | `ingest.py` | IMPLEMENTED_AND_TESTED | `test_app_ingest.py` |
| C | Health and prediction: data-quality gates, scope checks, model scoring, health states with latching | `health.py`, `states.py`, `risk.py`, `modelpack.py` (C-MAPSS RUL), `nbm.py` (wind anomaly) | IMPLEMENTED_AND_TESTED (SIMULATED/SYNTHETIC data only) | `test_app_states.py`, `test_app_health.py`, `test_app_wind.py` |
| D | Decision engine: deterministic priority, due date and explanation; never invents a probability | `decision.py` | IMPLEMENTED_AND_TESTED | `test_app_decision.py` |
| E | Scheduling: technicians, skills, shifts, parts, windows; greedy and MILP; independent validator; proposals applied by a planner | `scheduler.py`, `planning.py`, `resources.py` | IMPLEMENTED_AND_TESTED; value SIMULATED | `test_app_scheduler.py`, `test_app_planning.py`, `SCHEDULING_EVALUATION.md` |
| F | Work-order workflow: 10 states, role-checked transitions, idempotency, optimistic concurrency, re-prioritisation | `workorders.py` | IMPLEMENTED_AND_TESTED | `test_app_workorders.py` |
| G | Outcome feedback: outcome records with contradiction flags, missing-outcome list | `workorders.py` | IMPLEMENTED_AND_TESTED; use of outcomes for retraining or threshold review: PLANNED | same |
| H | Model operations: registry (candidate, approved, retired), human approval, rollback, checksum trust anchor, per-asset commissioning | `modelreg.py`, `modelpack.py`, `nbm.py` | IMPLEMENTED_AND_TESTED; drift-triggered retraining for wind: PLANNED | `test_app_health.py`, `test_app_wind.py` |
| I | Audit: HMAC chain in the same transaction as each change, anchor, verification, history per entity | `auditlog.py`, `db.py` | IMPLEMENTED_AND_TESTED | `test_app_foundation.py`, `test_app_admin.py` |
| J | Operator UI | PLANNED (Phase 7: Streamlit console over the REST API) | — | — |
| — | API, security, administration | `api.py`, `security.py`, `admin.py` | IMPLEMENTED_AND_TESTED | `test_app_api.py`, `test_app_admin.py` |
| — | Integration with a CMMS | PLANNED (Phase 6) | — | — |

## 3. Key flows

**Assessment** (`health.assess`). For one asset at one instant, checks run in this order:
1. Generic data quality: required signals present and fresh; missing and suspect shares.
2. Selection of an approved model. Its checksum is verified against the registry.
3. Operating scope: history, envelope, regime, idle turbine; for wind, a commissioned baseline.
4. Model-specific data quality: stuck sensors, conflicting relations. Regime-independent checks run even out of scope (PD-13).
5. Sensor-range scope.
6. Scoring.

The result is stored with its inputs reference, model checksum and resolved policy (with its SHA-256), and the asset state advances in the same transaction as the audit event. A prediction is exposed only when every gate passes.

**Decision** (`decision.generate`, per asset, errors isolated):
- **State → recommendation.**
  - URGENT_REVIEW → P1 repair, or P1 inspection when the type defines no repair job.
  - INSPECTION_RECOMMENDED → P2 inspection.
  - DATA_QUALITY_FAILURE → instrument check.
  - Out of scope or unavailable → manual review for criticality-A assets only.
- **Due date.** From the prediction interval when there is one, keeping P(failure before the job ends) ≤ p_accept. Otherwise the policy default.
- **The work order.** It is created awaiting approval, escalated, or left unchanged. It is **never executed** by the system.

**Planning**. `planning.plan` builds a problem from approved orders and the recorded technicians, shifts, parts and windows. It stores a proposal with any violations and changes nothing. `planning.apply` (a planner) schedules each order through the workflow and refuses a stale or infeasible proposal.

## 4. Storage

- **SQLite** in WAL mode, with foreign keys on and `BEGIN IMMEDIATE` write transactions.
- **Migrations** `0001`–`0004` are forward-only and checksummed. An edited migration is refused.
- **Instants** are integer epoch milliseconds, UTC.
- **Backups** use the SQLite online backup API, plus an audit-anchor file (`admin backup`). The anchor reveals truncation of the restored chain.
- **Model bundles** are files on disk. The registry row holds the path and the SHA-256, and loading refuses any mismatch. Pickles are loaded only after that check.
- **Scale assumption** (unmeasured until the Phase 7 load test): one site, up to a few hundred assets, 10-minute data. The migrations are plain SQL so that PostgreSQL is a port, not a redesign.

## 5. Configuration

| item | where | changed by |
|---|---|---|
| data-quality limits, scope tolerances, risk horizons, state thresholds | `configs/platform.yaml` (per asset type); SHA-256 stored with each assessment | review (policy change) |
| decision rules (p_accept, default due dates, job types, labour and downtime cost) | `DecisionConfig` | code or deployment config |
| audit key and key id; database path | environment: `SENTINELLOOP_AUDIT_KEY`, `SENTINELLOOP_AUDIT_KEY_ID`, `SENTINELLOOP_DB` | operations (secret store) |
| users, roles, API keys | database, via `admin create-admin` and `/api/v1/users` | admin |

## 6. Deliberate exclusions

- No write path to control systems or PLCs, and no OT network connection. Data arrive as exports or through a historian API (PLANNED).
- No automatic execution of maintenance work. Every action passes a named person's approval in the workflow (principle 8).
- No learned component decides priorities. The decision engine is a rule table, inspectable and versioned.
- No multi-tenant hosting. One deployment serves one customer.
