# Experiment Results (Phase 5, final evidence run after the Phase 6 red-team review)

Every number below is copied from `docs/NUMBERS.md`, which `experiments/numbers_digest.py` generates from the stored artefacts of ONE invocation of `experiments/run_all.py` on 2026-10-18 (log `experiments/results/run_all_phase6.log`, 55.0 minutes wall time, seed 42, Windows 11 laptop, 12 logical CPUs, no GPU). Earlier numbers in the project history (Phase 4/5 status entries, `analysis/evidence/results_pre_phase6/`) come from the pre-review code and differ by up to 0.3 RMSE because the rolling features are now computed with the stream's arithmetic (D23). All data are simulated NASA C-MAPSS engines; no real-world cost or safety claim is made. Hypothesis statuses use the pre-registered criteria of `docs/INNOVATION_HYPOTHESES.md`; negative results are kept.

## E0 — Baseline (official last-cycle protocol) and the leakage audit (H7) — **SUPPORTED**

| Subset | HGBR RMSE capped / raw | PHM08 | RandomForest | naive mean | CV random truncation (honest) | CV last cycle (leaky) | ratio |
|---|---|---|---|---|---|---|---|
| FD001 | 14.17 / 15.37 | 328 | 14.55 | 41.94 | 16.63 | 2.53 | 6.6× |
| FD002 | 14.92 / 26.99 | 1028 | 15.17 | 44.93 | 15.71 | 3.49 | 4.5× |
| FD003 | 13.57 / 15.32 | 356 | 15.22 | 43.70 | 12.40 | 2.98 | 4.2× |
| FD004 | 15.15 / 26.89 | 1140 | 16.23 | 45.57 | 15.59 | 6.87 | 2.3× |

The leakage-prone protocol ("last cycle of a held-out training engine", where RUL is always 0) overstates performance by 2.3–6.6× relative to the honest random-truncation protocol. Dropped sensors (train-only variance rule): FD001 s1, s5, s10, s16, s18, s19 (62 features); FD002 and FD004 s1, s5, s18, s19 (70); FD003 s1, s5, s16, s18, s19 (66). Regime clusters recover the six operating conditions with purity 1.00 on FD002 and FD004 (`experiments/results/regime_purity.json`).

## Pipeline — the deployed system on the official test engines

| Subset | HGBR RMSE capped / raw | agent's model (CQR point) capped / raw | PICP capped / raw (90% nominal) | MPIW | calibrated width limit | escalation share | orders batch + stream | audit records | elapsed s |
|---|---|---|---|---|---|---|---|---|---|
| FD001 | 14.17 / 15.37 | 14.75 / 15.87 | 0.940 / 0.870 | 64.2 | 80.3 | 0.16 | 37 + 3 | 510 | 36.6 |
| FD002 | 14.92 / 26.99 | 15.23 / 27.17 | 0.892 / 0.672 | 66.4 | 96.6 | 0.19 | 65 + 2 | 971 | 45.2 |
| FD003 | 13.57 / 15.32 | 13.54 / 15.24 | 0.920 / 0.810 | 71.6 | 116.1 | 0.10 | 23 + 2 | 897 | 36.3 |
| FD004 | 15.15 / 26.89 | 15.41 / 27.34 | 0.847 / 0.577 | 54.4 | 80.5 | 0.08 | 71 + 2 | 1031 | 44.8 |

The headline RMSE is the all-engine model; the agent acts on the 70%-engine model whose other 30% calibrate the interval (0.3–0.6 RMSE worse except FD003). Coverage is against capped truth; raw-truth coverage is lower because raw RUL exceeds the 125 cap early in life. FD004 under-covers (0.847) and is reported as such. No drift alarm and no quality flag on clean test data. Stream replay (first five engines per subset, cycle by cycle) gives the same predictions, flags and severities as the batch path for the same cycles (bitwise; `tests/test_pipeline_smoke.py`).

Agent decisions against the true RUL of the official test engines (`decision_outcomes_test` in `metrics.json`):

| Subset | engines with true RUL ≤ 25 not HIGH/CRITICAL | confident (non-escalated) HIGH/CRITICAL orders on engines with true RUL > 50 | lower bound above the true RUL | health-index flag rate, true RUL ≤ 25 / 26–50 / > 50 |
|---|---|---|---|---|
| FD001 | 5.3% | 1 engine (1.0%) | 5.0% | 0.47 / 0.36 / 0.03 |
| FD002 | 1.7% | 0 | 10.8% | 0.69 / 0.23 / 0.01 |
| FD003 | 0.0% | 1 engine (1.0%) | 8.0% | 0.69 / 0.54 / 0.06 |
| FD004 | 8.0% | 0 | 14.5% | 0.30 / 0.13 / 0.01 |

