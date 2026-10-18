# PROJECT STATUS — SentinelLoop (TELIPORT Season 4, Case Study 1 provisional)

Project root: `C:\Users\HP\OneDrive\Desktop\tata`. Updated after every phase. Vocabulary: VERIFIED / PARTIALLY VERIFIED / PROPOSED / BLOCKED.

## Phase 0 — Workspace audit and recovery (COMPLETE)
- Completed: inspected the workspace; located the five PDFs, the prior selection report, requirements matrix, scoring scripts and 26 agent outputs; copied the C-MAPSS archive into `data/raw/` and verified md5 = S3 ETag; created the project skeleton (`docs/ research/ src/ tests/ configs/ experiments/ artifacts/ data/ submission/`); wrote `docs/WORKSPACE_AUDIT.md` and `docs/DECISION_LOG.md`.
- Files changed: `docs/WORKSPACE_AUDIT.md`, `docs/DECISION_LOG.md`, `docs/OFFICIAL_REQUIREMENTS.md`, `PROJECT_STATUS.md`, `data/raw/*` (copied), `requirements.lock.txt` (pending venv).
- Commands executed: workspace listing; Python/package inventory; md5/sha256 of the dataset; unit-count check (FD001 100/100, FD002 260/259, FD003 100/100, FD004 249/248); venv creation with pinned packages (background).
- Test results: none yet (no code).
- Blockers: none. System Streamlit is broken (plotly mismatch) → isolated `.venv` created (VERIFIED: numpy 2.2.6, pandas 2.3.3, scikit-learn 1.7.2, scipy 1.18.1, mlflow 3.0.1, streamlit 1.66.0 imports OK, plotly 5.24.1, pytest 8.4.2; 92-line `requirements.lock.txt`).
- Risks: deadline (Round 1 single-slide PDF due 24 Oct 2026 per the Unstop listing, unconfirmed on an official page).

