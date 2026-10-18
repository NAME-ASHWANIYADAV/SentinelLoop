import math

import numpy as np
import pytest

from sentinelloop import metrics


def test_rmse_and_mae_known_values():
    y = np.array([1.0, 2.0, 3.0])
    p = np.array([1.0, 4.0, 1.0])
    assert metrics.rmse(y, p) == pytest.approx(math.sqrt((0 + 4 + 4) / 3))
    assert metrics.mae(y, p) == pytest.approx(4 / 3)


def test_phm08_score_hand_computed():
    # d = pred - true: -13 (early) -> exp(13/13)-1 ; +10 (late) -> exp(10/10)-1 ; 0 -> 0
    y = np.array([20.0, 20.0, 20.0])
    p = np.array([7.0, 30.0, 20.0])
    expected = (math.e - 1) + (math.e - 1) + 0.0
    assert metrics.phm08_score(y, p) == pytest.approx(expected)


def test_phm08_score_penalises_late_more_than_early():
    y = np.array([50.0])
    assert metrics.phm08_score(y, np.array([60.0])) > metrics.phm08_score(y, np.array([40.0]))


def test_phm08_convention_string_is_explicit():
    s = metrics.PHM08_CONVENTION
    assert "exp(-d/13)" in s and "exp(d/10)" in s and "d = pred" in s
    assert "a1=13" in s and "a2=10" in s   # Saxena et al. 2008: a1 = 13 for early (d < 0), a2 = 10 for late (d >= 0)


def test_picp_and_mpiw():
    y = np.array([10.0, 20.0, 30.0, 40.0])
    lo = np.array([5.0, 25.0, 20.0, 35.0])
    hi = np.array([15.0, 35.0, 40.0, 45.0])
    assert metrics.picp(y, lo, hi) == pytest.approx(0.75)
    assert metrics.mpiw(lo, hi) == pytest.approx((10 + 10 + 20 + 10) / 4)
