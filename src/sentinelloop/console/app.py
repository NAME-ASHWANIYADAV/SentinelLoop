"""SentinelLoop operator console (Streamlit). Run from the repository root: streamlit run src/sentinelloop/console/app.py

Sign in with your own API key; every action goes through the REST API under your identity and role. The console
shows only actions your role may take, and the API enforces them again. Nothing here executes maintenance work.
Text that comes from the API (titles, reasons, notes) is escaped before display, so it cannot inject links or images.
"""
from __future__ import annotations

import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from sentinelloop.console.client import ApiError, ConsoleClient, explanation_lines, md  # noqa: E402

APPROVERS = {"planner", "reliability_engineer", "admin"}
PLANNERS = {"planner", "admin"}
DOERS = {"technician", "planner", "admin"}
ASSESSORS = {"integration", "admin", "reliability_engineer", "planner"}
DISMISSERS = {"reliability_engineer", "planner", "admin"}
AUDITORS = {"admin", "reliability_engineer"}
BADGE = {"URGENT_REVIEW": "🔴", "INSPECTION_RECOMMENDED": "🟠", "DATA_QUALITY_FAILURE": "🟣", "MODEL_UNAVAILABLE": "⚫", "MODEL_OUT_OF_SCOPE": "⚪",
         "AWAITING_ASSESSMENT": "🔵", "NOT_ASSESSED": "▫️", "NORMAL_MONITORING": "🟢", "ASSESSMENT_OVERDUE": "⏰", "INSPECTION_PENDING": "🟠",
         "HUMAN_APPROVAL_REQUIRED": "✋"}
PLAIN = {"URGENT_REVIEW": "Urgent review", "INSPECTION_RECOMMENDED": "Inspection recommended", "DATA_QUALITY_FAILURE": "Data problem (check instruments or feed)",
         "MODEL_UNAVAILABLE": "Model not available", "MODEL_OUT_OF_SCOPE": "Cannot assess (outside the model's scope)",
         "AWAITING_ASSESSMENT": "Awaiting re-assessment after work", "NOT_ASSESSED": "Not assessed", "NORMAL_MONITORING": "Normal monitoring",
         "ASSESSMENT_OVERDUE": "Assessment overdue", "INSPECTION_PENDING": "Inspection still pending", "HUMAN_APPROVAL_REQUIRED": "Waiting for approval"}
FINDINGS = {"degradation_found": "Degradation found", "failure_found": "Failure found", "no_fault_found": "Inspected: no fault found",
            "not_inspected": "Could not inspect", "other": "Other"}
PAGES = ["Fleet", "Asset", "Work queue", "Schedule", "Do the work", "Audit"]


def _today() -> date:
    return date.today()


def _tz(site_id: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(st.session_state.get("site_tz", {}).get(site_id) or "UTC")
    except Exception:
        return ZoneInfo("UTC")


def when(value, site_id: str | None = None) -> str:
    """ISO text or epoch milliseconds -> local time at the asset's site, with the zone shown."""
    if value in (None, ""):
        return "n/a"
    try:
        dt = (datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc) if isinstance(value, (int, float))
              else datetime.fromisoformat(str(value).replace("Z", "+00:00")))
    except ValueError:
        return md(value)
    z = _tz(site_id)
    return dt.astimezone(z).strftime("%d %b %Y %H:%M ") + (dt.astimezone(z).tzname() or str(z))


def labels(states_) -> str:
    return " · ".join(f"{BADGE.get(s, '')} {PLAIN.get(s, s.replace('_', ' ').title())}" for s in states_)


def flash(kind: str, msg: str):
    st.session_state.setdefault("flash", []).append((kind, msg))


def show_flash():
    for kind, msg in st.session_state.pop("flash", []):
        getattr(st, kind)(md(msg))


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
    st.caption("Advisory maintenance decisions. Not part of any safety function. Sign in with your personal API key.")
    url = os.environ.get("SENTINELLOOP_API_URL", "http://127.0.0.1:8080/api/v1")    # server configuration only, never user input
    st.caption(f"API: {url}")
    with st.form("login"):
        key = st.text_input("API key", type="password", key="login_key")
        if st.form_submit_button("Sign in"):
            try:
                c = ConsoleClient.connect(url, key)
                st.session_state["me"] = c.me()
                st.session_state["client"] = c
                st.rerun()
            except ApiError as e:
                st.error(f"Sign-in failed: {md(e.message)}")
            except Exception as e:  # connection problems
                st.error(f"Cannot reach the API: {type(e).__name__}")