Reading: the lower bound is optimistic for 5–15% of engines (most of them early in life where it does not matter for an order); the engines that are genuinely close to failure are almost all HIGH or CRITICAL; the health index fires on 30–69% of engines within 25 cycles of failure and on 1–6% of healthy ones, which is the anomaly detector's measured performance on real degradation.

## E1 — Policy replay (H1) — **NOT SUPPORTED as pre-registered; reported as a trade-off**
Out-of-fold predictions over complete training trajectories (5 engine folds), tuning engines (30%) for thresholds, evaluation engines (70%) for metrics, minimum lead 5 cycles. Discarded life is averaged over on-time orders (late orders excluded); lead time over all orders.

| Subset | policy | threshold | late rate | mean discarded life | churn |
|---|---|---|---|---|---|
| FD001 | A point ≤ 25 | 25 | 0.000 | 25.2 | 5.03 |
| FD001 | C lower bound ≤ 25 | 25 | 0.000 | 40.3 | 5.53 |
| FD001 | C lower bound, tuned | 6 | 0.014 | 14.2 | |
| FD002 | A point ≤ 25 | 25 | 0.000 | 26.5 | 5.03 |
| FD002 | C lower bound ≤ 25 | 25 | 0.000 | 39.2 | 5.07 |
| FD002 | C lower bound, tuned | 5 | 0.071 | 11.2 | |
| FD003 | A point ≤ 25 | 25 | 0.000 | 25.7 | 4.49 |
| FD003 | C lower bound ≤ 25 | 25 | 0.000 | 36.7 | 5.33 |
| FD003 | C lower bound, tuned | 4 | 0.057 | 10.2 | |
| FD004 | A point ≤ 25 | 25 | 0.006 | 25.7 | 5.52 |
| FD004 | C lower bound ≤ 25 | 25 | 0.000 | 38.9 | 5.75 |
| FD004 | C lower bound, tuned | 8 | 0.006 | 14.3 | |

Findings:
1. At the generic threshold (25 cycles) both policies are never late on FD001–FD003 (test (i) is uninformative there) and the lower-bound policy is never late on FD004 where the point policy is late once (1/174). The lower-bound policy discards 11.0–15.0 more cycles of life per engine than the point policy at that threshold (FD001 15.0, FD002 12.7, FD003 11.0, FD004 13.2). Policy B (point minus margin) is the same family as A and collapsed onto it (margin 0), so test (ii) holds trivially; the pre-registered criterion is NOT SUPPORTED.
2. Secondary frontier (A-family vs C-family tuned to late-rate targets 0, 2.5, 5, 10% on the tuning engines, evaluated on the evaluation engines): the lower-bound family is better or equal on both metrics at 3 of 16 points (all FD004), dominated at 3 of 16 (FD002, FD003), and a trade-off elsewhere; where it has the lower late rate (10 of 16 points) it costs between −0.9 and +6.1 cycles of discarded life.
3. Tuned lower-bound thresholds of 4–8 cycles give evaluation late rates of 1.4% (FD001), 7.1% (FD002, above its 5% tuning target), 5.7% (FD003, above target) and 0.6% (FD004). Cost-tuned point thresholds move from 8–13 (cheap failures, ratio 25) to 10–17 (ratio 500); FD003 is insensitive to the cost ratio (11 throughout).
4. Seed sensitivity (post hoc, FD001, seeds 42/43/44; `e1_seed_sensitivity`): the T = 25 gap is stable (15.0, 16.3, 16.6 cycles; late rates 0 for both). The TUNED lower-bound threshold is not: 6, 2 and 0 cycles, with evaluation late rates of 1.4%, 20.0% and 54.3%; the tuned point threshold stayed at 10–11 with late rates 1.4–5.7%. Tuning the lower-bound threshold to a 5% late target on 30 tuning engines is unreliable, and finding 3 must be read with that in mind. Deploying either generic or tuned thresholds requires per-fleet calibration on far more engines.

## E2 — Abstention (H2) — **NOT SUPPORTED**
| Subset | eval engines | error rate, all decisions | error rate, acted upon (not escalated) | error rate, escalated | relative change | escalation share |
|---|---|---|---|---|---|---|
| FD001 | 70 | 0.157 | 0.150 | 0.200 | −4.5% | 0.143 |
| FD002 | 182 | 0.093 | 0.104 | 0.036 | +11.2% | 0.154 |
| FD003 | 70 | 0.071 | 0.078 | 0.000 | +9.4% | 0.086 |
| FD004 | 174 | 0.103 | 0.106 | 0.077 | +2.1% | 0.075 |

