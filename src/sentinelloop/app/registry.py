"""Asset registry: sites, asset types (with their data contracts and job definitions) and assets.

Every change is written together with an audit event in one transaction. An asset's identity, type and
site cannot be changed in place; retire it and register a new one, so history stays attributable.
"""
from __future__ import annotations

import json
import sqlite3

from . import auditlog
from .models import Asset, AssetSpec, AssetTypeSpec, ConsequenceSpec, WindowSpec
from .timeutil import now_iso

UPDATABLE = {"name", "location", "criticality", "status", "consequence", "config", "operating_context", "maintenance_windows", "last_maintenance_at"}


class RegistryError(ValueError):
    pass


def _audit(db, c, actor, action, entity, entity_id, payload):
    auditlog.append(c, actor=actor, action=action, entity=entity, entity_id=entity_id, payload=payload, key=db.audit_key, key_id=db.audit_key_id)


def create_site(db, site_id: str, name: str, timezone: str, actor: str) -> dict:
    from zoneinfo import ZoneInfo
    ZoneInfo(timezone)                                    # raises for an unknown zone
    row = {"site_id": site_id, "name": name, "timezone": timezone, "created_at": now_iso()}
    try:
        with db.tx() as c:
            c.execute("INSERT INTO sites (site_id, name, timezone, created_at) VALUES (:site_id, :name, :timezone, :created_at)", row)
            _audit(db, c, actor, "site.created", "site", site_id, row)
    except sqlite3.IntegrityError as e:
        raise RegistryError(f"site {site_id} already exists") from e
    return row


def get_site(db, site_id: str) -> dict | None:
    with db.connect() as c:
        r = c.execute("SELECT * FROM sites WHERE site_id = ?", (site_id,)).fetchone()
    return dict(r) if r else None


def list_sites(db) -> list[dict]:
    with db.connect() as c:
        return [dict(r) for r in c.execute("SELECT site_id, name, timezone, created_at FROM sites ORDER BY site_id")]


def create_asset_type(db, spec: AssetTypeSpec, actor: str) -> AssetTypeSpec:
    try:
        with db.tx() as c:
            c.execute("INSERT INTO asset_types (asset_type_id, name, description, time_basis, usage_hours_per_cycle, signals_json, jobs_json, created_at) "
                      "VALUES (?,?,?,?,?,?,?,?)",
                      (spec.asset_type_id, spec.name, spec.description, spec.time_basis, spec.usage_hours_per_cycle,
                       json.dumps([s.model_dump() for s in spec.signals]), json.dumps({k: v.model_dump() for k, v in spec.jobs.items()}), now_iso()))
            _audit(db, c, actor, "asset_type.created", "asset_type", spec.asset_type_id, spec.model_dump())
    except sqlite3.IntegrityError as e:
        raise RegistryError(f"asset type {spec.asset_type_id} already exists") from e
    return spec


def _type_from_row(r) -> AssetTypeSpec:
    return AssetTypeSpec(asset_type_id=r["asset_type_id"], name=r["name"], description=r["description"], time_basis=r["time_basis"],
                         usage_hours_per_cycle=r["usage_hours_per_cycle"], signals=json.loads(r["signals_json"]), jobs=json.loads(r["jobs_json"]))


def get_asset_type(db, asset_type_id: str) -> AssetTypeSpec | None:
    with db.connect() as c:
        r = c.execute("SELECT * FROM asset_types WHERE asset_type_id = ?", (asset_type_id,)).fetchone()
    return _type_from_row(r) if r else None


def list_asset_types(db) -> list[AssetTypeSpec]:
    with db.connect() as c:
        return [_type_from_row(r) for r in c.execute("SELECT * FROM asset_types ORDER BY asset_type_id")]


