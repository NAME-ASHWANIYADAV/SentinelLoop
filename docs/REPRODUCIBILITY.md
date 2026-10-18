# Reproducibility (Phase 3)

## Environment
- Python 3.12.1 in `.venv`; exact versions in `requirements.lock.txt` (numpy 2.2.6, pandas 2.3.3, scikit-learn 1.7.2, scipy 1.18.1, mlflow 3.0.1, SQLAlchemy 2.0.55, streamlit 1.66.0, plotly 5.24.1, pytest 8.4.2).
- Machine used for every number below: Windows 11 laptop, 12 logical CPUs, no GPU.
- Seeds: `seed: 42` in `configs/default.yaml`; every estimator receives `random_state`; conformal and fold splits use `numpy.random.default_rng(seed)`.

## Data
- Source: NASA PCoE archive (`pcoe_turbofan.zip`, 12,429,152 bytes, md5 `a83e8f128c59fc5614a4ca2e42a2e30c` = S3 ETag), inner `CMAPSSData.zip` md5 `79a22f36e80606c69d0e9e4da5bb2b7a`. `python -m sentinelloop data --download` fetches and verifies; `doctor` re-checks.
- Files and units (verified by loading): FD001 train 20,631 rows / 100 units, test 13,096 / 100; FD002 53,759 / 260, 33,991 / 259; FD003 24,720 / 100, 16,596 / 100; FD004 61,249 / 249, 41,214 / 248 (the readme states 248/249 for FD004; the files are authoritative). 26 columns: unit, cycle, 3 operating settings, 21 sensors.
- SHA-256 of every file is recorded in `artifacts/<subset>/metrics.json` → `data_hashes` and logged to MLflow.
- Licence: "License not specified" (data.nasa.gov); the archive is not redistributed with the submission; Saxena et al. (PHM08) is cited.

## Preprocessing and target (all fit on training engines only)
1. Per-unit forward fill then backward fill of missing sensor/setting values; `n_imputed` flag per row (C-MAPSS has no missing values; the path is exercised by the stress tests).
2. Operating regimes: KMeans on standardised operating settings (k = 1 for FD001/FD003, 6 for FD002/FD004; cluster purity on FD004 = 100%); per-regime mean/std scaling of sensors.
3. Drop list: sensors whose per-regime std on TRAIN is < 1e-3 (from `metrics.json`: FD001 s1, s5, s10, s16, s18, s19; FD003 s1, s5, s16, s18, s19; FD002 and FD004 s1, s5, s18, s19).
4. Features: raw kept sensors + causal rolling mean / std / OLS slope over 20 cycles + `cycle` + `regime` (operating settings are not model inputs). EMA denoising is disabled by default (see D13). Batch and stream features are computed with the same numpy arithmetic (D23); this moved the headline numbers by up to 0.3 RMSE relative to the pre-review pandas implementation (e.g. FD001 14.39 → 14.17, FD003 13.88 → 13.57).
5. Target: train RUL = max_cycle − cycle, capped at 125; test truth from `RUL_FD00x.txt`, reported capped and raw.

## Official evaluation protocol
Prediction at the last observed cycle of each test unit. RMSE against capped and raw truth; MAE; PHM08 score: d = pred − true, early (d < 0) exp(−d/13) − 1, late (d ≥ 0) exp(d/10) − 1, summed over engines. Validation on training engines: 5 engine-level folds; two protocols are reported, the honest random-truncation protocol and the leakage-prone "last cycle of a held-out training engine" protocol (always RUL = 0), to show the gap.

## E0 baseline results (`artifacts/baseline/<subset>/metrics.json`, copied to `experiments/results/e0_baseline/`; command `python -m sentinelloop baseline --subset all` as step 0 of `experiments/run_all.py`, 2026-10-18 final run)

| Subset | HGBR RMSE capped | HGBR RMSE raw | PHM08 | RandomForest capped | Naive mean capped | CV all rows | CV random truncation (honest) | CV last cycle (leaky) | Runtime |
|---|---|---|---|---|---|---|---|---|---|
| FD001 | **14.17** | 15.37 | 327.8 | 14.55 | 41.94 | 14.75 | 16.63 | 2.53 | 58 s |
| FD002 | **14.92** | 26.99 | 1027.7 | 15.17 | 44.93 | 15.32 | 15.71 | 3.49 | 207 s |
| FD003 | **13.57** | 15.32 | 356.0 | 15.22 | 43.70 | 11.94 | 12.40 | 2.98 | 71 s |
| FD004 | **15.15** | 26.89 | 1139.7 | 16.23 | 45.57 | 15.00 | 15.59 | 6.87 | 254 s |

