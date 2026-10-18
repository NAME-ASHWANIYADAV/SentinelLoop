import numpy as np
import pandas as pd
import pytest

from sentinelloop import policy, replay


def _engine(unit, n=100, bias=0.0, noise_seed=0, lower_gap=10.0, observed_until=None):
    rng = np.random.default_rng(noise_seed)
    cycles = np.arange(1, n + 1)
    truth = n - cycles  # raw RUL, failure at cycle n (RUL 0)
    point = np.clip(truth + bias + rng.normal(0, 0.5, n), 0, None)
    df = pd.DataFrame({"unit": unit, "cycle": cycles, "rul_true_raw": truth, "point": point, "lower": np.clip(point - lower_gap, 0, None), "upper": point + lower_gap})
    df["failure_cycle"] = n
    if observed_until is not None:
        df = df[df.cycle <= observed_until]
    return df


def test_point_policy_orders_when_point_crosses_threshold():
    e = _engine(1)
    p = policy.Policy(name="A", kind="point", threshold=20.0)
    c = policy.first_order_cycle(p, e)
    assert c is not None and abs(e.loc[e.cycle == c, "point"].iloc[0] - 20.0) < 1.5


def test_lower_bound_policy_orders_earlier_than_point_policy():
    e = _engine(1)
    a = policy.first_order_cycle(policy.Policy("A", "point", 20.0), e)
    c = policy.first_order_cycle(policy.Policy("C", "lower", 20.0), e)
    assert c < a


def test_margin_policy_equals_point_policy_with_shifted_threshold():
    e = _engine(1)
    a = policy.first_order_cycle(policy.Policy("A", "point", 30.0), e)
    b = policy.first_order_cycle(policy.Policy("B", "margin", 20.0, margin=10.0), e)
    assert a == b


def test_replay_marks_late_when_order_comes_too_close_to_failure():
    late_engine = _engine(1, bias=+18.0)   # model predicts too much life
    ok_engine = _engine(2, bias=0.0)
    out = replay.replay_policy(pd.concat([late_engine, ok_engine]), policy.Policy("A", "point", 20.0), min_lead=5)
    r1 = out[out.unit == 1].iloc[0]
    r2 = out[out.unit == 2].iloc[0]
    assert bool(r1.late) is True and bool(r2.late) is False
    assert r2.true_rul_at_order == pytest.approx(20.0, abs=2)


def test_replay_marks_pending_when_observation_ends_before_due():
    e = _engine(1, observed_until=40)  # true RUL at the end is 60: nothing should be due yet
    out = replay.replay_policy(e, policy.Policy("A", "point", 20.0), min_lead=5)
    r = out.iloc[0]
    assert bool(r.ordered) is False and bool(r.pending) is True and bool(r.late) is False


def test_decision_metrics_aggregate_per_policy():
    frames = [_engine(1, bias=18.0), _engine(2), _engine(3), _engine(4, observed_until=30)]
    df = pd.concat(frames)
    out = replay.replay_policy(df, policy.Policy("A", "point", 20.0), min_lead=5)
    m = replay.decision_metrics(out)
    assert m["n_engines"] == 4 and m["n_evaluable"] == 3 and m["n_pending"] == 1
    assert m["late_rate"] == pytest.approx(1 / 3)
    assert m["mean_discarded_life"] == pytest.approx(20.0, abs=2)  # over on-time orders only
    assert "order_rate" in m and "mean_lead_time" in m


def test_tune_threshold_to_target_late_rate_uses_only_tuning_engines():
    tune = pd.concat([_engine(u, bias=5.0, noise_seed=u) for u in range(1, 9)])
    t = replay.tune_threshold(tune, kind="point", target_late_rate=0.0, grid=np.arange(5, 60, 1.0), min_lead=5)
    out = replay.replay_policy(tune, policy.Policy("A", "point", t), min_lead=5)
    assert replay.decision_metrics(out)["late_rate"] == 0.0
    assert t >= 5.0


def test_churn_counts_severity_changes_before_first_order():
    e = _engine(1)
    e["severity"] = ["NONE"] * 50 + ["MEDIUM"] * 20 + ["HIGH"] * 15 + ["MEDIUM"] * 5 + ["HIGH"] * 5 + ["CRITICAL"] * 5
    assert replay.churn(e["severity"].to_numpy()) == 5
