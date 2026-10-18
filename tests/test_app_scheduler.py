"""Scheduling engine: feasibility, reasons for unscheduled work, policies and the independent validator (tests first)."""
import numpy as np
import pytest

from sentinelloop.app import scheduler as S
from sentinelloop.app.timeutil import HOUR_MS, parse_ts

T0 = parse_ts("2026-10-19T00:00:00Z")


def h(x):
    return T0 + int(x * HOUR_MS)


def tech(tid, skills=("mech",), shifts=((0, 24 * 7),)):
    return S.Tech(tid, frozenset(skills), tuple((h(a), h(b)) for a, b in shifts))


def job(jid, asset="A1", skill="mech", crew=1, dur=4, parts=None, windows=((0, 24 * 7),), release=0, due=None, pc="P2", crit="B", cost=100.0,
        risk=None, score=None):
    return S.Job(job_id=jid, asset_id=asset, skill=skill, crew=crew, duration_h=dur, parts=dict(parts or {}),
                 windows=[(h(a), h(b)) for a, b in windows], release_ms=h(release), due_ms=None if due is None else h(due), priority_class=pc,
                 criticality=crit, failure_cost=cost, risk=risk, score=score)


def problem(jobs, techs, parts=None, horizon=48, slot=1):
    return S.Problem(t0_ms=T0, horizon_h=horizon, slot_h=slot, jobs=jobs, techs=techs, parts=parts or {})


@pytest.mark.parametrize("policy", ["edd", "criticality_first", "risk_greedy", "milp"])
def test_one_technician_cannot_do_two_overlapping_jobs(policy):
    p = problem([job("J1", asset="A1"), job("J2", asset="A2")], [tech("T1")])
    s = S.plan(p, policy)
    assert S.validate(p, s) == []
    a = {x.job_id: x for x in s.assignments}
    assert set(a) == {"J1", "J2"} and (a["J1"].end_ms <= a["J2"].start_ms or a["J2"].end_ms <= a["J1"].start_ms)


def test_unscheduled_jobs_carry_a_specific_reason():
    p = problem([job("NOWIN", windows=()), job("NOSKILL", skill="electrical"), job("NOPARTS", parts={"kit": 1}),
                 job("WINDOW_TOO_SHORT", dur=6, windows=((2, 6),))],
                [tech("T1")], parts={"kit": S.PartStock("kit", on_hand=0, lead_time_h=96)}, horizon=48)
    s = S.plan(p, "risk_greedy")
    r = s.unscheduled
    assert "no maintenance window" in r["NOWIN"]
    assert "no technician with skill electrical" in r["NOSKILL"]
    assert "parts" in r["NOPARTS"] and "96" in r["NOPARTS"]
    assert "no window long enough" in r["WINDOW_TOO_SHORT"]
    assert S.validate(p, s) == []


def test_parts_shortage_delays_the_start_until_arrival():
    p = problem([job("J1", parts={"kit": 1}), job("J2", asset="A2", parts={"kit": 1})], [tech("T1"), tech("T2")],
                parts={"kit": S.PartStock("kit", on_hand=1, lead_time_h=24)}, horizon=72)
    s = S.plan(p, "edd")
    starts = sorted(x.start_ms for x in s.assignments)
    assert starts[0] == h(0) and starts[1] >= h(24)
    assert S.validate(p, s) == []


def test_crew_of_two_needs_two_qualified_technicians_on_shift():
    p = problem([job("J1", crew=2)], [tech("T1"), tech("T2", skills=("electrical",))])
    assert "J1" in S.plan(p, "edd").unscheduled
    p = problem([job("J1", crew=2)], [tech("T1"), tech("T2")])
    s = S.plan(p, "edd")
    assert len(s.assignments[0].techs) == 2 and S.validate(p, s) == []


def test_shifts_limit_when_work_can_happen():
    p = problem([job("J1", dur=4)], [tech("T1", shifts=((10, 18),))])
    a = S.plan(p, "edd").assignments[0]
    assert h(10) <= a.start_ms and a.end_ms <= h(18)


def test_frozen_assignments_are_kept_and_block_their_technicians():
    frozen = [S.Assignment("F1", "A9", h(0), h(8), ["T1"])]
    p = problem([job("J1")], [tech("T1")])
    p.frozen = frozen
    s = S.plan(p, "edd")
    assert s.assignments[0].start_ms >= h(8) and S.validate(p, s) == []


def test_criticality_first_and_risk_greedy_order_work_differently():
    jobs = [job("CRIT_A_LOWRISK", asset="A1", crit="A", dur=6, score=1.0, risk=(500, 900, 1500, 0.9, T0), cost=1000),
            job("CRIT_C_HIGHRISK", asset="A2", crit="C", dur=6, score=50.0, risk=(1, 10, 40, 0.9, T0), cost=1000)]   # only one 6 h job fits in 8 h
    p = problem(jobs, [tech("T1")], horizon=8)
    assert [a.job_id for a in S.plan(p, "criticality_first").assignments] == ["CRIT_A_LOWRISK"]
    assert [a.job_id for a in S.plan(p, "risk_greedy").assignments] == ["CRIT_C_HIGHRISK"]


