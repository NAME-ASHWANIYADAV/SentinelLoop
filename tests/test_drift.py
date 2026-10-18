import numpy as np
import pandas as pd

from sentinelloop import drift


def _ref(n=2000, seed=0, k=6):
    rng = np.random.default_rng(seed)
    return pd.DataFrame(rng.normal(0, 1, size=(n, k)), columns=[f"f{i}" for i in range(k)])


def test_psi_is_near_zero_for_same_distribution_and_large_for_shift():
    rng = np.random.default_rng(1)
    a = rng.normal(0, 1, 5000)
    b = rng.normal(0, 1, 5000)
    c = rng.normal(2.0, 1, 5000)
    assert drift.psi(a, b) < 0.05
    assert drift.psi(a, c) > 0.5


def test_monitor_does_not_alarm_on_same_distribution():
    mon = drift.DriftMonitor.fit(_ref(seed=0), psi_threshold=0.2, share_threshold=0.3)
    rep = mon.check(_ref(n=500, seed=99))
    assert rep.alarm is False and rep.drift_share < 0.3


def test_monitor_alarms_when_most_features_shift():
    mon = drift.DriftMonitor.fit(_ref(seed=0), psi_threshold=0.2, share_threshold=0.3)
    cur = _ref(n=500, seed=5)
    cur[["f0", "f1", "f2", "f3"]] += 3.0
    rep = mon.check(cur)
    assert rep.alarm is True and rep.drift_share >= 4 / 6
    assert set(rep.drifted_features) >= {"f0", "f1", "f2", "f3"}


def test_quality_check_reports_missing_and_out_of_range_fractions():
    ref = _ref(seed=0)
    mon = drift.DriftMonitor.fit(ref, psi_threshold=0.2, share_threshold=0.3)
    cur = _ref(n=100, seed=3)
    cur.loc[:9, "f0"] = np.nan
    cur.loc[10:19, "f1"] = 50.0  # far outside the reference range
    q = mon.quality(cur)
    assert abs(q["missing_frac"] - 10 / 600) < 1e-9
    assert q["out_of_range_frac"] >= 10 / 600 - 1e-9
