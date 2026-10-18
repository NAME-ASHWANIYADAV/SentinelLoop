"""Platform administration CLI: initialise, bootstrap the first admin, back up, restore, verify (tests first)."""
import json
import sqlite3

import pytest

from sentinelloop.app import admin, auditlog, db as dbmod, security

KEYHEX = "ab" * 32


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("SENTINELLOOP_AUDIT_KEY", KEYHEX)
    monkeypatch.setenv("SENTINELLOOP_AUDIT_KEY_ID", "k1")
    return tmp_path


def test_init_refuses_without_an_audit_key(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("SENTINELLOOP_AUDIT_KEY", raising=False)
    assert admin.main(["init", "--db", str(tmp_path / "p.db")]) == 2
    assert "SENTINELLOOP_AUDIT_KEY" in capsys.readouterr().err


def test_init_migrates_and_bootstrap_admin_prints_a_key_once(env, capsys):
    db = str(env / "p.db")
    assert admin.main(["init", "--db", db]) == 0
    assert admin.main(["create-admin", "--db", db, "--user", "root", "--name", "Root"]) == 0
    out = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert out["api_key"].startswith("slk_")
    d = dbmod.Database(db, audit_key=bytes.fromhex(KEYHEX), audit_key_id="k1")
    assert security.authenticate_key(d, out["api_key"])["role"] == "admin"
    assert admin.main(["create-admin", "--db", db, "--user", "root2", "--name", "Second"]) == 1      # only when no admin exists


def test_backup_restore_round_trip_and_audit_verification(env, capsys):
    db = str(env / "p.db")
    admin.main(["init", "--db", db])
    admin.main(["create-admin", "--db", db, "--user", "root", "--name", "Root"])
    bk = str(env / "backup.db")
    assert admin.main(["backup", "--db", db, "--to", bk]) == 0
    assert admin.main(["verify-audit", "--db", bk]) == 0
    target = str(env / "restored.db")
    assert admin.main(["restore", "--from", bk, "--db", target]) == 0
    assert admin.main(["restore", "--from", bk, "--db", target]) == 1          # never overwrites without --force
    assert admin.main(["verify-audit", "--db", target]) == 0
    with sqlite3.connect(target) as c:                                            # tamper with the restored copy
        c.execute("UPDATE audit_events SET payload_json = '{}' WHERE seq = (SELECT MIN(seq) FROM audit_events)")
    assert admin.main(["verify-audit", "--db", target]) == 1


def test_wrong_key_fails_audit_verification(env, monkeypatch):
    db = str(env / "p.db")
    admin.main(["init", "--db", db])
    admin.main(["create-admin", "--db", db, "--user", "root", "--name", "Root"])
    monkeypatch.setenv("SENTINELLOOP_AUDIT_KEY", "cd" * 32)
    assert admin.main(["verify-audit", "--db", db, "--allow-no-anchor"]) == 1          # fails on the key, not on the missing anchor
