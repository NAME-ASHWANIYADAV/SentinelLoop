# Operator feedback plan

> **NOT YET FIELD VALIDATED.** No operator has used SentinelLoop. This plan describes how feedback will be collected during the shadow pilot (`PILOT_PROTOCOL.md`).

## 1. What we need to learn

1. Are the recommendations right? Do they agree with what the engineers would conclude, and with what the turbines later show?
2. Are they understandable: the state, the reasons, the deviating signals and the due-date rule?
3. Are they bearable: how many there are, and how much time they take?
4. Do they fit the work: the existing CMMS, the crew planning and the OEM contract?

This is also the first real test of the persona and workflow hypotheses in `CUSTOMER_DISCOVERY.md` and `USER_WORKFLOWS.md`.

## 2. Per-recommendation feedback (every INSPECTION, URGENT and DATA_QUALITY state, and every desk-review order)

Recorded by the reliability engineer in a structured form.

**Blind judgement first.** Before opening the partner's CMMS for that turbine, the engineer records:
- would you inspect? (yes / no / need more data);
- urgency (days);
- confidence (1–5).

**Then the comparison:**
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

**Follow-up for DATA_QUALITY_FAILURE** (instrument-check orders): was there an instrumentation or data problem? (confirmed / not found / not checked). A whole-feed delay (`data_delivery_delay`) raises no order while it lasts. It is a data-path problem and is followed up in the ingestion log (criterion S2). The first good assessment after the delay can still raise an instrument-check order (a known gap, `DATA_CONTRACTS.md` §1). Such an order is recorded as a feed-delay recovery, not as a confirmed or unconfirmed instrument problem, and is kept out of S6 (`PILOT_ACCEPTANCE_CRITERIA.md`).

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

- Agreement between the blind judgement and SentinelLoop's state, as a cross-table plus Cohen's kappa with an interval. The numbers will be small.
- Usefulness share (criterion S4), with reason-code counts. The most frequent reason codes drive the changes.
- The interview themes are coded by two people independently where possible. Quotes are used only with consent and anonymised.

## 6. Ethics and data

- Participation is voluntary. Feedback is about the system, never a performance review of people.
- Interview notes are pseudonymised, stored under the data-sharing agreement, and deleted at the agreed date.
- No feedback is published without the partner's written consent.
