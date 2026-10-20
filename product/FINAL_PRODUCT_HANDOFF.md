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

None of it has met a customer, a real turbine or a real maintenance team. Every model result is SIMULATED (C-MAPSS) or SYNTHETIC (our own wind generator).

The product is fit for a local demonstration and for a platform-only sandbox. The CMMS sandbox is NO-GO until the Odoo run passes. It is **not** ready for a real-data pilot or for operational use; section 4 gives the reasons.

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
| 9 Adversarial review | See the two review rounds below the table | `ADVERSARIAL_REVIEW.md`, `KNOWN_LIMITATIONS.md`, PD-15–PD-28, G0 Amendments 1–2 |
| 10 Handoff | This document, then an adversarial audit of it: claims, principles, and reproducibility in a clean clone. The audit's findings were fixed (code items test-first) | — |

**Phase 9 in detail.**
- **First round.** Six role-played reviewers produced 83 findings: 40 fixed in code with tests, 14 partly fixed, 23 resolved by correcting documents, and 6 left open and recorded in `KNOWN_LIMITATIONS.md`.
- **Second round.** A re-review of those fixes produced 54 findings. Verification confirmed 34, partly confirmed 11 and refuted 9. Of these, 40 were fixed test-first and checked again against their original reproductions, 4 partly fixed and 1 resolved in documents.
- **Wind alarm setting.** After the gating fixes it was chosen again: first by W2 run 2, then by W3, whose protocol was committed before it ran.

**Verification at handoff.**
- **Full suite on this laptop:** `python -m pytest tests -q` gives **609 passed, 1 skipped** (the Odoo sandbox test, pending approval), with the handoff-audit fixes. The log is `product/evidence/tests/full_suite_2026-10-18.log`.
- **Clean clone:** 27 tests need git-ignored local data, the NASA C-MAPSS files and the competition's out-of-fold table, and skip without them. The auditor's clean clone at 2f281fe, before the 7 handoff-fix tests were added, gave 575 passed, 28 skipped for the full suite, and 467 passed, 22 skipped for the platform tests (`tests/test_app_*.py tests/test_console.py`).
- **Local demo:** rebuilt from scratch and checked in a browser twice, the second time on the final code (`product/evidence/demo/local_demo_check.md`).

## 2. Capability classification

Vocabulary (PD-03):
- **IMPLEMENTED_AND_TESTED**: the code exists and automated tests or recorded runs exercise it. It says nothing about real equipment.
- **IMPLEMENTED_NOT_FIELD_VALIDATED**: it works on our data, and its value depends on real data or real users it has never met.
- **SIMULATED**: shown only on simulated or synthetic data.
- **PLANNED**: not built.
- **BLOCKED**: needs something we do not have.
- **NOT_SUPPORTED**: our own evidence contradicts the claim.

The claim-by-claim record, with reproduce commands, is `CLAIM_EVIDENCE_MATRIX.md`. The lists below are a summary; the matrix and `KNOWN_LIMITATIONS.md` are complete.

