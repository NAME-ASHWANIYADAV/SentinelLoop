"""SentinelLoop dashboard (Streamlit). Reads pipeline artefacts only; it computes no prediction and no decision.

Run locally:  python -m streamlit run src/sentinelloop/dashboard.py -- --out-dir artifacts
Deployed:     streamlit_app.py (the same app on the committed snapshot in deploy/dashboard_data/)

Every number shown comes from the artefacts written by `pipeline.run` (metrics.json, decisions, predictions, work orders,
drift and conformal references, the audit log) or by the experiments (experiments/results/<exp>/summary.json).
Presentation helpers live in `sentinelloop.ui`.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

try:
    from sentinelloop import audit, viewdata
    from sentinelloop.ui import components as ui
    from sentinelloop.ui import format as fmt
    from sentinelloop.ui.theme import SEVERITY, SEVERITY_RANK, TOKENS, plotly_layout
except ImportError:  # running the file directly without the package installed
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from sentinelloop import audit, viewdata
    from sentinelloop.ui import components as ui
    from sentinelloop.ui import format as fmt
    from sentinelloop.ui.theme import SEVERITY, SEVERITY_RANK, TOKENS, plotly_layout

log = logging.getLogger("sentinelloop.dashboard")
LOGO = Path(__file__).resolve().parent / "ui" / "assets" / "logo.svg"
DATA_PILL = "Simulated benchmark data (NASA C-MAPSS)"
PLOT_CONFIG = {"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d"]}

# Kept for callers of the previous dashboard (severity colours by rule-table severity).
SEV_COLOR = {k: v["color"] for k, v in SEVERITY.items()}

EXPERIMENTS = {
    "e1_policy_replay": ("E1", "Decision policy replay", "Does acting on the interval's lower bound beat acting on the point estimate?"),
    "e1_seed_sensitivity": ("E1s", "Policy seed sensitivity", "Are the E1 policy results stable across random seeds?"),
    "e2_abstention": ("E2", "Escalating uncertain cases", "Does sending wide-interval cases to a human reduce decision errors?"),
    "e3_stress": ("E3", "Corrupted-input stress test", "Are corrupted inputs caught before they produce a confident wrong order?"),
    "e4_retrain_gate": ("E4", "Retraining gate (pre-registered)", "Does the promotion gate accept good challengers and reject bad ones?"),
    "e4_retrain_gate_secondary": ("E4s", "Retraining gate (secondary, post hoc)", "The E4 question with more validation rows and a label-corruption case."),
    "e5_decision_vs_rmse": ("E5", "Accuracy versus decision quality", "Does a lower RMSE always give better maintenance decisions?"),
    "e6_audit_check": ("E6", "Audit re-derivation", "Can every stored decision be re-derived from its audit record, and is tampering detected?"),
    "e7_ablation": ("E7", "Component ablation", "Which pipeline components matter for accuracy and interval coverage?"),
}


def _args():
    p = argparse.ArgumentParser()
    p.add_argument("--out-dir", default="artifacts")
    p.add_argument("--experiments-dir", default="experiments/results")
    argv = sys.argv[1:]
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    return p.parse_known_args(argv)[0]


# ---------------------------------------------------------------------------------------------------------------- data
def _signature(out_dir: str, subset: str) -> tuple:
    """File modification times, so the cache refreshes after a new pipeline run but not on ordinary reruns."""
    paths = list((Path(out_dir) / subset).glob("*")) + list((Path(out_dir) / "audit").glob(f"*{subset}*"))
    return tuple(sorted((p.name, p.stat().st_mtime) for p in paths if p.is_file()))


@st.cache_data(show_spinner=False)
def _load_bundle(out_dir: str, subset: str, _sig: tuple) -> viewdata.Bundle:
    return viewdata.load_bundle(out_dir, subset)


@st.cache_data(show_spinner=False)
def _load_summaries(exp_dir: str) -> dict:
    return viewdata.load_experiment_summaries(exp_dir)


def context(out_dir: str, exp_dir: str, subset: str) -> dict:
    b = _load_bundle(out_dir, subset, _signature(out_dir, subset))
    thr = dict(b.metrics.get("agent_thresholds") or {})
    return {"bundle": b, "subset": subset, "out_dir": out_dir, "exp_dir": exp_dir, "thr": thr, "fleet": viewdata.fleet_table(b)}


def _bool(v) -> bool:
    return str(v).strip().lower() in ("true", "1", "yes")


# ---------------------------------------------------------------------------------------------------------------- charts
def _chart(fig, key: str) -> None:
    st.plotly_chart(fig, width="stretch", config=PLOT_CONFIG, key=key)


def _threshold_lines(fig, thr: dict, axis: str = "y") -> None:
    for k, name, color in (("t_critical", "Critical", TOKENS["red"]), ("t_high", "High", TOKENS["orange"]), ("t_medium", "Plan", TOKENS["amber"])):
        if thr.get(k) is None:
            continue
        kw = dict(line_dash="dot", line_color=color, line_width=1, opacity=0.8,
                  annotation_text=f"{name} {fmt.fmt_num(thr[k], 0)}", annotation_font_color=color, annotation_font_size=11)
        (fig.add_hline(y=thr[k], annotation_position="top left", **kw) if axis == "y"
         else fig.add_vline(x=thr[k], annotation_position="top right", **kw))


def fleet_horizon(fleet: pd.DataFrame, thr: dict) -> go.Figure:
    """Every engine's remaining-life lower bound, sorted, coloured by severity: the fleet at one glance."""
    f = fleet.sort_values("rul_lower").reset_index(drop=True)
    fig = go.Figure()
    for sev, meta in SEVERITY.items():
        g = f[f["severity"] == sev]
        if g.empty:
            continue
        fig.add_trace(go.Bar(
            x=g.index, y=g["rul_lower"], name=meta["label"], marker_color=meta["color"], marker_line_width=0,
            customdata=list(zip(g["unit"], g["rul_point"], g["action"].map(fmt.action_label))),
            hovertemplate="Engine %{customdata[0]}<br>Lower bound %{y:.1f} cycles<br>Estimate %{customdata[1]:.1f} cycles"
                          "<br>%{customdata[2]}<extra>" + meta["label"] + "</extra>"))
    _threshold_lines(fig, thr)
    fig.update_layout(**plotly_layout(300, bargap=0.15, barmode="overlay"))
    fig.update_xaxes(title="Engines, ordered from least to most remaining life (hover for the engine number)", showticklabels=False)
    fig.update_yaxes(title="Remaining-life lower bound (cycles)", rangemode="tozero")
    return fig


