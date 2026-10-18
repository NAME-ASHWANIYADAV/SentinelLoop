# Pilot acceptance criteria

> **NOT YET FIELD VALIDATED.** These are proposed criteria. Every number marked *(to agree)* is a starting proposal, to be fixed with the partner **before** the back-test or pilot data are seen. They are recorded in writing with the date. Criteria agreed after seeing results do not count.

## 1. Principles

- **Fixed in advance.** Criteria are set before the evidence is seen.
- **Several criteria, all of which must pass.** A pass on detection with an unbearable alarm burden is a fail.
- **Small numbers stay uncertain.** Event counts in a 12-week pilot will be small. Every rate is reported with a Wilson 95% interval, and no precision claim is made from a handful of events.
- **Business value is not a criterion here.** Rung 5 cannot show savings. Savings belong to a rung-6 trial with a pre-agreed baseline.

## 2. Rung 4: back-test on the partner's history (gate before the pilot)

| # | criterion | proposal |
|---|---|---|
| B1 | Assessability: share of turbine-hours in scope with a valid assessment (not data failure, not out of scope) | ≥ 70% *(to agree)* |
| B2 | Detection: share of logged drivetrain failures with a sustained alarm 2 to 60 days before the failure date | ≥ 50%, with the Wilson interval reported *(to agree)* |
| B3 | Alarm burden: sustained-alarm episodes per turbine-year on turbines with no logged drivetrain event in the following 60 days | ≤ 2 *(to agree)* |
| B4 | Leakage control: training, threshold and evaluation periods disjoint in time for every turbine; the protocol pre-registered | yes |
| B5 | Comparison: the same metrics for the partner's existing alarms or CMS (if any) over the same period | reported; SentinelLoop must add detection or reduce burden *(to agree)* |

## 3. Rung 5: shadow pilot

| # | criterion | proposal | measured by |
|---|---|---|---|
| S1 | Assessability (as B1) during the pilot | ≥ 70% *(to agree)* | assessment records |
| S2 | Data-path reliability: days with the export received and ingested by the agreed time | ≥ 95% | ingestion batches, staleness reports |
| S3 | Alarm burden (as B3), live | ≤ the agreed ceiling | states |
| S4 | Usefulness: share of recommendations rated "useful" or "would act" by the reliability engineer (blind judgement first, `OPERATOR_FEEDBACK_PLAN.md`) | ≥ 50% *(to agree)* | feedback records |
| S5 | Timeliness: for every logged drivetrain event in the period, the lead time of the first preceding sustained alarm, or "missed" | reported for every event; no pass/fail on fewer than 5 events | reconciliation |
| S6 | Data-quality signal is real: share of DATA_QUALITY_FAILURE states confirmed as instrumentation or data problems on follow-up | ≥ 70% *(to agree)* | follow-up records |
| S7 | Operational: API and console availability during the partner's working hours; no data loss; audit chain valid at every weekly check | ≥ 99% *(to agree)*; zero loss; valid | `/ready` probes, backups, `verify-audit` |
| S8 | Safety: no instance in which SentinelLoop output was used to decide a maintenance action during the pilot (shadow rule) | zero | pilot log |
| S9 | Operator effort: median time for the weekly review | ≤ 60 min *(to agree)* | feedback plan |

## 4. Decision after the pilot

| outcome | consequence |
|---|---|
| all criteria pass | propose a rung-6 trial with defined actions, a pre-agreed baseline (e.g. matched turbines or a prior period) and a measurement plan for downtime and cost |
| B2 or S5 shows misses that matter, or S3/S4 fail | no rung-6 trial; publish the failure analysis; revisit the model or the vertical (`INITIAL_MARKET_AND_ASSET_CHOICE.md` §10) |
| S2 or S7 fails | fix the operational path and repeat the pilot |
