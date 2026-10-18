"""Regression tests for the CMMS-connector findings of the Phase 9 re-review (cmms-integration-1, -2, -5, -6, -7, -8, -9),
written before the fixes.

The CMMS is the contract test double `FakeOdoo` from test_app_integration.py. The subclasses below change only what the
double answers (a lost response, a slow create, a sign-in page) or what happens while it answers (a second dispatcher,
an admin switching the mode); the connector itself runs unmodified against a temporary database.
"""
import json
import threading

import httpx
import pytest
from fastapi.testclient import TestClient

from sentinelloop.app import api, db as dbmod, integration, policy as policymod, registry, security, workorders
from sentinelloop.app.timeutil import HOUR_MS, now_ms, parse_ts
from conftest import ROOT
from test_app_foundation import KEY, pump, pump_type
from test_app_integration import API_KEY, ODOO, FakeOdoo, _approved_order

NOW = parse_ts("2026-10-18T00:00:00Z")
POL = policymod.load(ROOT / "configs" / "platform.yaml")
CREATE = "/maintenance.request/create"


@pytest.fixture
def d(tmp_path, monkeypatch):
    monkeypatch.setenv("SENTINELLOOP_INTEGRATION_HOSTS", "localhost,cmms.example.com")
    monkeypatch.setenv("SENTINELLOOP_CRED_ODOO_TEST", API_KEY)
    db = dbmod.Database(tmp_path / "i.db", audit_key=KEY, audit_key_id="test")
    db.migrate()
    registry.create_site(db, "site1", "Plant 1", "UTC", actor="admin")
    registry.create_asset_type(db, pump_type(), actor="admin")
    registry.create_asset(db, pump("P-101"), actor="admin")
    registry.update_asset(db, "P-101", {"config": {"cmms_equipment_ref": "P-101"}}, actor="admin", reason="CMMS equipment mapping")
    return db


def _target(d, mode="draft_requests", **cfg):
    kw = {"mode": mode, "reason": "test"} if mode != "shadow" else {}
    return integration.register_target(d, "odoo", "odoo_json2", ODOO, {"database": "sandbox", "api_key_env": "SENTINELLOOP_CRED_ODOO_TEST", **cfg},
                                       actor="ada", role="admin", **kw)


def _creates(fake):
    return [c for c in fake.calls if c[1] == "create"]


def _item(d, wo_id):
    return next(i for i in integration.items(d, "odoo") if i["wo_id"] == wo_id)


# -- cmms-integration-1: a create whose response is lost ----------------------------------------------------------------
class LosesCreateResponse(FakeOdoo):
    """Commits the first create, then its answer is lost: a read timeout, or a gateway's 504."""

    def __init__(self, how="timeout"):
        super().__init__()
        self.how, self.lost = how, False

    def __call__(self, request):
        resp = super().__call__(request)
        if request.url.path.endswith(CREATE) and not self.lost:
            self.lost = True
            if self.how == "timeout":
                raise httpx.ReadTimeout("response lost after the commit", request=request)
            return httpx.Response(self.how, json={"message": "gateway timeout"})
        return resp


@pytest.mark.parametrize("how", ["timeout", 504])
def test_a_lost_create_response_is_found_by_marker_and_not_created_again(d, how):
    f = LosesCreateResponse(how)
    tr = httpx.MockTransport(f)
    _target(d)
    w = _approved_order(d)
    integration.dispatch(d, "odoo", now_ms=NOW, transport=tr)
    it = _item(d, w["wo_id"])
    assert it["status"] == "retry" and it["external_id"] is None and list(f.requests) == [101]          # committed, answer lost
    integration.dispatch(d, "odoo", now_ms=it["next_attempt_ms"], transport=tr)
    it = _item(d, w["wo_id"])
    assert it["status"] == "synced" and it["external_id"] == "101"
    assert len(_creates(f)) == 1 and list(f.requests) == [101]                                          # no duplicate
    workorders.transition(d, w["wo_id"], "cancel", actor="pat", role="planner", reason="false alarm: sensor fault")
    integration.dispatch(d, "odoo", now_ms=NOW + 2 * HOUR_MS, transport=tr)
    assert f.requests[101]["name"].startswith("[SentinelLoop WITHDRAWN]") and f.requests[101]["priority"] == "0"   # the withdrawal reaches it