def severity_bars(fleet: pd.DataFrame) -> go.Figure:
    order = [s for s in ("CRITICAL", "HIGH", "MEDIUM", "WATCH", "NONE")]
    counts = fleet["severity"].value_counts()
    vals = [int(counts.get(s, 0)) for s in order]
    fig = go.Figure(go.Bar(
        y=[SEVERITY[s]["label"] for s in order], x=vals, orientation="h", marker_color=[SEVERITY[s]["color"] for s in order],
        text=[str(v) for v in vals], textposition="outside", textfont=dict(color=TOKENS["text"]), cliponaxis=False,
        hovertemplate="%{y}: %{x} engines<extra></extra>"))
    fig.update_layout(**plotly_layout(230, margin=dict(l=8, r=36, t=8, b=8)))
    fig.update_yaxes(autorange="reversed", gridcolor="rgba(0,0,0,0)")
    fig.update_xaxes(title="Engines", rangemode="tozero")
    return fig


def rul_trace(tr: pd.DataFrame, thr: dict) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=tr["cycle"], y=tr["upper"], line=dict(width=0), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=tr["cycle"], y=tr["lower"], fill="tonexty", fillcolor="rgba(44,199,180,0.12)", line=dict(width=0),
                             name="90% interval", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=tr["cycle"], y=tr["point"], name="Estimate", line=dict(color=TOKENS["teal"], width=2),
                             hovertemplate="Cycle %{x}<br>Estimate %{y:.1f}<extra></extra>"))
    fig.add_trace(go.Scatter(x=tr["cycle"], y=tr["lower"], name="Lower bound (drives the decision)", line=dict(color=TOKENS["amber"], width=1.5, dash="dash"),
                             hovertemplate="Cycle %{x}<br>Lower bound %{y:.1f}<extra></extra>"))
    _threshold_lines(fig, thr)
    fig.update_layout(**plotly_layout(330))
    fig.update_xaxes(title="Operating cycle")
    fig.update_yaxes(title="Remaining useful life (cycles, capped at 125)", rangemode="tozero")
    return fig


def anomaly_trace(tr: pd.DataFrame, threshold) -> go.Figure:
    fig = go.Figure(go.Scatter(x=tr["cycle"], y=tr["anomaly_score"], name="Anomaly score", line=dict(color=TOKENS["steel"], width=1.6),
                               hovertemplate="Cycle %{x}<br>Score %{y:.2f}<extra></extra>"))
    flagged = tr[tr["anomaly_flag"].map(_bool)] if "anomaly_flag" in tr.columns else tr.iloc[0:0]
    if not flagged.empty:
        fig.add_trace(go.Scatter(x=flagged["cycle"], y=flagged["anomaly_score"], mode="markers", name="Sustained anomaly",
                                 marker=dict(color=TOKENS["orange"], size=6, symbol="diamond"), hovertemplate="Cycle %{x}<extra>flagged</extra>"))
    if threshold is not None:
        fig.add_hline(y=float(threshold), line_dash="dot", line_color=TOKENS["muted"], line_width=1,
                      annotation_text=f"Threshold {float(threshold):.2f}", annotation_position="top left", annotation_font_size=11)
    fig.update_layout(**plotly_layout(230))
    fig.update_xaxes(title="Operating cycle")
    fig.update_yaxes(title="Health-index score", rangemode="tozero")
    return fig


