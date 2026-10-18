# Threat Model and Failure Modes (Phase 2, revised after the Phase 6 red-team review)

"Threat" here means anything that makes the system wrong, unsafe, unreproducible or unconvincing. Each item has a control and a check. After the red-team review every control names only a mechanism that exists in the code or an artefact on disk; controls that were planned but not built are listed under "Not built" at the end.

## A. Scientific validity
| # | Failure mode | Control (as built) | Check (as it exists) |
|---|---|---|---|
| A1 | Data leakage: scalers/regime clusters fit on test; window-level splits; features that look ahead | Cleaning state (drop list, KMeans regimes, per-regime scaler) fit on training engines only (`clean.CleanState.fit` is called on `ds.train`); engine-level folds (`evaluate.engine_folds`); rolling features look backwards only (`features.build_features`); replay uses out-of-fold predictions (`oof.py`) | `tests/test_features.py` (feature at cycle t unchanged when later rows change), `tests/test_evaluate.py` (folds keep engines apart), `tests/test_clean.py` (train-only statistics), `tests/test_oof.py` |
| A2 | Tuning on the test set | Thresholds, margins and cost settings are tuned on tuning engines of the training split (`experiments/common.py: tune_eval_split`). **Disclosed deviation:** three binary design choices (EMA off, D13; regime normalisation on, D14; asymmetric CQR kept as a non-default option) were made by comparing official-test RMSE/PICP, and the monitoring rules D17/D19/D20 were iterated on FD001's official test engines (fast diagnostic chain); FD001's E3 and E4-drift rows are therefore the design set and FD002–FD004 are confirmatory. The test set was used more than once; the number of such decisions is small and listed in `docs/KNOWN_LIMITATIONS.md` | `docs/DECISION_LOG.md` D13, D14, D17, D19, D20; `docs/KNOWN_LIMITATIONS.md` (methodology) |
| A3 | Wrong target construction / censoring | Train RUL = max_cycle − cycle (run-to-failure, uncensored), capped at 125; test truth from the RUL file; replay reports "pending" for engines whose due time lies beyond observation | `tests/test_targets.py`; `docs/REPRODUCIBILITY.md` |
| A4 | Conformal coverage claimed as a guarantee | CQR calibrated on held-out training engines with random truncations; coverage reported as measured marginal coverage over engines, capped and raw truth, per subset, including under-coverage (FD004); the exchangeability assumption is written into `conformal.json` | `artifacts/<subset>/metrics.json` (`picp_test_capped`, `picp_test_raw`), `tests/test_conformal.py` |
| A5 | Residual drift "detected" live without labels | Only feature drift is live (age-matched PSI on early-life rows, `drift.DriftMonitor`); nothing in the code claims residual drift | `drift.py` has no residual path |
| A6 | Cost savings claimed from simulation | Cost ratios are assumptions swept in E1 (policy D); no document states a real-world saving | `submission/CLAIM_EVIDENCE_MATRIX.md` (claims not made) |
| A7 | Metric misreporting (capped vs raw; score convention) | Both RMSEs printed together everywhere; PHM08 convention string stored in every `metrics.json` and hand-checked | `tests/test_metrics.py` |
| A8 | Comparing to published numbers with different protocols | Literature numbers quoted as context only with the protocol difference stated | `research/PRIOR_ART_AND_DIFFERENTIATION.md`, `docs/REPRODUCIBILITY.md` |
| A9 | Single-seed results presented as stable | Main run uses seed 42 (pre-registered 5 seeds were not run); a post-hoc 3-seed sensitivity check of E1 on FD001 is reported separately (`experiments/results/e1_seed_sensitivity/`) | `experiments/e1_seed_sensitivity.py` |

## B. Safety and decision integrity
| # | Failure mode | Control (as built) | Check |
|---|---|---|---|
| B1 | Agent acts confidently on bad inputs | Window quality monitor (imputed fraction, missing, out-of-range, critical settings) and the fleet drift flag feed the agent in batch and stream mode (`pipeline.window_quality`, `pipeline.StreamQuality`); escalation rules R_ESC_QUALITY / R_ESC_DRIFT; E3 measures silent wrong orders with and without the fleet rule | E3; `tests/test_agent.py`; `tests/test_pipeline_smoke.py` (stream quality) |
| B2 | Interval too wide early in life | Width above the calibrated `max_width` on a MEDIUM/HIGH/CRITICAL decision adds `insufficient_evidence` and routes the decision to a human (INSPECTION order); severity itself is kept (not downgraded) | `tests/test_agent.py`; E2 (escalation share 7–20% on clean data) |
| B3 | Oscillating severities / duplicate work orders | One open order per unit; higher severity upgrades the order and moves its due-by cycle earlier, never later; no hysteresis on downgrades (not built: a downgrade never changes an open order); churn (severity changes before the first order) is measured in E1 | `tests/test_agent.py` (WorkOrderBook); E1 `churn` columns |
| B4 | Rule logic drifts from documentation | Rules are data (thresholds from config, reason codes) and every decision stores inputs, thresholds and the rule ids that fired; `audit.replay_check` re-derives every decision from its record | E6 (0 mismatches on every log) |
| B5 | Challenger promoted that is worse or unsafe | Gate: RMSE tolerance, PICP floor, late-rate non-regression (lower-bound policy at the CRITICAL threshold, D22); rejections logged with reasons in MLflow and `retrain_log.json`; every E4 scenario is gated against the same champion and the alias is handed back afterwards | E4, E4-secondary; `tests/test_gate.py`; `tests/test_retrain_flow.py` |
| B6 | A generative model invents risk or evidence | No LLM anywhere (PDF ground rule): no LLM package in `requirements.lock.txt`; all numbers come from stored predictions | dependency list; code |
| B7 | Audit log tampered or truncated | SHA-256 hash chain detects in-place edits and reordering (E6). **Not protected:** truncation of the tail and a full re-hash by someone with write access (no HMAC key, no external anchor other than the terminal hash and record count written to `metrics.json` and the MLflow run tags of the same run) | E6; `metrics.json` `audit_terminal_hash` |

