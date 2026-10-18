#!/usr/bin/env bash
# Create the sandbox: generate a local DB password, start Postgres + Odoo, initialise a database with the
# Maintenance app (no demo data), and generate an API key. Everything stays on this machine.
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -f .env.local ]; then
  echo "ODOO_DB_PASSWORD=$(python -c 'import secrets; print(secrets.token_urlsafe(24))')" > .env.local
fi
set -a; . ./.env.local; set +a
docker compose --env-file .env.local up -d db
sleep 5
docker compose --env-file .env.local run --rm odoo odoo -d sandbox -i maintenance --without-demo=all --stop-after-init \
  --db_host=db --db_user=odoo --db_password="$ODOO_DB_PASSWORD"
docker compose --env-file .env.local up -d odoo
KEYLINE=$(docker compose --env-file .env.local exec -T odoo odoo shell -d sandbox --no-http --db_host=db --db_user=odoo \
  --db_password="$ODOO_DB_PASSWORD" < generate_key.py | grep '^SENTINELLOOP_ODOO_KEY=' | tail -1)
grep -v '^SENTINELLOOP_ODOO_' .env.local > .env.tmp || true
{ cat .env.tmp; echo "$KEYLINE"; echo "SENTINELLOOP_ODOO_URL=http://localhost:8069"; echo "SENTINELLOOP_ODOO_DB=sandbox"; } > .env.local
rm -f .env.tmp
echo "sandbox ready at http://localhost:8069 (credentials in sandbox/odoo/.env.local)"
