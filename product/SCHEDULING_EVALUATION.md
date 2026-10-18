# Scheduling evaluation (Phase 4)

**Status: SIMULATED evidence only.** Every number below comes from a fleet simulator driven by out-of-fold predictions on NASA C-MAPSS engines (simulated turbofans). The costs are relative units chosen by us, not customer figures. Nothing here is a measured saving, and nothing here has been checked against a real maintenance organisation.

Written 2026-10-18. Code: `src/sentinelloop/app/scheduler.py` (scheduler and validator) and `src/sentinelloop/app/sim.py` (simulator). Experiments: `product/experiments/s1*.py`. Raw results: `product/evidence/scheduling/`.

## 1. Summary

1. **No policy wins everywhere.** The ranking depends on four things a customer must supply or that change over time:
   - whether trigger parameters are tuned to the site;
   - how much an hour of downtime costs;
   - whether labour or parts are scarce;
   - whether the prediction intervals stay calibrated.
2. **Run-to-failure and fixed-interval lose clearly in every scenario.**
   - Fixed-interval costs 54 to 139 units more than the tuned threshold rule on 8 of 8 seeds in every scenario (S1c).
   - Run-to-failure wins only when failures are cheap (failure cost × 0.25 in the cost sweep).
3. **A tuned threshold on the model's point RUL is the strongest simple rule.**
   - The untuned S1 comparison (threshold 60 h) favoured RISK_GREEDY by 5 to 132 units (paired means per scenario).
   - Once each family is tuned on separate seeds, the threshold rule matches or beats every risk-based policy in 5 of 6 scenarios (S1d).
   - Most of the earlier advantage was a tuning artefact.
4. **The probabilistic trigger on its own adds nothing in this simulation.**
   - With the same scheduler, it is never better on more than 2 of 8 seeds.
   - It is +50 units worse when the intervals are wider and optimistically biased (S1e).
   - It depends on calibrated intervals, which the threshold rule does not need.
5. **Queue ranking matters more than the trigger, but only because downtime is unpriced.**
   - Under scarce labour, ranking imminent preventive repairs above restoring already-failed assets saves 34 units (8/8 seeds).
   - That is only right because the S1 cost counts failures and repairs but not how long a failed asset stays down.
6. **The MILP is optimal for its own model, not for the plant.**
   - All 5,760 planning windows checked were solved to optimality within a relative gap of 1e-4. The exact technician-assignment step afterwards dropped 3 jobs in total.
   - The MILP restores failed assets much sooner when labour or parts are short. Compared with RISK_GREEDY, unplanned downtime is 29 to 35% lower under tight labour, 56 to 61% lower under parts shortage and 58 to 59% lower under adverse conditions (S1).
   - It therefore loses on the downtime-blind S1 cost and wins once an hour of downtime is worth more than about 0.003 to 0.005 cost units.
7. **No schedule here is claimed optimal for any real site.** "Optimal" applies only to the MILP's 72-hour, aggregated-capacity model within its reported gap.

**Product consequences** (recorded as PD-06 to PD-08 in `DECISION_LOG.md`):
- The default trigger is a **threshold on predicted RUL, tuned per site on held-out history**.
- The default queue is `risk_greedy` for crews that are actually constrained.
- The MILP is offered as a what-if planner once the site has priced downtime.
- Criticality-first ordering is **not** recommended under scarcity: +63 to +83 units in the parts-shortage and adverse scenarios.
- A site's downtime cost per hour is a required configuration input, not an optional one.

**For the chosen vertical (wind, Phase 1):** the approved wind model is an anomaly model with no RUL. The trigger comparison therefore does not transfer directly; wind assessments produce inspections and urgent reviews with policy default due dates. What does transfer:
- the scheduler's behaviour under scarcity;
- the lesson that downtime must be priced. For a wind owner, downtime is lost generation and plainly not zero.

## 2. The scheduling problem as implemented

**Decision.** Which approved work orders start when, and with which technicians, over a rolling 72-hour horizon in 1-hour slots. The first 24 hours are committed; the remainder is re-planned daily.

**Hard constraints.** `scheduler.validate()` checks every schedule independently of the policy that produced it.
- A job needs `crew` technicians who hold its skill, are on shift and are free for every slot it occupies. A crew stays within one shift.
- A job starts and ends inside one maintenance window of its asset. A failed asset is available at any time.
- Only one job runs per asset at a time.
- Parts are used only once they are on hand: initial stock plus known deliveries. A part can be ordered only if it is marked orderable, and then arrives after its lead time.
- A job cannot start before its release time (approval delay).
- Frozen assignments (work already scheduled or in progress) are respected.

