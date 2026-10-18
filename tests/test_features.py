import numpy as np
import pandas as pd

from sentinelloop import features
from conftest import make_synthetic_raw


def _frame(n=40):
    df = make_synthetic_raw(n_units=1, cycles=(n,), degrade=True)
    df["regime"] = 0
    return df


def test_rolling_features_are_causal():
    df = _frame()
    a = features.build_features(df, columns=["s2", "s3"], window=5)
    df2 = df.copy()
    df2.loc[df2.cycle >= 30, ["s2", "s3"]] += 1000.0
    b = features.build_features(df2, columns=["s2", "s3"], window=5)
    cols = [c for c in a.columns if c.endswith(("_rm", "_rs", "_slope"))]
    assert np.allclose(a.loc[a.cycle < 30, cols].values, b.loc[b.cycle < 30, cols].values)


def test_rolling_slope_matches_polyfit_on_full_window():
    df = _frame()
    out = features.build_features(df, columns=["s2"], window=5)
    y = df["s2"].values
    for pos in (4, 10, 39):  # 0-based positions with a full window available
        expected = np.polyfit(np.arange(5), y[pos - 4: pos + 1], 1)[0]
        assert abs(out.loc[pos, "s2_slope"] - expected) < 1e-9


def test_rolling_mean_and_std_match_pandas_with_min_periods_one():
    df = _frame()
    out = features.build_features(df, columns=["s2"], window=5)
    exp_mean = df["s2"].rolling(5, min_periods=1).mean()
    exp_std = df["s2"].rolling(5, min_periods=1).std().fillna(0.0)
    assert np.allclose(out["s2_rm"], exp_mean)
    assert np.allclose(out["s2_rs"], exp_std)


def test_features_are_computed_per_unit_not_across_units():
    df = make_synthetic_raw(n_units=2, cycles=(10, 10), degrade=False)
    df["regime"] = 0
    df.loc[df.unit == 1, "s2"] = 0.0
    df.loc[df.unit == 2, "s2"] = 100.0
    out = features.build_features(df, columns=["s2"], window=5)
    assert (out.loc[out.unit == 2, "s2_rm"] == 100.0).all()  # never contaminated by unit 1's zeros


def test_feature_manifest_lists_model_inputs_only():
    df = _frame()
    out = features.build_features(df, columns=["s2"], window=5)
    manifest = features.feature_manifest(out)
    assert "s2_rm" in manifest and "s2_slope" in manifest and "cycle" in manifest and "regime" in manifest
    for forbidden in ("unit", "rul", "rul_raw", "n_imputed"):
        assert forbidden not in manifest
