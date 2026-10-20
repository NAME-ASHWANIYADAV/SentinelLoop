# SentinelLoop

> **Product status (2026-10-18). Read this before anything else in the repository.**
>
> **What it is.** An advisory maintenance-decision prototype. It assesses asset data and flags assets for inspection. It drafts work orders, and a named person must approve each one. It runs as a REST API (`src/sentinelloop/app/`) with a Streamlit operator console (`src/sentinelloop/console/`).
>
> **What it is not.**
> - It is not production-ready. It is not a safety function and claims no SIL.
> - It never writes to a control system. It never triggers maintenance by itself.
> - It is not field-validated: no customer has been contacted, no real turbine or customer data have been run, and no pilot has taken place.
>
> **Evidence class.** All results are SIMULATED (NASA C-MAPSS turbofans) or SYNTHETIC (our own wind-SCADA generator). Public real wind data (CARE to Compare) have not been downloaded. The G0 test on them is pre-registered (`product/evidence/g0/PREREGISTRATION.md`) but not run.
>
> **Validation ladder** (`product/VALIDATION_LADDER.md`).
> - Highest rung reached: **2** (synthetic behaviour) for wind anomaly detection and the platform workflow; **1** (simulated benchmark) for RUL on C-MAPSS.
> - Rung 3 (public real field data, G0) is the next step. It is waiting for download approval.
> - No capability has reached rung 4, 5 or 6.
>
> **Unfavourable evidence, stated up front.**
> - The wind model is anomaly-only: it gives no remaining-life estimate and no failure probability.
> - The wind alarm setting (margin 1.25, sustain 18 operating points) was chosen on synthetic data only. On fresh held-out synthetic fleets it gave 0.44 healthy alarm episodes per turbine-year (1 in 2.27 turbine-years), but the 95% interval runs up to about 2.45, so the proposed pilot ceiling of 2 is not excluded. An earlier run's setting (sustain 6) gave 5.74, and drifting sensors still raise alarms (39 episodes on the fresh fleets) (`product/evidence/wind_synthetic/w3.md`; the 5.74 is from `product/evidence/wind_synthetic/w2.md`; interval and drift: `product/KNOWN_LIMITATIONS.md` E7, M1; `product/DECISION_LOG.md` PD-15). Counted the way the pilot's alarm-burden criterion counts (drifting-sensor turbines included), the fresh fleets give about 13 episodes per turbine-year, far above that ceiling (`product/PILOT_ACCEPTANCE_CRITERIA.md` B3). The real rate is unknown until G0.
> - RUL intervals under-cover near failure: 0.81–0.87 at true RUL 25–50 cycles against 0.90 nominal (`product/evidence/calibration/c1.md`).
> - The RUL model's P(failure) is not calibrated: about 0.55 shown where about 0.92 failed (`product/evidence/calibration/c2.md`).
> - The Odoo CMMS connector is shadow by default and tested only against a contract test double. A real Odoo instance has not been run.
>
> **Read next:**
> - `product/PRODUCT_STATUS.md`: what exists;
> - `product/KNOWN_LIMITATIONS.md`: what does not work, with severities;
> - `product/CLAIM_EVIDENCE_MATRIX.md`: every claim with its status and evidence.

## Product platform: where things are

| Path | Content |
|---|---|
| `product/` | Product documents (requirements, architecture, decision log, pilot protocol, limitations); evidence under `product/evidence/` |
| `src/sentinelloop/app/` | The product platform: ingestion, model registry, assessments, decision engine, work-order lifecycle, scheduler, CMMS integration, audit chain, REST API (`python -m sentinelloop.app.admin serve`) |
| `src/sentinelloop/console/` | Operator console, a thin Streamlit client of the API (`streamlit run src/sentinelloop/console/app.py`, run from the repository root, where `.streamlit/config.toml` binds it to 127.0.0.1; from any other directory Streamlit listens on every interface unless `--server.address 127.0.0.1` is passed; see `product/DEPLOYMENT_GUIDE.md` §1) |
| `tests/test_app_*.py`, `tests/test_console.py` | Platform and console tests |
| `sandbox/odoo/` | Local Odoo sandbox for the CMMS connector (not yet run) |

