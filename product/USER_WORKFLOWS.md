# User workflows

These workflows are built for the personas in `CUSTOMER_DISCOVERY.md` §3. **Those personas are hypotheses: no user has been interviewed.** Each workflow lists the steps, the system states involved, the API calls behind them, what the operator console offers, and its status.
- "Console" means the operator console (`src/sentinelloop/console/app.py`, PD-21). It is a thin Streamlit client of the REST API: every console action is an API call made with the user's own key, so the API's role checks apply. It is tested headless (`tests/test_console.py`), except the Schedule and Audit pages, and no operator has used it. It shows site-local times on the Fleet, Asset and Schedule pages; the Work queue and Do the work pages show work-order times in UTC.
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
1. The export job posts readings: `POST /ingest/readings` or `POST /ingest/csv`, at most 200,000 readings per request. It checks `rows_rejected` and the reason codes, and fixes the export mapping when rows are rejected. There is no per-site tag mapping: the export must use the asset type's signal names (KNOWN_LIMITATIONS P12).
2. An engineer registers a model bundle with the library (`modelreg.register`; no API route). Registration refuses a `bundle.pkl` that does not match the checksum in its own manifest. The model starts as a candidate.
3. The reliability engineer reviews the candidate's manifest (`GET /models`). It states what the model was trained on, its data class, its evaluation and its limitations.
4. The reliability engineer approves it with a reason: `POST /models/{id}/decision`. Approving retires the previous approved model for the same scope. `POST /models/rollback` restores an earlier one.

**Status:** IMPLEMENTED_AND_TESTED (`test_app_ingest.py`, `test_app_health.py`, `test_app_remediation_security.py`).

## W3. Commission a turbine (wind)

**Actor:** reliability engineer. **API only.**
1. Choose a period believed healthy: no open faults, no work on the drivetrain, normal operation. **This is a judgement and is recorded as one.**
2. `POST /assets/{id}/baseline` with the model id, start, end and reason.
3. The platform refuses if the period has fewer than 288 operating 10-minute points (two days), if the role is not reliability engineer or admin, if there is no reason, or if the model does not use per-asset baselines.
4. Until a turbine is commissioned, its assessments are MODEL_OUT_OF_SCOPE ("no_baseline").
5. Re-commission after a logged component replacement or retrofit. Automatic prompting from work-order history, and bulk re-commissioning after a model change, are PLANNED (KNOWN_LIMITATIONS M6).

**Status:** IMPLEMENTED_AND_TESTED on SYNTHETIC data (`test_app_wind.py`).

## W4. Daily review of the fleet

**Actor:** reliability engineer and planner.
1. **Assessments** run after each data load: `POST /assets/{id}/assess`, started by an external scheduler such as cron (no built-in scheduler, KNOWN_LIMITATIONS P5). Console: "Assess now" on the Asset page, for the integration, admin, reliability engineer and planner roles.
   - With a live feed the instant is now (`assess_at: now`).
   - For sites that deliver periodic exports, the asset type's policy can say `assess_at: latest_reading`. After each export, `POST /assets/{id}/assess-range` (start, end, step in minutes; at most 2,000 steps) assesses the period oldest first. **API only.**
   - An instant more than 5 minutes in the future is refused. An instant at or before the last one applied is stored as a replay and never changes what the fleet shows.
2. **The fleet list** (`GET /assets`; console: Fleet page) shows each asset's labels and when it was last assessed (`last_assessed_at`, shown in site-local time in the console).
   - Health states: NORMAL_MONITORING, INSPECTION_RECOMMENDED, URGENT_REVIEW, DATA_QUALITY_FAILURE, MODEL_OUT_OF_SCOPE, MODEL_UNAVAILABLE.
   - NOT_ASSESSED: never assessed. AWAITING_ASSESSMENT: a latch was cleared; the asset is not shown as healthy until it is assessed again.
   - INSPECTION_PENDING: a latched inspection is still open while a data, scope or model problem is shown.
   - ASSESSMENT_OVERDUE: no assessment has been applied within `max_assessment_age_hours` (6 h by default, 26 h for wind), so the assessment job has probably stopped.
   - HUMAN_APPROVAL_REQUIRED: an order for the asset waits for approval.
3. **The asset detail** (`GET /assets/{id}`, `/assessment`; console: Asset page) shows the reasons, the data-quality detail and the deviating signals, and for RUL models the interval and the risk. The console also shows the model's training-data class, says it is not field-validated, and labels RUL figures as model-implied.
4. A latched state shows why it is still latched, for example "latched: latest assessment is NORMAL_MONITORING; urgent review stays until maintenance or a reasoned dismissal".
5. Data-quality failures go to an instrument check, not to an inspection of the machine. When every required signal is late together, the reason is `data_delivery_delay` and no work order is raised: the feed is late, not the asset (`GET /ingest/staleness` lists silent signals).

