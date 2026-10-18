"""R1: recovery drill with real processes (SYNTHETIC data). Every step uses the admin CLI or the HTTP API.

 1. init + create-admin (CLI); start the server; ingest two days; create and approve a work order (API).
 2. backup (CLI) -> backup file + audit anchor.
 3. more writes after the backup (they define the recovery point objective: lost if the disk is lost now).
 4. crash: kill the server process hard while ingestion requests are in flight; restart it; check SQLite integrity
    and the audit chain on the live database (WAL recovery must leave a consistent state: whole batches or nothing).
 5. disaster: delete the live database; restore the backup to a new path; verify the audit chain against the
    backup's anchor; start the server on the restored database; measure the time from restore to ready.
 6. tamper check: edit one audit event in a copy; verification must fail.
Output: product/evidence/recovery/r1.{json,md}.
"""
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from contextlib import closing
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from sentinelloop.app import synthetic_wind as sw  # noqa: E402
from sentinelloop.app.adapters import wind  # noqa: E402
from sentinelloop.app.timeutil import DAY_MS  # noqa: E402

OUT = ROOT / "product" / "evidence" / "recovery"
KEYHEX = "3c" * 32
PORT = 8092
ENV = {**os.environ, "SENTINELLOOP_AUDIT_KEY": KEYHEX, "SENTINELLOOP_AUDIT_KEY_ID": "drill", "PYTHONPATH": str(ROOT / "src")}


def cli(*args):
    r = subprocess.run([sys.executable, "-m", "sentinelloop.app.admin", *args], cwd=str(ROOT), env=ENV, capture_output=True, text=True)
    return r.returncode, r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "", r.stderr.strip()


