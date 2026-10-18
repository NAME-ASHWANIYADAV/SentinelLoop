"""Operator console: API client behaviour and headless Streamlit runs (streamlit.testing.v1.AppTest) against the real API."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

from sentinelloop.app import api, db as dbmod, policy as policymod, registry, security, workorders
from sentinelloop.console.client import ApiError, ConsoleClient, explanation_lines
from conftest import ROOT
from test_app_foundation import KEY, pump, pump_type

APP = str(Path(ROOT) / "src" / "sentinelloop" / "console" / "app.py")


@pytest.fixture
def env(tmp_path):
    d = dbmod.Database(tmp_path / "c.db", audit_key=KEY, audit_key_id="test")
    d.migrate()
    registry.create_site(d, "site1", "Plant 1", "UTC", actor="admin")
    registry.create_asset_type(d, pump_type(), actor="admin")
    for t in ("P-101", "P-102"):
        registry.create_asset(d, pump(t), actor="admin")
    keys = {}
    for uid, role in (("pat", "planner"), ("vic", "viewer"), ("tom", "technician")):
        security.create_user(d, uid, uid.title(), role, actor="bootstrap")
        keys[role] = security.issue_api_key(d, uid, actor="bootstrap")
    http = TestClient(api.create_app(d, policymod.load(ROOT / "configs" / "platform.yaml"), rate_limit=(10000, 1000.0)))
    o = workorders.create(d, asset_id="P-101", job_type="inspect", priority_class="P2", title="Inspect P-101", origin="system", actor="sys",
                          role="system", idempotency_key="c-1", explanation={"why": "inspection recommended by the assessment", "p_fail_decision_horizon": None})
    workorders.transition(d, o["wo_id"], "submit", actor="sys", role="system")
    return {"db": d, "http": http, "keys": keys, "wo": o["wo_id"]}


def client(env, role):
    return ConsoleClient(env["http"], env["keys"][role], prefix="/api/v1")


def run_as(env, role, page=None):
    at = AppTest.from_file(APP, default_timeout=60)
    c = client(env, role)
    at.session_state["client"] = c
    at.session_state["me"] = c.me()
    if page:
        at.session_state["page"] = page
    at.run()
    assert not at.exception, at.exception
    return at


def test_client_raises_api_errors_with_message_and_request_id(env):
    with pytest.raises(ApiError) as e:
        client(env, "viewer").transition(env["wo"], "approve")
    assert e.value.status == 403 and "may not" in e.value.message and e.value.request_id


def test_explanation_never_invents_a_probability():
    lines = explanation_lines({"explanation": {"why": "x", "p_fail_decision_horizon": None}})
    assert any("No failure probability" in l for l in lines) and not any("P(failure" in l for l in lines)


def test_signed_out_console_shows_only_the_login_form(env):
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    assert not at.exception
    assert at.text_input(key="login_key") is not None and len(at.radio) == 0


def test_fleet_page_lists_every_asset_with_its_state(env):
    at = run_as(env, "viewer", "Fleet")
    df = at.dataframe[0].value
    assert set(df["asset"]) == {"P-101", "P-102"} and all("NOT_ASSESSED" in s for s in df["state"])


def test_planner_approves_from_the_work_queue(env):
    at = run_as(env, "planner", "Work queue")
    at.button(key=f"approve-{env['wo']}").click().run()
    assert not at.exception
    assert workorders.get(env["db"], env["wo"])["state"] == "APPROVED"


def test_defer_without_a_reason_is_refused_in_the_console(env):
    at = run_as(env, "planner", "Work queue")
    at.button(key=f"defer-{env['wo']}").click().run()
    assert any("reason is required" in e.value for e in at.error)
    assert workorders.get(env["db"], env["wo"])["state"] == "PENDING_APPROVAL"
    at.text_input(key=f"reason-{env['wo']}").input("waiting for the crane").run()
    at.button(key=f"defer-{env['wo']}").click().run()
    assert workorders.get(env["db"], env["wo"])["state"] == "DEFERRED"


def test_viewers_see_no_approval_buttons(env):
    at = run_as(env, "viewer", "Work queue")
    keys = {b.key for b in at.button}
    assert f"approve-{env['wo']}" not in keys and any("cannot approve" in c.value for c in at.caption)


def test_technician_records_an_outcome(env):
    d, wo = env["db"], env["wo"]
    workorders.transition(d, wo, "approve", actor="pat", role="planner")
    workorders.transition(d, wo, "schedule", actor="pat", role="planner", data={"start": "2026-10-19T08:00:00Z", "end": "2026-10-19T12:00:00Z",
                                                                               "technicians": ["T1"]})
    at = run_as(env, "technician", "Do the work")
    at.button(key=f"start-{wo}").click().run()
    assert workorders.get(d, wo)["state"] == "IN_PROGRESS"
    at.button(key=f"complete-{wo}").click().run()                     # no actions described: refused
    assert any("actions taken" in e.value for e in at.error) and workorders.get(d, wo)["state"] == "IN_PROGRESS"
    at.text_input(key=f"act-{wo}").input("inspected bearing; regreased").run()
    at.selectbox(key=f"found-{wo}").select("degradation_found").run()
    at.button(key=f"complete-{wo}").click().run()
    o = workorders.get(d, wo)
    assert o["state"] == "COMPLETED" and o["outcome"]["findings_code"] == "degradation_found"


def test_the_api_url_is_server_configuration_not_a_login_field(env):
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    assert [t.key for t in at.text_input] == ["login_key"]          # no URL field: the console cannot be pointed elsewhere


def test_non_json_upstream_errors_are_not_echoed():
    import httpx

    def handler(request):
        return httpx.Response(502, text="<html>internal proxy page with secrets</html>")
    c = ConsoleClient(httpx.Client(base_url="http://api.local", transport=httpx.MockTransport(handler)), "slk_x", prefix="/api/v1")
    with pytest.raises(ApiError) as e:
        c.me()
    assert e.value.status == 502 and "secrets" not in e.value.message