**Objective.** This is shared by every policy, so they can be compared. It is the expected loss of each job's start time:
- For a job with a prediction interval: failure cost × P(failure before the job ends).
- For a job without one: failure cost × floor[class] × hours to the job's end / horizon, where floor = {P1: 0.5, P2: 0.1, P3: 0.02}. This is a declared surrogate.
- For work left unscheduled: 1.5 × failure cost × max(P, floor).
- Optional stability term: a penalty proportional to floor × cost for moving a job that was in the previous plan.

**Policies.**

| policy | trigger | scheduler |
|---|---|---|
| RUN_TO_FAILURE | none (corrective only) | EDD |
| FIXED_INTERVAL | repair at a fixed age | EDD |
| THRESHOLD_EDD (the fixed-threshold baseline) | repair when point RUL ≤ threshold | EDD |
| RISK_CRITICALITY_FIRST (the criticality-first baseline) | P(failure before horizon) ≥ p_inspect → inspect, ≥ p_urgent → repair (P1) | criticality A > B > C, then class, then due date |
| RISK_GREEDY / _STABLE | risk trigger | class, then expected loss avoided per crew-hour |
| RISK_MILP / _STABLE | risk trigger | time-indexed MILP (HiGHS via `scipy.optimize.milp`), then exact technician assignment |
| RISK_EDD, THRESHOLD_CRITICALITY_FIRST, THRESHOLD_MILP, THRESHOLD_GREEDY | the factorial cells (S1e) | as named |

## 3. Simulator and its assumptions

`sim.py`, every run:
- **Fleet.** 30 assets for 120 days, 3 h per C-MAPSS cycle (an assumption). Criticality mix 20/50/30% for A/B/C.
- **Resources.** Daily maintenance window 20:00–06:00. Four mechanics on two overlapping shifts. Eight repair kits with one-for-one reorder and a 72-hour lead time.
- **Jobs.** Inspection 2 h, one technician. Repair 8 h, two technicians. Corrective work starts 24 h after a failure.
- **Predictions.** Each asset runs through real out-of-fold predictions (FD001 + FD003, 200 engines) from the competition model, which never saw that engine. True failure is the engine's recorded end of life.
- **Inspection.** Assumed **perfect**: it finds degradation exactly when true RUL ≤ 40 cycles. This is optimistic for every policy that inspects.
- **Costs.** Failure: A 10, B 4, C 1.5. Planned repair 1. Inspection 0.1. **Downtime duration is not priced in "total cost"**; it is reported separately as unplanned downtime hours.
- **Fairness.** All policies see the same fleet, trajectory order, starting ages and resources for a given seed and scenario.

| scenario | change from base |
|---|---|
| tight_labour | 3 mechanics instead of 4 |
| parts_shortage | 2 kits, 168 h lead time |
| degraded_predictions | intervals 1.5× wider, all bounds 30 h optimistic |
| approval_delay | every job released 24 h after creation |
| adverse | tight labour + 3 kits at 168 h + degraded predictions + 12 h approval delay |

**Disclosed design history.** After early runs, the base scenario's kit stock was raised to 8 because the first base setting was structurally short of kits. That was a scenario-design choice made after seeing results. The original shortage survives as the `parts_shortage` scenario.

## 4. Results

### 4.1 S1: hand-set parameters (threshold 60 h, interval 140 cycles, p_inspect/p_urgent 0.10/0.30)

384 runs: 8 policies × 6 scenarios × 8 seeds, 7.4 min. Full tables are in `evidence/scheduling/summary.md`. Mean total cost ± sd:

| scenario | RTF | FIXED_INT | THRESHOLD_EDD | RISK_CRIT_FIRST | RISK_GREEDY | RISK_MILP | RISK_MILP_STABLE |
|---|---|---|---|---|---|---|---|
| base | 444.3 ± 64.6 | 214.9 ± 10.0 | 150.8 ± 8.2 | 145.0 ± 7.0 | **139.7 ± 5.2** | 144.3 ± 7.1 | 142.3 ± 5.5 |
| tight_labour | 419.0 | 319.8 | 197.7 | 164.3 | **158.2** | 182.2 | 175.2 |
| parts_shortage | 210.6 | 202.4 | 169.7 | 197.8 | 165.1 | 203.8 | 202.6 |
| degraded_predictions | 444.3 | 214.9 | 307.1 | 179.7 | 175.2 | 189.2 | 185.6 |
| approval_delay | 444.3 | 227.9 | 279.6 | 159.0 | **156.9** | 168.1 | 168.4 |
| adverse | 260.7 | 243.9 | 213.6 | 222.4 | **180.2** | 227.3 | 227.0 |

