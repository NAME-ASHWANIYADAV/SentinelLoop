# Integration guide

How SentinelLoop exchanges data with the systems around it.

| part | status |
|---|---|
| Inbound data (ingestion API) | IMPLEMENTED_AND_TESTED |
| Outbound CMMS connector for Odoo (JSON-2) and signed webhooks | IMPLEMENTED_AND_TESTED **against a contract test double only** |
| Run against a real Odoo Community sandbox | **NOT RUN: the Odoo image download awaits approval** (`sandbox/odoo/`, PD-26). Compatibility with real Odoo is unproven (KNOWN_LIMITATIONS S1) |
| Connection to a customer CMMS | **none exists** |

Code: `src/sentinelloop/app/integration.py`, migration `0005_integration.sql`. Tests: `tests/test_app_integration.py` (13), the CMMS tests in `tests/test_app_remediation_security.py` (Phase 9 review fixes), `tests/test_app_api.py`, and `tests/test_app_odoo_sandbox.py` (opt-in; skipped unless a sandbox is configured, so far never run).

## 1. Principles

1. **Read-only shadow mode is the default.** A new target records exactly what it *would* send and makes no external call. Leaving shadow mode needs an admin and a written reason, and is audited.
2. **Only approved work leaves the system.** Orders in APPROVED, SCHEDULED or IN_PROGRESS are sent. DRAFT and PENDING_APPROVAL orders are never sent.
3. **Later changes are mirrored as text, never as CMMS actions** (PD-20). Once a request exists for an order, a later local state is written onto that same request:

   | local state | request name | priority | description |
   |---|---|---|---|
   | CANCELLED or REJECTED | `[SentinelLoop WITHDRAWN] <title>` | lowered to '0' | prefixed "SentinelLoop: this recommendation is now cancelled/rejected (withdrawn). Do not act on it unless your own process says so." |
   | DEFERRED | `[SentinelLoop DEFERRED until <date>] <title>` | lowered to '0' | the same prefix, for deferred |
   | COMPLETED or CLOSED | `[SentinelLoop COMPLETED] <title>` | unchanged | the same prefix, for completed |

   - Tested: cancellation and deferral (`test_cancelled_or_deferred_orders_are_marked_in_the_cmms`): the test checks the name, the description and that no second request is created, not the priority. The priority column is code only (`integration.odoo_payload`). Rejection and completion use the same code path (`integration.FOLLOW_STATES`, `odoo_payload`) but have no test of their own.
   - Mirroring only follows an order that already has a sync record for the target (live or shadow); an order that was never dispatched to it creates nothing.
   - A deferred order that comes back for approval (PENDING_APPROVAL) is not sent again until it is approved, so meanwhile the CMMS request keeps its DEFERRED text.
4. **SentinelLoop proposes; the CMMS owns the work.**
   - The connector creates and updates maintenance *requests* marked `[SentinelLoop]`.
   - It writes only the fields in an explicit allowlist (`ODOO_WRITABLE_FIELDS`: `name`, `description`, `priority`, `maintenance_type`, `schedule_date`, `schedule_end`, `duration`, `equipment_id`, `request_date`). Any other field raises an error; this is a real check, not an `assert` (`test_payload_fields_are_filtered_explicitly_not_by_assert`). `request_date` is allowed but not currently written.
   - It never changes stages, closes, archives or deletes CMMS records.
5. **No secrets in configuration or the database.**
   - The target config names an environment variable (`api_key_env` for Odoo, `secret_env` for a webhook). The name must start with `SENTINELLOOP_CRED_`, followed by letters, digits and `_`, so a target cannot be pointed at another secret such as the audit key. The name is checked at registration and again at every dispatch outside shadow mode.
   - Config keys are allowlisted: `database`, `api_key_env`, `secret_env`, `timeout_s`, `max_attempts`. Any other key is refused, and a key called `api_key`, `password`, `secret` or `token` is refused with a pointer to the environment variable (`test_unknown_config_keys_are_refused`).
   - A target's config is shown only to admins: `GET /integrations` drops it for every other role (`test_integration_config_is_shown_to_admins_only`).
   - A test scans the database file for the key.
6. **Controlled destinations.**
   - The target URL must be `http` or `https`; `https` is required except for local hosts (`localhost`, `127.0.0.1`, `::1`, `*.localhost`, `*.test`).
   - It may not carry credentials (`user:password@`), a query string or a fragment (`test_urls_with_credentials_queries_or_fragments_are_refused`).
   - Its host must be listed in `SENTINELLOOP_INTEGRATION_HOSTS`. The URL is checked at registration and **again at every dispatch outside shadow mode**: removing a host from the list stops delivery to it, and its items become dead letters (`test_the_host_allowlist_is_checked_again_at_dispatch`).
   - The allowlist matches host names, not ports: any port on an allowed host is accepted.

