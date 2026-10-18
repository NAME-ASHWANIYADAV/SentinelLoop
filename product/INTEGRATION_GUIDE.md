# Integration guide

How SentinelLoop exchanges data with the systems around it.

| part | status |
|---|---|
| Inbound data (ingestion API) | IMPLEMENTED_AND_TESTED |
| Outbound CMMS connector for Odoo (JSON-2) and signed webhooks | IMPLEMENTED_AND_TESTED against a contract test double |
| Run against a real Odoo Community sandbox | **PENDING: the Odoo image download needs approval** (`sandbox/odoo/`) |
| Connection to a customer CMMS | **none exists** |

Code: `src/sentinelloop/app/integration.py`, migration `0005_integration.sql`. Tests: `tests/test_app_integration.py` (10), `tests/test_app_api.py`, and `tests/test_app_odoo_sandbox.py` (opt-in).

## 1. Principles

1. **Read-only shadow mode is the default.** A new target records exactly what it *would* send and makes no external call. Leaving shadow mode needs an admin and a written reason, and is audited.
2. **Only approved work leaves the system.** Orders in APPROVED, SCHEDULED or IN_PROGRESS are sent. DRAFT and PENDING_APPROVAL orders are never sent. Once a request exists in the CMMS, later local changes are mirrored onto it: a cancelled or rejected order becomes `[SentinelLoop WITHDRAWN] …` with priority lowered, a deferred one `[SentinelLoop DEFERRED until …]`, a completed one `[SentinelLoop COMPLETED]` (tested).
3. **SentinelLoop proposes; the CMMS owns the work.**
   - The connector creates and updates maintenance *requests* marked `[SentinelLoop]`.
   - It writes only `name`, `description`, `priority`, `maintenance_type`, `schedule_date`, `schedule_end`, `duration`, `equipment_id` and `request_date`.
   - It never changes stages, closes, archives or deletes CMMS records.
4. **No secrets in configuration or the database.**
   - The target config names an environment variable (`api_key_env`, `secret_env`). The name must start with `SENTINELLOOP_CRED_`, so a target cannot be pointed at another secret such as the audit key.
   - A config key called `api_key`, `password`, `secret` or `token` is refused.
   - A test scans the database file for the key.
5. **Controlled destinations.** The target host must be listed in `SENTINELLOOP_INTEGRATION_HOSTS`. https is required except for local hosts.

## 2. Inbound: data into SentinelLoop

| source | path | notes |
|---|---|---|
| SCADA / historian exports | `POST /api/v1/ingest/csv` (long or wide CSV) or `/ingest/readings` (JSON) | contract v1 (`DATA_CONTRACTS.md`); an `integration` role key; check `rows_rejected` and the reason codes after every batch |
| Asset master data | `POST /api/v1/assets` (admin) | map the CMMS equipment reference into `asset.config.cmms_equipment_ref` |
| Crews and parts | `/api/v1/sites/{id}/technicians`, `/parts` | planner role |
| OPC UA, MQTT, live historian APIs | PLANNED | today the platform takes exports only; there is no OT network connection by design (`THREAT_MODEL.md` §4) |

## 3. Outbound: CMMS connector

### 3.1 Register a target (admin)

```
POST /api/v1/integrations
{"target_id": "odoo", "kind": "odoo_json2", "base_url": "https://cmms.example.com",
 "config": {"database": "prod", "api_key_env": "SENTINELLOOP_CRED_ODOO", "max_attempts": 8, "timeout_s": 15}}
→ 201 {"mode": "shadow", ...}
```

Kinds:
- `odoo_json2`: Odoo 19/20 JSON-2 API.
- `webhook`: a signed HTTP POST to a URL you control. It suits any system with an inbound HTTP integration.

### 3.2 Dispatch (integration role, e.g. from a cron job every few minutes)

`POST /api/v1/integrations/{id}/dispatch` → counts of `shadow`, `sent`, `retry`, `dead` and `skipped`.

