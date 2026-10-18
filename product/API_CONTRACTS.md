# API contracts (REST, version 1)

- **Base path:** `/api/v1`.
- **Implementation:** `src/sentinelloop/app/api.py`.
- **Machine-readable schema:** `product/evidence/api/openapi.json` (46 paths) and `product/evidence/api/routes.md` (53 method and path pairs, each with the permission it checks). Both were regenerated on 2026-10-18, after the re-review fixes, from `create_app` on a fresh temporary database, without starting a server (`product/scripts/gen_api_evidence.py`). The interactive docs are at `/api/v1/docs`.
- **Status:** IMPLEMENTED_AND_TESTED (`tests/test_app_api.py`, 20 test functions; route behaviour also in `tests/test_app_remediation.py`, `tests/test_app_remediation_security.py`, `tests/test_app_rereview_api.py` and `tests/test_app_rereview_wiring.py`). Not penetration-tested.
  - `assess-range` is tested through the API for its cost, its concurrency limits, whole-range validation and tags (`test_app_rereview_api.py`), and in the library (`test_app_rereview_health.py`).
  - The `reprioritise` route is tested for the version check and for keeping the risk score (`test_app_rereview_wiring.py::test_the_reprioritise_route_refuses_a_stale_version`, `test_app_rereview_decision.py::test_a_manual_reprioritisation_keeps_the_score_and_records_only_what_changed`).
  - The `requeue` route is covered only by the authentication check; the service behind it is tested.
  - The integration routes are tested against a contract test double only. Real Odoo has NOT been run (`INTEGRATION_GUIDE.md`).

## 1. Conventions

| topic | contract |
|---|---|
| Authentication | `Authorization: Bearer slk_…` or `X-API-Key: slk_…`. Keys are random 256-bit tokens, shown once and stored only as SHA-256. Every route except `health` and `ready` (and the docs) returns **401** without a valid key. A test walks all routes to check this (`test_every_route_except_health_and_docs_requires_credentials`) |
| Authorisation | role → permission table below. Each service checks the role again, so a direct call cannot bypass it. Refusal: **403** |
| Versioning | the path carries the major version. Breaking changes need `/api/v2`. Additive fields may appear within v1; clients must ignore unknown fields |
| Errors | JSON `{"error": "...", "request_id": "..."}`, never with a stack trace. 400 missing header, or a reserved idempotency-key prefix; 401; 403; 404 unknown object (the API also maps to 404 any service error whose message starts "unknown " or has " unknown " in its first 40 characters, such as an unknown integration config key, kind or mode); 409 conflict (state, version, idempotency); 413 body too large; 422 validation; 429 rate limited or an `assess-range` over its concurrency limit (with `Retry-After`); 500 internal (quote the request id) |
| Request id | `X-Request-ID` is echoed if sent and generated otherwise. It is included in every log line and error |
| Idempotency | `POST /work-orders` **requires** an `Idempotency-Key`. Transitions and completion accept one. The same key with the same payload returns the original result; the same key with a different payload, or for another action, returns **409**. Clients may not use keys starting `rec:`, `reactivate:` or `apply:`, which the platform uses for its own recommendations, deferral reactivations and schedule applications: **400** (`test_clients_cannot_use_the_engines_reserved_idempotency_keys`) |
| Concurrency | work-order changes, including `reprioritise`, accept `expected_version`. A stale version returns **409** |
| Limits | request body ≤ 10 MiB, counted while it streams, so chunked uploads are capped too. Ingestion: at most 200,000 readings per request (JSON records; CSV rows, or rows × signal columns for a wide CSV); CSV is parsed off the event loop. Rate limit: token bucket of 120 requests with refill 2/s per authenticated user, or per client address without valid credentials (`admin serve --rate-limit CAPACITY,REFILL`). `assess-range` pays one token per 10 steps (§3). Only the exact paths `/api/v1/health` and `/api/v1/ready` are exempt; `health` runs on the event loop, so it answers while worker threads are busy. Buckets are an in-process LRU (documented limitation: one bucket set per API process) |
| Time | timestamps in requests must carry a UTC offset. Responses use ISO-8601 UTC with `Z` |
| Assessment instants | `as_of` is optional (PD-17, PD-28).<br>• Without it the instant is now, or the asset's latest reading when the asset type's policy says `assess_at: latest_reading` (and always for cycle-indexed C-MAPSS replays).<br>• More than 5 minutes in the future, earlier than 2000-01-01T00:00Z, or more than 5 minutes before the asset's first stored reading: **422**, nothing stored.<br>• At or before the last applied instant: stored as a replay. The response has `applied_to_state: false` and a "historical replay" reason, and `GET …/assessment` ignores it. A replay never lowers a latch or moves the live state, but an URGENT_REVIEW or INSPECTION_RECOMMENDED replay above the latched risk raises the latch, starting at the wall-clock time: the response then has `latch_escalated: true`, and the asset's audit history records `asset_state.escalated_by_replay`. It raises nothing when an earlier assessment for the same instant already had that finding (a person has cleared it since).<br>• To back-fill a periodic export, use `assess-range`, which works oldest first |
| Asset labels | `state` is a list.<br>• The first entry is the health state, or NOT_ASSESSED (never assessed), or AWAITING_ASSESSMENT (a latch was cleared and the asset has not been assessed since).<br>• It may be followed by INSPECTION_PENDING (a latched inspection hidden by a data, scope or model problem) and HUMAN_APPROVAL_REQUIRED.<br>• In asset listings (`/assets`, `/assets/{id}`) ASSESSMENT_OVERDUE is appended when the last applied assessment is older than `max_assessment_age_hours` (6 h by default, 26 h for wind), or when the state shows a result but no assessment time is on record (for example a state row restored without its assessments; migration 0008). The same listings carry `last_assessed_at` and `last_assessment_instant`.<br>• The `asset_state` of an `assess` response and the `state` of a `clear-risk` response carry the same labels, without ASSESSMENT_OVERDUE |
| Exports | CSV cells starting with `= + - @`, tab or CR are prefixed with `'` (spreadsheet formula injection) |

