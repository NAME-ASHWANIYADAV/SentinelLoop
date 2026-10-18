"""L1: load test of the platform API on this machine (SYNTHETIC wind data; one site).

A real server process (admin serve, uvicorn) on 127.0.0.1 and real HTTP clients in threads. The rate limit is raised
for the test (it would otherwise be what is measured). Measures:
  1. ingestion throughput: one day of 10-minute SCADA per turbine per request, 4 concurrent clients;
  2. fleet assessment: every turbine assessed once (sequential and with 4 clients), compared with the 10-minute data
     interval, the budget for assessing a whole fleet;
  3. decision generation over the fleet;
  4. read latency: GET /assets and /work-orders with 8 concurrent clients for 20 s.
Output: product/evidence/load/l1.{json,md}. Hardware is recorded; numbers hold for this machine only.
"""
import json
import os
import platform
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from sentinelloop.app import auditlog, db as dbmod, modelreg, nbm, security, synthetic_wind as sw  # noqa: E402
from sentinelloop.app.adapters import wind  # noqa: E402
from sentinelloop.app.timeutil import DAY_MS, iso  # noqa: E402

OUT = ROOT / "product" / "evidence" / "load"
N_TURB, DAYS, PORT = int(os.environ.get("L1_TURBINES", 50)), 8, 8091
KEYHEX = "5a" * 32


def pct(xs, q):
    xs = sorted(xs)
    return round(xs[min(len(xs) - 1, int(q * len(xs)))] * 1000, 1) if xs else None


