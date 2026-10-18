import json

import pandas as pd

from sentinelloop import viewdata


def _fake_artifacts(root):
    out = root / "FD001"
    out.mkdir(parents=True)
    (out / "metrics.json").write_text(json.dumps({"subset": "FD001", "hgbr_rmse_capped": 13.5, "picp_test_capped": 0.9, "mlflow_run_id": "abc"}))
    pd.DataFrame({"unit": [1, 1, 2], "cycle": [1, 2, 1], "point": [50, 48, 70], "lower": [40, 38, 60], "upper": [60, 58, 80],
                  "point_all_engines": [50, 48, 70], "anomaly_score": [0.1, 0.2, 0.1], "anomaly_flag": [False, False, False]}).to_csv(out / "predictions_test_all_cycles.csv", index=False)
    pd.DataFrame({"unit": [1, 2], "cycle": [2, 1], "severity": ["MEDIUM", "NONE"], "action": ["PLAN_MAINTENANCE", "NONE"], "escalate": [False, False],
                  "reasons": ["", ""], "rules": ["R_MEDIUM", "R_NONE"], "rul_point": [48, 70], "rul_lower": [38, 60], "rul_upper": [58, 80],
                  "rul_true_capped": [45, 72], "anomaly_score": [0.2, 0.1], "anomaly_flag": [False, False], "order_event": ["none", "none"], "seq": [0, 1],
                  "rul_true_raw": [45, 72]}).to_csv(out / "decisions_test.csv", index=False)
    (out / "work_orders.json").write_text(json.dumps([{"id": 1, "unit": 1, "type": "MAINTENANCE", "severity": "HIGH", "status": "OPEN", "created_cycle": 2, "updated_cycle": 2, "reasons": [], "model_version": "abc", "n_decisions": 1, "mode": "batch"}]))
    (out / "drift_reference.json").write_text(json.dumps({"test_window": {"drift_share": 0.0, "alarm": False, "per_feature": {}, "drifted_features": [], "n_rows": 3}, "quality": {"missing_frac": 0.0, "out_of_range_frac": 0.0, "n_rows": 3}}))
    (root / "audit").mkdir()
    (root / "audit" / "decisions.jsonl").write_text(json.dumps({"seq": 0, "unit": 1, "cycle": 2, "severity": "MEDIUM", "hash": "x", "prev_hash": "0" * 64}) + "\n")


def test_available_subsets_and_bundle_loading(tmp_path):
    _fake_artifacts(tmp_path)
    assert viewdata.available_subsets(tmp_path) == ["FD001"]
    b = viewdata.load_bundle(tmp_path, "FD001")
    assert b.metrics["hgbr_rmse_capped"] == 13.5
    assert len(b.predictions) == 3 and len(b.decisions) == 2 and len(b.orders) == 1
    assert b.drift["test_window"]["alarm"] is False
    assert len(b.audit) == 1


def test_fleet_table_summarises_latest_decision_per_unit(tmp_path):
    _fake_artifacts(tmp_path)
    b = viewdata.load_bundle(tmp_path, "FD001")
    fleet = viewdata.fleet_table(b)
    assert list(fleet.columns[:4]) == ["unit", "severity", "rul_lower", "rul_point"]
    assert fleet.iloc[0]["severity"] == "MEDIUM"  # sorted by most severe first


def test_missing_subset_gives_empty_bundle(tmp_path):
    b = viewdata.load_bundle(tmp_path, "FD002")
    assert b.metrics == {} and b.predictions.empty and b.orders == []
