# Product requirements

**Product.** SentinelLoop is a maintenance decision layer between condition data and the maintenance system. It turns SCADA or sensor data into explained, auditable maintenance recommendations that a named person approves, and schedules the approved work against real crews, parts and windows.

**First target (provisional, gated, PD-10).** Indian onshore wind owner-operators and O&M providers: geared ~2.0–2.3 MW turbines with 10-minute SCADA, drivetrain and transformer faults first.

**Evidence status.** No customer has validated these requirements (`CUSTOMER_DISCOVERY.md`). They are the team's hypotheses and principles, to be confirmed or killed by discovery gate G1.

## 1. Problems addressed (hypotheses)

1. Alarms and condition data exist but are not turned into a ranked, explained list of what to inspect this week. This is the decision hypothesis in the choice record §1.
2. Recommendations from monitoring tools are not tied to work-order outcomes, so nobody learns whether they were right.
3. Planners lack a way to fit inspections into crews, parts and weather or maintenance windows, and to see what cannot be done.
4. Buyers distrust black-box predictions and false alarms (R2: false alarms erode trust; ROI uncertain).

## 2. Functional requirements

Status vocabulary per PD-03.

| id | requirement | status | evidence |
|---|---|---|---|
| FR-A1 | Register sites, asset types (signals with units and ranges, jobs) and assets (criticality, consequence, windows), with audited, reasoned changes | IMPLEMENTED_AND_TESTED | `test_app_foundation.py` |
| FR-B1 | Ingest readings with an explicit contract; reject what cannot be stored faithfully, with a reason per row; idempotent batches | IMPLEMENTED_AND_TESTED | `test_app_ingest.py` |
| FR-B2 | Report stale signals per asset | IMPLEMENTED_AND_TESTED | same |
| FR-B3 | Map each site's own signal names to the contract | PLANNED (G0 mapping files; per-site mapping config) | — |
| FR-C1 | Assess each asset into one of the defined health states, with reasons; expose a prediction only when data quality and scope pass | IMPLEMENTED_AND_TESTED | `test_app_health.py`, `test_app_wind.py` |
| FR-C2 | Latching of urgent and inspection states until maintenance or a reasoned dismissal | IMPLEMENTED_AND_TESTED | `test_app_states.py` |
| FR-C3 | Wind drivetrain anomaly detection from 10-minute SCADA | IMPLEMENTED_AND_TESTED on SYNTHETIC data; real-data test G0 pre-registered | `test_app_wind.py`, `evidence/wind_synthetic/w1.md` |
| FR-C4 | No failure probability or RUL is shown unless the model estimates one and has been validated for that use | IMPLEMENTED_AND_TESTED | `test_anomaly_only_classification_never_invents_a_probability` |
| FR-D1 | Recommend a job, priority and due date with a written explanation; never execute work | IMPLEMENTED_AND_TESTED | `test_app_decision.py` |
| FR-E1 | Propose schedules under technicians, skills, shifts, parts and windows; validate them independently; apply only by a planner | IMPLEMENTED_AND_TESTED | `test_app_scheduler.py`, `test_app_planning.py` |
| FR-F1 | Work-order lifecycle with approval, deferral, rejection, idempotency and concurrency control | IMPLEMENTED_AND_TESTED | `test_app_workorders.py` |
| FR-G1 | Record outcomes and flag contradictions; list orders missing outcomes | IMPLEMENTED_AND_TESTED | same |
| FR-G2 | Use outcomes to review thresholds and model performance per site | PLANNED | — |
| FR-H1 | Model registry with human approval, rollback and checksum verification | IMPLEMENTED_AND_TESTED | `test_app_health.py` |
| FR-H2 | Per-turbine commissioning baseline, audited | IMPLEMENTED_AND_TESTED | `test_app_wind.py` |
| FR-H3 | Drift monitoring and gated retraining for wind models | PLANNED (exists for C-MAPSS in the competition pipeline) | — |
| FR-I1 | Tamper-evident audit of every change; verification against an exported anchor | IMPLEMENTED_AND_TESTED | `test_app_foundation.py`, `test_app_admin.py` |
| FR-J1 | Operator console: login, fleet view, asset detail, work queue (approve/defer/reject), schedule view with conflicts, outcome form, audit view | PLANNED (Phase 7) | — |
| FR-K1 | CMMS integration: read-only shadow mode by default; optional creation of draft requests flagged as SentinelLoop output; idempotent upsert by external id; retries and dead letters | PLANNED (Phase 6) | — |

## 3. Non-functional requirements

| id | requirement | target | status |
|---|---|---|---|
| NFR-1 | Advisory only | no control-system connection; no automatic execution of physical work | IMPLEMENTED (by design; no such code path exists) |
| NFR-2 | Explainability | every recommendation carries its state, reasons, rule and inputs reference | IMPLEMENTED_AND_TESTED |
| NFR-3 | Reproducibility | every assessment records its model checksum, policy hash and input window | IMPLEMENTED_AND_TESTED |
| NFR-4 | Security | authenticated API; role permissions; secrets only from the environment; no plaintext credentials stored | IMPLEMENTED_AND_TESTED; external pen test PLANNED |
| NFR-5 | Throughput | one site: a few hundred assets at 10-minute resolution; assessment of the whole fleet within one data interval | PLANNED to measure (Phase 7 load test) |
| NFR-6 | Recoverability | online backup; restore to a new path; audit verification after restore; RPO/RTO set per deployment | IMPLEMENTED_AND_TESTED (mechanism); targets PLANNED |
| NFR-7 | Deployability | one server or VM, Python 3.12, SQLite; documented install | PLANNED (Phase 7 `DEPLOYMENT_GUIDE.md`) |
| NFR-8 | Data protection | customer data stay on approved infrastructure; pseudonymised analysis copies | PLANNED |

## 4. Out of scope (for now)

- Remaining-useful-life estimates for wind turbines (PD-11).
- Vibration or CMS hardware, and edge devices.
- Multi-tenant SaaS hosting.
- Writing to control systems.
- Automatic closing of CMMS work orders.
- Any claim of cost savings or downtime reduction. That requires ladder rung 6 (`VALIDATION_LADDER.md`).
