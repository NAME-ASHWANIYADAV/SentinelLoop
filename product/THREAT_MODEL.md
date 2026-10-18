# Threat model

**Scope:** a single-site deployment of SentinelLoop (`SYSTEM_ARCHITECTURE.md`).
**Method:** assets, trust boundaries and entry points, then STRIDE per entry point, with the mitigation and its status.
**Status of evidence:** automated tests and an automated code security review; findings were fixed test-first (PD-14). **No penetration test or external security review has been done.** This model is not a compliance claim.

## 1. What must be protected

| asset | why it matters |
|---|---|
| Integrity of recommendations and states | a manipulated reading, model or rule could hide an urgent condition or create needless work orders |
| Audit trail | the evidence of who decided what; needed for any post-incident review |
| Model artefacts | a replaced pickle executes code on load |
| Credentials: API keys, passwords, the audit key | they give access or the ability to forge audit events |
| Customer operational data: SCADA, work orders, technician names | commercially sensitive; personal data in technician fields (India's DPDP Act, per R5, not re-verified) |
| Availability of the service | lost assessments mean lost warnings; the plant itself does not depend on SentinelLoop (§4) |

## 2. Trust boundaries and entry points

1. **REST API** (`/api/v1`). Clients: integration jobs, the operator console, scripts.
2. **File and CSV ingestion** through the API: content from SCADA exports.
3. **Model bundle directory** on disk.
4. **Database file** and its backups on disk.
5. **Administration CLI** on the host. It reads its secrets from the environment.
6. **CMMS connection** (Phase 6): an outbound call to the CMMS API, plus any inbound webhook.
7. **Downloaded public datasets** (G0): untrusted archives.

## 3. STRIDE

| # | threat | entry | mitigation | status |
|---|---|---|---|---|
| S1 | Spoofing a user or integration | API | 256-bit API keys, stored as SHA-256 and compared in constant time; scrypt passwords (min 12 chars); deactivation revokes keys; every route but health/ready needs a key (test walks all routes) | IMPLEMENTED_AND_TESTED |
| S2 | Credential theft from the database | DB file | no plaintext keys or passwords stored; the user listing never returns hashes | IMPLEMENTED_AND_TESTED |
| T1 | Tampering with readings to hide a fault | ingestion | unit and range contract; conflicts rejected rather than overwritten; batches hashed and audited; implausible values flagged | IMPLEMENTED_AND_TESTED. A compromised source system sending plausible false data is **not** detectable by the platform (residual) |
| T2 | Tampering with the audit trail | DB file | HMAC chain with a key outside the database; anchor exported with backups detects truncation; fail-closed key (PD-07) | IMPLEMENTED_AND_TESTED. An attacker holding both the DB and the audit key can rewrite history (residual: protect the key in a secret store) |
| T3 | Replacing a model bundle (code execution through pickle) | bundle dir | the registry records the SHA-256 at registration; loading refuses a mismatch before unpickling; bundles come only from our packaging code | IMPLEMENTED_AND_TESTED. An attacker who can write both the bundle and the registry row can execute code (residual: file permissions; PLANNED: signed manifests) |
| T4 | Changing policy thresholds silently | config file | the policy SHA-256 is stored with each assessment | IMPLEMENTED. Change control for the file itself is operational (runbook) |
| R1 | Denying an approval, dismissal or override | API | every state change is audited with actor, role and reason; reasons are mandatory for dismissals, rejections, deferrals and asset changes | IMPLEMENTED_AND_TESTED |
| I1 | Reading another role's sensitive data | API | role permissions; audit history of `user` and other non-operational entities needs `audit.read` (PD-14) | IMPLEMENTED_AND_TESTED |
| I2 | Leaking internals through errors | API | JSON errors without stack traces; request id for correlation | IMPLEMENTED_AND_TESTED |
| I3 | CSV/spreadsheet formula injection through exported text | export | formula-leading cells are prefixed (PD-14) | IMPLEMENTED_AND_TESTED |
| I4 | Personal data in technician fields | DB, exports | PLANNED: pseudonymised analysis copies; retention policy per the data-sharing agreement | PLANNED |
| D1 | Request floods | API | token-bucket rate limit per user or client address; LRU-bounded bucket table | IMPLEMENTED_AND_TESTED. In-process only; behind several processes the limit multiplies (residual; put a reverse proxy limit in front) |
| D2 | Huge or endless request bodies | API | 10 MiB cap counted while the body streams (chunked included) | IMPLEMENTED_AND_TESTED |
| D3 | Pathological scheduling problems | API | horizon and slot bounds; MILP time limit with greedy fallback | IMPLEMENTED_AND_TESTED |
| E1 | A role performing a higher role's action | API and services | permission check at the API, and again inside every service; workflow transitions checked by role | IMPLEMENTED_AND_TESTED |
| E2 | Malicious content in downloaded datasets | G0 | own directory; `python -I`; nothing executed from archives; checksum verified | PLANNED (procedure written; DATA_STRATEGY §3) |
| E3 | CMMS credentials misused or over-privileged | Phase 6 | PLANNED: a dedicated least-privilege CMMS user; shadow (read-only) mode by default; outbound host allowlist; signed webhooks | PLANNED |

## 4. Safety boundary

SentinelLoop is **advisory**. It has no connection to control systems and cannot start, stop or reconfigure equipment.
- The worst outcome of a compromise is a wrong or missing recommendation. That is serious, so latching states and human approval are designed in, but it is not direct physical harm caused by the platform.
- **Plant safety must never depend on SentinelLoop.** A turbine's own protection systems and the operator's procedures stay in charge. This is stated to customers and in `RELIABILITY_AND_SAFETY.md`.

## 5. Deployment assumptions

These are written into `DEPLOYMENT_GUIDE.md`.
- TLS is terminated by a reverse proxy in front of the API; the API binds to localhost.
- The audit key and the database live on different storage, or the key is in a secret store.
- Host access is restricted to administrators; the bundle directory and database file are not world-writable.
- Backups are encrypted at rest by the hosting environment, and their anchors are kept apart from them.

## 6. Open items

- External penetration test before any customer deployment that is reachable beyond one host.
- Signed model manifests (an asymmetric signature) so that a database writer cannot also register a malicious bundle.
- `pip-audit` of the locked dependencies (Phase 7, `SECURITY_REVIEW.md`).
- SSO or OIDC for customer identity providers.
