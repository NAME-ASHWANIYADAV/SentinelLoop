# Integration guide

How SentinelLoop exchanges data with the systems around it.

| part | status |
|---|---|
| Inbound data (ingestion API) | IMPLEMENTED_AND_TESTED |
| Outbound CMMS connector for Odoo (JSON-2) and signed webhooks | IMPLEMENTED_AND_TESTED **against a contract test double only** |
| Run against a real Odoo Community sandbox | **NOT RUN: the Odoo image download awaits approval** (`sandbox/odoo/`, PD-26). Compatibility with real Odoo is unproven (KNOWN_LIMITATIONS S1) |
| Connection to a customer CMMS | **none exists** |

Code: `src/sentinelloop/app/integration.py`, migrations `0005_integration.sql` and `0009_integration_dispatch.sql`. Tests: `tests/test_app_integration.py` (13), the CMMS tests in `tests/test_app_remediation_security.py` (Phase 9 review fixes), `tests/test_app_rereview_integration.py` (fixes from the re-review of those fixes, PD-28), the integration cases in `tests/test_app_rereview_api.py`, `tests/test_app_api.py`, and `tests/test_app_odoo_sandbox.py` (opt-in; skipped unless a sandbox is configured, so far never run). All the others run against an in-process test double, not Odoo software.

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
   - Config values are checked at registration (`integration.check_config`; `test_bad_config_values_are_refused_at_registration`; 422 through the API):
     - `database` must be an Odoo database name (letters, digits, `_`, `.`, `-`, starting with a letter or digit, at most 128 characters), because it is sent as a header;
     - `timeout_s` must be a number above 0 and at most 120 s;
     - `max_attempts` must be a whole number from 1 to 100.
   - At every live dispatch, only what the adapter needs is checked again: the keys, the credential names and the database name. A target stored by an earlier version keeps its numbers as that version used them, except that `timeout_s` is clamped to 120 s, which the dispatch lease relies on (§3.2). A value that cannot be used makes every item a dead letter. There is no route to change a stored config: register the target again under a new id (KNOWN_LIMITATIONS S11; `DEPLOYMENT_GUIDE.md` §7 says what that means for requests already in the CMMS). `timeout_s` applies to Odoo targets; webhook calls use a fixed 10 s timeout.
   - A target's config and URL are shown only to admins: `GET /integrations` drops `config` and `base_url` for every other role. Dispatch error text is withheld from non-admins too, in the items listing and in audit histories (`test_integration_config_is_shown_to_admins_only`, `test_non_admins_do_not_see_integration_hosts_or_config`, `test_non_admins_do_not_see_dispatch_error_detail`).
   - A test scans the database file for the key.
6. **Controlled destinations.**
   - The target URL must be `http` or `https`; `https` is required except for local hosts (`localhost`, `127.0.0.1`, `::1`, `*.localhost`, `*.test`).
   - It may not carry credentials (`user:password@`, or an empty `@`), a query string or a fragment (`test_urls_with_credentials_queries_or_fragments_are_refused`).
   - It may not contain spaces, control characters or backslashes, its port must be valid, and httpx, which sends the request, must parse the same host and port as the check (`test_bad_urls_are_refused_at_registration`).
   - Its host must be listed in `SENTINELLOOP_INTEGRATION_HOSTS`. The URL is checked at registration and **again at every dispatch outside shadow mode**: removing a host from the list stops delivery to it, and its items become dead letters (`test_the_host_allowlist_is_checked_again_at_dispatch`).
   - The allowlist matches host names, not ports: any port on an allowed host is accepted.

## 2. Inbound: data into SentinelLoop

| source | path | notes |
|---|---|---|
| SCADA / historian exports | `POST /api/v1/ingest/csv` (long or wide CSV, at most 200,000 readings per batch) or `/ingest/readings` (JSON) | contract v1 (`DATA_CONTRACTS.md`); an `integration` role key; check `rows_rejected` and the reason codes after every batch. For periodic exports, see `DEPLOYMENT_GUIDE.md` §3 (`assess_at: latest_reading`, `assess-range`) |
| Asset master data | `POST /api/v1/assets` (admin) | map the CMMS equipment reference into `asset.config.cmms_equipment_ref` |
| Crews and parts | `/api/v1/sites/{id}/technicians`, `/parts` | planner role writes; technician listings need a planner, reliability-engineer or admin key |
| Work orders raised by another system | `POST /api/v1/work-orders` with an `integration` key (origin `external`) | the `Idempotency-Key` header is required. Keys starting `rec:`, `reactivate:` or `apply:` are reserved for the platform and refused with 400 on creation and transitions (`test_clients_cannot_use_the_engines_reserved_idempotency_keys`) and on completion (code only, `api.complete`). Completions by the `integration` role never clear a latched warning (KNOWN_LIMITATIONS S6) |
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

