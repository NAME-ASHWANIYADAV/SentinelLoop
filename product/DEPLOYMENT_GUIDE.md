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
| Operator console | `streamlit run src/sentinelloop/console/app.py`, started **from the repository root** so that `.streamlit/config.toml` applies | 127.0.0.1:8501 (`.streamlit/config.toml`: `address = "127.0.0.1"`, `port = 8501`, `headless = true`) |
| Reverse proxy (not ours) | e.g. nginx or Caddy: TLS, external access, request limits | 443 |
| Scheduled jobs | data loads, assessments, recommendations (which also bring back deferred orders), CMMS dispatch, backup and audit verification (§6) | — |
| Data | one SQLite file (WAL), model bundle directory, backups and their anchor files (anchors also copied off the host) | local disk |

If the console is started from another directory, Streamlit does not read `.streamlit/config.toml` and its own default listens on every interface. Pass `--server.address 127.0.0.1` in that case. The console is a client of the API only: it needs no database access and no audit key.

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
| site decision parameters | `--decision-config FILE` (example: `configs/decision.example.yaml`) | downtime and labour cost per hour, default due dates, rejection-suppression periods, RUL acceptance probabilities. Unknown keys and negative values are refused. Without a file the server prints a warning and runs with placeholder defaults (downtime cost 0), and `/api/v1/ready` reports `decision_config` as "placeholder defaults ..." instead of "site-configured" (PD-24) |

**Sites that deliver periodic exports** (for example daily OEM-portal files) instead of a live feed: set `assess_at: latest_reading` for the asset type in the policy file, so that the default assessment instant is the latest reading rather than "now", and keep `max_assessment_age_hours` above the export interval (the wind default is 26 h). Then replay each export with `assess-range` (§6). Do not also assess such assets at "now": once an assessment for "now" is applied, every earlier instant is stored as a replay that never moves the live state (PD-17).

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
| assessments | after each load | live feeds: `POST /api/v1/assets/{id}/assess` per asset (L1 re-run: 50 turbines in 7.2 s with 4 clients). Export-fed sites: `POST /api/v1/assets/{id}/assess-range` with `start`, `end` and `step_minutes` (1–1440, default 60) covering the new export, oldest first; at most 2,000 steps per call |
| recommendations, and the return of deferred orders | after assessments, and **at least daily** even when no data arrive | `POST /api/v1/decisions/generate` (optionally `?site_id=`). The same call returns deferred orders whose date has passed to PENDING_APPROVAL (`workorders.reactivate_due`). There is no separate reactivation call: deferred work comes back only when this job runs, and only for the site given when `site_id` is used |
| CMMS dispatch | every 5–15 min | `POST /api/v1/integrations/{id}/dispatch` with an `integration` or admin key (shadow by default). It also mirrors withdrawals, deferrals and completions onto requests already in the CMMS |
| staleness check | hourly | `GET /api/v1/ingest/staleness?max_age_h=<expected delivery interval>` (the API default is 6 h); alert on any stale required signal |
| overdue check | daily, or in monitoring | `GET /api/v1/assets`: any `ASSESSMENT_OVERDUE` label means assessments have stopped being applied for that asset |
| backup | at least daily; RPO = the interval | `admin backup --to <dated path>` writes the backup and `<backup>.anchor.json`; copy both off the host, and keep every anchor |
| audit verification | daily | `admin verify-audit --db <live database> --anchor <the previous backup's anchor, copied back from off the host>`; alert on exit 1. Without `--anchor` (and with no `<db>.anchor.json`) it exits 1, unless `--allow-no-anchor` is given, which checks internal consistency only. Verifying a backup against the anchor written beside it shows only that the copy is self-consistent. Direct edits of state tables are not detected (PD-22). Do not use `GET /api/v1/audit/verify` without `anchor_seq` and `anchor_hash`, or the console's "Verify the audit chain" button, for this check: neither uses an anchor, so a truncated chain still shows `valid: True` |

## 7. Upgrades

1. Back up.
2. Install the new version.
3. Run `admin init`. Migrations are forward-only and checksummed; an edited migration is refused. (Migration 0007 sets the start of latches that existed before 0006 to the time their state was last written, so older work cannot clear them.)
4. Restart the API.
5. Check `/ready` for `schema_current: true`.

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
