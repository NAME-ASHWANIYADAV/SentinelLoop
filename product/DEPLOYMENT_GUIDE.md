# Deployment guide

| item | status |
|---|---|
| the procedure below | tested **on one Windows 11 development laptop** (load test L1, recovery drill R1, console checked in a browser against a local synthetic demo site) |
| deployment on a customer server | **never done** |
| deployment on a hardened Linux host | **never done** |
| production readiness | **not claimed** (`PRODUCT_STATUS.md`) |

## 1. What gets deployed

| component | process | binds to |
|---|---|---|
| REST API | `python -m sentinelloop.app.admin serve` (uvicorn, one process) | 127.0.0.1:8080 by default |
| Operator console | `streamlit run src/sentinelloop/console/app.py`, started **from the repository root** so that `.streamlit/config.toml` applies | 127.0.0.1:8501 (`.streamlit/config.toml`: `address = "127.0.0.1"`, `port = 8501`, `headless = true`; `[client] showErrorDetails = "none"`, so the browser shows a generic message and never a traceback with server paths) |
| Reverse proxy (not ours) | e.g. nginx or Caddy: TLS, external access, request limits | 443 |
| Scheduled jobs | data loads, assessments, recommendations (which also bring back deferred orders), CMMS dispatch, backup and audit verification (§6) | — |
| Data | one SQLite file (WAL), model bundle directory, backups and their anchor files (anchors also copied off the host) | local disk |

If the console is started from another directory, Streamlit does not read `.streamlit/config.toml`: its own defaults listen on every interface and show full error details in the browser. Pass `--server.address 127.0.0.1 --client.showErrorDetails none` in that case. The console is a client of the API only: it needs no database access and no audit key.

## 2. Requirements

- Python 3.12 (as tested).
- About 1 GB RAM for one site at the tested scale. In the L1 re-run, 50 turbines × 8 days used 69.0 MB of database (`product/evidence/load/l1.md`). That is about 0.17 MB per turbine-day of 10-minute SCADA (10 signals, including indexes and audit); 100 turbines for a year is roughly 6 GB. A retention policy is PLANNED.
- Install **the platform requirement set only**. It excludes mlflow, which the platform never imports (`SECURITY_REVIEW.md` §3):

```bash
python -m venv .venv
```
```bash
.venv/bin/pip install -r requirements-platform.txt -c requirements.lock.txt
```

## 3. Secrets and configuration

**Environment** (secrets never go on the command line or into the database):

| variable | content |
|---|---|
| `SENTINELLOOP_AUDIT_KEY` | 32+ random bytes, hex. Generate once (`python -c "import secrets; print(secrets.token_hex(32))"`) and keep it in the host's secret store, **not** on the same disk as the database backups. Losing it makes old audit events unverifiable; leaking it lets someone forge them |
| `SENTINELLOOP_AUDIT_KEY_ID` | a label, e.g. `site1-2026-10` |
| `SENTINELLOOP_DB` | database path |
| `SENTINELLOOP_INTEGRATION_HOSTS` | comma-separated CMMS/webhook host names the connector may call. Checked at registration and again at every dispatch outside shadow mode: removing a host stops delivery to it |
| `SENTINELLOOP_CRED_*` | CMMS API keys and webhook secrets (at least 32 characters for a webhook), named in each integration target's config. A target cannot name any other variable (`INTEGRATION_GUIDE.md` §1) |
| `SENTINELLOOP_API_URL` | for the console only: the API base URL, e.g. `http://127.0.0.1:8080/api/v1` (the default). It is server configuration; users never type it (SSRF fix, `SECURITY_REVIEW.md` finding 12). Each user signs in with their own API key |

**Files** read by `serve`:

| file | flag | content |
|---|---|---|
| platform policy | `--policy` (default `configs/platform.yaml`) | data-quality limits, scope tolerances, state thresholds, `assess_at` and `max_assessment_age_hours`, per asset type. Its SHA-256 is stored with every assessment |
| site decision parameters | `--decision-config FILE` (example: `configs/decision.example.yaml`) | downtime and labour cost per hour, default due dates, rejection-suppression periods, RUL acceptance probabilities, job names. Refused when the file is loaded (`decision.load_config_text`): unknown keys; `p_accept` or `p_safety` outside [0, 1); negative costs; `default_due_h` or `reject_suppress_h` without exactly the keys P1, P2 and P3, or with hours above 8,760 (one year; due dates must also be above 0); booleans, strings, null, NaN or infinite values where a number belongs; empty job names; an `urgent_job` or `inspection_job` named like a data or review job. A file refused at load stops `serve` with a Python traceback (`ValueError`) and exit code 1: `admin.main` turns only configuration errors into exit 2. `serve` also refuses to start (exit 2) when a registered asset type lacks the file's `inspection_job` (`admin.cmd_serve`); the urgent, data and review jobs fall back to the inspection job on a type that lacks them. Without a file the server prints a warning and runs with placeholder defaults (downtime cost 0), and `/api/v1/ready` reports `decision_config` as "placeholder defaults ..." instead of "site-configured" (PD-24, PD-28) |

