import json

import pytest

from sentinelloop import audit, pipeline
from conftest import DATA_RAW, ROOT


@pytest.mark.slow
def test_run_pipeline_end_to_end_on_fd001_fast(tmp_path):
    if not (DATA_RAW / "train_FD001.txt").exists():
        pytest.skip("real data not present")
    res = pipeline.run("FD001", data_dir=DATA_RAW, out_dir=tmp_path, config_dir=ROOT / "configs", fast=True, stream_units=3, mlflow=True)
    out = tmp_path / "FD001"
    for f in ("metrics.json", "predictions_test.csv", "conformal.json", "anomaly.json", "drift_reference.json",
              "decisions_test.csv", "work_orders.json", "clean_state.pkl", "model_cqr.pkl"):
        assert (out / f).exists(), f
    m = json.loads((out / "metrics.json").read_text())
    assert 0.5 <= m["picp_test_capped"] <= 1.0 and m["mpiw_test"] > 0
    assert m["hgbr_rmse_capped"] < 25
    log = audit.AuditLog(tmp_path / "audit" / "decisions_FD001.jsonl")
    assert log.verify_chain() and log.n > 0
    chk = audit.replay_check_all(tmp_path)
    assert chk["mismatches"] == 0 and chk["n"] == log.n
    orders = json.loads((out / "work_orders.json").read_text())
    assert isinstance(orders, list)
    assert m["mlflow_run_id"] and m["model_alias"] == "champion"
    assert (tmp_path / "sentinelloop.db").exists()


@pytest.mark.slow
def test_stream_replay_reproduces_batch_decisions_bitwise_on_real_data(tmp_path):
    """The stream path (CleanStream -> FeatureStream -> CQR -> agent) must give the same predictions, flags and
    severities as the batch path for the same engine-cycles, and must record escalation reasons and input quality."""
    import pandas as pd
    if not (DATA_RAW / "train_FD001.txt").exists():
        pytest.skip("real data not present")
    pipeline.run("FD001", data_dir=DATA_RAW, out_dir=tmp_path, config_dir=ROOT / "configs", fast=True, stream_units=2, mlflow=False)
    out = tmp_path / "FD001"
    s = pd.read_csv(out / "decisions_stream.csv")
    p = pd.read_csv(out / "predictions_test_all_cycles.csv")
    j = s.merge(p, on=["unit", "cycle"], suffixes=("_s", "_b"))
    assert len(j) == len(s) > 50     # FD001 test engines 1 and 2 have 31 + 49 cycles
    for c in ("point", "lower", "upper", "anomaly_score"):
        assert (j[f"{c}_s"] == j[f"{c}_b"]).all(), f"{c} differs between stream and batch"
    assert (j["anomaly_flag_s"] == j["anomaly_flag_b"]).all()
    assert "reasons" in s.columns and "imputed_frac" in s.columns and "quality_flag" in s.columns
    d = pd.read_csv(out / "decisions_test.csv")
    last = s.sort_values("cycle").groupby("unit").tail(1).set_index("unit")
    for u, row in last.iterrows():
        b = d[d["unit"] == u].iloc[0]
        assert row["severity"] == b["severity"] and bool(row["escalate"]) == bool(b["escalate"])
    for c in ("imputed_frac", "quality_flag", "drift_flag"):
        assert c in d.columns
    m = json.loads((out / "metrics.json").read_text())
    assert "decision_outcomes_test" in m and "counts" in m["decision_outcomes_test"]
    orders = json.loads((out / "work_orders.json").read_text())
    assert orders and all("action" in o and "due_by_cycle" in o and "top_sensors" in o for o in orders)


def test_stream_quality_flags_a_window_with_too_many_imputed_values():
    import pandas as pd
    from sentinelloop import drift
    rng = __import__("numpy").random.default_rng(0)
    ref = pd.DataFrame({"a": rng.normal(size=400), "b": rng.normal(size=400), "os1": rng.normal(size=400)})
    mon = drift.DriftMonitor.fit(ref, psi_threshold=0.2, share_threshold=0.3, seed=0, critical_columns=["os1"], range_ref=ref)
    cfg = {"agent": {"quality_max_imputed_frac": 0.10, "quality_max_out_of_range_frac": 0.05, "quality_max_critical_out_of_range_frac": 0.5}}
    q = pipeline.StreamQuality(mon, ["a", "b", "os1"], window=5, n_sensors=2, cfg=cfg)
    clean_rows = [{"unit": 1, "a": 0.1, "b": -0.2, "os1": 0.0, "n_imputed": 0} for _ in range(5)]
    for r in clean_rows:
        res = q.update(r)
    assert res["flag"] is False and res["imputed_frac"] == 0.0
    for _ in range(5):
        res = q.update({"unit": 1, "a": 0.1, "b": -0.2, "os1": 0.0, "n_imputed": 1})   # 1 of 2 sensors imputed -> 50%
    assert res["flag"] is True and res["imputed_frac"] == pytest.approx(0.5)
    res2 = q.update({"unit": 2, "a": 0.1, "b": -0.2, "os1": 9.0, "n_imputed": 0})        # another unit; critical setting far out of range
    assert res2["critical_out_of_range_frac"] == 1.0 and res2["flag"] is True
