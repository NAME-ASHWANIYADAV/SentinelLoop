"""Model registry: candidate -> approved -> retired, with explicit human decisions and rollback.

Registration records the bundle's checksum; scoring loads only approved models and verifies that checksum, so the
registry (not the bundle directory) is the trust anchor. Approving a model retires any other approved model with the
same asset type and scope key. Only reliability engineers and admins may approve, reject or roll back.
"""
from __future__ import annotations

import json

from . import auditlog
from .errors import PermissionDenied
from .modelpack import read_manifest
from .timeutil import now_iso

DECIDERS = {"reliability_engineer", "admin"}


class ModelRegistryError(ValueError):
    pass


class ModelRolePermissionError(ModelRegistryError, PermissionDenied):
    pass


def _audit(db, c, actor, action, model_id, payload):
    auditlog.append(c, actor=actor, action=action, entity="model", entity_id=model_id, payload=payload, key=db.audit_key, key_id=db.audit_key_id)


def register(db, bundle_dir, actor: str) -> str:
    import hashlib
    from pathlib import Path
    m = read_manifest(bundle_dir)
    blob = Path(bundle_dir, "bundle.pkl")
    if not blob.exists() or hashlib.sha256(blob.read_bytes()).hexdigest() != m.get("artifact_sha256"):
        raise ModelRegistryError("the model artefact does not match the checksum in its manifest; refusing to register it")
    with db.tx() as c:
        if c.execute("SELECT 1 FROM asset_types WHERE asset_type_id = ?", (m["asset_type_id"],)).fetchone() is None:
            raise ModelRegistryError(f"asset type {m['asset_type_id']} is not registered")
        if c.execute("SELECT 1 FROM models WHERE model_id = ?", (m["model_id"],)).fetchone() is not None:
            raise ModelRegistryError(f"model {m['model_id']} is already registered")
        c.execute("INSERT INTO models (model_id, family, asset_type_id, scope_key, version, artifact_path, artifact_sha256, manifest_json, status, "
                  "registered_by, registered_at) VALUES (?,?,?,?,?,?,?,?,'candidate',?,?)",
                  (m["model_id"], m["family"], m["asset_type_id"], m["scope_key"], m["version"], str(bundle_dir), m["artifact_sha256"],
                   json.dumps(m), actor, now_iso()))
        _audit(db, c, actor, "model.registered", m["model_id"], {"artifact_sha256": m["artifact_sha256"], "scope_key": m["scope_key"],
                                                               "evaluation": m.get("evaluation"), "trained_on": m.get("trained_on")})
    return m["model_id"]


def _row(r) -> dict:
    d = dict(r)
    d["manifest"] = json.loads(d.pop("manifest_json"))
    return d


def get(db, model_id: str) -> dict | None:
    with db.connect() as c:
        r = c.execute("SELECT * FROM models WHERE model_id = ?", (model_id,)).fetchone()
    return _row(r) if r else None


def list_models(db, asset_type_id: str | None = None, status: str | None = None) -> list[dict]:
    q, a = "SELECT * FROM models WHERE 1=1", []
    if asset_type_id:
        q, a = q + " AND asset_type_id = ?", a + [asset_type_id]
    if status:
        q, a = q + " AND status = ?", a + [status]
    with db.connect() as c:
        return [_row(r) for r in c.execute(q + " ORDER BY registered_at DESC, model_id", a)]


def approved_models(db, asset_type_id: str) -> list[dict]:
    with db.connect() as c:
        rows = c.execute("SELECT * FROM models WHERE asset_type_id = ? AND status = 'approved' ORDER BY decided_at DESC", (asset_type_id,)).fetchall()
    return [_row(r) for r in rows]


def _check(role: str, reason: str):
    if role not in DECIDERS:
        raise ModelRolePermissionError(f"role {role!r} may not approve, reject or roll back models")
    if not reason or not reason.strip():
        raise ModelRegistryError("a written reason is required")


def decide(db, model_id: str, decision: str, actor: str, role: str, reason: str) -> dict:
    _check(role, reason)
    if decision not in ("approved", "rejected"):
        raise ModelRegistryError("decision must be 'approved' or 'rejected'")
    ts = now_iso()
    with db.tx() as c:
        m = c.execute("SELECT * FROM models WHERE model_id = ?", (model_id,)).fetchone()
        if m is None:
            raise ModelRegistryError(f"unknown model {model_id}")
        if m["status"] != "candidate":
            raise ModelRegistryError(f"model {model_id} is {m['status']}; only candidates can be decided")
        retired = []
        if decision == "approved":
            retired = [r["model_id"] for r in c.execute("SELECT model_id FROM models WHERE asset_type_id = ? AND scope_key = ? AND status = 'approved'",
                                                         (m["asset_type_id"], m["scope_key"]))]
            c.execute("UPDATE models SET status = 'retired' WHERE asset_type_id = ? AND scope_key = ? AND status = 'approved'",
                      (m["asset_type_id"], m["scope_key"]))
        c.execute("UPDATE models SET status = ?, decided_by = ?, decided_at = ?, decision_reason = ? WHERE model_id = ?", (decision, actor, ts, reason, model_id))
        _audit(db, c, actor, f"model.{decision}", model_id, {"reason": reason, "role": role, "retired": retired})
    return get(db, model_id)


def rollback(db, asset_type_id: str, to_model_id: str, actor: str, role: str, reason: str) -> dict:
    _check(role, reason)
    ts = now_iso()
    with db.tx() as c:
        target = c.execute("SELECT * FROM models WHERE model_id = ? AND asset_type_id = ?", (to_model_id, asset_type_id)).fetchone()
        if target is None or target["status"] != "retired":
            raise ModelRegistryError("rollback target must be a previously approved (now retired) model of this asset type")
        current = [r["model_id"] for r in c.execute("SELECT model_id FROM models WHERE asset_type_id = ? AND scope_key = ? AND status = 'approved'",
                                                    (asset_type_id, target["scope_key"]))]
        c.execute("UPDATE models SET status = 'retired' WHERE asset_type_id = ? AND scope_key = ? AND status = 'approved'", (asset_type_id, target["scope_key"]))
        c.execute("UPDATE models SET status = 'approved', decided_by = ?, decided_at = ?, decision_reason = ? WHERE model_id = ?",
                  (actor, ts, f"rollback: {reason}", to_model_id))
        _audit(db, c, actor, "model.rollback", to_model_id, {"reason": reason, "role": role, "replaced": current})
    return get(db, to_model_id)