## Phase 1 — Requirements, strategy, final selection (COMPLETE)
- Completed: `docs/OFFICIAL_REQUIREMENTS.md` (PDF facts vs platform facts vs third-party vs unknowns; requirement checklist R1–R15); `docs/PROBLEM_SELECTION.md` (Case 1 CONFIRMED, high confidence); `docs/SCORING_AND_RISKS.md` (rubric targets, calendar, 12-item risk register).
- Evidence: 4-agent challenge workflow (Case 1 advocate, Case 3 advocate, effort/delivery reviewer, independent judge), outputs saved in `analysis/evidence/agent_outputs/phase1/`. Judge: Case 1, high confidence; Case 3's minimum submission 20–26 person-days vs Case 1's 13–16 inside the 30-day Round 2 window.
- Platform facts (Unstop listing, not Tata Elxsi's own page): Round 1 single-slide PDF by 24 Oct 2026 23:59 IST; Round 2 10-slide PPT + prototype 14 Nov–13 Dec 2026; teams 2–3; no criteria beyond the PDFs.
- Blockers: none for engineering. TEAM ACTIONS this week: confirm registration/upload mechanics on the portal (listing contradicts itself on dates), confirm member count and hours, accept the IP clause, set up a git remote.
- Risks: K1 (portal/registration) is the only fatal one and is outside this session's control.

## Phase 2 — Design (COMPLETE pending the prior-art document)
- Completed: `docs/SYSTEM_DESIGN.md` (components, interfaces, storage, config, Mermaid diagram), `docs/INNOVATION_HYPOTHESES.md` (H1–H7, each with a pre-registered success criterion), `docs/EXPERIMENT_PLAN.md` (E0–E7 with the shared data protocol), `docs/THREAT_MODEL_AND_FAILURE_MODES.md` (A–E with controls and checks).
- In progress: prior-art research agent writing `research/PRIOR_ART_AND_DIFFERENTIATION.md` (live web research; will be reconciled with the hypotheses when it returns).
- Status of hypotheses: all PROPOSED (no experiment run yet).

## Phase 3 — Reproducible baseline (COMPLETE)
- FINAL E0 (project code, EMA off, all engines, official last-cycle protocol; `docs/REPRODUCIBILITY.md`, `experiments/results/e0_baseline/`): capped/raw RMSE FD001 14.39/15.53 (PHM08 336), FD002 14.88/27.10 (1007), FD003 13.88/15.54 (398), FD004 15.36/27.05 (1219); RF 14.6–16.2; naive 42–46; leaky last-cycle CV 2.6–7.2 vs honest random-truncation CV 12.5–16.7. VERIFIED (run log + metrics.json + predictions archived).
- Earlier draft of this section (kept for the audit trail):
- Implemented (tests first, RED observed, then GREEN): `src/sentinelloop/{config,data,targets,clean,features,metrics,models,evaluate,baseline,cli}.py`; `configs/default.yaml` + per-subset overrides; `pyproject.toml`; `Makefile`; package installed editable in `.venv`.
- Tests: 34 Phase 3 tests pass (`tests/test_{data,targets,clean,features,metrics,evaluate,models,baseline_smoke}.py`), including causality/leakage checks, hand-computed PHM08 score, train-only drop list and regime scaler, FD001 smoke run.
- E0 first run with the project code (`experiments/results/e0_baseline/run.log`, 5-fold engine CV, all engines): FD001 HGBR 13.48 capped / 14.72 raw, PHM08 303.7, RF 13.55, naive 41.94, leaky last-cycle CV 2.44 vs honest random-truncation CV 15.12; FD002 17.77 / 28.69; FD003 13.01 / 14.71; FD004 22.20 / 32.72. VERIFIED as executed; FD002/FD004 flagged for investigation.
- Diagnosis (VERIFIED): KMeans(6) regime clustering is perfectly pure on FD004 (one cluster per operating condition); regime normalisation gives FD004 15.54 vs 17.95 without it (max_iter 200, no EMA). The 22.20 therefore comes from the E0 path's EMA smoothing (0.3) and/or max_iter 400; ablation running. Default config will be set from the ablation result.
- Blockers: none. Risk: dependency drift (SQLAlchemy 2.1 broke MLflow; pinned to 2.0, see D12).

## Phase 4 — End-to-end implementation (IN PROGRESS)
- Implemented (tests first): `conformal.py` (CQR on held-out engines), `anomaly.py` (healthy-baseline z-score health index; IsolationForest ablation), `agent.py` (rule table, escalation, work-order book), `audit.py` (hash chain + re-derivation), `drift.py` (PSI + quality), `policy.py`/`replay.py` (policy replay, decision metrics, threshold tuning, churn), `retrain.py` (gate), `stress.py` (fault injectors), `tracking.py` (MLflow SQLite + aliases), `stream.py` (incremental clean/features, tested equal to batch), `pipeline.py` (`python -m sentinelloop run`), `viewdata.py` + `dashboard.py` (Streamlit), CLI `run/audit/dashboard`.
- VERIFIED: end-to-end smoke test on FD001 (fast) passes: artefacts, MLflow run + `champion` alias, audit chain valid, 0 re-derivation mismatches, SQLite written. MLflow tracking tests pass after the SQLAlchemy pin.
- Fast validation chain on FD001 (v3, `experiments/results/smoke_fast_fd001_v3.log`): pipeline + all seven experiment scripts run end-to-end without errors; the chain exposed and fixed three design faults before the full run (D16 calibrated width, D17 age-matched drift, D19/D20 change-relative stress metrics and quality rules).
- Full run launched in stages (each ≤ 30 min): stage 1 `run --subset all` (full models, stream replay of 5 engines per subset) → stage 2 E1/E2 on FD001+FD002 → stage 3 E1/E2 on FD003+FD004 → stage 4 E5 (OOF with baselines) → stage 5 E3, E4, E6, E7. Logs: `experiments/results/full_run_stage*.log`.
- VERIFIED in the built-in browser (`.claude/launch.json` → `python -m streamlit run src/sentinelloop/dashboard.py`): Fleet tiles and table, Engine interval plot and stream table, Work orders (MAINTENANCE vs INSPECTION), Model & monitoring JSON, Audit table render on the FD001 full artefacts (RMSE 14.39/15.54, PHM08 336, PICP 0.94, MPIW 65, escalation share 0.15, 500 audit records). Deprecated `use_container_width` replaced.
- Not yet: retraining scenarios on all subsets (stage 5).

## Phase 4 result (full models, `python -m sentinelloop run --subset all`, stage 1 log) — VERIFIED
| Subset | RMSE capped / raw | PHM08 | PICP (90% nominal) capped / raw | MPIW | calibrated max_width | escalation share | work orders (batch+stream) | runtime |
|---|---|---|---|---|---|---|---|---|
| FD001 | 14.39 / 15.53 | 336 | 0.940 / 0.870 | 65.1 | 82.0 | 0.15 | 37+2 | 33 s |
| FD002 | 14.88 / 27.10 | 1007 | 0.896 / 0.676 | 56.9 | 77.2 | 0.09 | 89+3 | 46 s |
| FD003 | 13.88 / 15.54 | 398 | 0.910 / 0.800 | 68.8 | 111.7 | 0.11 | 22+2 | 35 s |
| FD004 | 15.36 / 27.05 | 1219 | 0.823 / 0.556 | 54.1 | 80.5 | 0.07 | 70+2 | 39 s |
No drift alarm and no quality flag on clean test data (age-matched monitor); 3,409 hash-chained audit records; MLflow run + `champion` alias per subset. FD004 under-covers (0.82 vs 0.90 nominal): reported, not hidden; an asymmetric-CQR option is being added as an ablation.

## Phase 5 — Experiments (COMPLETE; `docs/EXPERIMENT_RESULTS.md`, `docs/FAILURE_ANALYSIS.md`)
- VERIFIED: E5/H5 supported as registered (inverted RMSE-vs-decision-metric pairs on 4/4 subsets) with sizes stated: among point models the better-RMSE model discards 0.3–1.8 cycles more life; the lower-bound policy has identical RMSE and 12–17 cycles more discarded life; naive mean never orders. Log `experiments/results/full_run_stage4_e5.log` (OOF tables 232 / 746 / 265 / 773 s).
- Final hypothesis scoreboard: H1 NOT SUPPORTED, H2 NOT SUPPORTED, H3 SUPPORTED (3/4 faults), H4 NOT SUPPORTED as registered (reject path demonstrated on label corruption 4/4; drift trigger 4/4), H5 SUPPORTED, H6 SUPPORTED, H7 SUPPORTED. Every negative result is reported in the deck plan.
- Other Phase 5 outputs: `docs/REPRODUCIBILITY.md` run record, `docs/OFFICIAL_REQUIREMENTS.md` R1–R15 statuses, `docs/SYSTEM_DESIGN.md`/`docs/EXPERIMENT_PLAN.md` aligned with the built components, `submission/round2_deck_content.md` (draft), `README.md` results table, `artifacts/<subset>/retrain_log.json` now keeps both E4 runs tagged by run name; dashboard re-checked in the browser (audit verify on the per-subset log: 510 records, 0 mismatches).
- VERIFIED so far (full models, all four subsets): E0/H7 supported; E1/H1 pre-registered criterion NOT supported (lower-bound policy is a more conservative operating point, trade-off frontier reported); E2/H2 NOT supported (width-based abstention does not concentrate errors; escalation share 7–20%); E3/H3 supported for 3 of 4 faults with zero false alarms and silent-wrong-order rate 0 for the full agent (single-sensor bias is a per-engine detection floor, caught at fleet level); E6/H6 supported (3,409 decisions, 0 mismatches, tamper detected, 227 traceable orders).
- VERIFIED: E4/H4 pre-registered criterion NOT supported (4/8 outcomes as expected: the +3σ sensor-offset challenger was no worse on validation and was promoted on FD002–FD004; FD001's more-data challenger was rejected by a noisy coverage estimate); drift trigger supported 4/4. Secondary E4 (post hoc, D21; `experiments/results/e4_retrain_gate_secondary/`, 20 validation rows per engine, label-corruption scenario B2): B2 REJECTED on all four subsets with logged reasons (RMSE 4–5 worse); 7/12 as expected; absolute 0.85 coverage floor identified as the weak rule (FD004 more-data challenger rejected at 0.849 with RMSE 1.9 better).
- VERIFIED: E7 ablations (FD001, FD004): rolling features worth 1.6–2.7 RMSE, regime normalisation 1.3 RMSE on FD004, EMA helps FD001 but costs 6.6 RMSE on FD004, asymmetric CQR raises FD004 coverage 0.839 → 0.863 (+1.2 width).
- VERIFIED: full test suite 103 passed (`experiments/results/test_full_phase5.log`, exit 0) after the per-subset audit logs, asymmetric CQR and E4 changes.
- Running: E5 (stage 4, `experiments/results/full_run_stage4_e5.log`; FD001 and FD002 out-of-fold tables with baselines done in 232 s and 746 s).
- Files changed this phase: `docs/EXPERIMENT_RESULTS.md` (E0–E4, E6, E7), `docs/FAILURE_ANALYSIS.md`, `docs/INNOVATION_HYPOTHESES.md` (H1–H4, H6, H7 statuses), `docs/KNOWN_LIMITATIONS.md` (21–23), `docs/DECISION_LOG.md` (D21), `experiments/e4_retrain_gate.py` (`--val-rows`, `--label-corruption`, `--out`), `experiments/run_all.py` (secondary E4 step), `submission/CLAIM_EVIDENCE_MATRIX.md` (new), `submission/make_round1_slide.py` (two unverifiable claims removed, re-rendered), `README.md` (audit path).
- Hypothesis statuses updated in `docs/INNOVATION_HYPOTHESES.md`; every negative result is kept.

## Verified facts so far
- Dataset: `data/raw/pcoe_turbofan.zip` 12,429,152 bytes, md5 a83e8f128c59fc5614a4ca2e42a2e30c (VERIFIED).
- Prior baseline (analysis/evidence): FD001 test RMSE 14.18 capped / 15.42 raw, NASA 308 (VERIFIED by four runs in the prior session). Re-run under the new `.venv` (scikit-learn 1.7.2, numpy 2.2.6, pandas 2.3.3): RMSE 14.22 capped / 15.38 raw, NASA 314.0, RF 14.34, naive 41.94, 76 s (VERIFIED; log `experiments/results/env_check_fd001.log`). To be re-established in Phase 3 under the project code.
- Round 1 = single-slide PDF by 24 Oct 2026; Round 2 = 10-slide PPT + prototype by 13 Dec 2026 (PLATFORM listing, not Tata Elxsi's own page).

## Phase history
Phases 0–9 complete on 2026-10-18; numbers quoted in Phases 3–5 above are superseded by the Phase 6 evidence run (see `docs/NUMBERS.md`).

## Phase 6 — Adversarial red-team review and fixes (COMPLETE; `docs/RED_TEAM_REVIEW.md`)
- Review: nine reviewers + two sceptics per critical/high finding + a completeness critic (98 agents, 48 min; raw output `analysis/evidence/red_team_raw.json`): 157 findings (2 critical, 43 high, 69 medium, 43 low). Dispositions: 127 fixed, 18 disclosed, 5 partial, 6 open for the team, 1 refuted.
- Code changes (all under tests, 112 tests pass): batch features computed with the stream's arithmetic so stream = batch bitwise (D23); stream quality monitor, escalation reasons and top deviating features in stream decisions; work orders carry action, interval, due-by cycle, top sensors, timestamp; decisions store quality/drift flags; `decision_outcomes_test` (severity vs true RUL) in every `metrics.json`; `python -m sentinelloop retrain` (D24); gate late rate at the CRITICAL threshold and alias hand-back in E4 (D22); post-agent metrics and the audit terminal hash logged to MLflow; `baseline` writes to `artifacts/baseline/`; experiment summaries carry seed and config hashes; E3 reports the fleet rule's cost and the no-fleet-rule rate; MLflow/alembic log noise silenced; dashboard fixes; lock file (no machine path, `pywin32` Windows-only), `mlflow>=3.0,<3.1`, pytest options, `.gitignore`.
- Evidence regenerated from a clean `artifacts/` and empty OOF cache by ONE `experiments/run_all.py` invocation (55.0 min; `experiments/results/run_all_phase6.log`): E0, pipeline, E1–E7, secondary E4, E1 seed check. `docs/NUMBERS.md` (generated) is the single source every document quotes. Headline numbers moved by up to 0.3 RMSE because of D23 (FD001 14.17/15.37, FD002 14.92/26.99, FD003 13.57/15.32, FD004 15.15/26.89; PICP 0.94/0.89/0.92/0.85). **The Phase 4/5 numbers above are superseded** and kept only as history.
- New honest findings from the final run: tuned lower-bound thresholds are unstable across seeds (limitation 37); the full agent's zero silent-wrong-order rate relies on the fleet rule (0–12% without it; the rule escalates 25–36% of clean engines); FD003's clean early-life rows raise a fleet alarm; the late-rate gate now fires on label-corrupted challengers on FD003/FD004.
- Documents rewritten: threat model, system design, plan deviations, D21–D26, limitations 21–37, failure analysis 7–16, experiment results, reproducibility, requirements statuses, prior-art references, README, deck plan, demo runbook and script, claim–evidence matrix (C1–C25), Round 1 slide (redesigned, placeholder guard, metadata, 4-page variant, generated content plan).
- Open for the team (cannot be done here): registration/upload mechanics and the page rule on the portal (deadline 24 Oct 2026), team and college names, git remote and moving out of OneDrive, the recorded run, the IP clause.

## Phase 7 — Demo and judge experience (COMPLETE)
- `docs/DEMO_RUNBOOK.md` and `docs/DEMO_SCRIPT.md` rewritten against the final artefacts: live commands write to `artifacts_demo/` (never over the evidence), measured on this laptop: `run --subset FD001 --fast --stream-units 3` 19 s, `retrain --subset FD003 --simulate-new-data --fast` 20 s (the live gate PROMOTED the challenger: RMSE 14.95 → 13.98, coverage 0.91 → 0.94); dashboard re-checked in the browser on the final artefacts (fleet, model & monitoring with the decision-vs-truth table and both E4 runs, experiments with frontier tables and subset filter, audit verify: 510 records, 0 mismatches); the Experiments-tab crash on dict-shaped summaries fixed; CLI accepts `--out-dir` after the subcommand (test added).
- README results table and prose regenerated from `docs/NUMBERS.md`; `Makefile` targets match the CLI.

## Phase 8 — Submission package (COMPLETE except team inputs; `submission/README.md`)
- Round 1: `submission/SentinelLoop_Round1_CaseStudy1.pdf` (one page, 80 KB, metadata, problem block, corrected claims, body text 8 pt) and `SentinelLoop_Round1_design_deck.pdf` (4 pages); `round1_slide_content.md` generated from the same script; the script refuses a placeholder team name without `--allow-placeholder`. **Team must re-render with the real team and college names and confirm the page rule on the portal before 24 Oct 2026.**
- Round 2: `submission/SentinelLoop_Round2_deck.pptx` (10 slides, 79 KB) generated by `make_round2_deck.js` from the stored artefacts (native charts and tables; theme applied); structure validated with the pptx skill's `validate.py` (all checks passed); heuristic text-fit check clean; **visual check in PowerPoint is a team action** (no LibreOffice on this machine); `round2_deck_content.md` and `CLAIM_EVIDENCE_MATRIX.md` (C1–C25) final.
- Not produced here: the recorded clean-clone run, the repository link (git remote + IP clause), portal registration.

## Phase 9 — Final win-readiness audit (COMPLETE; `FINAL_HANDOFF.md`, `docs/FINAL_VALIDATION.md`)
- VERIFIED: full test suite 114 passed (`experiments/results/test_full_final.log`); `doctor: OK`; `audit`: 3,409 decisions, 0 mismatches; evidence run 55.0 min; Round 1 PDF and 4-page variant rendered; Round 2 PPTX validated.
- `FINAL_HANDOFF.md` written: summary, architecture and decisions, exact commands, verified metrics, demo instructions, requirement compliance, limitations, deliverable locations, blockers with the exact unblocking action, candid readiness assessment (no win probability).
- Remaining for the team: portal registration and upload mechanics (Round 1 deadline 24 Oct 2026), team/college names on the slide and deck, git remote and moving out of OneDrive, the recorded run, viewing the PPTX in PowerPoint.