**Delivery is state-based.** Every eligible work order whose version differs from the last delivered version is sent. A failed write therefore never loses an update; the next dispatch carries the current state.

### 3.3 Odoo mapping

| SentinelLoop | Odoo `maintenance.request` |
|---|---|
| `[SentinelLoop] <title>` | `name` |
| explanation (why, due date and rule, P(failure) when it exists), advisory note, marker `[SentinelLoop-Ref:<wo_id>]` | `description` (HTML; every value escaped) |
| P1 / P2 / P3 | `priority` '3' / '2' / '1' |
| condition-based work | `maintenance_type` = `preventive` |
| scheduled start / end (UTC) | `schedule_date` / `schedule_end` (`YYYY-MM-DD HH:MM:SS`, UTC) |
| duration (h) | `duration` |
| `asset.config.cmms_equipment_ref` → `maintenance.equipment.serial_no` lookup | `equipment_id` |

**Idempotency.**
- The external id is stored per (target, work order).
- If that mapping is lost, the delimited marker in the description finds the existing request, so no duplicate is created. Only a request whose name starts with `[SentinelLoop]` and whose description holds the exact marker is adopted; two candidates make a dead letter for a person to resolve. Both cases are tested.
- Each JSON-2 call runs in its own Odoo transaction (Odoo documentation), so a create is never half-applied.

### 3.4 Failures

| failure | handling |
|---|---|
| timeout, connection error, HTTP 408/429/5xx | `retry`, with exponential backoff (30 s × 2ⁿ, capped at 1 h, ±20% deterministic jitter) |
| other HTTP 4xx (401 bad key, 403, 422 invalid data), missing credential variable | `dead`, with the error kept |
| `max_attempts` (default 8) exhausted | `dead` |

- **Dead letters** wait for an admin: `POST /api/v1/integrations/{id}/items/{wo_id}/requeue` with a reason (audited).
- **Stored error text** keeps the HTTP status and Odoo's `message`. It never keeps Odoo's `debug` traceback or the credential; both are tested.

### 3.5 Webhooks

**Headers.**
- `X-SentinelLoop-Timestamp`: Unix seconds.
- `X-SentinelLoop-Signature`: `sha256=<hex HMAC-SHA256(secret, "<timestamp>." + body)>`.
- The secret must be at least 32 characters, from `secret_env`.

**Receivers** verify the signature in constant time and reject timestamps outside ±300 s. `integration.verify_webhook` is the reference implementation; tests cover tampering, the wrong key and replay.

## 4. Going from shadow to live: checklist

1. Run in shadow for an agreed period. Compare the recorded payloads (`GET /integrations/{id}/items`) with what planners actually created in the CMMS.
2. Agree with the CMMS owner which fields SentinelLoop may write. Use a dedicated least-privilege CMMS user for its API key, and rotate keys; Odoo keys last at most three months per Odoo's documentation (R5).
3. Admin: `POST /integrations/{id}/mode` with `{"mode": "draft_requests", "reason": "<who agreed, when>"}`.
4. Watch `retry` and `dead` counts. Every dead letter is reviewed by a person.

## 5. Evidence

| claim | evidence | status |
|---|---|---|
| requests conform to the documented JSON-2 shape | the fake Odoo asserts path, headers and body for every call | IMPLEMENTED_AND_TESTED (test double) |
| shadow makes no external call | `test_targets_default_to_read_only_shadow_mode_and_shadow_never_calls_the_cmms` | IMPLEMENTED_AND_TESTED |
| idempotent upsert, no duplicates after a lost mapping | `test_draft_mode_creates_once_updates_on_change_and_never_duplicates` | IMPLEMENTED_AND_TESTED |
| retries, backoff, dead letters, requeue | `test_transient_failures_…`, `test_permanent_errors_…`, `test_retries_stop_after_the_attempt_limit` | IMPLEMENTED_AND_TESTED |
| works against real Odoo software | `tests/test_app_odoo_sandbox.py` | **NOT YET RUN** (needs the image download) |
| works with a customer's CMMS | — | BLOCKED (no customer) |
