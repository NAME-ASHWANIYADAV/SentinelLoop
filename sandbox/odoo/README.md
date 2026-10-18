# Odoo Community sandbox (local integration tests only)

**Why Odoo.** Research R5 found it to be the only free, local and unrestricted CMMS with a documented API: the Maintenance app plus the JSON-2 API, both LGPL-3. This sandbox is a **test environment, not a customer integration**. Passing tests here shows that the connector works against real Odoo software. It says nothing about any customer's CMMS configuration.

**Images.** `odoo:19.0-20261015` (Docker Hub, about 0.70 GB compressed) and `postgres:16`.

```bash
bash sandbox/odoo/setup.sh
```
```bash
set -a; . sandbox/odoo/.env.local; set +a; .venv/Scripts/python.exe -m pytest tests/test_app_odoo_sandbox.py -v
```
```bash
docker compose -f sandbox/odoo/docker-compose.yml --env-file sandbox/odoo/.env.local down
```

- The ports are bound to 127.0.0.1 only.
- `down -v` also deletes the sandbox data volumes.
- The API key expires after 30 days. Re-run `setup.sh` to issue a new one.