def test_a_record_planted_before_the_first_create_is_never_adopted_even_after_a_lost_response(d):
    f = LosesCreateResponse()
    tr = httpx.MockTransport(f)
    _target(d)
    f.requests[50] = {"id": 50, "name": "[SentinelLoop] planted", "description": f"<p>{integration.marker('WO-000001')}</p>", "priority": "0"}
    w = _approved_order(d)
    assert w["wo_id"] == "WO-000001"
    integration.dispatch(d, "odoo", now_ms=NOW, transport=tr)
    integration.dispatch(d, "odoo", now_ms=_item(d, w["wo_id"])["next_attempt_ms"], transport=tr)
    it = _item(d, w["wo_id"])
    assert it["status"] == "synced" and it["external_id"] == "101"
    assert f.requests[50]["name"] == "[SentinelLoop] planted" and sorted(f.requests) == [50, 101]


class RefusesFirstCreate(FakeOdoo):
    """The first create never reaches Odoo's database (503 before the commit)."""

    def __init__(self):
        super().__init__()
        self.refused = False

    def __call__(self, request):
        if request.url.path.endswith(CREATE) and not self.refused:
            self.refused = True
            self.calls.append(("maintenance.request", "create", json.loads(request.content)))
            return httpx.Response(503, json={"message": "service unavailable"})
        return super().__call__(request)


def test_a_planted_record_is_not_adopted_when_the_first_create_never_reached_the_cmms(d):
    f = RefusesFirstCreate()
    tr = httpx.MockTransport(f)
    _target(d)
    f.requests[50] = {"id": 50, "name": "[SentinelLoop] planted", "description": f"<p>{integration.marker('WO-000001')}</p>", "priority": "0"}
    w = _approved_order(d)
    integration.dispatch(d, "odoo", now_ms=NOW, transport=tr)
    integration.dispatch(d, "odoo", now_ms=_item(d, w["wo_id"])["next_attempt_ms"], transport=tr)
    it = _item(d, w["wo_id"])
    assert it["status"] == "synced" and it["external_id"] == "101" and f.requests[50]["name"] == "[SentinelLoop] planted"


def test_two_candidates_after_a_lost_create_make_a_dead_letter(d):
    f = LosesCreateResponse()
    tr = httpx.MockTransport(f)
    _target(d)
    w = _approved_order(d)
    integration.dispatch(d, "odoo", now_ms=NOW, transport=tr)
    f.requests[902] = {"id": 902, "name": "[SentinelLoop] copy", "description": f"<p>{integration.marker(w['wo_id'])}</p>"}
    integration.dispatch(d, "odoo", now_ms=_item(d, w["wo_id"])["next_attempt_ms"], transport=tr)
    it = _item(d, w["wo_id"])
    assert it["status"] == "dead" and "more than one" in it["last_error"] and "101" in it["last_error"] and "902" in it["last_error"]
    assert sorted(f.requests) == [101, 902]


# -- cmms-integration-2: overlapping dispatches -------------------------------------------------------------------------
class DispatchesDuringCreate(FakeOdoo):
    """While the first create is in flight, a second dispatcher runs (a cron run overlapping a manual POST /dispatch)."""

    def __init__(self, d):
        super().__init__()
        self.d, self.inner, self.transport = d, None, httpx.MockTransport(self)

    def __call__(self, request):
        if request.url.path.endswith(CREATE) and self.inner is None:
            self.inner = "running"
            self.inner = integration.dispatch(self.d, "odoo", now_ms=NOW, transport=self.transport)
        return super().__call__(request)


def test_a_dispatch_that_overlaps_a_running_one_reports_busy_and_sends_nothing(d):
    f = DispatchesDuringCreate(d)
    _target(d)
    w = _approved_order(d)
    outer = integration.dispatch(d, "odoo", now_ms=NOW, transport=f.transport)
    assert f.inner["busy"] is True and f.inner["sent"] == 0 and "already running" in f.inner["stopped"]
    assert outer["busy"] is False and outer["sent"] == 1
    assert len(_creates(f)) == 1 and list(f.requests) == [101] and _item(d, w["wo_id"])["external_id"] == "101"


class HoldsCreateOpen(FakeOdoo):
    """A slow CMMS: the first create waits until the test lets it finish, so the second dispatcher surely runs while it
    is in flight (no timing assumption)."""

    def __init__(self):
        super().__init__()
        self.in_create, self.release, self.lock = threading.Event(), threading.Event(), threading.Lock()

    def __call__(self, request):
        if request.url.path.endswith(CREATE):
            self.in_create.set()
            self.release.wait(10)
        with self.lock:
            return super().__call__(request)


def test_two_dispatcher_threads_create_one_request(d):
    f = HoldsCreateOpen()
    tr = httpx.MockTransport(f)
    _target(d)
    w = _approved_order(d)
    results = []

    def run():
        try:
            results.append(integration.dispatch(d, "odoo", now_ms=NOW, transport=tr))
        except Exception as e:                    # surfaced by the assertion below
            results.append(e)

    first = threading.Thread(target=run)
    first.start()
    assert f.in_create.wait(10)
    second = integration.dispatch(d, "odoo", now_ms=NOW, transport=tr)            # while the first is inside its create
    f.release.set()
    first.join(10)
    assert second["busy"] is True and second["sent"] == 0
    assert results[0]["busy"] is False and results[0]["sent"] == 1, results
    assert len(_creates(f)) == 1 and list(f.requests) == [101] and _item(d, w["wo_id"])["external_id"] == "101"


