"""Regression tests for the security findings confirmed by the Phase 9 adversarial review (written before the fixes)."""
import json
import tomllib

import httpx
import pytest
from fastapi.testclient import TestClient

from sentinelloop.app import admin, api, db as dbmod, integration, modelreg, nbm, policy as policymod, registry, security, synthetic_wind as sw, workorders
from sentinelloop.app.adapters import wind
from sentinelloop.app.timeutil import parse_ts
from conftest import ROOT
from test_app_foundation import KEY, pump, pump_type
from test_app_integration import API_KEY, FakeOdoo, _approved_order

POL = policymod.load(ROOT / "configs" / "platform.yaml")
NOW = parse_ts("2026-10-18T00:00:00Z")


# -- security-3: the console must not listen on every interface -----------------------------------------------------
def test_the_console_binds_to_localhost_by_configuration():
    cfg = tomllib.loads((ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8"))
    assert cfg["server"]["address"] == "127.0.0.1" and cfg["server"]["headless"] is True


# -- security-4: audit verification must not pass silently without an anchor --------------------------------------
def test_verify_audit_requires_an_anchor_unless_explicitly_waived(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("SENTINELLOOP_AUDIT_KEY", "ab" * 32)
    db = str(tmp_path / "p.db")
    admin.main(["init", "--db", db])
    admin.main(["create-admin", "--db", db, "--user", "root", "--name", "Root"])
    assert admin.main(["verify-audit", "--db", db]) == 1
    assert "anchor" in capsys.readouterr().err
    assert admin.main(["verify-audit", "--db", db, "--allow-no-anchor"]) == 0
    admin.main(["backup", "--db", db, "--to", str(tmp_path / "b.db")])
    assert admin.main(["verify-audit", "--db", db, "--anchor", str(tmp_path / "b.db.anchor.json")]) == 0


# -- integration fixtures ------------------------------------------------------------------------------------------
@pytest.fixture
def ictx(tmp_path, monkeypatch):
    monkeypatch.setenv("SENTINELLOOP_INTEGRATION_HOSTS", "localhost")
    monkeypatch.setenv("SENTINELLOOP_CRED_ODOO_TEST", API_KEY)
    d = dbmod.Database(tmp_path / "i.db", audit_key=KEY, audit_key_id="test")
    d.migrate()
    registry.create_site(d, "site1", "Plant 1", "UTC", actor="admin")
    registry.create_asset_type(d, pump_type(), actor="admin")
    registry.create_asset(d, pump("P-101"), actor="admin")
    fake = FakeOdoo()
    integration.register_target(d, "odoo", "odoo_json2", "http://localhost:8069", {"database": "x", "api_key_env": "SENTINELLOOP_CRED_ODOO_TEST"},
                                actor="ada", role="admin", mode="draft_requests", reason="test")
    return {"db": d, "fake": fake, "transport": httpx.MockTransport(fake)}


# -- safety-4 / security-6: withdrawn work must be withdrawn in the CMMS too -------------------------------------------
@pytest.mark.parametrize("action,kw,marker", [("cancel", {"reason": "false alarm: sensor fault"}, "WITHDRAWN"),
                                              ("defer", {"reason": "crane booked", "data": {"until": "2026-11-01T06:00:00Z"}}, "DEFERRED")])
def test_cancelled_or_deferred_orders_are_marked_in_the_cmms(ictx, action, kw, marker):
    d, f, tr = ictx["db"], ictx["fake"], ictx["transport"]
    w = _approved_order(d)
    integration.dispatch(d, "odoo", now_ms=NOW, transport=tr)
    ext = int(integration.items(d, "odoo")[0]["external_id"])
    workorders.transition(d, w["wo_id"], action, actor="pat", role="planner", **kw)
    integration.dispatch(d, "odoo", now_ms=NOW + 60_000, transport=tr)
    rec = f.requests[ext]
    assert rec["name"].startswith(f"[SentinelLoop {marker}")
    assert marker.lower() in rec["description"].lower()
    assert len(f.requests) == 1


def test_a_first_send_never_adopts_a_pre_planted_record(ictx):
    d, f, tr = ictx["db"], ictx["fake"], ictx["transport"]
    planted = "WO-000001"
    f.requests[50] = {"id": 50, "name": "[SentinelLoop] planted", "description": f"<p>{integration.marker(planted)}</p>", "priority": "0"}
    w = _approved_order(d)
    assert w["wo_id"] == planted
    integration.dispatch(d, "odoo", now_ms=NOW, transport=tr)
    assert f.requests[50]["name"] == "[SentinelLoop] planted"                    # untouched
    assert integration.items(d, "odoo")[0]["external_id"] != "50"


def test_payload_fields_are_filtered_explicitly_not_by_assert():
    with pytest.raises(integration.IntegrationError):
        integration.filter_fields({"name": "x", "stage_id": 3})


# -- security-7: allowlist at every dispatch; no credentials in URLs or unlisted config keys -----------------------
def test_the_host_allowlist_is_checked_again_at_dispatch(ictx, monkeypatch):
    d, f, tr = ictx["db"], ictx["fake"], ictx["transport"]
    _approved_order(d)
    monkeypatch.setenv("SENTINELLOOP_INTEGRATION_HOSTS", "cmms.example.com")      # localhost removed after registration
    integration.dispatch(d, "odoo", now_ms=NOW, transport=tr)
    assert f.calls == [] and integration.items(d, "odoo")[0]["status"] == "dead"
    assert "not in SENTINELLOOP_INTEGRATION_HOSTS" in integration.items(d, "odoo")[0]["last_error"]


@pytest.mark.parametrize("url", ["https://svc:Secret1@cmms.example.com/hook", "https://cmms.example.com/hook?token=abc",
                                 "https://cmms.example.com/hook#frag"])
def test_urls_with_credentials_queries_or_fragments_are_refused(ictx, monkeypatch, url):
    monkeypatch.setenv("SENTINELLOOP_INTEGRATION_HOSTS", "cmms.example.com")
    with pytest.raises(integration.IntegrationError):
        integration.register_target(ictx["db"], "w2", "webhook", url, {"secret_env": "SENTINELLOOP_CRED_HOOK"}, actor="ada", role="admin")


def test_unknown_config_keys_are_refused(ictx):
    with pytest.raises(integration.IntegrationError):
        integration.register_target(ictx["db"], "o2", "odoo_json2", "http://localhost:8070", {"api_key_env": "SENTINELLOOP_CRED_X", "apiKey": "k"},
                                    actor="ada", role="admin")


def test_integration_config_is_shown_to_admins_only(ictx):
    d = ictx["db"]
    for uid, role in (("ada", "admin"), ("pat", "planner")):
        security.create_user(d, uid, uid, role, actor="b")
    ka, kp = security.issue_api_key(d, "ada", actor="b"), security.issue_api_key(d, "pat", actor="b")
    c = TestClient(api.create_app(d, POL, rate_limit=(1000, 1000.0)))
    assert "config" in c.get("/api/v1/integrations", headers={"Authorization": f"Bearer {ka}"}).json()[0]
    assert "config" not in c.get("/api/v1/integrations", headers={"Authorization": f"Bearer {kp}"}).json()[0]


# -- security-8: CSV parse amplification ---------------------------------------------------------------------------------
def test_csv_uploads_are_capped_by_record_count(tmp_path):
    from sentinelloop.app import ingest
    d = dbmod.Database(tmp_path / "c.db", audit_key=KEY, audit_key_id="test")
    d.migrate()
    header = "asset,timestamp," + ",".join(f"s{i}" for i in range(60))
    rows = "\n".join(f"P-1,2026-10-17T00:{k % 60:02d}:00Z," + ",".join("1" for _ in range(60)) for k in range(4000))
    with pytest.raises(ingest.IngestLimitError):
        ingest.ingest_csv(d, (header + "\n" + rows).encode(), source="x", actor="svc", wide_units={f"s{i}": "u" for i in range(60)})


# -- security-12: API-sourced text is not rendered as markdown --------------------------------------------------------
def test_console_renders_api_text_as_code_spans_with_no_links():
    """Follow-up review: escaping markdown characters is not enough (GFM autolinks); API text goes into code spans."""
    from sentinelloop.console.client import md
    for raw in ("[Approved by R.E.](http://203.0.113.9/login) ![x](http://203.0.113.9/b.png)", "see www.evil.example now", "a `tick` here"):
        s = md(raw)
        assert s.startswith("`") and s.endswith("`") and s.count("`") == 2          # one code span, nothing can break out of it


# -- security-13: registration hashes the artefact itself -------------------------------------------------------------
def test_registration_refuses_an_artefact_that_does_not_match_its_manifest(tmp_path):
    d = dbmod.Database(tmp_path / "m.db", audit_key=KEY, audit_key_id="test")
    d.migrate()
    wind.ensure_site_and_type(d, actor="admin")
    train = sw.generate(sw.FleetSpec(n_turbines=3, days=12, seed=4)).scada
    b = nbm.package_wind_nbm(train, tmp_path / "models", scope_key="wind:synthetic", data_class="SYNTHETIC", source="t")
    blob = (b / "bundle.pkl").read_bytes()
    (b / "bundle.pkl").write_bytes(blob[:-1] + bytes([blob[-1] ^ 1]))
    with pytest.raises(modelreg.ModelRegistryError):
        modelreg.register(d, b, actor="rea")


def test_recovery_needs_evidence_of_an_earlier_real_delivery(ictx):
    """Follow-up review: shadow-mode items never delivered anything, so switching to live must not adopt planted records."""
    d, f, tr = ictx["db"], ictx["fake"], ictx["transport"]
    integration.set_mode(d, "odoo", "shadow", actor="ada", role="admin", reason="back to shadow for the test")
    w = _approved_order(d)
    integration.dispatch(d, "odoo", now_ms=NOW, transport=tr)                       # shadow: a sync item exists, nothing sent
    f.requests[60] = {"id": 60, "name": "[SentinelLoop] planted", "description": f"<p>{integration.marker(w['wo_id'])}</p>"}
    integration.set_mode(d, "odoo", "draft_requests", actor="ada", role="admin", reason="go live")
    integration.dispatch(d, "odoo", now_ms=NOW + 60_000, transport=tr)
    assert f.requests[60]["name"] == "[SentinelLoop] planted" and integration.items(d, "odoo")[0]["external_id"] != "60"