def serve(dbp):
    p = subprocess.Popen([sys.executable, "-m", "sentinelloop.app.admin", "serve", "--db", str(dbp), "--port", str(PORT),
                          "--policy", str(ROOT / "configs" / "platform.yaml"), "--rate-limit", "100000,10000"],
                         cwd=str(ROOT), env=ENV, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    t0 = time.perf_counter()
    for _ in range(200):
        try:
            if httpx.get(f"http://127.0.0.1:{PORT}/api/v1/ready", timeout=1).status_code == 200:
                return p, time.perf_counter() - t0
        except Exception:
            pass
        time.sleep(0.1)
    p.kill()
    raise SystemExit("server did not become ready")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="sl_drill_"))
    live, backup, restored = work / "live.db", work / "backup.db", work / "restored.db"
    log, res = [], {"data_class": "SYNTHETIC"}

    def step(msg):
        log.append(f"{time.strftime('%H:%M:%S')} {msg}")
        print(log[-1])

    code, out, err = cli("init", "--db", str(live))
    step(f"init exit {code}")
    code, out, err = cli("create-admin", "--db", str(live), "--user", "root", "--name", "Root")
    key = json.loads(out)["api_key"]
    step(f"create-admin exit {code}")
    H = {"Authorization": f"Bearer {key}"}
    api = f"http://127.0.0.1:{PORT}/api/v1"
    srv, _ = serve(live)
    gen = sw.generate(sw.FleetSpec(n_turbines=2, days=6, seed=5))
    st = gen.meta["start_ms"]
    try:
        httpx.post(f"{api}/users", json={"user_id": "svc", "display_name": "svc", "role": "integration"}, headers=H).raise_for_status()
        svc = {"Authorization": f"Bearer {httpx.post(f'{api}/users/svc/api-key', headers=H).json()['api_key']}"}
        # site, type and turbines via the library on the same file (the API has no asset-type route; documented)
        from sentinelloop.app import db as dbmod
        d = dbmod.Database(live, audit_key=bytes.fromhex(KEYHEX), audit_key_id="drill")   # connections close after each call
        wind.ensure_site_and_type(d, actor="root")
        for t in ("WT01", "WT02"):
            wind.create_turbine(d, t, criticality="A", actor="root")

        def ingest_days(day0, day1, client_headers):
            n = 0
            for t, g in gen.scada.groupby("turbine"):
                for dd in range(day0, day1):
                    part = g[(g.ts_ms >= st + dd * DAY_MS) & (g.ts_ms < st + (dd + 1) * DAY_MS)]
                    r = httpx.post(f"{api}/ingest/readings", json={"records": wind.records(part), "source": "drill"}, headers=client_headers, timeout=120)
                    r.raise_for_status()
                    n += r.json()["rows_accepted"]
            return n
        res["rows_before_backup"] = ingest_days(0, 2, svc)
        wo = httpx.post(f"{api}/work-orders", json={"asset_id": "WT01", "job_type": "inspect", "priority_class": "P2", "title": "drill"},
                        headers={**H, "Idempotency-Key": "drill-1"}).json()
        for act in ("submit", "approve"):
            httpx.post(f"{api}/work-orders/{wo['wo_id']}/transitions", json={"action": act}, headers=H).raise_for_status()
        step(f"ingested {res['rows_before_backup']} rows, work order {wo['wo_id']} approved")

        t0 = time.perf_counter()
        code, out, err = cli("backup", "--db", str(live), "--to", str(backup))
        res["backup"] = {"exit": code, "seconds": round(time.perf_counter() - t0, 2), "bytes": backup.stat().st_size, "anchor": json.loads(out)["anchor"]}
        step(f"backup exit {code} ({res['backup']['bytes']} bytes, anchor seq {res['backup']['anchor']['seq']})")
        res["rows_after_backup"] = ingest_days(2, 3, svc)
        step(f"ingested {res['rows_after_backup']} more rows after the backup (these define the RPO)")

        # 4. crash during writes
        errors = []

        def flood():
            try:
                ingest_days(3, 6, svc)
            except Exception as e:
                errors.append(type(e).__name__)
        th = threading.Thread(target=flood)
        th.start()
        time.sleep(1.5)
        srv.kill()                                                     # hard kill, no shutdown handlers
        srv.wait()
        th.join()
        step(f"server killed during ingestion (client saw {errors or 'no error'})")
        with closing(sqlite3.connect(live)) as c:
            integ = c.execute("PRAGMA integrity_check").fetchone()[0]
            rows = c.execute("SELECT COUNT(*) FROM readings").fetchone()[0]
            partial = c.execute("SELECT COUNT(*) FROM ingestion_batches b WHERE rows_accepted != (SELECT COUNT(*) FROM readings r WHERE r.batch_id = b.batch_id)"
                                ).fetchone()[0] if "batch_id" in [x[1] for x in c.execute("PRAGMA table_info(readings)")] else None
        code, out, err = cli("verify-audit", "--db", str(live), "--anchor", str(backup) + ".anchor.json")   # the earlier anchor, kept apart
        res["crash"] = {"integrity_check": integ, "readings": rows, "batches_with_mismatched_counts": partial, "audit_verify_exit": code,
                        "audit": json.loads(out) if out else err}
        step(f"after crash: integrity {integ}, readings {rows}, audit verify exit {code}")
        srv, restart_s = serve(live)
        res["crash"]["restart_to_ready_s"] = round(restart_s, 2)
        step(f"restarted on the live database in {restart_s:.2f} s")
        srv.terminate()
        srv.wait(10)

        # 5. disaster recovery
        live.unlink()
        for side in ("-wal", "-shm"):
            Path(str(live) + side).unlink(missing_ok=True)
        step("live database deleted (simulated disk loss)")
        t0 = time.perf_counter()
        code, out, err = cli("restore", "--from", str(backup), "--db", str(restored))
        rc_restore = code
        code, out_v, err = cli("verify-audit", "--db", str(restored))
        srv, ready_s = serve(restored)
        rto = time.perf_counter() - t0
        n_assets = len(httpx.get(f"{api}/assets", headers=H).json())
        wo_back = httpx.get(f"{api}/work-orders/{wo['wo_id']}", headers=H).json()
        with closing(sqlite3.connect(restored)) as c:
            rows_restored = c.execute("SELECT COUNT(*) FROM readings").fetchone()[0]
        res["restore"] = {"restore_exit": rc_restore, "verify_exit": code, "verify": json.loads(out_v) if out_v else err,
                          "restore_to_ready_s": round(rto, 2), "assets": n_assets, "work_order_state": wo_back.get("state"),
                          "readings_restored": rows_restored, "readings_lost_after_backup": res["rows_after_backup"] if rows_restored == res["rows_before_backup"] else None}
        step(f"restored, audit verify exit {code} (anchor checked: {res['restore']['verify'].get('anchor_checked') if isinstance(res['restore']['verify'], dict) else '?'}), "
             f"ready in {rto:.2f} s; work order state {wo_back.get('state')}; readings {rows_restored}")
        srv.terminate()
        srv.wait(10)

        # 6. tamper check on a copy
        copy = work / "tampered.db"
        shutil.copyfile(restored, copy)
        shutil.copyfile(str(restored) + ".anchor.json", str(copy) + ".anchor.json")
        with closing(sqlite3.connect(copy)) as c:
            c.execute("UPDATE audit_events SET payload_json = '{\"tampered\": true}' WHERE seq = 3")
            c.commit()
        code, out, err = cli("verify-audit", "--db", str(copy))
        res["tamper"] = {"verify_exit": code, "result": json.loads(out) if out else err}
        step(f"tampered copy: verify exit {code}")
        shutil.copyfile(restored, copy)                                            # fresh copy, then truncation: drop the newest events
        with closing(sqlite3.connect(copy)) as c:
            c.execute("DELETE FROM audit_events WHERE seq > (SELECT MAX(seq) - 3 FROM audit_events)")
            c.commit()
        shutil.copyfile(str(restored) + ".anchor.json", str(copy) + ".anchor.json")
        code, out, err = cli("verify-audit", "--db", str(copy))
        res["truncation"] = {"verify_exit": code, "result": json.loads(out) if out else err}
        step(f"truncated copy: verify exit {code}")
    finally:
        try:
            srv.kill()
        except Exception:
            pass
    res["log"] = log
    (OUT / "r1.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    c, r = res["crash"], res["restore"]
    md = ["# R1 recovery drill (generated; SYNTHETIC data; real processes on this machine)", "",
          "| step | result |", "|---|---|",
          f"| backup | exit {res['backup']['exit']}, {res['backup']['seconds']} s, {res['backup']['bytes'] / 1e6:.1f} MB, anchor seq {res['backup']['anchor']['seq']} |",
          f"| hard kill during ingestion | SQLite integrity: {c['integrity_check']}; audit verify exit {c['audit_verify_exit']}; "
          f"batches whose stored rows differ from their count: {c['batches_with_mismatched_counts']}; restart to ready {c['restart_to_ready_s']} s |",
          f"| restore after deleting the live database | restore exit {r['restore_exit']}; audit verify against the anchor exit {r['verify_exit']}; "
          f"restore to ready {r['restore_to_ready_s']} s (RTO on this machine); work order state {r['work_order_state']}; "
          f"readings {r['readings_restored']} (the {res['rows_after_backup']} rows written after the backup are lost: RPO = time since the last backup) |",
          f"| edited audit event in a copy | verify exit {res['tamper']['verify_exit']} (must be 1) |",
          f"| truncated audit chain in a copy | verify exit {res['truncation']['verify_exit']} (must be 1) |", "",
          "Log:", "", "```", *log, "```"]
    (OUT / "r1.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md[:9]))


if __name__ == "__main__":
    main()
