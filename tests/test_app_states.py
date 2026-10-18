"""Risk from an interval, assessment classification and the asset state machine (tests written before the code)."""
import pytest

from sentinelloop.app import risk, states
from sentinelloop.app.states import AssetState, Classification as Cl, HealthState as H, Thresholds

THR = Thresholds(p_inspect=0.10, p_urgent=0.30, dq_clear_after=2)


# ---- risk: P(failure before t) read from the interval -----------------------------------------------------
def test_cdf_hits_the_interval_quantiles():
    assert risk.p_fail_before(10, lower=10, point=30, upper=60, level=0.90) == pytest.approx(0.05)
    assert risk.p_fail_before(30, lower=10, point=30, upper=60, level=0.90) == pytest.approx(0.50)
    assert risk.p_fail_before(60, lower=10, point=30, upper=60, level=0.90) == pytest.approx(0.95)


def test_cdf_is_monotone_bounded_and_handles_degenerate_intervals():
    ps = [risk.p_fail_before(t, lower=10, point=30, upper=60, level=0.90) for t in range(-10, 200, 5)]
    assert all(b >= a for a, b in zip(ps, ps[1:])) and ps[0] == 0.0 and ps[-1] == 1.0
    assert risk.p_fail_before(5, lower=20, point=20, upper=20, level=0.9) == 0.0
    assert risk.p_fail_before(25, lower=20, point=20, upper=20, level=0.9) == 1.0


def test_wider_interval_means_more_early_risk_for_the_same_point():
    narrow = risk.p_fail_before(15, lower=20, point=30, upper=40, level=0.9)
    wide = risk.p_fail_before(15, lower=5, point=30, upper=80, level=0.9)
    assert wide > narrow


def test_censored_upper_bound_is_reported():
    r = risk.summarise(lower=40, point=110, upper=125, level=0.9, cap=125, horizons=[10, 50])
    assert r["upper_censored"] is True and r["p_fail_before"][10] < r["p_fail_before"][50]


# ---- classification precedence ----------------------------------------------------------------------------
def test_classification_precedence():
    assert states.classify(model_ok=False, data_ok=False, in_scope=False, p_fail=0.9, sustained_anomaly=True, thr=THR).state == H.MODEL_UNAVAILABLE
    assert states.classify(model_ok=True, data_ok=False, in_scope=False, p_fail=0.9, sustained_anomaly=False, thr=THR).state == H.DATA_QUALITY_FAILURE
    assert states.classify(model_ok=True, data_ok=True, in_scope=False, p_fail=0.9, sustained_anomaly=False, thr=THR).state == H.MODEL_OUT_OF_SCOPE
    assert states.classify(model_ok=True, data_ok=True, in_scope=True, p_fail=0.30, sustained_anomaly=False, thr=THR).state == H.URGENT_REVIEW
    assert states.classify(model_ok=True, data_ok=True, in_scope=True, p_fail=0.10, sustained_anomaly=False, thr=THR).state == H.INSPECTION_RECOMMENDED
    assert states.classify(model_ok=True, data_ok=True, in_scope=True, p_fail=0.01, sustained_anomaly=True, thr=THR).state == H.INSPECTION_RECOMMENDED
    assert states.classify(model_ok=True, data_ok=True, in_scope=True, p_fail=0.01, sustained_anomaly=False, thr=THR).state == H.NORMAL_MONITORING


# ---- the asset state machine ------------------------------------------------------------------------------
def step(s, *cls):
    for c in cls:
        s = states.advance(s, Cl(c, []), THR)
    return s


def test_urgent_latches_until_maintenance_or_dismissal():
    s = step(AssetState(), H.URGENT_REVIEW, H.NORMAL_MONITORING, H.NORMAL_MONITORING)
    assert s.effective == H.URGENT_REVIEW and s.latched_risk == "URGENT"
    assert "latched" in " ".join(s.notes)
    with pytest.raises(states.TransitionError):
        states.clear_risk(s, event="dismissed", actor="tech1", role="technician", reason="looks fine")   # technicians cannot dismiss
    with pytest.raises(states.TransitionError):
        states.clear_risk(s, event="dismissed", actor="re1", role="reliability_engineer", reason="")    # a reason is mandatory
    s2 = states.clear_risk(s, event="dismissed", actor="re1", role="reliability_engineer", reason="vibration route clean, sensor drift suspected")
    assert s2.latched_risk == "NONE"
    assert step(s2, H.NORMAL_MONITORING).effective == H.NORMAL_MONITORING