def create_asset(db, spec: AssetSpec, actor: str) -> Asset:
    ts = now_iso()
    with db.tx() as c:
        if c.execute("SELECT 1 FROM asset_types WHERE asset_type_id = ?", (spec.asset_type_id,)).fetchone() is None:
            raise RegistryError(f"unknown asset type {spec.asset_type_id}")
        if c.execute("SELECT 1 FROM sites WHERE site_id = ?", (spec.site_id,)).fetchone() is None:
            raise RegistryError(f"unknown site {spec.site_id}")
        # ids and tags form ONE namespace: neither may equal any existing id or tag, so a lookup key is never ambiguous
        if c.execute("SELECT 1 FROM assets WHERE asset_id IN (?, ?) OR tag IN (?, ?)",
                     (spec.asset_id, spec.tag, spec.asset_id, spec.tag)).fetchone() is not None:
            raise RegistryError(f"asset id {spec.asset_id} or tag {spec.tag} collides with an existing asset id or tag")
        c.execute("INSERT INTO assets (asset_id, tag, name, asset_type_id, site_id, location, criticality, failure_consequence_json, config_json, "
                  "operating_context_json, maintenance_windows_json, status, installed_at, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,'active',?,?,?)",
                  (spec.asset_id, spec.tag, spec.name, spec.asset_type_id, spec.site_id, spec.location, spec.criticality,
                   spec.consequence.model_dump_json(), json.dumps(spec.config), json.dumps(spec.operating_context),
                   json.dumps([w.model_dump() for w in spec.maintenance_windows]), spec.installed_at, ts, ts))
        _audit(db, c, actor, "asset.created", "asset", spec.asset_id, spec.model_dump())
    return get_asset_by_id(db, spec.asset_id)


def _asset_from_row(r) -> Asset:
    return Asset(asset_id=r["asset_id"], tag=r["tag"], name=r["name"], asset_type_id=r["asset_type_id"], site_id=r["site_id"], location=r["location"],
                 criticality=r["criticality"], consequence=ConsequenceSpec(**json.loads(r["failure_consequence_json"])), config=json.loads(r["config_json"]),
                 operating_context=json.loads(r["operating_context_json"]), maintenance_windows=[WindowSpec(**w) for w in json.loads(r["maintenance_windows_json"])],
                 installed_at=r["installed_at"], status=r["status"], last_maintenance_at=r["last_maintenance_at"], created_at=r["created_at"], updated_at=r["updated_at"])


def get_asset(db, asset_id_or_tag: str) -> Asset | None:
    """Exact id first, then tag (ids and tags share one namespace, enforced at creation)."""
    with db.connect() as c:
        r = c.execute("SELECT * FROM assets WHERE asset_id = ?", (asset_id_or_tag,)).fetchone()
        if r is None:
            r = c.execute("SELECT * FROM assets WHERE tag = ?", (asset_id_or_tag,)).fetchone()
    return _asset_from_row(r) if r else None


def get_asset_by_id(db, asset_id: str) -> Asset | None:
    with db.connect() as c:
        r = c.execute("SELECT * FROM assets WHERE asset_id = ?", (asset_id,)).fetchone()
    return _asset_from_row(r) if r else None


def list_assets(db, site_id: str | None = None, status: str | None = None, asset_type_id: str | None = None) -> list[Asset]:
    q, args = "SELECT * FROM assets WHERE 1=1", []
    for col, val in (("site_id", site_id), ("status", status), ("asset_type_id", asset_type_id)):
        if val is not None:
            q += f" AND {col} = ?"
            args.append(val)
    with db.connect() as c:
        return [_asset_from_row(r) for r in c.execute(q + " ORDER BY asset_id", args)]


def update_asset(db, asset_id: str, changes: dict, actor: str, reason: str) -> Asset:
    bad = set(changes) - UPDATABLE
    if bad:
        raise RegistryError(f"fields {sorted(bad)} cannot be changed in place (retire the asset and register a new one)")
    if not reason or not reason.strip():
        raise RegistryError("a reason is required for every asset change")
    old = get_asset_by_id(db, asset_id)
    if old is None:
        raise RegistryError(f"unknown asset id {asset_id}")
    merged = old.model_dump()
    merged.update(changes)
    new = Asset(**merged)                                  # validates criticality, windows, consequence
    cols = {"name": new.name, "location": new.location, "criticality": new.criticality, "status": new.status,
            "failure_consequence_json": new.consequence.model_dump_json(), "config_json": json.dumps(new.config),
            "operating_context_json": json.dumps(new.operating_context),
            "maintenance_windows_json": json.dumps([w.model_dump() for w in new.maintenance_windows]),
            "last_maintenance_at": new.last_maintenance_at, "updated_at": now_iso()}
    with db.tx() as c:
        c.execute("UPDATE assets SET " + ", ".join(f"{k} = :{k}" for k in cols) + " WHERE asset_id = :asset_id", {**cols, "asset_id": old.asset_id})
        _audit(db, c, actor, "asset.updated", "asset", old.asset_id,
               {"reason": reason, "old": {k: old.model_dump()[k] for k in changes}, "new": {k: new.model_dump()[k] for k in changes}})
    return get_asset_by_id(db, old.asset_id)
