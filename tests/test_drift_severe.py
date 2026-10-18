import numpy as np
import pandas as pd

from sentinelloop import drift


def _ref(n=2000, seed=0, k=12):
    rng = np.random.default_rng(seed)
    return pd.DataFrame(rng.normal(0, 1, size=(n, k)), columns=[f"f{i}" for i in range(k)])


def test_single_feature_with_severe_psi_raises_alarm_even_when_share_is_small():
    mon = drift.DriftMonitor.fit(_ref(seed=0), psi_threshold=0.2, share_threshold=0.3, severe_psi_threshold=1.0)
    cur = _ref(n=400, seed=3)
    cur["f0"] += 3.0  # one feature shifted by 3 sigma (a biased sensor)
    rep = mon.check(cur)
    assert rep.drift_share < 0.3 and rep.alarm is True and rep.severe_drift == ["f0"]


def test_mild_single_feature_shift_does_not_raise_alarm():
    mon = drift.DriftMonitor.fit(_ref(seed=0), psi_threshold=0.2, share_threshold=0.3, severe_psi_threshold=1.0)
    cur = _ref(n=400, seed=3)
    cur["f0"] += 0.3
    rep = mon.check(cur)
    assert rep.alarm is False and rep.severe_drift == []
