# Experiment Plan (Phase 2)

All experiments are scripts under `experiments/` writing to `experiments/results/<exp>/` (raw outputs, `metrics.json`, plots, a short `README.md` stating hypothesis, protocol, result). Commands are listed so judges can re-run them. Seeds: 5 (42, 43, 44, 45, 46) wherever randomness exists; reported as mean ± std. Subsets: FD001–FD004 unless stated.

## Data protocol (shared)
- Official split: `train_FD00x.txt` for all fitting; `test_FD00x.txt` + `RUL_FD00x.txt` only for the final last-cycle metrics and for the test-engine replay view.
- Training engines are partitioned by engine id: **model folds** (5-fold GroupKFold) for out-of-fold (OOF) predictions over complete trajectories; inside each training fold a 30% **calibration** engine split for conformal calibration; OOF predictions are produced for every training engine by a model that never saw that engine.
- For policy experiments the OOF training engines are further split by engine id into **tuning** (30%) and **evaluation** (70%) sets; thresholds, margins and cost-optimal settings are chosen on tuning engines only.
- Random truncation: when validating "test-like" performance on training engines, each held-out engine is truncated at a random cycle (uniform over the engine's life), repeated 5 times per engine.
- Target: RUL capped at 125 for training; metrics reported against capped truth and raw truth.

## E0 — Baseline reproduction (Phase 3)
Naive mean-RUL, RandomForest, HGBR on each subset; official last-cycle RMSE (capped, raw), MAE, PHM08 score (convention printed), runtime. Also the leakage demonstration (H7): last-cycle CV RMSE on held-out training engines vs official test RMSE. Success: reproduces the prior numbers within ±0.5 RMSE.

## E1 — Maintenance-policy replay (H1)
Inputs: OOF point predictions and CQR intervals for every cycle of every training engine; failure cycle known. Policies: A point-threshold T; B point − margin m ≤ T; C lower-bound ≤ T; D threshold chosen on tuning engines to minimise expected cost under ratio r ∈ {5, 10, 20, 50}. Metrics per engine: first-order cycle; late (first order after failure − L_min, L_min = 5 cycles, or never); discarded life = true RUL at first order; lead time = same quantity (replace-at-order assumption, stated); alert volume = number of severity changes before first order; stability = number of severity downgrades/upgrades per engine; escalation share. Outputs: table per subset × policy; plot of discarded-life distribution; cost-ratio sensitivity. Second view: the same policies replayed on official test engines, reporting "ordered / pending (observation ended before due) / late" counts.

## E2 — Abstention (H2)
Same replay as E1 with the full agent (escalation on wide interval, bad quality, conflicting evidence, drift) vs the agent with escalation disabled. Report error rate among acted-upon engines vs all engines, escalation share, and which reason codes fired.

## E3 — Sensor stress and input quality (H3)
Fault injectors applied to official test trajectories with a known mask: (a) 20% missing values at random, (b) Gaussian noise 3σ on all sensors in a window, (c) +2σ bias on one informative sensor from a random cycle onward, (d) regime shift (FD002 operating settings substituted). Measure per window: quality-monitor flag, drift flag, RMSE change, PICP change, agent severity distribution, confident orders (CRITICAL/HIGH without escalation). Baselines: clean data; agent without quality/drift inputs.

## E4 — Drift and gated retraining (H4)
Scenario A (accept): champion trained on 70% of training engines; new data = remaining 30% arrives in `data/incoming/`; challenger retrained on all; gates evaluated on the fixed validation engines; expected PROMOTE. Scenario B (reject): new data = training engines with +3σ bias on two sensors (simulated bad sensors); expected REJECT with reasons. Scenario C (drift trigger): feed FD002-regime windows into the FD001 drift monitor → alarm expected; feed clean FD001 windows → no alarm expected (false-alarm count over 20 windows). All outcomes logged to MLflow and `retrain_log`.

## E5 — Decision metrics vs RMSE (H5)
Run E1 metrics for naive, RandomForest, HGBR point, HGBR+CQR policy C. Tabulate RMSE next to late rate and discarded life; look for ordering inversions.

## E6 — Audit reconstruction (H6)
Automated test: for each decision in `decisions_<subset>.jsonl` re-run `agent.triage` on the stored inputs and thresholds; compare; verify hash chain; tamper one record; expect failure.

## E7 — Ablations
Remove one component at a time on FD001 and FD004: (i) regime normalisation (FD004), (ii) rolling features (raw sensors only), (iii) anomaly input to the agent, (iv) conformal interval (policy A instead of C), (v) EMA denoise. Report RMSE and E1 decision metrics.

## Runtime budget
Each subset: training ≈ 1–4 min; 5-fold OOF ≈ 5–15 min; policy replay seconds; stress and retrain scenarios ≈ 5 min. Whole suite under one hour on this laptop (to be measured).

## Deviations from this plan (recorded after the Phase 5 run and the Phase 6 red-team review)
1. **Seeds.** The plan promised five seeds; the main run used one (seed 42) for every experiment. A post-hoc three-seed sensitivity check of the core E1 comparison on FD001 is reported in `experiments/results/e1_seed_sensitivity/` and is labelled as such; all other results are single-seed.
2. **Discarded life.** `replay.decision_metrics` averages discarded life over on-time orders only (late orders, whose true RUL at order is below the minimum lead, are excluded); lead time is averaged over all orders. Both E1 and E5 state this; the two numbers are therefore not identical as the plan assumed.
3. **Plots and per-experiment metrics.json.** Experiments write `summary.json`, `README.md` and CSV tables; no plots were produced and there is no separate `metrics.json` per experiment.
4. **E7 (iii).** The "anomaly input to the agent" ablation was not run (it cannot change the E1 policy metrics, which act on the point estimate or the lower bound only); (iv) is the point-vs-lower-bound column pair of the E7 table.
5. **E3 fleet alarm.** The plan did not define the fleet-level drift signal; E3 reports it separately (`fleet_drift_alarm_mixed_tail`, `fleet_drift_alarm_clean_early`) and, after the review, also the silent-wrong-order rate of the full agent WITHOUT the fleet rule and the fleet rule's cost on clean engines.
6. **E4 gate late rate.** Pre-registered at the HIGH threshold (25), where nobody is late; after the review the late-rate gate is evaluated at the CRITICAL threshold (D22) and both rates are logged.
7. **Design iteration on official test engines.** The monitoring rules D17/D19/D20 and the EMA/regime choices D13/D14 were set while looking at official-test results on FD001 (fast diagnostic chain) and the E0 test metrics; FD001's E3/E4-drift rows are the design set, FD002–FD004 are confirmatory (threat model A2).
