# User workflows

These workflows are built for the personas in `CUSTOMER_DISCOVERY.md` §3. **Those personas are hypotheses: no user has been interviewed.** Each workflow lists the steps, the system states involved, the API calls behind them, what the operator console offers, and its status.
- "Console" means the operator console (`src/sentinelloop/console/app.py`, PD-21). It is a thin Streamlit client of the REST API: every console action is an API call made with the user's own key, so the API's role checks apply. It is tested headless (`tests/test_console.py`); the Schedule page is tested for proposing a plan but not for applying one, and the Audit page only for its chain-verification button. No operator has used it.
- **Times in the console.** The Fleet, Asset, Work queue, Schedule and Do the work pages show times in the local time of the asset's site, with the zone named. Work-order dates and times typed in the console (deferral dates, return to service) are read in that zone too (`test_job_cards_and_the_return_to_service_time_use_the_orders_site_time_zone`, `test_the_work_queue_shows_and_enters_dates_in_each_orders_site_time`). If the asset's site cannot be looked up, the time is shown in UTC and labelled UTC. The Audit page lists event times as stored, in UTC.
- Steps marked **API only** have no console control. Tests are in `tests/`.

| persona (hypothesis) | platform role |
|---|---|
| Wind turbine technician | `technician` |
| O&M planner / scheduler | `planner` |
| Reliability / performance engineer | `reliability_engineer` |
| Maintenance manager | `planner` or `viewer`, depending on site practice (UNVERIFIED) |
| IT/OT security, administrator | `admin` |
| SCADA export job, CMMS connector | `integration` |

## W1. Set up a site

**Actor:** admin, then planner. **API only**, apart from steps that need an engineer.
1. `admin init` and `admin create-admin` on the server. The first admin's key is shown once.
2. The admin creates users and roles: `POST /users`, then `POST /users/{id}/api-key`.
3. An engineer registers the site and the asset type with the library, for example `ensure_site_and_type` in `src/sentinelloop/app/adapters/wind.py`. No API route does this (KNOWN_LIMITATIONS P4).
4. The admin registers the turbines: `POST /assets`. Each turbine gets its criticality, failure consequence and maintenance windows.
5. The planner records technicians with skills and shifts, and parts with stock, lead times and known deliveries: `/sites/{id}/technicians`, `PUT /technicians/{id}/shifts`, `/sites/{id}/parts`. Technician listings are personal data and need `resources.read` (planner, reliability engineer, admin).

**Status:** IMPLEMENTED_AND_TESTED (`test_app_admin.py`, `test_app_api.py`); sites and asset types through the library only.

## W2. Load data and approve a model

**Actor:** integration, then reliability engineer. **API only.**
1. The export job posts readings: `POST /ingest/readings` or `POST /ingest/csv`, at most 200,000 readings per request. It checks `rows_rejected` and the reason codes, and fixes the export mapping when rows are rejected. There is no per-site tag mapping: the export must use the asset type's signal names (KNOWN_LIMITATIONS P12). A batch time zone (`default_tz`) that is not a known IANA zone is refused as a whole (422).
2. An engineer registers a model bundle with the library (`modelreg.register`; no API route). Registration refuses a `bundle.pkl` that does not match the checksum in its own manifest. The model starts as a candidate.
3. The reliability engineer reviews the candidate's manifest (`GET /models`). It states what the model was trained on, its data class, its evaluation and its limitations. The bundle's server path is shown to admins only.
4. The reliability engineer approves it with a reason: `POST /models/{id}/decision`. Approving retires the previous approved model for the same scope. `POST /models/rollback` restores an earlier one.

**Status:** IMPLEMENTED_AND_TESTED (`test_app_ingest.py`, `test_app_health.py`, `test_app_remediation_security.py`, `test_app_rereview_api.py`).

## W3. Commission a turbine (wind)

