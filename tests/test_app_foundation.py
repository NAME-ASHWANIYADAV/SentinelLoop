"""Platform foundation: migrations, keyed audit chain, asset registry (tests written before the code)."""
import sqlite3

import pytest

from sentinelloop.app import auditlog, db as dbmod, registry
from sentinelloop.app.models import AssetSpec, AssetTypeSpec, ConsequenceSpec, JobSpec, SignalSpec, WindowSpec

KEY = b"test-audit-key-0123456789abcdef-0123456789"


@pytest.fixture
def database(tmp_path):
    d = dbmod.Database(tmp_path / "plant.db", audit_key=KEY, audit_key_id="test")
    d.migrate()
    return d


def pump_type(**kw):
    base = dict(asset_type_id="centrifugal_pump", name="Centrifugal pump", description="test type", time_basis="timestamp",
                signals=[SignalSpec(name="bearing_temp", unit="degC", min=-20, max=150),
                         SignalSpec(name="vibration_rms", unit="mm/s", min=0, max=50),
                         SignalSpec(name="flow", unit="m3/h", min=0, max=500, required=False)],
                jobs={"inspect": JobSpec(duration_h=1.0, skill="mechanical"), "repair": JobSpec(duration_h=6.0, skill="mechanical", parts={"bearing_kit": 1}),
                      "replace": JobSpec(duration_h=12.0, skill="mechanical", parts={"pump_unit": 1})})
    base.update(kw)
    return AssetTypeSpec(**base)


def pump(asset_id="P-101", **kw):
    base = dict(asset_id=asset_id, tag=asset_id, name=f"Pump {asset_id}", asset_type_id="centrifugal_pump", site_id="site1", location="Line 1",
                criticality="A", consequence=ConsequenceSpec(downtime_hours=8, cost_per_failure=50000, safety_impact=False, environmental_impact=False),
                maintenance_windows=[WindowSpec(start="2026-10-20T06:00:00Z", end="2026-10-20T14:00:00Z")])
    base.update(kw)
    return AssetSpec(**base)


def test_migrations_apply_once_and_record_checksums(tmp_path):
    d = dbmod.Database(tmp_path / "a.db", audit_key=KEY, audit_key_id="test")
    applied = d.migrate()
    assert applied and applied[0].startswith("0001")
    assert d.migrate() == []                       # idempotent
    assert d.schema_version() == len(applied)
    with d.connect() as c:
        tables = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"assets", "asset_types", "sites", "readings", "ingestion_batches", "audit_events", "schema_migrations"} <= tables


def test_edited_migration_is_refused(tmp_path, monkeypatch):
    d = dbmod.Database(tmp_path / "a.db", audit_key=KEY, audit_key_id="test")
    d.migrate()
    with d.connect() as c:
        c.execute("UPDATE schema_migrations SET checksum='tampered' WHERE version=1")
        c.commit()
    with pytest.raises(dbmod.MigrationError):
        d.migrate()


def test_foreign_keys_are_enforced(database):
    with pytest.raises(sqlite3.IntegrityError):
        with database.tx() as c:
            c.execute("INSERT INTO assets (asset_id, tag, name, asset_type_id, site_id, criticality, failure_consequence_json, created_at, updated_at) "
                      "VALUES ('x','x','x','no_such_type','no_such_site','A','{}','t','t')")


def test_audit_chain_detects_edits_reordering_and_wrong_key(database):
    with database.tx() as c:
        for i in range(5):
            auditlog.append(c, actor="alice", action="test.event", entity="thing", entity_id=str(i), payload={"i": i}, key=KEY, key_id="test")
    with database.connect() as c:
        assert auditlog.verify(c, KEY)["valid"] is True
        assert auditlog.verify(c, b"another-key-xxxxxxxxxxxxxxxxxxx")["valid"] is False
        c.execute("UPDATE audit_events SET payload_json='{\"i\": 99}' WHERE seq=3")
        c.commit()
        rep = auditlog.verify(c, KEY)
    assert rep["valid"] is False and rep["first_bad_seq"] == 3


def test_audit_anchor_detects_truncation(database):
    with database.tx() as c:
        for i in range(4):
            auditlog.append(c, actor="a", action="x", entity="e", entity_id=str(i), payload={}, key=KEY, key_id="test")
        anchor = auditlog.anchor(c)
    with database.connect() as c:
        c.execute("DELETE FROM audit_events WHERE seq=4")
        c.commit()
        assert auditlog.verify(c, KEY)["valid"] is True            # a valid prefix on its own ...
        assert auditlog.verify(c, KEY, anchor=anchor)["valid"] is False   # ... but not against the external anchor


