import numpy as np
import pandas as pd

from sentinelloop import drift
from conftest import make_synthetic_raw


def test_early_life_rows_selects_the_age_matched_window():
    df = make_synthetic_raw(n_units=2, cycles=(100, 60), degrade=True)
    sub = drift.early_life_rows(df, warmup=20, max_cycle=50)
    assert sub["cycle"].min() == 20 and sub["cycle"].max() == 50
    assert set(sub["unit"]) == {1, 2}


def test_age_matched_monitoring_does_not_alarm_when_the_fleet_is_merely_younger():
    rng = np.random.default_rng(0)
    # reference: engines observed to failure (older rows degrade); current window: truncated early -> younger mix
    def fleet(n_units, max_len, seed):
        rows = []
        r = np.random.default_rng(seed)
        for u in range(n_units):
            n = int(r.integers(max_len // 2, max_len + 1))
            for c in range(1, n + 1):
                rows.append({"unit": u, "cycle": c, "f0": 0.5 * c / 100 + r.normal(0, 0.1), "f1": r.normal(0, 1)})
        return pd.DataFrame(rows)
    ref = fleet(60, 200, 1)
    cur = fleet(40, 60, 2)  # truncated young engines
    mon_all = drift.DriftMonitor.fit(ref[["f0", "f1"]], psi_threshold=0.2, share_threshold=0.3)
    naive = mon_all.check(cur[["f0", "f1"]])
    mon_age = drift.DriftMonitor.fit(drift.early_life_rows(ref, warmup=5, max_cycle=30)[["f0", "f1"]], psi_threshold=0.2, share_threshold=0.3)
    matched = mon_age.check(drift.early_life_rows(cur, warmup=5, max_cycle=30)[["f0", "f1"]])
    assert naive.per_feature["f0"] > matched.per_feature["f0"]
    assert matched.alarm is False
