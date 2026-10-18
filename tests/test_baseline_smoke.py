import json

import pytest

from sentinelloop import baseline
from conftest import DATA_RAW, ROOT


@pytest.mark.slow
def test_e0_baseline_runs_end_to_end_on_fd001(tmp_path):
    if not (DATA_RAW / "train_FD001.txt").exists():
        pytest.skip("real data not present")
    result = baseline.run_baseline("FD001", data_dir=DATA_RAW, out_dir=tmp_path, config_dir=ROOT / "configs", fast=True)
    m = result["metrics"]
    for key in ("hgbr_rmse_capped", "hgbr_rmse_raw", "hgbr_phm08", "naive_rmse_capped", "cv_rmse_all_rows", "cv_rmse_last_cycle_naive_protocol"):
        assert key in m
    assert m["hgbr_rmse_capped"] < m["naive_rmse_capped"]
    assert m["hgbr_rmse_capped"] < 25.0
    assert (tmp_path / "baseline" / "FD001" / "metrics.json").exists()
    assert (tmp_path / "baseline" / "FD001" / "predictions_test.csv").exists()
    saved = json.loads((tmp_path / "baseline" / "FD001" / "metrics.json").read_text())
    assert saved["phm08_convention"] == baseline.metrics.PHM08_CONVENTION
    assert saved["data_hashes"]["train"]