def _context(c):
    """Site time zones, signal descriptions and model training data, cached for the session."""
    if "site_tz" not in st.session_state:
        st.session_state["site_tz"] = {s["site_id"]: s["timezone"] for s in (call(c.sites) or [])}
    if "signal_text" not in st.session_state:
        st.session_state["signal_text"] = {s["name"]: s.get("description") or s["name"] for t in (call(c.asset_types) or []) for s in t["signals"]}


def page_fleet(c, me):
    st.header("Fleet")
    rows = call(c.assets) or []
    counts = {}
    for a in rows:
        counts[a["state"][0]] = counts.get(a["state"][0], 0) + 1
    cols = st.columns(max(1, len(counts)))
    for col, (s, n) in zip(cols, sorted(counts.items(), key=lambda kv: list(BADGE).index(kv[0]) if kv[0] in BADGE else 99)):
        col.metric(f"{BADGE.get(s, '')} {PLAIN.get(s, s)}", n)
    st.dataframe([{"state": labels(a["state"]), "asset": a["asset_id"], "name": a["name"], "criticality": a["criticality"], "site": a["site_id"],
                   "last assessed": when(a.get("last_assessed_at"), a["site_id"])} for a in rows], width="stretch", hide_index=True)
    st.caption("Anything other than Normal monitoring is either a recommendation or a reason SentinelLoop cannot assess the asset. "
               "'Cannot assess' is never a statement that the asset is healthy. Assessment overdue means the assessment job has stopped.")
    if me["role"] in ASSESSORS and st.button("Generate recommendations from the latest assessments", key="generate"):
        r = call(c.generate)
        if r is not None:
            n = {k: sum(1 for x in r if x.get("action") == k) for k in ("created", "escalated", "reactivated", "suppressed")}
            flash("success", f"{n['created']} created, {n['escalated']} escalated, {n['reactivated']} back from deferral, "
                             f"{n['suppressed']} held back by an earlier rejection")
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
    site = a["site_id"]
    st.subheader(labels(a["state"]))
    st.caption(f"Last assessed {when(a.get('last_assessed_at'), site)} (assessment instant {when(a.get('last_assessment_instant'), site)})")
    for n in a.get("state_notes", []):
        st.text(f"• {n}")
    asm = call(c.assessment, aid)
    if asm:
        model = next((m for m in (call(c.models) or []) if m["model_id"] == asm.get("model_id")), None)
        st.markdown(f"**Latest assessment** for {when(asm['as_of_ms'], site)}: **{md(PLAIN.get(asm['health_state'], asm['health_state']))}**")
        if model:
            tr = (model.get("manifest") or {}).get("trained_on") or {}
            st.caption(f"Model {md(model['model_id'])}, trained on {md(tr.get('data_class', 'unknown data'))} data "
                       f"({md(tr.get('source', ''))}). Not field-validated: see the validation ladder.")
        for r in asm.get("reasons", []):
            st.text(f"– {r}")
        if asm.get("rul_point_hours") is not None:
            st.write(f"Remaining life (hours): {asm['rul_lower_hours']:.0f} – {asm['rul_point_hours']:.0f} – {asm['rul_upper_hours']:.0f} "
                     f"({asm['interval_level']:.0%} interval; model-implied, coverage is lower near end of life)")
        else:
            st.caption("No remaining-life or failure-probability estimate for this assessment.")
        if asm.get("top_deviations"):
            st.write("Largest deviations from normal behaviour, in multiples of the inspection threshold (1.0 = threshold):")
            st.table([{"signal": st.session_state.get("signal_text", {}).get(s, s), "times the threshold": round(v, 2)} for s, v in asm["top_deviations"]])
    else:
        st.caption("Not assessed yet.")
    if me["role"] in ASSESSORS and st.button("Assess now", key="assess_now"):
        if call(c.assess, aid, ok="assessed") is not None:
            st.rerun()
    latched = any(s in ("URGENT_REVIEW", "INSPECTION_RECOMMENDED", "INSPECTION_PENDING") for s in a["state"])
    if me["role"] in DISMISSERS and latched:
        with st.expander("Dismiss a latched warning (no work done)"):
            st.caption("Completed maintenance clears a warning automatically when its work order is completed with an inspection outcome. "
                       "Use this only when the warning is judged wrong, and say why.")
            why = st.text_input("Written reason (required)", key="clear_reason")
            if st.button("Dismiss", key="clear_go"):
                if not why.strip():
                    flash("error", "A written reason is required.")
                elif call(c.clear_risk, aid, "dismissed", why, ok="dismissed") is not None:
                    st.rerun()


def _waiting(o) -> str:
    try:
        h = (datetime.now(timezone.utc) - datetime.fromisoformat(o["created_at"].replace("Z", "+00:00"))).total_seconds() / 3600
        return f"waiting {h:.0f} h" if h < 72 else f"waiting {h / 24:.1f} days"
    except Exception:
        return ""