`POST /api/v1/integrations/{id}/dispatch` → `target_id`, `mode`, `considered`, counts of `shadow`, `sent`, `retry`, `dead` and `skipped` (dead letters left alone), `busy` and `stopped`.

**Delivery is state-based.** Every eligible work order whose version differs from the last delivered version is sent: approved work, plus orders in a mirrored state (§1, principle 3) that already have a sync record. A failed write therefore never loses an update; the next dispatch carries the current state. At most 200 orders are handled per run; the rest wait for the next.

**One dispatch per target at a time** (PD-28; `test_a_dispatch_that_overlaps_a_running_one_reports_busy_and_sends_nothing`, `test_two_dispatcher_threads_create_one_request`).
- A run holds the target's lease, kept as events in `integration_log`. A run that finds the lease held returns `busy: true` and sends nothing, and its `stopped` says so too, so check `busy` before reading `stopped`.
- The lease lasts 10 minutes and is renewed as the run goes. A crashed run blocks the target for at most that long (`test_the_lease_of_a_crashed_dispatcher_expires`).
- Before every external call and every recorded result, the run checks that it still holds the lease and that the target's mode has not changed and the target is still enabled. Otherwise it stops, and `stopped` says why. A switch to shadow during a live run stops it before its next call (`test_switching_to_shadow_during_a_live_run_stops_it_before_the_next_call`).
- A lapsed run's failure never overwrites a newer record: its `retry` or `dead` result is recorded only if no other run has written the order since. Otherwise the newer result stands, and unless the lapsed run's failure certainly changed nothing in the CMMS, the order is sent again; if the lapsed run had attempted a create, the order is searched by marker again (§3.3) (`test_a_lapsed_dispatcher_whose_create_was_refused_does_not_overwrite_the_successors_delivery`).
- A lapsed run's success is recorded even if another run has written the order since, but as not yet delivered (`synced_version` empty), so the next run sends the order's current version again (`integration._record`; `test_a_dispatcher_that_lost_its_lease_records_what_it_did_and_stops`). Until then the CMMS may show the lapsed run's older version: its write can land after the newer run's, for example re-approving a request the newer run had marked withdrawn (not tested).
- If both runs created a request, the order becomes a dead letter that names both, at once or after the next run's marker search (`test_a_duplicate_made_by_a_dispatcher_that_lost_its_lease_is_a_dead_letter_not_an_orphan`, `test_a_lapsed_dispatcher_whose_create_answer_was_lost_leaves_no_silent_orphan`).
- The same lease and checks apply to webhook targets (`test_a_webhook_dispatch_honours_the_lease_and_stops_on_a_mode_change`).

**Switching a target from shadow to `draft_requests`** marks its shadow records as undelivered, so the next dispatch sends the current version of each for real. A shadow run still going when the switch happens does not record its results as delivered, so the next live dispatch sends them (`test_going_live_during_a_shadow_run_still_delivers_the_order`).

**Each order is handled on its own.** An error on one order, including an unexpected one, becomes a recorded retry or dead letter for that order, and the run goes on (`test_an_unexpected_error_on_one_order_is_a_dead_letter_and_the_run_goes_on`).

### 3.3 Odoo mapping

| SentinelLoop | Odoo `maintenance.request` |
|---|---|
| `[SentinelLoop] <title>` (or the mirrored labels in §1) | `name` |
| explanation (why, due date and rule, P(failure) when it exists), advisory note, marker `[SentinelLoop-Ref:<wo_id>]` | `description` (HTML; every value escaped). P(failure) is written as `P(failure before <h> h): 0.xx` with **no** calibration caveat, although the RUL model's P(failure) is not calibrated (`RELIABILITY_AND_SAFETY.md` §4); the console's "not calibrated" label is not carried into the CMMS |
| P1 / P2 / P3 | `priority` '3' / '2' / '1'; '0' when withdrawn or deferred (code only, §1) |
| condition-based work | `maintenance_type` = `preventive` |
| scheduled start / end (UTC) | `schedule_date` / `schedule_end` (`YYYY-MM-DD HH:MM:SS`, UTC) |
| duration (h) | `duration` |
| `asset.config.cmms_equipment_ref` → `maintenance.equipment.serial_no` lookup | `equipment_id` |