Model: `HistGradientBoostingRegressor(max_iter=400, learning_rate=0.05, max_leaf_nodes=31, random_state=42)`, no hyperparameter search, trained on all training engines. RandomForest: 200 trees, `min_samples_leaf=5`.

Context (not a like-for-like comparison; protocols differ): the prior research script without regime normalisation gave FD001 14.2 / FD002 16.2 / FD003 14.1 / FD004 17.9 capped; published FD001 results range from ≈ 21 (SVR) to ≈ 11–13 (deep models). Our FD002/FD004 gains come from the regime normalisation (D14); the leakage-prone protocol would have reported 2.6–7.2 instead of 12.5–16.7.

Run-to-run variation: expect ±0.5 RMSE and ±20% PHM08 across machines, library versions and feature-arithmetic implementations (observed between the research script, the pre-review pandas features and the final numpy features). On this machine two consecutive runs are bitwise identical.

## Commands

```bash
.venv/Scripts/python.exe -m sentinelloop doctor
.venv/Scripts/python.exe -m sentinelloop baseline --subset all          # E0, ~12 min
.venv/Scripts/python.exe -m sentinelloop run --subset all               # end-to-end artefacts, MLflow, audit
.venv/Scripts/python.exe experiments/run_all.py                         # E1–E7
.venv/Scripts/python.exe -m pytest tests -q                             # 100+ tests incl. integration
```

Artefacts: `artifacts/<subset>/{metrics.json, predictions_test.csv, predictions_test_all_cycles.csv, conformal.json, anomaly.json, drift_reference.json, agent_thresholds.json, decisions_test.csv, decisions_stream.csv, work_orders.json, feature_manifest.json, *.pkl}`, `artifacts/audit/decisions_<subset>.jsonl` (one hash chain per subset), `artifacts/sentinelloop.db`, `artifacts/mlflow.db`.

## Final evidence run (2026-10-18, after the Phase 6 review; same machine and environment)
One command from a clean `artifacts/` and an empty `experiments/results/oof/` cache:

```bash
.venv/Scripts/python.exe experiments/run_all.py       # log: experiments/results/run_all_phase6.log (stdout), run_all_phase6.err (MLflow registry notices)
```

| Step | Command | Wall time |
|---|---|---|
| E0 | `python -m sentinelloop baseline --subset FD00x` ×4 | 60 + 209 + 74 + 257 s |
| pipeline | `python -m sentinelloop run --subset FD00x --stream-units 5` ×4 | 40 + 48 + 40 + 48 s |
| E1, E2 | `e1_policy_replay.py`, `e2_abstention.py` (OOF tables computed here) | 251 + 5 s |
| E5 | `e5_decision_vs_rmse.py` (OOF tables with RandomForest and naive baselines) | 1604 s |
| E3 | `e3_stress.py` | 83 s |
| E4, E4-secondary | `e4_retrain_gate.py`, `… --val-rows 20 --label-corruption --out e4_retrain_gate_secondary` | 169 + 213 s |
| E6, E7 | `e6_audit_check.py`, `e7_ablation.py --subsets FD001 FD004` | 3 + 101 s |
| E1 seeds | `e1_seed_sensitivity.py --subsets FD001 --seeds 42 43 44` | 98 s |
| total | | **55.0 min** |

Tests: `python -m pytest tests -q` (112 tests); the final full run is recorded in `docs/FINAL_VALIDATION.md`. Every `summary.json` carries `generated`, `seed` and the config hash of every subset; every `metrics.json` carries the config hash, the data SHA-256 hashes and the MLflow run id. The earlier staged logs (`full_run_stage*.log`) and the pre-review summaries (`analysis/evidence/results_pre_phase6/`) are kept for the audit trail only; no document quotes them. OOF caches are keyed by subset and mode; delete `experiments/results/oof/` to force recomputation (the final run started from an empty cache).
