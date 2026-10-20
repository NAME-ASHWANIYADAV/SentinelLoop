"""Dashboard presentation layer: formatting helpers, plain-language explanations, and every page rendering headlessly."""
import json
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from sentinelloop.ui import format as fmt

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "deploy" / "dashboard_data"
THR = {"t_critical": 10.0, "t_high": 25.0, "t_medium": 50.0, "max_width": 80.34}


def test_numbers_keep_their_precision_and_missing_values_show_a_dash():
    assert fmt.fmt_num(14.1666, 2) == "14.17"
    assert fmt.fmt_num(64.2, 1, "cycles") == "64.2 cycles"
    assert fmt.fmt_num(float("nan")) == "–" and fmt.fmt_num(None) == "–"
    assert fmt.fmt_pct(0.94, 1) == "94.0%" and fmt.fmt_pct(None) == "–"
    assert fmt.short_id("c5135791fb1c4447918dd71a3fa00c3e", 8) == "c5135791"


def test_lists_are_read_from_json_lists_and_csv_strings():
    assert fmt.split_list("R_CRITICAL|R_ESC_WIDTH") == ["R_CRITICAL", "R_ESC_WIDTH"]
    assert fmt.split_list(["s20", "s8_rs"]) == ["s20", "s8_rs"]
    assert fmt.split_list(float("nan")) == [] and fmt.split_list("") == []


def test_explanations_come_only_from_the_rules_that_fired_with_the_thresholds_in_force():
    out = fmt.explain("R_ESC_WIDTH|R_CRITICAL", THR)
    assert [r for r, _ in out] == ["R_CRITICAL", "R_ESC_WIDTH"]           # severity rule first, escalation after
    assert "10 cycles" in out[0][1] and "80 cycles" in out[1][1]
    assert fmt.explain("", THR) == []
    assert fmt.rule_sentence("R_UNKNOWN", THR) == "R_UNKNOWN"              # an unknown rule is shown as it is, never invented


def test_priority_table_lists_only_engines_needing_attention_most_urgent_first():
    fleet = pd.DataFrame({
        "unit": [1, 2, 3, 4], "severity": ["NONE", "MEDIUM", "CRITICAL", "NONE"], "action": ["NONE", "PLAN_MAINTENANCE", "INSPECT", "INSPECT"],
        "escalate": [False, False, True, True], "reasons": ["", "", "insufficient_evidence", "data_quality"],
        "rul_lower": [90.0, 40.0, 7.0, 95.0], "rul_point": [110.0, 60.0, 16.0, 115.0], "rul_upper": [125.0, 90.0, 117.0, 125.0]})
    t = fmt.priority_table(fleet)
    assert t["Engine"].tolist() == [3, 2, 4]                                # healthy engine 1 dropped; escalated healthy engine 4 kept
    assert t.loc[0, "Priority"].endswith("Critical") and t.loc[0, "Human review"] == "Yes"
    assert t.loc[0, "Why"] == "Prediction interval too wide" and t.loc[0, "Recommended action"] == "Human inspection"
    assert t.loc[0, "Interval width"] == 110.0
    assert fmt.priority_table(pd.DataFrame()).empty


def test_experiment_verdicts_are_read_from_the_written_conclusion():
    assert fmt.verdict("Pre-registered criterion (>=3/4): NOT SUPPORTED.") == "Not supported"
    assert fmt.verdict("H5 ... criterion (at least one): SUPPORTED.") == "Supported"
    assert fmt.verdict("Ablation table: compare with 'full'.") == "No verdict stated"


SCRIPT = """
import sys
sys.path.insert(0, {src!r})
from sentinelloop import dashboard
ctx = dashboard.context({out!r}, {exp!r}, {subset!r})
dashboard.render({page!r}, ctx)
"""


def _run(page, out, exp, subset="FD001"):
    at = AppTest.from_string(SCRIPT.format(src=str(ROOT / "src"), out=str(out), exp=str(exp), subset=subset, page=page), default_timeout=120)
    return at.run()


@pytest.mark.skipif(not SNAPSHOT.exists(), reason="dashboard snapshot not present")
@pytest.mark.parametrize("page", ["fleet", "engine", "orders", "model", "experiments", "audit"])
def test_every_page_renders_on_the_committed_snapshot_without_an_error(page):
    at = _run(page, SNAPSHOT, ROOT / "experiments" / "results")
    assert not at.exception, [e.value for e in at.exception]
    text = " ".join(m.value for m in at.markdown)
    assert "could not be displayed" not in text                           # the page's own error panel did not fire
    assert "sl-header" in text


@pytest.mark.skipif(not SNAPSHOT.exists(), reason="dashboard snapshot not present")
def test_fleet_kpis_are_the_stored_metrics():
    m = json.loads((SNAPSHOT / "FD001" / "metrics.json").read_text(encoding="utf-8"))
    text = " ".join(x.value for x in _run("fleet", SNAPSHOT, ROOT / "experiments" / "results").markdown)
    assert f"{m['hgbr_rmse_capped']:.2f}" in text and f"{m['picp_test_capped'] * 100:.1f}%" in text
    assert f'<div class="value">{m["severity_counts_test"]["CRITICAL"]}</div>' in text
    assert "critical threshold" in text and "R_CRITICAL" in text          # the urgent engines are explained by their fired rules


@pytest.mark.skipif(not SNAPSHOT.exists(), reason="dashboard snapshot not present")
def test_audit_verification_reports_the_live_check():
    at = _run("audit", SNAPSHOT, ROOT / "experiments" / "results")
    at.button(key="audit_verify").click().run()
    text = " ".join(m.value for m in at.markdown)
    assert "Every record verified" in text and "0 mismatches" in text


@pytest.mark.parametrize("page", ["fleet", "engine", "orders", "model", "experiments", "audit"])
def test_every_page_shows_an_empty_state_when_there_is_no_data(tmp_path, page):
    at = _run(page, tmp_path / "nothing", tmp_path / "noexp")
    assert not at.exception, [e.value for e in at.exception]
    text = " ".join(m.value for m in at.markdown)
    assert "sl-empty" in text and "could not be displayed" not in text