def page_queue(c, me):
    st.header("Work queue")
    pend = call(c.orders, ["PENDING_APPROVAL"]) or []
    st.subheader("Waiting for approval")
    if not pend:
        st.info("Nothing waits for approval.")
    for o in sorted(pend, key=lambda x: (x["priority_class"], x["created_at"])):
        with st.container(border=True):
            st.markdown(f"**{o['priority_class']} · {md(o['title'])}** — {md(o['asset_id'])} · {md(o['job_type'])} · {o['duration_h']} h × {o['crew_size']} · "
                        f"due {when(o.get('due_by'), None)} · {_waiting(o)} · `{md(o['wo_id'])}`")
            for line in explanation_lines(o):
                st.text(line)
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
    deferred = call(c.orders, ["DEFERRED"]) or []
    with st.expander(f"Deferred ({len(deferred)}): they come back for approval on their date"):
        for o in sorted(deferred, key=lambda x: x.get("deferred_until") or ""):
            st.markdown(f"**{o['priority_class']} · {md(o['title'])}** — back on {when(o.get('deferred_until'), None)} · `{md(o['wo_id'])}`")
            if me["role"] in APPROVERS and st.button("Bring back now", key=f"reactivate-{o['wo_id']}"):
                if call(c.transition, o["wo_id"], "reactivate", o["version"], "brought back early by a planner", ok="back for approval") is not None:
                    st.rerun()
    with st.expander("Approved, scheduled and in progress"):
        st.dataframe([{"wo": o["wo_id"], "state": o["state"], "priority": o["priority_class"], "asset": o["asset_id"], "title": o["title"],
                       "start": when(o.get("scheduled_start"), None), "crew": ", ".join(o.get("assigned") or [])}
                      for o in (call(c.orders, ["APPROVED", "SCHEDULED", "IN_PROGRESS"]) or [])], width="stretch", hide_index=True)
    review = [o for o in (call(c.orders, ["COMPLETED"]) or []) if (o.get("outcome") or {}).get("flags")]
    if review and me["role"] in APPROVERS:
        with st.expander(f"Completed orders whose outcome needs review ({len(review)})"):
            for o in review:
                st.text(f"{o['wo_id']} {o['asset_id']}: {', '.join(o['outcome']['flags'])}")


