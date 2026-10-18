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
| Operator console | `streamlit run src/sentinelloop/console/app.py` | 127.0.0.1:8501 by default |
| Reverse proxy (not ours) | e.g. nginx or Caddy: TLS, external access, request limits | 443 |
| Scheduled jobs | data loads (`/ingest/*`), assessments, `decisions/generate`, `integrations/{id}/dispatch`, `admin backup` | — |
| Data | one SQLite file (WAL), model bundle directory, backups and their anchor files | local disk |

## 2. Requirements

- Python 3.12 (as tested).
- About 1 GB RAM for one site at the tested scale. L1 used 68.8 MB of database for 50 turbines × 8 days. That is about 0.17 MB per turbine-day of 10-minute SCADA (10 signals, including indexes and audit); 100 turbines for a year is roughly 6 GB. A retention policy is PLANNED.
- Install **the platform requirement set only**. It excludes mlflow, which the platform never imports (`SECURITY_REVIEW.md` §3):

```bash
python -m venv .venv
```
```bash
.venv/bin/pip install -r requirements-platform.txt -c requirements.lock.txt
```

## 3. Secrets and configuration (environment only)

| variable | content |
|---|---|
| `SENTINELLOOP_AUDIT_KEY` | 32+ random bytes, hex. Generate once (`python -c "import secrets; print(secrets.token_hex(32))"`) and keep it in the host's secret store, **not** on the same disk as the database backups. Losing it makes old audit events unverifiable; leaking it lets someone forge them |
| `SENTINELLOOP_AUDIT_KEY_ID` | a label, e.g. `site1-2026-10` |
| `SENTINELLOOP_DB` | database path |
| `SENTINELLOOP_INTEGRATION_HOSTS` | comma-separated CMMS/webhook hosts the connector may call |
| `SENTINELLOOP_CRED_*` | CMMS API keys and webhook secrets, named in each integration target's config |
| `SENTINELLOOP_API_URL` | for the console: the API base URL |

## 4. First start

```bash
python -m sentinelloop.app.admin init --db /srv/sentinelloop/plant.db
```
```bash
python -m sentinelloop.app.admin create-admin --db /srv/sentinelloop/plant.db --user it-admin --name "IT admin"
```

The admin key is printed **once**; store it in the password manager. Then, through the API as that admin, create the other users and their keys (`/api/v1/users`), the site, the asset types and assets, technicians and parts. Register and approve the model bundle as a reliability engineer, and commission the turbines (`USER_WORKFLOWS.md` W1–W3).

```bash
python -m sentinelloop.app.admin serve --db /srv/sentinelloop/plant.db --port 8080 --behind-proxy --trusted-proxy 127.0.0.1
```

- `--behind-proxy` makes the rate limiter see real client addresses. Without it, all requests appear to come from the proxy.
- `/api/v1/ready` reports database, schema currency, approved models and audit-key status. Use it as the health check.

## 5. Reverse proxy

- **TLS** terminates at the proxy. The API and console bind to localhost only.
- **Limits.** Set a request-body limit at the proxy as well as the API's 10 MiB, and a per-client rate limit. The API's limiter is per process.
- **Console access.** Restrict it to the site network or a VPN. The console signs in with personal API keys.

## 6. Scheduled jobs (cron or Windows Task Scheduler)

| job | frequency | call |
|---|---|---|
| data load | per SCADA export | `POST /api/v1/ingest/csv` with an `integration` key; alert when `rows_rejected` > 0 |
| assessments | after each load | `POST /api/v1/assets/{id}/assess` per asset (L1: 50 turbines in 5 s with 4 clients) |
| recommendations | after assessments | `POST /api/v1/decisions/generate` |
| CMMS dispatch | every 5–15 min | `POST /api/v1/integrations/{id}/dispatch` (shadow by default) |
| staleness check | hourly | `GET /api/v1/ingest/staleness`; alert on any stale required signal |
| backup | at least daily; RPO = the interval | `admin backup --to <dated path>`; copy the backup and its `.anchor.json` off the host |
| audit verification | daily | `admin verify-audit` on the latest backup; alert on exit 1 |

## 7. Upgrades

1. Back up.
2. Install the new version.
3. Run `admin init`. Migrations are forward-only and checksummed; an edited migration is refused.
4. Restart the API.
5. Check `/ready` for `schema_current: true`.

To roll back, restore the pre-upgrade backup to a new path and start the previous version on it. A new schema cannot be opened by an older version, so do not downgrade in place.

## 8. Not covered (PLANNED)

- Linux service units or a container image for the platform itself.
- High availability. One process and one SQLite file is the design (PD-06); the recovery drill measured a restore-to-ready of 3.3 s on the test laptop.
- Centralised log shipping. The API logs one JSON line per request (request id, method, path, status, duration, user) to stdout. Forward stdout with the host's tools.
