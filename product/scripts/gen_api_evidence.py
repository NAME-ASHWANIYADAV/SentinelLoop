"""Regenerate product/evidence/api/openapi.json and routes.md from the current application (no server started).

Usage (repository root): ./.venv/Scripts/python.exe product/scripts/gen_api_evidence.py
The app is built with sentinelloop.app.api.create_app on a fresh, migrated database in a temporary directory; the audit
key comes from SENTINELLOOP_AUDIT_KEY (a random 32-byte key is generated for this run if none is set).
"""
import inspect
import json
import os
import secrets
import sys
import tempfile
from pathlib import Path

root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / "src"))
os.environ.setdefault("SENTINELLOOP_AUDIT_KEY", secrets.token_hex(32))

from fastapi.routing import APIRoute  # noqa: E402

from sentinelloop.app import admin, api, db as dbmod, policy as policymod  # noqa: E402


def permission(dependant) -> str | None:
    """The permission named by the route's `need(...)` dependency, 'any authenticated user' for `current_user` alone."""
    found = None
    for d in dependant.dependencies:
        call = d.call
        fv = inspect.getclosurevars(call).nonlocals if inspect.isfunction(call) else {}
        if "permission" in fv:
            return fv["permission"]
        if getattr(call, "__name__", "") == "current_user":
            found = "any authenticated user"
        inner = permission(d)
        if inner and inner != "any authenticated user":
            return inner
        found = found or inner
    return found


with tempfile.TemporaryDirectory() as tmp:
    key, kid = admin.audit_key_from_env()
    d = dbmod.Database(Path(tmp) / "openapi.db", audit_key=key, audit_key_id=kid)
    d.migrate()
    app = api.create_app(d, policymod.load(root / "configs" / "platform.yaml"))
    spec = app.openapi()
    rows = []
    for r in app.routes:
        if not isinstance(r, APIRoute) or not r.path.startswith("/api/v1"):
            continue
        perm = permission(r.dependant) or "public"
        for m in sorted(r.methods - {"HEAD", "OPTIONS"}):
            rows.append(f"| {m} | `{r.path}` | {perm} |")

out = root / "product" / "evidence" / "api"
(out / "openapi.json").write_bytes((json.dumps(spec, indent=1, sort_keys=True) + "\n").encode("utf-8"))
(out / "routes.md").write_bytes(("| method | path | permission |\n|---|---|---|\n" + "\n".join(rows) + "\n").encode("utf-8"))
print(f"{len(spec['paths'])} paths, {len(rows)} routes")