Escalating on interval width, quality, drift or conflict removes 7.5–15.4% of engines from automatic action but does not concentrate the errors: the acted-upon engines have an equal or higher error rate on 3 of 4 subsets (the pre-registered criterion needed a 20% reduction on 3 of 4). Width-based abstention alone is not a safety mechanism on clean data; its value shows up only under corrupted inputs (E3).

## E3 — Stress tests on corrupted inputs (H3) — **SUPPORTED for 3 of 4 pre-registered faults**
Half of the official test engines are corrupted over their last 20 cycles; the other half stay clean. Detection and false alarms are change-relative to the clean run of the same engines (an engine counts only if it newly raises a quality flag, a sustained anomaly or an escalation); "silent wrong order" = HIGH/CRITICAL issued without escalation that differs from the clean decision.

| Fault | per-engine detection (FD001 / FD002 / FD003 / FD004) | false alarms on clean engines | silent wrong orders: point-threshold agent | full agent | full agent WITHOUT the fleet rule | escalation share on corrupted engines |
|---|---|---|---|---|---|---|
| 20% missing values | 1.00 / 1.00 / 1.00 / 1.00 | 0 | 0.04 / 0.03 / 0.00 / 0.03 | 0 | 0 / 0 / 0 / 0 | 1.00 |
| 3σ noise | 0.98 / 1.00 / 1.00 / 1.00 | 0 | 0.10 / 0.05 / 0.20 / 0.01 | 0 | 0.06 / 0 / 0.12 / 0 | 0.66–1.00 |
| regime shift | 1.00 / 1.00 / 1.00 / 1.00 | 0 | 0.00 / 0.00 / 0.00 / 0.08 | 0 | 0 / 0 / 0 / 0 | 1.00 |
| +2σ bias, one sensor | 0.12 / 0.88 / 0.04 / 0.96 | 0 | 0.04 / 0.03 / 0.10 / 0.04 | 0 | 0.04 / 0.03 / 0.10 / 0.03 | 0.32–0.75 |
| +3σ bias, one sensor (secondary) | 0.20 / 0.90 / 0.06 / 0.96 | 0 | 0.06 / 0.03 / 0.10 / 0.05 | 0 | 0.06 / 0.02 / 0.10 / 0.04 | 0.32–0.82 |

Findings:
1. Missing values, noise and a regime shift are detected per engine on 98–100% of corrupted engines with zero additional false alarms on the clean engines (change-relative, per engine). A single biased sensor is a per-engine detection floor on the single-regime subsets (4–20% on FD001/FD003) and is caught on the multi-regime subsets (88–96%); at fleet level the age-matched drift monitor's severe single-feature rule fires on every fault scenario (20/20).
2. The point-threshold agent issues silent wrong orders on 0–20% of corrupted engines (zero in 4 of 20 scenarios; denominators 50–125 engines). The full agent's rate is zero in every scenario, and most of that zero comes from the fleet-level rule: while the fleet alarm is active every HIGH/CRITICAL decision is escalated. Without the fleet rule the per-engine quality and anomaly evidence alone leaves 0–12% silent wrong orders (worst: FD003 under noise 0.12, FD003 under a biased sensor 0.10).
3. The cost of the fleet rule: on the CLEAN engines the escalation share rises from 6–18% (clean run) to 25–36% while the alarm is active; a fleet alarm therefore trades automatic action on a quarter to a third of healthy engines for the guarantee that no serious order goes out silently during a fleet-wide input problem.
4. A fleet-level false alarm: on FD003 the age-matched monitor raises a severe single-feature alarm on the early-life rows of the 50 clean test engines (one fixed engine subset, the same in all five scenarios; s9 rolling mean, PSI 1.5), while the pooled early-life rows of all 100 engines do not alarm. The per-engine false-alarm rate is unaffected, but the fleet rule would have escalated FD003's serious decisions in that fleet state; `fleet_drift_alarm_clean_early` is reported in the table and this is a known limitation (KNOWN_LIMITATIONS 32).

## E4 — Drift-triggered, gated retraining (H4) — **pre-registered criterion NOT SUPPORTED (4/8); reject path demonstrated on label corruption (4/4); drift trigger supported (4/4)**
Per subset: validation 20% of training engines (never trained on), champion 50%, new data 30%; gates RMSE ≤ champion + 2%, PICP ≥ 0.85, late rate (lower-bound policy at the CRITICAL threshold, D22) ≤ champion + 0.02. Every scenario is gated against the same champion and the registry alias is handed back afterwards.