## 2. Roles and permissions

| permission | roles |
|---|---|
| read | admin, integration, planner, reliability_engineer, technician, viewer. A model's `artifact_path` (a server path) is shown to admins only |
| assets.write | admin |
| assets.commission | admin, reliability_engineer |
| resources.read | admin, planner, reliability_engineer (technician names and shifts are personal data) |
| resources.write | admin, planner |
| ingest | admin, integration |
| assess | admin, integration, planner, reliability_engineer |
| decisions.generate | admin, integration, planner, reliability_engineer |
| workorders.write | admin, integration, planner, reliability_engineer, technician. Each action is further limited by role inside the workflow:<br>• approve, defer, reject, cancel, close and re-prioritise: planners, reliability engineers and admins;<br>• schedule and unschedule: planners and admins;<br>• start and hand back: technicians, planners and admins;<br>• complete: technicians, planners, admins and the integration role (not reliability engineers).<br>A completion by the integration role never clears a latch |
| schedules | admin, planner |
| models.decide | admin, reliability_engineer |
| asset_state.clear | admin, planner, reliability_engineer (reasoned dismissals only; maintenance clears a latch through its work order) |
| audit.read | admin, reliability_engineer. The audit history of operational entities (asset, assessment, work order, schedule run, model, ingestion batch) is readable with `read`. In `integration.*` events the CMMS host (`base_url`) and the error text are shown to admins only, whatever the route |
| users.admin | admin |
| integrations.read | admin, integration, planner, reliability_engineer. A target's config and `base_url`, and the error text of failed items, are shown to admins only (`test_app_rereview_api.py`) |
| integrations.manage | admin |
| integrations.dispatch | admin, integration |

## 3. Routes

Generated from the application: `product/evidence/api/routes.md`.

