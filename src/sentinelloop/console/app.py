"""SentinelLoop operator console (Streamlit). Run: streamlit run src/sentinelloop/console/app.py

Sign in with your own API key; every action goes through the REST API under your identity and role. The console
shows only actions your role may take, and the API enforces them again. Nothing here executes maintenance work.
"""
from __future__ import annotations

import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from sentinelloop.console.client import ApiError, ConsoleClient, explanation_lines  # noqa: E402

APPROVERS = {"planner", "reliability_engineer", "admin"}
PLANNERS = {"planner", "admin"}
DOERS = {"technician", "planner", "admin"}
ASSESSORS = {"integration", "admin", "reliability_engineer", "planner"}
DISMISSERS = {"reliability_engineer", "planner", "admin"}
AUDITORS = {"admin", "reliability_engineer"}
BADGE = {"URGENT_REVIEW": "🔴", "INSPECTION_RECOMMENDED": "🟠", "DATA_QUALITY_FAILURE": "🟣", "MODEL_UNAVAILABLE": "⚫", "MODEL_OUT_OF_SCOPE": "⚪",
         "NORMAL_MONITORING": "🟢", "NOT_ASSESSED": "▫️"}
PAGES = ["Fleet", "Asset", "Work queue", "Schedule", "Do the work", "Audit"]


def _today() -> date:
    return date.today()


def _utc(ms) -> str:
    return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC") if ms is not None else "n/a"


def flash(kind: str, msg: str):
    st.session_state.setdefault("flash", []).append((kind, msg))


def show_flash():
    for kind, msg in st.session_state.pop("flash", []):
        getattr(st, kind)(msg)


def call(fn, *a, ok: str | None = None, **kw):
    try:
        r = fn(*a, **kw)
        if ok:
            flash("success", ok)
        return r
    except ApiError as e:
        flash("error", f"{e.message} (HTTP {e.status}; request {e.request_id})")
        return None


def login():
    st.title("SentinelLoop console")
    st.caption("Advisory maintenance decisions. Sign in with your personal API key.")
    with st.form("login"):
        url = st.text_input("API URL", value=os.environ.get("SENTINELLOOP_API_URL", "http://127.0.0.1:8080/api/v1"), key="login_url")
        key = st.text_input("API key", type="password", key="login_key")
        if st.form_submit_button("Sign in"):
            try:
                c = ConsoleClient.connect(url, key)
                st.session_state["me"] = c.me()
                st.session_state["client"] = c
                st.rerun()
            except ApiError as e:
                st.error(f"Sign-in failed: {e.message}")
            except Exception as e:  # connection problems
                st.error(f"Cannot reach the API: {type(e).__name__}")


def page_fleet(c, me):
    st.header("Fleet")
    rows = call(c.assets) or []
    counts = {}
    for a in rows:
        counts[a["state"][0]] = counts.get(a["state"][0], 0) + 1
    cols = st.columns(max(1, len(counts)))
    for col, (s, n) in zip(cols, sorted(counts.items(), key=lambda kv: list(BADGE).index(kv[0]) if kv[0] in BADGE else 99)):
        col.metric(f"{BADGE.get(s, '')} {s.replace('_', ' ').title()}", n)
    st.dataframe([{"state": " ".join(BADGE.get(s, "") + s for s in a["state"]), "asset": a["asset_id"], "name": a["name"],
                   "criticality": a["criticality"], "site": a["site_id"]} for a in rows], width="stretch", hide_index=True)
    st.caption("States other than NORMAL MONITORING mean either a recommendation or that SentinelLoop cannot assess the asset "
               "(data, scope or model problem). Out-of-scope is never a statement that the asset is healthy.")
    if me["role"] in ASSESSORS and st.button("Generate recommendations from the latest assessments", key="generate"):
        r = call(c.generate)
        if r is not None:
            flash("success", f"{sum(1 for x in r if x.get('action') == 'created')} created, {sum(1 for x in r if x.get('action') == 'escalated')} escalated")
            st.rerun()


