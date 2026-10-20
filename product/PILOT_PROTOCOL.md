# Pilot protocol: read-only shadow pilot (validation-ladder rung 5)

> **NOT YET FIELD VALIDATED.** This is a protocol for a pilot that has not started. No partner has agreed to it and no field data have been received. Nothing in it is a result.

## 1. Purpose

Find out, on one partner's live turbines and with their people, whether SentinelLoop's recommendations are:
1. **Assessable:** the data support an assessment for most of the hours the turbines operate.
2. **Timely:** they precede the events the partner records.
3. **Bearable:** the alarm burden is acceptable.
4. **Useful:** planners and engineers would act on them.

This happens in **shadow mode**: nothing the system says changes what the partner does. So the pilot cannot show any downtime, cost or availability benefit. That needs a rung-6 trial in which recommendations are acted on, with a baseline agreed beforehand (§8; `PILOT_ACCEPTANCE_CRITERIA.md` §1, §4).

## 2. Preconditions (all required before day 1)

| # | precondition | evidence required |
|---|---|---|
| P1 | G0 passed under the pre-registered rule as amended before any download (`product/evidence/g0/PREREGISTRATION.md` §10.3, Amendment 1, PD-25). Farm A (onshore) is the primary decision. All three must hold: Farm A's CARE score is above the internal power-binned z-threshold baseline; Farm A mean Accuracy is ≥ 0.5; the pooled CARE score is > 0.66. A pooled pass with Farm A at or below the baseline is a fail | the results file (`product/evidence/g0/results.md`) with a pass verdict, Farm A's detection rate with its Wilson interval, and assessability per farm (§10.2) |
| P2 | G1 found a partner meeting all three access conditions (`INITIAL_MARKET_AND_ASSET_CHOICE.md` §7) | a signed data-sharing agreement: purpose, retention, deletion, access, publication |
| P3 | rung 4 back-test on the partner's own history (≥ 3 years of SCADA plus a failure or work-order log), with acceptance thresholds agreed **before** the back-test is run | a back-test report against the criteria in `PILOT_ACCEPTANCE_CRITERIA.md` §2 |
| P4 | the partner's IT/OT security review of the deployment (`THREAT_MODEL.md`, `SECURITY_REVIEW.md`, `DEPLOYMENT_GUIDE.md`); external penetration test if reachable beyond one host | written approval |
| P5 | the partner's change-management and safety sign-off that the pilot is advisory and read-only | written approval naming the partner's pilot owner |
| P6 | named roles: partner pilot owner, reliability engineer, planner(s), technicians' representative; the step-1 judge and the person who draws the step-1 sample (§3, Blinding); SentinelLoop engineer on call | a roster |
| P7 | turbines in scope commissioned on agreed healthy periods, the choice signed by the partner's reliability engineer | the commissioning records (audited) |

## 3. Design

