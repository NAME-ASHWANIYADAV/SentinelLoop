"""SentinelLoop monitoring dashboard (Streamlit). Reads artefacts only; no computation beyond plots.

Run:  python -m streamlit run src/sentinelloop/dashboard.py -- --out-dir artifacts
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

try:
    from sentinelloop import audit, viewdata
except ImportError:  # running the file directly without the package installed
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from sentinelloop import audit, viewdata

SEV_COLOR = {"CRITICAL": "#b91c1c", "HIGH": "#ea580c", "MEDIUM": "#ca8a04", "WATCH": "#2563eb", "NONE": "#6b7280"}


def _args():
    p = argparse.ArgumentParser()
    p.add_argument("--out-dir", default="artifacts")
    p.add_argument("--experiments-dir", default="experiments/results")
    argv = sys.argv[1:]
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    return p.parse_known_args(argv)[0]


def main() -> None:
    args = _args()
    st.set_page_config(page_title="SentinelLoop", layout="wide")
    st.title("SentinelLoop — closed-loop prognostics for a connected fleet")
    st.caption("NASA C-MAPSS is simulated engine data (Saxena et al., PHM08). 'Stream' decisions are a cycle-by-cycle REPLAY of test engines, not live telemetry. No LLM is used anywhere.")
    subsets = viewdata.available_subsets(args.out_dir)
    if not subsets:
        st.warning(f"No artefacts found in {args.out_dir}. Run: python -m sentinelloop run --subset FD001")
        return
    subset = st.sidebar.selectbox("Subset", subsets)
    b = viewdata.load_bundle(args.out_dir, subset)
    m = b.metrics
    st.sidebar.markdown(f"**Model version** `{m.get('mlflow_run_id', 'local')}` alias `{m.get('model_alias', '-')}` (registered model `sentinelloop-{subset}`)")
    st.sidebar.markdown(f"Config hash `{m.get('config_hash', '-')}` · data sha256 (train) `{str(m.get('data_hashes', {}).get('train', ''))[:12]}`")

    tab_fleet, tab_engine, tab_orders, tab_model, tab_exp, tab_audit = st.tabs(["Fleet", "Engine", "Work orders", "Model & monitoring", "Experiments", "Audit"])

    with tab_fleet:
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Test RMSE (capped / raw)", f"{m.get('hgbr_rmse_capped', float('nan')):.2f} / {m.get('hgbr_rmse_raw', float('nan')):.2f}")
        c2.metric("PHM08 score", f"{m.get('hgbr_phm08', float('nan')):.0f}")
        c3.metric("Interval coverage (90% nominal)", f"{m.get('picp_test_capped', float('nan')):.3f}")
        c4.metric("Mean interval width", f"{m.get('mpiw_test', float('nan')):.1f} cycles")
        c5.metric("Escalation share", f"{m.get('escalation_share_test', float('nan')):.2f}")
        fleet = viewdata.fleet_table(b)
        counts = fleet["severity"].value_counts() if not fleet.empty else pd.Series(dtype=int)
        if len(counts):
            fig = go.Figure(go.Bar(x=list(counts.index), y=list(counts.values), marker_color=[SEV_COLOR.get(s, "#999") for s in counts.index]))
            fig.update_layout(height=250, margin=dict(l=10, r=10, t=10, b=10), yaxis_title="engines")
            st.plotly_chart(fig, width='stretch')
        st.dataframe(fleet, width='stretch', height=400)

    with tab_engine:
        units = sorted(b.predictions["unit"].unique()) if not b.predictions.empty else []
        if units:
            unit = st.selectbox("Engine", units)
            tr = viewdata.engine_trace(b, int(unit))
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=tr["cycle"], y=tr["upper"], line=dict(width=0), showlegend=False))
            fig.add_trace(go.Scatter(x=tr["cycle"], y=tr["lower"], fill="tonexty", fillcolor="rgba(37,99,235,0.15)", line=dict(width=0), name="90% interval"))
            fig.add_trace(go.Scatter(x=tr["cycle"], y=tr["point"], name="RUL point", line=dict(color="#2563eb")))
            fig.add_trace(go.Scatter(x=tr["cycle"], y=tr["lower"], name="lower bound (drives the agent)", line=dict(color="#b91c1c", dash="dot")))
            fig.update_layout(height=350, margin=dict(l=10, r=10, t=10, b=10), xaxis_title="cycle", yaxis_title="RUL (capped at 125)")
            st.plotly_chart(fig, width='stretch')
            fig2 = go.Figure(go.Scatter(x=tr["cycle"], y=tr["anomaly_score"], name="anomaly score", line=dict(color="#ea580c")))
            thr = b.anomaly.get("threshold")
            if thr is not None:
                fig2.add_hline(y=thr, line_dash="dash", annotation_text="threshold")
            fig2.update_layout(height=220, margin=dict(l=10, r=10, t=10, b=10), xaxis_title="cycle", yaxis_title="score")
            st.plotly_chart(fig2, width='stretch')
            d = b.decisions[b.decisions["unit"] == unit] if not b.decisions.empty else pd.DataFrame()
            if not d.empty:
                r0 = d.iloc[0]
                reasons = r0.get("reasons")
                reasons = "-" if (reasons is None or (isinstance(reasons, float) and pd.isna(reasons)) or str(reasons).strip() == "") else str(reasons)
                tops = r0.get("top_sensors")
                tops = "" if (tops is None or (isinstance(tops, float) and pd.isna(tops))) else f" · top deviations `{tops}`"
                st.markdown(f"**Latest decision:** `{r0['severity']}` → `{r0['action']}` · rules `{r0['rules']}` · escalation `{reasons}` · "
                            f"input quality flag `{r0.get('quality_flag', '-')}` (imputed {float(r0.get('imputed_frac', 0.0) or 0.0):.0%}) · fleet drift `{r0.get('drift_flag', '-')}` · "
                            f"true RUL (capped) `{r0.get('rul_true_capped', '-')}`{tops}")
            s = b.stream[b.stream["unit"] == unit] if not b.stream.empty else pd.DataFrame()
            if not s.empty:
                st.markdown("Stream replay decisions (cycle by cycle):")
                scols = [c for c in ["cycle", "point", "lower", "upper", "anomaly_score", "anomaly_flag", "quality_flag", "imputed_frac", "severity", "action", "escalate", "reasons", "order_event"] if c in s.columns]
                st.dataframe(s[scols], width='stretch', height=250)

    with tab_orders:
        if b.orders:
            st.dataframe(pd.DataFrame(b.orders), width='stretch')
        else:
            st.info("No open work orders.")

    with tab_model:
        st.subheader("Model")
        keys = ["hgbr_rmse_capped", "hgbr_rmse_raw", "hgbr_phm08", "cqr_point_rmse_capped", "picp_test_capped", "picp_test_raw", "mpiw_test", "conformal_qhat", "n_features", "elapsed_s"]
        st.json({k: m.get(k) for k in keys})
        st.caption(m.get("phm08_convention", ""))
        st.subheader("Conformal calibration")
        st.json({k: b.conformal.get(k) for k in ["alpha", "qhat", "n_calibration_rows", "truncations_per_engine", "assumption"]})
        st.subheader("Drift and input quality (test window vs training reference)")
        st.json({"drift": {k: v for k, v in b.drift.get("test_window", {}).items() if k != "per_feature"}, "quality": b.drift.get("quality", {})})
        if m.get("decision_outcomes_test"):
            st.subheader("Agent decisions vs true RUL (official test engines)")
            oc = m["decision_outcomes_test"]
            st.dataframe(pd.DataFrame(oc.get("counts", {})).T, width='stretch')
            st.json({k: oc.get(k) for k in ["n", "lower_bound_above_truth_rate", "serious_truth_missed_rate", "confident_order_on_healthy_rate", "confident_order_on_healthy_count", "anomaly_flag_rate_by_band"]})
        if b.retrain_log:
            st.subheader("Retraining log (gate decisions; registered model `sentinelloop-" + subset + "-gated`)")
            gate_rows = [r for r in b.retrain_log if r.get("scenario") != "C_drift_trigger"]
            drift_rows = [r for r in b.retrain_log if r.get("scenario") == "C_drift_trigger"]
            if gate_rows:
                gcols = [c for c in ["run", "scenario", "expected", "decision", "as_expected", "champion_rmse", "challenger_rmse", "champion_picp", "challenger_picp",
                                     "champion_late_rate", "challenger_late_rate", "late_threshold", "reasons", "champion_alias_version", "ts"] if any(c in r for r in gate_rows)]
                st.dataframe(pd.DataFrame(gate_rows)[gcols], width='stretch')
            if drift_rows:
                st.caption("Drift trigger checks (false alarms on clean windows, alarms on regime shift and sensor bias)")
                st.dataframe(pd.DataFrame(drift_rows)[[c for c in ["run", "false_alarms_in_20_clean_windows", "regime_shift_alarm", "bias_alarm", "bias_share"] if any(c in r for r in drift_rows)]], width='stretch')

    with tab_exp:
        summaries = viewdata.load_experiment_summaries(args.experiments_dir)
        if not summaries:
            st.info("No experiment summaries yet (experiments/results/<exp>/summary.json).")
        only_subset = st.checkbox(f"Show only rows for {subset}", value=True)

        def _show(label, rows):
            if isinstance(rows, dict):
                rows = [rows] if all(not isinstance(v, (dict, list)) for v in rows.values()) else [{"key": k, **(v if isinstance(v, dict) else {"value": v})} for k, v in rows.items()]
            if not isinstance(rows, list) or not rows:
                return
            df = pd.DataFrame(rows)
            if only_subset and "subset" in df.columns:
                df = df[df["subset"] == subset]
            if len(df):
                st.caption(label)
                st.dataframe(df, width='stretch')

        for name, s in summaries.items():
            st.subheader(name)
            st.caption(s.get("conclusion", ""))
            if s.get("table"):
                _show("results", s["table"])
            for extra in ("frontier", "by_fault", "replay"):
                if s.get(extra):
                    _show(extra, s[extra])

    with tab_audit:
        log_path = Path(args.out_dir) / "audit" / f"decisions_{subset}.jsonl"
        st.markdown(f"Audit log: `{log_path}` · records: **{len(b.audit)}**")
        if log_path.exists():
            if st.button("Verify hash chain and re-derive every decision"):
                rep = audit.replay_check(log_path)
                st.json(rep)
            if b.audit:
                st.dataframe(pd.DataFrame([{k: r.get(k) for k in ["seq", "ts", "unit", "cycle", "severity", "action", "escalate_to_human", "escalation_reasons", "rules_fired", "model_version", "hash"]} for r in b.audit[-200:]]), width='stretch', height=400)


if __name__ == "__main__":
    main()