Primary run (5 validation rows per engine, pre-registered scenarios):

| Subset | A: more data (expect PROMOTE) | B: +3σ sensor offset on the new engines (expect REJECT) | drift: false alarms / 20 clean windows | regime-shift alarm | bias alarm |
|---|---|---|---|---|---|
| FD001 | REJECT — RMSE 16.50 → 16.41, PICP 0.950 → 0.780 (`picp < 0.85`) | REJECT — 17.80 (`rmse`), PICP 0.760 | 0 | yes (os1, os2) | yes (s2, s3 and their rolling means) |
| FD002 | PROMOTE — 15.05 → 15.21, PICP 0.904 | PROMOTE — 15.26, PICP 0.904 | 0 | yes | yes |
| FD003 | PROMOTE — 14.39 → 13.68, PICP 0.930 | PROMOTE — 12.98, PICP 0.870 | 0 | yes | yes |
| FD004 | PROMOTE — 19.30 → 18.03, PICP 0.892, late 0.000 → 0.020 | PROMOTE — 18.53, PICP 0.868 | 0 | yes | yes |

Secondary run (post hoc, D21: 20 validation rows per engine; scenario B2 = the new engines arrive with RUL labels 40 cycles too optimistic):

| Subset | A: more data | B: sensor offset | B2: optimistic labels (expect REJECT) |
|---|---|---|---|
| FD001 | REJECT — 15.16 → 14.96, PICP 0.830 (`picp`) | REJECT — 15.69 (`rmse`, `picp` 0.802) | REJECT — 19.90, PICP 0.775 (`rmse`, `picp`) |
| FD002 | PROMOTE — 16.35 → 16.15, PICP 0.906 | REJECT — 16.80 > 16.68 (`rmse`) | REJECT — 20.82 (`rmse`) |
| FD003 | PROMOTE — 14.17 → 13.65, PICP 0.912 | PROMOTE — 13.18, PICP 0.885 | REJECT — 19.33, PICP 0.738, late@10 0.000 → 0.100 (`rmse`, `picp`, `late_rate`) |
| FD004 | PROMOTE — 17.78 → 16.18, PICP 0.853 | PROMOTE — 16.71, PICP 0.857 | REJECT — 20.65, PICP 0.775, late@10 0.000 → 0.160 (`rmse`, `picp`, `late_rate`) |

Findings:
1. Primary run 4/8 as expected: the sensor-offset challenger is no worse on clean validation data on FD002–FD004 (a constant offset with correct labels does not hurt a tree model) and is promoted; FD001's more-data challenger is rejected by the coverage floor (0.780 on 100 rows). Secondary run 9/12: with 20 rows per engine FD002's offset challenger is rejected on RMSE, FD001's more-data challenger still measures 0.830 coverage and is rejected, and the label-corrupted challenger is rejected on all four subsets with 2.9–5.2 RMSE worse than the champion; on FD003 and FD004 the late-rate gate at the CRITICAL threshold fires as well (0.100 and 0.160 against a 0.020 limit), so the decision-metric branch of the gate now contributes to a rejection.
2. The absolute coverage floor is the weak rule: FD001's more-data challenger improved RMSE in both runs and was rejected at 0.780 and 0.830; a floor relative to the champion is the documented improvement (KNOWN_LIMITATIONS 21).
3. Drift trigger: 0 false alarms in 20 age-matched clean windows on every subset; the regime shift is caught through the operating-setting rule and the biased sensors through the severe single-feature rule on every subset. FD001's drift results are the design set (the rules were iterated on FD001's test engines); FD002–FD004 are confirmatory.

## E5 — Decision metrics vs RMSE (H5) — **SUPPORTED as pre-registered, with the sizes stated**
Out-of-fold tables with baselines; evaluation engines; RMSE on 5 random cycles per engine; replay at the HIGH threshold with a 5-cycle lead.