**Idempotency and recovery** (`integration.OdooJson2.upsert`, `_recovery_evidence`, `_record`; PD-20, PD-28).
- The external id is stored per (target, work order).
- **The marker.** Every request's description carries `[SentinelLoop-Ref:<wo_id>]`, delimited so that the marker of WO-1 is not part of the marker of WO-10. Without a stored external id, the connector searches the CMMS for it (`description ilike`, then an exact match on the delimited marker) before it creates anything. The name is not used, so a request renamed by mirroring is found too (`test_a_mirrored_request_is_recovered_by_its_marker_and_a_second_candidate_is_a_dead_letter`).
- **A first send never adopts an existing record.** It creates a new request even if one with the order's marker already exists (`test_a_first_send_never_adopts_a_pre_planted_record`). The ids it found are recorded with the create attempt, and are never adopted later either (`test_a_record_planted_before_the_first_create_is_never_adopted_even_after_a_lost_response`, `test_a_planted_record_is_not_adopted_when_the_first_create_never_reached_the_cmms`).
- **Every create attempt is logged before the call.** A request found by marker is adopted only when the integration log gives evidence that SentinelLoop itself may have created one: an earlier successful live delivery of that order to that target, or a create attempt whose outcome is unresolved (a read timeout or any transport error other than a failed connection, a 408, 429 or 5xx, or an answer that is not Odoo's). Shadow records never count, so the first live send after shadow mode creates new requests (`test_recovery_needs_evidence_of_an_earlier_real_delivery`). After a lost create answer, the next attempt therefore finds the request by its marker and does not create it again (`test_a_lost_create_response_is_found_by_marker_and_not_created_again`). A request carrying the marker that was not there before the attempt is taken to be SentinelLoop's own.
- **A definite refusal is not evidence.** A create that certainly created nothing (an HTTP 4xx other than 408 or 429, or a connection that was never made) is logged as refused. A request found with the marker later is not adopted (`test_a_record_planted_after_a_definitely_refused_create_is_not_adopted`).
- **Two or more candidates** make a dead letter for a person; none is adopted (`test_a_lost_mapping_adopts_only_the_exactly_marked_request_and_refuses_ambiguity`, `test_two_candidates_after_a_lost_create_make_a_dead_letter`).
- **One re-verification, about an hour later.** A create whose answer was lost may commit after the next attempt searched and created again. An order recovered while such an attempt is unresolved, or one that a run tried to create before its lease lapsed, is searched by marker once more at its first dispatch at least an hour later (`verify_after_ms`, migration 0009), and at every send before. The order is due for that search even if it has not changed. A second request carrying the marker makes a dead letter that names it, after SentinelLoop's own request has been written, so a withdrawal still reaches it. A clean search at or after that time ends the re-verification (`test_a_create_that_commits_after_the_retrys_search_is_detected`, `test_a_late_commit_is_detected_without_waiting_for_the_order_to_change`, `test_after_a_recovery_the_marker_is_searched_once_more_and_then_no_longer`).
- **What remains** (KNOWN_LIMITATIONS S10): a create that commits after that second search is not detected, and the other request in a duplicate dead letter stays live in the CMMS until a person closes it (`OPERATIONS_RUNBOOK.md` §3.5).
- Each JSON-2 call runs in its own Odoo transaction (Odoo documentation), so a create is never half-applied.

### 3.4 Failures

| failure | handling |
|---|---|
| timeout, connection error, HTTP 408/429/5xx; an answer to a create or write that is not JSON, or an answer to a create that is not a single new id (a sign-in or proxy page: the call may have been committed, so a create's next attempt searches by marker first). A write answered with HTTP 200 and any JSON body counts as delivered: its answer is not checked (`integration.OdooJson2.upsert`) | `retry`, with exponential backoff: 30 s × 2ⁿ⁻¹ after the n-th failed attempt, capped at 1 h, then lengthened by a deterministic 0–20% jitter (never shortened; at most 72 min) (`integration._backoff_s`; `test_an_unexpected_answer_to_a_create_is_recorded_and_the_create_is_not_repeated`) |
| other HTTP 4xx (401 bad key, 403, 422 invalid data), missing credential variable, host no longer allowlisted, invalid URL, credential name or stored config value; an answer to a read that is not JSON or not a list of records (`test_a_sign_in_page_instead_of_the_api_gives_recorded_dead_letters_not_a_crash`) | `dead`, with the error kept |
| two CMMS requests carrying the order's marker (§3.3), or two CMMS ids for one order after a lapsed lease (§3.2) | `dead`; the error names the request ids, and a person decides in the CMMS (`OPERATIONS_RUNBOOK.md` §3.5) |
| any other error while delivering one order | `dead`, as `unexpected <type> while delivering this order (details in the server log)`; the traceback goes to the API's stderr, and the run goes on |
| `max_attempts` (default 8) exhausted | `dead` |

- **Dead letters** wait for an admin: `POST /api/v1/integrations/{id}/items/{wo_id}/requeue` with a reason (audited). A dead letter is not dispatched again, even if its order changes, until it is requeued.
- **Stored error text** keeps the HTTP status and Odoo's `message`. It never keeps Odoo's `debug` traceback or the credential; both are tested. Only admins see it (§1, principle 5).

### 3.5 Webhooks

**Headers.**
- `X-SentinelLoop-Timestamp`: Unix seconds.
- `X-SentinelLoop-Signature`: `sha256=<hex HMAC-SHA256(secret, "<timestamp>." + body)>`.
- The secret must be at least 32 characters, from `secret_env`.

**Body.** `{"event": "work_order.upsert", "wo_id": ..., "payload": ...}`, where `payload` holds the fields of the Odoo request (§3.3) without `equipment_id`.

**Receivers** verify the signature in constant time and reject timestamps outside ±300 s. `integration.verify_webhook` is the reference implementation; tests cover tampering, the wrong key and replay. It returns `False` for malformed headers instead of raising: a timestamp that is not 1–15 ASCII digits, or a signature that is not ASCII text (`test_verify_webhook_returns_false_for_malformed_headers`). SentinelLoop itself exposes no inbound webhook endpoint.

**No version or delivery id yet** (KNOWN_LIMITATIONS S9). The signed body carries no version, delivery id or state field. The state appears only in the description text, and for a withdrawn, deferred or completed order in the name label. A receiver therefore cannot reject a replay inside the ±300 s window, or an older delivery that arrives after a newer one. It must deduplicate by work-order id and state itself.

## 4. Going from shadow to live: checklist

1. Run in shadow for an agreed period. Compare the recorded payloads (`GET /integrations/{id}/items`) with what planners actually created in the CMMS.
2. Agree with the CMMS owner which fields SentinelLoop may write. Use a dedicated least-privilege CMMS user for its API key, and rotate keys; Odoo keys last at most three months per Odoo's documentation (R5). SentinelLoop cannot limit what that CMMS user is allowed to do; the CMMS configuration does.
3. Check the API's environment: `SENTINELLOOP_INTEGRATION_HOSTS` lists only the CMMS host, and the `SENTINELLOOP_CRED_*` variable is set.
4. Admin: `POST /integrations/{id}/mode` with `{"mode": "draft_requests", "reason": "<who agreed, when>"}`. The next dispatch creates new requests for every eligible order; it adopts no existing CMMS record. Orders withdrawn, deferred or completed during the shadow period also have shadow records, so they too are created, already carrying their mirrored text and priority (code: `set_mode`, `dispatch`; not tested).
5. Watch `retry` and `dead` counts, and `busy` and `stopped` in the dispatch responses. Every dead letter is reviewed by a person; a duplicate (two CMMS requests for one order) is resolved in the CMMS first (`OPERATIONS_RUNBOOK.md` §3.5).
6. Before any of this at a customer: run `sandbox/odoo/setup.sh` and `tests/test_app_odoo_sandbox.py` against a real Odoo. **Not done yet**: the Odoo image download still awaits approval, so none of the behaviour in this guide has been seen against Odoo software.

## 5. Evidence

All IMPLEMENTED_AND_TESTED entries below are against the in-process test double of Odoo's documented JSON-2 API, not against Odoo software.

| claim | evidence | status |
|---|---|---|
| requests conform to the documented JSON-2 shape | the fake Odoo asserts path, headers and body for every call | IMPLEMENTED_AND_TESTED (test double) |
| shadow makes no external call | `test_targets_default_to_read_only_shadow_mode_and_shadow_never_calls_the_cmms` | IMPLEMENTED_AND_TESTED |
| unapproved work never leaves the system | `test_unapproved_work_never_leaves_the_system` | IMPLEMENTED_AND_TESTED |
| idempotent upsert, no duplicates after a lost mapping, including for a request renamed by mirroring (the delimited marker in the description is matched, not the name) | `test_draft_mode_creates_once_updates_on_change_and_never_duplicates`, `test_a_mirrored_request_is_recovered_by_its_marker_and_a_second_candidate_is_a_dead_letter` | IMPLEMENTED_AND_TESTED |
| cancelled and deferred orders are marked on the existing request | `test_cancelled_or_deferred_orders_are_marked_in_the_cmms` | IMPLEMENTED_AND_TESTED for name and description (rejection, completion and the lowered priority: code only) |
| no adoption on a first send; recovery only after a logged delivery or an unresolved create attempt; a definitely refused attempt is no evidence | `test_a_first_send_never_adopts_a_pre_planted_record`, `test_recovery_needs_evidence_of_an_earlier_real_delivery`, `test_a_record_planted_before_the_first_create_is_never_adopted_even_after_a_lost_response`, `test_a_record_planted_after_a_definitely_refused_create_is_not_adopted` | IMPLEMENTED_AND_TESTED |
| a lost create answer does not create a second request; a create that commits late is found by the re-verification and dead-lettered | `test_a_lost_create_response_is_found_by_marker_and_not_created_again`, `test_a_create_that_commits_after_the_retrys_search_is_detected`, `test_after_a_recovery_the_marker_is_searched_once_more_and_then_no_longer` | IMPLEMENTED_AND_TESTED (a commit later than the re-verification: not detected, S10) |
| one dispatch per target; a lapsed run never overwrites a newer record; a mode change stops a run | `test_two_dispatcher_threads_create_one_request`, `test_the_lease_of_a_crashed_dispatcher_expires`, `test_a_duplicate_made_by_a_dispatcher_that_lost_its_lease_is_a_dead_letter_not_an_orphan`, `test_a_lapsed_dispatcher_whose_create_was_refused_does_not_overwrite_the_successors_delivery`, `test_switching_to_shadow_during_a_live_run_stops_it_before_the_next_call`, `test_going_live_during_a_shadow_run_still_delivers_the_order` | IMPLEMENTED_AND_TESTED (two dispatchers tested as threads of one process) |
| an unexpected answer or error is isolated to its order | `test_an_unexpected_answer_to_a_create_is_recorded_and_the_create_is_not_repeated`, `test_a_sign_in_page_instead_of_the_api_gives_recorded_dead_letters_not_a_crash`, `test_an_unexpected_error_on_one_order_is_a_dead_letter_and_the_run_goes_on` | IMPLEMENTED_AND_TESTED |
| field allowlist enforced by an explicit check | `test_payload_fields_are_filtered_explicitly_not_by_assert` | IMPLEMENTED_AND_TESTED |
| allowlist at registration and at every dispatch; https unless local; no credentials, query or fragment in URLs; URLs parsed as httpx sends them | `test_targets_must_be_on_the_host_allowlist_and_use_https_unless_local`, `test_the_host_allowlist_is_checked_again_at_dispatch`, `test_urls_with_credentials_queries_or_fragments_are_refused`, `test_bad_urls_are_refused_at_registration` | IMPLEMENTED_AND_TESTED |
| credentials only from `SENTINELLOOP_CRED_*`; config keys allowlisted; config for admins only; secrets never stored | `test_credential_variables_must_use_the_dedicated_prefix`, `test_unknown_config_keys_are_refused`, `test_integration_config_is_shown_to_admins_only`, `test_secrets_are_never_stored_in_the_database` | IMPLEMENTED_AND_TESTED |
| config values checked at registration; a target stored with a bad value gives dead letters, not a crash; values an earlier version accepted still deliver, with the timeout clamped to 120 s | `test_bad_config_values_are_refused_at_registration`, `test_through_the_api_a_bad_config_value_or_url_is_a_422`, `test_a_target_stored_with_a_bad_value_gives_dead_letters_not_a_crash`, `test_a_target_stored_with_values_the_previous_version_accepted_still_delivers` | IMPLEMENTED_AND_TESTED |
| hosts, config and error text withheld from non-admins | `test_non_admins_do_not_see_integration_hosts_or_config`, `test_non_admins_do_not_see_dispatch_error_detail`, `test_open_work_order_audit_history_hides_integration_error_detail` | IMPLEMENTED_AND_TESTED |
| retries, backoff, dead letters, requeue | `test_transient_failures_…`, `test_permanent_errors_…`, `test_retries_stop_after_the_attempt_limit` | IMPLEMENTED_AND_TESTED |
| reference webhook verifier rejects malformed headers | `test_verify_webhook_returns_false_for_malformed_headers` | IMPLEMENTED_AND_TESTED. A version or delivery id in the signed body: not implemented (open limitation S9) |
| works against real Odoo software | `tests/test_app_odoo_sandbox.py` | **NOT YET RUN** (needs the image download, awaiting approval) |
| works with a customer's CMMS | — | BLOCKED (no customer) |
