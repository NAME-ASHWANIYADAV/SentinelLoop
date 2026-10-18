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
| B1 | Assessability: share of **operating** turbine-hours with a valid assessment (no data-quality failure, not out of scope, model available). An operating hour is one in which the turbine produced power above 5% of rated, the model's own definition (`nbm.OP_FRAC`), taken from the active-power readings. Also reported, without pass/fail:<br>• the calendar share (all turbine-hours), the unit W2 reports;<br>• the non-assessable operating hours by cause: data-quality failure, out of scope (by reason), model unavailable;<br>• the share per calendar month, so that the pilot plan can state the expected share for its season (`PILOT_PROTOCOL.md` §3);<br>• the share over curtailment-free operating hours, only if the partner supplies a curtailment log. Curtailment is not in the data contract (`KNOWN_LIMITATIONS.md` M3) | ≥ 70% of operating turbine-hours *(to agree)*. This is a starting proposal with no evidence behind it: no data set has measured the operating-hours share. W2 measured only the calendar share: 0.54–0.59 on SYNTHETIC data (`product/evidence/wind_synthetic/w2.md`), and about 15–22% of its instants are turbines stopped after their injected failure (`PILOT_PROTOCOL.md` §3) |
| B2 | Detection: share of logged drivetrain failures with a sustained alarm 2 to 60 days before the failure date | ≥ 50%, with the Wilson interval reported *(to agree)* |
| B3 | Alarm burden: **system work orders raised per turbine-year, by type** (note below):<br>• **inspection** (`inspect`, P1 or P2) on turbines with no logged drivetrain event in the following 60 days;<br>• **desk review** (`desk_review`: a criticality-A turbine out of scope or without a usable model);<br>• **instrument check** (`instrument_check`: a data-quality failure). A feed delay raises none while it lasts, but its recovery can (known gap, S6); those orders are counted separately.<br>Also reported in technician-hours per site per month (orders × job duration × crew size), in case the partner prefers to set its ceilings in that unit | inspection ≤ 2 per turbine-year *(to agree)*. **Synthetic evidence is already above this ceiling** (note below). Desk review and instrument check: ceilings *(to agree)*; there is no evidence-based proposal, because W2 does not count them |
| B4 | Leakage control: training, threshold and evaluation periods disjoint in time for every turbine; the protocol pre-registered | yes |
| B5 | Comparison: the same metrics for the partner's existing alarms or CMS (if any) over the same period | reported; SentinelLoop must add detection or reduce burden *(to agree)* |

**Note on B3: unit and evidence.**
- **Unit.** W2 counts healthy alarm episodes per turbine-year: an episode is a run of consecutive sustained exceedances (`nbm._episodes`). The platform raises orders per latch, not per episode.
  - The first sustained alarm latches the turbine at INSPECTION_RECOMMENDED until a qualifying inspection is completed or the latch is dismissed (PD-16, `states.advance`). Later episodes during the latch do not start a new one.
  - While an order of any type is open on the turbine, a new recommendation escalates it in place or is absorbed by it (`decision._generate_one`).
  - New orders for the same latch come in three cases (PD-16, PD-18):
    - a separate, higher-priority order when the condition becomes more urgent during lower-priority work in progress;
    - a new order after a rejection, once its suppression period ends (168 h for P2), or at once if the turbine's state has changed, because the suppression holds only for the same state (`decision._suppressed_by_rejection`). A rejected inspection on a turbine that then goes out of scope, with the inspection still pending, is re-raised at the next decision run after a new assessment (reproduced on a test asset; no test covers it);
    - a new order at the next assessment after a completion that does not clear the latch (`not_inspected` or `other`, an `instrument_check` or `desk_review`, or an order raised before the latch began).
  - The last two happen whether or not the alarm persists.
  - So one latch can raise an inspection order every 7 days while each one is rejected, even after its alarm has stopped, and several episodes can share one order. Inspection orders per turbine-year are compared with W2's episodes per turbine-year only as an approximation.