# ---------------------------------------------------------------------------------------------------------------- pages
def page_fleet(ctx: dict) -> None:
    b, fleet, thr, subset = ctx["bundle"], ctx["fleet"], ctx["thr"], ctx["subset"]
    m = b.metrics
    ui.page_header("Fleet overview", "Which engines need attention, and why. Each engine shows its latest assessment by the rule table, "
                   "which acts on the pessimistic end of the remaining-life interval.", [subset, DATA_PILL, "Advisory: a person decides"])
    if fleet.empty:
        ui.empty_state("No assessments for this subset yet", "Run python -m sentinelloop run --subset " + subset + " to produce them.")
        return
    sev = fleet["severity"].value_counts()
    esc = fleet["escalate"].map(_bool) if "escalate" in fleet.columns else pd.Series(False, index=fleet.index)
    dq = fleet["quality_flag"].map(_bool) if "quality_flag" in fleet.columns else pd.Series(False, index=fleet.index)
    cards = []
    cards.append(ui.kpi_card("Critical", str(int(sev.get("CRITICAL", 0))), note=f"Lower bound at or below {fmt.fmt_num(thr.get('t_critical'), 0)} cycles",
           accent="red" if sev.get("CRITICAL", 0) else ""))
    cards.append(ui.kpi_card("High", str(int(sev.get("HIGH", 0))), note=f"At or below {fmt.fmt_num(thr.get('t_high'), 0)} cycles",
           accent="amber" if sev.get("HIGH", 0) else ""))
    cards.append(ui.kpi_card("Human review", str(int(esc.sum())), note="Evidence not trustworthy enough to act on", accent="amber" if esc.sum() else ""))
    cards.append(ui.kpi_card("Data-quality flags", str(int(dq.sum())), note="Missing, imputed or out-of-range inputs", accent="amber" if dq.sum() else "teal"))
    cards.append(ui.kpi_card("Engines assessed", str(len(fleet)), note=f"Official {subset} test engines"))

    ui.kpi_row(cards)
    drift_alarm = bool(m.get("drift_alarm_test"))
    if drift_alarm:
        ui.alert("warning", "Fleet data drift alarm is active", "Incoming data no longer resemble the training data; serious orders are escalated to a person.")
    if dq.sum():
        ui.alert("warning", f"{int(dq.sum())} engines have unreliable input data", "Their decisions are escalated for human inspection, not acted on.")

    ui.section("Fleet horizon", "Remaining-life lower bound of every engine, ordered. Bars under a dotted line are inside that severity band.")
    _chart(fleet_horizon(fleet, thr), "horizon")

    left, right = st.columns([2, 3], gap="large")
    with left:
        ui.section("Severity distribution")
        _chart(severity_bars(fleet), "sevbars")
    with right:
        ui.section("Why the most urgent engines were prioritised", "Built from the rules that fired for each engine.")
        top = fmt.priority_table(fleet).head(3)
        if top.empty:
            ui.empty_state("Nothing needs attention", "Every engine's lower bound is above the planning threshold and no anomaly is sustained.")
        for eng in top["Engine"]:
            r = fleet[fleet["unit"] == eng].iloc[0]
            with st.container(border=True):
                st.markdown(f"{ui.severity_badge(r['severity'])} &nbsp;**Engine {int(eng)}**: {fmt.action_label(r['action'])}, "
                            f"lower bound {fmt.fmt_num(r['rul_lower'])} cycles", unsafe_allow_html=True)
                ui.reasons(fmt.explain(r.get("rules"), thr))

    ui.section("Engines needing attention", "Most urgent first. Open the Engine view for the full assessment of any engine.")
    pt = fmt.priority_table(fleet)
    if pt.empty:
        ui.empty_state("No engine needs attention", "All lower bounds are above the planning threshold.")
    else:
        st.dataframe(pt.style.apply(ui.severity_style, subset=["Priority"]), hide_index=True, width="stretch",
                     height=min(420, 38 + 35 * len(pt)), column_config={
                         "Engine": st.column_config.NumberColumn(format="%d", width="small"),
                         "Life lower bound": st.column_config.NumberColumn(format="%.1f", help="Pessimistic end of the 90% interval, in cycles"),
                         "Life estimate": st.column_config.NumberColumn(format="%.1f", help="Point estimate of remaining life, in cycles"),
                         "Interval width": st.column_config.NumberColumn(format="%.1f", help="Upper minus lower bound, in cycles"),
                         "Why": st.column_config.TextColumn(width="large")})
    with st.expander("All engines, with every recorded field"):
        st.dataframe(fleet, hide_index=True, width="stretch", height=360)

    ui.section("Model quality on this benchmark", "How the remaining-life model scored on the official test engines. "
               "These are benchmark numbers on simulated engines, separate from the operational decisions above.")
    cards = []
    cards.append(ui.kpi_card("Test RMSE", m.get("hgbr_rmse_capped"), "cycles", f"Raw truth: {fmt.fmt_num(m.get('hgbr_rmse_raw'), 2)} cycles",
           help="Typical size of the error in remaining life, against truth capped at 125 cycles."))
    cards.append(ui.kpi_card("PHM08 score", m.get("hgbr_phm08"), "", "Lower is better; late predictions cost more", digits=0,
           help=m.get("phm08_convention", "")))
    cards.append(ui.kpi_card("Interval coverage", fmt.fmt_pct(m.get("picp_test_capped"), 1), "", f"90% nominal; raw truth {fmt.fmt_pct(m.get('picp_test_raw'), 1)}",
           help="Share of engines whose true remaining life fell inside the 90% interval. Coverage is marginal: it holds on average, not per engine."))
    cards.append(ui.kpi_card("Mean interval width", m.get("mpiw_test"), "cycles", "Narrower is more informative", digits=1))
    cards.append(ui.kpi_card("Escalation share", fmt.fmt_pct(m.get("escalation_share_test"), 0), "", "Decisions sent to a person",
           help="Share of test-engine decisions the rule table escalated for human review."))
    ui.kpi_row(cards)


def page_engine(ctx: dict) -> None:
    b, fleet, thr = ctx["bundle"], ctx["fleet"], ctx["thr"]
    ui.page_header("Engine investigation", "The full assessment of one engine: how its remaining-life estimate and health score evolved, "
                   "and which rules produced its decision.", [ctx["subset"], DATA_PILL])
    if b.predictions.empty or fleet.empty:
        ui.empty_state("No engine data", "This subset has no stored predictions yet.")
        return
    order = fleet["unit"].astype(int).tolist()
    labels = {u: f"Engine {u} ({fmt.severity_label(fleet.loc[fleet['unit'] == u, 'severity'].iloc[0]).lower()})" for u in order}
    unit = st.selectbox("Engine", order, format_func=labels.get, key="engine_unit",
                        help="Ordered by urgency: the most severe and lowest lower bound first.")
    r = fleet[fleet["unit"] == unit].iloc[0]
    tr = viewdata.engine_trace(b, int(unit))
    esc = _bool(r.get("escalate"))

    st.markdown(f"{ui.severity_badge(r['severity'])} &nbsp;"
                + (ui.badge_html("Human review", TOKENS["amber"], "!") if esc else ui.badge_html("Acted on by rule", TOKENS["muted"], "")),
                unsafe_allow_html=True)
    cards = []
    cards.append(ui.kpi_card("Recommended action", fmt.action_label(r.get("action")), note="From the rule table", accent="amber" if esc else ""))
    cards.append(ui.kpi_card("Remaining life", r.get("rul_point"), "cycles", f"90% interval {fmt.fmt_num(r.get('rul_lower'))} to {fmt.fmt_num(r.get('rul_upper'))}", digits=1))
    cards.append(ui.kpi_card("Lower bound", r.get("rul_lower"), "cycles", "The value the severity rules use", digits=1,
           accent={"CRITICAL": "red", "HIGH": "amber"}.get(str(r["severity"]), "")))
    thr_a = b.anomaly.get("threshold")
    cards.append(ui.kpi_card("Health-index score", r.get("anomaly_score"), "", f"Threshold {fmt.fmt_num(thr_a, 2)}; "
                             + ("sustained anomaly" if _bool(r.get("anomaly_flag")) else "no sustained anomaly"), digits=2))
    ui.kpi_row(cards)

    left, right = st.columns([3, 2], gap="large")
    with left:
        ui.section("Why this decision", "Each sentence is a rule that fired, with its rule id.")
        ui.reasons(fmt.explain(r.get("rules"), thr))
        tops = fmt.split_list(r.get("top_sensors"))
        if tops:
            st.caption("Largest deviations from the healthy baseline: " + ", ".join(tops))
    with right:
        ui.section("Input checks")
        ui.key_values([
            ("Input quality", "Flagged" if _bool(r.get("quality_flag")) else "Passed"),
            ("Imputed values", fmt.fmt_pct(r.get("imputed_frac"), 0)),
            ("Fleet drift", "Alarm active" if _bool(r.get("drift_flag")) else "No alarm"),
            ("Assessed at cycle", fmt.fmt_num(r.get("cycle"), 0)),
            ("Work-order event", str(r.get("order_event", "–"))),
        ])

    ui.section("Remaining-life history", f"Cycles {int(tr['cycle'].min())} to {int(tr['cycle'].max())}. "
               "The dashed line is the lower bound the rules act on; dotted lines are the severity thresholds.")
    _chart(rul_trace(tr, thr), "rul")
    ui.section("Health-index history", "Score against the healthy-phase baseline. Diamonds mark cycles where the anomaly was sustained.")
    _chart(anomaly_trace(tr, thr_a), "anom")

    s = b.stream[b.stream["unit"] == unit] if not b.stream.empty else pd.DataFrame()
    if not s.empty:
        with st.expander(f"Cycle-by-cycle replay of this engine ({len(s)} decisions)"):
            st.caption("A replay of the stored test file one cycle at a time, not live telemetry.")
            cols = [x for x in ["cycle", "point", "lower", "upper", "anomaly_score", "severity", "action", "escalate", "reasons", "order_event"] if x in s.columns]
            st.dataframe(s[cols], hide_index=True, width="stretch", height=260)
    with st.expander("Benchmark ground truth (evaluation only)"):
        st.caption("Simulated engines come with their true remaining life. A real machine would not have this number.")
        ui.key_values([("True remaining life (capped)", fmt.fmt_num(r.get("rul_true_capped"), 0, "cycles")),
                       ("True remaining life (raw)", fmt.fmt_num(r.get("rul_true_raw"), 0, "cycles")),
                       ("Estimate error (capped)", fmt.fmt_num(float(r["rul_point"]) - float(r["rul_true_capped"]), 1, "cycles")
                        if not fmt.is_missing(r.get("rul_true_capped")) else "–")])


