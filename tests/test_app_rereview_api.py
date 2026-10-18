"""Regression tests for the API, ingest and admin defects confirmed by the re-review of the Phase 9 fixes.

Each test names the finding it covers (api-security-console-N). They were written before the fixes and failed then,
except where a section says otherwise.
"""
import asyncio
import inspect
import json
import os
import sqlite3
import time

import httpx
import pytest
from fastapi.testclient import TestClient

from sentinelloop.app import (admin, api, auditlog, db as dbmod, health, ingest, integration, policy as policymod, registry, resources, security,
                              workorders)
from sentinelloop.app.timeutil import HOUR_MS, iso, now_ms
from conftest import ROOT
from test_app_foundation import KEY, pump, pump_type

POL = policymod.load(ROOT / "configs" / "platform.yaml")
ROLES = (("ada", "admin"), ("pat", "planner"), ("rea", "reliability_engineer"), ("tom", "technician"), ("vic", "viewer"), ("svc", "integration"))


def _plant(tmp_path):
    d = dbmod.Database(tmp_path / "rr.db", audit_key=KEY, audit_key_id="test")
    d.migrate()
    registry.create_site(d, "site1", "Plant 1", "UTC", actor="admin")
    registry.create_asset_type(d, pump_type(), actor="admin")
    registry.create_asset(d, pump("P-101"), actor="admin")
    registry.create_asset(d, pump("P-103", tag="TAG-103"), actor="admin")
    keys = {}
    for uid, role in ROLES:
        security.create_user(d, uid, uid.title(), role, actor="bootstrap")
        keys[role] = security.issue_api_key(d, uid, actor="bootstrap")
    return d, keys


@pytest.fixture
def ctx(tmp_path):
    d, keys = _plant(tmp_path)
    app = api.create_app(d, POL, rate_limit=(100_000, 100_000.0))
    return {"db": d, "keys": keys, "app": app, "client": TestClient(app, raise_server_exceptions=False)}


def H(ctx, role):
    return {"Authorization": f"Bearer {ctx['keys'][role]}"}


def n_assessments(d, asset_id):
    with d.connect() as c:
        return c.execute("SELECT COUNT(*) FROM assessments WHERE asset_id = ?", (asset_id,)).fetchone()[0]


# -- api-security-console-1: assess-range is charged by its work ---------------------------------------------------------
def test_the_rate_limiter_can_charge_more_than_one_token():
    lim = security.RateLimiter(capacity=10, refill_per_s=0.0001)
    assert lim.allow("u", cost=7)[0] is True
    ok, retry = lim.allow("u", cost=7)                     # 3 left: refused, nothing taken
    assert ok is False and retry > 0
    assert lim.allow("u", cost=3)[0] is True


def test_assess_range_is_charged_one_token_per_ten_steps_and_refused_with_429_when_unpaid(tmp_path):
    d, keys = _plant(tmp_path)
    c = TestClient(api.create_app(d, POL, rate_limit=(20, 0.0001)), raise_server_exceptions=False)
    h = {"Authorization": f"Bearer {keys['integration']}"}
    t = now_ms() - 10 * HOUR_MS
    body = {"start": iso(t), "end": iso(t + 149 * 60_000), "step_minutes": 1}        # 150 steps: 15 tokens
    r = c.post("/api/v1/assets/P-101/assess-range", json=body, headers=h)
    assert r.status_code == 200 and r.json()["assessments"] == 150
    before = n_assessments(d, "P-101")
    r = c.post("/api/v1/assets/P-101/assess-range", json=body, headers=h)            # 4 tokens left: cannot pay
    assert r.status_code == 429 and int(r.headers["Retry-After"]) >= 1
    assert n_assessments(d, "P-101") == before                                         # nothing computed or stored


