# FINAL HANDOFF — SentinelLoop (Tata Elxsi TELIPORT Season 4, Case Study 1)

Project root: `C:\Users\HP\OneDrive\Desktop\tata` (one documented root; everything below is relative to it). Written 2026-10-18 at the end of Phase 9. Vocabulary: VERIFIED = executed here with the artefact stored; PARTIALLY VERIFIED = executed with a stated caveat; PROPOSED = designed, not measured; OPEN = needs the team.

## 1. Project summary
SentinelLoop is a closed-loop predictive-maintenance pipeline on the NASA C-MAPSS turbofan data (simulated engines, all four subsets FD001–FD004). It cleans and features the sensor stream with every fit on training engines only, predicts Remaining Useful Life with a HistGradientBoosting model plus a conformalized quantile regression 90% interval, runs a healthy-baseline health index, and lets a deterministic Triage Agent (no LLM) raise work orders from the interval lower bound, escalate untrustworthy inputs to a human, and record every decision in a hash-chained audit log that re-derives it. A drift monitor, a retraining command with a promotion gate (visible accept and reject), an MLflow registry on SQLite, a Streamlit dashboard and a cycle-by-cycle stream mode complete the loop. Seven hypotheses were pre-registered; three failed as registered and are reported as such. Case selection: `docs/PROBLEM_SELECTION.md` (Case 1 confirmed over Case 3; no evidence emerged to reopen it).

## 2. Architecture and key decisions
- `docs/SYSTEM_DESIGN.md` (components, interfaces, artefacts, configuration), `docs/DECISION_LOG.md` (D1–D26), `docs/THREAT_MODEL_AND_FAILURE_MODES.md` (controls as built, with a "not built" list).
- Decisions that shaped the result: HGBR instead of LightGBM/LSTM (D5); healthy-baseline z-score health index instead of IsolationForest (D10); EMA off (D13); regime normalisation (D14); calibrated interval-width limit (D16); age-matched drift monitoring (D17); change-relative stress metrics (D19); range reference and critical-setting rules (D20); secondary E4 scenario (D21); gate late rate at the CRITICAL threshold and alias hand-back (D22); batch features computed with the stream's arithmetic so stream = batch bitwise (D23); `retrain` command (D24); differentiation re-weighted to what was measured (D25).

## 3. Exact commands (from the project root, `.venv` active or prefixed as shown)
```bash
.venv/Scripts/python.exe -m sentinelloop doctor                                   # environment + data checksums
.venv/Scripts/python.exe -m sentinelloop run --subset all --stream-units 5        # end-to-end artefacts, 36-45 s per subset
.venv/Scripts/python.exe -m sentinelloop retrain --subset FD003 --simulate-new-data   # retraining flow (new data -> gate -> promote/reject)
.venv/Scripts/python.exe -m sentinelloop audit                                    # verify every audit chain, re-derive every decision
.venv/Scripts/python.exe -m sentinelloop dashboard                                # Streamlit on http://localhost:8501
.venv/Scripts/python.exe experiments/run_all.py                                   # EVERY number: E0, pipeline, E1-E7, secondary E4, seed check (55 min)
.venv/Scripts/python.exe experiments/numbers_digest.py                            # docs/NUMBERS.md from the artefacts
.venv/Scripts/python.exe -m pytest tests -q                                       # full test suite
.venv/Scripts/python.exe submission/make_round1_slide.py --team "Team · College" --deck
NODE_PATH=submission/deck_build/node_modules node submission/make_round2_deck.js --team "Team · College" --apply-theme <pptx-skill>/scripts/apply_theme.js
```
Fresh machine: `python -m venv .venv`, `pip install -r requirements.lock.txt`, `pip install -e . --no-deps`, `python -m sentinelloop data --download`, then `doctor`.

## 4. Verified metrics (final evidence run, one `run_all.py` invocation, 2026-10-18; `docs/NUMBERS.md`, `docs/EXPERIMENT_RESULTS.md`)
| Subset | RMSE capped / raw | PHM08 | coverage capped / raw | width | escalation share | orders |
|---|---|---|---|---|---|---|
| FD001 | 14.17 / 15.37 | 328 | 0.94 / 0.87 | 64.2 | 0.16 | 37 + 3 |
| FD002 | 14.92 / 26.99 | 1028 | 0.89 / 0.67 | 66.4 | 0.19 | 65 + 2 |
| FD003 | 13.57 / 15.32 | 356 | 0.92 / 0.81 | 71.6 | 0.10 | 23 + 2 |
| FD004 | 15.15 / 26.89 | 1140 | 0.85 / 0.58 | 54.4 | 0.08 | 71 + 2 |

Experiments (VERIFIED, artefacts under `experiments/results/<exp>/summary.json`): E0/H7 leakage audit 2.3–6.6× (supported); E1/H1 lower-bound policy discards 11.0–15.0 more cycles at the generic threshold, frontier 3/16 better and 3/16 dominated, tuned thresholds unstable across seeds (NOT SUPPORTED as pre-registered); E2/H2 abstention does not concentrate errors (NOT SUPPORTED); E3/H3 detection 98–100% on three faults with zero per-engine false alarms, silent wrong orders 0–20% (point agent) vs 0 (full agent) vs 0–12% (without the fleet rule), fleet rule escalates 25–36% of clean engines while active, one fleet-level false alarm on FD003 (SUPPORTED 3/4); E4/H4 gate 4/8 as pre-registered, label-corrupted challenger rejected 4/4 in the secondary run, drift trigger 4/4 (NOT SUPPORTED as pre-registered, reject path demonstrated); E5/H5 inversions on 4/4 (SUPPORTED, sizes stated); E6/H6 3,409 decisions re-derived with 0 mismatches, tamper detected (SUPPORTED); E7 ablations; E1 seed check (3 seeds, FD001).