def page_orders(ctx: dict) -> None:
    b = ctx["bundle"]
    ui.page_header("Work orders", "Draft orders raised by the rule table, one open order per engine. They are records for a planner to "
                   "review: nothing here is sent to a maintenance system or executed.", [ctx["subset"], "Draft records"])
    if not b.orders:
        ui.empty_state("No open work orders", "No engine reached the high or critical band, and none was escalated.")
        return
    o = pd.DataFrame(b.orders)
    o["due_in"] = o["due_by_cycle"] - o["updated_cycle"] if {"due_by_cycle", "updated_cycle"} <= set(o.columns) else float("nan")
    cards = []
    cards.append(ui.kpi_card("Open orders", str(len(o)), note="Status: open draft"))
    cards.append(ui.kpi_card("Human inspection", str(int((o["type"] == "INSPECTION").sum())), note="Escalated: evidence not trustworthy",
           accent="amber" if (o["type"] == "INSPECTION").any() else ""))
    cards.append(ui.kpi_card("Maintenance", str(int((o["type"] == "MAINTENANCE").sum())), note="High or critical severity, acted on by rule"))
    cards.append(ui.kpi_card("Critical", str(int((o["severity"] == "CRITICAL").sum())), note="Lower bound in the critical band",
           accent="red" if (o["severity"] == "CRITICAL").any() else ""))
    ui.kpi_row(cards)
    ui.alert("info", "These orders have no approval workflow in this pipeline",
             "The competition pipeline drafts them; the product platform (src/sentinelloop/app) adds named approval, scheduling and completion.")

    f1, f2, f3 = st.columns([2, 2, 2])
    kind = f1.segmented_control("Order type", ["All", "Maintenance", "Inspection"], default="All", key="wo_type")
    sevs = f2.multiselect("Severity", [s for s in ("CRITICAL", "HIGH", "MEDIUM", "WATCH", "NONE") if s in set(o["severity"])],
                          format_func=fmt.severity_label, key="wo_sev")
    src = f3.segmented_control("Source", ["All", "Batch assessment", "Cycle replay"], default="All", key="wo_src")
    v = o.copy()
    if kind and kind != "All":
        v = v[v["type"] == kind.upper()]
    if sevs:
        v = v[v["severity"].isin(sevs)]
    if src and src != "All" and "mode" in v.columns:
        v = v[v["mode"] == ("batch" if src == "Batch assessment" else "stream")]
    v = v.assign(_r=v["severity"].map(SEVERITY_RANK)).sort_values(["_r", "due_in"], ascending=[False, True])
    table = pd.DataFrame({
        "Order": v["id"].astype(int), "Engine": v["unit"].astype(int),
        "Priority": [f"{SEVERITY.get(s, {}).get('glyph', '')} {fmt.severity_label(s)}" for s in v["severity"]],
        "Type": v["type"].str.capitalize(), "Recommended action": v["action"].map(fmt.action_label),
        "Due in": v["due_in"], "Reason": [", ".join(fmt.reason_label(x) for x in fmt.split_list(rs)) or "Severity rule" for rs in v["reasons"]],
        "Status": "Open (draft)", "Source": v.get("mode", pd.Series("batch", index=v.index)).map({"batch": "Batch", "stream": "Replay"}),
    })
    ui.section(f"Queue ({len(table)} of {len(o)} orders)", "Most urgent first; within a band, the soonest due.")
    if table.empty:
        ui.empty_state("No orders match these filters", "Clear a filter to see more orders.")
        return
    st.dataframe(table.style.apply(ui.severity_style, subset=["Priority"]), hide_index=True, width="stretch",
                 height=min(440, 38 + 35 * len(table)), column_config={
                     "Order": st.column_config.NumberColumn(format="%d", width="small"),
                     "Engine": st.column_config.NumberColumn(format="%d", width="small"),
                     "Due in": st.column_config.NumberColumn(format="%d cycles", help="Cycles from the latest update to the due cycle (the lower bound)")})
    ui.section("Order details")
    pick = st.selectbox("Order", table["Order"].tolist(), format_func=lambda i: f"Order {i}, engine {int(o.loc[o['id'] == i, 'unit'].iloc[0])}",
                        key="wo_pick")
    d = o[o["id"] == pick].iloc[0]
    left, right = st.columns(2, gap="large")
    with left:
        st.markdown(ui.severity_badge(d["severity"]), unsafe_allow_html=True)
        ui.key_values([("Type", str(d["type"]).capitalize()), ("Recommended action", fmt.action_label(d.get("action"))),
                       ("Created at cycle", fmt.fmt_num(d.get("created_cycle"), 0)), ("Last updated at cycle", fmt.fmt_num(d.get("updated_cycle"), 0)),
                       ("Due by cycle", fmt.fmt_num(d.get("due_by_cycle"), 0)), ("Decisions merged", fmt.fmt_num(d.get("n_decisions"), 0)),
                       ("Raised", str(d.get("ts", "–")).replace("T", " "))])
    with right:
        ui.key_values([("Life estimate", fmt.fmt_num(d.get("rul_point"), 1, "cycles")),
                       ("90% interval", f"{fmt.fmt_num(d.get('rul_lower'))} to {fmt.fmt_num(d.get('rul_upper'))} cycles"),
                       ("Top deviating sensors", ", ".join(fmt.split_list(d.get("top_sensors"))) or "–"),
                       ("Model version", fmt.short_id(d.get("model_version"), 12))])
        ui.reasons(fmt.explain(d.get("rules_fired"), ctx["thr"]))


