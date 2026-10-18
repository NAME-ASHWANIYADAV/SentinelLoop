import numpy as np
import pandas as pd

from sentinelloop import stress
from conftest import SENSORS, make_synthetic_raw


def test_inject_missing_hits_requested_fraction_and_returns_mask():
    df = make_synthetic_raw(n_units=3, cycles=(50, 50, 50), degrade=False)
    out, mask = stress.inject_missing(df, frac=0.2, columns=SENSORS, seed=0)
    assert abs(mask.values.mean() - 0.2) < 0.03
    assert out[SENSORS].isna().values.sum() == mask.values.sum()
    assert not df[SENSORS].isna().any().any()  # input untouched


def test_inject_noise_changes_only_targeted_rows():
    df = make_synthetic_raw(n_units=2, cycles=(30, 30), degrade=False)
    out, mask = stress.inject_noise(df, sigma_mult=3.0, columns=["s2", "s3"], units=[2], from_cycle=11, seed=0)
    assert np.allclose(out.loc[out.unit == 1, ["s2", "s3"]], df.loc[df.unit == 1, ["s2", "s3"]])
    assert not np.allclose(out.loc[(out.unit == 2) & (out.cycle >= 11), "s2"], df.loc[(df.unit == 2) & (df.cycle >= 11), "s2"])
    assert mask.loc[(df.unit == 2) & (df.cycle >= 11)].all() and not mask.loc[df.unit == 1].any()


def test_inject_bias_shifts_one_sensor_from_a_cycle_onward():
    df = make_synthetic_raw(n_units=1, cycles=(20,), degrade=False)
    out, mask = stress.inject_bias(df, sensor="s4", k_std=2.0, from_cycle=10, units=[1])
    sd = df["s4"].std()
    assert np.allclose(out.loc[out.cycle >= 10, "s4"] - df.loc[df.cycle >= 10, "s4"], 2.0 * sd)
    assert np.allclose(out.loc[out.cycle < 10, "s4"], df.loc[df.cycle < 10, "s4"])
    assert mask.sum() == 11


def test_inject_regime_shift_replaces_operating_settings():
    df = make_synthetic_raw(n_units=1, cycles=(10,), degrade=False)
    out, mask = stress.inject_regime_shift(df, settings=(35.0, 0.84, 100.0), units=[1], from_cycle=1)
    assert (out["os1"] == 35.0).all() and (out["os2"] == 0.84).all() and mask.all()