Sanity checks:
- Policies that do not use predictions (RTF, FIXED_INTERVAL) give identical results in `base` and `degraded_predictions`, as they should.
- Schedule violations found by the independent validator: 0 in 384 runs.

**This table must not be read as "risk-based scheduling wins".** S1c and S1d below show that the threshold baseline was under-tuned.

### 4.2 S1b: MILP optimality status and the assignment relaxation

Seeds 0–3, both MILP policies, all scenarios; 5,760 planning windows (`evidence/scheduling/milp_assignment_check.md`):
- non-optimal solves: 0;
- jobs placed by the aggregated model that no specific crew could staff: 3 in total (2 under approval delay, 1 under degraded predictions);
- mean MILP run: 21 s for 120 days with a 10 s per-window limit, against about 1.3 s for the greedy schedulers.

### 4.3 S1c and S1d: tuned baselines and robustness

Each family's parameter was tuned on seeds 100–107 and evaluated on seeds 0–7 (`evidence/scheduling/robust_tuning.md`). The grids were:
- threshold 60–300 h;
- interval 80–130 cycles;
- risk decision horizon {60, 100, 150} h × (p_inspect, p_urgent) {(0.01, 0.05), (0.03, 0.15), (0.05, 0.2), (0.1, 0.3)}.

**Tuned once in `base`, then deployed under the shifted condition.** This is the realistic case: a site tunes on its normal operation. Mean total cost on the evaluation seeds:

| scenario | THRESHOLD_EDD | FIXED_INTERVAL | RISK_GREEDY | best | RISK_GREEDY − THRESHOLD, paired |
|---|---|---|---|---|---|
| base | 138.2 | 210.9 | 138.3 | tie | +0.0 [−5.9, +4.7], better 3/8 |
| tight_labour | 165.8 | 312.1 | 153.5 | RISK_GREEDY | **−12.3 [−25.3, −2.5], better 8/8** |
| parts_shortage | 158.0 | 201.4 | 162.6 | THRESHOLD | +4.5 [−3.6, +26.2], better 3/8 |
| degraded_predictions | 140.3 | 210.9 | 166.6 | THRESHOLD | **+26.3 [+16.1, +43.0], worse 8/8** |
| approval_delay | 148.0 | 212.7 | 148.9 | tie | +1.0 [−17.5, +18.2], better 4/8 |
| adverse | 175.4 | 240.9 | 172.2 | RISK_GREEDY_STABLE (171.7) | −3.2 [−13.4, +7.5], better 5/8 |

**Tuned within each scenario:** the tuned threshold rule is cheapest in 5 of 6 scenarios. RISK_GREEDY is cheapest only under tight labour, by −5.6 units, better on 6 of 8 seeds.

**Grid edges** (the optimum may lie outside the grid):
- The threshold reached 300 h in `parts_shortage` and `adverse`. This can only make the threshold rule look better still.
- The fixed interval reached its edge in several scenarios. It is 54+ units behind everywhere, so this does not change any conclusion.

### 4.4 S1e: trigger × scheduler factorial (base-tuned settings)

Threshold 100 h; risk decision horizon 60 h with p_inspect/p_urgent 0.05/0.2 (`evidence/scheduling/factorial.md`). Mean total cost:

| scenario | THR_EDD | THR_CRIT_FIRST | THR_MILP | THR_GREEDY | RISK_EDD | RISK_GREEDY | RISK_MILP |
|---|---|---|---|---|---|---|---|
| base | 138.2 | 139.2 | 137.7 | 138.2 | 141.0 | 138.3 | 142.0 |
| tight_labour | 165.8 | 170.5 | 163.8 | 339.5 | 187.9 | **153.5** | 180.9 |
| parts_shortage | **158.0** | 220.9 | 200.7 | 208.4 | 164.6 | 162.6 | 206.7 |
| degraded_predictions | 140.3 | **137.1** | 145.6 | 141.8 | 190.0 | 166.6 | 183.7 |
| approval_delay | **148.0** | 149.5 | 153.8 | 148.9 | 163.5 | 148.9 | 162.8 |
| adverse | 175.4 | 258.8 | 224.2 | 255.6 | 188.6 | **172.2** | 213.3 |