def page_model(ctx: dict) -> None:
    b, m, subset = ctx["bundle"], ctx["bundle"].metrics, ctx["subset"]
    ui.page_header("Model and monitoring", "What model produced these assessments, how well it scored, how trustworthy its intervals are, "
                   "whether incoming data still look like the training data, and how retraining candidates were judged.", [subset, DATA_PILL])
    if not m:
        ui.empty_state("No model metrics", "Run the pipeline for this subset first.")
        return
    ui.section("Active model")
    left, right = st.columns([3, 2], gap="large")
    with left:
        ui.key_values([("Registry alias", str(m.get("model_alias", "–"))), ("Registered model", f"sentinelloop-{subset}"),
                       ("Run", fmt.short_id(m.get("mlflow_run_id"), 12)), ("Point model", "Gradient-boosted trees (HistGradientBoosting)"),
                       ("Interval method", "Conformalized quantile regression, 90% nominal"),
                       ("Input features", fmt.fmt_num(m.get("n_features"), 0)), ("Pipeline run time", fmt.fmt_num(m.get("elapsed_s"), 1, "s"))])
    with right:
        with st.expander("Technical identifiers"):
            ui.key_values([("MLflow run id", str(m.get("mlflow_run_id", "–"))), ("Config hash", str(m.get("config_hash", "–"))),
                           ("Training data sha256", str((m.get("data_hashes") or {}).get("train", "–"))),
                           ("Dropped sensors", ", ".join(m.get("dropped_sensors") or []) or "–"), ("Seed", str(m.get("seed", "–")))])

    ui.section("Evaluation on the official test engines", "Headline model: all training engines. Decision model: 70% of engines, "
               "the other 30% calibrate its interval. Errors are in cycles; RUL is capped at 125 for the capped columns.")
    ev = pd.DataFrame([
        {"Model": "Headline (all engines)", "RMSE capped": m.get("hgbr_rmse_capped"), "RMSE raw": m.get("hgbr_rmse_raw"), "PHM08": m.get("hgbr_phm08")},
        {"Model": "Decision model (70% engines)", "RMSE capped": m.get("cqr_point_rmse_capped"), "RMSE raw": m.get("cqr_point_rmse_raw"), "PHM08": m.get("cqr_point_phm08")},
    ])
    st.dataframe(ev, hide_index=True, width="stretch", column_config={
        "RMSE capped": st.column_config.NumberColumn(format="%.2f"), "RMSE raw": st.column_config.NumberColumn(format="%.2f"),
        "PHM08": st.column_config.NumberColumn(format="%.0f", help=m.get("phm08_convention", ""))})

    ui.section("Prediction uncertainty", "Coverage is marginal: it holds on average over engines under an exchangeability assumption, "
               "not for each engine, and it is lower near failure and against the raw truth.")
    pc = m.get("picp_test_capped")
    ui.kpi_row([
        ui.kpi_card("Coverage, capped truth", fmt.fmt_pct(pc, 1), note="Nominal 90%", accent="teal" if (pc or 0) >= 0.9 else "amber"),
        ui.kpi_card("Coverage, raw truth", fmt.fmt_pct(m.get("picp_test_raw"), 1), note="Uncapped remaining life", accent="amber"),
        ui.kpi_card("Mean width", m.get("mpiw_test"), "cycles", digits=1),
        ui.kpi_card("Width limit for acting", m.get("agent_max_width"), "cycles", "Wider intervals go to a person", digits=1)])
    with st.expander("Calibration details"):
        cf = b.conformal
        ui.key_values([("Calibration engines", fmt.fmt_num(len(cf.get("calibration_units") or []), 0)),
                       ("Calibration rows", fmt.fmt_num(cf.get("n_calibration_rows"), 0)),
                       ("Truncations per engine", fmt.fmt_num(cf.get("truncations_per_engine"), 0)),
                       ("Conformal correction (qhat)", fmt.fmt_num(cf.get("qhat"), 2, "cycles")), ("Assumption", str(cf.get("assumption", "–")))])

    ui.section("Drift and input quality", "Early-life test rows compared with the same age slice of the training engines (PSI per feature).")
    tw, q = b.drift.get("test_window", {}), b.drift.get("quality", {})
    alarm = bool(tw.get("alarm"))
    ui.kpi_row([
        ui.kpi_card("Drift alarm", "Active" if alarm else "None", note=f"Alarm if over {fmt.fmt_pct(b.drift.get('share_threshold'), 0)} of features drift",
                    accent="red" if alarm else "teal"),
        ui.kpi_card("Features drifting", fmt.fmt_pct(tw.get("drift_share"), 1), note=f"PSI over {fmt.fmt_num(b.drift.get('psi_threshold'), 1)}"),
        ui.kpi_card("Missing values", fmt.fmt_pct(q.get("missing_frac"), 2), note=f"{fmt.fmt_num(q.get('n_rows'), 0)} rows checked"),
        ui.kpi_card("Out of training range", fmt.fmt_pct(q.get("out_of_range_frac"), 3), note="Against the full training range")])
    if tw.get("drifted_features"):
        st.caption("Drifting features: " + ", ".join(tw["drifted_features"]))

    oc = m.get("decision_outcomes_test")
    if oc:
        ui.section("Decisions against the benchmark truth", "Possible only because simulated engines come with their true remaining life.")
        cards = []
        cards.append(ui.kpi_card("Lower bound above truth", fmt.fmt_pct(oc.get("lower_bound_above_truth_rate"), 1), note="Optimistic lower bounds"))
        cards.append(ui.kpi_card("Serious cases missed", fmt.fmt_pct(oc.get("serious_truth_missed_rate"), 1), note=f"True life at or below {fmt.fmt_num(ctx['thr'].get('t_high'), 0)} cycles, rated below high"))
        cards.append(ui.kpi_card("Confident orders on healthy engines", fmt.fmt_num(oc.get("confident_order_on_healthy_count"), 0), note="True life over the planning threshold"))
        ui.kpi_row(cards)
        counts = pd.DataFrame(oc.get("counts", {})).T
        if not counts.empty:
            counts.index = [fmt.severity_label(i) for i in counts.index]
            st.dataframe(counts.rename_axis("Severity given").reset_index(), hide_index=True, width="stretch")
            st.caption("Columns: true remaining-life band in cycles. Each cell counts engines.")

    ui.section("Retraining history", "A challenger replaces the champion only if it passes every gate on held-out engines: "
               "RMSE no worse than the champion plus 2%, coverage at least 85%, late-order rate no more than 2 points higher.")
    gate = [r for r in b.retrain_log if r.get("scenario") != "C_drift_trigger"]
    drift_rows = [r for r in b.retrain_log if r.get("scenario") == "C_drift_trigger"]
    if not gate:
        ui.empty_state("No retraining runs recorded", "Run python -m sentinelloop retrain --subset " + subset + " --simulate-new-data.")
    else:
        g = pd.DataFrame(gate)
        scen = {"A_accept_more_data": "More new engines (should promote)", "B_reject_corrupted_data": "Sensor offset in new data (should reject)",
                "B2_reject_label_corruption": "Wrong labels in new data (should reject)"}
        runs = {"e4_retrain_gate": "Pre-registered", "e4_retrain_gate_secondary": "Secondary"}
        col = lambda k: g[k] if k in g.columns else pd.Series([None] * len(g))  # noqa: E731
        st.dataframe(pd.DataFrame({
            "Run": col("run").map(lambda x: runs.get(x, x)), "Scenario": col("scenario").map(lambda x: scen.get(x, x)),
            "Decision": col("decision").map(lambda x: str(x).capitalize()), "As expected": col("as_expected").map(lambda x: "Yes" if x else "No"),
            "RMSE": [f"{fmt.fmt_num(a, 2)} → {fmt.fmt_num(c_, 2)}" for a, c_ in zip(col("champion_rmse"), col("challenger_rmse"))],
            "Coverage": [f"{fmt.fmt_pct(a, 1)} → {fmt.fmt_pct(c_, 1)}" for a, c_ in zip(col("champion_picp"), col("challenger_picp"))],
            "Why": [x if x else "All gates passed" for x in col("reasons").fillna("")],
        }), hide_index=True, width="stretch", column_config={
            "RMSE": st.column_config.TextColumn(help="Champion → challenger, cycles, on held-out validation engines"),
            "Coverage": st.column_config.TextColumn(help="Champion → challenger interval coverage on validation engines"),
            "Why": st.column_config.TextColumn(width="large")})
        st.caption("These runs used simulated 'new data' (training engines the champion had not seen). The pre-registered gate test met "
                   "4 of 8 expected outcomes, so the gate's selectivity is not established (experiment E4).")
    if drift_rows:
        with st.expander("Drift-trigger checks"):
            st.dataframe(pd.DataFrame(drift_rows)[[k for k in ["run", "false_alarms_in_20_clean_windows", "regime_shift_alarm", "bias_alarm", "bias_share"]
                                                   if any(k in r for r in drift_rows)]], hide_index=True, width="stretch")


