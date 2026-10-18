"""Operator console: API client behaviour and headless Streamlit runs (streamlit.testing.v1.AppTest) against the real API."""
import json
from datetime import date
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

from sentinelloop.app import api, db as dbmod, health, policy as policymod, registry, security, states, workorders
from sentinelloop.app.states import AssetState, Classification, HealthState as H, Thresholds
from sentinelloop.app.timeutil import iso, now_ms, parse_ts
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
    assert set(df["asset"]) == {"P-101", "P-102"} and all("Not assessed" in s for s in df["state"])


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
    at.button(key=f"complete-{wo}").click().run()                     # downtime not entered: refused, nothing made up
    assert any("downtime" in e.value for e in at.error) and workorders.get(d, wo)["state"] == "IN_PROGRESS"
    at.number_input(key=f"down-{wo}").set_value(0.5).run()
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


def test_deferred_work_is_listed_and_can_be_brought_back(env):
    d, w = env["db"], env["wo"]
    workorders.transition(d, w, "defer", actor="pat", role="planner", reason="crane booked", data={"until": "2026-12-01T06:00:00Z"})
    at = run_as(env, "planner", "Work queue")
    assert any("Deferred (1)" in e.label for e in at.expander)
    at.button(key=f"reactivate-{w}").click().run()
    assert workorders.get(d, w)["state"] == "PENDING_APPROVAL"


def test_a_technician_hands_a_job_back_with_a_reason(env):
    d, w = env["db"], env["wo"]
    workorders.transition(d, w, "approve", actor="pat", role="planner")
    workorders.transition(d, w, "schedule", actor="pat", role="planner", data={"start": "2026-10-19T08:00:00Z", "end": "2026-10-19T12:00:00Z",
                                                                              "technicians": ["T1"]})
    at = run_as(env, "technician", "Do the work")
    assert any("inspection recommended" in t.value.lower() for t in at.text)          # the job card says why
    at.button(key=f"handback-{w}").click().run()
    assert workorders.get(d, w)["state"] == "SCHEDULED"                              # no reason: refused
    at.text_input(key=f"hb-{w}").input("wind above climbing limit").run()
    at.button(key=f"handback-{w}").click().run()
    assert workorders.get(d, w)["state"] == "APPROVED"


def test_dismissal_is_offered_only_to_dismissers_and_only_when_something_is_latched(env):
    from sentinelloop.app import health, states
    from sentinelloop.app.states import AssetState, Classification, HealthState as H, Thresholds
    at = run_as(env, "planner", "Asset")
    assert not any("Dismiss" in e.label for e in at.expander)                        # nothing latched
    with env["db"].tx() as c:
        health._store_state(c, "P-101", states.advance(AssetState(), Classification(H.URGENT_REVIEW, []), Thresholds()), None)
    at = run_as(env, "planner", "Asset")
    assert any("Dismiss" in e.label for e in at.expander)
    at = run_as(env, "technician", "Asset")
    assert not any("Dismiss" in e.label for e in at.expander)


# -- re-review of the Phase 9 fixes (api-security-console-2, -3, -9, -10) ----------------------------------------------------
def _site(env, site_id, tz, asset_id):
    registry.create_site(env["db"], site_id, f"Plant {site_id}", tz, actor="admin")
    registry.create_asset(env["db"], pump(asset_id, site_id=site_id), actor="admin")


def _kolkata_order(env, state="IN_PROGRESS"):
    """An order for an asset at an Indian site (UTC+05:30): due 12:00 IST, scheduled 09:00-10:00 IST."""
    d = env["db"]
    _site(env, "site2", "Asia/Kolkata", "P-201")
    o = workorders.create(d, asset_id="P-201", job_type="inspect", priority_class="P2", title="Inspect P-201", origin="manual", actor="pat",
                          role="planner", idempotency_key="k-201", due_by="2026-10-19T06:30:00Z",
                          explanation={"why": "inspection recommended", "due_by": "2026-10-19T06:30:00Z", "p_fail_decision_horizon": None})
    w = o["wo_id"]
    workorders.transition(d, w, "submit", actor="pat", role="planner")
    if state in ("SCHEDULED", "IN_PROGRESS"):
        workorders.transition(d, w, "approve", actor="pat", role="planner")
        workorders.transition(d, w, "schedule", actor="pat", role="planner", data={"start": "2026-10-19T03:30:00Z", "end": "2026-10-19T04:30:00Z",
                                                                                  "technicians": ["T1"]})
    if state == "IN_PROGRESS":
        workorders.transition(d, w, "start", actor="tom", role="technician")
    return w


