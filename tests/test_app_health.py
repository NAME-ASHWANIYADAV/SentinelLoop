"""Model packaging and registry, the C-MAPSS adapter, and the assessment service (tests written before the code).

Runs on the real C-MAPSS files with a fast model; module-scoped fixtures keep it to one packaging run."""
import json
import shutil

import numpy as np
import pytest

from sentinelloop import baseline, config, data
from sentinelloop.app import db as dbmod, health, modelpack, modelreg, policy as policymod, registry
from sentinelloop.app.adapters import cmapss
from sentinelloop.app.states import HealthState as H
from conftest import DATA_RAW, ROOT
from test_app_foundation import KEY

pytestmark = pytest.mark.slow
HPC = 3.0          # assumed hours per flight cycle (adapter parameter)


@pytest.fixture(scope="module")
def env(tmp_path_factory):
    if not (DATA_RAW / "train_FD001.txt").exists():
        pytest.skip("real data not present")
    home = tmp_path_factory.mktemp("home")
    d = dbmod.Database(home / "platform.db", audit_key=KEY, audit_key_id="test")
    d.migrate()
    cmapss.ensure_site_and_type(d, actor="admin", hours_per_cycle=HPC, data_dir=DATA_RAW)
    bundle_dir = modelpack.package_cmapss("FD001", home / "models", data_dir=DATA_RAW, config_dir=ROOT / "configs", fast=True)
    model_id = modelreg.register(d, bundle_dir, actor="re1")
    ids = cmapss.load_fleet(d, "FD001", "test", actor="svc", units=[1, 2, 3, 4, 5], hours_per_cycle=HPC, data_dir=DATA_RAW)
    pol = policymod.load(ROOT / "configs" / "platform.yaml")
    return {"db": d, "home": home, "bundle_dir": bundle_dir, "model_id": model_id, "ids": ids, "policy": pol}


def test_registered_model_is_a_candidate_and_needs_approval(env):
    d = env["db"]
    m = modelreg.get(d, env["model_id"])
    assert m["status"] == "candidate" and m["manifest"]["asset_type_id"] == cmapss.ASSET_TYPE_ID
    a = health.assess(d, env["ids"][0], policy=env["policy"], actor="system")
    assert a["health_state"] == H.MODEL_OUT_OF_SCOPE.value and "no_approved_model" in json.dumps(a["reasons"])
    with pytest.raises(modelreg.ModelRegistryError):
        modelreg.decide(d, env["model_id"], "approved", actor="re1", role="technician", reason="ok")     # wrong role
    modelreg.decide(d, env["model_id"], "approved", actor="re1", role="reliability_engineer", reason="FD001 fast model, benchmark only")
    assert modelreg.get(d, env["model_id"])["status"] == "approved"


def test_assessment_reproduces_the_batch_pipeline_bitwise(env):
    d, pol = env["db"], env["policy"]
    cfg = config.load("FD001", ROOT / "configs")
    ds = data.load_subset("FD001", DATA_RAW)
    bundle = modelpack.load_bundle(env["bundle_dir"])
    _, _, test_f, cols = baseline.prepare_frames(ds, cfg)
    last = test_f.sort_values(["unit", "cycle"]).groupby("unit").tail(1).set_index("unit")
    p, lo, hi = bundle.cqr.predict(last.loc[[1, 2, 3, 4, 5], cols])
    for i, asset_id in enumerate(env["ids"]):
        a = health.assess(d, asset_id, policy=pol, actor="system")
        assert a["model_id"] == env["model_id"]
        assert a["health_state"] in {H.NORMAL_MONITORING.value, H.INSPECTION_RECOMMENDED.value, H.URGENT_REVIEW.value}, a["reasons"]
        assert (a["rul_point"], a["rul_lower"], a["rul_upper"]) == (float(p[i]), float(lo[i]), float(hi[i]))
        assert a["rul_point_hours"] == pytest.approx(float(p[i]) * HPC)
        assert a["inputs"]["time_basis"] == "cycle_index" and a["inputs"]["feature_sha256"]


def test_assessment_is_persisted_audited_and_drives_the_asset_state(env):
    d, pol = env["db"], env["policy"]
    a = health.assess(d, env["ids"][1], policy=pol, actor="system")
    with d.connect() as c:
        row = c.execute("SELECT health_state, model_id FROM assessments WHERE assessment_id = ?", (a["assessment_id"],)).fetchone()
        ev = c.execute("SELECT COUNT(*) FROM audit_events WHERE action = 'assessment.created' AND entity_id = ?", (a["assessment_id"],)).fetchone()[0]
    assert row["health_state"] == a["health_state"] and ev == 1
    st = health.asset_state(d, env["ids"][1])
    assert st.effective.value in {x.value for x in H} and st.last_health.value == a["health_state"]


def test_tampered_model_artifact_makes_the_model_unavailable(env, tmp_path):
    d = env["db"]
    copy = tmp_path / "tampered"
    shutil.copytree(env["bundle_dir"], copy)
    with open(copy / "bundle.pkl", "ab") as fh:
        fh.write(b"\x00")
    with pytest.raises(modelpack.ModelIntegrityError):
        modelpack.load_bundle(copy)