def _exp_chart(name: str, df: pd.DataFrame):
    if df.empty:
        return None
    lay = plotly_layout(300)
    palette = [TOKENS["teal"], TOKENS["amber"], TOKENS["steel"], TOKENS["orange"], "#B48EE0", "#5FD38D", "#F28FB1", "#9FB3C8", "#D9C36A", "#6FD6E8"]

    def _scatter(group, x, y, xt, yt, hover):
        fig = go.Figure()
        for k, (key, g) in enumerate(df.groupby(group, sort=False)):
            fig.add_trace(go.Scatter(x=g[x], y=g[y], mode="markers", name=str(key), marker=dict(size=11, color=palette[k % len(palette)],
                                     line=dict(width=1, color=TOKENS["bg"])), hovertemplate=f"{key}<br>{hover}<extra></extra>"))
        fig.update_layout(**plotly_layout(340, legend=dict(orientation="v", x=1.01, y=1, font=dict(size=11))))
        fig.update_xaxes(title=xt)
        fig.update_yaxes(title=yt)
        return fig
    if name == "e1_policy_replay" and {"late_rate", "mean_discarded_life"} <= set(df.columns):
        return _scatter("policy", "mean_discarded_life", "late_rate", "Mean discarded life per engine (cycles; lower is better)",
                        "Late-order rate (lower is better)", "Discarded life %{x:.1f} cycles<br>Late rate %{y:.3f}")
    if name == "e3_stress" and "fault" in df.columns:
        fig = go.Figure([go.Bar(x=df["fault"], y=df["detection_rate"], name="Detected", marker_color=TOKENS["teal"]),
                         go.Bar(x=df["fault"], y=df["silent_wrong_order_naive"], name="Silent wrong order, naive", marker_color=TOKENS["red"]),
                         go.Bar(x=df["fault"], y=df["silent_wrong_order_full"], name="Silent wrong order, full rules", marker_color=TOKENS["amber"])])
        fig.update_layout(**lay, barmode="group")
        fig.update_yaxes(title="Share of corrupted engines", tickformat=".0%")
        fig.update_xaxes(title="Injected fault")
        return fig
    if name == "e5_decision_vs_rmse" and {"rmse_eval_random_truncation", "mean_discarded_life"} <= set(df.columns):
        return _scatter("model", "rmse_eval_random_truncation", "mean_discarded_life", "RMSE (cycles)", "Mean discarded life (cycles)",
                        "RMSE %{x:.2f}<br>Discarded life %{y:.1f}")
    if name == "e7_ablation" and "variant" in df.columns:
        fig = go.Figure(go.Bar(x=df["variant"], y=df["test_rmse_capped"], marker_color=TOKENS["steel"], text=df["test_rmse_capped"].round(2),
                               textposition="outside", cliponaxis=False))
        fig.update_layout(**lay)
        fig.update_yaxes(title="Test RMSE, capped (cycles)")
        return fig
    if name == "e2_abstention" and "error_rate_all_decisions" in df.columns:
        fig = go.Figure([go.Bar(x=df["subset"], y=df[k], name=lbl, marker_color=col) for k, lbl, col in
                         (("error_rate_all_decisions", "All decisions", TOKENS["steel"]), ("error_rate_acted_upon", "Acted upon", TOKENS["teal"]),
                          ("error_rate_among_escalated", "Escalated", TOKENS["amber"]))])
        fig.update_layout(**lay, barmode="group")
        fig.update_yaxes(title="Decision error rate", tickformat=".0%")
        return fig
    return None


