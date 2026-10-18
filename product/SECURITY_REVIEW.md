# Security review

**Date:** 2026-10-18.
**Scope:** the product platform (`src/sentinelloop/app`, the REST API, the admin CLI, the CMMS integration) on branch `product/platform`.
**Reviewers:** the engineering lead plus an automated code security review that runs on each commit. **No external penetration test has been done.** Nothing here is a compliance claim or certification.

The threat model is `THREAT_MODEL.md`. This document records what was checked, what was found, and what was done.

## 1. Findings from the automated reviews, and their resolution

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

**Acknowledged, not changed:** model bundles are Python pickles. Loading arbitrary pickles executes code. Mitigation: a bundle is loaded only after its SHA-256 matches the value recorded at registration (the registry is the trust anchor), and bundles come only from our packaging code. The residual risk is in `THREAT_MODEL.md` T3 (planned: signed manifests).

## 2. Controls verified by tests

| control | test(s) |
|---|---|
| every API route except health, ready and docs requires credentials (walks all routes) | `test_every_route_except_health_and_docs_requires_credentials` |
| role permissions enforced (403), and enforced again inside the services | `test_roles_are_enforced_with_403`, role tests in the workflow, planning, model and integration modules |
| keys stored only as hashes; listings never return hashes | `test_missing_or_wrong_credentials_are_401_and_api_keys_are_stored_hashed`, `test_user_administration_is_admin_only_and_keys_are_shown_once` |
| scrypt passwords, minimum length | `test_password_hashing_uses_scrypt_and_rejects_short_passwords` |
| errors carry no internals | `test_validation_errors_are_422_without_internal_details`, `test_an_unexpected_server_error_is_a_json_500_with_a_request_id_and_no_internals` |
| integration secrets never stored; CMMS `debug` tracebacks never stored | `test_secrets_are_never_stored_in_the_database`, `test_permanent_errors_go_to_dead_letters_without_leaking_server_internals_and_can_be_requeued` |
| integration host allowlist, https unless local | `test_targets_must_be_on_the_host_allowlist_and_use_https_unless_local` |
| webhook signatures and replay window | `test_webhook_signatures_verify_and_reject_tampering_and_replays` |
| tamper evidence of the audit chain, including truncation and the wrong key | `test_backup_restore_round_trip_and_audit_verification`, `test_wrong_key_fails_audit_verification`, recovery drill R1 |

## 3. Dependency audit

`product/scripts/osv_audit.py` queries OSV.dev for every pin in `requirements.lock.txt` (`product/evidence/security/osv_audit.md`, 2026-10-18). Result: 94 packages, **56 advisories in 3 packages.**

| package | pinned | advisories | exposure in the platform | action |
|---|---|---|---|---|
| mlflow | 3.0.1 | 52, including RCE, path traversal, SSRF and missing authorisation in its tracking server | **The platform never imports mlflow** (checked: importing every platform module leaves `mlflow` absent from `sys.modules`). Only the competition pipeline's experiment tracking (`sentinelloop/tracking.py`) uses it, as a local file store; no MLflow server is run | platform deployments **must not install mlflow** (`DEPLOYMENT_GUIDE.md` uses a platform-only requirement set). Upgrading the development environment to mlflow ≥ 3.15.0 is PLANNED and needs a package download (approval pending) |
| pyarrow | 20.0.0 | 2 (one issue: use-after-free reading Arrow IPC files with pre-buffering; fixed in 23.0.1) | loaded through pandas; the platform does not read Arrow IPC files | upgrade to ≥ 23.0.1: PLANNED (download approval pending) |
| pytest | 8.4.2 | 2 (one issue: tmpdir handling; fixed in 9.0.3) | development and test only | upgrade: PLANNED (download approval pending) |

## 4. Not reviewed or not done

- External penetration test; review of TLS and reverse-proxy configuration on a real host.
- Review of a customer's identity integration (SSO/OIDC). Not implemented.
- Supply-chain controls beyond pinned versions: no hash-pinned requirements, no SBOM signing. PLANNED.
- Load and denial-of-service behaviour beyond the in-process limits. The load test measured throughput, not attack resistance.
- Data-protection review against India's DPDP Act. R5 lists duties, but they were not verified against the Act's text in this workspace.
