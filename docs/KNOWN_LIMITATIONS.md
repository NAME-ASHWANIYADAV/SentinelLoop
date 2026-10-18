# Known Limitations (living document; updated after the experiments and the red-team review)

Honesty rules: simulated data is labelled; estimates are labelled; nothing below is hidden in the deck.

## Data and scope
1. **C-MAPSS is simulated turbofan data** with one snapshot per cycle and a prescribed train/test split. Nothing here is validated on real fleet telemetry; sampling-rate, missingness and sensor-fault patterns of real trucks or compressors are not represented.
2. **Test trajectories are right-censored** (observation ends before failure). Decision metrics on the official test set therefore contain "pending" engines; the leakage-free decision metrics come from out-of-fold replay over complete training trajectories.
3. **The RUL cap at 125** is a literature convention, not a physical fact; every RMSE is reported against capped and raw truth.
4. **No CMMS or ERP integration**: work orders are SQLite/JSON records with a documented schema.

## Models and uncertainty
5. **Conformal coverage is marginal over engines** and relies on exchangeability between calibration truncation points and test truncation points (Romano et al. 2019). Measured coverage is reported per subset; under-coverage on some subsets is possible and is shown, not hidden. Coverage is not a guarantee for an individual engine.
6. **The point model is a gradient-boosting model**, not the strongest published architecture; published deep models reach ≈ 11–13 RMSE on FD001 versus our ≈ 14. Model performance is 15% of the Round 2 rubric and was traded for explainability, CPU retraining and interval calibration.
7. **The anomaly health index** is a healthy-baseline z-score, which flags deviation from early-life behaviour; it does not identify fault modes.
8. **EMA denoising hurt** the multi-regime subsets (FD004 22.5 vs 15.4 RMSE) and is disabled by default; "basic noise handling" is therefore the per-unit imputation plus the rolling-window features.

## Monitoring and retraining
9. **Only feature drift is computed live.** Residual drift needs the true RUL, which is unknown until an engine fails; it is evaluated retrospectively on completed engines.
10. **The promotion gate uses assumed tolerances** (RMSE +2%, PICP ≥ 0.85, late-rate +0.02) chosen before the experiments; they are configuration, not learned.
11. **The drift scenarios are synthetic** (regime shift, biased sensors) and labelled as such.

## Decisions and evaluation
12. **Replay assumption**: the first work order is acted on immediately, so the useful life discarded equals the true RUL at that cycle. Real maintenance has lead times and scheduling constraints that are not modelled.
13. **Cost ratios in policy D are assumptions** swept over 5×–50×; no real-world saving is claimed anywhere.
14. **Thresholds are tuned on a tuning split of training engines**; they are not optimal for any real fleet.
15. **Escalation to a human is simulated** by routing; no human-in-the-loop study was performed.

## Engineering
16. **Single-machine, offline demo**; stream mode is a replay, not a message bus.
17. **Pickled artefacts** are produced and consumed only by this package on the same machine; never load pickles from untrusted sources.
18. **Dependency sensitivity**: SQLAlchemy 2.1 broke MLflow 3.0 (pinned); Streamlit/plotly mismatch broke the system Python (venv). The lock file is the reproducibility contract.
19. **Windows-specific**: RandomForest with many jobs can emit a joblib `CreateProcess` traceback (harmless).

## Competition format
20. The competition dates and format (one-slide Round 1, 10-slide Round 2 with prototype annex) come from the Unstop listing, not from a Tata Elxsi page; the 5 MB limit is a Season 3 precedent (unverified).

## Gate and monitoring (added after E4/E7)
21. **The coverage gate is noisy on small validation sets.** With 5 rows per validation engine on FD001 (100 rows) the PICP estimate moved from 0.97 to 0.80 and a better challenger was rejected; with 20 rows per engine the estimate was 0.835 (FD001) and 0.849 on 1,000 rows (FD004), and both better-RMSE challengers were rejected by the absolute floor. The floor should be relative to the champion (for example champion coverage minus 0.05, never below 0.80) before deployment; the absolute 0.85 rule is what was pre-registered and what every reported number uses.
22. **Not every data corruption is harmful to a tree model.** A constant sensor offset with correct labels (E4 scenario B) was promoted on FD002–FD004 because it did not worsen validation metrics; the gate protects against challengers that predict worse, not against every upstream fault. Upstream faults are the quality/drift monitor's job (E3), not the gate's.
23. **Asymmetric CQR is an option, not the default.** It improves FD004 coverage (0.839 → 0.863 on the ablation split) at +1.2 cycles of width; the pre-registered symmetric variant is what every headline number uses.

