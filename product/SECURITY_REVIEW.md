# Security review

**Date:** 2026-10-18 (updated after the Phase 9 fixes).
**Scope:** the product platform (`src/sentinelloop/app`, the REST API, the admin CLI, the CMMS integration) and the operator console (`src/sentinelloop/console`) on branch `product/platform`.
**Reviewers:** the engineering lead, an automated code security review that runs on each commit, and the Phase 9 adversarial review, in which one of six role-played reviewers was an IT/OT security assessor (`ADVERSARIAL_REVIEW.md`; personas, not a real assessor). **No external penetration test has been done.** Nothing here is a compliance claim or certification.

The threat model is `THREAT_MODEL.md`. This document records what was checked, what was found, and what was done.

## 1. Findings and their resolution

### 1.1 Automated reviews, Phases 3–8

Every finding was fixed **test-first**: the failing test was written and seen to fail, then the fix was made. They are listed in the order found.

| # | severity | finding | fix | test | commit |
|---|---|---|---|---|---|
| 1 | MEDIUM | audit key silently fell back to a built-in development key | fail-closed: a key of at least 32 bytes is required; the dev key needs explicit opt-in and every event signed with it is counted | `test_app_foundation.py` | e9ca41b |
| 2 | MEDIUM | an asset id could equal another asset's tag, so ingestion could write to the wrong asset | one namespace for ids and tags; ambiguous keys rejected | `test_app_ingest.py` | e9ca41b |
| 3 | MEDIUM | work-order completion silently accepted an idempotency key already used for another action | `IdempotencyConflict` (409) | `test_app_workorders.py` | bf6b41c / e9ca41b |
| 4 | MEDIUM | decision generation aborted for the whole fleet on one in-progress or rejected order | per-asset isolation; `unchanged` / `already_decided` | `test_one_bad_asset_never_stops_generation_for_the_others` | 29cb8f0 |
| 5 | MEDIUM | the audit history of any entity, including `user`, was readable with `read` | non-operational entities need `audit.read` | `test_audit_history_of_sensitive_entities_needs_audit_permission` | bdd801e |
| 6 | MEDIUM | the body-size limit relied on Content-Length (chunked bodies bypassed it) | ASGI middleware counts bytes while streaming; 413 on JSON and CSV | `test_chunked_bodies_without_content_length_are_capped` | bdd801e |
| 7 | MEDIUM | rate-limit buckets keyed by the raw header string (bypass by re-formatting the key); unbounded bucket map | keyed by authenticated user id, or by client address otherwise; LRU-bounded | `test_rate_limit_is_per_user_not_per_credential_string_and_buckets_are_bounded` | bdd801e |
| 8 | MEDIUM | CSV export open to spreadsheet formula injection | formula-leading cells prefixed with `'` | `test_csv_export_neutralises_spreadsheet_formulas` | bdd801e |
| 9 | MEDIUM | an integration target could name any environment variable as its credential (e.g. the audit key) and send it to an allowlisted host | credential variables must start with `SENTINELLOOP_CRED_` | `test_credential_variables_must_use_the_dedicated_prefix` | bb8c363 |
| 10 | MEDIUM | HTML injection into the CMMS request description | every interpolated value escaped | `test_every_value_in_the_cmms_description_is_html_escaped` | bb8c363 |
| 11 | MEDIUM | lost-mapping recovery matched markers by substring (WO-1 inside WO-10) and could adopt the wrong CMMS record | delimited marker; exact match; name prefix; ambiguity → dead letter | `test_a_lost_mapping_adopts_only_the_exactly_marked_request_and_refuses_ambiguity` | bb8c363 |
| 12 | MEDIUM | SSRF through the console: the API URL was a login field, so the console server could be pointed at any host with a typed key; raw upstream error bodies were shown | the API URL is server configuration only (`SENTINELLOOP_API_URL`); non-JSON upstream errors reported by status only | `test_the_api_url_is_server_configuration_not_a_login_field`, `test_non_json_upstream_errors_are_not_echoed` | af7a752 |

### 1.2 Phase 9 adversarial review: security findings

Severities for high findings are shown as reported → after adversarial verification; medium and low findings were not verified (`ADVERSARIAL_REVIEW.md`). The regression tests were written before the fixes. Per the commit messages, 20 of the 22 tests then in `tests/test_app_remediation.py` failed against the earlier code (38e8741), and 15 tests in `tests/test_app_remediation_security.py` did (6abeb26, which gives no total). Tests are in `tests/test_app_remediation.py` (R) and `tests/test_app_remediation_security.py` (RS) unless named otherwise.

