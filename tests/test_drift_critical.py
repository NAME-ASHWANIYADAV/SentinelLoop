import numpy as np
import pandas as pd

from sentinelloop import drift


def _ref(n=2000, seed=0):
    rng = np.random.default_rng(seed)
    df = pd.DataFrame(rng.normal(0, 1, size=(n, 5)), columns=[f"f{i}" for i in range(5)])
    df["os1"] = rng.normal(0, 0.002, n)  # operating setting, nearly constant in a single-regime subset
    return df


def test_drift_in_a_critical_column_alone_raises_the_alarm():
    mon = drift.DriftMonitor.fit(_ref(seed=0), psi_threshold=0.2, share_threshold=0.3, critical_columns=["os1"])
    cur = _ref(n=300, seed=4)
    cur["os1"] = 20.0  # regime shift on the operating setting only
    rep = mon.check(cur)
    assert rep.alarm is True and "os1" in rep.drifted_features and rep.drift_share < 0.3
    assert rep.critical_drift == ["os1"]


def test_no_alarm_when_critical_column_is_stable():
    mon = drift.DriftMonitor.fit(_ref(seed=0), psi_threshold=0.2, share_threshold=0.3, critical_columns=["os1"])
    rep = mon.check(_ref(n=300, seed=9))
    assert rep.alarm is False and rep.critical_drift == []
