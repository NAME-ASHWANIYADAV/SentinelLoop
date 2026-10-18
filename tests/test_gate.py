from sentinelloop import retrain

GATE = {"rmse_tol": 0.02, "min_picp": 0.85, "max_late_rate_increase": 0.02}
CHAMP = {"rmse": 14.0, "picp": 0.90, "late_rate": 0.05}


def test_gate_accepts_a_challenger_that_is_not_worse():
    r = retrain.evaluate_gate(CHAMP, {"rmse": 13.8, "picp": 0.89, "late_rate": 0.05}, GATE)
    assert r.passed and r.reasons == []


def test_gate_rejects_worse_rmse_beyond_tolerance():
    r = retrain.evaluate_gate(CHAMP, {"rmse": 14.5, "picp": 0.90, "late_rate": 0.05}, GATE)
    assert not r.passed and any("rmse" in x for x in r.reasons)


def test_gate_rejects_low_coverage():
    r = retrain.evaluate_gate(CHAMP, {"rmse": 13.0, "picp": 0.80, "late_rate": 0.05}, GATE)
    assert not r.passed and any("picp" in x for x in r.reasons)


def test_gate_rejects_higher_late_rate():
    r = retrain.evaluate_gate(CHAMP, {"rmse": 13.0, "picp": 0.90, "late_rate": 0.09}, GATE)
    assert not r.passed and any("late_rate" in x for x in r.reasons)


def test_gate_reports_all_failed_checks_not_just_the_first():
    r = retrain.evaluate_gate(CHAMP, {"rmse": 20.0, "picp": 0.5, "late_rate": 0.5}, GATE)
    assert len(r.reasons) == 3


def test_gate_result_is_serialisable():
    import json
    r = retrain.evaluate_gate(CHAMP, {"rmse": 13.8, "picp": 0.89, "late_rate": 0.05}, GATE)
    json.dumps(r.to_dict())
