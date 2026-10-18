# Pilot protocol: read-only shadow pilot (validation-ladder rung 5)

> **NOT YET FIELD VALIDATED.** This is a protocol for a pilot that has not started. No partner has agreed to it and no field data have been received. Nothing in it is a result.

## 1. Purpose

Find out, on one partner's live turbines and with their people, whether SentinelLoop's recommendations are:
1. **Assessable:** the data support an assessment most of the time.
2. **Timely:** they precede the events the partner records.
3. **Bearable:** the alarm burden is acceptable.
4. **Useful:** planners and engineers would act on them.

This happens in **shadow mode**: nothing the system says changes what the partner does.

## 2. Preconditions (all required before day 1)

| # | precondition | evidence required |
|---|---|---|
| P1 | G0 passed: the pre-registered public-data test (`product/evidence/g0/PREREGISTRATION.md`) | the results file with a pass verdict |
| P2 | G1 found a partner meeting all three access conditions (`INITIAL_MARKET_AND_ASSET_CHOICE.md` §7) | a signed data-sharing agreement: purpose, retention, deletion, access, publication |
| P3 | rung 4 back-test on the partner's own history (≥ 3 years of SCADA plus a failure or work-order log), with acceptance thresholds agreed **before** the back-test is run | a back-test report against the criteria in `PILOT_ACCEPTANCE_CRITERIA.md` §2 |
| P4 | the partner's IT/OT security review of the deployment (`THREAT_MODEL.md`, `SECURITY_REVIEW.md`, `DEPLOYMENT_GUIDE.md`); external penetration test if reachable beyond one host | written approval |
| P5 | the partner's change-management and safety sign-off that the pilot is advisory and read-only | written approval naming the partner's pilot owner |
| P6 | named roles: partner pilot owner, reliability engineer, planner(s), technicians' representative; SentinelLoop engineer on call | a roster |
| P7 | turbines in scope commissioned on agreed healthy periods, the choice signed by the partner's reliability engineer | the commissioning records (audited) |

## 3. Design

| item | plan |
|---|---|
| Scope | 10–30 turbines of one model and rating (geared ~2.0–2.3 MW), one site or one O&M region. A size giving at least a few expected drivetrain events in the period is preferred; the partner's history will show whether that is realistic |
| Duration | 12 weeks minimum, plus 2 weeks of setup |
| Mode | CMMS integration in **shadow**. The partner's normal process runs unchanged. SentinelLoop recommendations are visible only to the pilot team in the console |
| Data | daily or more frequent SCADA export (10-minute averages, status codes, alarms) through the ingestion API; the partner's work orders and failure log exported weekly for comparison |
| Model | the wind NBM trained and thresholded on the partner's own turbines (rung 4); no thresholds tuned during the pilot without a documented, dated change (§6) |
| Blinding | the reliability engineer reviews each recommendation **before** looking at the partner's work-order system for that turbine, and records an independent judgement (`OPERATOR_FEEDBACK_PLAN.md`) |

## 4. Weekly cycle

1. **Data.** The ingestion report: rejected rows by reason code, staleness, share of turbine-hours assessable.
2. **Review.** The reliability engineer and planner review every new INSPECTION, URGENT and DATA_QUALITY state and record feedback per recommendation (useful, not useful, reason code).
3. **Reconciliation.** Match the week's partner work orders and failure-log entries to SentinelLoop states in the preceding weeks: hits, misses, alarms without a matching event.
4. **Log.** Changes made, issues, and any safety-relevant observation, passed to the partner's own process **immediately**, not at the weekly meeting.

## 5. Safety and ethics rules (non-negotiable)

- SentinelLoop output is **never** the reason to skip, delay or perform a maintenance action during the pilot. The partner's procedures decide.
- If the pilot team sees a recommendation it believes indicates a hazard, it informs the partner's pilot owner at once through the partner's normal channel. It is then the partner's decision.
- No technician is assessed individually from SentinelLoop data. Feedback is about the recommendations, not the people.
- Personal data (technician names in work orders) are pseudonymised in analysis copies. Data are deleted at the end as the agreement states.

## 6. Changes during the pilot

Threshold, policy or model changes are allowed only:
- with a written reason;
- as a dated change in `DECISION_LOG.md`;
- with the before/after reported separately.

The primary analysis uses the configuration frozen at the start.

## 7. Stopping rules

| condition | action |
|---|---|
| data assessable on < 50% of turbine-hours for 2 consecutive weeks | stop, fix the data path, restart the clock |
| partner raises a safety or security concern | pause until resolved |
| alarm burden exceeds the agreed ceiling (`PILOT_ACCEPTANCE_CRITERIA.md`) for 3 consecutive weeks | stop and review thresholds |

## 8. Outputs

- Weekly logs.
- A final report against `PILOT_ACCEPTANCE_CRITERIA.md`.
- An updated `CLAIM_EVIDENCE_MATRIX.md`: rows move to rung 5 only with this evidence.
- A go/no-go recommendation for a rung-6 trial with defined actions.