| Subset | naive mean | RandomForest | HGBR all fold engines | HGBR 70% (agent's point model) | same model, lower bound |
|---|---|---|---|---|---|
| FD001 | RMSE 41.86, late 1.00, never orders | 15.25 / late 0 / discarded 25.2 | 14.18 / 0 / 26.2 | 15.04 / 0 / 25.2 | 15.04 / 0 / 40.3 |
| FD002 | 42.01 / 1.00 / — | 16.79 / 0 / 24.3 | 15.97 / 0 / 26.3 | 16.21 / 0 / 26.5 | 16.21 / 0 / 39.2 |
| FD003 | 41.81 / 1.00 / — | 13.67 / 0 / 24.8 | 12.61 / 0 / 25.8 | 13.73 / 0 / 25.7 | 13.73 / 0 / 36.7 |
| FD004 | 42.09 / 1.00 / — | 16.68 / 0.006 / 24.8 | 16.05 / 0.006 / 26.0 | 16.09 / 0.006 / 25.7 | 16.09 / 0 / 38.9 |

Findings: of the 12 ordered pairs of point models, 10 invert on discarded life (the better-RMSE model discards 0.04–2.23 cycles more) and 2 go the other way (FD002 all-engine vs 70% HGBR −0.25; FD003 RandomForest vs 70% HGBR −0.94); late rates are tied at zero except on FD004. The lower-bound row has by construction the RMSE of its point model and discards 11.0–15.0 cycles more, with the only late order on FD004 removed: RMSE cannot see the policy. The naive mean has a finite RMSE and never orders. RMSE orders the point models in the same direction as late rate but not as discarded life; the differences among point models are one to two cycles, which the deck states as such.

## E6 — Auditability (H6) — **SUPPORTED**
3,409 decisions across the four per-subset audit logs (510 / 971 / 897 / 1,031) re-derived from their stored inputs, thresholds and model version with 0 mismatches; every chain valid; a tampered record in each log is detected (chain invalid, 1 re-derivation mismatch); all 205 work-order records (batch + stream replay) carry the model version and severity. Not covered: truncation of a log's tail and a full re-hash by an insider (KNOWN_LIMITATIONS 31).

## E7 — Ablations (one 20%-engine holdout split; official test metrics; `experiments/results/e7_ablation/`)
| Subset | Variant | Test RMSE capped / raw | PICP | MPIW | Holdout late / discarded (point policy) | (lower-bound policy) |
|---|---|---|---|---|---|---|
| FD001 | full | 15.05 / 16.13 | 0.900 | 65.6 | 0.00 / 22.6 | 0.00 / 32.4 |
| FD001 | raw sensors only (no rolling features) | 17.75 / 18.86 | 0.890 | 53.9 | 0.00 / 25.9 | 0.00 / 41.0 |
| FD001 | with EMA 0.3 | 13.68 / 14.72 | 0.930 | 67.5 | 0.00 / 25.3 | 0.00 / 35.6 |
| FD001 | asymmetric CQR | 15.05 / 16.13 | 0.920 | 68.0 | 0.00 / 22.6 | 0.00 / 35.4 |
| FD004 | full | 16.55 / 28.02 | 0.827 | 54.4 | 0.00 / 30.3 | 0.00 / 39.9 |
| FD004 | no regime normalisation | 17.70 / 28.77 | 0.891 | 70.5 | 0.00 / 34.3 | 0.00 / 55.6 |
| FD004 | raw sensors only | 18.24 / 29.04 | 0.879 | 64.6 | 0.00 / 32.9 | 0.00 / 51.1 |
| FD004 | with EMA 0.3 | 23.20 / 33.79 | 0.839 | 77.6 | 0.04 / 31.3 | 0.00 / 58.3 |
| FD004 | asymmetric CQR | 16.55 / 28.02 | 0.887 | 56.8 | 0.00 / 30.3 | 0.00 / 43.8 |

Findings: rolling features are worth 2.7 (FD001) and 1.7 (FD004) RMSE; regime normalisation is worth 1.2 RMSE on FD004 and 16 cycles of discarded life under the lower-bound policy; EMA helps FD001 (−1.4) but costs 6.7 RMSE on FD004, so it stays off; asymmetric CQR leaves the point model unchanged and raises coverage (FD001 0.900 → 0.920, FD004 0.827 → 0.887) for +2.4 cycles of width (kept as an option; the symmetric variant remains the pre-registered default). These variants train on 80% of the engines, so RMSEs are slightly worse than E0. These are official-test comparisons (KNOWN_LIMITATIONS 24). Deviation from the plan: ablation (iii) "anomaly input to the agent" was not run (it cannot change the replay policies, which act on the point estimate or the lower bound only); (iv) is the point-vs-lower-bound column pair.

## Hypothesis scoreboard
H1 NOT SUPPORTED (trade-off reported; tuned thresholds unstable across seeds) · H2 NOT SUPPORTED · H3 SUPPORTED for 3 of 4 faults (single-sensor bias is a detection floor on single-regime subsets; the zero silent-wrong-order rate relies on the fleet rule) · H4 NOT SUPPORTED as pre-registered (reject path demonstrated on label corruption 4/4, late-rate gate contributes on 2/4; drift trigger 4/4) · H5 SUPPORTED (inversions of one to two cycles among point models; the policy is invisible to RMSE) · H6 SUPPORTED · H7 SUPPORTED.
