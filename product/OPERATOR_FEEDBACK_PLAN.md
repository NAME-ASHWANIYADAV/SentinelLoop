# Operator feedback plan

> **NOT YET FIELD VALIDATED.** No operator has used SentinelLoop. This plan describes how feedback will be collected during the shadow pilot (`PILOT_PROTOCOL.md`).

## 1. What we need to learn

1. Are the recommendations right? Do they agree with what the engineers would conclude, and with what the turbines later show?
2. Are they understandable: the state, the reasons, the deviating signals and the due-date rule?
3. Are they bearable: how many there are, and how much time they take?
4. Do they fit the work: the existing CMMS, the crew planning and the OEM contract?

This is also the first real test of the persona and workflow hypotheses in `CUSTOMER_DISCOVERY.md` and `USER_WORKFLOWS.md`.

## 2. Per-recommendation feedback (every INSPECTION, URGENT and DATA_QUALITY state, and every desk-review order)

Recorded in a structured form: step 1 by the step-1 judge, the rest by the reliability engineer. There are two blinded steps (PD-23; `PILOT_PROTOCOL.md` §3).

**Step 1: independent judgement, blind to SentinelLoop.** For a random sample of turbine-weeks, the reliability engineer records an independent judgement from the SCADA trends **before** seeing SentinelLoop's state for that turbine:
- would you inspect? (yes / no / need more data);
- urgency (days);
- confidence (1–5);
- had you seen this turbine's SentinelLoop state, or an order for it, before? (yes / no).

Agreement statistics (§5) use only these judgements. How step 1 is kept independent (as in `PILOT_PROTOCOL.md` §3, Blinding):
- Someone other than the judge (for example the SentinelLoop engineer) draws the sample from all pilot turbines, with a recorded random seed, before the weekly review, and tells the judge nothing about the sampled turbines' states.
- The judge reads the trends in the partner's own SCADA tool or export. The console has no trend view and the API has no readings route (`src/sentinelloop/console/app.py`, `src/sentinelloop/app/api.py`).
- The judge has no console access during the pilot, for example a second reliability engineer of the partner, outside the pilot team. If the only judge available is the pilot team's reliability engineer, who sees every state in the console and reviews every recommendation in step 2, they judge only turbines whose state they have not seen in any earlier week: a latch persists across weeks until it is cleared (PD-16).
- The SentinelLoop state each judgement is compared with is fixed in the analysis plan before day 1, for example the most severe state shown for the turbine during that week (replays excluded), together with the mapping from states to the judge's answers.

If these conditions cannot all be met, independence is not guaranteed and kappa is reported as indicative only.

**Step 2: review of every recommendation, blind to the CMMS.** Every recommendation is then reviewed **before** looking at the partner's CMMS for that turbine. The engineer records the first three step-1 items for the recommendation: would you inspect, urgency, confidence.

**Then the comparison, with the partner's CMMS and failure log open:**
- what the CMMS or failure log shows;
- whether the recommendation was useful (useful / not useful / unclear).

**Reason codes when not useful:**
- known issue already in hand;
- data artefact;
- operating condition not modelled (curtailment, icing, grid);
- sensor fault;
- duplicate;
- too late;
- too early to act;
- wrong component;
- other (free text).

**Follow-up for DATA_QUALITY_FAILURE** (instrument-check orders): was there an instrumentation or data problem? (confirmed / not found / not checked). A whole-feed delay (`data_delivery_delay`) raises no instrument-check order while it lasts; a turbine with a pending latched inspection still gets its inspection order, unless an open order already stands in for it (`decision._planned`; `test_a_latched_inspection_hidden_by_a_data_failure_gets_its_inspection_order`). The delay is a data-path problem and is followed up in the ingestion log (criterion S2). The first good assessment after the delay can still raise an instrument-check order (a known gap, `DATA_CONTRACTS.md` §1). Such an order is recorded as a feed-delay recovery, not as a confirmed or unconfirmed instrument problem, and is kept out of S6 (`PILOT_ACCEPTANCE_CRITERIA.md`).

**Storage.** The operator console exists (Streamlit, PD-21), but it has no feedback form (`KNOWN_LIMITATIONS.md` P7); a form is PLANNED. Until then, records go in a pilot spreadsheet keyed by work-order id and assessment id.
- The work-order id is shown on the console's work cards.
- The assessment id is stored on each system work order (`assessment_id` in `GET /api/v1/work-orders/{id}`).

The spreadsheet is joined to the audit trail.

## 3. Weekly review meeting (30–60 minutes)

- Attendees: the reliability engineer, a planner, a technicians' representative, and the SentinelLoop engineer as observer and notetaker.
- Walk through the week's states and feedback, the system work orders by type (criterion S3), assessability over operating hours (S1), and the reconciliation table (`PILOT_PROTOCOL.md` §4).
- Note the time spent (criterion S9).
- Three standing questions:
  - What would you have done differently because of SentinelLoop this week?
  - What was confusing?
  - What did it miss that you knew about?

## 4. Interviews (weeks 1, 6 and 12)

- **Who:** semi-structured, 30–45 minutes, with each role. Follow the interview rules in `CUSTOMER_DISCOVERY.md` §8: no leading questions; ask about the last real occurrence.
- **Week 1:** the current process for a drivetrain warning, from where it comes from to who decides; expectations.
- **Week 6:** trust, workload, misunderstandings, and changes they would make.
- **Week 12:** would they use it with actions enabled? What would have to change? Who would pay, and from which budget (for the buyer persona)?
- **Usability:** a standard usability questionnaire (e.g. SUS) for console users at weeks 6 and 12, reported as raw scores. The small sample is stated.

## 5. Analysis

- Agreement between the step-1 independent judgements (the sampled turbine-weeks only) and the SentinelLoop state fixed for comparison in the analysis plan (§2, Step 1), as a cross-table plus Cohen's kappa with an interval. Judgements whose judge had seen the turbine's state before are left out of kappa and reported apart. If the independence conditions in §2 could not all be met, kappa is reported as indicative only. Step-2 judgements are made after seeing the recommendation and are not used for agreement. The numbers will be small.
- Usefulness share (criterion S4: "useful" in the comparison), with reason-code counts, and step 2's would-inspect share beside it. The most frequent reason codes drive the changes.
- The interview themes are coded by two people independently where possible. Quotes are used only with consent and anonymised.

## 6. Ethics and data

- Participation is voluntary. Feedback is about the system, never a performance review of people.
- Interview notes are pseudonymised, stored under the data-sharing agreement, and deleted at the agreed date.
- No feedback is published without the partner's written consent.