def test_a_range_the_bucket_can_never_pay_is_refused_without_work(tmp_path):
    d, keys = _plant(tmp_path)
    c = TestClient(api.create_app(d, POL, rate_limit=(20, 0.0001)), raise_server_exceptions=False)
    t = now_ms() - 10 * HOUR_MS
    r = c.post("/api/v1/assets/P-101/assess-range", json={"start": iso(t), "end": iso(t + 299 * 60_000), "step_minutes": 1},
               headers={"Authorization": f"Bearer {keys['integration']}"})                 # 300 steps = 30 tokens > capacity 20
    assert r.status_code == 422 and "split the range" in r.json()["error"]                 # 429 would invite retrying forever
    assert n_assessments(d, "P-101") == 0


def test_health_does_not_wait_for_the_worker_threads(ctx):
    """The liveness route runs on the event loop, so busy worker threads (e.g. long assess-range calls) cannot stall it."""
    route = next(r for r in ctx["app"].routes if getattr(r, "path", "") == "/api/v1/health")
    assert inspect.iscoroutinefunction(route.endpoint)
    assert ctx["client"].get("/api/v1/health").json() == {"status": "ok"}


def test_the_assess_range_docstring_states_its_cost(ctx):
    route = next(r for r in ctx["app"].routes if getattr(r, "path", "") == "/api/v1/assets/{asset_id}/assess-range")
    assert "token" in (route.endpoint.__doc__ or "")


# -- api-security-console-11 (a, b): assess-range resolves tags and validates the whole range up front ----------------
# health.assess_range now makes the same checks itself, so these three pass without the route's own checks: they are
# kept as contract tests of the route (test_a_range_refused_by_validation_is_not_charged covers the route's ordering).
def test_assess_range_accepts_a_tag_like_assess_does(ctx):
    c, t = ctx["client"], now_ms() - 2 * HOUR_MS
    r = c.post("/api/v1/assets/TAG-103/assess-range", json={"start": iso(t), "end": iso(t + 20 * 60_000), "step_minutes": 10},
               headers=H(ctx, "integration"))
    assert r.status_code == 200, r.text
    assert r.json()["asset_id"] == "P-103" and r.json()["assessments"] == 3 and n_assessments(ctx["db"], "P-103") == 3


def test_a_range_ending_in_the_future_is_refused_whole(ctx):
    c, t = ctx["client"], now_ms()
    r = c.post("/api/v1/assets/P-101/assess-range", json={"start": iso(t - HOUR_MS), "end": iso(t + 6 * HOUR_MS), "step_minutes": 10},
               headers=H(ctx, "integration"))
    assert r.status_code == 422 and "future" in r.json()["error"]
    assert n_assessments(ctx["db"], "P-101") == 0 and health.asset_state(ctx["db"], "P-101") is None


def test_assess_range_for_an_unknown_asset_is_404(ctx):
    t = now_ms() - HOUR_MS
    r = ctx["client"].post("/api/v1/assets/NOPE/assess-range", json={"start": iso(t), "end": iso(t), "step_minutes": 10}, headers=H(ctx, "integration"))
    assert r.status_code == 404


# -- api-security-console-7: planning requests are bounded ---------------------------------------------------------------
@pytest.mark.parametrize("slot_h", [0.1, 0.0001, 1e-6])
def test_schedule_slots_below_a_quarter_hour_are_refused(ctx, slot_h):
    r = ctx["client"].post("/api/v1/schedules", json={"site_id": "site1", "horizon_h": 336, "slot_h": slot_h}, headers=H(ctx, "planner"))
    assert r.status_code == 422 and "slot_h" in r.json()["error"]


def test_a_quarter_hour_slot_is_still_accepted(ctx):
    r = ctx["client"].post("/api/v1/schedules", json={"site_id": "site1", "horizon_h": 24, "slot_h": 0.25}, headers=H(ctx, "planner"))
    assert r.status_code == 200, r.text