| method | path | permission |
|---|---|---|
| GET | `/api/v1/health` | public (liveness) |
| GET | `/api/v1/ready` | public. Reports the database, schema version and whether it is current, approved models and audit-key status. It also reports `decision_config`: "site-configured", or "placeholder defaults …" when the server was started without `serve --decision-config` (PD-24) |
| GET | `/api/v1/me` | any authenticated user |
| GET / POST | `/api/v1/assets` | read (with labels and `last_assessed_at`) / assets.write |
| GET / PATCH | `/api/v1/assets/{asset_id}` | read (adds `state_notes`) / assets.write (PATCH needs `reason`; identity, type and site cannot change) |
| GET | `/api/v1/sites` | read (site id, name, time zone) |
| GET | `/api/v1/asset-types` | read |
| POST | `/api/v1/assets/{asset_id}/baseline` | assets.commission (wind commissioning: model id, healthy period, reason) |
| GET / POST | `/api/v1/sites/{site_id}/technicians` | resources.read / resources.write |
| PUT | `/api/v1/technicians/{tech_id}/shifts` | resources.write |
| GET / POST | `/api/v1/sites/{site_id}/parts` | read / resources.write |
| POST | `/api/v1/sites/{site_id}/parts/{part_id}/deliveries` | resources.write |
| GET / POST | `/api/v1/users` | users.admin (the listing never returns key or password hashes) |
| POST | `/api/v1/users/{user_id}/api-key` | users.admin (the new key is returned once) |
| POST | `/api/v1/users/{user_id}/deactivate` | users.admin (reason required; an admin cannot deactivate their own account) |
| GET / POST | `/api/v1/integrations` | integrations.read (non-admins see neither `config` nor `base_url`) / integrations.manage. A new target starts in shadow mode; another mode needs a written reason. Secrets in its config are refused; the URL and config values (`timeout_s` above 0 and at most 120, `max_attempts` 1–100, the database name, `SENTINELLOOP_CRED_*` variable names) are checked at registration (422; also 422 for a `target_id` that exists). An unknown config key, target kind or mode gives **404**, not 422, because of that error mapping (§1, Errors) |
| POST | `/api/v1/integrations/{target_id}/mode` | integrations.manage (`shadow` or `draft_requests`; reason required) |
| POST | `/api/v1/integrations/{target_id}/dispatch` | integrations.dispatch (in shadow mode: records what would be sent, no external call). Returns `target_id`, `mode`, the counts `considered`, `shadow`, `sent`, `retry`, `dead` and `skipped`, then `busy` (true when another dispatch of the target holds its lease: nothing was sent) and `stopped`: why the run stopped or sent nothing (another dispatch held the lease, with `considered` reset to 0; the lease lapsed; or the mode changed or the target was disabled during the run), or null |
| GET | `/api/v1/integrations/{target_id}/items[?status=…]` | integrations.read (non-admins see that an item failed, not its error text) |
| POST | `/api/v1/integrations/{target_id}/items/{wo_id}/requeue` | integrations.manage (dead letters only; reason required) |
| POST | `/api/v1/ingest/readings` | ingest (JSON records, contract v1; `default_tz`, when given, must be a known IANA time zone: 422 otherwise, nothing recorded) |
| POST | `/api/v1/ingest/csv?source=…[&default_tz=…][&wide_units=…]` | ingest (long or wide CSV body; `default_tz` as above, `wide_units` a JSON object of column → unit: 422 otherwise) |
| GET | `/api/v1/ingest/batches/{batch_id}` | read |
| GET | `/api/v1/ingest/staleness?max_age_h=…[&site_id=…]` | read (`max_age_h` above 0 and at most 8,760; default 6) |
| POST | `/api/v1/assets/{asset_id}/assess` | assess (optional `as_of`; rules in §1). The response carries `applied_to_state` and `latch_escalated` |
| POST | `/api/v1/assets/{asset_id}/assess-range` | assess. Body: `start`, `end` and `step_minutes` (1–1440, default 60). The asset may be named by id or tag.<br>• **Cost:** one rate-limit token per 10 steps (at least one). With the shipped bucket of 120 that is at most 1,200 steps per call, from a full bucket; a range that costs more than the bucket holds is refused with 422 ("split the range"), and one the bucket cannot pay now gets 429 with `Retry-After`. The library limit is 2,000 steps (`health.MAX_RANGE_STEPS`).<br>• **Concurrency:** one running range per user and two per server; another gets 429 with `Retry-After`, without being queued.<br>• **All or nothing:** every instant is checked (§1) before any is assessed, so a refused range stores nothing.<br>• Steps are assessed oldest first. Returns `assessments`, `applied`, `replays_escalated` (replays that raised the latch, not counted in `applied`), the count per state and the asset's labels |
| GET | `/api/v1/assets/{asset_id}/assessment` | read (the latest applied assessment; replays are ignored) |
| POST | `/api/v1/assets/{asset_id}/clear-risk` | asset_state.clear (`event` must be `dismissed`, with a `reason`). `maintenance_completed` is refused with 422, because maintenance clears a latch only by completing its work order. 409 when nothing is latched |
| POST | `/api/v1/decisions/generate[?site_id=…]` | decisions.generate. First returns to approval any deferred orders whose date has passed (one failure is reported as `error` and the others still come back). Then, for each recommended job, it creates an order, escalates or links an open one, or holds it back after a reasoned rejection (`USER_WORKFLOWS.md` W5). Each result has an `action`: `reactivated`, `created`, `escalated`, `linked`, `unchanged`, `already_decided`, `suppressed` or `error`. Never executes work |
| GET | `/api/v1/work-orders[?state=…&asset_id=…]` | read |
| GET | `/api/v1/work-orders/missing-outcomes` | read |
| GET | `/api/v1/work-orders/{wo_id}`, `…/history` | read |
| POST | `/api/v1/work-orders` | workorders.write (Idempotency-Key required; the order starts as DRAFT) |
| POST | `/api/v1/work-orders/{wo_id}/transitions` | workorders.write (`action`, `reason`, `data`, `expected_version`). `defer` needs `data.until`; `hand_back` needs a reason and clears the schedule |
| POST | `/api/v1/work-orders/{wo_id}/reprioritise` | workorders.write; the workflow allows planners, reliability engineers and admins. Body: `priority_class`, `reason`, optional `due_by` and `expected_version` (409 when stale). Open orders only (DRAFT, PENDING_APPROVAL, APPROVED, SCHEDULED, DEFERRED). The order keeps its risk score, and its due date unless `due_by` is given; the event records only what changed. A deferred order raised to P1 returns to PENDING_APPROVAL, recorded under the caller's role |
| POST | `/api/v1/work-orders/{wo_id}/complete` | workorders.write (outcome record). Clears a latched risk only under the PD-16 rule as refined by PD-28 (`USER_WORKFLOWS.md` W7). The site's configured data and review jobs (`serve --decision-config`) never clear a latch through this route either (`test_the_api_complete_route_applies_the_sites_non_clearing_jobs`) |
| POST | `/api/v1/schedules` | schedules (stores a proposal; changes nothing). `horizon_h` above 0 and at most 336; `slot_h` from 0.25 to 24. `milp` is refused with 422 above 5,000 approved orders at the site × slots: use `risk_greedy`, a shorter horizon or longer slots (KNOWN_LIMITATIONS P14) |
| GET | `/api/v1/schedules/{run_id}` | read |
| POST | `/api/v1/schedules/{run_id}/apply` | schedules (refused if the proposal has violations or is stale; idempotent) |
| GET | `/api/v1/models` | read (`artifact_path` for admins only) |
| POST | `/api/v1/models/{model_id}/decision` | models.decide (`approved` or `rejected`, reason; `artifact_path` in the response for admins only) |
| POST | `/api/v1/models/rollback` | models.decide (`artifact_path` in the response for admins only) |
| GET | `/api/v1/audit/verify[?anchor_seq=…&anchor_hash=…]`, `/api/v1/audit/anchor` | audit.read. Verify returns `n`, `valid`, `first_bad_seq`, `reason`, `events_signed_with_dev_key` and `anchor_checked`. Without anchor parameters it checks only internal consistency, cannot detect truncation, and says `anchor_checked: false`. An anchor needs both parameters: `anchor_seq` from 1 to 2^63−1 and `anchor_hash` of 64 lowercase hex characters; a partial or malformed anchor is refused with 422 |
| GET | `/api/v1/audit/{entity}/{entity_id}` | read for operational entities, audit.read otherwise. Integration hosts and error text are withheld from non-admins (§2) |
| GET | `/api/v1/export/work-orders.csv` | read |

