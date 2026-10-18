# User workflows

These workflows are built for the personas in `CUSTOMER_DISCOVERY.md` §3. **Those personas are hypotheses: no user has been interviewed.** Each workflow lists the steps, the system states involved, the API calls behind them, and its status.
- "UI" means the operator console, which is PLANNED (Phase 7).
- Until it exists, every workflow below runs through the REST API and is exercised by the tests named.

| persona (hypothesis) | platform role |
|---|---|
| Wind turbine technician | `technician` |
| O&M planner / scheduler | `planner` |
| Reliability / performance engineer | `reliability_engineer` |
| Maintenance manager | `planner` or `viewer`, depending on site practice (UNVERIFIED) |
| IT/OT security, administrator | `admin` |
| SCADA export job, CMMS connector | `integration` |

## W1. Set up a site

**Actor:** admin, then planner.
1. `admin init` and `admin create-admin` on the server. The first admin's key is shown once.
2. The admin creates users and roles: `POST /users`, then `POST /users/{id}/api-key`.
3. The admin registers the site, asset type and turbines: `POST /assets`. Each turbine gets its criticality, failure consequence and maintenance windows.
4. The planner records technicians with skills and shifts, and parts with stock, lead times and known deliveries: `/sites/{id}/technicians`, `/technicians/{id}/shifts`, `/sites/{id}/parts`.

**Status:** IMPLEMENTED_AND_TESTED (`test_app_admin.py`, `test_app_api.py`).

## W2. Load data and approve a model

**Actor:** integration, then reliability engineer.
1. The export job posts readings: `POST /ingest/readings` or `POST /ingest/csv`. It checks `rows_rejected` and the reason codes, and fixes the export mapping when rows are rejected.
2. The reliability engineer reviews a candidate model's manifest. It states what the model was trained on, its data class, its evaluation and its limitations.
3. The reliability engineer approves it with a reason: `POST /models/{id}/decision`. Approving retires the previous approved model for the same scope. `POST /models/rollback` restores an earlier one.

**Status:** IMPLEMENTED_AND_TESTED (`test_app_ingest.py`, `test_app_health.py`).

## W3. Commission a turbine (wind)

**Actor:** reliability engineer.
1. Choose a period believed healthy: no open faults, no work on the drivetrain, normal operation. **This is a judgement and is recorded as one.**
2. `POST /assets/{id}/baseline` with the model id, start, end and reason.
3. The platform refuses if fewer than two days of operating data exist, if the role is not allowed, or if the model is not a baseline-type model.
4. Until a turbine is commissioned, its assessments are MODEL_OUT_OF_SCOPE ("no_baseline").
5. Re-commission after a logged component replacement or retrofit. Automatic prompting from work-order history is PLANNED.

**Status:** IMPLEMENTED_AND_TESTED on SYNTHETIC data (`test_app_wind.py`).

## W4. Daily review of the fleet

**Actor:** reliability engineer and planner.
1. Assessments run after each data load: `POST /assets/{id}/assess`. A scheduler for this is PLANNED; today it runs as a cron job over the API.
2. The fleet list (`GET /assets`) shows each asset's state.
   - States: NORMAL_MONITORING, INSPECTION_RECOMMENDED, URGENT_REVIEW, DATA_QUALITY_FAILURE, MODEL_OUT_OF_SCOPE, MODEL_UNAVAILABLE, NOT_ASSESSED.
   - HUMAN_APPROVAL_REQUIRED is shown next to the state while an order waits.
3. The asset detail (`GET /assets/{id}`, `/assessment`) shows the reasons, the data-quality detail, the deviating signals and, for RUL models, the interval and the risk.
4. A latched state shows why it is still latched: "latest assessment is NORMAL; urgent review stays until maintenance or a reasoned dismissal".
5. Data-quality failures go to an instrument check, not to an inspection of the machine.

**Status:** API IMPLEMENTED_AND_TESTED; UI PLANNED.

## W5. Turn recommendations into approved work

**Actor:** planner or reliability engineer.
1. `POST /decisions/generate`. Orders are created PENDING_APPROVAL with an explanation: the state, the reasons, the due-date rule and, where it exists, P(failure) and the expected loss.
2. The approver opens each order and approves, defers (reason), rejects (reason) or edits its priority. A rejected or deferred recommendation is not recreated for the same assessment (`already_decided`). A higher-priority assessment escalates it.
3. Dismissing a latched risk without doing work needs a written reason from an allowed role: `POST /assets/{id}/clear-risk` with `dismissed`.

**Status:** IMPLEMENTED_AND_TESTED (`test_app_decision.py`, `test_app_workorders.py`).

## W6. Schedule the week

**Actor:** planner.
1. `POST /schedules` with the site, policy and horizon creates a proposal: assignments, unscheduled work with reasons, and any violations. **Nothing changes yet.**
2. The planner reviews the proposal: conflicts, unscheduled jobs and the objective.
3. `POST /schedules/{id}/apply` schedules each order with its technicians. It is refused if any order changed since planning (stale) or if the proposal has violations.

**Status:** IMPLEMENTED_AND_TESTED (`test_app_planning.py`). The choice of policy follows PD-09.

## W7. Do the work and record what was found

**Actor:** technician.
1. Start the order: `transitions` with `start`.
2. Complete it: `POST /work-orders/{id}/complete` with the outcome — what was found (`findings_code`), whether a failure is confirmed, root cause, actions taken, parts used, downtime, return to service, notes (`DATA_CONTRACTS.md` §3).
3. Contradictions are flagged for review rather than refused, for example "no fault found" together with a replaced part.
4. Completing maintenance clears a latched risk (`maintenance_completed`).
5. `GET /work-orders/missing-outcomes` lists completed orders without an outcome, for the planner to chase.

**Status:** IMPLEMENTED_AND_TESTED.

## W8. Investigate a decision afterwards

**Actor:** reliability engineer or admin.
1. `GET /audit/{entity}/{id}` gives the full history of an asset, assessment, work order, schedule run or model.
2. `GET /audit/verify` and `admin verify-audit` with the backup's anchor prove the trail has not been edited or truncated.
3. Each assessment carries its model checksum, policy SHA-256 and input window, so the result can be reproduced.

**Status:** IMPLEMENTED_AND_TESTED (`test_app_foundation.py`, `test_app_admin.py`).

## W9. Recover from a failure

**Actor:** admin.
- Back up: `admin backup --to …`. Restore to a new path: `admin restore --from …`. Then verify the audit chain against the anchor.
- If a model misbehaves, roll it back: `POST /models/rollback`.

**Status:** IMPLEMENTED_AND_TESTED; full procedure in `OPERATIONS_RUNBOOK.md` (Phase 7).
