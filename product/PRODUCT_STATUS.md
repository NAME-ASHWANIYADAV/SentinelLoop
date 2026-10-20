# Product Status

Living document, updated at the end of every phase. Status vocabulary for capabilities: IMPLEMENTED_AND_TESTED, IMPLEMENTED_NOT_FIELD_VALIDATED, SIMULATED, PLANNED, BLOCKED, and NOT_SUPPORTED for claims our own evidence contradicts (PD-03). Git: competition version on `main` (tag `competition-baseline`, 43050c6); product work on `product/platform`.

## Status at handoff (Phases 0–10 complete, 2026-10-18)

| question | answer | where |
|---|---|---|
| What is it? | A single-site **advisory** maintenance platform. It ingests data, applies data-quality gates, keeps latching health states, recommends work and never executes it, runs a human-approved work-order lifecycle and a scheduler, has a CMMS connector (shadow by default), an operator console and an HMAC audit chain | `FINAL_PRODUCT_HANDOFF.md` §2 |
| What has it been tested on? | Only SIMULATED (C-MAPSS) and SYNTHETIC (our wind generator) data. No customer, real turbine, real CMMS or maintenance team has been involved | `CLAIM_EVIDENCE_MATRIX.md`, `VALIDATION_LADDER.md` (rungs 1–2 reached; rung 3 pre-registered and blocked; rungs 4–6 not reached) |
| Automated tests | 609 passed, 1 skipped on this laptop (`product/evidence/tests/full_suite_2026-10-18.log`) (the Odoo sandbox test waits for the image-download approval). In a clean clone without the git-ignored C-MAPSS data and out-of-fold table, 27 more tests skip | `FINAL_PRODUCT_HANDOFF.md` §1 |
| Reviews | Six-persona adversarial review: 83 findings (40 fixed in code with tests, 14 partly fixed, 23 by document corrections, 6 open and recorded as limitations). Re-review of the fixes: 54 findings (34 confirmed, 11 partly confirmed, 9 refuted); 40 fixed test-first, 4 partly fixed, 1 by documents. Final adversarial audit of this handoff: its findings fixed (code items test-first) | `ADVERSARIAL_REVIEW.md`, `KNOWN_LIMITATIONS.md` |
| Go / no-go | Local demo **GO**. Platform sandbox **GO**. CMMS sandbox **NO-GO** until the Odoo run passes. Real-data shadow pilot **NO-GO**. Operational use **NO-GO** | `FINAL_PRODUCT_HANDOFF.md` §4 |
| Blocked on the user | Approval of the CARE download (G0), the Odoo and Postgres images, and the dependency upgrades | `FINAL_PRODUCT_HANDOFF.md` §5 |

Phase records follow. Phases 1–9 are recorded in their own documents (`FINAL_PRODUCT_HANDOFF.md` §1 lists them) and in `DECISION_LOG.md` PD-01–PD-28.

## Phase 0 — Reconstruction of the existing system (COMPLETE, 2026-10-18)

### Commands run and actual results
Script `product/scripts/phase0_checks.sh`, log `product/evidence/phase0/phase0_checks.log` (run 10:11–10:15, commit 43050c6). The pipeline and retraining runs wrote into a scratch directory so the shipped evidence was not touched.

| Check | Command | Result |
|---|---|---|
| Environment and data | `python -m sentinelloop doctor` | OK: Python 3.12.1, numpy 2.2.6, pandas 2.3.3, scikit-learn 1.7.2, MLflow 3.0.1, Streamlit 1.66.0; 12 C-MAPSS files present; both archive checksums OK (14 s) |
| Test suite | `python -m pytest tests -q` | 114 passed in 132.6 s |
| Pipeline, single regime | `run --subset FD001 --fast --stream-units 3 --out-dir <scratch>` | completed in 28.9 s; fast model RMSE 14.54 capped / 15.84 raw, coverage 0.910, 23 order records, escalation share 0.13 |
| Pipeline, six regimes | `run --subset FD004 --fast --stream-units 2 --out-dir <scratch>` | completed in 45.0 s; RMSE 16.80 / 28.57, coverage 0.879, 76 order records |
| Retraining flow | `retrain --subset FD003 --simulate-new-data --fast --out-dir <scratch>` | challenger PROMOTED (validation RMSE 14.95 → 13.98, coverage 0.910 → 0.940, late rate 0 → 0) in 25 s |
| Audit, shipped evidence | `audit` | 3,409 decisions, 0 mismatches, chains valid |
| Audit, scratch run | `--out-dir <scratch> audit` | 937 decisions, 0 mismatches, chains valid |
| Dashboard | Streamlit on port 8599, `GET /_stcore/health` | HTTP 200 |
| Size | line counts | package 27 files / 2,539 lines; tests 31 files / 1,362 lines; experiment scripts 11 files / 1,231 lines |

