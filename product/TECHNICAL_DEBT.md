# Technical Debt Register (product lens)

Written in Phase 0 (2026-10-18) against git tag `competition-baseline` (commit 43050c6). The competition version was built to answer one question on one simulated dataset; this register lists what stands between it and software a maintenance team could pilot. Each item says where the debt is, why it matters for a product, and what the product work does about it. Severity: **blocker** (a pilot cannot start), **major** (a pilot would be misleading or fragile), **minor** (polish or maintainability).

## A. Domain model and data

| # | Debt | Where | Why it matters | Severity | Plan |
|---|---|---|---|---|---|
| A1 | No notion of time: assets are indexed by C-MAPSS "cycle", there are no timestamps, time zones, sampling rates or units | `data.py`, `features.py`, `agent.py` (`cycle` everywhere) | Real telemetry arrives with timestamps, gaps, late and duplicate records; maintenance lead times are in hours/days, not cycles | blocker | Product data contract with UTC timestamps and units; the C-MAPSS adapter maps cycles to synthetic timestamps and flags the time basis as `cycle_index` |
| A2 | No asset registry: an "asset" is an integer `unit` inside one subset file | everywhere | Criticality, location, configuration, operating context and maintenance windows cannot be expressed | blocker | Asset registry (Phase 3/4) |
| A3 | The data schema is the fixed 26-column C-MAPSS layout | `data.read_cmapss_txt`, `validate_schema` | Any other asset or site needs a new code path | blocker | Long-format readings contract (asset, timestamp, signal, value, unit, quality) plus adapters |
| A4 | RUL target capped at 125 cycles and thresholds of 10/25/50 cycles | `configs/default.yaml` (`rul_cap`, `agent.t_*`) | The cap is a C-MAPSS modelling convention; thresholds must come from maintenance lead times and consequences per asset class | major | Decision engine uses lead time, criticality and consequence; RUL cap documented as a model property |
| A5 | Cleaning statistics, regime clusters and features are fitted per C-MAPSS subset | `clean.py`, `baseline.prepare_frames` | A new asset type needs its own fitted pipeline and an applicability check before any prediction is shown | major | Model registry entries carry their scope (asset type, signals, operating envelope); out-of-scope inputs abstain |
| A6 | "New data" for retraining is simulated by held-out training engines; no real label pipeline | `retrain.run_retrain(simulate_new_data=True)` | Retraining on real data needs confirmed failure/repair outcomes, which do not exist in the system | major | Outcome feedback (Phase 3/6) produces labels; retraining stays gated |
| A7 | Batch imputation back-fills leading gaps (non-causal) | `clean.impute` | Harmless on C-MAPSS (no gaps) but wrong for live data | minor | Product ingestion forward-fills only and records imputation |

## B. Workflow, persistence and state

| # | Debt | Where | Why it matters | Severity | Plan |
|---|---|---|---|---|---|
| B1 | Work orders live in an in-memory `WorkOrderBook` rebuilt on every run and dumped to JSON | `agent.WorkOrderBook`, `pipeline.run` | No lifecycle (review, approval, assignment, execution, close-out), no persistence across runs, no idempotency | blocker | Persistent work-order workflow with explicit states, idempotency keys and audit (Phase 3) |
| B2 | Every pipeline run deletes the subset's decisions and orders from SQLite and unlinks the subset's audit log | `pipeline.write_sqlite` (`DELETE FROM`), `pipeline.run` (`audit_path.unlink()`) | History is lost on re-run; the "audit trail" only covers the latest run | blocker | Append-only event store with migrations; runs never delete history |
| B3 | "Escalate to a human" is a label; there is no user, approval, override or reason record | `agent.triage`, dashboard | A pilot needs to know who approved or rejected what and why | blocker | Users, roles, approvals and overrides (Phase 3/7) |
| B4 | No outcome feedback: nothing records what the technician found, what was repaired, or whether a failure occurred | — | Without outcomes, no recommendation can ever be confirmed or used for learning | blocker | Outcome records with contradiction checks (Phase 3) |
| B5 | Severity uses only the RUL lower bound; asset criticality, consequence, lead time, parts and technicians are ignored | `agent.triage` | Real priorities depend on consequence and resource constraints | major | Decision and scheduling engine (Phase 4) |
| B6 | The stream "replay" uses the batch run's fleet drift result for every cycle (look-ahead) | `pipeline.run` stream loop | A live stream cannot know the end-of-test fleet state | major | Drift evaluated on a trailing window in the service; documented until then |

