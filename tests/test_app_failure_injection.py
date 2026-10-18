"""Failure injection: the platform's behaviour when its own parts fail (tests first; SYNTHETIC wind data).

Covered elsewhere and not repeated here: missing, stale, stuck and conflicting signals, unfamiliar operating
conditions, too little history, tampered model artefacts, latching rules, rollback (test_app_health.py,
test_app_states.py, test_app_wind.py). This module adds: a model that crashes while scoring, a model file that
disappears after approval, a latched urgent state surviving a model outage, concurrent writers, a restart, and an
unexpected server error.
"""
import shutil
import threading

import pytest
from fastapi.testclient import TestClient

from sentinelloop.app import api, db as dbmod, health, ingest, modelreg, nbm, policy as policymod, security, states, synthetic_wind as sw
from sentinelloop.app.adapters import wind
from sentinelloop.app.timeutil import DAY_MS, HOUR_MS
from conftest import ROOT
from test_app_foundation import KEY

POL = policymod.load(ROOT / "configs" / "platform.yaml")
FAULT = sw.Fault("WT02", "hss_bearing", start_day=10.0, fail_day=16.0, peak_heat_c=25.0)


@pytest.fixture(scope="module")
def fleet():
    return sw.generate(sw.FleetSpec(n_turbines=2, days=16, seed=31, faults=(FAULT,)))


@pytest.fixture(scope="module")
def bundle_src(tmp_path_factory):
    train = sw.generate(sw.FleetSpec(n_turbines=3, days=20, seed=4)).scada
    return nbm.package_wind_nbm(train, tmp_path_factory.mktemp("m"), scope_key="wind:synthetic", data_class="SYNTHETIC", source="test")


def _ingest(d, fleet, turbine, t0, t1):
    s = fleet.scada[(fleet.scada.turbine == turbine) & (fleet.scada.ts_ms > t0) & (fleet.scada.ts_ms <= t1)]
    return ingest.ingest_records(d, wind.records(s), source="t", actor="svc", now_ms=t1 + 60_000)


@pytest.fixture
def plant(tmp_path, bundle_src, fleet):
    bdir = tmp_path / "bundle"
    shutil.copytree(bundle_src, bdir)                    # each test may break its own copy
    d = dbmod.Database(tmp_path / "p.db", audit_key=KEY, audit_key_id="test")
    d.migrate()
    wind.ensure_site_and_type(d, actor="admin")
    st = fleet.meta["start_ms"]
    for t in ("WT01", "WT02"):
        wind.create_turbine(d, t, criticality="A", actor="admin")
        _ingest(d, fleet, t, st, st + int(9 * DAY_MS))
    mid = modelreg.register(d, bdir, actor="rea")
    modelreg.decide(d, mid, "approved", actor="rea", role="reliability_engineer", reason="test")
    for t in ("WT01", "WT02"):
        nbm.commission(d, t, mid, st, st + int(9 * DAY_MS), actor="rea", role="reliability_engineer", reason="days 0-9 healthy (synthetic)")
    health._BUNDLE_CACHE.clear()
    return {"db": d, "bundle_dir": bdir, "model_id": mid, "start": st}


def test_a_model_that_crashes_while_scoring_gives_model_unavailable_and_no_numbers(plant, fleet, monkeypatch):
    d, st = plant["db"], plant["start"]
    t = st + int(10.0 * DAY_MS)
    _ingest(d, fleet, "WT01", t - 12 * HOUR_MS, t)

    def boom(self, raw, baseline=None):
        raise RuntimeError("simulated scoring crash")
    monkeypatch.setattr(nbm.WindNBMBundle, "score", boom)
    a = health.assess(d, "WT01", POL, as_of_ms=t, actor="svc")
    assert a["health_state"] == "MODEL_UNAVAILABLE"
    assert a["anomaly_score"] is None and a["rul_point"] is None and a["risk"] == {}
    assert any("scoring failed (RuntimeError)" in r for r in a["reasons"])
    assert not any("simulated scoring crash" in r for r in a["reasons"])           # exception text stays in the server log


