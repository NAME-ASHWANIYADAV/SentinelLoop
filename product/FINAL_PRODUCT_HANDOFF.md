# SentinelLoop — final product handoff (Phase 10)

Date 2026-10-18. Branch `product/platform` (the competition version is on `main`, tag `competition-baseline`).

**Bottom line.** SentinelLoop is now a working, tested, single-site **advisory** maintenance platform:
- asset registry, ingestion and data-quality gates;
- health states that latch and fail visibly;
- a decision engine that recommends work and never executes it;
- a human-approved work-order lifecycle;
- scheduling under crew, parts and window constraints;
- a CMMS connector that runs in shadow mode by default;
- an operator console;
- an HMAC audit chain;
- backup, restore and recovery drills.

None of it has met a customer, a real turbine or a real maintenance team. Every model result is SIMULATED (C-MAPSS) or SYNTHETIC (our own wind generator). The product is fit for a local demonstration and a sandbox. It is **not** ready for a real-data pilot or for operational use; section 4 lists the reasons.

## 1. What was done (Phases 0–10)

| phase | outcome | main record |
|---|---|---|
| 0 Audit | The competition system was rebuilt and measured; its technical debt was listed | `PRODUCT_STATUS.md`, `TECHNICAL_DEBT.md` |
| 1 Discovery and market | Sourced research; an interview plan (**no interviews held**); a gated provisional choice: Indian onshore wind | `CUSTOMER_DISCOVERY.md`, `COMPETITIVE_LANDSCAPE.md`, `INITIAL_MARKET_AND_ASSET_CHOICE.md`, PD-10 |
| 2 Data | Data strategy, contracts, domain-gap report, validation ladder; synthetic wind generator | `DATA_*.md`, `DOMAIN_GAP_REPORT.md`, `VALIDATION_LADDER.md` |
| 3 Requirements and architecture | Modular monolith (PD-06), threat model, API contracts, workflows, admin CLI | `PRODUCT_REQUIREMENTS.md`, `SYSTEM_ARCHITECTURE.md`, `THREAT_MODEL.md`, `API_CONTRACTS.md`, `USER_WORKFLOWS.md` |
| 4 Scheduling | Greedy and MILP schedulers with an independent validator; simulator evaluation (S1–S2) | `SCHEDULING_EVALUATION.md`, PD-27 |
| 5 Reliability and safety | Failure-injection tests; calibration audits C1 and C2 | `RELIABILITY_AND_SAFETY.md`, PD-19 |
| 6 Integration | Odoo JSON-2 connector, shadow by default, contract-tested; sandbox kit (**not run**) | `INTEGRATION_GUIDE.md`, PD-20 |
| 7 Security and operations | Security reviews with fixes; console; load test L1; recovery drill R1; deployment guide and runbook | `SECURITY_REVIEW.md`, `DEPLOYMENT_GUIDE.md`, `OPERATIONS_RUNBOOK.md` |
| 8 Pilot design | Read-only shadow-pilot protocol and acceptance criteria, **NOT YET FIELD VALIDATED** | `PILOT_PROTOCOL.md`, `PILOT_ACCEPTANCE_CRITERIA.md`, `OPERATOR_FEEDBACK_PLAN.md` |
| 9 Adversarial review | Six role-played reviewers produced 83 findings; fixes test-first, then a re-review of the fixes | `ADVERSARIAL_REVIEW.md`, `KNOWN_LIMITATIONS.md`, PD-15–PD-27 |
| 10 Handoff | This document | — |

Verification at handoff:
- `python -m pytest tests -q`: **335 passed, 1 skipped** (the Odoo sandbox test, pending approval), 350 s on this laptop.
- The local demo was rebuilt from scratch and checked in a browser (`product/evidence/demo/local_demo_check.md`).

## 2. Capability classification

Vocabulary (PD-03):
- **IMPLEMENTED_AND_TESTED**: the code exists and automated tests or recorded runs exercise it. It says nothing about real equipment.
- **IMPLEMENTED_NOT_FIELD_VALIDATED**: it works on our data, and its value depends on real data or real users it has never met.
- **SIMULATED**: shown only on simulated or synthetic data.
- **PLANNED**: not built.
- **BLOCKED**: needs something we do not have.

The claim-by-claim record, with reproduce commands, is `CLAIM_EVIDENCE_MATRIX.md`.