def test_registry_creates_and_reads_assets_with_audit(database):
    registry.create_site(database, "site1", "Plant 1", "Asia/Kolkata", actor="admin")
    registry.create_asset_type(database, pump_type(), actor="admin")
    a = registry.create_asset(database, pump(), actor="admin")
    assert a.asset_id == "P-101" and a.criticality == "A" and a.status == "active"
    got = registry.get_asset(database, "P-101")
    assert got.consequence.cost_per_failure == 50000 and got.maintenance_windows[0].start_ms < got.maintenance_windows[0].end_ms
    assert [x.asset_id for x in registry.list_assets(database)] == ["P-101"]
    t = registry.get_asset_type(database, "centrifugal_pump")
    assert {s.name for s in t.signals} == {"bearing_temp", "vibration_rms", "flow"}
    with database.connect() as c:
        actions = [r["action"] for r in c.execute("SELECT action FROM audit_events ORDER BY seq")]
    assert actions == ["site.created", "asset_type.created", "asset.created"]


def test_registry_rejects_unknown_type_duplicate_tag_and_bad_window(database):
    registry.create_site(database, "site1", "Plant 1", "UTC", actor="admin")
    registry.create_asset_type(database, pump_type(), actor="admin")
    with pytest.raises(registry.RegistryError):
        registry.create_asset(database, pump(asset_type_id="unknown"), actor="admin")
    registry.create_asset(database, pump(), actor="admin")
    with pytest.raises(registry.RegistryError):
        registry.create_asset(database, pump(asset_id="P-102", tag="P-101"), actor="admin")
    with pytest.raises(ValueError):
        pump(asset_id="P-103", maintenance_windows=[WindowSpec(start="2026-10-20T14:00:00Z", end="2026-10-20T06:00:00Z")])


def test_registry_update_records_old_and_new_values(database):
    registry.create_site(database, "site1", "Plant 1", "UTC", actor="admin")
    registry.create_asset_type(database, pump_type(), actor="admin")
    registry.create_asset(database, pump(), actor="admin")
    a = registry.update_asset(database, "P-101", {"criticality": "B", "status": "out_of_service"}, actor="planner", reason="spare pump installed")
    assert a.criticality == "B" and a.status == "out_of_service"
    with database.connect() as c:
        row = c.execute("SELECT payload_json FROM audit_events WHERE action='asset.updated'").fetchone()
    assert '"old"' in row[0] and '"spare pump installed"' in row[0]
    with pytest.raises(registry.RegistryError):
        registry.update_asset(database, "P-101", {"asset_type_id": "other"}, actor="planner", reason="not allowed")


def test_naive_timestamps_are_refused_in_specs():
    with pytest.raises(ValueError):
        WindowSpec(start="2026-10-20T06:00:00", end="2026-10-20T08:00:00Z")


def test_database_refuses_to_run_without_a_real_audit_key(tmp_path):
    with pytest.raises(ValueError):
        dbmod.Database(tmp_path / "a.db")                                  # no key and no explicit dev opt-in
    with pytest.raises(ValueError):
        dbmod.Database(tmp_path / "a.db", audit_key=b"short")             # too short to be a secret
    d = dbmod.Database(tmp_path / "a.db", allow_dev_key=True)
    assert d.audit_key_id == "dev-insecure" and d.insecure_dev_key
    d.migrate()
    with d.tx() as c:
        auditlog.append(c, actor="a", action="x", entity="e", entity_id="1", payload={}, key=d.audit_key, key_id=d.audit_key_id)
    with d.connect() as c:
        assert auditlog.verify(c, d.audit_key)["events_signed_with_dev_key"] == 1


def test_asset_ids_and_tags_share_one_namespace(database):
    registry.create_site(database, "site1", "Plant 1", "UTC", actor="admin")
    registry.create_asset_type(database, pump_type(), actor="admin")
    registry.create_asset(database, pump("P-101", tag="TAG-A"), actor="admin")
    with pytest.raises(registry.RegistryError):
        registry.create_asset(database, pump("P-102", tag="P-101"), actor="admin")      # tag equal to another asset's id
    with pytest.raises(registry.RegistryError):
        registry.create_asset(database, pump("TAG-A", tag="TAG-B"), actor="admin")      # id equal to another asset's tag
    assert registry.get_asset(database, "TAG-A").asset_id == "P-101"