# -- api-security-console-2: verification without an anchor says so; partial anchors are refused --------------------------
def test_audit_verify_without_an_anchor_says_it_was_not_anchored(ctx):
    c = ctx["client"]
    v = c.get("/api/v1/audit/verify", headers=H(ctx, "admin")).json()
    assert v["anchor_checked"] is False
    with ctx["db"].connect() as conn:
        a = auditlog.anchor(conn)
    v = c.get(f"/api/v1/audit/verify?anchor_seq={a['seq']}&anchor_hash={a['hash']}", headers=H(ctx, "admin")).json()
    assert v["valid"] is True and v["anchor_checked"] is True


def test_audit_verify_detects_truncation_only_with_the_anchor(ctx):
    c, d = ctx["client"], ctx["db"]
    with d.connect() as conn:
        a = auditlog.anchor(conn)
    with sqlite3.connect(d.path) as conn:                                              # delete the newest events
        conn.execute("DELETE FROM audit_events WHERE seq > ?", (a["seq"] - 3,))
    v = c.get("/api/v1/audit/verify", headers=H(ctx, "admin")).json()
    assert v["anchor_checked"] is False                                                # never a plain 'valid'
    v = c.get(f"/api/v1/audit/verify?anchor_seq={a['seq']}&anchor_hash={a['hash']}", headers=H(ctx, "admin")).json()
    assert v["valid"] is False and v["anchor_checked"] is True


@pytest.mark.parametrize("query", ["anchor_seq=5", "anchor_hash=" + "a" * 64, "anchor_seq=5&anchor_hash=xyz", "anchor_seq=0&anchor_hash=" + "a" * 64,
                                   "anchor_seq=5&anchor_hash="])
def test_a_partial_or_malformed_anchor_is_refused(ctx, query):
    r = ctx["client"].get(f"/api/v1/audit/verify?{query}", headers=H(ctx, "admin"))
    assert r.status_code == 422, (query, r.status_code, r.text)


