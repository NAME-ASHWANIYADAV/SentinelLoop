import numpy as np

from sentinelloop import agent, clean, conformal, features, targets
from conftest import make_synthetic_raw


def _frames(n_units, seed):
    raw = make_synthetic_raw(n_units=n_units, cycles=(60, 80, 70, 90, 65), degrade=True, seed=seed)
    state = clean.CleanState.fit(raw, n_regimes=1, std_threshold=1e-3)
    f = features.build_features(state.transform(clean.impute(raw)), columns=state.kept_sensors, window=10)
    f = targets.add_train_rul(f, cap=50)
    return f, features.feature_manifest(f)


def test_cqr_model_suggests_a_max_width_from_calibration_rows():
    train, cols = _frames(20, seed=0)
    m = conformal.fit_cqr(train, cols, alpha=0.1, calib_frac=0.3, seed=1, max_iter=40, learning_rate=0.1, max_leaf_nodes=15, serious_lower_max=25.0)
    assert np.isfinite(m.suggested_max_width) and m.suggested_max_width > 0
    assert m.metadata()["suggested_max_width"] == m.suggested_max_width
    assert m.metadata()["serious_lower_max"] == 25.0


def test_suggested_width_is_the_75th_percentile_of_serious_calibration_widths():
    train, cols = _frames(20, seed=0)
    m = conformal.fit_cqr(train, cols, alpha=0.1, calib_frac=0.3, seed=1, max_iter=40, learning_rate=0.1, max_leaf_nodes=15, serious_lower_max=25.0)
    cal = train[train.unit.isin(m.calibration_units)]
    _, lo, hi = m.predict(cal[cols])
    widths = (hi - lo)[lo <= 25.0]
    assert abs(m.suggested_max_width - np.percentile(widths, 75)) < 1e-6


def test_agent_escalates_on_quality_flag_even_when_imputed_fraction_is_low():
    thr = agent.Thresholds(t_critical=10, t_high=25, t_medium=50, max_width=60, quality_max_imputed_frac=0.1)
    o = agent.Observation(unit=1, cycle=5, rul_point=20.0, rul_lower=15.0, rul_upper=40.0, anomaly_flag=False, anomaly_score=0.0,
                          drift_flag=False, imputed_frac=0.0, missing_sensors=0, model_version="v", quality_flag=True)
    d = agent.triage(o, thr)
    assert d.escalate_to_human and "data_quality" in d.escalation_reasons and d.action == "INSPECT"
    assert d.to_record()["inputs"]["quality_flag"] is True


def test_thresholds_from_config_accept_auto_width_with_a_fallback():
    cfg = {"agent": {"t_critical": 10, "t_high": 25, "t_medium": 50, "max_width": "auto", "quality_max_imputed_frac": 0.1}}
    thr = agent.Thresholds.from_config(cfg, auto_max_width=72.5)
    assert thr.max_width == 72.5
    cfg["agent"]["max_width"] = 60
    assert agent.Thresholds.from_config(cfg, auto_max_width=72.5).max_width == 60