def test_a_model_file_deleted_after_approval_gives_model_unavailable(plant, fleet):
    d, st = plant["db"], plant["start"]
    t = st + int(10.0 * DAY_MS)
    _ingest(d, fleet, "WT01", t - 12 * HOUR_MS, t)
    (plant["bundle_dir"] / "bundle.pkl").unlink()
    a = health.assess(d, "WT01", POL, as_of_ms=t, actor="svc")
    assert a["health_state"] == "MODEL_UNAVAILABLE" and any("model_unavailable" in r for r in a["reasons"])


def test_a_latched_urgent_state_survives_a_model_outage_and_a_restart(plant, fleet, tmp_path):
    d, st = plant["db"], plant["start"]
    t_bad = st + int(15.5 * DAY_MS)
    _ingest(d, fleet, "WT02", t_bad - 24 * HOUR_MS, t_bad)
    a = health.assess(d, "WT02", POL, as_of_ms=t_bad, actor="svc")
    assert a["health_state"] in ("URGENT_REVIEW", "INSPECTION_RECOMMENDED"), a["reasons"]
    latched = health.asset_state(d, "WT02").effective
    (plant["bundle_dir"] / "bundle.pkl").unlink()                     # the model service then fails
    health._BUNDLE_CACHE.clear()
    t2 = t_bad + 2 * HOUR_MS
    a2 = health.assess(d, "WT02", POL, as_of_ms=t2, actor="svc")
    assert a2["health_state"] == "MODEL_UNAVAILABLE"
    assert health.asset_state(d, "WT02").effective == latched         # the warning does not disappear with the model
    d2 = dbmod.Database(d.path, audit_key=KEY, audit_key_id="test")   # process restart: state is in the database
    assert health.asset_state(d2, "WT02").effective == latched


def test_concurrent_ingestion_loses_nothing_and_double_counts_nothing(tmp_path, fleet):
    d = dbmod.Database(tmp_path / "c.db", audit_key=KEY, audit_key_id="test")
    d.migrate()
    wind.ensure_site_and_type(d, actor="admin")
    wind.create_turbine(d, "WT01", criticality="B", actor="admin")
    st = fleet.meta["start_ms"]
    s = fleet.scada[(fleet.scada.turbine == "WT01") & (fleet.scada.ts_ms <= st + int(1 * DAY_MS))]
    recs = wind.records(s)
    chunks = [recs[i::4] + recs[: len(recs) // 3] for i in range(4)]            # every worker also re-sends an overlapping third
    results, errors = [], []

    def work(chunk, k):
        try:
            results.append(ingest.ingest_records(d, chunk, source=f"w{k}", actor="svc", now_ms=st + int(2 * DAY_MS)))
        except Exception as e:  # pragma: no cover - the assertion below reports it
            errors.append(repr(e))
    th = [threading.Thread(target=work, args=(c, k)) for k, c in enumerate(chunks)]
    [t.start() for t in th]
    [t.join() for t in th]
    assert not errors, errors
    with d.connect() as c:
        stored = c.execute("SELECT COUNT(*) FROM readings WHERE asset_id = 'WT01'").fetchone()[0]
    assert stored == len(recs)
    assert sum(r.rows_accepted for r in results) == len(recs)
    assert all(r.rows_rejected == 0 for r in results)
    with d.connect() as c:
        from sentinelloop.app import auditlog
        assert auditlog.verify(c, KEY)["valid"]


def test_an_unexpected_server_error_is_a_json_500_with_a_request_id_and_no_internals(tmp_path, monkeypatch):
    d = dbmod.Database(tmp_path / "e.db", audit_key=KEY, audit_key_id="test")
    d.migrate()
    security.create_user(d, "vic", "Vic", "viewer", actor="bootstrap")
    key = security.issue_api_key(d, "vic", actor="bootstrap")
    client = TestClient(api.create_app(d, POL), raise_server_exceptions=False)

    def broken(*a, **k):
        raise RuntimeError("secret internal detail")
    monkeypatch.setattr(api.registry, "list_assets", broken)
    r = client.get("/api/v1/assets", headers={"Authorization": f"Bearer {key}", "X-Request-ID": "rid-42"})
    assert r.status_code == 500 and r.json()["request_id"] == "rid-42"
    assert "secret internal detail" not in r.text and "Traceback" not in r.text