def page_experiments(ctx: dict) -> None:
    ui.page_header("Experiments", "The pre-registered experiments behind the claims, including the ones whose hypothesis was not supported. "
                   "All were run on simulated engines: they test the method, not savings or field performance.", [DATA_PILL, "Pre-registered"])
    summaries = _load_summaries(ctx["exp_dir"])
    if not summaries:
        ui.empty_state("No experiment results", "Run python experiments/run_all.py to produce experiments/results/<exp>/summary.json.")
        return
    names = [n for n in EXPERIMENTS if n in summaries] + [n for n in summaries if n not in EXPERIMENTS]
    rows = []
    for n in names:
        code, title, _ = EXPERIMENTS.get(n, (n, n, ""))
        rows.append({"Experiment": f"{code} {title}", "Verdict": fmt.verdict(summaries[n].get("conclusion", "")), "Key": n})
    ov = pd.DataFrame(rows)
    ui.section("Overview")
    st.dataframe(ov[["Experiment", "Verdict"]], hide_index=True, width="stretch", height=42 + 36 * len(ov))
    ui.section("Inspect an experiment")
    c1, c2 = st.columns([3, 1])
    pick = c1.selectbox("Experiment", names, format_func=lambda n: " ".join(EXPERIMENTS.get(n, (n, n, ""))[:2]), key="exp_pick")
    only = c2.toggle(f"Only {ctx['subset']}", value=True, key="exp_only")
    s = summaries[pick]
    code, title, question = EXPERIMENTS.get(pick, (pick, pick, ""))
    v = fmt.verdict(s.get("conclusion", ""))
    color = {"Supported": TOKENS["teal"], "Not supported": TOKENS["amber"]}.get(v, TOKENS["muted"])
    st.markdown(ui.badge_html(v, color), unsafe_allow_html=True)
    if question:
        st.markdown(f"**Question.** {question}")
    if s.get("hypothesis"):
        st.markdown(f"**Pre-registered hypothesis.** {s['hypothesis'] if isinstance(s['hypothesis'], str) else json.dumps(s['hypothesis'])}")
    if s.get("conclusion"):
        st.markdown(f"**Result.** {s['conclusion']}")
    tbl = s.get("table")
    df = pd.DataFrame(tbl) if isinstance(tbl, list) and tbl else pd.DataFrame()
    if only and "subset" in df.columns:
        df = df[df["subset"] == ctx["subset"]]
    fig = _exp_chart(pick, df)
    if fig is not None:
        _chart(fig, f"exp_{pick}")
    if not df.empty:
        st.dataframe(df, hide_index=True, width="stretch", height=min(420, 38 + 35 * len(df)))
    elif pick == "e6_audit_check":
        rp = s.get("replay", {})
        cards = []
        cards.append(ui.kpi_card("Decisions re-derived", fmt.fmt_num(rp.get("n"), 0)))
        cards.append(ui.kpi_card("Mismatches", fmt.fmt_num(rp.get("mismatches"), 0), accent="teal" if rp.get("mismatches") == 0 else "red"))
        cards.append(ui.kpi_card("Chain valid", "Yes" if rp.get("chain_valid") else "No", accent="teal" if rp.get("chain_valid") else "red"))
        ui.kpi_row(cards)
    with st.expander("Raw summary (JSON)"):
        st.json(s, expanded=False)


