import numpy as np

from sentinelloop import clean, features, oof, targets
from conftest import make_synthetic_raw


def _train(n_units=12, seed=0):
    raw = make_synthetic_raw(n_units=n_units, cycles=(60, 80, 70, 90), degrade=True, seed=seed)
    state = clean.CleanState.fit(raw, n_regimes=1, std_threshold=1e-3)
    f = features.build_features(state.transform(clean.impute(raw)), columns=state.kept_sensors, window=10)
    f = targets.add_train_rul(f, cap=50)
    return f, features.feature_manifest(f)


def test_oof_predictions_cover_every_training_row_exactly_once():
    train, cols = _train()
    out, folds = oof.oof_cqr_predictions(train, cols, n_folds=3, alpha=0.1, calib_frac=0.3, seed=1, max_iter=40, learning_rate=0.1, max_leaf_nodes=15)
    assert len(out) == len(train)
    assert set(out.columns) >= {"unit", "cycle", "rul", "rul_raw", "point", "lower", "upper", "fold", "anomaly_score", "anomaly_flag", "failure_cycle"}
    assert out.groupby(["unit", "cycle"]).size().max() == 1


def test_no_engine_is_predicted_by_a_model_that_saw_it():
    train, cols = _train()
    out, folds = oof.oof_cqr_predictions(train, cols, n_folds=3, alpha=0.1, calib_frac=0.3, seed=1, max_iter=40, learning_rate=0.1, max_leaf_nodes=15)
    for k, info in folds.items():
        val = set(info["val_units"])
        assert val.isdisjoint(info["train_units"]) and val.isdisjoint(info["calib_units"])
        assert set(out.loc[out.fold == k, "unit"].unique()) == val


def test_failure_cycle_equals_last_cycle_of_each_training_engine():
    train, cols = _train()
    out, _ = oof.oof_cqr_predictions(train, cols, n_folds=3, alpha=0.1, calib_frac=0.3, seed=1, max_iter=40, learning_rate=0.1, max_leaf_nodes=15)
    for u, g in out.groupby("unit"):
        assert g["failure_cycle"].iloc[0] == train.loc[train.unit == u, "cycle"].max()
        assert (g["failure_cycle"] - g["cycle"] == g["rul_raw"]).all()