## 4. Example: from reading to approved work order

```
POST /api/v1/ingest/readings                 (integration key)
  {"source": "scada-export", "records": [{"asset": "WT03", "timestamp": "2026-02-07T10:00:00Z",
    "signal": "gearbox_bearing_temp", "value": 81.4, "unit": "degC"}, ...]}
→ 200 {"batch_id": "...", "status": "accepted", "rows_accepted": ..., "rows_rejected": 0, "errors": []}

POST /api/v1/assets/WT03/assess              → 200 {"health_state": "INSPECTION_RECOMMENDED", "risk": {}, "rul_point": null,
                                                   "top_deviations": [["gearbox_bearing_temp", 3.2], ...],
                                                   "applied_to_state": true, "latch_escalated": false, "asset_state": [...]}
POST /api/v1/decisions/generate              → 200 [{"asset_id": "WT03", "action": "created", "wo_id": "WO-...", "priority_class": "P2"}]
POST /api/v1/work-orders/WO-.../transitions  (planner)  {"action": "approve", "expected_version": 1}
```

## 5. Not in v1 (PLANNED)

- Pagination on list endpoints (the lists are unbounded today; acceptable at one-site scale, a known limitation).
- SSO/OIDC and password login. The console signs in with the user's own API key. `security.set_password` and `verify_password` exist in the library, but no route or console page uses them.
- Routes to create sites and asset types (library only, KNOWN_LIMITATIONS P4) and to register model bundles (`modelreg.register`, library only).
- Self-service webhook subscriptions. Outbound signed webhooks exist only as integration targets that an admin registers (§3). Their signed body carries no delivery id or version (KNOWN_LIMITATIONS S9).
- A route to update an integration target's config: an admin re-registers it under a new id (KNOWN_LIMITATIONS S11).
- A queued back-fill job for exports longer than one `assess-range` call (KNOWN_LIMITATIONS P13).
- Per-site role scoping: roles apply to every site (KNOWN_LIMITATIONS P11).
- A correction endpoint for stored readings.