## 2. Inbound: data into SentinelLoop

| source | path | notes |
|---|---|---|
| SCADA / historian exports | `POST /api/v1/ingest/csv` (long or wide CSV, at most 200,000 readings per batch) or `/ingest/readings` (JSON) | contract v1 (`DATA_CONTRACTS.md`); an `integration` role key; check `rows_rejected` and the reason codes after every batch. For periodic exports, see `DEPLOYMENT_GUIDE.md` §3 (`assess_at: latest_reading`, `assess-range`) |
| Asset master data | `POST /api/v1/assets` (admin) | map the CMMS equipment reference into `asset.config.cmms_equipment_ref` |
| Crews and parts | `/api/v1/sites/{id}/technicians`, `/parts` | planner role writes; technician listings need a planner, reliability-engineer or admin key |
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

### 3.2 Dispatch (integration or admin role, e.g. from a cron job every few minutes)

`POST /api/v1/integrations/{id}/dispatch` → counts of `shadow`, `sent`, `retry`, `dead` and `skipped`.

**Delivery is state-based.** Every eligible work order whose version differs from the last delivered version is sent: approved work, plus orders in a mirrored state (§1, principle 3) that already have a sync record. A failed write therefore never loses an update; the next dispatch carries the current state.

**Switching a target from shadow to `draft_requests`** marks its shadow records as undelivered, so the next dispatch sends the current version of each for real.

### 3.3 Odoo mapping

| SentinelLoop | Odoo `maintenance.request` |
|---|---|
| `[SentinelLoop] <title>` (or the mirrored labels in §1) | `name` |
| explanation (why, due date and rule, P(failure) when it exists), advisory note, marker `[SentinelLoop-Ref:<wo_id>]` | `description` (HTML; every value escaped). P(failure) is written as "P(failure before <h> h): 0.xx" with **no** calibration caveat, although the RUL model's P(failure) is not calibrated (`RELIABILITY_AND_SAFETY.md` §4); the console's "not calibrated" label is not carried into the CMMS |
| P1 / P2 / P3 | `priority` '3' / '2' / '1'; '0' when withdrawn or deferred (code only, §1) |
| condition-based work | `maintenance_type` = `preventive` |
| scheduled start / end (UTC) | `schedule_date` / `schedule_end` (`YYYY-MM-DD HH:MM:SS`, UTC) |
| duration (h) | `duration` |
| `asset.config.cmms_equipment_ref` → `maintenance.equipment.serial_no` lookup | `equipment_id` |

**Idempotency and recovery.**
- The external id is stored per (target, work order).
- **A first send never adopts an existing record.** It always creates a new request, even if a request with the order's marker already exists in the CMMS (`test_a_first_send_never_adopts_a_pre_planted_record`).
- **Recovery by marker only after a logged delivery.** If the stored external id is lost, the connector searches for the marker only when the integration log records an earlier successful delivery of that order to that target. Shadow records never count, so the first live send after shadow mode creates new requests (`test_recovery_needs_evidence_of_an_earlier_real_delivery`).
- When recovery runs, only a request whose name starts with `[SentinelLoop]` and whose description holds the exact delimited marker is adopted; two candidates make a dead letter for a person to resolve (`test_a_lost_mapping_adopts_only_the_exactly_marked_request_and_refuses_ambiguity`, `test_draft_mode_creates_once_updates_on_change_and_never_duplicates`).
- **A mirrored request is never recovered.** Mirroring renames it `[SentinelLoop WITHDRAWN] ...`, `[SentinelLoop DEFERRED until ...] ...` or `[SentinelLoop COMPLETED] ...`, which does not start with `[SentinelLoop]`. If its mapping is lost, the next dispatch of that order creates a second request (`integration.OdooJson2.upsert`; not tested). The no-duplicates guarantee therefore holds only while the request still carries the `[SentinelLoop]` name.
- Each JSON-2 call runs in its own Odoo transaction (Odoo documentation), so a create is never half-applied.

### 3.4 Failures

| failure | handling |
|---|---|
| timeout, connection error, HTTP 408/429/5xx | `retry`, with exponential backoff: 30 s × 2ⁿ⁻¹ after the n-th failed attempt, capped at 1 h, then lengthened by a deterministic 0–20% jitter (never shortened; at most 72 min) (`integration._backoff_s`) |
| other HTTP 4xx (401 bad key, 403, 422 invalid data), missing credential variable, host no longer allowlisted, invalid URL or credential name | `dead`, with the error kept |
| `max_attempts` (default 8) exhausted | `dead` |

