import pytest
import numpy as np
import pandas as pd

from sentinelloop import evaluate
from conftest import make_synthetic_raw


def test_last_cycle_rows_selects_max_cycle_per_unit():
    df = make_synthetic_raw(n_units=3, cycles=(5, 7, 6), degrade=False)
    last = evaluate.last_cycle_rows(df)
    assert list(last.unit) == [1, 2, 3]
    assert list(last.cycle) == [5, 7, 6]


def test_engine_folds_keep_units_separate():
    df = make_synthetic_raw(n_units=10, cycles=(8,), degrade=False)
    for tr_idx, va_idx in evaluate.engine_folds(df, n_folds=5, seed=0):
        tr_units = set(df.iloc[tr_idx].unit)
        va_units = set(df.iloc[va_idx].unit)
        assert tr_units.isdisjoint(va_units)
        assert tr_units | va_units == set(range(1, 11))


def test_random_truncation_keeps_a_prefix_of_each_engine():
    df = make_synthetic_raw(n_units=4, cycles=(30, 40, 25, 35), degrade=False)
    trunc = evaluate.random_truncate(df, n_per_engine=2, seed=1, min_cycles=5)
    assert set(trunc.columns) >= set(df.columns) | {"trunc_id"}
    for (u, t), g in trunc.groupby(["unit", "trunc_id"]):
        n = len(g)
        orig = df[df.unit == u].head(n)
        assert list(g.cycle) == list(range(1, n + 1))
        assert np.allclose(g["s2"].values, orig["s2"].values)
        assert 5 <= n <= len(df[df.unit == u])


def test_decision_outcomes_cross_tabulates_severity_against_true_rul_bands():
    dec = pd.DataFrame({"severity": ["CRITICAL", "CRITICAL", "HIGH", "NONE", "MEDIUM", "NONE"],
                        "escalate": [False, True, False, False, False, False],
                        "rul_lower": [5.0, 8.0, 20.0, 80.0, 40.0, 90.0],
                        "rul_true_capped": [6.0, 30.0, 22.0, 100.0, 45.0, 60.0],
                        "anomaly_flag": [True, False, True, False, False, False]})
    out = evaluate.decision_outcomes(dec, t_critical=10, t_high=25, t_medium=50)
    assert out["counts"]["CRITICAL"]["<=10"] == 1 and out["counts"]["CRITICAL"]["26-50"] == 1
    assert out["counts"]["NONE"][">50"] == 2
    assert out["lower_bound_above_truth_rate"] == pytest.approx(1 / 6)      # engine 6: lower 90 > true 60
    assert out["serious_truth_missed_rate"] == pytest.approx(0.0)           # every true RUL <= 25 got HIGH/CRITICAL
    assert out["confident_order_on_healthy_rate"] == pytest.approx(0.0)     # no non-escalated order with true RUL > 50
    assert out["anomaly_flag_rate_by_band"]["<=25"] == pytest.approx(1.0) and out["anomaly_flag_rate_by_band"][">50"] == 0.0