Install and run the platform with `product/DEPLOYMENT_GUIDE.md`. It uses `requirements-platform.txt`, not the competition setup below.

Platform tests: `python -m pytest tests -k "test_app_ or test_console"` (it works in PowerShell, cmd and POSIX shells; `tests/test_app_*.py tests/test_console.py` collects the same 496 tests but needs a POSIX shell to expand the wildcard). 21 of them need git-ignored local data and skip without it: the C-MAPSS files (`python -m sentinelloop data --download`) and the out-of-fold table from `python experiments/run_all.py`. A clean clone gives 474 passed, 22 skipped (checked on a copy of the working tree without the local data, including `tests/test_app_handoff_fixes.py`); the other skip is the Odoo sandbox test.

**Competition-pipeline-only capabilities.** Gated retraining, drift monitoring, the batch pipeline, stream replay and the competition dashboard exist only in the frozen competition code: `src/sentinelloop/*.py` outside `app/` and `console/`. The product platform does not include them. Drift monitoring and gated retraining for wind are PLANNED.

---

## Competition history (frozen; not product material)

Everything below describes the competition entry as submitted. It is kept as history: `main`, tag `competition-baseline`. Its documents under `docs/` and `submission/` are frozen (`product/DECISION_LOG.md` PD-02) and are not updated. Its numbers are benchmark results on simulated data, not product claims. Wording that the product rules forbid is qualified in brackets. "Agent" in this section always means the competition pipeline's deterministic triage rule table, never an AI agent.

