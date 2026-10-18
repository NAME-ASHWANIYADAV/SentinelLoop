import numpy as np

from sentinelloop import anomaly, clean, features, targets
from conftest import make_synthetic_raw


def _frames(n_units, seed):
    raw = make_synthetic_raw(n_units=n_units, cycles=(80, 100, 90), degrade=True, seed=seed)
    state = clean.CleanState.fit(raw, n_regimes=1, std_threshold=1e-3)
    f = features.build_features(state.transform(clean.impute(raw)), columns=state.kept_sensors, window=10)
    f = targets.add_train_rul(f, cap=125)
    return f, features.feature_manifest(f)


def test_detector_is_fit_on_healthy_phase_and_flags_late_life_more_often():
    train, cols = _frames(9, seed=0)
    det = anomaly.AnomalyDetector.fit(train, cols, healthy_frac=0.4, threshold_pct=99.0, seed=0)
    test, _ = _frames(3, seed=5)
    scores = det.score(test[cols])
    flags = scores > det.threshold
    early = test["cycle"] <= test.groupby("unit")["cycle"].transform("max") * 0.3
    late = test["cycle"] >= test.groupby("unit")["cycle"].transform("max") * 0.9
    assert flags[late.to_numpy()].mean() > flags[early.to_numpy()].mean()
    assert flags[early.to_numpy()].mean() <= 0.10


def test_sustained_flag_requires_k_consecutive_exceedances():
    raw = np.array([False, True, False, True, True, True, False, True, True, True, True])
    out = anomaly.sustained(raw, k=3)
    assert list(out) == [False, False, False, False, False, True, False, False, False, True, True]


def test_sustained_flag_is_computed_per_unit():
    import pandas as pd
    df = pd.DataFrame({"unit": [1, 1, 1, 2, 2, 2], "cycle": [1, 2, 3, 1, 2, 3], "exceed": [True, True, True, True, True, False]})
    out = anomaly.sustained_per_unit(df, "exceed", k=3)
    assert list(out) == [False, False, True, False, False, False]