**Actor:** reliability engineer. **API only.**
1. Choose a period believed healthy: no open faults, no work on the drivetrain, normal operation. **This is a judgement and is recorded as one.**
2. `POST /assets/{id}/baseline` with the model id, start, end and reason.
3. The platform refuses if the period has fewer than 288 operating 10-minute points (two days), if the role is not reliability engineer or admin, if there is no reason, or if the model does not use per-asset baselines.
4. Until a turbine is commissioned, its assessments are MODEL_OUT_OF_SCOPE ("no_baseline"), unless a data check fails first: the model's data checks run before that scope decision, so a stuck sensor on an uncommissioned turbine is a DATA_QUALITY_FAILURE (`test_a_stuck_sensor_on_an_uncommissioned_turbine_is_a_data_failure`).
5. Re-commission after a logged component replacement or retrofit. Automatic prompting from work-order history, and bulk re-commissioning after a model change, are PLANNED (KNOWN_LIMITATIONS M6).

**Status:** IMPLEMENTED_AND_TESTED on SYNTHETIC data (`test_app_wind.py`, `test_app_rereview_health.py`).

## W4. Daily review of the fleet

**Actor:** reliability engineer and planner.
1. **Assessments** run after each data load: `POST /assets/{id}/assess`, started by an external scheduler such as cron (no built-in scheduler, KNOWN_LIMITATIONS P5). Console: "Assess now" on the Asset page, for the integration, admin, reliability engineer and planner roles.
   - With a live feed the instant is now (`assess_at: now`).
   - For sites that deliver periodic exports, the asset type's policy can say `assess_at: latest_reading`. After each export, `POST /assets/{id}/assess-range` (start, end, step in minutes) assesses the period oldest first. **API only.**
     - A call costs one rate-limit token per 10 steps: with the shipped limiter at most 1,200 steps per call, so a longer export is sent as several calls (KNOWN_LIMITATIONS P13).
     - One range runs per user and two per server. A call over either limit, or one the user's bucket cannot pay yet, gets 429 with `Retry-After`; the export job waits that long and sends it again.
     - Every instant is checked before any is assessed, so a refused range stores nothing.
   - An instant more than 5 minutes in the future, earlier than 2000-01-01, or more than 5 minutes before the asset's first reading is refused.
   - An instant at or before the last one applied is stored as a replay. A replay never lowers a warning or moves the live state. But a replay that finds an urgent or inspection condition the latch does not yet carry raises the latch, so an urgent episode inside a late export is not lost (PD-28). `assess-range` counts these as `replays_escalated`, and each is recorded in the asset's audit history. A replay of an instant already assessed with the same finding raises nothing, so re-running on the same latest reading never undoes a dismissal or a completed inspection.
2. **The fleet list** (`GET /assets`; console: Fleet page) shows each asset's labels and when it was last assessed (`last_assessed_at`, shown in site-local time in the console).
   - Health states: NORMAL_MONITORING, INSPECTION_RECOMMENDED, URGENT_REVIEW, DATA_QUALITY_FAILURE, MODEL_OUT_OF_SCOPE, MODEL_UNAVAILABLE.
   - NOT_ASSESSED: never assessed. AWAITING_ASSESSMENT: a latch was cleared; the asset is not shown as healthy until it is assessed again.
   - INSPECTION_PENDING: a latched inspection is still open while a data, scope or model problem is shown.
   - ASSESSMENT_OVERDUE: no assessment has been applied within `max_assessment_age_hours` (6 h by default, 26 h for wind), so the assessment job has probably stopped. It is also shown when the asset shows a result but no assessment time is on record (for example on an upgraded database whose state row has no assessments).
   - HUMAN_APPROVAL_REQUIRED: an order for the asset waits for approval.