## C. Engineering and reproducibility
| # | Failure mode | Control (as built) | Check |
|---|---|---|---|
| C1 | Environment breakage | Pinned `.venv` (`requirements.lock.txt`, no machine-specific lines, `pywin32` Windows-only marker); HGBR not LightGBM; `python -m sentinelloop doctor` | `doctor` output in `docs/REPRODUCIBILITY.md` |
| C2 | MLflow registry on file store / stages | SQLite backend; aliases only; MLflow pinned to 3.0.x | `tests/test_tracking.py` |
| C3 | Dashboard and pipeline writing at the same time | The dashboard reads JSON/CSV artefacts only (no database writes); the runbook never runs the pipeline into `artifacts/` during the demo (live runs use `--out-dir artifacts_demo`) | `docs/DEMO_RUNBOOK.md` |
| C4 | Dataset site unreachable | Hash-verified local copy; S3 URL with checksum in `data.py`; `python -m sentinelloop data --download` verifies | `doctor` checks both archive checksums |
| C5 | Non-determinism | Seeds in config; `random_state` everywhere; batch and stream features are computed with identical numpy arithmetic (D23); thread counts are not pinned, so bitwise equality across machines is not claimed | two full runs compared (`PROJECT_STATUS.md`); `tests/test_stream.py` |
| C6 | Long runtimes break the demo | Pre-computed artefacts shipped; the live demo runs the fast FD001 pipeline into a separate folder (about 10 s); `run` always retrains (no cache flag) | runbook timings measured from logs |
| C7 | Single laptop / OneDrive sync; no version control | Team action: move the project out of OneDrive and initialise a git remote (this session commits nothing by rule D9); artefacts carry config hash and MLflow run id, not a commit hash | — |

## D. Demonstration and judging
| # | Failure mode | Control (as built) | Check |
|---|---|---|---|
| D1 | Judges never run code | Deck carries every number with its artefact; annex: repository link (team action), clean-clone commands, recorded run (team action; no Dockerfile is shipped) | `submission/CLAIM_EVIDENCE_MATRIX.md` |
| D2 | Live demo fails | Deterministic scripted scenario; restore-from-zip reset; recorded fallback labelled as a recording | `docs/DEMO_RUNBOOK.md` |
| D3 | Over-claiming novelty | Prior art cited (Robinson 2026 for CQR on C-MAPSS; Romano et al. 2019 for CQR; Mitici 2023 and Lee & Mitici 2023 for decision-level metrics; the IntelliTwin repository for policy replay); nothing called "first"; "not found in our search" is the strongest wording used | `research/PRIOR_ART_AND_DIFFERENTIATION.md` |
| D4 | Mock data mistaken for live results | Dashboard banner: simulated data, stream = replay; deck says "simulated" on every C-MAPSS or injected-fault number | dashboard header |
| D5 | Deck over 5 MB (unverified limit) | Round 1 PDF is about 70 KB; the deck will be checked in Phase 8 | file size |

## E. Data and licensing
| # | Failure mode | Control |
|---|---|---|
| E1 | Redistributing the NASA archive against its (unspecified) terms | Download script instead of bundling; `.gitignore` excludes `data/raw/`; citation of Saxena et al. (PHM08) |
| E2 | Copying GPL notebook code | All code written in this project; references cited in the prior-art document |

## Not built (planned controls removed from the tables above)
`tests/test_leakage.py` (leakage is covered by the tests named in A1), `audit.explain()` (replaced by `audit.replay_check`), downgrade hysteresis (B3), `data --verify` (the download command verifies; `doctor` re-checks), `run --force` / cached artefacts (`run` always retrains), a Dockerfile, KS tests in the drift monitor (PSI only), a `drift_log` table and `retrain_log` table in SQLite (the retraining log is `artifacts/<subset>/retrain_log.json`), `model_quantile.pkl` and `predictions_oof_train.csv` (the CQR model is `model_cqr.pkl`; OOF tables live under `experiments/results/oof/`).