def page_asset(c, me):
    st.header("Asset")
    rows = call(c.assets) or []
    if not rows:
        st.info("No assets registered.")
        return
    aid = st.selectbox("Asset", [a["asset_id"] for a in rows], key="asset_pick")
    a = call(c.asset, aid)
    if not a:
        return
    st.subheader(" ".join(BADGE.get(s, "") + " " + s for s in a["state"]))
    for n in a.get("state_notes", []):
        st.write(f"• {n}")
    asm = call(c.assessment, aid)
    if asm:
        st.markdown(f"**Latest assessment** {asm['assessment_id']} for {_utc(asm['as_of_ms'])} (model {asm.get('model_id') or 'none'}): "
                    f"**{asm['health_state']}**")
        for r in asm.get("reasons", []):
            st.write(f"– {r}")
        if asm.get("rul_point_hours") is not None:
            st.write(f"Remaining life (hours): {asm['rul_lower_hours']:.0f} – {asm['rul_point_hours']:.0f} – {asm['rul_upper_hours']:.0f} "
                     f"({asm['interval_level']:.0%} interval)")
        else:
            st.caption("No remaining-life or failure-probability estimate for this assessment.")
        if asm.get("top_deviations"):
            st.write("Largest deviations from normal behaviour (in units of the inspection threshold):")
            st.table([{"signal": s, "deviation": v} for s, v in asm["top_deviations"]])
    else:
        st.caption("Not assessed yet.")
    if me["role"] in ASSESSORS and st.button("Assess now", key="assess_now"):
        if call(c.assess, aid, ok="assessed") is not None:
            st.rerun()
    if me["role"] in DISMISSERS | DOERS:
        with st.expander("Clear a latched warning"):
            ev = st.selectbox("Event", ["maintenance_completed"] + (["dismissed"] if me["role"] in DISMISSERS else []), key="clear_event")
            why = st.text_input("Written reason (required)", key="clear_reason")
            if st.button("Record", key="clear_go"):
                if not why.strip():
                    flash("error", "A written reason is required.")
                elif call(c.clear_risk, aid, ev, why, ok="recorded") is not None:
                    st.rerun()


def page_queue(c, me):
    st.header("Work queue: waiting for approval")
    pend = call(c.orders, ["PENDING_APPROVAL"]) or []
    if not pend:
        st.info("Nothing waits for approval.")
    for o in pend:
        with st.container(border=True):
            st.markdown(f"**{o['priority_class']} · {o['title']}** — {o['asset_id']} · {o['job_type']} · {o['duration_h']} h × {o['crew_size']} · "
                        f"due {o.get('due_by') or 'n/a'} · `{o['wo_id']}`")
            for line in explanation_lines(o):
                st.write(line)
            if me["role"] in APPROVERS:
                reason = st.text_input("Reason (required to defer or reject)", key=f"reason-{o['wo_id']}")
                until = st.date_input("If deferred, back for approval on", value=_today() + timedelta(days=7), key=f"until-{o['wo_id']}")
                b1, b2, b3 = st.columns(3)
                if b1.button("Approve", key=f"approve-{o['wo_id']}"):
                    if call(c.transition, o["wo_id"], "approve", o["version"], reason or None, ok=f"{o['wo_id']} approved") is not None:
                        st.rerun()
                for col, act in ((b2, "defer"), (b3, "reject")):
                    if col.button(act.title(), key=f"{act}-{o['wo_id']}"):
                        if not reason.strip():
                            flash("error", f"A written reason is required to {act}.")
                            st.rerun()
                        elif call(c.transition, o["wo_id"], act, o["version"], reason,
                                  data={"until": f"{until.isoformat()}T06:00:00Z"} if act == "defer" else None,
                                  ok=f"{o['wo_id']} {'deferred' if act == 'defer' else 'rejected'}") is not None:
                            st.rerun()
            else:
                st.caption("Your role cannot approve work.")
    with st.expander("Approved, scheduled and in progress"):
        st.dataframe([{"wo": o["wo_id"], "state": o["state"], "priority": o["priority_class"], "asset": o["asset_id"], "title": o["title"],
                       "start": o.get("scheduled_start"), "crew": ", ".join(o.get("assigned") or [])}
                      for o in (call(c.orders, ["APPROVED", "SCHEDULED", "IN_PROGRESS"]) or [])], width="stretch", hide_index=True)


def page_schedule(c, me):
    st.header("Schedule")
    if me["role"] not in PLANNERS:
        st.info("Only planners create and apply schedules.")
        return
    site = st.text_input("Site", key="sched_site")
    policy = st.selectbox("Policy", ["risk_greedy", "edd", "criticality_first", "milp"], key="sched_policy",
                          help="risk_greedy is the default (PD-09); milp is a what-if planner")
    horizon = st.number_input("Horizon (hours)", min_value=8.0, max_value=336.0, value=72.0, step=8.0, key="sched_h")
    if st.button("Propose a schedule (changes nothing)", key="sched_plan") and site:
        st.session_state["proposal"] = call(c.plan, site, policy, horizon)
    p = st.session_state.get("proposal")
    if p:
        st.markdown(f"Proposal `{p['run_id']}` · policy {p['policy']} · objective {p['objective']:.3f} · "
                    f"{len(p['assignments'])} assigned · {len(p['unscheduled'])} unscheduled · {len(p['violations'])} violations")
        st.dataframe([{"wo": a["wo_id"], "asset": a["asset_id"], "start": a["start"], "end": a["end"], "technicians": ", ".join(a["technicians"])}
                      for a in p["assignments"]], width="stretch", hide_index=True)
        if p["unscheduled"]:
            st.write("Could not be scheduled:")
            st.table([{"wo": k, "reason": v} for k, v in p["unscheduled"].items()])
        if p["violations"]:
            st.error("This proposal violates constraints and cannot be applied: " + "; ".join(p["violations"][:5]))
        elif st.button("Apply this schedule", key="sched_apply"):
            if call(c.apply, p["run_id"], ok="schedule applied") is not None:
                st.session_state.pop("proposal", None)
                st.rerun()