Entry for Tata Elxsi TELIPORT Season 4, Case Study 1, "Self-Healing Machines: Predictive Maintenance for a Connected Fleet" (the case study's title) [nothing in SentinelLoop heals itself; every output is advisory]. It is a closed-loop [no autonomous maintenance action: work orders are drafts for a person; a retrained model replaces the old one automatically, but only if it passes the automated promotion gate] prognostics pipeline on NASA C-MAPSS (simulated engine data). The pipeline:
- predicts Remaining Useful Life with a conformal 90% interval [coverage is marginal over engines. It is below nominal on FD004 (0.85), near failure (0.81–0.87) and against the raw truth (0.58–0.87), so it is not "calibrated" without that qualifier];
- lets a deterministic Triage Agent [a rule table, not an AI agent] raise work orders [draft records; nothing is sent to or executed in any maintenance system] from the interval **lower bound** (a conservative operating point the operator chooses);
- escalates untrustworthy inputs to a human instead of acting on them;
- retrains only through a promotion gate;
- makes every decision re-derivable from its audit record [within one run: a re-run deletes the subset's stored decisions and audit log, `product/TECHNICAL_DEBT.md` B2].

No LLM anywhere (case-study ground rule).

Competition status and evidence: `PROJECT_STATUS.md`, `docs/`, `experiments/results/`, `submission/CLAIM_EVIDENCE_MATRIX.md` (every competition claim with its supporting artefact). The product's claim matrix is `product/CLAIM_EVIDENCE_MATRIX.md`.

### Results at a glance (full run, 2026-10-18, official last-cycle protocol; simulated C-MAPSS data)

| Subset | RMSE capped / raw (all-engine model) | RMSE capped (agent's model) | PHM08 | 90% interval coverage, capped / raw truth | mean width | work orders | escalated to a human |
|---|---|---|---|---|---|---|---|
| FD001 | 14.17 / 15.37 | 14.75 | 328 | 0.94 / 0.87 | 64 | 37 | 16% |
| FD002 | 14.92 / 26.99 | 15.23 | 1028 | 0.89 / 0.67 | 66 | 65 | 19% |
| FD003 | 13.57 / 15.32 | 13.54 | 356 | 0.92 / 0.81 | 72 | 23 | 10% |
| FD004 | 15.15 / 26.89 | 15.41 | 1140 | 0.85 / 0.58 | 54 | 71 | 8% |

Naive-mean baseline 41.9–45.6, RandomForest 14.6–16.2; the leakage-prone validation protocol would have reported 2.5–6.9 instead of the honest 12.4–16.6. Every number is regenerated by `experiments/numbers_digest.py` into `docs/NUMBERS.md`.

What the experiments showed (details and the negative results in `docs/EXPERIMENT_RESULTS.md`): the agent's [rule table's] quality and drift monitors catch missing values, noise and regime shifts on 98–100% of corrupted engines with zero additional per-engine false alarms, and the full agent [the complete rule table, including its fleet-level rule] issues no silent wrong order in any of 20 corruption scenarios (the point-threshold agent: 0–20%); most of that zero comes from the fleet-level rule, which also escalates 25–36% of healthy engines while a fleet alarm is active, and per-engine evidence alone leaves 0–12% (E3). Every one of 3,409 decisions re-derives from its audit record and in-place tampering is detected (E6). A challenger trained on wrongly labelled new data is rejected by the promotion gate on all four subsets with the reasons logged (E4, secondary run added post hoc); a harmless sensor offset is promoted on two of four [the pre-registered gate test met 4 of 8 expected outcomes, so H4 is NOT SUPPORTED; in it the sensor-offset challenger, expected to be rejected, was promoted on three of four subsets]. Acting on the interval lower bound is a conservative operating point that discards 11–15 more cycles of life per engine, not a free improvement, and its tuned thresholds are unstable across seeds (E1); width-based abstention alone did not reduce decision errors (E2); FD004 coverage is below nominal: all reported, none hidden.

### Setup (Windows, macOS or Linux; Python 3.11+, tested on 3.12.1)

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.lock.txt      # Windows (use .venv/bin/python elsewhere)
.venv/Scripts/python.exe -m pip install -e . --no-deps
.venv/Scripts/python.exe -m sentinelloop data --download              # fetches the NASA archive and verifies its checksum
.venv/Scripts/python.exe -m sentinelloop doctor
```

`doctor` checks the interpreter, package versions, the twelve C-MAPSS files and the archive checksums (md5 `a83e8f12…` = the NASA S3 ETag).

### Run

| Command | What it does |
|---|---|
| `python -m sentinelloop baseline --subset FD001` (`--subset all`) | E0 reproducible baseline: naive / RandomForest / HistGradientBoosting with the official last-cycle protocol, capped and raw RMSE, PHM08 score, engine-level CV incl. the leakage demonstration |
| `python -m sentinelloop run --subset FD001` (`--subset all`, `--fast`) | End-to-end: clean → features → point model + conformal interval → anomaly → drift → Triage Agent [rule table] → work orders → hash-chained audit log → SQLite → MLflow (sqlite backend, `champion` alias). Also replays the first N test engines cycle by cycle (`--stream-units`) |
| `python -m sentinelloop retrain --subset FD003 --new-data <file>` (`--simulate-new-data`, `--only-if-drift`) | The retraining flow when new data arrives: a challenger trained on the stored champion's engines plus the new engines is gated on held-out validation engines (RMSE, coverage, late-order rate) and promoted or rejected with the reasons logged to MLflow and `artifacts/<subset>/retrain_log.json` |
| `python -m sentinelloop audit` | Verifies the audit hash chain and re-derives every stored decision |
| `python -m sentinelloop dashboard` | Streamlit dashboard (fleet, engine, work orders, model & monitoring, experiments, audit) |
| `python experiments/run_all.py` (`--fast`, `--skip-baseline`) | The whole evidence run: E0 baseline, pipeline for all subsets, experiments E1–E7 (policy replay, abstention, stress, gated retraining primary and secondary, decision-vs-RMSE, audit, ablations) and the E1 seed check; summaries in `experiments/results/<exp>/summary.json`; `experiments/numbers_digest.py` prints every number the documents quote |
| `python -m pytest tests -q` | Test suite (fast unit tests plus slow integration tests on the real data, including stream-equals-batch and the retraining flow). 27 tests need the C-MAPSS files or the out-of-fold table from `experiments/run_all.py` and skip without them: a clean clone gives 582 passed, 28 skipped |

Artefacts land in `artifacts/<subset>/` (metrics, predictions, models, decisions, work orders), `artifacts/audit/decisions_<subset>.jsonl`, `artifacts/sentinelloop.db`, `artifacts/mlflow.db` + `artifacts/mlruns/`. Inspect MLflow with `python -m mlflow ui --backend-store-uri sqlite:///artifacts/mlflow.db`.

### Layout (competition pipeline)

```
configs/        default.yaml + per-subset overrides (every threshold lives here)
src/sentinelloop/
  data.py clean.py features.py targets.py   loading, schema checks, train-only cleaning, causal features
  models.py conformal.py anomaly.py          point model, CQR intervals, healthy-baseline health index
  agent.py audit.py drift.py retrain.py      Triage Agent [rule table] + work-order book, hash-chained audit, drift/quality, promotion gate
  policy.py replay.py oof.py stress.py       policy replay harness, out-of-fold predictions, fault injectors
  tracking.py stream.py pipeline.py cli.py   MLflow, stream mode, end-to-end run, CLI
  viewdata.py dashboard.py                   Streamlit dashboard
tests/          pytest suite (unit tests on synthetic frames, integration tests on the real data)
experiments/    e1..e7 scripts, run_all.py, results/
docs/           requirements, design, hypotheses, experiment plan, results, failure analysis, red-team review, limitations, demo runbook, numbers digest
submission/     Round 1 slide, Round 2 deck, claim–evidence matrix
analysis/       the prior case-selection study (read-only)
```

The product platform (`src/sentinelloop/app/`, `src/sentinelloop/console/`, `product/`) is described in the status banner at the top.

### Metrics and conventions
- Official protocol: prediction at the last observed cycle of each test engine vs `RUL_FD00x.txt`. The headline RMSE is the all-engine HistGradientBoosting model; the agent acts on the 70%-engine model whose other 30% calibrate the interval (`cqr_point_rmse_*` in `metrics.json`, reported alongside).
- RMSE is always reported against RUL **capped at 125** and against **raw** truth.
- PHM08 score: d = pred − true; early d<0: exp(−d/13) − 1; late d≥0: exp(d/10) − 1; summed over engines.
- Interval coverage (PICP) and width (MPIW) at 90% nominal, calibrated on held-out engines with random truncations; coverage is marginal over engines under an exchangeability assumption (stated, not guaranteed) [and below nominal on FD004 (0.85) and against the raw truth (0.58–0.87), table above].

### Troubleshooting
- `import streamlit` fails on a system Python: use the venv (a plotly 4.x install breaks Streamlit).
- MLflow `ImportError … FallbackAsyncAdaptedQueuePool`: SQLAlchemy 2.1 is incompatible with MLflow 3.0; the lock file pins SQLAlchemy 2.0.
- data.nasa.gov unreachable: the download uses the NASA PCoE S3 mirror with a checksum; keep `data/raw/` once fetched.
- Windows `joblib` traceback with RandomForest: harmless; reduce `n_jobs` in `models.py` if it recurs.
- Dashboard shows nothing: run `python -m sentinelloop run --subset FD001` first.

## Citation and licence
Dataset: A. Saxena, K. Goebel, D. Simon, N. Eklund, "Damage Propagation Modeling for Aircraft Engine Run-to-Failure Simulation", PHM08; NASA Prognostics Center of Excellence data repository (licence not specified; cite, do not redistribute). Methods we build on: Romano, Patterson, Candès, "Conformalized Quantile Regression" (NeurIPS 2019); Robinson, IJPHM 17(1) 2026 (CQR for RUL on C-MAPSS); Mitici et al. 2023 and Lee & Mitici 2023 (decision-level evaluation of prognostics); the IntelliTwin repository (policy replay of a maintenance agent on C-MAPSS). Full search and wording rules in `research/PRIOR_ART_AND_DIFFERENTIATION.md`; nothing here is claimed as first. Project code: MIT (see `LICENSE`).