3. **The asset detail** (`GET /assets/{id}`, `/assessment`; console: Asset page) shows the reasons, the data-quality detail and the deviating signals, and for RUL models the interval and the risk. The console also shows the model's training-data class, says it is not field-validated, and labels RUL figures as model-implied. A stored instant the console cannot show as a date is shown as text; the page does not fail (`test_odd_assessment_instants_do_not_crash_the_asset_page`).
4. A latched state shows why it is still latched, for example "latched: latest assessment is NORMAL_MONITORING; urgent review stays until maintenance or a reasoned dismissal".
5. Data-quality failures go to an instrument check, not to an inspection of the machine. When every required signal is late together, the reason is `data_delivery_delay` and no instrument check is raised: the feed is late, not the asset (`GET /ingest/staleness` lists silent signals). If an inspection was latched before the data failure, its P2 inspection is raised as well, also during a feed delay (`test_a_latched_inspection_hidden_by_a_data_failure_gets_its_inspection_order`).

**Status:** IMPLEMENTED_AND_TESTED (`test_app_health.py`, `test_app_remediation.py`, `test_app_rereview_health.py`, `test_app_rereview_api.py`, `test_console.py`). `assess_at: latest_reading`, `assess-range` and replay escalation are tested on SYNTHETIC wind data and test pumps (`test_app_rereview_health.py`), and the route's cost and concurrency limits through the API (`test_app_rereview_api.py`).

## W5. Turn recommendations into approved work

**Actor:** planner or reliability engineer (approval: planner, reliability engineer, admin).
1. `POST /decisions/generate`; console: "Generate recommendations" on the Fleet page. Deferred orders whose date has passed come back for approval first. New orders are created PENDING_APPROVAL with an explanation: the state, the reasons and the due-date rule. Where it exists, the explanation adds P(failure) and the expected loss; the console labels that probability model-implied and not calibrated (C2). Anomaly models give no probability; their orders are ranked by deviation and consequence.
   - **Open orders that cover a recommendation** (PD-28). No duplicate is raised when an open order can satisfy the recommendation:
     - An order for the recommended job, the inspection or the urgent job that was raised before the current warning latched is **linked** to it only while it awaits approval or is deferred. It is escalated in place (its class and due date only ever move earlier) and is up for approval again (a deferred one comes back), so an approver confirms it for its new purpose; completing it can then clear the warning (W7).
     - An older order for one of those jobs that is already approved, scheduled or in progress is **superseded**: a new order is raised, its explanation names the older one, and the older one is left as it is. A routine job (for example a lubrication) and a DRAFT never stand in for a warning.
     - An instrument check or desk review never stands in for an inspection or urgent job; the needed order is raised as well.
     - An open equipment order that has been submitted (not a DRAFT) covers a desk review: a person is already going to look at the asset.
   - The console's message after generating counts the orders created, escalated, linked (without a change of class or date), back from deferral and held back by a rejection.