def test_data_failure_never_hides_an_urgent_condition():
    s = step(AssetState(), H.URGENT_REVIEW, H.DATA_QUALITY_FAILURE)
    assert s.effective == H.URGENT_REVIEW and H.DATA_QUALITY_FAILURE.value in " ".join(s.notes)


def test_data_quality_failure_needs_consecutive_good_assessments_to_clear():
    s = step(AssetState(), H.DATA_QUALITY_FAILURE)
    assert s.effective == H.DATA_QUALITY_FAILURE
    s = step(s, H.NORMAL_MONITORING)
    assert s.effective == H.DATA_QUALITY_FAILURE          # one good assessment is not enough
    s = step(s, H.NORMAL_MONITORING)
    assert s.effective == H.NORMAL_MONITORING


def test_inspection_upgrades_to_urgent_but_never_silently_downgrades():
    s = step(AssetState(), H.INSPECTION_RECOMMENDED, H.NORMAL_MONITORING)
    assert s.effective == H.INSPECTION_RECOMMENDED
    s = step(s, H.URGENT_REVIEW, H.INSPECTION_RECOMMENDED)
    assert s.effective == H.URGENT_REVIEW


def test_maintenance_completion_clears_the_latched_risk():
    s = step(AssetState(), H.URGENT_REVIEW)
    s = states.clear_risk(s, event="maintenance_completed", actor="planner1", role="planner", reason="WO-12 completed, bearing replaced")
    assert s.latched_risk == "NONE" and s.effective == H.NORMAL_MONITORING


def test_out_of_scope_and_model_unavailable_show_through_when_no_risk_is_latched():
    assert step(AssetState(), H.MODEL_OUT_OF_SCOPE).effective == H.MODEL_OUT_OF_SCOPE
    assert step(AssetState(), H.MODEL_UNAVAILABLE).effective == H.MODEL_UNAVAILABLE
    s = step(AssetState(), H.INSPECTION_RECOMMENDED, H.MODEL_UNAVAILABLE)
    assert s.effective == H.MODEL_UNAVAILABLE and s.latched_risk == "INSPECTION"


def test_approval_flag_is_independent_of_the_health_state():
    s = step(AssetState(), H.URGENT_REVIEW)
    s = states.set_approval_pending(s, True)
    assert s.labels() == ["URGENT_REVIEW", "HUMAN_APPROVAL_REQUIRED"]
    assert states.set_approval_pending(s, False).labels() == ["URGENT_REVIEW"]


def test_every_transition_in_the_table_is_exercised():
    """Exhaustive check: from every reachable state, every classification yields a defined, valid state."""
    seen = set()
    frontier = [AssetState()]
    for _ in range(4):
        nxt = []
        for s in frontier:
            for h in H:
                t = states.advance(s, Cl(h, []), THR)
                assert t.effective in H and t.latched_risk in ("NONE", "INSPECTION", "URGENT")
                if t.latched_risk == "URGENT":
                    assert t.effective == H.URGENT_REVIEW
                key = (t.effective, t.latched_risk, t.dq_ok_streak)
                if key not in seen:
                    seen.add(key)
                    nxt.append(t)
        frontier = nxt
    assert len(seen) >= 8


def test_point_outside_the_interval_is_clipped_for_the_cdf_and_flagged():
    # the point model and the quantile models are fitted separately, so the point can fall outside [lower, upper]
    assert risk.p_fail_before(125.0, lower=124.2, point=127.0, upper=125.6, level=0.9) == pytest.approx(
        risk.p_fail_before(125.0, lower=124.2, point=125.6, upper=125.6, level=0.9))
    r = risk.summarise(lower=124.2, point=127.0, upper=125.6, level=0.9, cap=125, horizons=[50])
    assert r["point_outside_interval"] is True
    with pytest.raises(ValueError):
        risk.p_fail_before(5, lower=30, point=20, upper=10, level=0.9)       # an inverted interval is still an error


def test_a_never_assessed_asset_is_never_labelled_normal():
    s = states.set_approval_pending(states.AssetState(), True)       # an order waits, but no assessment has run
    assert s.labels() == ["NOT_ASSESSED", "HUMAN_APPROVAL_REQUIRED"]
    assessed = states.advance(states.AssetState(), states.classify(True, True, True, 0.01, False, states.Thresholds()), states.Thresholds())
    assert assessed.labels() == ["NORMAL_MONITORING"]