@pytest.fixture
def cli_db(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("SENTINELLOOP_AUDIT_KEY", "ab" * 32)
    db = str(tmp_path / "p.db")
    admin.main(["init", "--db", db])
    admin.main(["create-admin", "--db", db, "--user", "root", "--name", "Root"])
    admin.main(["backup", "--db", db, "--to", str(tmp_path / "b.db")])
    with sqlite3.connect(db) as c:                                                     # truncate the chain after the backup
        c.execute("DELETE FROM audit_events WHERE seq > 1")
    capsys.readouterr()
    return db, tmp_path


@pytest.mark.parametrize("content", ["{}", "[]", "null", '{"seq": 3}', '{"hash": "' + "a" * 64 + '"}', '{"seq": "3", "hash": "' + "a" * 64 + '"}',
                                     '{"seq": 3, "hash": "short"}', '{"seq": true, "hash": "' + "a" * 64 + '"}', "not json", "",
                                     '{"seq": 9223372036854775808, "hash": "' + "a" * 64 + '"}', '{"seq": ' + "9" * 30 + ', "hash": "' + "a" * 64 + '"}'])
def test_the_cli_refuses_an_anchor_file_without_the_required_fields(cli_db, content, capsys):
    db, tmp = cli_db
    f = tmp / "anchor.json"
    f.write_text(content, encoding="utf-8")
    rc = admin.main(["verify-audit", "--db", db, "--anchor", str(f)])
    out = capsys.readouterr()
    assert rc != 0 and '"anchor_checked": true' not in out.out
    assert "anchor" in out.err and "Traceback" not in out.err


def test_the_cli_still_detects_truncation_with_a_real_anchor(cli_db, capsys):
    db, tmp = cli_db
    assert admin.main(["verify-audit", "--db", db, "--anchor", str(tmp / "b.db.anchor.json")]) == 1
    assert json.loads(capsys.readouterr().out)["anchor_checked"] is True


# -- api-security-console-8: credential variable names, hosts and server paths reach admins only -----------------------
@pytest.fixture
def ictx(ctx, monkeypatch):
    monkeypatch.setenv("SENTINELLOOP_INTEGRATION_HOSTS", "cmms.plant.example")
    monkeypatch.delenv("SENTINELLOOP_CRED_ODOO_PROD", raising=False)
    d = ctx["db"]
    integration.register_target(d, "odoo", "odoo_json2", "https://cmms.plant.example", {"database": "prod", "api_key_env": "SENTINELLOOP_CRED_ODOO_PROD"},
                                actor="ada", role="admin", mode="draft_requests", reason="go live")
    o = workorders.create(d, asset_id="P-101", job_type="inspect", priority_class="P2", title="t", origin="manual", actor="pat", role="planner",
                          idempotency_key="ir1")
    for a in ("submit", "approve"):
        workorders.transition(d, o["wo_id"], a, actor="pat", role="planner")
    assert ctx["client"].post("/api/v1/integrations/odoo/dispatch", headers=H(ctx, "integration")).status_code == 200    # fails: variable unset
    return {**ctx, "wo": o["wo_id"]}


def test_non_admins_do_not_see_integration_hosts_or_config(ictx):
    c = ictx["client"]
    for role in ("planner", "reliability_engineer", "integration"):
        t = c.get("/api/v1/integrations", headers=H(ictx, role)).json()[0]
        assert "config" not in t and "base_url" not in t and "cmms.plant.example" not in json.dumps(t), role
    t = c.get("/api/v1/integrations", headers=H(ictx, "admin")).json()[0]
    assert t["base_url"] == "https://cmms.plant.example" and t["config"]["api_key_env"] == "SENTINELLOOP_CRED_ODOO_PROD"


def test_non_admins_do_not_see_dispatch_error_detail(ictx):
    c = ictx["client"]
    for role in ("planner", "reliability_engineer", "integration"):
        items = c.get("/api/v1/integrations/odoo/items", headers=H(ictx, role)).json()
        assert items and items[0]["status"] == "dead" and items[0]["last_error"], role                  # still told that it failed
        assert "SENTINELLOOP_CRED" not in json.dumps(items), role
    items = c.get("/api/v1/integrations/odoo/items", headers=H(ictx, "admin")).json()
    assert "SENTINELLOOP_CRED_ODOO_PROD" in items[0]["last_error"]


def test_open_work_order_audit_history_hides_integration_error_detail(ictx):
    c, w = ictx["client"], ictx["wo"]
    for role in ("viewer", "technician", "planner"):
        rows = c.get(f"/api/v1/audit/work_order/{w}", headers=H(ictx, role)).json()
        assert any(r["action"] == "integration.dead" for r in rows), role
        assert "SENTINELLOOP_CRED" not in json.dumps(rows), role
    rows = c.get(f"/api/v1/audit/work_order/{w}", headers=H(ictx, "admin")).json()          # audit.read: the full record
    assert "SENTINELLOOP_CRED_ODOO_PROD" in json.dumps(rows)


def test_models_list_hides_server_paths_from_non_admins(ctx):
    with ctx["db"].tx() as c:
        c.execute("INSERT INTO models (model_id, family, asset_type_id, scope_key, version, artifact_path, artifact_sha256, manifest_json, status, "
                  "registered_by, registered_at) VALUES (?,?,?,?,?,?,?,?,'candidate',?,?)",
                  ("m1", "x", "centrifugal_pump", "k", "1", r"C:\srv\models\m1", "0" * 64, json.dumps({"model_id": "m1"}), "ada", iso(now_ms())))
    for role in ("viewer", "technician", "planner", "reliability_engineer", "integration"):
        m = ctx["client"].get("/api/v1/models", headers=H(ctx, role)).json()[0]
        assert m["model_id"] == "m1" and "artifact_path" not in m and "srv" not in json.dumps(m), role
    assert ctx["client"].get("/api/v1/models", headers=H(ctx, "admin")).json()[0]["artifact_path"] == r"C:\srv\models\m1"


# -- api-security-console-11 (c): client input errors are 4xx, not 500 ---------------------------------------------------
@pytest.mark.parametrize("v", ["inf", "-inf", "nan", "-1", "0", "1e300"])
def test_staleness_rejects_impossible_ages(ctx, v):
    r = ctx["client"].get(f"/api/v1/ingest/staleness?max_age_h={v}", headers=H(ctx, "viewer"))
    assert r.status_code == 422, (v, r.status_code)


def test_staleness_still_reports_with_a_valid_age(ctx):
    r = ctx["client"].get("/api/v1/ingest/staleness?max_age_h=6", headers=H(ctx, "viewer"))
    assert r.status_code == 200 and {x["asset_id"] for x in r.json()} == {"P-101", "P-103"}


REC = {"asset": "P-101", "timestamp": "2026-10-17T10:00:00", "signal": "bearing_temp", "value": 60, "unit": "degC"}


@pytest.mark.parametrize("tz", ["Mars/Base", "../../etc/passwd", "Not A Zone", "/abs"])
def test_an_unknown_batch_time_zone_is_a_client_error(ctx, tz):
    r = ctx["client"].post("/api/v1/ingest/readings", json={"source": "x", "default_tz": tz, "records": [REC]}, headers=H(ctx, "integration"))
    assert r.status_code == 422 and "time zone" in r.json()["error"], (tz, r.status_code, r.text)
    r = ctx["client"].post(f"/api/v1/ingest/csv?source=x&default_tz={tz}", content=b"asset,timestamp,signal,value,unit\nP-101,2026-10-17T10:00:00,bearing_temp,60,degC\n",
                           headers=H(ctx, "integration"))
    assert r.status_code == 422, (tz, r.status_code, r.text)
    with ctx["db"].connect() as c:
        assert c.execute("SELECT COUNT(*) FROM readings").fetchone()[0] == 0


def test_the_library_raises_a_value_error_for_an_unknown_time_zone(ctx):
    with pytest.raises(ValueError, match="time zone"):
        ingest.ingest_records(ctx["db"], [REC], source="x", actor="svc", default_tz="Mars/Base")
    r = ingest.ingest_records(ctx["db"], [REC], source="x", actor="svc", default_tz="Asia/Kolkata")
    assert r.rows_accepted == 1


@pytest.mark.parametrize("units", ['"degC"', '["d"]', '{"d": 5}', "7", "null-ish", '{"d": ["degC"]}'])
def test_wide_units_must_be_an_object_of_unit_names(ctx, units):
    r = ctx["client"].post(f"/api/v1/ingest/csv?source=x&wide_units={units}", content=b"asset,timestamp,d\nP-101,2026-10-17T10:00:00Z,1\n",
                           headers=H(ctx, "integration"))
    assert r.status_code == 422, (units, r.status_code, r.text)


def test_wide_units_as_an_object_still_work(ctx):
    r = ctx["client"].post('/api/v1/ingest/csv?source=x&wide_units={"bearing_temp": "degC"}',
                           content=b"asset,timestamp,bearing_temp\nP-101,2026-10-17T10:00:00Z,61\n", headers=H(ctx, "integration"))
    assert r.status_code == 200 and r.json()["rows_accepted"] == 1


# -- repair pass: the verifier's residuals of api-security-console-1, -2, -7, -8 and the two regressions -----------------
def _rng(t0, steps):
    return {"start": iso(t0), "end": iso(t0 + (steps - 1) * 60_000), "step_minutes": 1}


async def _until(cond, timeout_s=30.0):
    end = time.monotonic() + timeout_s
    while not cond():
        assert time.monotonic() < end, "timed out"
        await asyncio.sleep(0.02)


def test_one_keys_assess_range_burst_leaves_other_users_responsive(tmp_path):
    """api-security-console-1: with the shipped limiter (120, 2/s) a burst of one-token ranges from one key, all inside its
    rate limit, held every worker thread (another user waited 73 s). Now the key's ranges run one at a time and the rest
    are refused with 429, so another user's request is answered promptly."""
    d, keys = _plant(tmp_path)
    app = api.create_app(d, POL)                                                       # shipped rate limit

    async def main():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t", timeout=600) as ac:
            h, t0 = {"Authorization": f"Bearer {keys['integration']}"}, now_ms() - 20 * HOUR_MS
            burst = [asyncio.create_task(ac.post("/api/v1/assets/P-101/assess-range", json=_rng(t0 + i * 10 * 60_000, 10), headers=h)) for i in range(60)]
            await asyncio.sleep(0.5)
            t = time.perf_counter()
            r = await ac.get("/api/v1/assets", headers={"Authorization": f"Bearer {keys['viewer']}"})
            waited = time.perf_counter() - t
            return r.status_code, waited, [x.status_code for x in await asyncio.gather(*burst)]
    status, waited, codes = asyncio.run(main())
    assert status == 200 and waited < 3.0, waited
    assert set(codes) <= {200, 429} and codes.count(429) >= 30, codes


def test_assess_range_runs_one_call_per_user_and_two_server_wide(tmp_path):
    """api-security-console-1: a second range from the same user is refused while the first runs; at most two ranges
    (api.RANGE_WORKERS) run at once on the server, so the other routes always keep worker threads. Refused ranges store
    nothing, and a refused user can run a range once the others have finished."""
    d, keys = _plant(tmp_path)
    for a in ("P-104", "P-105"):
        registry.create_asset(d, pump(a), actor="admin")
    app = api.create_app(d, POL, rate_limit=(100_000, 100_000.0))

    def h(role):
        return {"Authorization": f"Bearer {keys[role]}"}

    async def main():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t", timeout=600) as ac:
            url, t0 = "/api/v1/assets/{}/assess-range", now_ms() - 20 * HOUR_MS
            first = asyncio.create_task(ac.post(url.format("P-101"), json=_rng(t0, 80), headers=h("integration")))
            await _until(lambda: n_assessments(d, "P-101") > 0)
            again = await ac.post(url.format("P-103"), json=_rng(t0, 10), headers=h("integration"))
            other = asyncio.create_task(ac.post(url.format("P-104"), json=_rng(t0, 80), headers=h("admin")))
            await _until(lambda: n_assessments(d, "P-104") > 0)
            busy = await ac.post(url.format("P-105"), json=_rng(t0, 10), headers=h("planner"))
            viewer = await ac.get("/api/v1/assets", headers=h("viewer"))
            done = [await first, await other]
            later = await ac.post(url.format("P-105"), json=_rng(t0, 10), headers=h("planner"))
            return again, busy, viewer, done, later
    again, busy, viewer, done, later = asyncio.run(main())
    assert again.status_code == 429 and "still running" in again.json()["error"] and int(again.headers["Retry-After"]) >= 1, again.text
    assert busy.status_code == 429 and "already running" in busy.json()["error"] and int(busy.headers["Retry-After"]) >= 1, busy.text
    assert n_assessments(d, "P-103") == 0
    assert viewer.status_code == 200
    assert [r.status_code for r in done] == [200, 200] and [r.json()["assessments"] for r in done] == [80, 80]
    assert later.status_code == 200 and n_assessments(d, "P-105") == 10


class _Clock:
    """The rate limiter's clock, advanced by the test instead of by sleeping."""
    def __init__(self):
        self.t = 1000.0

    def monotonic(self):
        return self.t


def test_a_client_that_waits_the_retry_after_of_an_assess_range_429_is_served(tmp_path, monkeypatch):
    """Regression: the route's 429 gave Retry-After for its own share (cost - 1) only, but a retry pays the envelope's token
    again first, so a client that waited exactly Retry-After was refused again (every time at refill <= 1/s)."""
    clock = _Clock()
    monkeypatch.setattr(security, "time", clock)
    d, keys = _plant(tmp_path)
    c = TestClient(api.create_app(d, POL, rate_limit=(5, 1.0)), raise_server_exceptions=False)
    h, body = {"Authorization": f"Bearer {keys['integration']}"}, _rng(now_ms() - 10 * HOUR_MS, 30)  # 30 steps: 3 tokens
    assert c.post("/api/v1/assets/P-101/assess-range", json=body, headers=h).status_code == 200       # 2 tokens left
    r = c.post("/api/v1/assets/P-101/assess-range", json=body, headers=h)                            # 1 after the envelope's
    assert r.status_code == 429
    clock.t += int(r.headers["Retry-After"])
    r = c.post("/api/v1/assets/P-101/assess-range", json=body, headers=h)
    assert r.status_code == 200, (r.status_code, r.headers.get("Retry-After"))


def test_a_range_refused_by_validation_is_not_charged(tmp_path):
    """The route checks the whole range before it takes any of the bucket: a refused 40-step range costs only its request."""
    d, keys = _plant(tmp_path)
    c = TestClient(api.create_app(d, POL, rate_limit=(5, 0.0001)), raise_server_exceptions=False)
    h, t = {"Authorization": f"Bearer {keys['integration']}"}, now_ms()
    r = c.post("/api/v1/assets/P-101/assess-range", json=_rng(t - 30 * 60_000, 40), headers=h)        # ends 9 min ahead: future
    assert r.status_code == 422 and "future" in r.json()["error"]
    r = c.post("/api/v1/assets/P-101/assess-range", json=_rng(t - 10 * HOUR_MS, 40), headers=h)       # 4 tokens: 4 left before it
    assert r.status_code == 200, r.text


def _approved_orders(d, assets):
    for a in assets:
        if registry.get_asset(d, a) is None:
            registry.create_asset(d, pump(a), actor="admin")
        o = workorders.create(d, asset_id=a, job_type="inspect", priority_class="P2", title="t", origin="manual", actor="pat", role="planner",
                              idempotency_key=f"milp-{a}")
        for act in ("submit", "approve"):
            workorders.transition(d, o["wo_id"], act, actor="pat", role="planner")
    resources.upsert_technician(d, "T1", "Tech 1", "site1", ["mechanical"], actor="pat")


def n_schedule_runs(d):
    with d.connect() as c:
        return c.execute("SELECT COUNT(*) FROM schedule_runs").fetchone()[0]


def test_milp_is_refused_for_more_orders_times_slots_than_it_can_build_in_time(ctx):
    """api-security-console-7: building the MILP ignores time_limit_s and grows with orders x slots (squared); 150 approved
    orders at 1344 slots took 94.5 s. Four orders x 1344 slots is above the bound: 422 before any work, nothing stored."""
    d = ctx["db"]
    _approved_orders(d, ("P-101", "P-103", "P-104", "P-105"))
    r = ctx["client"].post("/api/v1/schedules", json={"site_id": "site1", "policy": "milp", "horizon_h": 336, "slot_h": 0.25}, headers=H(ctx, "planner"))
    assert r.status_code == 422 and "milp" in r.json()["error"] and "risk_greedy" in r.json()["error"], r.text
    assert n_schedule_runs(d) == 0


def test_small_milp_problems_and_the_greedy_policies_are_still_planned(ctx):
    d = ctx["db"]
    _approved_orders(d, ("P-101", "P-103", "P-104", "P-105"))
    c = ctx["client"]
    r = c.post("/api/v1/schedules", json={"site_id": "site1", "policy": "milp", "horizon_h": 72, "slot_h": 1}, headers=H(ctx, "planner"))
    assert r.status_code == 200 and r.json()["policy"] == "milp", r.text
    r = c.post("/api/v1/schedules", json={"site_id": "site1", "policy": "risk_greedy", "horizon_h": 336, "slot_h": 0.25}, headers=H(ctx, "planner"))
    assert r.status_code == 200, r.text


def _models(d):
    with d.tx() as c:
        for mid, status in (("m1", "candidate"), ("m0", "retired"), ("m2", "candidate")):
            c.execute("INSERT INTO models (model_id, family, asset_type_id, scope_key, version, artifact_path, artifact_sha256, manifest_json, status, "
                      "registered_by, registered_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                      (mid, "x", "centrifugal_pump", "k", "1", rf"C:\srv\secret-models\{mid}", "0" * 64, json.dumps({"model_id": mid}), status, "ada",
                       iso(now_ms())))