**Status:** IMPLEMENTED_AND_TESTED (`test_app_health.py`, `test_app_remediation.py`, `test_console.py`). `assess_at: latest_reading` and `assess-range` have no automated test yet.

## W5. Turn recommendations into approved work

**Actor:** planner or reliability engineer (approval: planner, reliability engineer, admin).
1. `POST /decisions/generate`; console: "Generate recommendations" on the Fleet page. Deferred orders whose date has passed come back for approval first. New orders are created PENDING_APPROVAL with an explanation: the state, the reasons and the due-date rule. Where it exists, the explanation adds P(failure) and the expected loss; the console labels that probability model-implied and not calibrated (C2). Anomaly models give no probability; their orders are ranked by deviation and consequence.
2. The approver opens each order and approves, defers (reason and the date it comes back) or rejects (reason). Console: Work queue page. Each card shows the priority, the job, duration × crew, the due date (in UTC), how long the order has waited and why it was raised. Roles that cannot approve see no buttons.
3. After the decision:
   - A deferred order returns for approval on its date, the next time `decisions/generate` runs. Console: the Deferred list shows each return date (in UTC), with "Bring back now".
   - A rejected recommendation is not re-raised for the same assessment (`already_decided`). For the same condition it is held back for 24 h, 168 h or 720 h (P1/P2/P3) after a reasoned rejection (`suppressed`), unless it escalates.
   - A higher-priority assessment escalates an open order. A deferred order escalated to P1 comes back for approval.
   - If the condition becomes urgent while lower-priority work on the asset is in progress, a separate P1 order is raised.
   - A planner, reliability engineer or admin can change an open order's priority, with a reason: `POST /work-orders/{id}/reprioritise`. **API only.**
4. Dismissing a latched risk without doing work needs a written reason from a planner, reliability engineer or admin: `POST /assets/{id}/clear-risk` with `dismissed`. That route refuses `maintenance_completed`, because maintenance clears a latch only through its work order (W7). Console: "Dismiss a latched warning" on the Asset page, shown only to those roles and only while something is latched. The asset then shows AWAITING_ASSESSMENT.

**Status:** IMPLEMENTED_AND_TESTED (`test_app_decision.py`, `test_app_workorders.py`, `test_app_remediation.py`, `test_console.py`). The `reprioritise` route itself is covered only by the authentication check; the service behind it is tested.

## W6. Schedule the week

**Actor:** planner (or admin). Console: Schedule page.
1. `POST /schedules` with the site, policy and horizon creates a proposal: assignments, unscheduled work with reasons, and any violations. **Nothing changes yet.**
2. The planner reviews the proposal: conflicts, unscheduled jobs and the objective. The console shows assignments, unscheduled jobs with their reasons and the violations, and offers no Apply button while there are violations.
3. `POST /schedules/{id}/apply` schedules each order with its technicians. It is refused if any order changed since planning (stale) or if the proposal has violations. Where the site has a recorded crew list, only its registered, active technicians can be assigned.
4. Shifts are changed only through `PUT /technicians/{id}/shifts`. **API only**: the console cannot edit shifts (KNOWN_LIMITATIONS P11).
5. Weather, climbing limits, cranes, travel and multi-day jobs are not modelled (KNOWN_LIMITATIONS P8). The console's help text says to enter weather windows as maintenance windows.

**Status:** IMPLEMENTED_AND_TESTED (`test_app_planning.py`, `test_app_remediation.py`); the console's Schedule page has no automated test. The choice of policy follows PD-27 (supersedes PD-09): the probabilistic trigger with the risk-ranked greedy queue (`risk_greedy`, the default) at placeholder settings, to be tuned per site; a tuned point-threshold trigger is PLANNED; the MILP is a what-if planner, never claimed optimal. The scheduling evidence is SIMULATED only: see `SCHEDULING_EVALUATION.md` (S2).

## W7. Do the work and record what was found

**Actor:** technician (planner and admin may do the same steps). Console: "Do the work" page, which lists scheduled and in-progress jobs with a job card: why, start and due (in UTC), duration, crew size and skill, planned parts and the assigned technicians.
1. Start the order: `transitions` with `start`.
2. If the crew cannot do the job (weather, access, crew), hand it back with a reason: `transitions` with `hand_back`, from SCHEDULED or IN_PROGRESS. The order returns to APPROVED with its schedule and crew cleared, for the planner to reschedule. Console: "Hand back to the planner"; a reason is required.
3. Complete it: `POST /work-orders/{id}/complete` with the outcome (`DATA_CONTRACTS.md` §3): what was found (`findings_code`), whether a failure is confirmed, root cause, actions taken, parts used, downtime, return to service, notes. In the console, actions taken and downtime are required. The return-to-service field is labelled local time, but the console reads the value as UTC (`console/app.py`, `_tz(None)`), so enter it in UTC.
4. Contradictions are flagged for review rather than refused. Examples: "failure confirmed" together with "no fault found", parts that differ from the plan, or a P1 system recommendation with no fault found. Console: the technician is told which flags were recorded, and approvers see completed orders whose outcome needs review.
5. Completing the order clears a latched risk only when all of these hold (PD-16):
   - the order was raised after the latch began;
   - its job addresses the equipment, so not `instrument_check` or `desk_review`;
   - the findings are `degradation_found`, `failure_found` or `no_fault_found`;
   - it was completed by a person, not the integration role.

   Otherwise the latch stays, the outcome is flagged `latch_kept` and the reason is noted on the asset. "Could not inspect" (`not_inspected`) keeps the warning; the console says so and suggests handing the job back if it should be redone. A latch whose start is unknown is kept. A cleared asset shows AWAITING_ASSESSMENT until its next assessment.