def test_an_engine_from_another_operating_envelope_is_out_of_scope(env):
    d, pol = env["db"], env["policy"]
    [other] = cmapss.load_fleet(d, "FD002", "test", actor="svc", units=[1], hours_per_cycle=HPC, data_dir=DATA_RAW, id_prefix="X")
    a = health.assess(d, other, policy=pol, actor="system")
    assert a["health_state"] == H.MODEL_OUT_OF_SCOPE.value
    assert any("operating_envelope" in r or "unknown_operating_regime" in r for r in a["reasons"])
    assert a["rul_point"] is None                      # no prediction is exposed for an out-of-scope asset


def _custom_asset(d, asset_id, unit_df, mutate=None, drop=None):
    registry.create_asset(d, cmapss.asset_spec(asset_id, criticality="B", installed_ms=cmapss.START_MS - int(HPC * 3_600_000)), actor="admin")
    recs = cmapss.unit_records(unit_df, asset_id, cmapss.START_MS - int(HPC * 3_600_000), HPC)
    if drop:
        recs = [r for r in recs if not drop(r)]
    if mutate:
        recs = [mutate(r) for r in recs]
    from sentinelloop.app import ingest
    ingest.ingest_records(d, recs, source="test", actor="svc", now_ms=cmapss.START_MS + 10**12)
    return asset_id


def test_missing_signal_stale_data_and_stuck_sensor_are_data_quality_failures(env):
    d, pol = env["db"], env["policy"]
    model_ds = data.load_subset("FD001", DATA_RAW)
    u = model_ds.test[model_ds.test.unit == 7].sort_values("cycle")
    n = int(u.cycle.max())
    missing = _custom_asset(d, "Q-MISSING", u, drop=lambda r: r["signal"] == "s2" and r["_cycle"] > n - 15)
    stuck = _custom_asset(d, "Q-STUCK", u, mutate=lambda r: {**r, "value": 47.5} if r["signal"] == "s11" and r["_cycle"] > n - 15 else r)
    a = health.assess(d, missing, policy=pol, actor="system")
    assert a["health_state"] == H.DATA_QUALITY_FAILURE.value and any("s2" in r for r in a["reasons"])
    a = health.assess(d, stuck, policy=pol, actor="system")
    assert a["health_state"] == H.DATA_QUALITY_FAILURE.value and any("stuck" in r and "s11" in r for r in a["reasons"])
    late = cmapss.END_MS + int(40 * HPC * 3_600_000)              # 40 cycles after the fleet was last observed
    a = health.assess(d, env["ids"][2], as_of_ms=late, policy=pol, actor="system")
    # every signal stopped together: a late feed (data path), reported as data_delivery_delay rather than per-signal staleness
    assert a["health_state"] == H.DATA_QUALITY_FAILURE.value and any(r.startswith("data_delivery_delay") for r in a["reasons"])


def test_conflicting_redundant_sensors_are_a_data_quality_failure(env):
    d, pol = env["db"], env["policy"]
    bundle = modelpack.load_bundle(env["bundle_dir"])
    assert bundle.consistency, "packaging must learn at least one redundant-sensor relation on FD001"
    a_sig = bundle.consistency[0]["a"]
    ds = data.load_subset("FD001", DATA_RAW)
    u = ds.test[ds.test.unit == 8].sort_values("cycle")
    n = int(u.cycle.max())
    sd = float(ds.train[a_sig].std())
    conflict = _custom_asset(d, "Q-CONFLICT", u, mutate=lambda r: {**r, "value": r["value"] + 8 * sd} if r["signal"] == a_sig and r["_cycle"] > n - 15 else r)
    a = health.assess(d, conflict, policy=pol, actor="system")
    assert a["health_state"] == H.DATA_QUALITY_FAILURE.value and any("conflicting" in r for r in a["reasons"])


def test_too_little_history_is_out_of_scope(env):
    d, pol = env["db"], env["policy"]
    ds = data.load_subset("FD001", DATA_RAW)
    u = ds.test[ds.test.unit == 9].sort_values("cycle").head(4)
    young = _custom_asset(d, "Q-YOUNG", u)
    a = health.assess(d, young, policy=pol, actor="system")
    assert a["health_state"] == H.MODEL_OUT_OF_SCOPE.value and any("insufficient_history" in r for r in a["reasons"])


def test_model_rollback_restores_the_previous_approved_version(env):
    d = env["db"]
    second = modelpack.package_cmapss("FD001", env["home"] / "models", data_dir=DATA_RAW, config_dir=ROOT / "configs", fast=True, seed=7)
    mid2 = modelreg.register(d, second, actor="re1")
    modelreg.decide(d, mid2, "approved", actor="re1", role="reliability_engineer", reason="retrained with seed 7")
    assert modelreg.get(d, env["model_id"])["status"] == "retired" and modelreg.get(d, mid2)["status"] == "approved"
    modelreg.rollback(d, cmapss.ASSET_TYPE_ID, to_model_id=env["model_id"], actor="re1", role="reliability_engineer", reason="seed 7 model under review")
    assert modelreg.get(d, env["model_id"])["status"] == "approved" and modelreg.get(d, mid2)["status"] == "retired"