def test_a_held_lease_makes_dispatch_report_busy_until_it_is_released(d):
    f = FakeOdoo()
    tr = httpx.MockTransport(f)
    _target(d)
    _approved_order(d)
    assert integration._claim_lease(d, "odoo", "another-dispatcher")
    r = integration.dispatch(d, "odoo", now_ms=NOW, transport=tr)
    assert r["busy"] is True and r["sent"] == 0 and f.calls == [] and integration.items(d, "odoo") == []
    integration._release_lease(d, "odoo", "another-dispatcher")
    r = integration.dispatch(d, "odoo", now_ms=NOW, transport=tr)
    assert r["busy"] is False and r["sent"] == 1


def test_the_lease_of_a_crashed_dispatcher_expires(d):
    f = FakeOdoo()
    tr = httpx.MockTransport(f)
    _target(d)
    _approved_order(d)
    assert integration._claim_lease(d, "odoo", "crashed", wall_ms=now_ms() - integration.LEASE_MS - 1)   # taken long ago, never released
    r = integration.dispatch(d, "odoo", now_ms=NOW, transport=tr)
    assert r["busy"] is False and r["sent"] == 1 and len(f.requests) == 1


class HangsPastItsLease(FakeOdoo):
    """The dispatcher hangs in its first create for longer than its lease, and another dispatcher takes the lease over."""

    def __init__(self, d):
        super().__init__()
        self.d, self.hung = d, False

    def __call__(self, request):
        if request.url.path.endswith(CREATE) and not self.hung:
            self.hung = True
            assert integration._claim_lease(self.d, "odoo", "successor", wall_ms=now_ms() + integration.LEASE_MS + 1)
        return super().__call__(request)


def test_a_dispatcher_that_lost_its_lease_records_what_it_did_and_stops(d):
    f = HangsPastItsLease(d)
    tr = httpx.MockTransport(f)
    _target(d)
    a, b = _approved_order(d, key="a", title="first"), _approved_order(d, key="b", title="second")
    r = integration.dispatch(d, "odoo", now_ms=NOW, transport=tr)
    assert "lease" in r["stopped"] and len(_creates(f)) == 1                       # the second order is left to the successor
    first = next(i for i in integration.items(d, "odoo") if i["external_id"] == "101")
    assert first["synced_version"] is None                                         # recorded, and re-sent by the next run
    integration._release_lease(d, "odoo", "successor")
    integration.dispatch(d, "odoo", now_ms=NOW + 60_000, transport=tr)
    assert len(f.requests) == 2 and {_item(d, a["wo_id"])["status"], _item(d, b["wo_id"])["status"]} == {"synced"}


class SuccessorRunsDuringCreate(FakeOdoo):
    """The first create hangs past its lease; meanwhile a successor takes over, delivers the order and finishes. Then
    the hung create commits too: the CMMS now holds two requests for one order."""

    def __init__(self, d):
        super().__init__()
        self.d, self.successor, self.transport = d, None, httpx.MockTransport(self)

    def __call__(self, request):
        if request.url.path.endswith(CREATE) and self.successor is None:
            self.successor = "running"
            assert integration._claim_lease(self.d, "odoo", "expiry", wall_ms=now_ms() + integration.LEASE_MS + 1)
            integration._release_lease(self.d, "odoo", "expiry")                   # the hung dispatcher's lease has lapsed
            self.successor = integration.dispatch(self.d, "odoo", now_ms=NOW, transport=self.transport)
        return super().__call__(request)


def test_a_duplicate_made_by_a_dispatcher_that_lost_its_lease_is_a_dead_letter_not_an_orphan(d):
    f = SuccessorRunsDuringCreate(d)
    _target(d)
    w = _approved_order(d)
    r = integration.dispatch(d, "odoo", now_ms=NOW, transport=f.transport)
    assert f.successor["sent"] == 1 and sorted(f.requests) == [101, 102]
    it = _item(d, w["wo_id"])
    assert it["status"] == "dead" and it["external_id"] == "101" and "101" in it["last_error"] and "102" in it["last_error"]
    assert "lease" in r["stopped"]