- **Counting.** Orders are counted by `job_type`, but an inspection recommendation can escalate an open order of another type, which keeps its `job_type`; the escalation shows as a `reprioritise` event whose reason ends `recommended job inspect` (`GET /api/v1/work-orders/{id}/history`). A recommendation absorbed by an open order (`open order covers it`) leaves no work-order record. Inspection recommendations are therefore counted from `job_type` plus those events, and cross-checked against the stored assessments (INSPECTION_RECOMMENDED, URGENT_REVIEW).
- **Evidence (SYNTHETIC).** On W2's held-out synthetic fleets, the shipped setting (margin 1.25, sustain 12; PD-15) gives **2.65 healthy alarm episodes per turbine-year**: 6 in 2.27 turbine-years, with a Poisson 95% interval of about 1.0–5.8 (`product/evidence/wind_synthetic/w2.md`, `KNOWN_LIMITATIONS.md` E7).
  - That is above the proposed inspection ceiling of 2, on idealised data.
  - Drifting temperature sensors also raise inspection orders, not instrument checks. They added 37 alarm episodes from 6 drifting sensors on the same fleets (`KNOWN_LIMITATIONS.md` M1), and they count here whenever no drivetrain event follows.
  - **Under B3's own definition (every turbine without a drivetrain event), the held-out synthetic count is therefore (6 + 37) episodes in about 3.0 turbine-years (2.27 + 6 × 0.126), about 14 per turbine-year.** That is an episode count, not an order count (Unit, above). It depends on the synthetic fleet having one drifting sensor per 10 turbines (`product/experiments/w2_threshold_revisit.py`).
  - The real-data rate is unknown until G0 reports the product alarm count on normal datasets.
- **The ceiling of 2 may be too high.** A reviewer role-playing the head of O&M of a 200-turbine fleet judged it far too high: about 400 inspections a year (`ADVERSARIAL_REVIEW.md` om_manager-12). The ceiling is the partner's decision, made before the back-test.

## 3. Rung 5: shadow pilot

| # | criterion | proposal | measured by |
|---|---|---|---|
| S1 | Assessability (as B1, over operating turbine-hours) during the pilot, for the season stated in the pilot plan (`PILOT_PROTOCOL.md` §3) | ≥ 70% *(to agree)*, set with the back-test's share for that season in view | assessment records and active-power readings, by a pilot analysis script (PLANNED) |
| S2 | Data-path reliability: days with the export received and ingested by the agreed time | ≥ 95% | ingestion batches, staleness reports, `data_delivery_delay` assessments |
| S3 | Alarm burden (as B3, by work-order type), live | ≤ the agreed ceilings | system work orders by `job_type` (`GET /api/v1/export/work-orders.csv`: `origin`, `job_type`, `created_at`), plus inspection escalations of open orders of another type (`GET /api/v1/work-orders/{id}/history`) and the stored assessments (note on B3) |
| S4 | Usefulness: share of recommendations rated "useful" or "would act" by the reliability engineer (blind judgement first, `OPERATOR_FEEDBACK_PLAN.md`) | ≥ 50% *(to agree)* | feedback records |
| S5 | Timeliness: for every logged drivetrain event in the period, the lead time of the first preceding sustained alarm, or "missed" | reported for every event; no pass/fail on fewer than 5 events | reconciliation |
| S6 | Data-quality signal is real: share of instrument-check orders (from DATA_QUALITY_FAILURE states) confirmed as instrumentation or data problems on follow-up. Feed delays (`data_delivery_delay`) raise no order while they last and count under S2. **Known gap:** the first good assessment after a feed delay can still raise an instrument-check order (`DATA_CONTRACTS.md` §1). Such an order's explanation carries no data-quality reason code, and the asset's preceding applied assessments show `data_delivery_delay`. These orders are excluded from S6 and reported separately | ≥ 70% *(to agree)* | follow-up records; order explanations and assessment history |
| S7 | Operational: API and console availability during the partner's working hours; no data loss; audit chain valid at every weekly check | ≥ 99% *(to agree)*; zero loss; valid | `/ready` probes, backups, `admin verify-audit` against an anchor kept off the host (PD-22) |
| S8 | Safety: no instance in which SentinelLoop output was used to decide a maintenance action during the pilot (shadow rule) | zero | pilot log |
| S9 | Operator effort: median time for the weekly review | ≤ 60 min *(to agree)* | feedback plan |

## 4. Decision after the pilot

| outcome | consequence |
|---|---|
| all criteria pass | propose a rung-6 trial with defined actions, a pre-agreed baseline (e.g. matched turbines or a prior period) and a measurement plan for downtime and cost |
| B2 or S5 shows misses that matter, or S3/S4 fail | no rung-6 trial; publish the failure analysis; revisit the model or the vertical (`INITIAL_MARKET_AND_ASSET_CHOICE.md` §10) |
| S2 or S7 fails | fix the operational path and repeat the pilot |