def test_job_cards_and_the_return_to_service_time_use_the_orders_site_time_zone(env):
    """api-security-console-3: 14:00 typed as local time at an IST site is 08:30 UTC, and the card shows IST times."""
    d, w = env["db"], _kolkata_order(env)
    at = run_as(env, "technician", "Do the work")
    card = next(m.value for m in at.markdown if w in m.value)
    assert "start 19 Oct 2026 09:00 IST" in card and "due 19 Oct 2026 12:00 IST" in card and "UTC" not in card
    assert any("Due by 19 Oct 2026 12:00 IST" in t.value for t in at.text)                     # the explanation's due date too
    assert "Asia/Kolkata" in at.text_input(key=f"rts-{w}").label                                 # the zone is named where the time is typed
    at.text_input(key=f"act-{w}").input("inspected, nothing found").run()
    at.number_input(key=f"down-{w}").set_value(1.0).run()
    at.selectbox(key=f"found-{w}").select("no_fault_found").run()
    at.text_input(key=f"rts-{w}").input("2026-10-19 14:00").run()
    at.button(key=f"complete-{w}").click().run()
    assert not at.exception, at.exception
    o = workorders.get(d, w)
    assert o["state"] == "COMPLETED" and parse_ts(o["outcome"]["returned_to_service_at"]) == parse_ts("2026-10-19T08:30:00Z")


def test_in_progress_work_in_the_queue_shows_its_sites_time(env):
    _kolkata_order(env)
    at = run_as(env, "planner", "Work queue")
    rows = [r for df in at.dataframe for r in df.value.to_dict("records") if r.get("asset") == "P-201"]
    assert rows and rows[0]["start"] == "19 Oct 2026 09:00 IST"


def test_the_work_queue_shows_and_enters_dates_in_each_orders_site_time(env):
    """Due dates are shown in the site's zone; a deferral comes back at 06:00 local time at the asset's site."""
    d, w = env["db"], _kolkata_order(env, state="PENDING_APPROVAL")
    at = run_as(env, "planner", "Work queue")
    card = next(m.value for m in at.markdown if w in m.value)
    assert "due 19 Oct 2026 12:00 IST" in card
    assert "Asia/Kolkata" in at.date_input(key=f"until-{w}").label
    at.text_input(key=f"reason-{w}").input("crane booked").run()
    at.date_input(key=f"until-{w}").set_value(date(2026, 12, 1)).run()
    at.button(key=f"defer-{w}").click().run()
    assert not at.exception, at.exception
    o = workorders.get(d, w)
    assert o["state"] == "DEFERRED" and o["deferred_until"] == "2026-12-01T00:30:00Z"           # 06:00 IST
    at = run_as(env, "planner", "Work queue")
    assert any("back on 01 Dec 2026 06:00 IST" in m.value for m in at.markdown)
    wutc = env["wo"]                                                                          # the UTC site's order is still shown in UTC
    workorders.transition(d, wutc, "defer", actor="pat", role="planner", reason="r", data={"until": "2026-12-01T06:00:00Z"})
    at = run_as(env, "planner", "Work queue")
    assert any("back on 01 Dec 2026 06:00 UTC" in m.value for m in at.markdown if wutc in m.value)


def test_an_unanchored_audit_verification_is_not_shown_as_valid(env):
    """api-security-console-2: without an anchor, deleting the newest events cannot be detected, so no green 'valid'."""
    security.create_user(env["db"], "rea", "Rea", "reliability_engineer", actor="bootstrap")
    env["keys"]["reliability_engineer"] = security.issue_api_key(env["db"], "rea", actor="bootstrap")
    at = run_as(env, "reliability_engineer", "Audit")
    at.button(key="aud_verify").click().run()
    assert not at.exception, at.exception
    assert not at.success
    assert any("not verified against an anchor" in w.value for w in at.warning)