def page_schedule(c, me):
    st.header("Schedule")
    if me["role"] not in PLANNERS:
        st.info("Only planners create and apply schedules.")
        return
    sites = list((st.session_state.get("site_tz") or {}).keys())
    site = st.selectbox("Site", sites, key="sched_site") if sites else st.text_input("Site", key="sched_site")
    policy = st.selectbox("Policy", ["risk_greedy", "edd", "criticality_first", "milp"], key="sched_policy",
                          help="risk_greedy ranks by priority, then evidence; milp is a what-if planner. Weather and climbing limits are "
                               "not modelled: enter weather windows as maintenance windows.")
    horizon = st.number_input("Horizon (hours)", min_value=8.0, max_value=336.0, value=72.0, step=8.0, key="sched_h")
    if st.button("Propose a schedule (changes nothing)", key="sched_plan") and site:
        st.session_state["proposal"] = call(c.plan, site, policy, horizon)
    p = st.session_state.get("proposal")
    if p:
        st.markdown(f"Proposal `{md(p['run_id'])}` · policy {md(p['policy'])} · {len(p['assignments'])} assigned · "
                    f"{len(p['unscheduled'])} unscheduled · {len(p['violations'])} violations")
        st.dataframe([{"wo": a["wo_id"], "asset": a["asset_id"], "start": when(a["start"], p.get("site_id")), "end": when(a["end"], p.get("site_id")),
                       "technicians": ", ".join(a["technicians"])} for a in p["assignments"]], width="stretch", hide_index=True)
        if p["unscheduled"]:
            st.write("Could not be scheduled:")
            st.table([{"wo": k, "reason": v} for k, v in p["unscheduled"].items()])
        if p["violations"]:
            st.error("This proposal violates constraints and cannot be applied: " + md("; ".join(p["violations"][:5])))
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
            st.markdown(f"**{md(o['state'].title().replace('_', ' '))} · {md(o['title'])}** — {md(o['asset_id'])} · `{md(o['wo_id'])}` · "
                        f"start {when(o.get('scheduled_start'), None)} · due {when(o.get('due_by'), None)}")
            st.caption(f"Job: {md(o['job_type'])} · {o['duration_h']} h · crew {o['crew_size']} ({md(o['required_skill'])}) · parts: "
                       + (md(", ".join(f"{k} × {v}" for k, v in (o.get("parts") or {}).items())) or "none planned")
                       + f" · assigned: {md(', '.join(o.get('assigned') or []) or 'nobody')}")
            for line in explanation_lines(o):
                st.text(line)
            if me["role"] not in DOERS:
                continue
            hb = st.text_input("If you cannot do this job: why (weather, access, crew)?", key=f"hb-{o['wo_id']}")
            b1, b2 = st.columns(2)
            if o["state"] == "SCHEDULED" and b1.button("Start", key=f"start-{o['wo_id']}"):
                if call(c.transition, o["wo_id"], "start", o["version"], ok="started") is not None:
                    st.rerun()
            if b2.button("Hand back to the planner", key=f"handback-{o['wo_id']}"):
                if not hb.strip():
                    flash("error", "Say why the job cannot be done.")
                    st.rerun()
                elif call(c.transition, o["wo_id"], "hand_back", o["version"], hb, ok="handed back") is not None:
                    st.rerun()
            if o["state"] == "IN_PROGRESS":
                found = st.selectbox("What was found", list(FINDINGS), format_func=FINDINGS.get, key=f"found-{o['wo_id']}")
                confirmed = st.selectbox("Failure confirmed?", ["unknown", "yes", "no"], key=f"conf-{o['wo_id']}")
                cause = st.text_input("Root cause (if known)", key=f"cause-{o['wo_id']}")
                action = st.text_input("Actions taken (required)", key=f"act-{o['wo_id']}")
                down = st.number_input("Downtime caused by this job (hours, required)", min_value=0.0, value=None, key=f"down-{o['wo_id']}")
                back = st.text_input("Returned to service at (local time, YYYY-MM-DD HH:MM; leave empty if still down)", key=f"rts-{o['wo_id']}")
                parts = st.text_input("Parts used (part=qty, comma-separated)", key=f"parts-{o['wo_id']}")
                notes = st.text_area("Notes", key=f"notes-{o['wo_id']}")
                if found == "not_inspected":
                    st.caption("Could not inspect: the warning stays active and the order is recorded as done without an inspection. "
                               "If the job should be redone, hand it back instead.")
                if st.button("Complete with this outcome", key=f"complete-{o['wo_id']}"):
                    try:
                        used = {k.strip(): int(v) for k, v in (x.split("=") for x in parts.split(",") if x.strip())}
                    except ValueError:
                        used = None
                    rts = None
                    if back.strip():
                        try:
                            rts = datetime.strptime(back.strip(), "%Y-%m-%d %H:%M").replace(tzinfo=_tz(None)).astimezone(timezone.utc).isoformat()
                        except ValueError:
                            rts = "bad"
                    if not action.strip():
                        flash("error", "Describe the actions taken.")
                        st.rerun()
                    elif down is None:
                        flash("error", "Enter the downtime caused by the job (0 if none).")
                        st.rerun()
                    elif used is None:
                        flash("error", "Parts must be written as part=qty, separated by commas.")
                        st.rerun()
                    elif rts == "bad":
                        flash("error", "Return to service must be written as YYYY-MM-DD HH:MM.")
                        st.rerun()
                    else:
                        outcome = {"findings_code": found, "failure_confirmed": confirmed, "root_cause": cause, "actions_taken": action,
                                   "parts_used": used, "downtime_hours": float(down), "returned_to_service_at": rts, "notes": notes}
                        r = call(c.complete, o["wo_id"], outcome, o["version"], ok="completed")
                        if r is not None:
                            fl = (r.get("outcome") or {}).get("flags") or []
                            if fl:
                                flash("warning", "Recorded with flags for review: " + ", ".join(fl))
                            st.rerun()
    miss = call(c.missing_outcomes) or []
    if miss:
        st.warning(f"{len(miss)} completed orders have no outcome recorded: " + md(", ".join(m["wo_id"] for m in miss[:10])))


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
    _context(c)
    with st.sidebar:
        st.markdown(f"**{md(me['display_name'])}** · {md(me['role'])}")
        page = st.radio("Page", PAGES, key="page")
        if st.button("Sign out", key="logout"):
            for k in ("client", "me", "proposal", "site_tz", "signal_text"):
                st.session_state.pop(k, None)
            st.rerun()
        st.caption("Advisory only: recommendations become work only after a named person approves them. Not part of any safety function.")
    show_flash()
    {"Fleet": page_fleet, "Asset": page_asset, "Work queue": page_queue, "Schedule": page_schedule, "Do the work": page_work,
     "Audit": page_audit}[page](c, me)
    show_flash()


main()