### IMPLEMENTED_AND_TESTED
| capability | evidence |
|---|---|
| REST API: API keys stored as hashes, 6 roles, per-route permissions, rate limits, streaming body cap, idempotency keys, JSON errors without internals | `tests/test_app_api.py`, the route-walk auth test, `tests/test_app_remediation_security.py` |
| Asset registry, sites, asset types, resources (technicians, shifts, parts) | `tests/test_app_foundation.py`, `tests/test_app_api.py` |
| Ingestion (JSON and CSV): schema checks, batch reports, 200,000-reading cap, parsing off the event loop | `tests/test_app_ingest.py` |
| Health states with latching (PD-08, PD-16). Fail-visible states: DATA_QUALITY_FAILURE, MODEL_OUT_OF_SCOPE, MODEL_UNAVAILABLE. Replays never move state; ASSESSMENT_OVERDUE (PD-17) | `tests/test_app_states.py`, `tests/test_app_remediation.py`, `tests/test_app_failure_injection.py` |
| Decision engine: job, priority, due date and written reason; never executes work; rejection suppression; desk reviews; site decision config (PD-18, PD-24) | `tests/test_app_decision.py`, `tests/test_app_remediation.py` |
| Work-order lifecycle with named human approval, outcomes and contradiction flags; hand-back; deferral return | `tests/test_app_workorders.py`, `tests/test_app_remediation.py` |
| Scheduling **feasibility**: greedy and MILP planners, with an independent validator (0 violations in every recorded run) | `tests/test_app_scheduler.py`, `tests/test_app_planning.py`, S1b |
| Model registry: approval, rollback, bundle hash checked against its manifest | `tests/test_app_health.py`, `tests/test_app_remediation_security.py` |
| HMAC audit chain with anchor verification. It detects edits and truncation of audit events, not of state tables (PD-22) | `tests/test_app_foundation.py`, `tests/test_app_admin.py`, R1 |
| Migrations 0001–0007 (checksummed, forward-only); backup and restore; recovery after a hard kill and after deleting the database | `tests/test_app_admin.py`, `product/evidence/recovery/r1.md` |
| Throughput on one laptop: 50 turbines, 0 errors | `product/evidence/load/l1.md` (two runs; the second under background load) |