6. A follow-up job (for example a repair found during an inspection) cannot be raised from the console (KNOWN_LIMITATIONS P11). A planner creates it with `POST /work-orders` (an `Idempotency-Key` header is required); it starts as DRAFT and needs `submit` and approval. Or it is raised in the CMMS. **API only.**
7. `GET /work-orders/missing-outcomes` lists completed orders without an outcome, for the planner to chase. The console shows them on the "Do the work" page.
8. Limitation: technician resources are not linked to users, so any technician can start or complete any scheduled order (KNOWN_LIMITATIONS P10).

**Status:** IMPLEMENTED_AND_TESTED (`test_app_workorders.py`, `test_app_remediation.py`, `test_console.py`).

## W8. Investigate a decision afterwards

**Actor:** reliability engineer or admin. Console: Audit page.
1. `GET /audit/{entity}/{id}` gives the full history of an asset, assessment, work order, schedule run, model or ingestion batch (any role). Other entities, such as users, need `audit.read`.
2. `GET /audit/verify` (admin, reliability engineer) checks the chain.
   - Without anchor parameters it checks only internal consistency, and so does the console's "Verify the audit chain" button. It cannot detect that the newest events were deleted.
   - To prove the trail has not been edited or truncated, run `admin verify-audit --anchor <anchor file kept off the host>`. It fails without an anchor unless `--allow-no-anchor` is given (PD-22).
3. The chain covers audit events, not the state tables: a direct database edit of state is not detected (PD-22).
4. Each assessment carries its model checksum, policy SHA-256 and input window, so the result can be reproduced. Replays are marked `applied_to_state = 0`.

**Status:** IMPLEMENTED_AND_TESTED (`test_app_foundation.py`, `test_app_admin.py`, `test_app_remediation_security.py`); the console's Audit page has no automated test.

## W9. Recover from a failure

**Actor:** admin. **API and CLI only.**
- Back up: `admin backup --to …`. Restore to a new path: `admin restore --from …`. Then verify the audit chain against the anchor.
- If a model misbehaves, roll it back: `POST /models/rollback`.

**Status:** IMPLEMENTED_AND_TESTED. Recovery drill R1 (`product/evidence/recovery/r1.md`, one laptop, SYNTHETIC data): restore to ready in 6.34 s, audit verified against the backup's anchor; data written after the last backup are lost. Full procedure in `OPERATIONS_RUNBOOK.md`.

## W10. Send approved work to a CMMS

**Actor:** admin, then the integration job. **API only.** Details: `INTEGRATION_GUIDE.md`.
1. Operations add the CMMS host to `SENTINELLOOP_INTEGRATION_HOSTS` and put its credential in a `SENTINELLOOP_CRED_*` environment variable on the server.
2. The admin registers the target (`odoo_json2` or `webhook`): `POST /integrations`. The config names the environment variable, never the secret. The target starts in read-only shadow mode.
3. A scheduled job (integration role) calls `POST /integrations/{id}/dispatch`. In shadow mode it records what it would send and makes no external call. `GET /integrations/{id}/items` shows the records; only admins see a target's config. Only approved work (APPROVED, SCHEDULED, IN_PROGRESS) is ever sent.
4. After review, the admin switches the target to `draft_requests` with a written reason: `POST /integrations/{id}/mode`.
   - Requests marked `[SentinelLoop]` are then created and updated.
   - Withdrawn, deferred and completed orders are mirrored onto the existing request as text.
   - CMMS stages are never changed, and nothing is closed or deleted.
5. Permanent failures become dead letters. The admin requeues one with a reason: `POST /integrations/{id}/items/{wo_id}/requeue`.

**Status:** IMPLEMENTED_AND_TESTED against a contract test double only (`test_app_integration.py`, `test_app_remediation_security.py`, `test_app_api.py`). Mirroring is tested for cancelled and deferred orders only; mirroring of rejected, completed and closed orders is implemented with no automated test. The real Odoo sandbox has NOT been run: the image download awaits approval. No customer CMMS is connected.