| id | severity | finding | resolution | test | commit |
|---|---|---|---|---|---|
| security-1 | high → medium | a technician could clear a latched URGENT_REVIEW with no maintenance and no work order | **FIXED at the API.** `clear-risk` records reasoned dismissals only, by planners, reliability engineers and admins; maintenance clears a latch only through its completed work order, under the PD-16 conditions. Residual: the dismissal-only rule is in the API route alone; `health.clear_latched_risk` and `states.clear_risk` still accept `maintenance_completed` from technicians (`THREAT_MODEL.md` T7) | R: `test_maintenance_cannot_be_recorded_through_clear_risk` and the latch tests | 38e8741 |
| security-2 | high → high | an unbounded `as_of` let the integration key or a planner silence recommendations and clear a data-quality failure | **FIXED.** Instants more than 5 min in the future refused; back-dated assessments stored as replays that never move the live state | R: `test_future_assessment_instants_are_refused`, `test_back_dated_assessments_are_stored_but_never_move_the_live_state` | 38e8741 |
| security-3 | high → medium | the console listened on all interfaces over plain HTTP, contrary to the deployment guide | **FIXED.** `.streamlit/config.toml` binds 127.0.0.1 (read when Streamlit starts from the repository root); TLS through a reverse proxy. Long-lived personal API keys remain (residual) | RS: `test_the_console_binds_to_localhost_by_configuration` | 6abeb26 |
| security-4 | high → medium | audit verification could not detect truncation without an anchor, nor direct edits of state; "tamper-evident audit of every platform action" was overclaimed | **PARTIAL.** The CLI: `verify-audit` fails without an anchor unless `--allow-no-anchor`; `--anchor` takes an anchor kept off the host; the recovery drill verifies the live database against the backup's anchor. Claim reworded: the chain covers audit events, not state tables (PD-22). **OPEN:** `GET /api/v1/audit/verify` still verifies without an anchor when `anchor_seq` and `anchor_hash` are absent, and the console's "Verify the audit chain" button sends none, so both report `valid: True` without checking truncation (`THREAT_MODEL.md` T2) | RS: `test_verify_audit_requires_an_anchor_unless_explicitly_waived`; recovery drill R1 | 6abeb26; R1 re-run evidence afadc02 |
| security-5 | medium | the integration role is over-privileged and work orders have no assignment checks | **PARTIAL.** Completions by a machine role never clear a latch; schedule technicians must be registered where the site has a crew list. **OPEN:** splitting the integration role, assignment checks, a per-action schema for transition data | R: `test_a_machine_credential_completion_does_not_clear_a_latch`, `test_schedule_technicians_must_be_registered_when_the_site_has_a_crew_list` | 38e8741 |
| security-6 | medium | cancelled work stayed live in the CMMS, and the first send adopted pre-planted CMMS records | **FIXED.** Cancelled, rejected, deferred and completed orders are mirrored onto the existing request; a first send never searches by marker; an explicit field allowlist that raises instead of an `assert` | RS: `test_cancelled_or_deferred_orders_are_marked_in_the_cmms`, `test_a_first_send_never_adopts_a_pre_planted_record`, `test_payload_fields_are_filtered_explicitly_not_by_assert` | 6abeb26 |
| security-7 | medium | the host allowlist was checked only at registration; credentials were accepted in URLs and unlisted config keys, shown to planners and written into the audit chain | **FIXED.** Allowlist re-checked at every dispatch; URLs with credentials, a query or a fragment refused; config keys allowlisted; config shown to admins only. Residual: the allowlist matches host names, so any port on an allowed host is accepted | RS: `test_the_host_allowlist_is_checked_again_at_dispatch`, `test_urls_with_credentials_queries_or_fragments_are_refused`, `test_unknown_config_keys_are_refused`, `test_integration_config_is_shown_to_admins_only` | 6abeb26 |
| security-8 | medium | a 10 MiB CSV upload blocked the API event loop and expanded to gigabytes of memory | **FIXED** (streaming parse **OPEN**). At most 200,000 readings per CSV batch; parsed in a worker thread, off the event loop | RS: `test_csv_uploads_are_capped_by_record_count` (the cap; the worker thread is code only) | 6abeb26 |
| security-9 | medium | THREAT_MODEL E1 said every service re-checks permissions; most write paths do not | **DOCS.** E1 now lists the services that re-check roles and those that rely on the API check alone. In-service checks for the latter: **OPEN** | — | this update |
| security-10 | low | rate limiting was skipped for any path ending in `/health` or `/ready`; `/ready` and the OpenAPI schema are unauthenticated | **PARTIAL.** Only the exact paths `/api/v1/health` and `/api/v1/ready` are exempt. `/ready` and the OpenAPI schema stay unauthenticated: **accepted**, documented in THREAT_MODEL S1 and `DEPLOYMENT_GUIDE.md` §5 | no dedicated test (`api.py`, request envelope) | 38e8741 |
| security-11 | low | server filesystem paths and exception text reached every role through assessment reasons | **FIXED.** Reasons carry a code and, for a crash, the exception type; paths and messages go to the server log | `test_a_model_that_crashes_while_scoring_gives_model_unavailable_and_no_numbers` (exception text); no test asserts the absence of paths (code: `health.assess`) | 38e8741 |
| security-12 | low | free-text titles and reasons were rendered as Markdown on the approval and asset pages | **FIXED.** API text is rendered inside code spans (see the follow-up finding below) | RS: `test_console_renders_api_text_as_code_spans_with_no_links` | 6abeb26, c0f172a |
| security-13 | low | the registry's checksum was copied from the bundle's own manifest | **PARTIAL.** Registration hashes `bundle.pkl` and refuses a mismatch with its manifest. **OPEN:** signed manifests | RS: `test_registration_refuses_an_artefact_that_does_not_match_its_manifest` | 6abeb26 |
| security-14 | low | security documents were stale or inconsistent with the code and the OSV evidence | **DOCS.** THREAT_MODEL and this review synchronised with the code; OSV advisories deduplicated (§3) | — | this update |