# -- cmms-integration-5: a mode change during a run ------------------------------------------------------------------
class StopsDuringCreate(FakeOdoo):
    """An admin switches the target back to shadow ('STOP: wrong data') while the first create is in flight."""

    def __init__(self, d):
        super().__init__()
        self.d, self.switched = d, False

    def __call__(self, request):
        if request.url.path.endswith(CREATE) and not self.switched:
            self.switched = True
            integration.set_mode(self.d, "odoo", "shadow", actor="ada", role="admin", reason="STOP: wrong data")
        return super().__call__(request)


def test_switching_to_shadow_during_a_live_run_stops_it_before_the_next_call(d):
    f = StopsDuringCreate(d)
    tr = httpx.MockTransport(f)
    _target(d)
    for k in range(3):
        _approved_order(d, key=f"k{k}", title=f"order {k}")
    r = integration.dispatch(d, "odoo", now_ms=NOW, transport=tr)
    assert "mode" in r["stopped"] and len(_creates(f)) == 1
    n = len(f.calls)
    integration.dispatch(d, "odoo", now_ms=NOW + 60_000, transport=tr)            # shadow now: recorded, nothing sent
    assert len(f.calls) == n


def test_going_live_during_a_shadow_run_still_delivers_the_order(d, monkeypatch):
    f = FakeOdoo()
    tr = httpx.MockTransport(f)
    _target(d, mode="shadow")
    w = _approved_order(d)
    real, fired = registry.get_asset, []

    def get_asset(db, asset_id):                  # the admin goes live while the shadow run is between reading and writing
        if not fired:
            fired.append(True)
            integration.set_mode(db, "odoo", "draft_requests", actor="ada", role="admin", reason="go live")
        return real(db, asset_id)

    monkeypatch.setattr(registry, "get_asset", get_asset)
    integration.dispatch(d, "odoo", now_ms=NOW, transport=tr)
    monkeypatch.setattr(registry, "get_asset", real)
    r = integration.dispatch(d, "odoo", now_ms=NOW + 60_000, transport=tr)
    assert r["sent"] == 1 and list(f.requests) == [101] and _item(d, w["wo_id"])["status"] == "synced"


# -- cmms-integration-6: a mirrored (renamed) request after a lost mapping ---------------------------------------------
@pytest.mark.parametrize("plant", [False, True])
def test_a_mirrored_request_is_recovered_by_its_marker_and_a_second_candidate_is_a_dead_letter(d, plant):
    f = FakeOdoo()
    tr = httpx.MockTransport(f)
    _target(d)
    w = _approved_order(d)
    integration.dispatch(d, "odoo", now_ms=NOW, transport=tr)
    workorders.transition(d, w["wo_id"], "defer", actor="pat", role="planner", reason="crane booked", data={"until": "2026-11-01T06:00:00Z"})
    integration.dispatch(d, "odoo", now_ms=NOW + 60_000, transport=tr)
    assert f.requests[101]["name"].startswith("[SentinelLoop DEFERRED")
    if plant:
        f.requests[900] = {"id": 900, "name": "[SentinelLoop] Replace pump unit P-101 NOW", "priority": "3",
                           "description": f"<p>{integration.marker(w['wo_id'])}</p>"}
    integration._forget_external_id(d, "odoo", w["wo_id"])
    workorders.transition(d, w["wo_id"], "reactivate", actor="pat", role="planner", reason="crane free")
    workorders.transition(d, w["wo_id"], "approve", actor="pat", role="planner")
    integration.dispatch(d, "odoo", now_ms=NOW + 120_000, transport=tr)
    it = _item(d, w["wo_id"])
    if plant:
        assert it["status"] == "dead" and "more than one" in it["last_error"]
        assert f.requests[900]["name"] == "[SentinelLoop] Replace pump unit P-101 NOW"           # not adopted
    else:
        assert it["status"] == "synced" and it["external_id"] == "101" and list(f.requests) == [101]
        assert f.requests[101]["name"] == "[SentinelLoop] Inspect P-101"


# -- cmms-integration-7: an unexpected CMMS response ---------------------------------------------------------------------
class OddAnswerToCreate(FakeOdoo):
    """Odoo commits the create, but what comes back is not its JSON answer (a proxy's sign-in page, or another shape)."""

    def __init__(self, answer):
        super().__init__()
        self.answer = answer

    def __call__(self, request):
        resp = super().__call__(request)
        if request.url.path.endswith(CREATE):
            return self.answer()
        return resp


@pytest.mark.parametrize("answer", [lambda: httpx.Response(200, text="<html>Login</html>"), lambda: httpx.Response(200, json={"id": 5})],
                         ids=["html", "wrong-shape"])