| item | plan |
|---|---|
| Scope | 10–30 turbines of one model and rating (geared ~2.0–2.3 MW), one site or one O&M region. A size giving at least a few expected drivetrain events in the period is preferred; the partner's history will show whether that is realistic |
| Duration | 12 weeks minimum, plus 2 weeks of setup |
| Season | **the pilot plan states the calendar months of the 12 weeks before day 1.** It also states, from the rung-4 back-test on the partner's history (P3), the expected share of operating turbine-hours and of assessable operating hours in those months. The S1 threshold and the stopping rule in §7 are agreed with that stated, before pilot data are seen. Reason: the wind model makes no statement unless the turbine produced power above 5% of rated in at least half of its 9-hour scoring window (`nbm.applicability`), so the calendar share of assessable time follows the wind. W3's calendar share on SYNTHETIC data (0.59 on its fresh fleets, 0.57 on its tuning fleets; `product/evidence/wind_synthetic/w3.md`) does not measure this. On W3's fleets, about 15–25% of scored instants are turbines stopped for the rest of the record after their injected component failure (`synthetic_wind.py`); without them the per-fleet share is about 0.51–0.80 on the tuning fleets and 0.64–0.84 on the fresh fleets (a re-count at the shipped setting, sustain 18 with the 9-hour window, after the gating fixes; not part of `w2.md` or `w3.md`) |
| Mode | CMMS integration in **shadow**. The partner's normal process runs unchanged. SentinelLoop recommendations are visible only to the pilot team in the console |
| Data | daily or more frequent export of 10-minute SCADA averages for the wind type's contract signals (`DATA_CONTRACTS.md` §1), through the ingestion API.<br>• The partner's tags are renamed and converted to the platform's signal names and units before ingestion: there is no per-site tag mapping and no unit conversion (`KNOWN_LIMITATIONS.md` P12).<br>• For a periodic export, the policy file sets `assess_at: latest_reading` for the wind type (the shipped default is `now`), and each export is replayed with `assess-range`, oldest instant first, after the last applied instant (PD-17).<br>• **Turbine status codes, alarm codes and curtailment or derating setpoints are not in the data contract and cannot be ingested** (`KNOWN_LIMITATIONS.md` M3). If the partner supplies them, they are used offline in the weekly reconciliation (§4), not loaded.<br>• The partner's work orders and failure log are exported weekly for comparison |
| Model | the wind NBM trained and thresholded on the partner's own turbines (rung 4), with the shipped persistence (sustain 18 operating points = 3 h of operation, inspect margin 1.25; PD-15, chosen on SYNTHETIC data in W3) unless the back-test changes it under §6. The training period covers the ambient and wind range of the pilot season: the envelope check puts anything outside the training range out of scope (`nbm.applicability`). No thresholds are tuned during the pilot without a documented, dated change (§6) |
| Blinding | two blinded steps (PD-23; `OPERATOR_FEEDBACK_PLAN.md` §2):<br>1. For a random sample of turbine-weeks, the reliability engineer records an independent judgement from the SCADA trends **before** seeing SentinelLoop's state for that turbine. Agreement statistics (for example Cohen's kappa) use only these judgements. How step 1 is kept independent:<br>• someone other than the judge (for example the SentinelLoop engineer) draws the sample from all pilot turbines, with a recorded random seed, before the weekly review, and tells the judge nothing about the sampled turbines' states;<br>• the judge reads the trends in the partner's own SCADA tool or export. The console has no trend view and the API has no readings route (`src/sentinelloop/console/app.py`, `src/sentinelloop/app/api.py`);<br>• the judge has no console access during the pilot, for example a second reliability engineer of the partner, outside the pilot team. If the only judge available is the pilot team's reliability engineer, who sees every state in the console (Mode, above) and reviews every recommendation (step 2), they judge only turbines whose state they have not seen in any earlier week: a latch persists across weeks until it is cleared (PD-16);<br>• each judgement records whether the judge had seen that turbine's SentinelLoop state, or an order for it, before;<br>• the SentinelLoop state each judgement is compared with is fixed in the analysis plan before day 1, for example the most severe state shown for the turbine during that week (replays excluded), together with the mapping from states to the judge's answers.<br>If these conditions cannot all be met, independence is not guaranteed and kappa is reported as indicative only.<br>2. Every recommendation is then reviewed **before** looking at the partner's work-order system for that turbine |

## 4. Weekly cycle

1. **Data.** The ingestion report:
   - rejected rows by reason code, and staleness;
   - whole-feed delays (`data_delivery_delay`: a data-path problem). No instrument-check order is raised while the delay lasts; a turbine with a pending latched inspection still gets its inspection order, unless an open order already stands in for it, and that order counts as an inspection (`decision._planned`; `test_a_latched_inspection_hidden_by_a_data_failure_gets_its_inspection_order`). The first good assessment after it can still raise an instrument-check order, a known gap (`DATA_CONTRACTS.md` §1); such orders are logged as feed-delay recoveries and reported apart from the other instrument checks (`PILOT_ACCEPTANCE_CRITERIA.md` B3, S6);
   - assessability as defined in `PILOT_ACCEPTANCE_CRITERIA.md` S1: the share of **operating** turbine-hours with a valid assessment, with the calendar share beside it. The non-assessable operating hours are split by cause: data-quality failure, out of scope (insufficient operation, operating envelope, no commissioning baseline) and model unavailable.
   - No platform report computes assessability yet. It is computed from the stored assessments and readings by a pilot analysis script (PLANNED).
2. **Review.**
   - First, the step-1 judge records the independent judgements for the week's sampled turbine-weeks, before seeing SentinelLoop's state for them (§3, Blinding, step 1).
   - Then the reliability engineer and planner review every new INSPECTION, URGENT and DATA_QUALITY state and every desk-review order before opening the partner's work-order system for that turbine, and record would-you-inspect, urgency and confidence (step 2).
   - Then they compare each recommendation with the partner's work-order system and failure log, and record whether it was useful and, if not, the reason code (`OPERATOR_FEEDBACK_PLAN.md` §2).
   - The week's system work orders are counted by type (inspection, desk review, instrument check) for `PILOT_ACCEPTANCE_CRITERIA.md` S3, including inspection recommendations that escalated or were absorbed by an open order (note on B3).
