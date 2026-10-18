"""The retraining flow: validation metrics for the gate and the end-to-end `retrain` command."""
import json

import numpy as np
import pandas as pd
import pytest

from sentinelloop import agent, retrain
from conftest import DATA_RAW, ROOT


class _ConstantInterval:
    """Stand-in for a CQR model: point = lower + 10, upper = lower + 30, lower given per row by a column."""

    def predict(self, X):
        lower = X["lower_src"].to_numpy(dtype=float)
        return lower + 10.0, lower, lower + 30.0


def _frame():
    rows = []
    for u in (1, 2):
        for c in range(1, 61):
            rul_raw = 60 - c
            rows.append({"unit": u, "cycle": c, "lower_src": float(rul_raw - 4), "rul": float(min(rul_raw, 125)), "rul_raw": float(rul_raw)})
    return pd.DataFrame(rows)


def test_validation_metrics_report_late_rate_at_the_critical_threshold():
    thr = agent.Thresholds(t_critical=10, t_high=25, t_medium=50, max_width=60, quality_max_imputed_frac=0.1)
    m = retrain.validation_metrics(_ConstantInterval(), _frame(), ["lower_src"], thr, seed=0, rows_per_engine=5)
    for k in ("rmse", "picp", "mpiw", "late_rate", "late_rate_high", "late_threshold"):
        assert k in m
    assert m["late_threshold"] == 10
    assert m["mpiw"] == pytest.approx(30.0)
    # lower bound = true RUL - 4: the first cycle with lower <= 10 has true RUL 14 (not late at either threshold)
    assert m["late_rate"] == 0.0 and m["late_rate_high"] == 0.0


def test_split_units_is_deterministic_and_disjoint():
    val, champ, new = retrain.split_units(range(1, 101), seed=42)
    assert len(val) == 20 and len(champ) == 50 and len(new) == 30
    assert set(val).isdisjoint(champ) and set(champ).isdisjoint(new) and set(val).isdisjoint(new)
    assert (val, champ, new) == retrain.split_units(range(1, 101), seed=42)


@pytest.mark.slow
def test_retrain_command_gates_a_simulated_new_data_file_end_to_end(tmp_path):
    if not (DATA_RAW / "train_FD001.txt").exists():
        pytest.skip("real data not present")
    res = retrain.run_retrain("FD001", data_dir=DATA_RAW, out_dir=tmp_path, config_dir=ROOT / "configs", simulate_new_data=True, fast=True, log=lambda m: None)
    assert res["decision"] in ("PROMOTE", "REJECT") and res["reasons"] is not None
    assert res["champion_metrics"]["rmse"] > 0 and res["challenger_metrics"]["rmse"] > 0
    log = json.loads((tmp_path / "FD001" / "retrain_log.json").read_text(encoding="utf-8"))
    assert log[-1]["run"] == "cli" and log[-1]["decision"] == res["decision"] and "checks" in log[-1]
    assert (tmp_path / "FD001" / "gated_champion.pkl").exists()
    assert (tmp_path / "incoming" / "FD001_new_engines.txt").exists()
    # a second invocation on the same file must find the stored champion and skip the drift gate when asked to
    res2 = retrain.run_retrain("FD001", data_dir=DATA_RAW, out_dir=tmp_path, config_dir=ROOT / "configs", new_data=tmp_path / "incoming" / "FD001_new_engines.txt",
                               fast=True, only_if_drift=True, log=lambda m: None)
    assert res2["decision"] == "SKIPPED" and "drift" in res2["reasons"][0]