def test_an_unexpected_answer_to_a_create_is_recorded_and_the_create_is_not_repeated(d, answer):
    f = OddAnswerToCreate(answer)
    tr = httpx.MockTransport(f)
    _target(d)
    a, b = _approved_order(d, key="a", title="first"), _approved_order(d, key="b", title="second")
    r = integration.dispatch(d, "odoo", now_ms=NOW, transport=tr)                  # no exception: each order gets a recorded outcome
    assert r["retry"] == 2 and all(_item(d, w["wo_id"])["last_error"] for w in (a, b))
    with d.connect() as c:
        assert c.execute("SELECT COUNT(*) FROM integration_log WHERE action = 'upsert' AND outcome = 'retry'").fetchone()[0] == 2
    for k in (1, 2):
        integration.dispatch(d, "odoo", now_ms=NOW + k * HOUR_MS, transport=tr)
    assert len(f.requests) == 2 and len(_creates(f)) == 2                           # one request per order, never repeated
    assert {_item(d, w["wo_id"])["status"] for w in (a, b)} == {"synced"}


class SignInPageEverywhere(FakeOdoo):
    def __call__(self, request):
        self.calls.append(tuple(request.url.path.split("/")[3:5]) + (None,))
        return httpx.Response(200, text="<html>Please sign in</html>")


def test_a_sign_in_page_instead_of_the_api_gives_recorded_dead_letters_not_a_crash(d):
    f = SignInPageEverywhere()
    _target(d)
    a, b = _approved_order(d, key="a", title="first"), _approved_order(d, key="b", title="second")
    r = integration.dispatch(d, "odoo", now_ms=NOW, transport=httpx.MockTransport(f))
    assert r["dead"] == 2 and f.requests == {}
    assert all("not JSON" in _item(d, w["wo_id"])["last_error"] for w in (a, b))


class BreaksOnFirstCreate(FakeOdoo):
    def __init__(self):
        super().__init__()
        self.broken = False

    def __call__(self, request):
        if request.url.path.endswith(CREATE) and not self.broken:
            self.broken = True
            raise RuntimeError("unexpected failure inside the HTTP stack")
        return super().__call__(request)


def test_an_unexpected_error_on_one_order_is_a_dead_letter_and_the_run_goes_on(d):
    f = BreaksOnFirstCreate()
    _target(d)
    a, b = _approved_order(d, key="a", title="first"), _approved_order(d, key="b", title="second")
    r = integration.dispatch(d, "odoo", now_ms=NOW, transport=httpx.MockTransport(f))
    assert r["dead"] == 1 and r["sent"] == 1
    dead = [i for i in integration.items(d, "odoo") if i["status"] == "dead"]
    assert len(dead) == 1 and "RuntimeError" in dead[0]["last_error"]


# -- cmms-integration-8: config values and URLs are validated when a target is registered ----------------------------
BAD_CONFIG = [{"max_attempts": None}, {"max_attempts": "eight"}, {"max_attempts": 0}, {"max_attempts": True}, {"max_attempts": 2.5},
              {"timeout_s": "15s"}, {"timeout_s": 0}, {"timeout_s": -1}, {"timeout_s": 1e9}, {"timeout_s": float("nan")}, {"timeout_s": None},
              {"database": 123}, {"database": "prod\r\nX-Injected: 1"}, {"database": ""}]
BAD_URLS = ["http://localhost:80a", "https://cmms.exam\nple.com", "http://localhost:8069:80", "http://localhost:99999", "http://localhost:0",
            "https://cmms.example.com\t", "https://cmms.example.com/a b", "http://@localhost:8069"]


@pytest.mark.parametrize("extra", BAD_CONFIG, ids=[repr(c) for c in BAD_CONFIG])
def test_bad_config_values_are_refused_at_registration(d, extra):
    with pytest.raises(integration.IntegrationError):
        _target(d, **extra)
    assert integration.get_target(d, "odoo") is None


@pytest.mark.parametrize("url", BAD_URLS, ids=[ascii(u) for u in BAD_URLS])
def test_bad_urls_are_refused_at_registration(d, url):
    with pytest.raises(integration.IntegrationError):
        integration.register_target(d, "o2", "odoo_json2", url, {"api_key_env": "SENTINELLOOP_CRED_ODOO_TEST"}, actor="ada", role="admin")


def test_good_config_values_and_urls_are_still_accepted(d):
    _target(d, max_attempts=3, timeout_s=2.5)
    integration.register_target(d, "o2", "odoo_json2", "https://cmms.example.com:8443/odoo", {"api_key_env": "SENTINELLOOP_CRED_X", "timeout_s": 120,
                                "database": "prod-db_1.eu"}, actor="ada", role="admin")


