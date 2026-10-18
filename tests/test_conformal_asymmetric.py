import numpy as np

from sentinelloop import clean, conformal, features, metrics, targets
from conftest import make_synthetic_raw


def _frames(n_units, seed, cycles=(60, 80, 70, 90, 65, 75)):
    raw = make_synthetic_raw(n_units=n_units, cycles=cycles, degrade=True, seed=seed)
    state = clean.CleanState.fit(raw, n_regimes=1, std_threshold=1e-3)
    f = features.build_features(state.transform(clean.impute(raw)), columns=state.kept_sensors, window=10)
    f = targets.add_train_rul(f, cap=50)
    return f, features.feature_manifest(f)


def test_asymmetric_cqr_has_two_corrections_and_covers_near_nominal():
    train, cols = _frames(40, seed=0)
    test, _ = _frames(20, seed=11)
    m = conformal.fit_cqr(train, cols, alpha=0.1, calib_frac=0.3, seed=1, max_iter=80, learning_rate=0.1, max_leaf_nodes=15, asymmetric=True)
    assert m.asymmetric is True and m.qhat_lo >= 0 and m.qhat_hi >= 0
    _, lo, hi = m.predict(test[cols])
    assert (lo <= hi).all() and metrics.picp(test["rul"], lo, hi) >= 0.80
    assert m.metadata()["asymmetric"] is True


def test_symmetric_default_is_unchanged():
    train, cols = _frames(20, seed=0)
    m = conformal.fit_cqr(train, cols, alpha=0.1, calib_frac=0.3, seed=1, max_iter=40, learning_rate=0.1, max_leaf_nodes=15)
    assert m.asymmetric is False and m.qhat_lo == m.qhat == m.qhat_hi
