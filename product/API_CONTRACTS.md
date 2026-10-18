# API contracts (REST, version 1)

- **Base path:** `/api/v1`.
- **Implementation:** `src/sentinelloop/app/api.py`.
- **Machine-readable schema:** `product/evidence/api/openapi.json`, generated from the running application. The interactive docs are at `/api/v1/docs`.
- **Status:** IMPLEMENTED_AND_TESTED (`tests/test_app_api.py`, 19 tests). Not penetration-tested. Integration endpoints for an external CMMS are Phase 6 (`INTEGRATION_GUIDE.md`).

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
| Limits | request body ≤ 10 MiB, counted while it streams, so chunked uploads are capped too. Rate limit: token bucket of 120 requests with refill 2/s per authenticated user, or per client address without valid credentials. Buckets are an in-process LRU (documented limitation: one bucket set per API process) |
| Time | timestamps in requests must carry a UTC offset. Responses use ISO-8601 UTC with `Z` |
| Exports | CSV cells starting with `= + - @`, tab or CR are prefixed with `'` (spreadsheet formula injection) |

## 2. Roles and permissions

| permission | roles |
|---|---|
| read | admin, integration, planner, reliability_engineer, technician, viewer |
| assets.write | admin |
| assets.commission | admin, reliability_engineer |
| resources.write | admin, planner |
| ingest | admin, integration |
| assess | admin, integration, planner, reliability_engineer |
| decisions.generate | admin, integration, planner, reliability_engineer |
| workorders.write | admin, integration, planner, reliability_engineer, technician (each transition is further limited by role inside the workflow, e.g. only planners, reliability engineers and admins approve) |
| schedules | admin, planner |
| models.decide | admin, reliability_engineer |
| asset_state.clear | admin, planner, reliability_engineer, technician (dismissal needs a reliability engineer, planner or admin; "maintenance completed" can be recorded by technicians) |
| audit.read | admin, reliability_engineer. The audit history of operational entities (asset, assessment, work order, schedule run, model, ingestion batch) is readable with `read` |
| users.admin | admin |

## 3. Routes

Generated from the application: `product/evidence/api/routes.md`.

| method | path | permission |
|---|---|---|
| GET | `/api/v1/health` | public (liveness) |
| GET | `/api/v1/ready` | public (database, schema currency, approved models, audit-key status) |
| GET | `/api/v1/me` | any authenticated user |
| GET / POST | `/api/v1/assets` | read / assets.write |
| GET / PATCH | `/api/v1/assets/{asset_id}` | read / assets.write (PATCH needs `reason`; identity, type and site cannot change) |
| GET | `/api/v1/asset-types` | read |
| POST | `/api/v1/assets/{asset_id}/baseline` | assets.commission (wind commissioning: model id, healthy period, reason) |
| GET / POST | `/api/v1/sites/{site_id}/technicians` | read / resources.write |
| PUT | `/api/v1/technicians/{tech_id}/shifts` | resources.write |
| GET / POST | `/api/v1/sites/{site_id}/parts` | read / resources.write |
| POST | `/api/v1/sites/{site_id}/parts/{part_id}/deliveries` | resources.write |
| GET / POST | `/api/v1/users` | users.admin (the listing never returns key or password hashes) |
| POST | `/api/v1/users/{user_id}/api-key` | users.admin (the new key is returned once) |
| POST | `/api/v1/users/{user_id}/deactivate` | users.admin (reason required; an admin cannot deactivate their own account) |
| POST | `/api/v1/ingest/readings` | ingest (JSON records, contract v1) |
| POST | `/api/v1/ingest/csv?source=…[&default_tz=…][&wide_units=…]` | ingest (long or wide CSV body) |
| GET | `/api/v1/ingest/batches/{batch_id}` | read |
| GET | `/api/v1/ingest/staleness?max_age_h=…` | read |
| POST | `/api/v1/assets/{asset_id}/assess` | assess (optional `as_of`) |
| GET | `/api/v1/assets/{asset_id}/assessment` | read (latest) |
| POST | `/api/v1/assets/{asset_id}/clear-risk` | asset_state.clear (`event`: dismissed or maintenance_completed; `reason`) |
| POST | `/api/v1/decisions/generate[?site_id=…]` | decisions.generate (creates or escalates orders that need approval; never executes work) |
| GET | `/api/v1/work-orders[?state=…&asset_id=…]` | read |
| GET | `/api/v1/work-orders/missing-outcomes` | read |
| GET | `/api/v1/work-orders/{wo_id}`, `…/history` | read |
| POST | `/api/v1/work-orders` | workorders.write (Idempotency-Key required) |
| POST | `/api/v1/work-orders/{wo_id}/transitions` | workorders.write (`action`, `reason`, `data`, `expected_version`) |
| POST | `/api/v1/work-orders/{wo_id}/complete` | workorders.write (outcome record) |
| POST | `/api/v1/schedules` | schedules (stores a proposal; changes nothing) |
| GET | `/api/v1/schedules/{run_id}` | read |
| POST | `/api/v1/schedules/{run_id}/apply` | schedules (refused if the proposal has violations or is stale; idempotent) |
| GET | `/api/v1/models` | read |
| POST | `/api/v1/models/{model_id}/decision` | models.decide (`approved` or `rejected`, reason) |
| POST | `/api/v1/models/rollback` | models.decide |
| GET | `/api/v1/audit/verify[?anchor_seq=…&anchor_hash=…]`, `/api/v1/audit/anchor` | audit.read |
| GET | `/api/v1/audit/{entity}/{entity_id}` | read for operational entities, audit.read otherwise |
| GET | `/api/v1/export/work-orders.csv` | read |

## 4. Example: from reading to approved work order

```
POST /api/v1/ingest/readings                 (integration key)
  {"source": "scada-export", "records": [{"asset": "WT03", "timestamp": "2026-02-07T10:00:00Z",
    "signal": "gearbox_bearing_temp", "value": 81.4, "unit": "degC"}, ...]}
→ 200 {"batch_id": "...", "status": "accepted", "rows_accepted": ..., "rows_rejected": 0, "errors": []}

POST /api/v1/assets/WT03/assess              → 200 {"health_state": "INSPECTION_RECOMMENDED", "risk": {}, "rul_point": null,
                                                   "top_deviations": [["gearbox_bearing_temp", 3.2], ...], "asset_state": [...]}
POST /api/v1/decisions/generate              → 200 [{"asset_id": "WT03", "action": "created", "wo_id": "WO-...", "priority_class": "P2"}]
POST /api/v1/work-orders/WO-.../transitions  (planner)  {"action": "approve", "expected_version": 2}
```

## 5. Not in v1 (PLANNED)

- Pagination on list endpoints (the lists are unbounded today; acceptable at one-site scale, a known limitation).
- SSO/OIDC; password login for the operator console uses `security.verify_password`, not an API route.
- Webhook subscriptions and the CMMS outbox (Phase 6).
- A correction endpoint for stored readings.