def wait_ready(base):
    for _ in range(150):
        try:
            if httpx.get(f"{base}/health", timeout=1).status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.2)
    return False


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="sl_load_"))
    dbp = tmp / "load.db"
    env = {**os.environ, "SENTINELLOOP_AUDIT_KEY": KEYHEX, "SENTINELLOOP_AUDIT_KEY_ID": "load", "PYTHONPATH": str(ROOT / "src")}
    d = dbmod.Database(dbp, audit_key=bytes.fromhex(KEYHEX), audit_key_id="load")
    d.migrate()
    wind.ensure_site_and_type(d, actor="admin")
    names = [f"WT{i + 1:02d}" for i in range(N_TURB)]
    for i, n in enumerate(names):
        wind.create_turbine(d, n, criticality="ABC"[i % 3], actor="admin")
    keys = {}
    for uid, role in (("svc", "integration"), ("rea", "reliability_engineer"), ("vic", "viewer")):
        security.create_user(d, uid, uid, role, actor="bootstrap")
        keys[uid] = security.issue_api_key(d, uid, actor="bootstrap")
    train = sw.generate(sw.FleetSpec(n_turbines=4, days=30, seed=3)).scada
    bdir = nbm.package_wind_nbm(train, tmp / "models", scope_key="wind:synthetic", data_class="SYNTHETIC", source="load test")
    mid = modelreg.register(d, bdir, actor="rea")
    modelreg.decide(d, mid, "approved", actor="rea", role="reliability_engineer", reason="load test")
    faults = tuple(sw.Fault(names[i], "hss_bearing", 5.0, 9.0, 20.0) for i in range(0, N_TURB, 10))
    gen = sw.generate(sw.FleetSpec(n_turbines=N_TURB, days=DAYS, seed=8, faults=faults))
    st = gen.meta["start_ms"]

    srv = subprocess.Popen([sys.executable, "-m", "sentinelloop.app.admin", "serve", "--db", str(dbp), "--port", str(PORT),
                            "--policy", str(ROOT / "configs" / "platform.yaml"), "--rate-limit", "100000,10000"],
                           cwd=str(ROOT), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{PORT}/api/v1"
    if not wait_ready(base):
        srv.kill()
        raise SystemExit("server did not start")
    res = {"machine": {"platform": platform.platform(), "processor": platform.processor(), "cpus": os.cpu_count(), "python": platform.python_version()},
           "turbines": N_TURB, "days": DAYS, "data_class": "SYNTHETIC"}
    try:
        # 1. ingestion
        batches = []
        for t, g in gen.scada.groupby("turbine"):
            for day in range(DAYS):
                part = g[(g.ts_ms >= st + day * DAY_MS) & (g.ts_ms < st + (day + 1) * DAY_MS)]
                batches.append(wind.records(part))
        hdr = {"Authorization": f"Bearer {keys['svc']}"}

        def post(recs):
            t0 = time.perf_counter()
            r = httpx.post(f"{base}/ingest/readings", json={"records": recs, "source": "load"}, headers=hdr, timeout=300)
            return time.perf_counter() - t0, r.status_code, r.json().get("rows_accepted", 0) if r.status_code == 200 else 0
        lat, rows, errs = [], 0, 0
        t0 = time.perf_counter()
        with ThreadPoolExecutor(4) as ex:
            for dt, code, acc in ex.map(post, batches):
                lat.append(dt)
                rows += acc
                errs += code != 200
        wall = time.perf_counter() - t0
        res["ingestion"] = {"requests": len(batches), "rows": rows, "errors": errs, "wall_s": round(wall, 1), "rows_per_s": round(rows / wall),
                            "p50_ms": pct(lat, 0.5), "p95_ms": pct(lat, 0.95), "clients": 4, "rows_per_request": len(batches[0])}
        commissioned = 0
        for n in names:                          # days 0-4 declared healthy (no fault starts before day 5)
            try:
                nbm.commission(d, n, mid, st, st + 4 * DAY_MS, actor="rea", role="reliability_engineer", reason="load test baseline")
                commissioned += 1
            except nbm.CommissionError:
                pass
        res["commissioned"] = commissioned
        # 2. fleet assessment
        as_of = st + int(8 * DAY_MS) - 600_000
        h2 = {"Authorization": f"Bearer {keys['rea']}"}

        def assess(a):
            t0 = time.perf_counter()
            r = httpx.post(f"{base}/assets/{a}/assess", json={"as_of": iso(as_of)}, headers=h2, timeout=120)
            return time.perf_counter() - t0, r.status_code, r.json().get("health_state") if r.status_code == 200 else None
        t0 = time.perf_counter()
        seq = [assess(a) for a in names]
        seq_wall = time.perf_counter() - t0
        t0 = time.perf_counter()
        with ThreadPoolExecutor(4) as ex:
            par = list(ex.map(assess, names))
        par_wall = time.perf_counter() - t0
        states = {}
        for _, _, s in par:
            states[s] = states.get(s, 0) + 1
        res["assessment"] = {"assets": len(names), "sequential_wall_s": round(seq_wall, 1), "parallel4_wall_s": round(par_wall, 1),
                             "p50_ms": pct([x[0] for x in seq], 0.5), "p95_ms": pct([x[0] for x in seq], 0.95),
                             "errors": sum(1 for x in seq + par if x[1] != 200), "states": states, "budget_s": 600,
                             "fits_10_min_interval": par_wall < 600}
        # 3. decisions
        t0 = time.perf_counter()
        r = httpx.post(f"{base}/decisions/generate", headers=h2, timeout=300)
        res["decisions"] = {"wall_s": round(time.perf_counter() - t0, 2), "status": r.status_code,
                            "created": sum(1 for x in r.json() if x.get("action") == "created") if r.status_code == 200 else None}
        # 4. reads
        h3 = {"Authorization": f"Bearer {keys['vic']}"}
        stop = time.time() + 20
        lat_a, lat_w, codes = [], [], {}
        lock = threading.Lock()

        def reader(k):
            with httpx.Client(timeout=60) as c:
                while time.time() < stop:
                    path = "/assets" if k % 2 == 0 else "/work-orders"
                    t1 = time.perf_counter()
                    rr = c.get(f"{base}{path}", headers=h3)
                    dt = time.perf_counter() - t1
                    with lock:
                        (lat_a if path == "/assets" else lat_w).append(dt)
                        codes[rr.status_code] = codes.get(rr.status_code, 0) + 1
        th = [threading.Thread(target=reader, args=(k,)) for k in range(8)]
        for t in th:
            t.start()
        for t in th:
            t.join()
        res["reads"] = {"clients": 8, "duration_s": 20, "requests": len(lat_a) + len(lat_w), "status_codes": codes,
                        "assets_p50_ms": pct(lat_a, 0.5), "assets_p95_ms": pct(lat_a, 0.95), "assets_p99_ms": pct(lat_a, 0.99),
                        "work_orders_p50_ms": pct(lat_w, 0.5), "work_orders_p95_ms": pct(lat_w, 0.95),
                        "throughput_rps": round((len(lat_a) + len(lat_w)) / 20, 1)}
        with d.connect() as c:
            v = auditlog.verify(c, d.audit_key)
        res["audit_after_load"] = {"valid": v["valid"], "events": v["n"]}
        res["db_bytes"] = dbp.stat().st_size
    finally:
        srv.terminate()
        try:
            srv.wait(10)
        except Exception:
            srv.kill()
    (OUT / "l1.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    i, a, rd = res["ingestion"], res["assessment"], res["reads"]
    md = ["# L1 load test (generated; SYNTHETIC wind data; this machine only)", "",
          f"Machine: {res['machine']['platform']}, {res['machine']['cpus']} logical CPUs, Python {res['machine']['python']}. "
          f"Server: one uvicorn process, SQLite WAL. {N_TURB} turbines x {DAYS} days of 10-minute SCADA (10 signals); "
          f"{res['commissioned']} turbines commissioned.", "",
          "| measure | result |", "|---|---|",
          f"| ingestion | {i['rows']:,} rows in {i['requests']} requests ({i['rows_per_request']} rows each), 4 clients, {i['wall_s']} s: "
          f"{i['rows_per_s']:,} rows/s; request p50 {i['p50_ms']} ms, p95 {i['p95_ms']} ms; errors {i['errors']} |",
          f"| fleet assessment | {a['assets']} turbines: sequential {a['sequential_wall_s']} s, 4 clients {a['parallel4_wall_s']} s "
          f"(budget: one 10-minute interval = 600 s; fits: {a['fits_10_min_interval']}); per assessment p50 {a['p50_ms']} ms, p95 {a['p95_ms']} ms; "
          f"errors {a['errors']}; states {a['states']} |",
          f"| decision generation | {res['decisions']['wall_s']} s for the fleet; orders created {res['decisions']['created']} |",
          f"| reads (8 clients, 20 s) | {rd['throughput_rps']} req/s; /assets p50 {rd['assets_p50_ms']} ms, p95 {rd['assets_p95_ms']} ms, "
          f"p99 {rd['assets_p99_ms']} ms; /work-orders p50 {rd['work_orders_p50_ms']} ms, p95 {rd['work_orders_p95_ms']} ms; "
          f"status codes {rd['status_codes']} |",
          f"| audit chain after load | valid {res['audit_after_load']['valid']}, {res['audit_after_load']['events']:,} events |",
          f"| database size | {res['db_bytes'] / 1e6:.1f} MB |"]
    (OUT / "l1.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