## 5. Demo instructions
`docs/DEMO_RUNBOOK.md` (setup, reset, timings, fallbacks) and `docs/DEMO_SCRIPT.md` (seven beats, about 7 minutes). Live commands write to `artifacts_demo/`; the evidence in `artifacts/` is never touched. Measured on this laptop: the fast FD001 loop 19 s, the FD003 retraining flow 20 s.

## 6. Official-requirement compliance (`docs/OFFICIAL_REQUIREMENTS.md`, R1–R15)
R1–R13 VERIFIED (ingest batch/stream, missing values and noise, rolling features, anomaly detection, RUL, MLflow tracking, retraining flow, dashboard, rule-based agent with human escalation, mild imbalance handled by a healthy baseline, one command end-to-end, no LLM and open-source tools, all four subsets); R14 PARTIALLY VERIFIED (Round 1 PDF rendered; team/college names and the portal page rule are open); R15 PROPOSED (Round 2 PPTX built and validated; recording and visual check are team actions). Ground rules: no LLM anywhere (no LLM package in `requirements.lock.txt`), open-source only, documented design.

## 7. Limitations and risks (`docs/KNOWN_LIMITATIONS.md`, 37 items; `docs/RED_TEAM_REVIEW.md`, 157 findings)
Most important for a judge: simulated data and no cost claim; the official test set was used for three design toggles and FD001's monitoring rules (FD002–FD004 confirmatory); single seed except the E1 seed check; tuned lower-bound thresholds unstable; coverage subset-dependent (FD004 0.85); the full agent's zero silent-wrong-order rate relies on the fleet rule; the absolute coverage gate floor is the weak rule; the audit chain has no external anchor beyond MLflow; no CMMS integration; the project lives in OneDrive without version control.

## 8. Deliverable locations
- Submission: `submission/README.md` (index), `submission/SentinelLoop_Round1_CaseStudy1.pdf` (+ `.png`), `submission/SentinelLoop_Round1_design_deck.pdf`, `submission/SentinelLoop_Round2_deck.pptx`, `submission/round2_deck_content.md`, `submission/CLAIM_EVIDENCE_MATRIX.md`.
- Evidence: `artifacts/` (authoritative; `artifacts_pre_phase6/` is the superseded pre-review run and can be deleted), `experiments/results/` (summaries, `run_all_phase6.log`, `test_full_final.log`), `docs/NUMBERS.md`.
- Documents: `PROJECT_STATUS.md` (phase log), `docs/` (requirements, selection, scoring, design, hypotheses, plan, results, failure analysis, limitations, reproducibility, threat model, decision log, red-team review, demo runbook and script, final validation), `research/PRIOR_ART_AND_DIFFERENTIATION.md`.
- Code: `src/sentinelloop/`, `tests/`, `experiments/`, `configs/`, `Makefile`, `pyproject.toml`, `requirements.lock.txt`, `.gitignore`.

## 9. Blockers and the exact action to unblock each (all outside this session's control)
1. **Portal registration and upload mechanics (fatal if missed; Round 1 deadline 24 Oct 2026 23:59 IST).** Action: one team member logs in to the Unstop listing, registers the team (2–3 members, same college), opens the Round 1 upload form and notes whether it accepts one page or several and the size limit; then re-render the slide (or the 4-page variant) with the real names and upload.
2. **Team and college names.** Action: `python submission/make_round1_slide.py --team "<Team> · <College>" --deck` and `node submission/make_round2_deck.js --team "<Team> · <College>" …`.
3. **Version control and location.** Action: move the folder out of OneDrive, `git init`, commit, tag the evidence run, add the remote; accept the IP clause before sharing the repository link.
4. **Recorded clean-clone run.** Action: on the demo machine, record `doctor`, `run --subset FD001 --fast --stream-units 3 --out-dir artifacts_demo`, `retrain --subset FD003 --simulate-new-data --fast --out-dir artifacts_demo` and the dashboard walk-through; save as `submission/recording_<date>.mp4` and label it as a recording.
5. **Visual check of the PPTX in PowerPoint** (no LibreOffice here): open `submission/SentinelLoop_Round2_deck.pptx`, check every slide for text fit, then fix text in `make_round2_deck.js` and rebuild if needed.

## 10. Candid readiness assessment
Round 1 (one slide): ready to upload once the names are filled and the page rule is confirmed; the slide answers every PDF-named item, quotes only measured numbers, and states what is planned versus built. Round 2 (deck + prototype): the working pipeline, the measured evidence, the honest negative results and the reproducibility story are strong for the rubric's working-pipeline, data-engineering, MLOps and demo lines; model performance is ordinary by the published numbers (deep models reach ≈ 11–13 on FD001 against our 14.2) and the deck says so; the deck has been validated structurally but not viewed in PowerPoint; the recording and the repository link do not exist yet. No win probability is stated here: the only fatal risk is logistical (blocker 1), the rest is polish the team can do in the Round 2 window.
