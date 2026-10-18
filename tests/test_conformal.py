import numpy as np

from sentinelloop import clean, conformal, features, metrics, targets
from conftest import make_synthetic_raw


def _frames(n_units, seed, cycles=(60, 80, 70, 90, 65)):
    raw = make_synthetic_raw(n_units=n_units, cycles=cycles, degrade=True, seed=seed)
    state = clean.CleanState.fit(raw, n_regimes=1, std_threshold=1e-3)
    f = features.build_features(state.transform(clean.impute(raw)), columns=state.kept_sensors, window=10)
    f = targets.add_train_rul(f, cap=50)
    return f, features.feature_manifest(f)


def test_calibration_engines_are_disjoint_from_training_engines():
    train, cols = _frames(20, seed=0)
    m = conformal.fit_cqr(train, cols, alpha=0.1, calib_frac=0.3, seed=1, max_iter=60, learning_rate=0.1, max_leaf_nodes=15)
    assert set(m.calibration_units).isdisjoint(set(m.training_units))
    assert set(m.calibration_units) | set(m.training_units) == set(train.unit.unique())
    assert len(m.calibration_units) == 6


def test_intervals_are_ordered_and_nonnegative():
    train, cols = _frames(20, seed=0)
    test, _ = _frames(5, seed=7)
    m = conformal.fit_cqr(train, cols, alpha=0.1, calib_frac=0.3, seed=1, max_iter=60, learning_rate=0.1, max_leaf_nodes=15)
    point, lo, hi = m.predict(test[cols])
    assert (lo <= hi).all() and (lo >= 0).all() and (point >= 0).all()
    assert m.qhat >= 0.0


def test_marginal_coverage_on_held_out_engines_is_near_nominal():
    train, cols = _frames(40, seed=0, cycles=(60, 80, 70, 90, 65, 75))
    test, _ = _frames(20, seed=11, cycles=(60, 80, 70, 90, 65, 75))
    m = conformal.fit_cqr(train, cols, alpha=0.1, calib_frac=0.3, seed=1, max_iter=80, learning_rate=0.1, max_leaf_nodes=15)
    _, lo, hi = m.predict(test[cols])
    cov = metrics.picp(test["rul"], lo, hi)
    assert cov >= 0.80, cov  # nominal 0.90; allow sampling slack on a small synthetic set


def test_cqr_state_records_alpha_and_is_json_serialisable():
    train, cols = _frames(12, seed=2)
    m = conformal.fit_cqr(train, cols, alpha=0.2, calib_frac=0.25, seed=1, max_iter=40, learning_rate=0.1, max_leaf_nodes=15)
    meta = m.metadata()
    assert meta["alpha"] == 0.2 and "qhat" in meta and "calibration_units" in meta and meta["n_calibration_rows"] > 0
    import json
    json.dumps(meta)