def test_through_the_api_a_bad_config_value_or_url_is_a_422(d):
    security.create_user(d, "ada", "ada", "admin", actor="b")
    c = TestClient(api.create_app(d, POL, rate_limit=(1000, 1000.0)))
    h = {"Authorization": f"Bearer {security.issue_api_key(d, 'ada', actor='b')}"}
    body = {"target_id": "odoo", "kind": "odoo_json2", "base_url": ODOO, "config": {"api_key_env": "SENTINELLOOP_CRED_ODOO_TEST"}}
    for change in ({"config": {**body["config"], "max_attempts": "eight"}}, {"config": {**body["config"], "timeout_s": "15s"}},
                   {"config": {**body["config"], "database": 123}}, {"base_url": "http://localhost:80a"}):
        r = c.post("/api/v1/integrations", json={**body, **change}, headers=h)
        assert r.status_code == 422, (change, r.status_code, r.text)
    assert c.post("/api/v1/integrations", json=body, headers=h).status_code == 201


def test_a_target_stored_with_a_bad_value_gives_dead_letters_not_a_crash(d):
    f = FakeOdoo()
    tr = httpx.MockTransport(f)
    _target(d, mode="shadow")
    with d.tx() as c:                             # a row written before values were validated
        c.execute("UPDATE integration_targets SET config_json = ? WHERE target_id = 'odoo'",
                  (json.dumps({"api_key_env": "SENTINELLOOP_CRED_ODOO_TEST", "max_attempts": None, "database": 123}),))
    w = _approved_order(d)
    assert integration.dispatch(d, "odoo", now_ms=NOW, transport=tr)["shadow"] == 1        # shadow never needs those values
    integration.set_mode(d, "odoo", "draft_requests", actor="ada", role="admin", reason="go live")
    r = integration.dispatch(d, "odoo", now_ms=NOW + 60_000, transport=tr)
    assert r["dead"] == 1 and f.calls == [] and "config" in _item(d, w["wo_id"])["last_error"]
    with d.tx() as c:
        c.execute("UPDATE integration_targets SET base_url = ?, config_json = ? WHERE target_id = 'odoo'",
                  ("https://cmms.exam\nple.com", json.dumps({"api_key_env": "SENTINELLOOP_CRED_ODOO_TEST"})))
    integration.requeue(d, "odoo", w["wo_id"], actor="ada", role="admin", reason="config fixed")
    r = integration.dispatch(d, "odoo", now_ms=NOW + 120_000, transport=tr)
    assert r["dead"] == 1 and f.calls == []


# -- cmms-integration-9: the reference webhook verifier rejects malformed headers --------------------------------------
SECRET, BODY, TS = b"s" * 32, b'{"event": "work_order.upsert"}', 1_760_000_000


@pytest.mark.parametrize("ts,sig", [("1760000000.0", None), ("abc", None), (None, None), ("", None), (" 1760000000", None), ("１７６０", None),
                                    (TS, "sha256=é"), (TS, b"sha256=00"), (TS, None)])
def test_verify_webhook_returns_false_for_malformed_headers(ts, sig):
    good = integration.sign_webhook(SECRET, TS, BODY)
    sig = good if sig is None and ts != TS else sig
    assert integration.verify_webhook(SECRET, ts, BODY, sig, now_s=TS + 10) is False


def test_verify_webhook_accepts_the_timestamp_header_as_text():
    good = integration.sign_webhook(SECRET, TS, BODY)
    assert integration.verify_webhook(SECRET, str(TS), BODY, good, now_s=TS + 10) is True
    assert integration.verify_webhook(SECRET, TS, BODY, good, now_s=TS + 10) is True


# -- repair pass: the variants a second verification found ---------------------------------------------------------------
class LapsesDuringCreate(FakeOdoo):
    """The first create hangs past its lease; meanwhile a successor takes over, delivers the order (101) and finishes.
    Then the hung create ends: Odoo commits it (102) and its answer is lost, or Odoo refuses it (400, nothing committed)."""

    def __init__(self, d, how):
        super().__init__()
        self.d, self.how, self.successor, self.transport = d, how, None, httpx.MockTransport(self)

    def __call__(self, request):
        if request.url.path.endswith(CREATE) and self.successor is None:
            self.successor = "running"
            assert integration._claim_lease(self.d, "odoo", "expiry", wall_ms=now_ms() + integration.LEASE_MS + 1)
            integration._release_lease(self.d, "odoo", "expiry")                   # the hung dispatcher's lease has lapsed
            self.successor = integration.dispatch(self.d, "odoo", now_ms=NOW, transport=self.transport)
            if self.how == "lost":
                super().__call__(request)
                raise httpx.ReadTimeout("answer lost after the commit", request=request)
            self.calls.append(("maintenance.request", "create", json.loads(request.content)))
            return httpx.Response(400, json={"message": "validation error"})
        return super().__call__(request)