- **Dead letters** wait for an admin: `POST /api/v1/integrations/{id}/items/{wo_id}/requeue` with a reason (audited).
- **Stored error text** keeps the HTTP status and Odoo's `message`. It never keeps Odoo's `debug` traceback or the credential; both are tested.

### 3.5 Webhooks

**Headers.**
- `X-SentinelLoop-Timestamp`: Unix seconds.
- `X-SentinelLoop-Signature`: `sha256=<hex HMAC-SHA256(secret, "<timestamp>." + body)>`.
- The secret must be at least 32 characters, from `secret_env`.

**Receivers** verify the signature in constant time and reject timestamps outside ±300 s. `integration.verify_webhook` is the reference implementation; tests cover tampering, the wrong key and replay. SentinelLoop itself exposes no inbound webhook endpoint.

## 4. Going from shadow to live: checklist

1. Run in shadow for an agreed period. Compare the recorded payloads (`GET /integrations/{id}/items`) with what planners actually created in the CMMS.
2. Agree with the CMMS owner which fields SentinelLoop may write. Use a dedicated least-privilege CMMS user for its API key, and rotate keys; Odoo keys last at most three months per Odoo's documentation (R5). SentinelLoop cannot limit what that CMMS user is allowed to do; the CMMS configuration does.
3. Check the API's environment: `SENTINELLOOP_INTEGRATION_HOSTS` lists only the CMMS host, and the `SENTINELLOOP_CRED_*` variable is set.
4. Admin: `POST /integrations/{id}/mode` with `{"mode": "draft_requests", "reason": "<who agreed, when>"}`. The next dispatch creates new requests for every eligible order; it adopts no existing CMMS record. Orders withdrawn, deferred or completed during the shadow period also have shadow records, so they too are created, already carrying their mirrored text and priority (code: `set_mode`, `dispatch`; not tested).
5. Watch `retry` and `dead` counts. Every dead letter is reviewed by a person.
6. Before any of this at a customer: run `sandbox/odoo/setup.sh` and `tests/test_app_odoo_sandbox.py` against a real Odoo (not done yet).

## 5. Evidence

All IMPLEMENTED_AND_TESTED entries below are against the in-process test double of Odoo's documented JSON-2 API, not against Odoo software.

| claim | evidence | status |
|---|---|---|
| requests conform to the documented JSON-2 shape | the fake Odoo asserts path, headers and body for every call | IMPLEMENTED_AND_TESTED (test double) |
| shadow makes no external call | `test_targets_default_to_read_only_shadow_mode_and_shadow_never_calls_the_cmms` | IMPLEMENTED_AND_TESTED |
| unapproved work never leaves the system | `test_unapproved_work_never_leaves_the_system` | IMPLEMENTED_AND_TESTED |
| idempotent upsert, no duplicates after a lost mapping, for a request still named `[SentinelLoop]` (a request already renamed by mirroring is not recovered: §3.3) | `test_draft_mode_creates_once_updates_on_change_and_never_duplicates` | IMPLEMENTED_AND_TESTED |
| cancelled and deferred orders are marked on the existing request | `test_cancelled_or_deferred_orders_are_marked_in_the_cmms` | IMPLEMENTED_AND_TESTED for name and description (rejection, completion and the lowered priority: code only) |
| no adoption on a first send; recovery only after a logged delivery | `test_a_first_send_never_adopts_a_pre_planted_record`, `test_recovery_needs_evidence_of_an_earlier_real_delivery` | IMPLEMENTED_AND_TESTED |
| field allowlist enforced by an explicit check | `test_payload_fields_are_filtered_explicitly_not_by_assert` | IMPLEMENTED_AND_TESTED |
| allowlist at registration and at every dispatch; https unless local; no credentials, query or fragment in URLs | `test_targets_must_be_on_the_host_allowlist_and_use_https_unless_local`, `test_the_host_allowlist_is_checked_again_at_dispatch`, `test_urls_with_credentials_queries_or_fragments_are_refused` | IMPLEMENTED_AND_TESTED |
| credentials only from `SENTINELLOOP_CRED_*`; config keys allowlisted; config for admins only; secrets never stored | `test_credential_variables_must_use_the_dedicated_prefix`, `test_unknown_config_keys_are_refused`, `test_integration_config_is_shown_to_admins_only`, `test_secrets_are_never_stored_in_the_database` | IMPLEMENTED_AND_TESTED |
| retries, backoff, dead letters, requeue | `test_transient_failures_…`, `test_permanent_errors_…`, `test_retries_stop_after_the_attempt_limit` | IMPLEMENTED_AND_TESTED |
| works against real Odoo software | `tests/test_app_odoo_sandbox.py` | **NOT YET RUN** (needs the image download, awaiting approval) |
| works with a customer's CMMS | — | BLOCKED (no customer) |