def test_milp_is_never_worse_than_the_greedy_policies_on_its_own_objective():
    rng = np.random.default_rng(3)
    for trial in range(5):
        jobs = []
        for i in range(8):
            lo = float(rng.uniform(5, 60)); pt = lo + float(rng.uniform(5, 60)); up = pt + float(rng.uniform(5, 80))
            jobs.append(job(f"J{i}", asset=f"A{i}", dur=int(rng.integers(2, 7)), crit="ABC"[i % 3], cost=float(rng.uniform(100, 1000)),
                            risk=(lo, pt, up, 0.9, T0), score=float(rng.uniform(1, 10)), pc=["P1", "P2"][i % 2],
                            windows=[(int(d * 24 + 18), int(d * 24 + 30)) for d in range(3)]))
        p = problem(jobs, [tech("T1"), tech("T2")], horizon=72)
        m = S.plan(p, "milp", time_limit_s=20)
        assert S.validate(p, m) == []
        for pol in ("edd", "criticality_first", "risk_greedy"):
            g = S.plan(p, pol)
            assert S.validate(p, g) == []
            assert m.objective <= g.objective + 1e-6, (trial, pol, m.objective, g.objective)
        assert m.solver["status_text"] and "aggregated" in m.solver["caveat"]


def test_validator_catches_double_booking_wrong_skill_off_shift_and_outside_window():
    p = problem([job("J1", windows=((0, 10),)), job("J2", asset="A2")], [tech("T1"), tech("T9", skills=("electrical",), shifts=((20, 30),))])
    bad = S.Schedule("handmade", [S.Assignment("J1", "A1", h(8), h(12), ["T1"]), S.Assignment("J2", "A2", h(9), h(13), ["T1", "T9"])], {}, 0.0, {}, {})
    v = " | ".join(S.validate(p, bad))
    assert "outside" in v and "double-booked" in v and "lacks skill" in v and "not on shift" in v


def test_random_instances_always_validate():
    rng = np.random.default_rng(11)
    for trial in range(10):
        techs = [tech(f"T{k}", skills=(["mech"], ["mech", "elec"], ["elec"])[k % 3], shifts=(((k * 3) % 8, (k * 3) % 8 + 40),)) for k in range(3)]
        jobs = [job(f"J{i}", asset=f"A{i % 5}", skill=["mech", "elec"][i % 2], crew=1 + (i % 4 == 0), dur=int(rng.integers(1, 6)),
                    parts={"kit": 1} if i % 3 == 0 else None, windows=[(int(rng.integers(0, 20)), int(rng.integers(25, 47)))],
                    risk=(10, 30, 60, 0.9, T0), score=float(rng.uniform(0, 5)), crit="ABC"[i % 3]) for i in range(10)]
        p = problem(jobs, techs, parts={"kit": S.PartStock("kit", 2, 12)}, horizon=48)
        for pol in ("edd", "criticality_first", "risk_greedy", "milp"):
            assert S.validate(p, S.plan(p, pol, time_limit_s=10)) == [], (trial, pol)


@pytest.mark.parametrize("policy", ["edd", "criticality_first", "risk_greedy", "milp"])
def test_a_day_with_no_schedulable_work_is_a_valid_empty_plan(policy):
    p = problem([], [tech("T1")])
    s = S.plan(p, policy)
    assert s.assignments == [] and s.unscheduled == {} and S.validate(p, s) == []
    p = problem([job("NOWIN", windows=())], [tech("T1")])
    s = S.plan(p, policy)
    assert s.assignments == [] and "NOWIN" in s.unscheduled


@pytest.mark.parametrize("policy", ["edd", "risk_greedy", "milp"])
def test_known_part_arrivals_are_respected_when_more_cannot_be_ordered(policy):
    # one kit on hand, one arriving at 30 h, nothing else can be ordered: the third job cannot be scheduled
    stock = S.PartStock("kit", on_hand=1, lead_time_h=999, arrivals=((h(30), 1),), orderable=False)
    jobs = [job(f"J{i}", asset=f"A{i}", parts={"kit": 1}, risk=(10, 30, 60, 0.9, T0), score=1.0) for i in range(3)]
    p = problem(jobs, [tech("T1"), tech("T2"), tech("T3")], parts={"kit": stock}, horizon=72)
    s = S.plan(p, policy)
    assert S.validate(p, s) == []
    starts = sorted(a.start_ms for a in s.assignments)
    assert len(starts) == 2 and starts[1] >= h(30)
    assert len(s.unscheduled) == 1 and "part" in list(s.unscheduled.values())[0]


def test_validator_catches_parts_used_before_they_arrive():
    stock = S.PartStock("kit", on_hand=0, lead_time_h=999, arrivals=((h(30), 1),), orderable=False)
    p = problem([job("J1", parts={"kit": 1})], [tech("T1")], parts={"kit": stock}, horizon=72)
    bad = S.Schedule("handmade", [S.Assignment("J1", "A1", h(2), h(6), ["T1"])], {}, 0.0, {}, {})
    assert any("kit" in v for v in S.validate(p, bad))


@pytest.mark.parametrize("policy", ["risk_greedy", "milp"])
def test_stability_preference_keeps_feasible_previous_starts(policy):
    jobs = [job(f"J{i}", asset=f"A{i}", risk=(20, 40, 80, 0.9, T0), score=float(i)) for i in range(3)]
    p = problem(jobs, [tech("T1")], horizon=48)
    first = S.plan(p, policy)
    prev = {a.job_id: a.start_ms for a in first.assignments}
    # tomorrow the scores change order; with the stability preference the plan keeps yesterday's starts where they are still feasible
    jobs2 = [job(f"J{i}", asset=f"A{i}", risk=(20, 40, 80, 0.9, T0), score=float(3 - i)) for i in range(3)]
    p2 = problem(jobs2, [tech("T1")], horizon=48)
    p2.previous = prev
    p2.stability_weight = 1.0
    s2 = S.plan(p2, policy)
    assert {a.job_id: a.start_ms for a in s2.assignments} == prev and S.validate(p2, s2) == []