def test_a_lapsed_dispatcher_whose_create_answer_was_lost_leaves_no_silent_orphan(d):
    f = LapsesDuringCreate(d, "lost")
    _target(d)
    w = _approved_order(d)
    r = integration.dispatch(d, "odoo", now_ms=NOW, transport=f.transport)
    assert f.successor["sent"] == 1 and sorted(f.requests) == [101, 102] and "lease" in r["stopped"]
    it = _item(d, w["wo_id"])
    assert it["status"] == "synced" and it["external_id"] == "101"                # the successor's result stands
    integration.dispatch(d, "odoo", now_ms=NOW + 60_000, transport=f.transport)    # the next run looks for a second request
    it = _item(d, w["wo_id"])
    assert it["status"] == "dead" and "101" in it["last_error"] and "102" in it["last_error"]
    workorders.transition(d, w["wo_id"], "cancel", actor="pat", role="planner", reason="false alarm: sensor fault")
    integration.requeue(d, "odoo", w["wo_id"], actor="ada", role="admin", reason="102 closed in the CMMS by hand")
    integration.dispatch(d, "odoo", now_ms=NOW + 2 * HOUR_MS, transport=f.transport)
    assert _item(d, w["wo_id"])["status"] == "synced" and f.requests[101]["name"].startswith("[SentinelLoop WITHDRAWN]")


def test_a_lapsed_dispatcher_whose_create_was_refused_does_not_overwrite_the_successors_delivery(d):
    f = LapsesDuringCreate(d, "refused")
    _target(d)
    w = _approved_order(d)
    integration.dispatch(d, "odoo", now_ms=NOW, transport=f.transport)
    it = _item(d, w["wo_id"])
    assert it["status"] == "synced" and it["external_id"] == "101" and sorted(f.requests) == [101]
    workorders.transition(d, w["wo_id"], "cancel", actor="pat", role="planner", reason="false alarm: sensor fault")
    integration.dispatch(d, "odoo", now_ms=NOW + 2 * HOUR_MS, transport=f.transport)
    assert f.requests[101]["name"].startswith("[SentinelLoop WITHDRAWN]") and f.requests[101]["priority"] == "0"
    assert _item(d, w["wo_id"])["status"] == "synced"


class CommitsLate(FakeOdoo):
    """The first create times out on the client while Odoo is still working on it. Odoo commits it only after the
    retry's marker search found nothing (a slow transaction)."""

    def __init__(self):
        super().__init__()
        self.pending = None

    def __call__(self, request):
        if request.url.path.endswith(CREATE):
            if self.pending is None:
                self.pending = request
                raise httpx.ReadTimeout("client timeout; Odoo still working", request=request)
            resp = super().__call__(request)
            late, self.pending = self.pending, False
            if late:
                super().__call__(late)
            return resp
        return super().__call__(request)


def test_a_create_that_commits_after_the_retrys_search_is_detected(d):
    f = CommitsLate()
    tr = httpx.MockTransport(f)
    _target(d)
    w = _approved_order(d)
    integration.dispatch(d, "odoo", now_ms=NOW, transport=tr)
    integration.dispatch(d, "odoo", now_ms=_item(d, w["wo_id"])["next_attempt_ms"], transport=tr)
    assert sorted(f.requests) == [101, 102] and _item(d, w["wo_id"])["external_id"] == "101"
    workorders.transition(d, w["wo_id"], "cancel", actor="pat", role="planner", reason="false alarm: sensor fault")
    integration.dispatch(d, "odoo", now_ms=NOW + 3 * HOUR_MS, transport=tr)
    it = _item(d, w["wo_id"])
    assert f.requests[101]["name"].startswith("[SentinelLoop WITHDRAWN]")         # SentinelLoop's own request is withdrawn
    assert it["status"] == "dead" and "102" in it["last_error"]                     # and the late one is reported, not left


def test_a_late_commit_is_detected_without_waiting_for_the_order_to_change(d):
    f = CommitsLate()
    tr = httpx.MockTransport(f)
    _target(d)
    w = _approved_order(d)
    integration.dispatch(d, "odoo", now_ms=NOW, transport=tr)
    integration.dispatch(d, "odoo", now_ms=_item(d, w["wo_id"])["next_attempt_ms"], transport=tr)
    integration.dispatch(d, "odoo", now_ms=NOW + 3 * HOUR_MS, transport=tr)
    it = _item(d, w["wo_id"])
    assert it["status"] == "dead" and "102" in it["last_error"]


