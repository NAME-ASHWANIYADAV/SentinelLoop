# API contracts (REST, version 1)

- **Base path:** `/api/v1`.
- **Implementation:** `src/sentinelloop/app/api.py`.
- **Machine-readable schema:** `product/evidence/api/openapi.json` (46 paths) and `product/evidence/api/routes.md` (53 method and path pairs, each with the permission it checks). Both were regenerated on 2026-10-18 from `create_app` on a fresh temporary database, without starting a server. The interactive docs are at `/api/v1/docs`.
- **Status:** IMPLEMENTED_AND_TESTED (`tests/test_app_api.py`, 20 test functions; route behaviour also in `tests/test_app_remediation.py` and `tests/test_app_remediation_security.py`). Not penetration-tested.
  - `assess-range` has no automated test yet.
  - The `reprioritise` and `requeue` routes are covered only by the authentication check; the services behind them are tested.
  - The integration routes are tested against a contract test double only. Real Odoo has NOT been run (`INTEGRATION_GUIDE.md`).

## 1. Conventions

| topic | contract |
|---|---|
| Authentication | `Authorization: Bearer slk_…` or `X-API-Key: slk_…`. Keys are random 256-bit tokens, shown once and stored only as SHA-256. Every route except `health` and `ready` (and the docs) returns **401** without a valid key. A test walks all routes to check this (`test_every_route_except_health_and_docs_requires_credentials`) |
| Authorisation | role → permission table below. Each service checks the role again, so a direct call cannot bypass it. Refusal: **403** |
| Versioning | the path carries the major version. Breaking changes need `/api/v2`. Additive fields may appear within v1; clients must ignore unknown fields |
| Errors | JSON `{"error": "...", "request_id": "..."}`, never with a stack trace. 400 missing header; 401; 403; 404 unknown object; 409 conflict (state, version, idempotency); 413 body too large; 422 validation; 429 rate limited (with `Retry-After`); 500 internal (quote the request id) |
| Request id | `X-Request-ID` is echoed if sent and generated otherwise. It is included in every log line and error |
| Idempotency | `POST /work-orders` **requires** an `Idempotency-Key`. Transitions and completion accept one. The same key with the same payload returns the original result; the same key with a different payload, or for another action, returns **409** |
| Concurrency | work-order changes accept `expected_version`. A stale version returns **409** |
| Limits | request body ≤ 10 MiB, counted while it streams, so chunked uploads are capped too. Ingestion: at most 200,000 readings per request (JSON records; CSV rows, or rows × signal columns for a wide CSV); CSV is parsed off the event loop. Rate limit: token bucket of 120 requests with refill 2/s per authenticated user, or per client address without valid credentials. Only the exact paths `/api/v1/health` and `/api/v1/ready` are exempt. Buckets are an in-process LRU (documented limitation: one bucket set per API process) |
| Time | timestamps in requests must carry a UTC offset. Responses use ISO-8601 UTC with `Z` |
| Assessment instants | `as_of` is optional (PD-17).<br>• Without it the instant is now, or the asset's latest reading when the asset type's policy says `assess_at: latest_reading` (and always for cycle-indexed C-MAPSS replays).<br>• More than 5 minutes in the future: **422**.<br>• At or before the last applied instant: stored as a replay. The response has `applied_to_state: false` and a "historical replay" reason, the live state is unchanged, and `GET …/assessment` ignores it.<br>• To back-fill a periodic export, use `assess-range`, which works oldest first |
| Asset labels | `state` is a list.<br>• The first entry is the health state, or NOT_ASSESSED (never assessed), or AWAITING_ASSESSMENT (a latch was cleared and the asset has not been assessed since).<br>• It may be followed by INSPECTION_PENDING (a latched inspection hidden by a data, scope or model problem) and HUMAN_APPROVAL_REQUIRED.<br>• In asset listings (`/assets`, `/assets/{id}`) ASSESSMENT_OVERDUE is appended when the last applied assessment is older than `max_assessment_age_hours` (6 h by default, 26 h for wind). The same listings carry `last_assessed_at` and `last_assessment_instant`.<br>• The `asset_state` of an `assess` response and the `state` of a `clear-risk` response carry the same labels, without ASSESSMENT_OVERDUE |
| Exports | CSV cells starting with `= + - @`, tab or CR are prefixed with `'` (spreadsheet formula injection) |

## 2. Roles and permissions

