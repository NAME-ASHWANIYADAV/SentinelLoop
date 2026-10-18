import numpy as np
import pandas as pd

from sentinelloop import drift


def _ref(n=2000, seed=0):
    rng = np.random.default_rng(seed)
    df = pd.DataFrame(rng.normal(0, 1, size=(n, 4)), columns=["f0", "f1", "f2", "f3"])
    df["os1"] = rng.normal(0, 0.002, n)
    return df


def test_range_reference_can_be_wider_than_the_psi_reference():
    full = _ref(seed=0)
    early = full.iloc[:200].copy()
    early[["f0", "f1", "f2", "f3"]] *= 0.3  # a narrow early-life slice
    mon = drift.DriftMonitor.fit(early, psi_threshold=0.2, share_threshold=0.3, critical_columns=["os1"], range_ref=full)
    late_like = _ref(n=100, seed=7)  # values from the full distribution, outside the narrow slice but inside the full range
    q = mon.quality(late_like)
    assert q["out_of_range_frac"] < 0.02
    assert mon.ref_max["f0"] >= full["f0"].max() - 1e-9


def test_quality_reports_critical_out_of_range_fraction_separately():
    full = _ref(seed=0)
    mon = drift.DriftMonitor.fit(full, psi_threshold=0.2, share_threshold=0.3, critical_columns=["os1"], range_ref=full)
    cur = _ref(n=50, seed=3)
    cur["os1"] = 35.0  # operating setting far outside its range
    q = mon.quality(cur)
    assert q["critical_out_of_range_frac"] == 1.0
    assert q["out_of_range_frac"] < 0.3  # only 1 of 5 columns, so the pooled fraction stays small
    clean = _ref(n=50, seed=4)
    assert mon.quality(clean)["critical_out_of_range_frac"] == 0.0
