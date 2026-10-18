from sentinelloop import clean, features, oof, targets
from conftest import make_synthetic_raw


def test_oof_table_can_include_baseline_point_models():
    raw = make_synthetic_raw(n_units=9, cycles=(60, 80, 70), degrade=True, seed=0)
    state = clean.CleanState.fit(raw, n_regimes=1, std_threshold=1e-3)
    f = targets.add_train_rul(features.build_features(state.transform(clean.impute(raw)), columns=state.kept_sensors, window=10), cap=50)
    cols = features.feature_manifest(f)
    out, _ = oof.oof_cqr_predictions(f, cols, n_folds=3, alpha=0.1, calib_frac=0.3, seed=1, max_iter=30, learning_rate=0.1, max_leaf_nodes=15,
                                     with_baselines=True, rf_trees=20)
    assert {"point_rf", "point_naive", "point_hgbr_all"} <= set(out.columns)
    assert (out["point_naive"].round(6).nunique() <= 3)  # one constant per fold