| permission | roles |
|---|---|
| read | admin, integration, planner, reliability_engineer, technician, viewer |
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
| audit.read | admin, reliability_engineer. The audit history of operational entities (asset, assessment, work order, schedule run, model, ingestion batch) is readable with `read` |
| users.admin | admin |
| integrations.read | admin, integration, planner, reliability_engineer (target config is shown to admins only) |
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
| GET / POST | `/api/v1/integrations` | integrations.read / integrations.manage. A new target starts in shadow mode; another mode needs a written reason. Secrets in its config are refused |
| POST | `/api/v1/integrations/{target_id}/mode` | integrations.manage (`shadow` or `draft_requests`; reason required) |
| POST | `/api/v1/integrations/{target_id}/dispatch` | integrations.dispatch (in shadow mode: records what would be sent, no external call) |
| GET | `/api/v1/integrations/{target_id}/items[?status=…]` | integrations.read |
| POST | `/api/v1/integrations/{target_id}/items/{wo_id}/requeue` | integrations.manage (dead letters only; reason required) |
| POST | `/api/v1/ingest/readings` | ingest (JSON records, contract v1) |
| POST | `/api/v1/ingest/csv?source=…[&default_tz=…][&wide_units=…]` | ingest (long or wide CSV body) |
| GET | `/api/v1/ingest/batches/{batch_id}` | read |
| GET | `/api/v1/ingest/staleness?max_age_h=…[&site_id=…]` | read |
| POST | `/api/v1/assets/{asset_id}/assess` | assess (optional `as_of`; rules in §1) |
| POST | `/api/v1/assets/{asset_id}/assess-range` | assess. Body: `start`, `end` and `step_minutes` (1–1440, default 60); at most 2,000 steps, assessed oldest first. Returns the count per state, how many were applied and the asset's labels |
| GET | `/api/v1/assets/{asset_id}/assessment` | read (the latest applied assessment; replays are ignored) |
| POST | `/api/v1/assets/{asset_id}/clear-risk` | asset_state.clear (`event` must be `dismissed`, with a `reason`). `maintenance_completed` is refused with 422, because maintenance clears a latch only by completing its work order. 409 when nothing is latched |
| POST | `/api/v1/decisions/generate[?site_id=…]` | decisions.generate. First returns to approval any deferred orders whose date has passed. Then creates, escalates or holds back (after a reasoned rejection) the orders that need approval. Never executes work |
| GET | `/api/v1/work-orders[?state=…&asset_id=…]` | read |
| GET | `/api/v1/work-orders/missing-outcomes` | read |
| GET | `/api/v1/work-orders/{wo_id}`, `…/history` | read |
| POST | `/api/v1/work-orders` | workorders.write (Idempotency-Key required; the order starts as DRAFT) |
| POST | `/api/v1/work-orders/{wo_id}/transitions` | workorders.write (`action`, `reason`, `data`, `expected_version`). `defer` needs `data.until`; `hand_back` needs a reason and clears the schedule |
| POST | `/api/v1/work-orders/{wo_id}/reprioritise` | workorders.write; the workflow allows planners, reliability engineers and admins. Body: `priority_class`, `reason`, optional `due_by`. Open orders only (DRAFT, PENDING_APPROVAL, APPROVED, SCHEDULED, DEFERRED); a deferred order raised to P1 returns to PENDING_APPROVAL |
| POST | `/api/v1/work-orders/{wo_id}/complete` | workorders.write (outcome record). Clears a latched risk only under the PD-16 rule (`USER_WORKFLOWS.md` W7) |
| POST | `/api/v1/schedules` | schedules (stores a proposal; changes nothing) |
| GET | `/api/v1/schedules/{run_id}` | read |
| POST | `/api/v1/schedules/{run_id}/apply` | schedules (refused if the proposal has violations or is stale; idempotent) |
| GET | `/api/v1/models` | read |
| POST | `/api/v1/models/{model_id}/decision` | models.decide (`approved` or `rejected`, reason) |
| POST | `/api/v1/models/rollback` | models.decide |
| GET | `/api/v1/audit/verify[?anchor_seq=…&anchor_hash=…]`, `/api/v1/audit/anchor` | audit.read. Without anchor parameters, verify checks only internal consistency and cannot detect truncation |
| GET | `/api/v1/audit/{entity}/{entity_id}` | read for operational entities, audit.read otherwise |
| GET | `/api/v1/export/work-orders.csv` | read |

## 4. Example: from reading to approved work order

```
POST /api/v1/ingest/readings                 (integration key)
  {"source": "scada-export", "records": [{"asset": "WT03", "timestamp": "2026-02-07T10:00:00Z",
    "signal": "gearbox_bearing_temp", "value": 81.4, "unit": "degC"}, ...]}
→ 200 {"batch_id": "...", "status": "accepted", "rows_accepted": ..., "rows_rejected": 0, "errors": []}

POST /api/v1/assets/WT03/assess              → 200 {"health_state": "INSPECTION_RECOMMENDED", "risk": {}, "rul_point": null,
                                                   "top_deviations": [["gearbox_bearing_temp", 3.2], ...],
                                                   "applied_to_state": true, "asset_state": [...]}
POST /api/v1/decisions/generate              → 200 [{"asset_id": "WT03", "action": "created", "wo_id": "WO-...", "priority_class": "P2"}]
POST /api/v1/work-orders/WO-.../transitions  (planner)  {"action": "approve", "expected_version": 1}
```

## 5. Not in v1 (PLANNED)

- Pagination on list endpoints (the lists are unbounded today; acceptable at one-site scale, a known limitation).
- SSO/OIDC and password login. The console signs in with the user's own API key. `security.set_password` and `verify_password` exist in the library, but no route or console page uses them.
- Routes to create sites and asset types (library only, KNOWN_LIMITATIONS P4) and to register model bundles (`modelreg.register`, library only).
- Self-service webhook subscriptions. Outbound signed webhooks exist only as integration targets that an admin registers (§3).
- Per-site role scoping: roles apply to every site (KNOWN_LIMITATIONS P11).
- A correction endpoint for stored readings.