**Follow-up automated security reviews of the Phase 9 fixes:**

| severity | finding | fix | test | commit |
|---|---|---|---|---|
| MEDIUM | fail-open latch start: a latch with an unknown start let older work clear it | an unknown start fails closed; `advance` never records 0; migration 0007 backfills existing latches from their last update | R: `test_an_unknown_latch_start_fails_closed`, `test_advance_never_records_a_zero_latch_start`, `test_migration_backfills_the_start_of_existing_latches` | 6abeb26 |
| MEDIUM | lost-mapping recovery could adopt planted records after a shadow-to-live switch | recovery by marker needs a logged earlier successful delivery of that order to that target | RS: `test_recovery_needs_evidence_of_an_earlier_real_delivery` | c0f172a |
| MEDIUM | escaping markdown characters still left GFM autolinks | API text goes into one code span, with backticks and line breaks replaced | RS: `test_console_renders_api_text_as_code_spans_with_no_links` | c0f172a |

**Acknowledged, not changed:** model bundles are Python pickles. Loading arbitrary pickles executes code. Mitigation: registration hashes `bundle.pkl` against its manifest and records that hash; a bundle is loaded only after its SHA-256 matches the recorded value; bundles come only from our packaging code. A bundle altered together with its manifest before registration is still accepted. The residual risk is in `THREAT_MODEL.md` T3 (planned: signed manifests).

## 2. Controls verified by tests

