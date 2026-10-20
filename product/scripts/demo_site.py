"""Build a local DEMO site with SYNTHETIC wind data for the operator console (not evidence of anything).

Creates <dir>/demo.db with: a synthetic wind farm (6 turbines, 20 days of 10-minute SCADA, one injected HSS-bearing
fault on WT03), an approved wind NBM trained on a separate synthetic fleet, commissioned baselines, two technicians and
a part, assessments at the end of the record, and generated recommendations. Users and their API keys are written to
<dir>/demo_credentials.json (keep it local; the directory is git-ignored when it is under artifacts_demo/).

Usage: SENTINELLOOP_AUDIT_KEY=<hex> python product/scripts/demo_site.py [artifacts_demo/console]
(the default is the directory product/scripts/run_demo_api.py reads)
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from sentinelloop.app import admin, decision, health, ingest, modelreg, nbm, policy as policymod, resources, security, synthetic_wind as sw  # noqa: E402
from sentinelloop.app import db as dbmod  # noqa: E402
from sentinelloop.app.adapters import wind  # noqa: E402
from sentinelloop.app.timeutil import DAY_MS, HOUR_MS, iso  # noqa: E402


def main(out_dir: str):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    key, kid = admin.audit_key_from_env()
    dbp = out / "demo.db"
    if dbp.exists():
        raise SystemExit(f"{dbp} exists; remove it first")
    d = dbmod.Database(dbp, audit_key=key, audit_key_id=kid)
    d.migrate()
    wind.ensure_site_and_type(d, actor="demo", site_name="Demo wind farm (SYNTHETIC data)")
    gen = sw.generate(sw.FleetSpec(n_turbines=6, days=20, seed=21, faults=(sw.Fault("WT03", "hss_bearing", 9.0, 21.0, 22.0),),
                                   sensor_faults=(sw.SensorFault("WT05", "gearbox_oil_temp", "stuck", 19.5, 20.0),)))
    st = gen.meta["start_ms"]
    for i, t in enumerate(sorted(gen.scada.turbine.unique())):
        wind.create_turbine(d, t, criticality="A" if t in ("WT03", "WT01") else "B", actor="demo", windows_from_ms=st + 20 * DAY_MS, window_days=10)
        part = gen.scada[gen.scada.turbine == t]
        ingest.ingest_records(d, wind.records(part), source="demo-synthetic", actor="demo", now_ms=st + 21 * DAY_MS)
    train = sw.generate(sw.FleetSpec(n_turbines=4, days=30, seed=3)).scada
    bdir = nbm.package_wind_nbm(train, out / "models", scope_key="wind:synthetic", data_class="SYNTHETIC", source="demo: synthetic_wind seed 3")
    mid = modelreg.register(d, bdir, actor="demo")
    modelreg.decide(d, mid, "approved", actor="demo", role="admin", reason="demo")
    for t in sorted(gen.scada.turbine.unique()):
        try:
            nbm.commission(d, t, mid, st, st + 8 * DAY_MS, actor="demo", role="admin", reason="demo: days 0-8 synthetic, no fault injected yet")
        except nbm.CommissionError as e:
            print(f"{t}: not commissioned ({e})")
    resources.upsert_technician(d, "T1", "Asha (demo)", wind.SITE_ID, ["wtg_technician"], actor="demo")
    resources.upsert_technician(d, "T2", "Ravi (demo)", wind.SITE_ID, ["wtg_technician", "scada_technician"], actor="demo")
    shifts = [(iso(st + (20 + k) * DAY_MS + 7 * HOUR_MS), iso(st + (20 + k) * DAY_MS + 17 * HOUR_MS)) for k in range(10)]
    for t in ("T1", "T2"):
        resources.set_shifts(d, t, shifts, actor="demo")
    pol = policymod.load(ROOT / "configs" / "platform.yaml")
    as_of = st + 20 * DAY_MS - 10 * 60 * 1000
    for t in sorted(gen.scada.turbine.unique()):
        a = health.assess(d, t, pol, as_of_ms=as_of, actor="demo")
        print(t, a["health_state"])
    decision.generate(d, decision.DecisionConfig(), actor="demo", now_ms=as_of)
    creds = {}
    for uid, role in (("planner", "planner"), ("engineer", "reliability_engineer"), ("tech", "technician"), ("viewer", "viewer"), ("admin", "admin")):
        security.create_user(d, uid, f"Demo {role}", role, actor="demo")
        creds[uid] = {"role": role, "api_key": security.issue_api_key(d, uid, actor="demo")}
    (out / "demo_credentials.json").write_text(json.dumps(creds, indent=1), encoding="utf-8")
    print(f"demo site ready: {dbp}; credentials in {out / 'demo_credentials.json'}; time of the demo data: {iso(as_of)}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "artifacts_demo/console")