2. The approver opens each order and approves, defers (reason and the date it comes back) or rejects (reason). Console: Work queue page. Each card shows the priority, the job, duration × crew, the due date (in the site's local time), how long the order has waited and why it was raised. A deferred order comes back at 06:00 local time at its site on the chosen date. Roles that cannot approve see no buttons.
3. After the decision:
   - A deferred order returns for approval on its date, the next time `decisions/generate` runs. One order that fails to return is reported and the others still return. Console: the Deferred list shows each return date (in the site's local time), with "Bring back now".
   - A rejected recommendation is not re-raised for the same assessment and job (`already_decided`). After a reasoned rejection the same condition is held back (`suppressed`) for 24 h, 168 h or 720 h, by the rejected order's class (P1/P2/P3; site-configurable), unless the new recommendation is of a higher class. The rules (PD-28):
     - It applies on every path that raises an order, including the separate P1 below.
     - While a warning is latched, the condition is the latch, whatever state the asset shows: a switch to out of scope or model unavailable and back does not raise it again. The rejected order can be any order that stood in for the warning, for example an inspection escalated to P1, or an older order brought back for approval.
     - It does not carry over to a new latch: after a dismissal or a completed inspection, a new warning is raised again.
     - When the latch's start is not on record, the rejection holds until a dismissal, or a completion that cleared the latch, is recorded for the asset.
     - Without a latch, it holds for the system's own order for the same job and state.
   - A higher-priority assessment escalates an open order. A deferred order that the engine escalates to a higher class, or links to a new warning, comes back for approval. A system escalation never moves a due date later.
   - If the condition becomes urgent while lower-priority work for it is in progress, the engine first escalates in place another order that stands in for it and is awaiting approval, approved, scheduled or deferred (a deferred one comes back for approval). Only when there is no such order is a separate P1 order raised (`decision._decide`).
   - A planner, reliability engineer or admin can change an open order's priority, with a reason: `POST /work-orders/{id}/reprioritise`. The order keeps its risk score, and its due date unless a new one is given; with `expected_version`, a change based on a stale copy is refused (409). **API only.**
4. Dismissing a latched risk without doing work needs a written reason from a planner, reliability engineer or admin: `POST /assets/{id}/clear-risk` with `dismissed`. That route refuses `maintenance_completed`, because maintenance clears a latch only through its work order (W7). Console: "Dismiss a latched warning" on the Asset page, shown only to those roles and only while something is latched. The asset then shows AWAITING_ASSESSMENT.

**Status:** IMPLEMENTED_AND_TESTED (`test_app_decision.py`, `test_app_workorders.py`, `test_app_remediation.py`, `test_app_rereview_decision.py`, `test_app_rereview_wiring.py`, `test_console.py`). The `reprioritise` route is tested for the version check and for keeping the score; the console's linked count is checked only in the source (`test_the_console_counts_linked_orders_after_generating`).

## W6. Schedule the week

**Actor:** planner (or admin). Console: Schedule page.
1. `POST /schedules` with the site, policy and horizon creates a proposal: assignments, unscheduled work with reasons, and any violations. **Nothing changes yet.** Slots are at least 0.25 h. The MILP policy is refused above 5,000 approved orders × slots; use `risk_greedy`, a shorter horizon or longer slots (KNOWN_LIMITATIONS P14).
2. The planner reviews the proposal: conflicts, unscheduled jobs and the objective. The console shows assignments, unscheduled jobs with their reasons (as plain text) and the violations, and offers no Apply button while there are violations.
3. `POST /schedules/{id}/apply` schedules each order with its technicians. It is refused if any order changed since planning (stale) or if the proposal has violations. Where the site has a recorded crew list, only its registered, active technicians can be assigned.
4. Shifts are changed only through `PUT /technicians/{id}/shifts`. **API only**: the console cannot edit shifts (KNOWN_LIMITATIONS P11).
5. Weather, climbing limits, cranes, travel and multi-day jobs are not modelled (KNOWN_LIMITATIONS P8). The console's help text says to enter weather windows as maintenance windows.

**Status:** IMPLEMENTED_AND_TESTED (`test_app_planning.py`, `test_app_remediation.py`, `test_app_rereview_api.py`). The console's Schedule page is tested for proposing a plan and showing unscheduled reasons (`test_api_text_in_tables_is_plain_text_not_markdown`), not for applying one. The choice of policy follows PD-27 (supersedes PD-09): the probabilistic trigger with the risk-ranked greedy queue (`risk_greedy`, the default) at placeholder settings, to be tuned per site; a tuned point-threshold trigger is PLANNED; the MILP is a what-if planner, never claimed optimal. The scheduling evidence is SIMULATED only: see `SCHEDULING_EVALUATION.md` (S2).

## W7. Do the work and record what was found

**Actor:** technician (planner and admin may do the same steps). Console: "Do the work" page, which lists scheduled and in-progress jobs with a job card: why, start and due (in the site's local time), duration, crew size and skill, planned parts and the assigned technicians.
1. Start the order: `transitions` with `start`.
2. If the crew cannot do the job (weather, access, crew), hand it back with a reason: `transitions` with `hand_back`, from SCHEDULED or IN_PROGRESS. The order returns to APPROVED with its schedule and crew cleared, for the planner to reschedule. Console: "Hand back to the planner"; a reason is required.
3. Complete it: `POST /work-orders/{id}/complete` with the outcome (`DATA_CONTRACTS.md` §3): what was found (`findings_code`), whether a failure is confirmed, root cause, actions taken, parts used, downtime, return to service, notes. In the console, actions taken and downtime are required, and the return-to-service time is entered in the site's local time; the field names the zone.
4. Contradictions are flagged for review rather than refused. Examples: "failure confirmed" together with "no fault found", parts that differ from the plan, or a P1 system recommendation with no fault found. Console: the technician is told which flags were recorded, and approvers see completed orders whose outcome needs review.
5. Completing the order clears a latched risk only when all of these hold (PD-16, refined by PD-28):
   - the order was raised after the latch began, or was linked to it by a system escalation recorded after it began (W5);
   - its job addresses the equipment: not `instrument_check` or `desk_review`, nor the site's configured data or review job, whichever route completes it;
   - the findings are `degradation_found`, `failure_found` or `no_fault_found`;
   - it was completed by a person, not the integration role.

   Otherwise the latch stays, the outcome is flagged `latch_kept` and the reason is noted on the asset. "Could not inspect" (`not_inspected`) keeps the warning; the console says so and suggests handing the job back if it should be redone. A latch whose start is unknown is kept. On a database upgraded through migration 0007 the recorded start may be later than the true start, and the kept-latch reason speaks of "the recorded start" for that reason. Both outcomes are recorded in the asset's own audit history (`asset_state.maintenance_completed`, `asset_state.latch_kept`). A cleared asset shows AWAITING_ASSESSMENT until its next assessment.
6. A follow-up job (for example a repair found during an inspection) cannot be raised from the console (KNOWN_LIMITATIONS P11). A planner creates it with `POST /work-orders` (an `Idempotency-Key` header is required, and may not start with `rec:`, `reactivate:` or `apply:`); it starts as DRAFT and needs `submit` and approval. Or it is raised in the CMMS. **API only.**
7. `GET /work-orders/missing-outcomes` lists completed orders without an outcome, for the planner to chase. The console shows them on the "Do the work" page.
8. Limitation: technician resources are not linked to users, so any technician can start or complete any scheduled order (KNOWN_LIMITATIONS P10).

**Status:** IMPLEMENTED_AND_TESTED (`test_app_workorders.py`, `test_app_remediation.py`, `test_app_rereview_decision.py`, `test_app_rereview_wiring.py`, `test_console.py`).

## W8. Investigate a decision afterwards

**Actor:** reliability engineer or admin. Console: Audit page.
1. `GET /audit/{entity}/{id}` gives the full history of an asset, assessment, work order, schedule run, model or ingestion batch (any role). Other entities, such as users, need `audit.read`. The CMMS host and error text in integration events are shown to admins only.
2. `GET /audit/verify` (admin, reliability engineer) checks the chain.
   - Without anchor parameters it checks only internal consistency and says so (`anchor_checked: false`). It cannot detect that the newest events were deleted. The console's "Verify the audit chain" button makes this unanchored check, and shows a consistent chain as a warning that no anchor was checked, never as a pass (`test_an_unanchored_audit_verification_is_not_shown_as_valid`).
   - An anchor needs both `anchor_seq` and `anchor_hash`; a partial or malformed anchor is refused (422).
   - To prove the trail has not been edited or truncated, run `admin verify-audit --anchor <anchor file kept off the host>`. It fails without an anchor unless `--allow-no-anchor` is given (PD-22), and refuses an anchor file without an integer `seq` and a 64-hex `hash` (exit 2).
3. The chain covers audit events, not the state tables: a direct database edit of state is not detected (PD-22).
4. Each assessment carries its model checksum, policy SHA-256 and input window, so the result can be reproduced. Replays are marked `applied_to_state = 0`; a replay that raised a latch is recorded on the asset as `asset_state.escalated_by_replay`. The order raised afterwards cites the latest applied assessment, not the replay, so the approver opens the asset history to see that evidence (KNOWN_LIMITATIONS M10).

**Status:** IMPLEMENTED_AND_TESTED (`test_app_foundation.py`, `test_app_admin.py`, `test_app_remediation_security.py`, `test_app_rereview_api.py`, `test_app_rereview_wiring.py`); the console's Audit page is tested only for the verification button.

## W9. Recover from a failure

**Actor:** admin. **API and CLI only.**
- Back up: `admin backup --to …`. Restore to a new path: `admin restore --from …`. Then verify the audit chain against the anchor.
- If a model misbehaves, roll it back: `POST /models/rollback`.

**Status:** IMPLEMENTED_AND_TESTED. Recovery drill R1 (`product/evidence/recovery/r1.md`, one laptop, SYNTHETIC data): restore to ready in 6.34 s, audit verified against the backup's anchor; data written after the last backup are lost. Full procedure in `OPERATIONS_RUNBOOK.md`.

## W10. Send approved work to a CMMS

**Actor:** admin, then the integration job. **API only.** Details: `INTEGRATION_GUIDE.md`.
1. Operations add the CMMS host to `SENTINELLOOP_INTEGRATION_HOSTS` and put its credential in a `SENTINELLOOP_CRED_*` environment variable on the server.
2. The admin registers the target (`odoo_json2` or `webhook`): `POST /integrations`. The config names the environment variable, never the secret, and its values are checked at registration. The target starts in read-only shadow mode.
3. A scheduled job (integration role) calls `POST /integrations/{id}/dispatch`. In shadow mode it records what it would send and makes no external call. `GET /integrations/{id}/items` shows the records; only admins see a target's config and host and the error text of failed items. Only approved work (APPROVED, SCHEDULED, IN_PROGRESS) is ever sent.
   - One dispatch of a target runs at a time, under an expiring lease. An overlapping call returns `busy: true` and sends nothing.
   - A run whose lease lapsed, or whose target's mode changed, stops before its next call (`stopped` says why); a switch to shadow mode during a live run stops it.
4. After review, the admin switches the target to `draft_requests` with a written reason: `POST /integrations/{id}/mode`.
   - Requests marked `[SentinelLoop]` are then created and updated.
   - Withdrawn, deferred and completed orders are mirrored onto the existing request as text.
   - CMMS stages are never changed, and nothing is closed or deleted.
5. Failures:
   - Permanent failures become dead letters. The admin requeues one with a reason: `POST /integrations/{id}/items/{wo_id}/requeue`.
   - An unexpected answer to a create or write (a body that is not JSON, or a create answer that is not a single id) is recorded and retried, like a timeout; the retry of a create searches by marker first, so nothing is created twice. An unexpected answer to a read (for example a sign-in page instead of the API), or an unexpected error, is a dead letter for that order only. Either way the run goes on.
   - Every create is logged before it is sent. If its answer is lost, the next attempt first searches the CMMS by the order's marker, and an order recovered this way is searched once more about an hour later. Two requests carrying one order's marker make a dead letter for a person, and the other request stays live until a person acts (KNOWN_LIMITATIONS S10).

**Status:** IMPLEMENTED_AND_TESTED against a contract test double only (`test_app_integration.py`, `test_app_remediation_security.py`, `test_app_rereview_integration.py`, `test_app_api.py`). Mirroring is tested for cancelled and deferred orders only; mirroring of rejected, completed and closed orders is implemented with no automated test. The real Odoo sandbox has NOT been run: the image download awaits approval. No customer CMMS is connected.