| control | test(s) |
|---|---|
| every API route except health, ready and docs requires credentials (walks all routes) | `test_every_route_except_health_and_docs_requires_credentials` |
| role permissions enforced at the API (403), tested for a sample of about a dozen route and role pairs, not for every route (the route walk checks 401 only); re-checked inside the work-order, state-clearing, model-registry, planning, integration and commissioning services only (`THREAT_MODEL.md` E1) | `test_roles_are_enforced_with_403` and the other 403 assertions in `tests/test_app_api.py`, role tests in the workflow, planning, model and integration modules |
| keys stored only as hashes; listings never return hashes | `test_missing_or_wrong_credentials_are_401_and_api_keys_are_stored_hashed`, `test_user_administration_is_admin_only_and_keys_are_shown_once` |
| scrypt passwords, minimum length | `test_password_hashing_uses_scrypt_and_rejects_short_passwords` |
| technician names and shifts readable only by planners, reliability engineers and admins | `test_resources_can_be_managed_by_planners_only` |
| errors carry no internals | `test_validation_errors_are_422_without_internal_details`, `test_an_unexpected_server_error_is_a_json_500_with_a_request_id_and_no_internals` |
| latched warnings clear only under PD-16 through the API and work-order completion (the services below the `clear-risk` route still accept `maintenance_completed`: `THREAT_MODEL.md` T7); assessment instants cannot move the live state backwards | `tests/test_app_remediation.py` (latch, instant and replay tests) |
| integration secrets never stored; CMMS `debug` tracebacks never stored | `test_secrets_are_never_stored_in_the_database`, `test_permanent_errors_go_to_dead_letters_without_leaking_server_internals_and_can_be_requeued` |
| integration host allowlist, https unless local, re-checked at every dispatch; URL and config-key rules; config for admins only | `test_targets_must_be_on_the_host_allowlist_and_use_https_unless_local`, `test_the_host_allowlist_is_checked_again_at_dispatch`, `test_urls_with_credentials_queries_or_fragments_are_refused`, `test_unknown_config_keys_are_refused`, `test_integration_config_is_shown_to_admins_only` |
| CMMS: shadow by default, approved work only, withdrawal mirrored, no adoption on first send or without a logged delivery | `test_targets_default_to_read_only_shadow_mode_and_shadow_never_calls_the_cmms`, `test_unapproved_work_never_leaves_the_system`, `test_cancelled_or_deferred_orders_are_marked_in_the_cmms`, `test_a_first_send_never_adopts_a_pre_planted_record`, `test_recovery_needs_evidence_of_an_earlier_real_delivery` (all against a test double) |
| webhook signatures and replay window | `test_webhook_signatures_verify_and_reject_tampering_and_replays` |
| tamper evidence of the audit chain: edits, the wrong key, truncation against an anchor, the CLI's refusal without an anchor. State tables are **not** covered (PD-22); the API route and the console button verify without an anchor (security-4) | `test_backup_restore_round_trip_and_audit_verification`, `test_wrong_key_fails_audit_verification`, `test_audit_anchor_detects_truncation`, `test_verify_audit_requires_an_anchor_unless_explicitly_waived`, recovery drill R1 |
| console: localhost binding, API URL from server configuration, API text in code spans | `test_the_console_binds_to_localhost_by_configuration`, `test_the_api_url_is_server_configuration_not_a_login_field`, `test_console_renders_api_text_as_code_spans_with_no_links` |
| CSV uploads capped at 200,000 readings | `test_csv_uploads_are_capped_by_record_count` |

## 3. Dependency audit

`product/scripts/osv_audit.py` queries OSV.dev for every pin in `requirements.lock.txt` (`product/evidence/security/osv_audit.md`, 2026-10-18). Result: 94 packages, 56 OSV records in 3 packages. Most issues appear twice, once as a GHSA record and once as its PYSEC alias. **Merged by alias, they are 29 distinct issues** (counted from `osv_audit.json`).

| package | pinned | distinct issues (OSV records) | exposure in the platform | action |
|---|---|---|---|---|
| mlflow | 3.0.1 | 27 (52), including RCE, path traversal, SSRF and missing authorisation in its tracking server | **The platform never imports mlflow** (checked again on 2026-10-18: importing every platform module and the console client leaves `mlflow` absent from `sys.modules`). Only the competition pipeline's experiment tracking (`sentinelloop/tracking.py`) uses it, as a local file store; no MLflow server is run | platform deployments **must not install mlflow** (`DEPLOYMENT_GUIDE.md` uses a platform-only requirement set). Upgrading the development environment is PLANNED and needs a package download (approval pending). The listed fixes go up to 3.15.0; three advisories list no fixed version (GHSA-7qhf-v65m-g5f3, GHSA-g6pg-52vf-843h, GHSA-wf7f-8fxf-xfxc) |
| pyarrow | 20.0.0 | 1 (2): use-after-free reading Arrow IPC files with pre-buffering; fixed in 23.0.1 | installed in platform deployments, because Streamlit (the console) requires it, and loaded by pandas; the platform code does not read Arrow IPC files | upgrade to ≥ 23.0.1: PLANNED (download approval pending) |
| pytest | 8.4.2 | 1 (2): tmpdir handling; fixed in 9.0.3 | development and test only | upgrade: PLANNED (download approval pending) |

`requirements-platform.txt` pins only direct dependencies. Transitive versions come from the development lock (`-c requirements.lock.txt`), and the audit above ran against that whole lock, not against a platform-only set. A hash-locked, platform-only lock audited on its own is PLANNED.

## 4. Not reviewed or not done

- External penetration test; review of TLS and reverse-proxy configuration on a real host.
- Review of a customer's identity integration (SSO/OIDC). Not implemented.
- Run of the CMMS connector against a real Odoo sandbox (pending image-download approval), and review of a customer CMMS user's privileges.
- Role checks inside the services that rely on the API check alone (`THREAT_MODEL.md` E1).
- Supply-chain controls beyond pinned versions: no hash-pinned requirements, no SBOM signing. PLANNED.
- Load and denial-of-service behaviour beyond the in-process limits. The load test measured throughput, not attack resistance.
- Data-protection review against India's DPDP Act. R5 lists duties, but they were not verified against the Act's text in this workspace.