### IMPLEMENTED_NOT_FIELD_VALIDATED
| capability | what is missing |
|---|---|
| Wind turbine asset type, 10-minute SCADA ingestion, data-quality gates (stuck sensors, gear relation, envelope, missing data, feed delay) | Never fed real SCADA. Per-site tag mapping is PLANNED (KNOWN_LIMITATIONS P12) |
| Per-turbine commissioning baselines (PD-12) | Never commissioned on a real turbine |
| Operator console (Streamlit, localhost, the user's own key) | 13 headless tests and a browser check on demo data. No operator has used it. No mobile layout or offline mode (P7) |
| CMMS connector (Odoo JSON-2, shadow by default, withdrawal mirroring, allowlist at every dispatch) | Tested only against a contract test double (`tests/test_app_integration.py`). The real Odoo run is **BLOCKED**, and there is no customer CMMS |

### SIMULATED
| capability | result and its unfavourable part |
|---|---|
| RUL prediction with 90% intervals (C-MAPSS) | RMSE 13.6–15.2 (capped). Coverage 0.85–0.94 overall, but 0.81–0.87 in late life (C1) |
| Failure probability for due dates | **Not calibrated** (C2): shown about 0.55 when about 0.92 was observed. Labelled "model-implied, not calibrated" |
| Wind anomaly detection (SYNTHETIC; the generator shares the model's assumptions) | 36/36 injected faults flagged on tuning fleets. **Held-out healthy fleets: 2.65 alarm episodes per turbine-year**, above the proposed pilot ceiling of 2 (W2, E7). A slow drift of a single sensor cannot be told apart from heating |
| Scheduling value | No policy dominates (S2). Parts shortage and adverse are fleet collapse. The MILP cuts downtime only under tight labour, at higher unpriced cost. The shipped trigger is worse under biased predictions (part C) |

### PLANNED
- A tuned point-threshold RUL trigger, and recalibration of P(failure) (PD-19, PD-27).
- Cranes, weather and climbing limits, travel and multi-day jobs in the scheduler (P8).
- An OEM-serviced workflow (P9).
- "My jobs" and linking resources to users (P10).
- Follow-up jobs and a shift editor in the console (P11).
- Per-site tag mapping (P12).
- Bulk re-commissioning (M6).
- SSO, signed model manifests and pseudonymisation (S3, S5).
- A PostgreSQL port and data retention (P1, P3).

### BLOCKED
| item | blocked on |
|---|---|
| G0: the wind model on real public data (CARE to Compare, 95 datasets; pre-registered, amended before download) | The user's approval of the 5.5 GB download. The team should also publish the SHA-256 of `product/evidence/g0/PREREGISTRATION.md` externally before the download (the repository has no remote) |
| Real Odoo sandbox run (`sandbox/odoo/setup.sh`, then `tests/test_app_odoo_sandbox.py`) | The user's approval of the Odoo and Postgres image downloads. Docker Desktop also starts the user's other containers |
| Dependency upgrades (pyarrow, pytest; mlflow is development only) | Download approval |
| G1 access conversations; rung-4 back-test; rung-5 shadow pilot | A customer partner. None has been contacted |
| Any claim of downtime, cost or availability benefit | A pilot with a measurement plan agreed beforehand |

### NOT_SUPPORTED (claims our own evidence contradicts)
- Calibrated failure probability.
- MILP downtime savings under parts shortage or adverse conditions.
- "The risk trigger beats a tuned threshold."
- Optimal schedules for a real site.
- The competition-era "self-healing" framing.
- Any compliance or certification claim.

## 3. Validation ladder position

- Rungs 1–2 (unit and behaviour tests; simulated and synthetic data) are reached.
- Rung 3 (public real data, G0) is pre-registered and blocked.
- Rungs 4–6 (customer back-test, shadow pilot, operational use) are **not reached**.

Details: `VALIDATION_LADDER.md`.

## 4. Go / no-go

| use | decision | basis |
|---|---|---|
| **Local demo** (one laptop, SYNTHETIC data, labelled as such) | **GO** | Full suite passes. The demo was rebuilt from scratch and checked (`product/evidence/demo/local_demo_check.md`). The console shows the synthetic data class, gives no probability for anomaly models, and states that it is advisory. Keep it on 127.0.0.1 and say "synthetic" out loud |
| **Sandbox** (platform plus sandbox CMMS in shadow mode, no real equipment) | **GO for the platform sandbox. NO-GO for the CMMS sandbox until the Odoo run passes** | The platform side is covered by the suite and by R1/L1. The connector is proven only against a contract test double; the real Odoo run awaits image-download approval (S1) |
| **Real-data shadow pilot** (read-only, a partner's turbines) | **NO-GO** | `PILOT_PROTOCOL.md` preconditions P1–P7 are all unmet: G0 not run, no partner (G1), no rung-4 back-test, no partner security or safety sign-off, no commissioning. Open issues: the held-out synthetic false-alarm rate is above the pilot ceiling (E7); the scheduler lacks wind-site constraints (P8); there is no OEM workflow (P9) |
| **Operational use** | **NO-GO** | Rungs 4–6 not reached; no field validation; no external penetration test or SSO; no high availability; the limitations marked H and M in `KNOWN_LIMITATIONS.md` |

## 5. What the team should do next, in order

1. **Approve or decline the three pending downloads:**
   - CARE (5.5 GB), for G0;
   - the Odoo and Postgres images, for the sandbox;
   - the pyarrow and pytest upgrades.

   Before the CARE download, publish the SHA-256 of `PREREGISTRATION.md` somewhere external.
2. **Run G0** exactly as pre-registered (Farm A primary against the internal baseline). Record any deviation in §9. If G0 fails, re-table the vertical as PD-10 states.
3. **Run the Odoo sandbox test.** A pass moves S1 to "tested against real Odoo (sandbox)".
4. **G1:** hold three to five access conversations using `CUSTOMER_DISCOVERY.md`, and record only what was actually said. Ask specifically about curtailment, seasons, OEM contracts and acceptable false-inspection rates (E7).
5. **With a partner:** agree the acceptance thresholds and ROI method before seeing data (`PILOT_ACCEPTANCE_CRITERIA.md`). Then run the rung-4 back-test on their history, and only then a read-only shadow pilot.
6. **Engineering backlog, in priority order:**
   - the point-threshold trigger and recalibration;
   - per-site tag mapping and operating-state signals (M3, P12);
   - "my jobs", user-linked resources and a split integration role (P10, S6);
   - scheduler constraints for wind work (P8).

## 6. How to run it

The commands are tested on this laptop: Windows 11, Python 3.12, `.venv`.

**Run the tests:**
```bash
.venv/Scripts/python.exe -m pytest tests -q
```

**Build the demo site.** First create a demo audit key, once:
```bash
python -c "import secrets; print('SENTINELLOOP_AUDIT_KEY=' + secrets.token_hex(32))" > artifacts_demo/demo_key.env
```
Then build the site:
```bash
set -a; . artifacts_demo/demo_key.env; set +a; PYTHONPATH=src .venv/Scripts/python.exe product/scripts/demo_site.py artifacts_demo/console
```

**Start the API.** It listens on 127.0.0.1:8080, and reads the key and the demo database from `artifacts_demo/`:
```bash
.venv/Scripts/python.exe product/scripts/run_demo_api.py
```

**Start the console:**
```bash
.venv/Scripts/python.exe -m streamlit run src/sentinelloop/console/app.py
```

Sign in with a key from `artifacts_demo/console/demo_credentials.json`. Keep that file local; it is git-ignored.

Production-style deployment, backups, `verify-audit` with an anchor and the cron jobs are covered in `DEPLOYMENT_GUIDE.md` and `OPERATIONS_RUNBOOK.md`.

## 7. Where the evidence is

| evidence | path |
|---|---|
| Decisions | `product/DECISION_LOG.md` (PD-01–PD-27) |
| Limitations | `product/KNOWN_LIMITATIONS.md` |
| Adversarial review and resolutions | `product/ADVERSARIAL_REVIEW.md`, `product/evidence/adversarial/` |
| Scheduling | `product/evidence/scheduling/` (S1), `product/evidence/scheduling_v2/` (S2 and part C) |
| Wind (synthetic) | `product/evidence/wind_synthetic/` (W1, W2) |
| Calibration | `product/evidence/calibration/` (C1, C2) |
| Load, recovery, security | `product/evidence/load/`, `product/evidence/recovery/`, `product/evidence/security/` |
| G0 pre-registration | `product/evidence/g0/PREREGISTRATION.md` |
| API | `product/evidence/api/` (OpenAPI and the route/permission table) |