### IMPLEMENTED_AND_TESTED
| capability | evidence |
|---|---|
| REST API: API keys stored as hashes, 6 roles, per-route permissions, rate limits, streaming body cap, idempotency keys (the platform's own prefixes are reserved), JSON errors without internals, one JSON request log line per request | `tests/test_app_api.py`, the route-walk auth test, `tests/test_app_remediation_security.py`, `tests/test_app_rereview_api.py`, `tests/test_app_handoff_fixes.py` |
| Asset registry, sites, asset types, resources (technicians, shifts, parts) | `tests/test_app_foundation.py`, `tests/test_app_api.py` |
| Ingestion (JSON and CSV): schema checks, batch reports, 200,000-reading cap. CSV parsing runs off the event loop (`api.py`, `run_in_threadpool`), but no test covers that | `tests/test_app_ingest.py`; the cap: `tests/test_app_remediation_security.py` |
| Health states with latching (PD-08, PD-16, PD-28). Fail-visible states: DATA_QUALITY_FAILURE, MODEL_OUT_OF_SCOPE, MODEL_UNAVAILABLE. Replays never lower a latch or move the live state, but may raise a latch. Only a qualifying completed work order records maintenance. ASSESSMENT_OVERDUE (PD-17) | `tests/test_app_states.py`, `tests/test_app_remediation.py`, `tests/test_app_rereview_health.py`, `tests/test_app_failure_injection.py`, `tests/test_app_handoff_fixes.py` |
| Decision engine: job, priority, due date and written reason; never executes work; rejection suppression keyed on the latched condition; desk reviews; older orders linked or superseded; validated site decision config (PD-18, PD-24, PD-28) | `tests/test_app_decision.py`, `tests/test_app_remediation.py`, `tests/test_app_rereview_decision.py` |
| Work-order lifecycle with named human approval, outcomes and contradiction flags; hand-back; deferral return | `tests/test_app_workorders.py`, `tests/test_app_remediation.py` |
| Scheduling **feasibility**: greedy and MILP planners, with an independent validator. 0 violations in every run that records them (the S1 grid and all S2 runs) | `tests/test_app_scheduler.py`, `tests/test_app_planning.py`, S1b |
| Model registry: approval, rollback, bundle hash checked against its manifest | `tests/test_app_health.py` (needs the C-MAPSS files), `tests/test_app_remediation_security.py` |
| HMAC audit chain with anchor verification. It detects edits and truncation of audit events, not of state tables (PD-22). A malformed anchor is refused | `tests/test_app_foundation.py`, `tests/test_app_admin.py`, `tests/test_app_rereview_wiring.py`, R1 |
| Migrations 0001–0009 (checksummed, forward-only; 0008 restores replay protection on upgraded databases); backup and restore; recovery after a hard kill and after deleting the database | `tests/test_app_admin.py`, `tests/test_app_rereview_health.py`, `product/evidence/recovery/r1.md` |
| Throughput on one laptop, SYNTHETIC data: 50 turbines, 0 errors, audit chain valid. 27–28 of the 50 were out of scope, so fewer assessments were fully scored | `product/evidence/load/l1_run1.md` (first run) and `l1.md` (re-run, measured while other work ran on the laptop) |

### IMPLEMENTED_NOT_FIELD_VALIDATED
| capability | what is missing |
|---|---|
| Wind turbine asset type, 10-minute SCADA ingestion, data-quality gates (stuck sensors anywhere in the scored window, gear relation, envelope, missing data, feed delay). The claim matrix rates the related performance claim P11 as SIMULATED | Never fed real SCADA. Per-site tag mapping is PLANNED (KNOWN_LIMITATIONS P12) |
| Per-turbine commissioning baselines (PD-12) | Never commissioned on a real turbine |
| Operator console (Streamlit, localhost, the user's own key, site-local times) | `tests/test_console.py` (22 tests collected) and two browser checks on demo data. No operator has used it. No mobile layout or offline mode (P7) |
| CMMS connector (Odoo JSON-2, shadow by default, withdrawal mirroring, allowlist at every dispatch, one dispatch per target under a lease, create attempts logged before the call, the failure probability labelled as not calibrated) | Tested only against a contract test double (`tests/test_app_integration.py`, `tests/test_app_rereview_integration.py`). The real Odoo run is **BLOCKED**, and there is no customer CMMS |

### SIMULATED
| capability | result and its unfavourable part |
|---|---|
| RUL prediction with 90% intervals (C-MAPSS; the CQR model the platform packages) | Point RMSE 13.5–15.4 against the capped truth, and 15.2–27.3 against the raw truth. Coverage 0.85–0.94 overall, but 0.81–0.87 in late life (C1), and 0.58–0.87 against the raw truth |
| Failure probability for due dates | **Not calibrated** (C2): shown about 0.55 when about 0.92 was observed. Labelled "model-implied, not calibrated" wherever the platform shows it: assessment and decision reasons, the console and the CMMS description |
| Wind anomaly alarms (SYNTHETIC; the generator shares the model's assumptions) | The setting was chosen by a pre-stated rule (W3). On fresh held-out fleets, healthy turbines gave **0.44 alarm episodes per turbine-year**, with a 95% interval up to about 2.45, so the proposed pilot ceiling of 2 is not excluded.<br>Counted as the pilot's alarm-burden criterion counts (drifting-sensor turbines included), the burden is about **13 episodes per turbine-year**, far above that ceiling (E7). Shorter persistence gave 5.74 and 2.65. Out of scope about 41% of calendar time.<br>Injected faults are flagged, but that is a behaviour check: the generator sets detection and lead time (E3) |
| Scheduling value | No policy dominates (S2). Parts shortage and adverse are fleet collapse. The MILP cuts downtime only under tight labour, at higher unpriced cost. The shipped trigger is worse under biased predictions (part C) |

### PLANNED (main items)
- A tuned point-threshold RUL trigger, and recalibration of P(failure) (PD-19, PD-27).
- Automatic scarcity reporting (PD-27 (e)).
- Cranes, weather and climbing limits, travel and multi-day jobs in the scheduler (P8).
- An OEM-serviced workflow (P9).
- "My jobs" and linking resources to users (P10).
- Follow-up jobs and a shift editor in the console (P11).
- Per-site tag mapping (P12).
- Bulk re-commissioning (M6).
- Drift monitoring and gated retraining for wind.
- SSO, signed model manifests and pseudonymisation (S3, S5).
- A PostgreSQL port and data retention (P1, P3).
- The pilot's assessability analysis script (`PILOT_PROTOCOL.md` §4).

### BLOCKED
| item | blocked on |
|---|---|
| G0: the wind model on real public data (CARE to Compare, 95 datasets; pre-registered, Amendments 1 and 2 written before download) | The user's approval of the 5.5 GB download. The team should also publish the SHA-256 of `product/evidence/g0/PREREGISTRATION.md` externally before the download (the repository has no remote) |
| Real Odoo sandbox run (`sandbox/odoo/setup.sh`, then `tests/test_app_odoo_sandbox.py`) | The user's approval of the Odoo and Postgres image downloads. Docker Desktop also starts the user's other containers |
| Dependency upgrades (pyarrow, pytest; mlflow is development only) | Download approval |
| G1 access conversations; rung-4 back-test; rung-5 shadow pilot | A customer partner. None has been contacted |
| Any claim of downtime, cost or availability benefit | A rung-6 trial in which recommendations are acted on, with a baseline and measurement plan agreed beforehand. A shadow pilot cannot show it |

### NOT_SUPPORTED (claims our own evidence contradicts)
- Calibrated failure probability (P29).
- Interval coverage that holds on new data as a general claim (P2).
- Selectivity of the competition retraining gate (P7).
- A dependency set free of known advisories (P31).
- MILP downtime savings under parts shortage or adverse conditions.
- "The risk trigger beats a tuned threshold" (P17).
- Optimal schedules for a real site (P18).
- The competition-era "self-healing" framing.
- Any compliance or certification claim.

## 3. Validation ladder position

- Rungs 1–2 (unit and behaviour tests; simulated and synthetic data) are reached.
- Rung 3 (public real data, G0) is pre-registered and blocked.
- Rungs 4–6 (customer back-test, shadow pilot, operational use) are **not reached**.
- Business value can only be shown at rung 6.

Details: `VALIDATION_LADDER.md`.

## 4. Go / no-go

| use | decision | basis |
|---|---|---|
| **Local demo** (one laptop, SYNTHETIC data, labelled as such) | **GO** | Full suite passes. The demo was rebuilt from scratch and checked on the final code (`product/evidence/demo/local_demo_check.md`). The console shows the synthetic data class, gives no probability for anomaly models, and states that it is advisory. Keep it on 127.0.0.1 and say "synthetic" out loud |
| **Sandbox** (platform plus sandbox CMMS in shadow mode, no real equipment) | **GO for the platform sandbox. NO-GO for the CMMS sandbox until the Odoo run passes** | The platform side is covered by the suite and by R1/L1. The connector is proven only against a contract test double; the real Odoo run awaits image-download approval (S1) |
| **Real-data shadow pilot** (read-only, a partner's turbines) | **NO-GO** | `PILOT_PROTOCOL.md` preconditions P1–P7 are all unmet: G0 not run, no partner (G1), no rung-4 back-test, no partner security or safety sign-off, no commissioning. Open issues:<br>• the false-alarm rate is known only on synthetic data, where its interval includes the pilot ceiling;<br>• counted as the alarm-burden criterion B3 counts, the synthetic burden is about 13 per turbine-year, so the proposed stopping rule would almost always stop the pilot (E7, `PILOT_PROTOCOL.md` §7);<br>• the scheduler lacks wind-site constraints (P8);<br>• there is no OEM workflow (P9) |
| **Operational use** | **NO-GO** | Rungs 4–6 not reached; no field validation; no external penetration test or SSO; no high availability; the limitations marked H and M in `KNOWN_LIMITATIONS.md` |

## 5. What the team should do next, in order

1. **Approve or decline the three pending downloads:**
   - CARE (5.5 GB), for G0;
   - the Odoo and Postgres images, for the sandbox;
   - the pyarrow and pytest upgrades.

   Before the CARE download, publish the SHA-256 of `PREREGISTRATION.md` somewhere external.
2. **Run G0** exactly as pre-registered (Farm A primary against the internal baseline; Amendments 1–2). Record any deviation in §9. If G0 fails, re-table the vertical as PD-10 states.
3. **Run the Odoo sandbox test.** A pass moves S1 to "tested against real Odoo (sandbox)".
4. **G1:** hold three to five access conversations using `CUSTOMER_DISCOVERY.md`, and record only what was actually said. Ask specifically about:
   - curtailment;
   - seasons;
   - OEM contracts;
   - the false-inspection rate a site would accept, including alarms on drifting sensors (E7).
5. **With a partner:**
   - agree the acceptance thresholds before seeing data (`PILOT_ACCEPTANCE_CRITERIA.md`);
   - run the rung-4 back-test on their history;
   - only then run a read-only shadow pilot.

   A value claim needs a later rung-6 trial with an ROI method agreed in advance.
6. **Engineering backlog, in priority order:**
   - the alarm burden from drifting sensors (M1, E7);
   - the point-threshold trigger and recalibration;
   - per-site tag mapping and operating-state signals (M3, P12);
   - "my jobs", user-linked resources and a split integration role (P10, S6);
   - scheduler constraints for wind work (P8).

## 6. How to run it

Tested on this laptop: Windows 11, Python 3.12. The commands use the Windows venv layout (`.venv/Scripts/`); on Linux or macOS use `.venv/bin/`.

**From a fresh clone**, once (README "Setup" has the full competition setup):
```bash
python -m venv .venv
```
```bash
.venv/Scripts/python.exe -m pip install -r requirements-platform.txt -c requirements.lock.txt
```
```bash
.venv/Scripts/python.exe -m pip install -e . --no-deps
```
```bash
mkdir -p artifacts_demo
```

**Optional: local data for the 27 data-dependent tests.** First the C-MAPSS files:
```bash
.venv/Scripts/python.exe -m sentinelloop data --download
```
Then the out-of-fold table:
```bash
.venv/Scripts/python.exe experiments/run_all.py
```
The first downloads the NASA C-MAPSS archive. The second takes about an hour. Without these files the 27 tests skip.

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

**Start the console**, from the repository root:
```bash
.venv/Scripts/python.exe -m streamlit run src/sentinelloop/console/app.py
```

Sign in with a key from `artifacts_demo/console/demo_credentials.json`. Keep that file local; it is git-ignored.

Production-style deployment, backups, `verify-audit` with an anchor and the cron jobs are covered in `DEPLOYMENT_GUIDE.md` and `OPERATIONS_RUNBOOK.md`.

## 7. Where the evidence is

| evidence | path |
|---|---|
| Decisions | `product/DECISION_LOG.md` (PD-01–PD-28) |
| Limitations | `product/KNOWN_LIMITATIONS.md` |
| Adversarial review, re-review and resolutions | `product/ADVERSARIAL_REVIEW.md`, `product/evidence/adversarial/` (`review.json`, `rereview.json`) |
| Test runs | `product/evidence/tests/` |
| Scheduling | `product/evidence/scheduling/` (S1), `product/evidence/scheduling_v2/` (S2 and part C) |
| Wind (synthetic) | `product/evidence/wind_synthetic/` (W1, W2 runs 1–2, W3) |
| Calibration | `product/evidence/calibration/` (C1, C2) |
| Load, recovery, security | `product/evidence/load/` (`l1_run1.md`, `l1.md`), `product/evidence/recovery/`, `product/evidence/security/` |
| G0 pre-registration | `product/evidence/g0/PREREGISTRATION.md` (Amendments 1–2 in §10–11) |
| API | `product/evidence/api/` (OpenAPI and the route/permission table) |
| Local demo checks | `product/evidence/demo/local_demo_check.md` |