## C. Models and model operations

| # | Debt | Where | Why it matters | Severity | Plan |
|---|---|---|---|---|---|
| C1 | `run` retrains every model from scratch; the MLflow `champion` alias is written but never read for inference | `pipeline.run`, `tracking.load_model` (unused by the pipeline) | Serving must use a pinned, approved model version, not whatever the last run produced | major | Model registry with explicit promotion and rollback; inference loads the approved version |
| C2 | The gated retraining flow keeps its own champion pickle (`gated_champion.pkl`) and registered model, separate from the pipeline's | `retrain.py` | Two sources of truth for "the current model" | major | One registry; one promotion path |
| C3 | Model artefacts are pickles loaded without integrity checks | `retrain.py`, `experiments/e3_stress.py`, pipeline outputs | Loading a tampered pickle executes code | major | Store a SHA-256 manifest with each artefact and verify before loading; never load from untrusted locations |
| C4 | Interval calibration is marginal over engines, single seed, and under-covers on FD004 (0.85) | `conformal.py`, `docs/EXPERIMENT_RESULTS.md` | Uncertainty shown to operators must be audited per operating condition | major | Calibration audit and alternatives (Phase 5) |
| C5 | Several design choices and monitoring rules were tuned while looking at official test results (documented) | `docs/KNOWN_LIMITATIONS.md` items 24-25 | Benchmark numbers are optimistic | minor | Keep the documented caveat; validation ladder level 2 uses fresh splits |

## D. Interfaces, security and operations

| # | Debt | Where | Why it matters | Severity | Plan |
|---|---|---|---|---|---|
| D1 | No API: the only interfaces are a CLI and a read-only Streamlit page | `cli.py`, `dashboard.py` | No integration with CMMS, historians or other tools | blocker | Versioned REST API (Phase 3/6) |
| D2 | No authentication or authorisation anywhere; the dashboard serves anyone who reaches the port | `dashboard.py` | Approval and override actions require identity and roles | blocker | API keys/sessions with roles (Phase 7) |
| D3 | No structured logs, metrics or health endpoints | everywhere | Operators cannot see whether ingestion or scoring is working | major | Structured logging, health and readiness endpoints (Phase 7) |
| D4 | No database migrations, backup or restore | `pipeline.write_sqlite` creates tables ad hoc | Upgrades would lose or corrupt data | major | Versioned migrations, online backup and restore test (Phase 7) |
| D5 | Paths default to the current directory; the project lives in a OneDrive-synced folder | `cli.py` defaults, workspace | SQLite and OneDrive sync can conflict; installs depend on where the command runs | minor | Configurable data directory outside sync folders in the deployment guide |
| D6 | Audit chain uses plain SHA-256 without a key or external anchor; truncation by an insider is undetectable | `audit.py` | Tamper evidence is limited | minor | Keyed (HMAC) chain plus periodic anchors recorded outside the log (Phase 7) |
| D7 | Dependency set is heavy (MLflow, Streamlit, plotly) and partly Windows-specific | `requirements.lock.txt` | Installation friction for another team | minor | Separate core, service and UI extras; documented install paths |

## E. Evidence and claims

| # | Debt | Where | Why it matters | Severity | Plan |
|---|---|---|---|---|---|
| E1 | Every ML result is on simulated C-MAPSS engines | `docs/EXPERIMENT_RESULTS.md` | No statement about real equipment can be made yet | blocker for field claims | Validation ladder (Phase 2), real public data where licensable |
| E2 | Competition documents describe the system in competition terms (Round 1/Round 2, rubric) | `docs/`, `submission/` | Product documents must not inherit competition framing or numbers out of context | minor | Product documents live under `product/`; competition material stays as history |