**Sites that deliver periodic exports** (for example daily OEM-portal files) instead of a live feed: set `assess_at: latest_reading` for the asset type in the policy file, so that the default assessment instant is the latest reading rather than "now", and keep `max_assessment_age_hours` above the export interval (the wind default is 26 h). Then replay each export with `assess-range` (§6) as soon as it is loaded, before any assessment at the default instant (the scheduled `/assess` or the console's "Assess now"). Do not also assess such assets at "now": once an assessment for "now" is applied, every earlier instant is stored as a replay. A replay that finds URGENT_REVIEW or INSPECTION_RECOMMENDED not already recorded for its instant still raises the latch (PD-28), but a replay never lowers a latch or moves the live state, so the export's data failures, recoveries and normal readings are not applied (PD-17).

## 4. First start

```bash
python -m sentinelloop.app.admin init --db /srv/sentinelloop/plant.db
```
```bash
python -m sentinelloop.app.admin create-admin --db /srv/sentinelloop/plant.db --user it-admin --name "IT admin"
```

The admin key is printed **once**; store it in the password manager. Then:
- **Through the API as that admin:** create the other users and their keys (`/api/v1/users`), the assets (`POST /api/v1/assets`), technicians and parts.
- **On the host, with the library:** create the site and the asset types (there is no API route for them: KNOWN_LIMITATIONS P4; the adapters' `ensure_site_and_type` functions do it, see `product/scripts/demo_site.py`), and register the model bundle (`modelreg.register`, no API route). Registration hashes `bundle.pkl` and refuses a bundle that does not match its manifest.
- **Through the API as a reliability engineer:** approve the model (`POST /api/v1/models/{id}/decision`) and commission the turbines (`POST /api/v1/assets/{id}/baseline`) (`USER_WORKFLOWS.md` W1–W3).

```bash
python -m sentinelloop.app.admin serve --db /srv/sentinelloop/plant.db --port 8080 --behind-proxy --trusted-proxy 127.0.0.1 --decision-config /srv/sentinelloop/decision.yaml
```

- `--behind-proxy` makes the rate limiter see real client addresses. Without it, all requests appear to come from the proxy.
- `--rate-limit CAPACITY,REFILL_PER_SECOND` (default `120,2.0`) sets each user's token bucket. It also sets the largest `assess-range` call (§6).
- With `--decision-config`, `serve` checks the file against the asset types registered at start-up and exits with code 2, naming them, if one lacks the file's `inspection_job`. Restart `serve` after adding an asset type, so the check covers it.
- `/api/v1/ready` reports database, schema currency, approved models, audit-key status and whether the decision parameters are site-configured. Use it as the health check; expect `decision_config: site-configured` before any pilot.

Start the console from the repository root:

```bash
SENTINELLOOP_API_URL=http://127.0.0.1:8080/api/v1 streamlit run src/sentinelloop/console/app.py
```

## 5. Reverse proxy

- **TLS** terminates at the proxy. The API and the console bind to localhost only.
- **Limits.** Set a request-body limit at the proxy as well as the API's 10 MiB, and a per-client rate limit. The API's limiter is per process; only the exact paths `/api/v1/health` and `/api/v1/ready` are exempt from it.
- **Unauthenticated paths.** `/api/v1/health`, `/api/v1/ready`, `/api/v1/docs` and `/api/v1/openapi.json` need no key. This is accepted (finding security-10): they reveal the schema version, the approved-model count, the audit-key and decision-config status and the API surface, but no data or secrets. Block them at the proxy for clients outside the site network if that surface should not be visible.
- **Console access.** Restrict it to the site network or a VPN. The console signs in with personal API keys, which do not expire; it has a sign-out button but no idle timeout.

## 6. Scheduled jobs (cron or Windows Task Scheduler)

Nothing runs inside the server on a timer (KNOWN_LIMITATIONS P5). Operations must schedule these jobs; if the assessment job stops, assets show ASSESSMENT_OVERDUE.

| job | frequency | call |
|---|---|---|
| data load | per SCADA export or feed interval | `POST /api/v1/ingest/csv` (at most 200,000 readings per batch: split larger files) or `/ingest/readings`, with an `integration` key; alert when `rows_rejected` > 0 |
| assessments | after each load | live feeds: `POST /api/v1/assets/{id}/assess` per asset (L1 re-run: 50 turbines in 7.2 s with 4 clients). Export-fed sites: `POST /api/v1/assets/{id}/assess-range` with `start`, `end` and `step_minutes` (1–1440, default 60) covering the whole new export, from its first reading to its last, oldest first, before any `/assess` call for that asset. The job must respect the `assess-range` limits below the table. When a response reports `replays_escalated` > 0, run the recommendations job next and check its result for that asset. `created`, `escalated` or `linked` (or `unchanged`, naming an open order that already covers the warning) means the raised latch has its order. `already_decided` means it has none: the latest applied assessment already produced an order for that job, even one since completed (`decision._create_checked`). `suppressed` means a rejection still holds. In either case a planner raises the order by hand or dismisses the warning with a reason (`OPERATIONS_RUNBOOK.md` §1 step 3) |
| recommendations, and the return of deferred orders | after assessments, and **at least daily** even when no data arrive | `POST /api/v1/decisions/generate` (optionally `?site_id=`). The same call returns deferred orders whose date has passed to PENDING_APPROVAL (`workorders.reactivate_due`). There is no separate reactivation call: deferred work comes back only when this job runs, and only for the site given when `site_id` is used. A recommendation or reactivation that fails is returned with `action: error` and audited as `decision.error`, and the run goes on with the other assets and orders; alert on any `error` |
| CMMS dispatch | every 5–15 min | `POST /api/v1/integrations/{id}/dispatch` with an `integration` or admin key (shadow by default; tested against a contract test double only, never against real Odoo: `INTEGRATION_GUIDE.md`). It also mirrors withdrawals, deferrals and completions onto requests already in the CMMS. At most 200 orders per run. One run per target at a time: a run that overlaps another returns `busy: true` and sends nothing, and the lease of a crashed run lapses after 10 minutes. A non-empty `stopped` gives the reason whenever a run sent less than it could: another run held the lease (then `busy` is true, so check `busy` first), the run's own lease lapsed, or the target's mode was changed or the target disabled during the run (`integration.STOPPED`) |
| staleness check | hourly | `GET /api/v1/ingest/staleness?max_age_h=<expected delivery interval>` (the API default is 6 h); alert on any stale required signal |
| overdue check | daily, or in monitoring | `GET /api/v1/assets`: any `ASSESSMENT_OVERDUE` label means assessments have stopped being applied for that asset |
| backup | at least daily; RPO = the interval | `admin backup --to <dated path>` writes the backup and `<backup>.anchor.json`; copy both off the host, and keep every anchor |
| audit verification | daily | `admin verify-audit --db <live database> --anchor <the previous backup's anchor, copied back from off the host>`; alert on any exit other than 0 (1: the chain is invalid, or no anchor was found; 2: a configuration error, such as a malformed anchor or a missing audit key). Without `--anchor` (and with no `<db>.anchor.json`) it exits 1, unless `--allow-no-anchor` is given, which checks internal consistency only. Verifying a backup against the anchor written beside it shows only that the copy is self-consistent. Direct edits of state tables are not detected (PD-22). An anchor file without an integer `seq` and a 64-hex `hash` is a configuration error (exit 2). Do not use `GET /api/v1/audit/verify` without `anchor_seq` and `anchor_hash`, or the console's "Verify the audit chain" button, for this check: neither uses an anchor, so a truncated chain still shows `valid: True`. Both say so: the response carries `anchor_checked: false`, and the console shows "not verified against an anchor" |

**`assess-range` limits** (`api.assess_range`, `health.assess_range`; KNOWN_LIMITATIONS P13). The assessment job must handle all of them:
- **Size.** A call costs one rate-limit token per 10 steps, rounded up. With the shipped `--rate-limit 120,2.0`, a call can have at most 1,200 steps; a longer range is refused with 422 ("split the range"). Only a bucket of 200 tokens or more reaches the absolute cap of 2,000 steps. The refill pays for about 20 steps per second per key, shared with that key's other calls.
- **Concurrency.** One running range per user and two per server. Another range gets 429 with `Retry-After`, and so does a range the key's bucket cannot pay for yet. The job must wait that many seconds and resend, and must not send ranges in parallel under one key.
- **Instants.** The whole range is checked before any step is assessed, and a refused range stores nothing. Refused: an `end` later than now plus 5 minutes, an instant before 2000-01-01, or an instant more than 5 minutes before the asset's first reading.
- **Response.** `assessments`, `applied`, `replays_escalated`, `states` and `asset_state`. `replays_escalated` counts the replays that raised the latch; they are not counted in `applied`.

## 7. Upgrades

1. Back up.
2. Install the new version.
3. Run `admin init`. Migrations are forward-only and checksummed; an edited migration is refused.
   - 0007 sets the start of latches that existed before 0006 to the time their state was last written, so older work cannot clear them.
   - 0008 backfills the last applied assessment instant and time on databases upgraded from before 0006. Each instant counts at most up to the time it was stored plus 5 minutes. Back-dated assessments are then replays there too, and ASSESSMENT_OVERDUE works. An asset whose state row has no stored assessments shows ASSESSMENT_OVERDUE until its next applied assessment.
   - 0009 adds the CMMS re-verification time (`verify_after_ms`, `INTEGRATION_GUIDE.md` §3.3).
4. Before restarting, check the decision config with the new version: `python -c "from sentinelloop.app import decision; decision.load_config('/srv/sentinelloop/decision.yaml')"`. The loader is stricter than before and refuses files the previous version accepted: a `default_due_h` or `reject_suppress_h` map without all of P1, P2 and P3, numbers given as strings or booleans, NaN or infinite values, `p_accept` or `p_safety` of 1 or more, a due date of 0 h, hours above 8,760, and empty job names or an urgent or inspection job named like a data or review job (§3). Such a file stops `serve` with a `ValueError` traceback and exit code 1. Then restart the API. If `--decision-config` names an `inspection_job` that a registered asset type lacks, `serve` now refuses to start, with exit code 2 (§4).
5. Check `/ready` for `schema_current: true`.
6. Check each integration target's stored config (admin: `GET /api/v1/integrations`; KNOWN_LIMITATIONS S11). Config values are now checked at registration, but a target stored by an earlier version is checked only at each live dispatch:
   - a `timeout_s` above 120 is used as 120 s;
   - a `max_attempts` outside 1–100 is still used;
   - every item becomes a dead letter when the stored config has a `database` that is not an Odoo database name (letters, digits, `_`, `.`, `-`, starting with a letter or digit, at most 128 characters), a credential variable name that does not start with `SENTINELLOOP_CRED_`, a `timeout_s` or `max_attempts` that cannot be used as a number, or a `timeout_s` that is not above 0 or not finite (`integration.check_config`, `_settings`).

   There is no route to change a stored config: register the target again under a new id. The new target has no record of the requests the old one created, and a first send never adopts an existing request. When it goes live, it creates a new request for every eligible order, including those the old target already delivered (`integration._recovery_evidence` reads the log of one target only). Agree with the CMMS owner how those duplicates will be handled before the new target leaves shadow mode.

To roll back, restore the pre-upgrade backup to a new path and start the previous version on it. A new schema cannot be opened by an older version, so do not downgrade in place.

## 8. Not covered (PLANNED)

- Linux service units or a container image for the platform itself.
- High availability. One process and one SQLite file is the design (PD-06); the recovery drill re-run measured a restore-to-ready of 6.34 s on the test laptop (`product/evidence/recovery/r1.md`).
- A built-in job scheduler (§6).
- Centralised log shipping, and logging configuration. `admin serve` starts uvicorn with its default logging (`log_level="info"`, no `log_config`) and never configures the `sentinelloop.*` loggers, so they run at WARNING with no handler. As a result:
  - The API's JSON line per request (request id, method, path, status, duration, user; `api.py`, request envelope) is **not emitted**.
  - uvicorn's own access log goes to stdout: client address, method, path and status, with no request id or user.
  - Unhandled errors (`unhandled error <request_id>` with the traceback), model-unavailable warnings and scoring failures reach **stderr** through Python's last-resort handler, as bare messages without timestamps.
  - Capture both stdout and stderr with the host's tools. Configuring the `sentinelloop` loggers (INFO to stdout) in `serve` is PLANNED.