3. **Reconciliation.** Match the week's partner work orders and failure-log entries to SentinelLoop states in the preceding weeks: hits, misses, alarms without a matching event. Where the partner supplies status, alarm or curtailment logs, they are compared here, offline, to explain out-of-scope periods and alarms.
4. **Log.** Changes made, issues, and any safety-relevant observation, passed to the partner's own process **immediately**, not at the weekly meeting.

## 5. Safety and ethics rules (non-negotiable)

- SentinelLoop output is **never** the reason to skip, delay or perform a maintenance action during the pilot. The partner's procedures decide.
- If the pilot team sees a recommendation it believes indicates a hazard, it informs the partner's pilot owner at once through the partner's normal channel. It is then the partner's decision.
- No technician is assessed individually from SentinelLoop data. Feedback is about the recommendations, not the people.
- Personal data (technician names in work orders) are pseudonymised in analysis copies. Data are deleted at the end as the agreement states. The platform has no pseudonymisation or deletion tooling yet, and its audit chain records actor names that cannot be redacted (`KNOWN_LIMITATIONS.md` S5). The agreement (P2) must cover this.

## 6. Changes during the pilot

Threshold, policy or model changes are allowed only:
- with a written reason;
- as a dated change in `DECISION_LOG.md`;
- with the before/after reported separately.

The primary analysis uses the configuration frozen at the start.

## 7. Stopping rules

| condition | action |
|---|---|
| a valid assessment on < 50% of **operating** turbine-hours (S1 definition) for 2 consecutive weeks. The 50% is a proposal *(to agree)* with the partner before pilot data are seen, with the season stated (§3) | stop, fix the data path or the model scope, restart the clock |
| partner raises a safety or security concern | pause until resolved |
| alarm burden: for a work-order type with an agreed ceiling (S3, `PILOT_ACCEPTANCE_CRITERIA.md` B3), the lower bound of the exact 95% Poisson interval of its rate per turbine-year, counted from day 1 and checked weekly, is above the ceiling. The window and the trigger are a proposal *(to agree)* before pilot data are seen | stop and review thresholds |

The alarm-burden rule uses the whole pilot so far, because short windows hold few orders. In 3 weeks, 10–30 turbines give only 0.58–1.73 turbine-years, so a 3-week annualised rate above a ceiling of 2 needs only 2–4 orders. In a Poisson simulation (50,000 pilots per case), such a rule, checked weekly, trips at least once in 12 weeks with probability about 0.45–0.48 at a true rate of 1 per turbine-year and 0.84–0.95 at a true rate of 2. The proposed rule trips with probability about 0.05–0.06 at a true rate equal to the ceiling, and 0.53–0.89 at twice it. **When the drifting-sensor turbines are counted as B3 does, W3's held-out synthetic count is about 13 episodes per turbine-year (`PILOT_ACCEPTANCE_CRITERIA.md` B3), so the ceiling of 2 is already exceeded and the proposed rule almost always stops the pilot.** That is an episode count, not an order count. If real turbines behave like that, S3 is likely to fail at the end. Healthy turbines alone give 0.44 episodes per turbine-year (W3, SYNTHETIC; 1 episode in 2.27 turbine-years). If each episode raised one inspection order, the proposed rule would almost never trip at that rate: about 1 in 7,000 12-week pilots of 10 turbines, and fewer for larger pilots (exact probability 0.014% for 10 turbines and 0.001% for 30). These are episode counts, not order counts: one latch can raise an inspection order every 7 days while each is rejected, even after its alarm stops, so the order rate can be higher (`PILOT_ACCEPTANCE_CRITERIA.md` B3, Unit). The episode rate rests on one episode: at the upper end of its 95% interval (about 2.45) the rule stops the pilot early in about 12–21% of such pilots. It is also sensitive to persistence: an earlier run's setting (sustain 6) gave 5.74 on its held-out fleets (`w2.md`).

The assessability rule is measured against operating hours, so idle hours in a low-wind season do not count against it. Intermittent operation still can: the model needs power above 5% of rated in at least half of its 9-hour scoring window (`nbm.applicability`; window 36 + sustain 18 ten-minute points). That is why the season and its expected share are declared before day 1.

## 8. Outputs

- Weekly logs.
- A final report against `PILOT_ACCEPTANCE_CRITERIA.md`.
- An updated `CLAIM_EVIDENCE_MATRIX.md`: rows move to rung 5 only with this evidence.
- A go/no-go recommendation for a rung-6 trial with defined actions.
