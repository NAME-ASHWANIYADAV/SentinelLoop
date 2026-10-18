import pickle

import numpy as np
import pandas as pd
import pytest

from sentinelloop import clean
from conftest import SENSORS, make_synthetic_raw


def test_impute_fills_within_unit_and_counts_imputed_values():
    df = make_synthetic_raw(n_units=2, cycles=(5, 5), degrade=False)
    df.loc[(df.unit == 1) & (df.cycle == 3), "s4"] = np.nan   # interior gap -> forward fill
    df.loc[(df.unit == 2) & (df.cycle == 1), "s5"] = np.nan   # leading gap -> back fill
    out = clean.impute(df)
    u1 = out[out.unit == 1].reset_index(drop=True)
    u2 = out[out.unit == 2].reset_index(drop=True)
    assert u1.loc[2, "s4"] == u1.loc[1, "s4"]            # forward-filled from cycle 2
    assert u2.loc[0, "s5"] == u2.loc[1, "s5"]            # back-filled from cycle 2
    assert list(u1["n_imputed"]) == [0, 0, 1, 0, 0]
    assert list(u2["n_imputed"]) == [1, 0, 0, 0, 0]
    assert not out[SENSORS].isna().any().any()


def test_impute_never_crosses_unit_boundary():
    df = make_synthetic_raw(n_units=2, cycles=(3, 3), degrade=False)
    df.loc[df.unit == 2, "s6"] = np.nan  # whole unit missing -> cannot be filled from unit 1
    out = clean.impute(df)
    assert out.loc[out.unit == 2, "s6"].isna().all()
    assert list(out.loc[out.unit == 2, "n_imputed"]) == [0, 0, 0]  # unfillable values are not counted as imputed
    assert out.loc[out.unit == 1, "s6"].notna().all()


def test_ema_is_causal():
    df = make_synthetic_raw(n_units=1, cycles=(12,), degrade=False)
    a = clean.ema_denoise(df, alpha=0.3, columns=["s2"])
    df2 = df.copy()
    df2.loc[df2.cycle >= 9, "s2"] += 1000.0
    b = clean.ema_denoise(df2, alpha=0.3, columns=["s2"])
    assert np.allclose(a.loc[a.cycle < 9, "s2"], b.loc[b.cycle < 9, "s2"])
    assert not np.allclose(a.loc[a.cycle >= 9, "s2"], b.loc[b.cycle >= 9, "s2"])


def test_ema_first_value_equals_raw_and_smooths_after():
    df = make_synthetic_raw(n_units=1, cycles=(3,), degrade=False)
    df["s2"] = [10.0, 20.0, 30.0]
    out = clean.ema_denoise(df, alpha=0.5, columns=["s2"])
    assert list(np.round(out["s2"], 6)) == [10.0, 15.0, 22.5]


def test_drop_list_is_computed_from_train_only():
    train = make_synthetic_raw(n_units=2, cycles=(20, 20), degrade=False)
    test = make_synthetic_raw(n_units=1, cycles=(20,), degrade=False, seed=1)
    test["s1"] = np.linspace(0, 100, len(test))  # varies in test but constant in train
    state = clean.CleanState.fit(train, n_regimes=1, std_threshold=1e-3)
    assert "s1" in state.dropped_sensors
    assert "s2" not in state.dropped_sensors
    out = state.transform(test)
    assert "s1" not in out.columns


def test_regime_scaler_is_fit_on_train_only_and_normalises_train():
    train = make_synthetic_raw(n_units=3, cycles=(30, 30, 30), degrade=False)
    train.loc[train.unit == 3, "os1"] += 20.0  # a second operating regime
    train.loc[train.unit == 3, SENSORS] += 50.0  # regime shifts all sensors
    state = clean.CleanState.fit(train, n_regimes=2, std_threshold=1e-3)
    assert state.n_regimes == 2
    out = state.transform(train)
    kept = [s for s in SENSORS if s not in state.dropped_sensors]
    for r in (0, 1):
        sub = out[out.regime == r]
        assert np.allclose(sub[kept].mean().values, 0.0, atol=1e-6)
    assert set(out.regime.unique()) == {0, 1}
    test = make_synthetic_raw(n_units=1, cycles=(10,), degrade=False, seed=5)
    test[SENSORS] += 50.0
    test["os1"] += 20.0
    out_t = state.transform(test)
    assert (out_t.regime == out[out.unit == 3].regime.iloc[0]).all()


def test_clean_state_pickle_roundtrip():
    train = make_synthetic_raw(n_units=2, cycles=(15, 15), degrade=False)
    state = clean.CleanState.fit(train, n_regimes=1, std_threshold=1e-3)
    state2 = pickle.loads(pickle.dumps(state))
    a = state.transform(train)
    b = state2.transform(train)
    pd.testing.assert_frame_equal(a, b)
