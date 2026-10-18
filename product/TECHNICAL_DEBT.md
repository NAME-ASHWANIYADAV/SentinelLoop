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

## Resolution status (updated 2026-10-18, after the Phase 9 review fixes)

The register above is the Phase 0 audit of the competition baseline and is kept unchanged. The table below records what the product platform (`src/sentinelloop/app`, `src/sentinelloop/console`, branch `product/platform`) did about each item, checked against the code after commits 38e8741 to 83f8509. "Resolved in the platform" means the platform has a tested replacement. The competition pipeline itself is frozen and still has the item. "KL" plus an ID is a row of `KNOWN_LIMITATIONS.md`; F-items are in §F below.

| item | status | where |
|---|---|---|
| A1 time model | resolved in the platform: epoch-ms UTC, refusal of naive timestamps, cycle-index assets declare hours per cycle. Assessment instants are bounded: future instants are refused and earlier ones are stored as replays that never move the state (PD-17) | `timeutil.py`, `ingest.py`, `adapters/cmapss.py`, `health.py` |
| A2 asset registry | resolved. No API route creates asset types or sites (KL P4) | `registry.py`, `models.py` |
| A3 fixed C-MAPSS schema | resolved: long-format readings contract v1; wind signals added, `pitch_angle` optional (om_manager-11). Open: per-site tag mapping (KL P12); turbine status, alarm and curtailment signals are not in the contract (KL M3) | `ingest.py`, `adapters/wind.py` |
| A4 cycle thresholds and RUL cap | resolved for decisions: risk horizons in hours (policy file) and site decision parameters from `serve --decision-config` (PD-24). The shipped values are placeholders (KL M5), and the RUL trigger ships at the untuned S1 settings (PD-27, KL M7). The C-MAPSS model keeps its cap, disclosed in the manifest | `configs/platform.yaml`, `configs/decision.example.yaml`, `decision.py` |
| A5 per-subset fitting | addressed: model bundles with scope checks (envelope, regime, sensor ranges); wind models commissioned per turbine (PD-12). Open: no re-commissioning prompt after a component replacement and no bulk re-commissioning after a model change (KL M6) | `modelpack.py`, `nbm.py` |
| A6 simulated "new data" | open: no real outcome data exist. Retraining exists only in the frozen competition pipeline; the platform has a model registry with approval and rollback, and no retraining (`CLAIM_EVIDENCE_MATRIX.md` P7) | KL E1 |
| A7 back-fill imputation | unchanged: open in the C-MAPSS bundle (reused from the competition); the wind model forward-fills and back-fills only inside a scoring window and counts imputed cells | `nbm.py` |
| B1 in-memory work orders | resolved: persistent lifecycle. Phase 9 added deferral reactivation, rejection suppression, hand-back, reprioritisation and a separate P1 for an urgent condition during lower-priority work (PD-18) | `workorders.py`, `decision.py` |
| B2 history deleted on re-run | resolved in the platform: no history table is deleted; readings, assessments, work-order events, outcomes and audit events are insert-only. Current-state rows (asset states, work orders, sync items, technicians, parts) are updated in place and are not covered by the audit chain (PD-22, KL S7). Shift plans are replaced in place: `set_shifts` with `replace_from` deletes the technician's shifts from that instant on, and its audit entry records only the count and span of the new shifts, not the rows removed | `db.py`, `auditlog.py`, `resources.py` `set_shifts` |
| B3 escalation without identity | resolved: users, roles, approvals and dismissals with reasons. Since Phase 9 a latch clears only when a person completes a qualifying work order, or when a planner, reliability engineer or admin dismisses it with a reason (PD-16). Open: technician resources are not linked to users (KL P10) | `security.py`, `workorders.py`, `states.py` |
| B4 no outcomes | resolved: outcome records with contradiction flags; the console requires the downtime and shows flags for review. Open: use for learning PLANNED; no instrument-check finding codes (KL M8) | `workorders.py`, `console/app.py` |
| B5 severity ignores consequence and resources | resolved: criticality, consequence and scheduling under constraints; anomaly orders are ranked within a class by deviation and consequence. Open: the platform MILP objective leaves out the site's downtime cost (F5) | `decision.py`, `scheduler.py`, `planning.py` |
| B6 look-ahead in replay | not applicable to the platform: assessments use only data up to the instant, and future instants are refused (PD-17). The competition stream replay still has it (`CLAIM_EVIDENCE_MATRIX.md` P8, P9) | `health.py` |
| C1 inference retrains | resolved: assessments load the approved, checksum-verified bundle | `health.py`, `modelreg.py` |
| C2 two champions | resolved in the platform: one registry, one approved model per scope | `modelreg.py` |
| C3 pickles without integrity check | resolved: SHA-256 verified before unpickling; registration hashes `bundle.pkl` against its manifest (security-13). Open: the expected hash still comes from the bundle's own manifest; signed manifests PLANNED (KL S3) | `modelpack.load_bundle`, `modelreg.register` |
| C4 marginal calibration | audited, not fixed. C1: late-life interval coverage 0.81–0.87. C2: the RUL model's P(failure) is not calibrated (PD-19). The console labels it "model-implied, not calibrated"; the CMMS description does not (F1). Recalibration OPEN (KL E5, E6) | `RELIABILITY_AND_SAFETY.md` §4, `product/evidence/calibration/` |
| C5 tuning on test results | addressed for product experiments: S2 tunes on FD001 engines and evaluates on FD003 engines (S1c and S1d had reused the same engine trajectories, data_scientist-9); W2 was tuned on synthetic fleets not used before and checked on held-out fleets; G0 was pre-registered and amended before download (PD-25). The competition caveat stays | `product/evidence/scheduling_v2/`, `product/evidence/wind_synthetic/w2.md`, `product/evidence/g0/PREREGISTRATION.md` |
| D1 no API | resolved; Phase 9 added `assess-range`, `reprioritise` and the `hand_back` transition | `api.py`, `API_CONTRACTS.md` |
| D2 no authentication | resolved for the API and the console (keys, roles); the console binds to 127.0.0.1 when started from the repository root (project `.streamlit/config.toml`; otherwise Streamlit's defaults apply); technician listings need `resources.read`. Open: no SSO (KL S3); the integration role is broader than one job needs (KL S6) | `security.py`, `.streamlit/config.toml` |
| D3 no logs or health endpoints | resolved: JSON request logs with request ids, `/health`, `/ready` (schema, audit-key and decision-config status) | `api.py` |
| D4 no migrations or backup | resolved: checksummed migrations (0001–0007), online backup with an anchor file, restore, drill R1 (re-run in Phase 9; every step passes) | `db.py`, `admin.py`, `product/evidence/recovery/r1.md` |
| D5 OneDrive folder | open for this workspace; deployments use explicit paths (`DEPLOYMENT_GUIDE.md`) | — |
| D6 unkeyed audit chain | resolved with limits: HMAC chain; `verify-audit` requires an anchor unless `--allow-no-anchor` (PD-22). Truncation is detected only against an anchor kept off the host, and only back to that anchor's sequence number; state tables are not covered (KL S7). Open: F2, F3 | `auditlog.py`, `admin.py` |
| D7 heavy dependencies | addressed: `requirements-platform.txt` excludes mlflow. Open: dependency advisories (KL S4) | `SECURITY_REVIEW.md` §3 |
| E1 simulated data only | open: wind evaluated on SYNTHETIC data only; G0 pre-registered and amended before download (PD-25), blocked on the user's download approval (PD-26) | `VALIDATION_LADDER.md`; KL E1, E2 |
| E2 competition framing | resolved for the documents under `product/`; the claim matrix marks competition-pipeline-only capabilities (buyer-3); the README front page is handled under review finding buyer-1 | `CLAIM_EVIDENCE_MATRIX.md` |

## F. Debt found in the Phase 9 review and the documentation sync

Found by the adversarial review (`ADVERSARIAL_REVIEW.md`) or while checking the documents against the code after its fixes, and not listed in `KNOWN_LIMITATIONS.md`. Review findings whose OPEN or PARTIAL part already has a row there are not repeated; they are cross-referenced after the table.

| # | Debt | Where | Why it matters | Severity | Plan |
|---|---|---|---|---|---|
| F1 | The CMMS request description shows the RUL model's P(failure) without the "model-implied, not calibrated" label the console uses, and gives the due date in UTC | `app/integration.py` `odoo_payload` | A planner working from the CMMS sees a probability that C2 shows is too low (about 0.55 shown where about 0.92 failed). Wind models carry no probability, so only RUL models are affected | major | The console's label (`console/client.explanation_lines`) in the payload, plus a contract test |
| F2 | `GET /api/v1/audit/verify` takes the anchor as optional, and the console's "Verify the audit chain" button calls it without one, so both report `valid: true` on a truncated chain | `app/api.py` `audit_verify`; `console/client.verify_audit`, `console/app.py` `page_audit` | The overclaim security-4 found in the CLI survives on the path an auditor is most likely to use | major | Require an anchor, or label the result "internal consistency only; truncation not checked" |
| F3 | `admin verify-audit` falls back to `<db>.anchor.json` beside the database, and `restore` copies the backup's anchor there. An anchor proves the chain only up to its own sequence number | `app/admin.py` `cmd_verify_audit`, `cmd_restore` | Anyone who can rewrite the database can rewrite an anchor on the same host. The off-host procedure in `OPERATIONS_RUNBOOK.md` §2.1 is the only protection, and comparing successive anchors is manual | minor | Warn when the anchor sits next to the database; check that each anchor's seq is not lower than the last one recorded |
| F4 | The console applies the site's time zone on the Fleet and Asset pages and in the Schedule page's proposal table only. The work queue, the deferred list, the approved-and-scheduled table and the job card call `when(..., None)` and show UTC, and the job card's "Returned to service at (local time ...)" entry is parsed as UTC. The console tests use a UTC site | `console/app.py` `page_queue`, `page_work`, `_tz(None)`; `tests/test_console.py` | At an Indian site a technician who enters local time records a return to service 5 h 30 min off, which distorts the downtime record. technician-9 is marked FIXED, but the fix covers only part of the console | major | Pass each order's site to `when` and `_tz`; add a non-UTC site to the console tests |
| F5 | The platform MILP objective uses only `cost_per_failure`. The site's downtime cost per hour (PD-24) reaches the risk-greedy order through the decision score, but not the MILP | `app/planning.py` `build_problem` (`failure_cost`), `app/scheduler.py` `start_cost` | buyer-6 asked for downtime in the scheduler objective; S2 priced downtime only inside the simulator. The MILP is a what-if planner (PD-27), so no default schedule depends on it | minor | Add the downtime term to the planner's failure cost and test it |
| F6 | Review fixes with no automated test: `assess_at: latest_reading` and `POST /assets/{id}/assess-range` (the export-site fix for om_manager-1); the `POST /work-orders/{id}/reprioritise` route (the service is tested); CMMS mirroring of COMPLETED, CLOSED and REJECTED orders (cancel and defer are tested); the console's waiting time and training-data caption | `app/health.py`, `app/api.py`, `app/integration.py`, `console/app.py` | These are marked FIXED in the review. Without tests a regression would go unnoticed, and sites that deliver daily exports depend on the export-site path | major | A test for each path |
| F7 | The decision-generation error entry returns the raw exception text to the caller and writes it into the audit chain | `app/decision.py` `generate` | PD-19 and security-11 keep exception text out of assessment reasons. This path can still expose internal detail, and the chain cannot redact it | minor | Log the details server-side; return and audit an error code |
| F8 | Code docstrings that contradict the code: `workorders.py` says any completed order clears the latch (PD-16 changed that); `api.py` and `security.py` say roles are enforced again inside every service, but the ingestion, assessment, decision-generation, registry and resource services take no role (`THREAT_MODEL.md` E1 was corrected under security-9) | `app/workorders.py`, `app/api.py`, `app/security.py` | A reviewer reading the code is told the pre-fix behaviour | minor | Correct the docstrings |
| F9 | G0's date stamps are local git commits (the repository has no remote). The external publication of the pre-registration's SHA-256, asked for in its §10, has not happened (data_scientist-7) | `product/evidence/g0/PREREGISTRATION.md` §10 | An outside reader cannot verify that the protocol predates the data | major for the G0 claim | The team publishes the hash (a pushed tag or a public registry entry) before the download |
| F10 | Assessability, the share of time the product can say anything, has been measured only on SYNTHETIC data and only per calendar hour: 0.54–0.59 (W2). The share of operating hours that the pilot criterion uses (≥ 70%, to agree) has never been measured (buyer-9, om_manager-8) | `product/evidence/wind_synthetic/w2.md`; `PILOT_ACCEPTANCE_CRITERIA.md` B1 | A gating pilot criterion has no evidence behind it; in the low-wind season the product may be silent most of the time | major | G0 reports assessability per farm (§10.2); the rung-4 back-test reports it per month |
| F11 | The platform has no re-derivation command. Each assessment stores its inputs reference, feature hash, model checksum and policy hash, but nothing recomputes a decision from them; the competition pipeline's re-derivation (3,409 decisions, 0 mismatches) does not carry over (`CLAIM_EVIDENCE_MATRIX.md` P6) | `app/health.py`, `app/decision.py` | Re-derivable decisions are listed as a possible differentiator (`COMPETITIVE_LANDSCAPE.md`; `CUSTOMER_DISCOVERY.md` IP6), but the platform cannot demonstrate one | minor | An admin command that re-derives stored assessments and their explanations |
| F12 | No test checks each documented row of the state-transition table (`RELIABILITY_AND_SAFETY.md` §2) against the code. `test_every_transition_in_the_table_is_exercised` only feeds every classification to the states reachable in four steps and checks that the result is a valid state. The clearing and approval functions are tested one by one elsewhere in `tests/test_app_states.py` and `tests/test_app_remediation.py`, but some rows are code only: the latch restart on an upgrade to URGENT, the AWAITING_ASSESSMENT label after a dismissal and its reset at the next assessment, and a `desk_review` completion keeping the latch. safety-8 is PARTIAL | `tests/test_app_states.py`; `app/states.py`, `app/workorders.py` `NON_CLEARING_JOBS` | The untested rows are latch rules, where the review found defects; a change to a row's destination would pass the suite | major | A table-driven test that asserts each documented row, including the clear and approval rows |

Review findings whose OPEN or PARTIAL part is tracked elsewhere:

| review finding (open part) | tracked in |
|---|---|
| om_manager-2 (bulk re-commissioning after a model change) | KL M6 |
| om_manager-3 (status, alarm and curtailment signals) | KL M3 |
| om_manager-4 (cranes, weather, travel, multi-day jobs) | KL P8 |
| om_manager-10 (OEM-serviced turbines) | KL P9 |
| om_manager-11 (per-site tag mapping) | KL P12 |
| om_manager-15, technician-7 (per-site role scoping, O&M reporting, follow-up job, shift editor) | KL P11 |
| data_scientist-4 (recalibration of P(failure)) | KL E6; F1 |
| data_scientist-6 (healthy alarm rate above the target on held-out synthetic fleets) | KL E7 |
| data_scientist-7 (external timestamp of the G0 pre-registration) | F9 |
| technician-8, technician-10 (deviations in °C, instrument finding codes, re-commissioning prompts) | KL M8, M6 |
| technician-9 (site-local times: partly fixed) | F4 |
| technician-11 (offline, mobile, language) | KL P7 |
| technician-12, security-5 (my jobs, assignment checks, integration role) | KL P10, S6 |
| security-4 (anchor paths that remain) | F2, F3 |
| safety-8 (a table-driven test of every documented state transition) | F12 |
| security-8 (streaming CSV parse) | KL S8 |
| security-10 (`/ready` and OpenAPI unauthenticated) | KL S7 |
| security-13 (signed manifests) | KL S3 |
| safety-9 (pseudonymisation, deletion, opaque audit actors) | KL S5 |
| buyer-6 (downtime in the scheduler objective) | F5 |
| buyer-9, om_manager-8 (assessability) | F10 |
| buyer-10 (Indian alternatives not verified) | KL C2 |