Full-scale results come from the competition's final evidence run (`experiments/results/run_all_phase6.log`, 55 minutes, all four subsets); `docs/NUMBERS.md` holds every number. Those are benchmark results on simulated data and are not re-stated here as product claims.

### What actually works (IMPLEMENTED_AND_TESTED, on C-MAPSS only)
- Loading and schema-checking the C-MAPSS text format; train-only cleaning (imputation, constant-sensor drop list, operating-regime clustering and scaling); causal rolling features computed identically in batch and replay.
- Gradient-boosted RUL regression with conformalized quantile intervals; a healthy-baseline health index; an age-matched feature-drift monitor and an input-quality monitor.
- A deterministic triage rule table that turns an interval, a health flag, drift and input quality into a severity and an escalation reason; a per-run draft order record.
- A hash-chained audit log whose records re-derive every decision.
- Experiment tracking and a model registry in MLflow on SQLite; a retraining command with a promotion gate that logs accept and reject reasons.
- A cycle-by-cycle replay of test files that gives bitwise-identical decisions to batch.
- A read-only Streamlit dashboard over the stored artefacts.
- An evaluation harness: policy replay on out-of-fold trajectories, stress tests with injected faults, ablations, a numbers digest.

### What has only been demonstrated on simulated data (SIMULATED)
Every model result, every coverage figure, every detection rate and every decision metric. The stress tests corrupt simulated engines with synthetic faults. "New data" for retraining is held-out simulated engines. No real sensor, real asset, real maintenance record or real user has ever touched the system.

### What is mocked or stand-in
| Stand-in | Real-world counterpart it stands for |
|---|---|
| C-MAPSS cycle index | timestamps, sampling rates, operating hours |
| replay of a test file | live telemetry with gaps, delays and duplicates |
| "unit" integer inside a subset | a registered asset with criticality, location and context |
| draft order record in JSON | a work order in a CMMS with a lifecycle |
| "escalate to a human" label | a review by a named person with a decision and a reason |
| held-out training engines as "new data" | newly confirmed failures and repairs from the field |
| batch fleet-drift result used during replay | a drift check over a trailing window of live data |

### What is incomplete
No asset registry; no time model; no persistent work-order lifecycle (review, approval, assignment, execution, close-out); no outcome feedback; no scheduling under technician, parts or window constraints; no API; no authentication or roles; no integration with any CMMS, historian or protocol; no migrations, backup or restore; no structured logs or health endpoints beyond Streamlit's; inference retrains instead of loading an approved model version. Details and severities: `product/TECHNICAL_DEBT.md`.

### What is technically incorrect or misleading if read as a product
- Re-running the pipeline deletes the subset's stored decisions, orders and audit log (TECHNICAL_DEBT B2), so "auditable" holds within one run only.
- The MLflow `champion` alias suggests that inference uses an approved model; it does not (C1). The retraining flow keeps a separate champion (C2).
- Severity thresholds of 10/25/50 cycles and the 125-cycle RUL cap are C-MAPSS conventions, not maintenance lead times (A4).
- Interval coverage is marginal and below nominal on FD004; "calibrated" must not be stated without that qualifier (C4).
- The replay uses a fleet drift result that a live system could not know at that time (B6).
- The competition documents' phrase "work orders" means draft records; nothing is sent to or executed in any maintenance system.

### Preserve, replace, remove
| Component | Decision | Reason |
|---|---|---|
| ML core (`clean`, `features`, `models`, `conformal`, `anomaly`, `drift`, `stress`, `replay`, `oof`, `metrics`) | PRESERVE | tested, evidence-backed; becomes the C-MAPSS model family behind a model-scope check |
| `agent.triage` rule table | PRESERVE as one input | deterministic and audited; the product's decision engine adds criticality, lead time and resources around it |
| `audit.py` chain and re-derivation | PRESERVE and extend | product audit adds approvals and outcomes and a keyed chain |
| `retrain.evaluate_gate` | PRESERVE | gate logic carries over to model operations |
| Experiment scripts and stored evidence | PRESERVE unchanged | the benchmark record |
| `agent.WorkOrderBook`, `pipeline.write_sqlite`, per-run JSON orders | REPLACE | by a persistent work-order workflow and event store |
| `pipeline.run` as the only entry point | REPLACE for product use | by an ingestion → assessment → decision service; `run` stays for the benchmark |
| Streamlit dashboard | EXTEND | becomes the operator console with work queue, approvals and outcomes; local only until authentication exists |
| `submission/` deck and slide generators | FREEZE | competition history, not product material |
| Nothing is removed in Phase 0 | — | removal waits until replacements are tested |

### Phase 0 deliverables
`product/PRODUCT_STATUS.md` (this file), `product/TECHNICAL_DEBT.md`, `product/CLAIM_EVIDENCE_MATRIX.md`, `product/DECISION_LOG.md`, `product/evidence/phase0/phase0_checks.log`, `product/scripts/phase0_checks.sh`, backup `backups/competition_baseline_2026-10-18.zip`.
