import numpy as np

from sentinelloop import clean, features, metrics, models, targets
from conftest import SENSORS, make_synthetic_raw


def _prepare(n_units, seed):
    raw = make_synthetic_raw(n_units=n_units, cycles=(60, 80, 70, 90), degrade=True, seed=seed)
    state = clean.CleanState.fit(raw, n_regimes=1, std_threshold=1e-3)
    cleaned = state.transform(clean.impute(raw))
    feat = features.build_features(cleaned, columns=state.kept_sensors, window=10)
    feat = targets.add_train_rul(feat, cap=50)
    return feat, features.feature_manifest(feat)


def test_point_model_beats_naive_mean_on_synthetic_degradation():
    train, cols = _prepare(8, seed=0)
    test, _ = _prepare(4, seed=99)
    model = models.train_point_model(train[cols], train["rul"], max_iter=100, learning_rate=0.1, max_leaf_nodes=15, seed=0)
    pred = model.predict(test[cols])
    naive = models.NaiveMean().fit(train["rul"]).predict(test[cols])
    # synthetic engines of unequal length: the capped region dominates the error, so demand a clear
    # but not extreme improvement over the naive mean (observed ratio ~0.5 on this fixture)
    assert metrics.rmse(test["rul"], pred) < 0.7 * metrics.rmse(test["rul"], naive)
    assert (pred >= 0).all()


def test_naive_mean_predicts_training_mean():
    y = np.array([1.0, 3.0, 5.0])
    m = models.NaiveMean().fit(y)
    assert list(m.predict(np.zeros((2, 4)))) == [3.0, 3.0]


def test_point_model_is_deterministic_given_seed():
    train, cols = _prepare(6, seed=3)
    a = models.train_point_model(train[cols], train["rul"], max_iter=50, learning_rate=0.1, max_leaf_nodes=15, seed=7)
    b = models.train_point_model(train[cols], train["rul"], max_iter=50, learning_rate=0.1, max_leaf_nodes=15, seed=7)
    assert np.allclose(a.predict(train[cols]), b.predict(train[cols]))