def page_work(c, me):
    st.header("Do the work")
    orders = call(c.orders, ["SCHEDULED", "IN_PROGRESS"]) or []
    if not orders:
        st.info("No scheduled or in-progress work.")
    for o in orders:
        with st.container(border=True):
            st.markdown(f"**{o['state']} · {o['title']}** — {o['asset_id']} · `{o['wo_id']}` · start {o.get('scheduled_start')}")
            if me["role"] not in DOERS:
                continue
            if o["state"] == "SCHEDULED" and st.button("Start", key=f"start-{o['wo_id']}"):
                if call(c.transition, o["wo_id"], "start", o["version"], ok="started") is not None:
                    st.rerun()
            if o["state"] == "IN_PROGRESS":
                found = st.selectbox("What was found", ["degradation_found", "failure_found", "no_fault_found", "not_inspected", "other"],
                                     key=f"found-{o['wo_id']}")
                confirmed = st.selectbox("Failure confirmed?", ["unknown", "yes", "no"], key=f"conf-{o['wo_id']}")
                cause = st.text_input("Root cause (if known)", key=f"cause-{o['wo_id']}")
                action = st.text_input("Actions taken (required)", key=f"act-{o['wo_id']}")
                down = st.number_input("Downtime (hours)", min_value=0.0, value=0.0, key=f"down-{o['wo_id']}")
                parts = st.text_input("Parts used (part=qty, comma-separated)", key=f"parts-{o['wo_id']}")
                notes = st.text_area("Notes", key=f"notes-{o['wo_id']}")
                if st.button("Complete with this outcome", key=f"complete-{o['wo_id']}"):
                    try:
                        used = {k.strip(): int(v) for k, v in (x.split("=") for x in parts.split(",") if x.strip())}
                    except ValueError:
                        used = None
                    if not action.strip():
                        flash("error", "Describe the actions taken.")
                        st.rerun()
                    elif used is None:
                        flash("error", "Parts must be written as part=qty, separated by commas.")
                        st.rerun()
                    else:
                        outcome = {"findings_code": found, "failure_confirmed": confirmed, "root_cause": cause, "actions_taken": action,
                                   "parts_used": used, "downtime_hours": down, "notes": notes}
                        if call(c.complete, o["wo_id"], outcome, o["version"], ok="completed") is not None:
                            st.rerun()
    miss = call(c.missing_outcomes) or []
    if miss:
        st.warning(f"{len(miss)} completed orders have no outcome recorded: " + ", ".join(m["wo_id"] for m in miss[:10]))


def page_audit(c, me):
    st.header("Audit")
    ent = st.selectbox("Entity", ["asset", "work_order", "assessment", "schedule_run", "model", "ingestion_batch"], key="aud_ent")
    eid = st.text_input("Id", key="aud_id")
    if eid and st.button("Show history", key="aud_go"):
        rows = call(c.audit, ent, eid) or []
        st.dataframe([{"seq": r.get("seq"), "time": r.get("ts"), "actor": r.get("actor"), "action": r.get("action")} for r in rows],
                     width="stretch", hide_index=True)
    if me["role"] in AUDITORS and st.button("Verify the audit chain", key="aud_verify"):
        v = call(c.verify_audit)
        if v:
            (st.success if v["valid"] else st.error)(f"valid: {v['valid']} · events: {v['n']} · first bad seq: {v.get('first_bad_seq')}")


def main():
    st.set_page_config(page_title="SentinelLoop console", layout="wide")
    c, me = st.session_state.get("client"), st.session_state.get("me")
    if c is None or me is None:
        login()
        return
    with st.sidebar:
        st.markdown(f"**{me['display_name']}** · {me['role']}")
        page = st.radio("Page", PAGES, key="page")
        if st.button("Sign out", key="logout"):
            for k in ("client", "me", "proposal"):
                st.session_state.pop(k, None)
            st.rerun()
        st.caption("Advisory only: recommendations become work only after a named person approves them.")
    show_flash()
    {"Fleet": page_fleet, "Asset": page_asset, "Work queue": page_queue, "Schedule": page_schedule, "Do the work": page_work,
     "Audit": page_audit}[page](c, me)
    show_flash()


main()
