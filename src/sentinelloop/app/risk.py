"""Probability of failure before a time t, read from a prediction interval.

The model gives a point estimate and a central interval at a stated level (e.g. 90%: the 5th and 95th
percentiles). We read P(RUL <= t) off a piecewise-linear CDF through (lower, a), (point, 0.5), (upper, 1 - a)
with a = (1 - level) / 2, and linear tails that reach 0 one lower half-width below `lower` and 1 one upper
half-width above `upper`. This is a transparent, monotone approximation, not a fitted distribution: its own
calibration (do events happen as often as it says?) is measured in the reliability study, not assumed.
"""
from __future__ import annotations


def p_fail_before(t: float, lower: float, point: float, upper: float, level: float = 0.90) -> float:
    """The point model and the quantile models are fitted separately, so the point can fall outside [lower, upper];
    the CDF then uses the point clipped into the interval as its median (flagged by `summarise`)."""
    if lower > upper:
        raise ValueError(f"interval must satisfy lower <= upper, got {lower}, {upper}")
    point = min(max(point, lower), upper)
    if not 0 < level < 1:
        raise ValueError("level must be in (0, 1)")
    a = (1.0 - level) / 2.0
    dl, du = point - lower, upper - point
    knots = [(lower - dl, 0.0), (lower, a), (point, 0.5), (upper, 1.0 - a), (upper + du, 1.0)]
    if t < knots[0][0]:
        return 0.0
    p = 0.0
    for (x0, y0), (x1, y1) in zip(knots, knots[1:]):
        if t >= x1:
            p = y1
            continue
        if t >= x0:
            p = y0 if x1 == x0 else y0 + (y1 - y0) * (t - x0) / (x1 - x0)
        break
    return float(min(1.0, max(0.0, p)))


def summarise(lower: float, point: float, upper: float, level: float, cap: float | None, horizons) -> dict:
    """P(failure before each horizon) plus flags a reviewer needs to read the numbers correctly."""
    return {"p_fail_before": {h: p_fail_before(h, lower, point, upper, level) for h in horizons},
            "upper_censored": bool(cap is not None and upper >= cap - 1e-9),
            "lower_at_zero": bool(lower <= 0.0),
            "point_outside_interval": bool(point < lower or point > upper),
            "level": level, "method": "piecewise-linear CDF through the interval quantiles"}