def _odd_assessment(env, asset_id, as_of_ms):
    d = env["db"]
    with d.tx() as c:
        c.execute("INSERT INTO assessments (assessment_id, asset_id, as_of_ms, created_at, model_id, health_state, reasons_json, data_quality_json, "
                  "applicability_json, risk_json, top_deviations_json, inputs_json, policy_json, applied_to_state) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,1)",
                  (f"A-{asset_id}", asset_id, as_of_ms, iso(now_ms()), None, "DATA_QUALITY_FAILURE", json.dumps(["x"]), "{}", "{}", "{}",
                   json.dumps([["bearing_temp", 1.5]]), "{}", "{}"))
        s = states.advance(AssetState(), Classification(H.DATA_QUALITY_FAILURE, ["x"]), Thresholds())
        health._store_state(c, asset_id, states.replace(s, last_applied_as_of_ms=as_of_ms, last_applied_at_ms=now_ms()), f"A-{asset_id}")


@pytest.mark.parametrize("tz,as_of_ms,shown", [("UTC", -62135596800000, "for 01 Jan 0001 00:00 UTC:"),
                                               ("America/Chicago", -62135596800000, "for `-62135596800000`:"),
                                               ("Asia/Kolkata", 253402300799000, "for `253402300799000`:")])
def test_odd_assessment_instants_do_not_crash_the_asset_page(env, tz, as_of_ms, shown):
    """api-security-console-10: year-1 and year-9999 instants are shown as text; the page still renders to the end."""
    _site(env, "site9", tz, "P-901")
    _odd_assessment(env, "P-901", as_of_ms)
    at = AppTest.from_file(APP, default_timeout=60)
    c = client(env, "planner")
    at.session_state["client"], at.session_state["me"], at.session_state["page"], at.session_state["asset_pick"] = c, c.me(), "Asset", "P-901"
    at.run()
    assert not at.exception, at.exception
    latest = [m.value for m in at.markdown if m.value.startswith("**Latest assessment**")]
    assert latest and shown in latest[0] and "Data problem" in latest[0], latest       # a date, or the instant as escaped text
    assert at.button(key="assess_now") is not None                                           # rendered past the assessment section


def test_api_text_in_tables_is_plain_text_not_markdown(env):
    """api-security-console-9: st.table renders markdown in cells; unscheduled reasons and signal names use st.dataframe."""
    d, w = env["db"], env["wo"]
    _odd_assessment(env, "P-101", now_ms() - 60_000)
    at = AppTest.from_file(APP, default_timeout=60)
    c = client(env, "planner")
    at.session_state["client"], at.session_state["me"], at.session_state["page"], at.session_state["asset_pick"] = c, c.me(), "Asset", "P-101"
    at.run()
    assert not at.exception and len(at.table) == 0
    assert any("signal" in df.value.columns for df in at.dataframe)
    workorders.transition(d, w, "approve", actor="pat", role="planner")
    at = run_as(env, "planner", "Schedule")
    at.button(key="sched_plan").click().run()
    assert not at.exception and len(at.table) == 0
    reasons = [r for df in at.dataframe for r in df.value.to_dict("records") if r.get("wo") == w and r.get("reason")]
    assert reasons, [df.value for df in at.dataframe]


class _FlakyAssets:
    """The console's HTTP connection, with the first GET /assets refused (429, as under rate limiting); then the API answers."""
    def __init__(self, http):
        self.http, self.failed = http, False

    def request(self, method, url, **kw):
        if method == "GET" and url.endswith("/assets") and not self.failed:
            self.failed = True
            return httpx.Response(429, json={"error": "rate limit exceeded", "request_id": "r-1"}, headers={"Retry-After": "1"})
        return self.http.request(method, url, **kw)


def test_a_failed_asset_lookup_is_not_remembered_as_utc(env):
    """Regression: one failed GET /assets cached 'no site' for the asset until sign-out, so an IST site's order stayed in UTC."""
    d = env["db"]
    workorders.transition(d, env["wo"], "reject", actor="pat", role="planner", reason="duplicate")    # only the IST order is listed
    w = _kolkata_order(env, state="PENDING_APPROVAL")
    c = ConsoleClient(_FlakyAssets(env["http"]), env["keys"]["planner"], prefix="/api/v1")
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state["client"], at.session_state["me"], at.session_state["page"] = c, c.me(), "Work queue"
    at.run()
    assert not at.exception, at.exception
    assert "due 19 Oct 2026 06:30 UTC" in next(m.value for m in at.markdown if w in m.value)        # site unknown: UTC, labelled
    assert any("rate limit" in e.value for e in at.error)
    at.run()
    assert not at.exception, at.exception
    assert "due 19 Oct 2026 12:00 IST" in next(m.value for m in at.markdown if w in m.value)
    assert "Asia/Kolkata" in at.date_input(key=f"until-{w}").label