Paired effects (seeds better out of 8):
- **Trigger** (RISK_EDD − THRESHOLD_EDD): worse or equal everywhere. +2.8 (0/8) in base, +49.7 (0/8) with degraded predictions, +15.5 (0/8) with approval delay.
- **Risk-ranked queue given the risk trigger** (RISK_GREEDY − RISK_EDD): better everywhere. −34.4 (8/8) tight labour, −23.4 (8/8) degraded predictions, −14.5 (8/8) approval delay, −16.4 (7/8) adverse.
- **Criticality-first given the threshold trigger:** +62.9 (0/8) under parts shortage and +83.3 (0/8) under adverse conditions.
- **MILP given either trigger:** +42 to +49 (0/8) under parts shortage and adverse conditions; about neutral elsewhere.
- **THRESHOLD_GREEDY** collapses under tight labour (+173.8, 0/8 better).
  - Mechanism: `risk_greedy` ranks priority class first. Threshold repairs are P2, so they always queue behind corrective work (P1) on already-failed assets.
  - With scarce crews, preventive work starves and failures cascade.
  - RISK_GREEDY escapes this only because its urgent repairs are P1 and, carrying a score, outrank corrective jobs. Corrective jobs carry no score.
  - The S1 cost rewards this ordering because it does not price downtime.

### 4.5 Cost sensitivity

**Failure, inspection and repair costs** (`evidence/scheduling/sensitivity.csv`). The same simulated decisions are re-priced, not re-optimised, over 45 settings: failure × {0.25, 0.5, 1, 2, 4}, inspection {0.05, 0.1, 0.3}, repair {0.5, 1, 2}.

| base: cheapest policy by failure-cost multiplier | ×0.25 | ×0.5 | ×1 | ×2 | ×4 |
|---|---|---|---|---|---|
| RUN_TO_FAILURE | 6 | 3 | 0 | 0 | 0 |
| THRESHOLD_EDD (untuned, 60 h) | 3 | 3 | 1 | 0 | 0 |
| RISK_CRITICALITY_FIRST | 0 | 1 | 2 | 0 | 0 |
| RISK_GREEDY | 0 | 2 | 6 | 9 | 9 |

With degraded predictions and expensive failures (×4), FIXED_INTERVAL is cheapest in 6 of 9 settings. When predictions go wrong and failures are expensive, a schedule that ignores the predictions is the safer default.

**Downtime price** (`evidence/scheduling/downtime_sensitivity.md`). The S1 runs are re-priced at d cost units per unplanned downtime hour; for scale, one A failure costs 10.

| scenario | d = 0 | 0.002 | 0.005 | 0.01 | 0.02 |
|---|---|---|---|---|---|
| base | RISK_GREEDY | RISK_GREEDY | RISK_GREEDY | RISK_GREEDY | RISK_GREEDY |
| tight_labour | RISK_GREEDY | RISK_GREEDY | RISK_GREEDY | RISK_MILP | RISK_MILP |
| parts_shortage | RISK_GREEDY_STABLE | RISK_GREEDY_STABLE | RISK_MILP | RISK_MILP | RISK_MILP |
| adverse | RISK_GREEDY | RISK_GREEDY | RISK_MILP_STABLE | RISK_MILP_STABLE | RISK_MILP_STABLE |

Break-even prices at which RISK_MILP_STABLE becomes cheaper than RISK_GREEDY:

| scenario | break-even d per hour | downtime hours saved by the MILP |
|---|---|---|
| adverse | 0.0026 | 17,698 |
| parts_shortage | 0.0026 | 14,569 |
| tight_labour | 0.0054 | 3,146 |

In the base, approval-delay and degraded-prediction scenarios the MILP never wins, because it does not reduce downtime there.

## 5. What this evaluation does not establish

- Anything about a real site. Fleet, costs, crews, windows, perfect inspection and replenishment are assumptions.
- Optimality of any schedule for a plant. The MILP is optimal only for its own model within its gap, and its objective differs from the evaluation metric: the objective values restoring failed assets through the P1 floor, while S1 total cost ignores downtime.
- The value of risk-based triggering for wind turbines. The wind model gives no RUL.
- Statistical significance beyond the stated seed-level paired counts. With 8 seeds, a "7/8 better" result is suggestive, not conclusive.
- Human behaviour: approval latency beyond the fixed delays, overrides, and trust in the recommendations.

## 6. Reproduce

```bash
.venv/Scripts/python.exe product/experiments/s1_scheduling.py --seeds 8 --days 120
```
```bash
.venv/Scripts/python.exe product/experiments/s1_downtime_sensitivity.py
```
```bash
.venv/Scripts/python.exe product/experiments/s1b_milp_assignment_check.py
```
```bash
.venv/Scripts/python.exe product/experiments/s1c_tuned_baselines.py
```
```bash
.venv/Scripts/python.exe product/experiments/s1d_robust_tuning.py
```
```bash
.venv/Scripts/python.exe product/experiments/s1e_factorial.py
```

The runs are deterministic given the seeds. Wall-clock times (on this laptop): S1 7.4 min; S1d about 6 min; S1e about 5 min (the MILP dominates). The scheduler and simulator tests are `tests/test_app_scheduler.py` (23) and `tests/test_app_sim.py` (11).