def page_audit(ctx: dict) -> None:
    b, m = ctx["bundle"], ctx["bundle"].metrics
    ui.page_header("Audit trail", "Every decision is stored with its inputs, thresholds and the rules that fired, in a hash-chained log. "
                   "Verification proves the record is complete and unaltered; it does not prove the prediction was right.", [ctx["subset"], "Tamper-evident log"])
    log_path = Path(ctx["out_dir"]) / "audit" / f"decisions_{ctx['subset']}.jsonl"
    if not log_path.exists() or not b.audit:
        ui.empty_state("No audit log for this subset", "The pipeline writes it to audit/decisions_<subset>.jsonl when it runs.")
        return
    key = f"audit_report_{ctx['subset']}"
    rep = st.session_state.get(key)
    cards = [ui.kpi_card("Records", str(len(b.audit)), note="Decisions in this log")]
    if rep is None:
        stored = m.get("audit_chain_valid")
        cards += [ui.kpi_card("Chain at write time", "Valid" if stored else ("Invalid" if stored is False else "–"), note="Recorded by the pipeline run",
                              accent="teal" if stored else ""),
                  ui.kpi_card("Re-derivation", "Not run", note="Press Verify to check now")]
    else:
        cards += [ui.kpi_card("Hash chain", "Valid" if rep.get("chain_valid") else "Broken", note="Checked just now",
                              accent="teal" if rep.get("chain_valid") else "red"),
                  ui.kpi_card("Mismatches", fmt.fmt_num(rep.get("mismatches"), 0), note=f"Of {fmt.fmt_num(rep.get('n'), 0)} decisions re-derived",
                              accent="teal" if rep.get("mismatches") == 0 else "red")]
    cards.append(ui.kpi_card("Last record hash", fmt.short_id(m.get("audit_terminal_hash") or b.audit[-1].get("hash"), 12), note="Anchor for comparison"))
    ui.kpi_row(cards)
    if st.button("Verify the chain and re-derive every decision", type="primary", key="audit_verify"):
        with st.spinner("Re-deriving decisions from their stored inputs"):
            st.session_state[key] = audit.replay_check(log_path)
        st.rerun()
    if rep is not None:
        ok = rep.get("chain_valid") and rep.get("mismatches") == 0
        ui.alert("ok" if ok else "critical", "Every record verified" if ok else "Verification found problems",
                 f"{fmt.fmt_num(rep.get('n'), 0)} decisions re-derived from their inputs with {fmt.fmt_num(rep.get('mismatches'), 0)} mismatches; "
                 f"hash chain {'intact' if rep.get('chain_valid') else 'broken'}." if ok else json.dumps(rep.get("details", []))[:400])

    recs = pd.DataFrame([{
        "Seq": r.get("seq"), "Time (UTC)": str(r.get("ts", ""))[:19].replace("T", " "), "Engine": r.get("unit"), "Cycle": r.get("cycle"),
        "Severity": fmt.severity_label(r.get("severity")), "Action": fmt.action_label(r.get("action")),
        "Human review": "Yes" if r.get("escalate_to_human") else "No",
        "Reasons": ", ".join(fmt.reason_label(x) for x in r.get("escalation_reasons") or []),
        "Source": {"batch": "Batch", "stream": "Replay"}.get((r.get("extra") or {}).get("mode", ""), ""), "Model": fmt.short_id(r.get("model_version"), 8)} for r in b.audit])
    ui.section("Records", "Filter the log, then open one record to see exactly what the rule table saw.")
    f1, f2, f3 = st.columns([2, 1, 1])
    sev = f1.multiselect("Severity", [SEVERITY[s]["label"] for s in SEVERITY if SEVERITY[s]["label"] in set(recs["Severity"])], key="aud_sev")
    only_esc = f2.toggle("Human review only", key="aud_esc")
    eng = f3.number_input("Engine", min_value=0, value=0, step=1, help="0 shows every engine", key="aud_eng")
    v = recs
    if sev:
        v = v[v["Severity"].isin(sev)]
    if only_esc:
        v = v[v["Human review"] == "Yes"]
    if eng:
        v = v[v["Engine"] == eng]
    if v.empty:
        ui.empty_state("No records match", "Clear a filter to see more records.")
        return
    st.dataframe(v, hide_index=True, width="stretch", height=min(420, 38 + 35 * len(v)),
                 column_config={"Seq": st.column_config.NumberColumn(format="%d", width="small"), "Engine": st.column_config.NumberColumn(format="%d", width="small")})
    pick = st.selectbox("Record", v["Seq"].tolist(), format_func=lambda s_: f"Record {s_}", key="aud_pick")
    rec = next(r for r in b.audit if r.get("seq") == pick)
    left, right = st.columns(2, gap="large")
    inp, th = rec.get("inputs") or {}, rec.get("thresholds") or {}
    with left:
        ui.section("What the rule table saw")
        ui.key_values([("Engine, cycle", f"{rec.get('unit')}, {rec.get('cycle')}"),
                       ("Remaining life", f"{fmt.fmt_num(inp.get('rul_point'))} (interval {fmt.fmt_num(inp.get('rul_lower'))} to {fmt.fmt_num(inp.get('rul_upper'))})"),
                       ("Health-index score", fmt.fmt_num(inp.get("anomaly_score"), 2)), ("Imputed values", fmt.fmt_pct(inp.get("imputed_frac"), 0)),
                       ("Quality flag", "Yes" if inp.get("quality_flag") else "No"), ("Drift flag", "Yes" if inp.get("drift_flag") else "No")])
    with right:
        ui.section("What it decided")
        st.markdown(ui.severity_badge(rec.get("severity")), unsafe_allow_html=True)
        ui.reasons(fmt.explain(rec.get("rules_fired"), th))
    with st.expander("Raw record, with hashes"):
        st.json(rec, expanded=False)


PAGES = {
    "fleet": (page_fleet, "Fleet overview", ":material/monitoring:"),
    "engine": (page_engine, "Engine investigation", ":material/precision_manufacturing:"),
    "orders": (page_orders, "Work orders", ":material/assignment:"),
    "model": (page_model, "Model and monitoring", ":material/model_training:"),
    "experiments": (page_experiments, "Experiments", ":material/science:"),
    "audit": (page_audit, "Audit trail", ":material/verified_user:"),
}


def render(page_key: str, ctx: dict) -> None:
    """Render one page; an unexpected error is explained in plain words and logged, never shown as a traceback."""
    try:
        PAGES[page_key][0](ctx)
    except Exception:  # noqa: BLE001 - the UI must stay usable; the details go to the server log
        log.exception("dashboard page %s failed", page_key)
        ui.alert("critical", "This view could not be displayed", "Some stored results are missing or in an unexpected format. "
                 "Re-run the pipeline for this subset, then reload the page.")


def main() -> None:
    args = _args()
    st.set_page_config(page_title="SentinelLoop", page_icon=str(LOGO) if LOGO.exists() else None, layout="wide",
                       initial_sidebar_state="auto")
    ui.inject_css()
    if LOGO.exists():
        st.logo(str(LOGO), size="large")
    subsets = viewdata.available_subsets(args.out_dir)
    holder: dict = {}

    def make(key):
        def _page():
            render(key, holder["ctx"])
        _page.__name__ = f"page_{key}"
        return _page

    nav = st.navigation([st.Page(make(k), title=t, icon=i, url_path=k, default=(k == "fleet")) for k, (_, t, i) in PAGES.items()])
    if not subsets:
        ui.page_header("SentinelLoop", "No pipeline results were found.", [])
        ui.empty_state("Nothing to show yet", f"No artefacts in {args.out_dir}. Run python -m sentinelloop run --subset FD001, then reload.")
        return
    with st.sidebar:
        st.markdown("##### Dataset")
        subset = st.selectbox("C-MAPSS subset", subsets, key="subset", help="Each subset is a separate simulated fleet with its own model.")
        st.caption(fmt.SUBSETS.get(subset, ""))
        holder["ctx"] = context(args.out_dir, args.experiments_dir, subset)
        m = holder["ctx"]["bundle"].metrics
        with st.expander("Run context"):
            ui.key_values([("Model alias", str(m.get("model_alias", "–"))), ("Run", fmt.short_id(m.get("mlflow_run_id"), 10)),
                           ("Config", fmt.short_id(m.get("config_hash"), 10))])
        st.markdown('<div class="sl-foot">Advisory decision support on NASA C-MAPSS simulated engines. Not validated on real equipment; '
                    "every order needs a person's judgement.</div>", unsafe_allow_html=True)
    nav.run()


if __name__ == "__main__":
    main()
