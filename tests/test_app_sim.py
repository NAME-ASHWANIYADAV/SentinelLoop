"""Fleet simulator invariants on a small fleet (real out-of-fold predictions; marked slow)."""
from dataclasses import replace

import pytest

from sentinelloop.app import sim
from conftest import ROOT

pytestmark = pytest.mark.slow
OOF = [ROOT / "experiments" / "results" / "oof" / "FD001_full.csv"]


@pytest.fixture(scope="module")
def trajs():
    if not OOF[0].exists():
        pytest.skip("out-of-fold table not present (run experiments/run_all.py)")
    return sim.load_trajectories(OOF)


SMALL = replace(sim.SimConfig(), n_assets=8, days=20, milp_time_limit_s=5.0)


@pytest.mark.parametrize("policy", list(sim.POLICIES))
def test_every_policy_runs_with_zero_schedule_violations_and_consistent_accounting(trajs, policy):
    r = sim.run(trajs, SMALL, policy, seed=1)
    m = r.metrics
    assert m["schedule_violations"] == 0
    assert m["plans"] == SMALL.days
    assert m["failures"] == m["failures_A"] + m["failures_B"] + m["failures_C"]
    assert m["corrective_repairs"] <= m["failures"]
    if m["failures"] and SMALL.days >= 20:
        assert m["corrective_repairs"] > 0 and m["unplanned_downtime_h"] > 0     # failed assets do get repaired
    assert m["early_repairs"] <= m["preventive_repairs"] and m["inspections_no_fault"] <= m["inspections"]
    assert m["total_cost"] == pytest.approx(m["failure_cost"] + m["preventive_repairs"] * SMALL.repair_cost + m["inspections"] * SMALL.inspect_cost)
    if policy == "RUN_TO_FAILURE":
        assert m["preventive_repairs"] == 0 and m["inspections"] == 0


def test_same_seed_same_result_and_same_fleet_across_policies(trajs):
    a = sim.run(trajs, SMALL, "RISK_GREEDY", seed=4).metrics
    b = sim.run(trajs, SMALL, "RISK_GREEDY", seed=4).metrics
    assert a == b
    f1 = sim.FleetSim(trajs, SMALL, "THRESHOLD_EDD", seed=4)
    f2 = sim.FleetSim(trajs, SMALL, "RISK_MILP", seed=4)
    assert [(x.criticality, x.traj_idx, x.age_h) for x in f1.assets.values()] == [(x.criticality, x.traj_idx, x.age_h) for x in f2.assets.values()]


def test_no_maintenance_means_failures_and_preventive_work_reduces_them(trajs):
    cfg = replace(SMALL, n_assets=10, days=40)
    rtf = sim.run(trajs, cfg, "RUN_TO_FAILURE", seed=2).metrics
    risk = sim.run(trajs, cfg, "RISK_GREEDY", seed=2).metrics
    assert rtf["failures"] > 0 and risk["failures"] < rtf["failures"]


def test_parts_are_never_consumed_beyond_physical_stock(trajs):
    cfg = sim.scenario_config("parts_shortage", replace(SMALL, days=30))
    r = sim.FleetSim(trajs, cfg, "RISK_GREEDY", seed=3)
    res = r.run()
    assert r.kits >= 0 and res.metrics["schedule_violations"] == 0


def test_downtime_of_assets_still_failed_at_the_end_is_counted(trajs):
    """Adversarial review data_scientist-1: downtime was credited only when a repair finished (right-censoring)."""
    cfg = replace(sim.scenario_config("parts_shortage"), days=40, n_assets=12)
    m = sim.run(trajs, cfg, "RUN_TO_FAILURE", seed=0, scenario="parts_shortage").metrics
    assert m["assets_failed_at_end"] > 0
    assert m["unplanned_downtime_total_h"] > m["unplanned_downtime_h"]
    fleet_h = cfg.n_assets * cfg.days * 24
    assert abs(m["availability"] - (1 - (m["unplanned_downtime_total_h"] + m["planned_downtime_h"]) / fleet_h)) < 1e-9
    assert 0.0 <= m["availability"] <= 1.0