def test_after_a_recovery_the_marker_is_searched_once_more_and_then_no_longer(d):
    f = LosesCreateResponse()
    tr = httpx.MockTransport(f)
    _target(d)
    w = _approved_order(d)
    integration.dispatch(d, "odoo", now_ms=NOW, transport=tr)
    integration.dispatch(d, "odoo", now_ms=_item(d, w["wo_id"])["next_attempt_ms"], transport=tr)

    def searches():
        return sum(1 for m, meth, _ in f.calls if (m, meth) == ("maintenance.request", "search_read"))

    n = searches()
    integration.dispatch(d, "odoo", now_ms=NOW + 3 * HOUR_MS, transport=tr)
    assert searches() == n + 1 and _item(d, w["wo_id"])["status"] == "synced" and list(f.requests) == [101]
    assert integration.dispatch(d, "odoo", now_ms=NOW + 6 * HOUR_MS, transport=tr)["considered"] == 0


OLD_VALUES = [{"timeout_s": 300}, {"timeout_s": "15"}, {"max_attempts": 8.0}, {"max_attempts": 500}]


@pytest.mark.parametrize("old", OLD_VALUES, ids=[repr(v) for v in OLD_VALUES])
def test_a_target_stored_with_values_the_previous_version_accepted_still_delivers(d, old):
    timeouts = []
    f = FakeOdoo()

    def handler(request):
        timeouts.append(request.extensions["timeout"]["read"])
        return f(request)

    _target(d)
    with d.tx() as c:                             # the row as the previous version stored it (registration checked keys only)
        c.execute("UPDATE integration_targets SET config_json = ? WHERE target_id = 'odoo'",
                  (json.dumps({"api_key_env": "SENTINELLOOP_CRED_ODOO_TEST", **old}),))
    w = _approved_order(d)
    r = integration.dispatch(d, "odoo", now_ms=NOW, transport=httpx.MockTransport(handler))
    assert r["sent"] == 1 and r["dead"] == 0 and list(f.requests) == [101] and _item(d, w["wo_id"])["status"] == "synced"
    assert max(timeouts) <= integration.MAX_TIMEOUT_S                               # 300 s is clamped: the lease relies on it


class RefusesFirstCreateDefinitely(FakeOdoo):
    """The first create certainly created nothing: Odoo refused it (400), or no connection was made."""

    def __init__(self, how):
        super().__init__()
        self.how, self.refused = how, False

    def __call__(self, request):
        if request.url.path.endswith(CREATE) and not self.refused:
            self.refused = True
            self.calls.append(("maintenance.request", "create", json.loads(request.content)))
            if self.how == "connect":
                raise httpx.ConnectError("connection refused", request=request)
            return httpx.Response(400, json={"message": "Invalid field value"})
        return super().__call__(request)


@pytest.mark.parametrize("how", [400, "connect"])
def test_a_record_planted_after_a_definitely_refused_create_is_not_adopted(d, how):
    f = RefusesFirstCreateDefinitely(how)
    tr = httpx.MockTransport(f)
    _target(d)
    w = _approved_order(d)
    integration.dispatch(d, "odoo", now_ms=NOW, transport=tr)
    assert _item(d, w["wo_id"])["status"] == ("dead" if how == 400 else "retry")
    f.requests[900] = {"id": 900, "name": "[SentinelLoop] planted", "priority": "3", "stage": "in progress (assigned to crew B)",
                       "description": f"<p>{integration.marker(w['wo_id'])}</p>"}
    if how == 400:
        integration.requeue(d, "odoo", w["wo_id"], actor="ada", role="admin", reason="field fixed")
    integration.dispatch(d, "odoo", now_ms=NOW + HOUR_MS, transport=tr)
    it = _item(d, w["wo_id"])
    assert it["status"] == "synced" and it["external_id"] == "101" and f.requests[900]["name"] == "[SentinelLoop] planted"


def test_a_webhook_dispatch_honours_the_lease_and_stops_on_a_mode_change(d, monkeypatch):
    monkeypatch.setenv("SENTINELLOOP_CRED_HOOK", "w" * 40)
    posts = []

    def handler(request):
        posts.append(json.loads(request.content)["wo_id"])
        if len(posts) == 1:                       # an admin stops the target while the first post is in flight
            integration.set_mode(d, "hook", "shadow", actor="ada", role="admin", reason="STOP: wrong data")
        return httpx.Response(204)

    tr = httpx.MockTransport(handler)
    integration.register_target(d, "hook", "webhook", "http://localhost:9000/hook", {"secret_env": "SENTINELLOOP_CRED_HOOK"}, actor="ada",
                                role="admin", mode="draft_requests", reason="test")
    for k in range(3):
        _approved_order(d, key=f"k{k}", title=f"order {k}")
    assert integration._claim_lease(d, "hook", "another-dispatcher")
    r = integration.dispatch(d, "hook", now_ms=NOW, transport=tr)
    assert r["busy"] is True and posts == []
    integration._release_lease(d, "hook", "another-dispatcher")
    r = integration.dispatch(d, "hook", now_ms=NOW, transport=tr)
    assert "mode" in r["stopped"] and len(posts) == 1