## Methodology (added after the Phase 6 red-team review)
24. **The official test set was used more than once.** Three binary design choices (EMA off, regime normalisation on, asymmetric CQR as a non-default option) were made by comparing official-test RMSE/PICP (D13, D14, E7), and the monitoring rules D17/D19/D20 were iterated against FD001's official test engines in the fast diagnostic chain. FD001's E3 and E4-drift rows are therefore design-set results; FD002–FD004 are confirmatory. The headline RMSEs were not tuned on the test set (no hyperparameter search), but the test set is not pristine.
25. **Single seed.** Every main-run number is from seed 42 (folds, calibration split, tune/eval split, random truncations). A post-hoc three-seed check of the core E1 comparison on FD001 is reported separately; no other experiment has a seed-to-seed spread.
26. **Cleaning statistics are fitted on all training engines.** Out-of-fold, holdout and validation splits refit the model, the interval calibration and the anomaly detector per fold, but the drop list, regime clusters and per-regime scalers are fitted once on every training engine (unsupervised statistics; expected effect small, not measured).
27. **Nested splits.** The E1 tuning engines, the deployed model's calibration engines and the first OOF folds come from the same seed-42 permutation, so the splits are nested rather than independent; tuned thresholds were evaluated on engines whose OOF predictions come from two of the five fold models.
28. **Discarded life is averaged over on-time orders only** (late orders excluded); lead time over all orders. Stated in E1/E5; it inflates discarded life for policies with many late orders (cost-tuned policies with 1–21% late orders).
29. **The headline RMSE is the all-engine HGBR; the agent acts on the 70%-engine CQR point model** whose RMSE is 0.3–0.6 worse (`cqr_point_rmse_capped` in `metrics.json`); both are reported.
30. **Batch imputation back-fills leading gaps within a unit** (uses the first observed value), stream mode forward-fills only; C-MAPSS has no missing values, so batch and stream are identical on the shipped data and differ only in the first cycles of a unit under the injected missing-value fault.
31. **The audit chain detects in-place edits and reordering, not truncation or a full re-hash by an insider** (plain SHA-256, no key); the terminal hash and record count are anchored in `metrics.json` and the MLflow run of the same pipeline run, which an insider with write access to both could still rewrite.
32. **E3's "zero false alarms" is per engine and change-relative** (an engine counts as a false alarm only if the clean half of the fleet newly raises a flag relative to its own clean run); the fleet-level monitor raised a severe single-feature alarm on the clean early-life rows of FD003's 50 clean engines (one fixed engine subset) in every scenario, which is a fleet-level false alarm and is reported in the E3 table.
33. **The full agent's zero silent-wrong-order rate in E3 comes largely from the fleet-level rule** (every HIGH/CRITICAL decision is escalated while the fleet alarm is active, and the fleet alarm fired in all 20 scenarios); the rate without the fleet rule and the rule's cost on clean engines (escalation share of clean engines) are reported in the E3 table after the review.
34. **Thread counts are not pinned**; bitwise reproducibility is verified on this machine (two full runs identical), not across machines.
35. **Test-suite blind spots**: the CLI argument parsing, the dashboard rendering and the experiment scripts are exercised only by running them; the stream path is tested end-to-end on FD001 (single regime) only.
36. **The project lives in a OneDrive-synced folder on one laptop with no version control**; artefacts carry a config hash and an MLflow run id, not a commit hash. Team action before Round 2: move out of OneDrive, initialise git, tag the evidence run.
37. **Tuned lower-bound thresholds are unstable.** Tuning the lower-bound policy's threshold to a 5% late target on 30 tuning engines gave 6, 2 and 0 cycles for seeds 42, 43 and 44 on FD001, with evaluation late rates of 1.4%, 20% and 54%; the point policy's tuned threshold stayed at 10–11 cycles. The tuned-threshold rows of E1 are illustrative, not a recommendation; a fleet would tune on far more engines and validate on held-out ones.