## Resolution status (updated 2026-10-18, after the product-platform work)

The register above is the Phase 0 audit of the competition baseline and is kept unchanged. The table below records what the product platform (`src/sentinelloop/app`, branch `product/platform`) did about each item. "Resolved in the platform" means the platform has a tested replacement. The competition pipeline itself is frozen and still has the item.

| item | status | where |
|---|---|---|
| A1 time model | resolved in the platform: epoch-ms UTC, refusal of naive timestamps, cycle-index assets declare hours per cycle | `timeutil.py`, `ingest.py`, `adapters/cmapss.py` |
| A2 asset registry | resolved | `registry.py`, `models.py` |
| A3 fixed C-MAPSS schema | resolved: long-format readings contract v1; wind signals added | `ingest.py`, `adapters/wind.py` |
| A4 cycle thresholds and RUL cap | resolved for decisions (risk horizons in hours, policy file); the C-MAPSS model keeps its cap, disclosed in the manifest | `configs/platform.yaml`, `decision.py` |
| A5 per-subset fitting | addressed: model bundles with scope checks (envelope, regime, sensor ranges); wind models commissioned per turbine | `modelpack.py`, `nbm.py` |
| A6 simulated "new data" | open: no real outcome data exist | KNOWN_LIMITATIONS E1 |
| A7 back-fill imputation | open in the C-MAPSS bundle (reused from the competition); the wind model forward-fills and back-fills only inside a scoring window and counts imputed cells | `nbm.py` |
| B1 in-memory work orders | resolved: persistent lifecycle | `workorders.py` |
| B2 history deleted on re-run | resolved in the platform: append-only tables and audit chain | `db.py`, `auditlog.py` |
| B3 escalation without identity | resolved: users, roles, approvals with reasons | `security.py`, `workorders.py` |
| B4 no outcomes | resolved: outcome records with contradiction flags; use for learning still PLANNED | `workorders.py` |
| B5 severity ignores consequence and resources | resolved: criticality, consequence and scheduling under constraints | `decision.py`, `scheduler.py` |
| B6 look-ahead in replay | not applicable to the platform (assessments use only data up to the instant) | `health.py` |
| C1 inference retrains | resolved: assessments load the approved, checksum-verified bundle | `health.py`, `modelreg.py` |
| C2 two champions | resolved in the platform: one registry, one approved model per scope | `modelreg.py` |
| C3 pickles without integrity check | resolved: SHA-256 recorded at registration, verified before unpickling; signed manifests PLANNED | `modelpack.load_bundle` |
| C4 marginal calibration | audited (C1): late-life under-coverage confirmed; Mondrian recalibration PLANNED | `RELIABILITY_AND_SAFETY.md` §4 |
| C5 tuning on test results | disclosed; product experiments tune on separate seeds (S1c/S1d) and pre-register G0 | `SCHEDULING_EVALUATION.md`, `evidence/g0/PREREGISTRATION.md` |
| D1 no API | resolved | `api.py`, `API_CONTRACTS.md` |
| D2 no authentication | resolved for the API and console (keys, roles); no SSO | `security.py` |
| D3 no logs or health endpoints | resolved: JSON request logs with request ids, `/health`, `/ready` | `api.py` |
| D4 no migrations or backup | resolved: checksummed migrations, online backup, restore, drill R1 | `db.py`, `admin.py` |
| D5 OneDrive folder | open for this workspace; deployments use explicit paths (`DEPLOYMENT_GUIDE.md`) | — |
| D6 unkeyed audit chain | resolved: HMAC chain plus anchor | `auditlog.py` |
| D7 heavy dependencies | addressed: `requirements-platform.txt` excludes mlflow | `SECURITY_REVIEW.md` §3 |
| E1 simulated data only | open: wind evaluated on SYNTHETIC data only; real-data G0 pre-registered, blocked on download | `VALIDATION_LADDER.md` |
| E2 competition framing | resolved for product documents (under `product/`) | — |