def test_model_decisions_and_rollbacks_hide_server_paths_from_non_admins(ctx):
    """api-security-console-8: POST /models/{id}/decision and /models/rollback returned artifact_path to reliability engineers."""
    _models(ctx["db"])
    c = ctx["client"]
    r = c.post("/api/v1/models/m1/decision", json={"decision": "approved", "reason": "ok"}, headers=H(ctx, "reliability_engineer"))
    assert r.status_code == 200 and r.json()["status"] == "approved" and "artifact_path" not in r.json() and "srv" not in r.text, r.text
    r = c.post("/api/v1/models/rollback", json={"asset_type_id": "centrifugal_pump", "to_model_id": "m0", "reason": "back"},
               headers=H(ctx, "reliability_engineer"))
    assert r.status_code == 200 and r.json()["model_id"] == "m0" and "artifact_path" not in r.json() and "srv" not in r.text, r.text
    r = c.post("/api/v1/models/m2/decision", json={"decision": "rejected", "reason": "no"}, headers=H(ctx, "admin"))
    assert r.status_code == 200 and r.json()["artifact_path"] == r"C:\srv\secret-models\m2"


def test_audit_readers_who_are_not_admins_do_not_see_integration_hosts_or_errors(ictx):
    """api-security-console-8: /integrations and /items withhold the host and the error text from reliability engineers, but
    the same role read both from the audit routes. One rule now: integration details reach admins only, everywhere."""
    c, w = ictx["client"], ictx["wo"]
    rows = c.get(f"/api/v1/audit/work_order/{w}", headers=H(ictx, "reliability_engineer")).json()
    dead = [r for r in rows if r["action"] == "integration.dead"]
    assert dead and dead[0]["payload"]["error"] == api.WITHHELD and "SENTINELLOOP_CRED" not in json.dumps(rows)
    rows = c.get("/api/v1/audit/integration_target/odoo", headers=H(ictx, "reliability_engineer")).json()
    reg = [r for r in rows if r["action"] == "integration.target_registered"]
    assert reg and reg[0]["payload"]["base_url"] == api.WITHHELD and "cmms.plant.example" not in json.dumps(rows)
    rows = c.get("/api/v1/audit/integration_target/odoo", headers=H(ictx, "admin")).json()           # admins: the full record
    assert [r["payload"]["base_url"] for r in rows if r["action"] == "integration.target_registered"] == ["https://cmms.plant.example"]


@pytest.mark.parametrize("seq", [2 ** 63, 10 ** 30])
def test_an_anchor_seq_beyond_the_database_integer_range_is_refused(ctx, seq):
    """api-security-console-2 (edge): a seq above SQLite's INTEGER range passed ge=1 and gave 500 (OverflowError)."""
    r = ctx["client"].get(f"/api/v1/audit/verify?anchor_seq={seq}&anchor_hash={'a' * 64}", headers=H(ctx, "admin"))
    assert r.status_code == 422, (r.status_code, r.text)


def test_the_largest_anchor_seq_is_checked_and_reported_missing(ctx):
    r = ctx["client"].get(f"/api/v1/audit/verify?anchor_seq={2 ** 63 - 1}&anchor_hash={'a' * 64}", headers=H(ctx, "admin"))
    assert r.status_code == 200 and r.json()["valid"] is False and r.json()["anchor_checked"] is True
