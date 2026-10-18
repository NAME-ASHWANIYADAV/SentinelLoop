"""Platform administration CLI: `python -m sentinelloop.app.admin <command>`.

Configuration comes from the environment, never from command-line secrets:
  SENTINELLOOP_AUDIT_KEY     audit HMAC key, hex (>= 64 hex characters) or `base64:<value>` (>= 32 bytes)
  SENTINELLOOP_AUDIT_KEY_ID  label stored with every audit event (default "configured")
  SENTINELLOOP_DB            database path (or --db)

Commands:
  init           create or migrate the database (forward-only, checksummed migrations)
  create-admin   bootstrap the first admin user and print its API key once (refused if an active admin exists)
  backup         consistent online copy (SQLite backup API) plus an audit-anchor file next to it
  restore        copy a backup to a new database path (never overwrites without --force), then check integrity
  verify-audit   verify the HMAC chain against an anchor (--anchor FILE, or <db>.anchor.json next to the database);
                 without an anchor truncation cannot be detected, so it fails unless --allow-no-anchor is given
  serve          run the REST API with uvicorn (bind to 127.0.0.1 by default; put TLS in front, see DEPLOYMENT_GUIDE)

Exit codes: 0 success, 1 the operation failed or found a problem, 2 configuration error.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import json
import os
import shutil
import sqlite3
import sys
from pathlib import Path

from . import auditlog, db as dbmod, security


class ConfigError(RuntimeError):
    pass


def audit_key_from_env() -> tuple[bytes, str]:
    raw = os.environ.get("SENTINELLOOP_AUDIT_KEY")
    if not raw:
        raise ConfigError("SENTINELLOOP_AUDIT_KEY is not set: generate one with `python -c \"import secrets; print(secrets.token_hex(32))\"` "
                          "and store it in the deployment's secret store")
    try:
        key = base64.b64decode(raw[7:], validate=True) if raw.startswith("base64:") else bytes.fromhex(raw)
    except (binascii.Error, ValueError) as e:
        raise ConfigError(f"SENTINELLOOP_AUDIT_KEY is neither hex nor base64:<value> ({type(e).__name__})") from e
    if len(key) < dbmod.MIN_AUDIT_KEY_BYTES:
        raise ConfigError(f"SENTINELLOOP_AUDIT_KEY must be at least {dbmod.MIN_AUDIT_KEY_BYTES} bytes")
    return key, os.environ.get("SENTINELLOOP_AUDIT_KEY_ID", "configured")


def _db_path(args) -> str:
    p = args.db or os.environ.get("SENTINELLOOP_DB")
    if not p:
        raise ConfigError("no database path: pass --db or set SENTINELLOOP_DB")
    return p


def _open(path: str) -> dbmod.Database:
    key, kid = audit_key_from_env()
    return dbmod.Database(path, audit_key=key, audit_key_id=kid)


def _out(obj):
    print(json.dumps(obj, default=str))


def cmd_init(args) -> int:
    d = _open(_db_path(args))
    applied = d.migrate()
    _out({"database": str(d.path), "applied": applied, "schema_version": d.schema_version()})
    return 0


def cmd_create_admin(args) -> int:
    d = _open(_db_path(args))
    with d.connect() as c:
        if c.execute("SELECT 1 FROM users WHERE role = 'admin' AND active = 1").fetchone():
            print("an active admin already exists; create further users through the API as that admin", file=sys.stderr)
            return 1
    security.create_user(d, args.user, args.name, "admin", actor="bootstrap")
    key = security.issue_api_key(d, args.user, actor="bootstrap")
    print("store this key now; it is shown only once and kept only as a hash", file=sys.stderr)
    _out({"user_id": args.user, "role": "admin", "api_key": key})
    return 0


def cmd_backup(args) -> int:
    d = _open(_db_path(args))
    dest = Path(args.to)
    if dest.exists() and not args.force:
        print(f"{dest} exists; refusing to overwrite (use --force)", file=sys.stderr)
        return 1
    d.backup(dest)
    with sqlite3.connect(dest) as c:
        c.row_factory = sqlite3.Row
        anchor = auditlog.anchor(c)
    Path(str(dest) + ".anchor.json").write_text(json.dumps(anchor), encoding="utf-8")
    _out({"backup": str(dest), "bytes": dest.stat().st_size, "anchor": anchor})
    return 0


def cmd_restore(args) -> int:
    src, target = Path(args.from_), Path(_db_path(args))
    if not src.exists():
        print(f"backup {src} not found", file=sys.stderr)
        return 1
    if target.exists() and not args.force:
        print(f"{target} exists; refusing to overwrite (use --force after moving the current database aside)", file=sys.stderr)
        return 1
    target.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(src) as s, sqlite3.connect(target) as t:
        s.backup(t)
    with sqlite3.connect(target) as t:
        ok = t.execute("PRAGMA integrity_check").fetchone()[0]
    anchor_file = Path(str(src) + ".anchor.json")
    if anchor_file.exists():
        shutil.copyfile(anchor_file, str(target) + ".anchor.json")
    _out({"restored": str(target), "integrity_check": ok})
    return 0 if ok == "ok" else 1


def cmd_verify_audit(args) -> int:
    path = _db_path(args)
    key, _ = audit_key_from_env()
    anchor = None
    af = Path(args.anchor) if args.anchor else Path(str(path) + ".anchor.json")
    if af.exists():
        anchor = json.loads(af.read_text(encoding="utf-8"))
    elif args.anchor:
        print(f"anchor file {af} not found", file=sys.stderr)
        return 1
    elif not args.allow_no_anchor:
        print("no anchor: deleting the newest events cannot be detected without one. Pass --anchor with an anchor kept off this host "
              "(e.g. from the last backup), or --allow-no-anchor to check the chain's internal consistency only", file=sys.stderr)
        return 1
    with sqlite3.connect(path) as c:
        c.row_factory = sqlite3.Row
        res = auditlog.verify(c, key, anchor=anchor)
    _out({**res, "anchor_checked": anchor is not None})
    return 0 if res["valid"] else 1


def cmd_serve(args) -> int:
    import uvicorn

    from . import api, policy as policymod
    d = _open(_db_path(args))
    if d.schema_version() != len(d.migration_files()):
        print("database schema is not current; run `init` first", file=sys.stderr)
        return 1
    cap, refill = (float(x) for x in args.rate_limit.split(","))
    app = api.create_app(d, policymod.load(args.policy), rate_limit=(int(cap), refill))
    uvicorn.run(app, host=args.host, port=args.port, log_level="info", proxy_headers=args.behind_proxy, forwarded_allow_ips=args.trusted_proxy)
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="sentinelloop-admin", description="SentinelLoop platform administration")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def with_db(p):
        p.add_argument("--db", help="database path (default: $SENTINELLOOP_DB)")
        return p
    with_db(sub.add_parser("init")).set_defaults(func=cmd_init)
    p = with_db(sub.add_parser("create-admin"))
    p.add_argument("--user", required=True)
    p.add_argument("--name", required=True)
    p.set_defaults(func=cmd_create_admin)
    p = with_db(sub.add_parser("backup"))
    p.add_argument("--to", required=True)
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_backup)
    p = with_db(sub.add_parser("restore"))
    p.add_argument("--from", dest="from_", required=True)
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_restore)
    p = with_db(sub.add_parser("verify-audit"))
    p.add_argument("--anchor", help="anchor JSON kept off the host (e.g. <backup>.anchor.json from an earlier backup)")
    p.add_argument("--allow-no-anchor", action="store_true", help="check internal consistency only (cannot detect truncation)")
    p.set_defaults(func=cmd_verify_audit)
    p = with_db(sub.add_parser("serve"))
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8080)
    p.add_argument("--policy", default="configs/platform.yaml")
    p.add_argument("--behind-proxy", action="store_true", help="trust X-Forwarded-For from --trusted-proxy (for rate limiting by client address)")
    p.add_argument("--trusted-proxy", default="127.0.0.1")
    p.add_argument("--rate-limit", default="120,2.0", help="token bucket per user or client: CAPACITY,REFILL_PER_SECOND")
    p.set_defaults(func=cmd_serve)
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except ConfigError as e:
        print(f"configuration error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
