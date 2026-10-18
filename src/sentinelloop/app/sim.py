"""Fleet simulator for comparing maintenance policies under constrained resources (SIMULATED evidence only).

Each simulated asset runs through a sequence of NASA C-MAPSS engine trajectories (FD001/FD003 training engines)
and sees, at every planning instant, the OUT-OF-FOLD prediction the competition model made for that engine at that
cycle (point, 90% interval): realistic prediction errors from a model that never saw the engine. True failure times
are the engines' recorded end of life. Time is in hours (3 h per cycle, declared assumption). Every policy gets the
same fleet, the same trajectory sequence, the same starting ages and the same resources (per seed and scenario).

Daily loop at 06:00: predictions -> trigger policy creates or upgrades jobs -> approval (instant or delayed) ->
scheduler plans a 72 h horizon -> the first 24 h of the plan are committed -> hour-by-hour execution: assets age,
fail if their true RUL runs out, committed jobs start only if their parts are physically on hand (otherwise
`parts_blocked`, back to the backlog), repairs renew the asset, inspections reveal the true condition (perfect
inspection: degradation is found iff true RUL <= `inspect_detect_cycles`, a declared assumption).

Costs are relative units (one planned repair = 1.0); they are assumptions, swept in the evaluation; no figure here is
a real-world saving.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from pathlib import Path

import numpy as np
import pandas as pd

from . import scheduler as S
from .decision import inverse_cdf
from .risk import p_fail_before
from .timeutil import HOUR_MS, DAY_MS, parse_ts

T_START = parse_ts("2027-01-04T06:00:00Z")


@dataclass(frozen=True)
class SimConfig:
    n_assets: int = 30
    days: int = 120
    hours_per_cycle: float = 3.0
    slot_h: float = 1.0
    plan_horizon_h: float = 72.0
    commit_h: float = 24.0
    window_open_h: int = 20            # daily maintenance window 20:00-06:00 (assets may be taken offline at night)
    window_close_h: int = 6
    technicians: tuple = (("M1", ("mech",), 20, 4), ("M2", ("mech",), 20, 4), ("M3", ("mech",), 22, 6), ("M4", ("mech",), 22, 6))
    kit_stock: int = 8                 # repair kits on hand at the start; one-for-one reorder on use
    kit_lead_h: float = 72.0
    inspect_job: tuple = (2.0, 1)      # (hours, crew)
    repair_job: tuple = (8.0, 2)
    corrective_job: tuple = (8.0, 2)       # crew time once started; a crew stays with a job inside one shift
    corrective_delay_h: float = 24.0       # after a failure: diagnosis and logistics before corrective work can start
    inspect_detect_cycles: int = 40    # perfect inspection finds degradation iff true RUL <= this
    unnecessary_cycles: int = 40       # a preventive repair with more true RUL than this left is counted as early/unnecessary
    approval_delay_h: float = 0.0
    criticality_mix: tuple = (0.2, 0.5, 0.3)
    failure_cost: tuple = (("A", 10.0), ("B", 4.0), ("C", 1.5))
    repair_cost: float = 1.0
    inspect_cost: float = 0.1
    # trigger parameters
    decision_horizon_h: float = 60.0
    p_inspect: float = 0.10
    p_urgent: float = 0.30
    p_accept: float = 0.05
    threshold_h: float = 60.0          # fixed-threshold baseline: repair when the point RUL <= this
    interval_age_cycles: int = 140     # fixed-interval baseline: repair at this age
    prediction_widen: float = 1.0      # degraded-prediction scenario: interval half-widths x this
    prediction_bias_h: float = 0.0     # degraded-prediction scenario: point and bounds shifted by this (positive = optimistic)
    milp_time_limit_s: float = 10.0


POLICIES = {                          # (trigger, scheduler, stability weight)
    "RUN_TO_FAILURE": ("none", "edd", 0.0),
    "FIXED_INTERVAL": ("interval", "edd", 0.0),
    "THRESHOLD_EDD": ("threshold", "edd", 0.0),
    "RISK_CRITICALITY_FIRST": ("risk", "criticality_first", 0.0),
    "RISK_GREEDY": ("risk", "risk_greedy", 0.0),
    "RISK_GREEDY_STABLE": ("risk", "risk_greedy", 1.0),
    "RISK_MILP": ("risk", "milp", 0.0),
    "RISK_MILP_STABLE": ("risk", "milp", 1.0),
}
# Extra combinations for the trigger x scheduler factorial (S1e). Kept apart so that S1 reruns exactly as recorded.
EXTRA_POLICIES = {
    "RISK_EDD": ("risk", "edd", 0.0),
    "THRESHOLD_CRITICALITY_FIRST": ("threshold", "criticality_first", 0.0),
    "THRESHOLD_MILP": ("threshold", "milp", 0.0),
    # threshold trigger (repair when the point RUL <= threshold_h), queue ranked by expected loss avoided per crew-hour
    "THRESHOLD_GREEDY": ("threshold_scored", "risk_greedy", 0.0),
}
ALL_POLICIES = {**POLICIES, **EXTRA_POLICIES}


def load_trajectories(oof_paths) -> list[dict]:
    """Engines from out-of-fold tables: per engine arrays of cycle, point, lower, upper and the failure cycle."""
    out = []
    for path in oof_paths:
        df = pd.read_csv(path)
        tag = Path(path).stem.split("_")[0]
        for u, g in df.sort_values(["unit", "cycle"]).groupby("unit"):
            out.append({"engine": f"{tag}-{int(u)}", "failure_cycle": int(g["failure_cycle"].iloc[0]), "cycle": g["cycle"].to_numpy(),
                        "point": g["point"].to_numpy(dtype=float), "lower": g["lower"].to_numpy(dtype=float), "upper": g["upper"].to_numpy(dtype=float)})
    return out


@dataclass
class _Asset:
    asset_id: str
    criticality: str
    traj_idx: int
    age_h: float                      # operating hours on the current trajectory
    status: str = "running"           # running | maintenance | failed
    failed_at: int | None = None


@dataclass
class _Job:
    job_id: str
    asset_id: str
    kind: str                         # inspect | repair | corrective
    priority: str
    release_ms: int
    created_ms: int
    risk: tuple | None = None
    score: float | None = None
    due_ms: int | None = None
    committed: S.Assignment | None = None
    started_ms: int | None = None


@dataclass
class SimResult:
    policy: str
    scenario: str
    seed: int
    metrics: dict
    events: list = field(default_factory=list)


class FleetSim:
    def __init__(self, trajectories: list[dict], cfg: SimConfig, policy: str, seed: int, scenario: str = "base"):
        if policy not in ALL_POLICIES:
            raise ValueError(f"unknown policy {policy}")
        self.cfg, self.policy, self.seed, self.scenario = cfg, policy, seed, scenario
        self.trigger, self.sched_policy, self.stability = ALL_POLICIES[policy]
        rng = np.random.default_rng(seed)
        self.pool = [trajectories[i] for i in rng.permutation(len(trajectories))]
        self.next_traj = 0
        crit = rng.choice(["A", "B", "C"], size=cfg.n_assets, p=list(cfg.criticality_mix))
        self.cost = dict(cfg.failure_cost)
        self.assets = {}
        for i in range(cfg.n_assets):
            t = self._draw()
            start_cycle = int(rng.uniform(0, 0.8) * self.pool[t]["failure_cycle"])
            self.assets[f"S{i:03d}"] = _Asset(f"S{i:03d}", str(crit[i]), t, start_cycle * cfg.hours_per_cycle)
        self.now = T_START
        self.jobs: dict[str, _Job] = {}
        self.jid = 0
        self.kits = cfg.kit_stock
        self.kit_orders: list[int] = []             # arrival times
        self.ev = []
        self.m = {k: 0 for k in ("failures", "failures_A", "failures_B", "failures_C", "preventive_repairs", "early_repairs", "inspections",
                                 "inspections_no_fault", "corrective_repairs", "late_jobs", "parts_blocked", "jobs_created", "jobs_upgraded",
                                 "schedule_violations", "plans", "plan_changes", "plan_comparisons", "unscheduled_job_days")}
        self.m.update({"discarded_life_h": 0.0, "unplanned_downtime_h": 0.0, "planned_downtime_h": 0.0, "tech_hours_busy": 0.0,
                       "tech_hours_available": 0.0, "failure_cost": 0.0, "milp_non_optimal_plans": 0, "milp_dropped_in_assignment": 0})
        self.prev_plan: dict[str, int] = {}

    # -- trajectories and predictions --------------------------------------------------------------------------
    def _draw(self) -> int:
        i = self.next_traj % len(self.pool)
        self.next_traj += 1
        return i

    def _traj(self, a: _Asset) -> dict:
        return self.pool[a.traj_idx]

    def _cycle(self, a: _Asset) -> int:
        return int(math.floor(a.age_h / self.cfg.hours_per_cycle + 1e-9))

    def true_rul_h(self, a: _Asset) -> float:
        return self._traj(a)["failure_cycle"] * self.cfg.hours_per_cycle - a.age_h

    def prediction(self, a: _Asset):
        tr = self._traj(a)
        c = min(max(self._cycle(a), 1), int(tr["cycle"][-1]))
        i = int(np.searchsorted(tr["cycle"], c))
        hpc = self.cfg.hours_per_cycle
        pt, lo, up = tr["point"][i] * hpc, tr["lower"][i] * hpc, tr["upper"][i] * hpc
        pt = min(max(pt, lo), up)
        if self.cfg.prediction_widen != 1.0:
            lo, up = pt - (pt - lo) * self.cfg.prediction_widen, pt + (up - pt) * self.cfg.prediction_widen
        b = self.cfg.prediction_bias_h
        return max(lo + b, 0.0), max(pt + b, 0.0), max(up + b, 0.0)

    # -- jobs ----------------------------------------------------------------------------------------------------
    def _open_job(self, asset_id: str) -> _Job | None:
        for j in self.jobs.values():
            if j.asset_id == asset_id and j.started_ms is None:
                return j
        return None

    def _new_job(self, asset_id, kind, priority, risk=None, score=None, due=None, release=None):
        self.jid += 1
        j = _Job(f"J{self.jid:05d}-{kind}", asset_id, kind, priority, release if release is not None else self.now, self.now, risk, score, due)
        self.jobs[j.job_id] = j
        self.m["jobs_created"] += 1
        return j

    def _trigger(self):
        cfg = self.cfg
        for a in self.assets.values():
            if a.status != "running":
                continue
            open_j = self._open_job(a.asset_id)
            if self.trigger == "none":
                continue
            if self.trigger == "interval":
                if open_j is None and self._cycle(a) >= cfg.interval_age_cycles:
                    self._new_job(a.asset_id, "repair", "P2", release=self.now + int(cfg.approval_delay_h * HOUR_MS))
                continue
            lo, pt, up = self.prediction(a)
            risk = (lo, pt, up, 0.9, self.now)
            if self.trigger in ("threshold", "threshold_scored"):
                score = None
                if self.trigger == "threshold_scored":
                    score = p_fail_before(cfg.decision_horizon_h, lo, pt, up, 0.9) * self.cost[a.criticality] / (cfg.repair_job[0] * cfg.repair_job[1])
                if open_j is None and pt <= cfg.threshold_h:
                    self._new_job(a.asset_id, "repair", "P2", risk=risk, score=score, due=self.now + int(max(pt - cfg.repair_job[0], 0) * HOUR_MS),
                                  release=self.now + int(cfg.approval_delay_h * HOUR_MS))
                elif open_j is not None and open_j.kind == "repair" and open_j.committed is None and score is not None:
                    open_j.risk, open_j.score = risk, score
                continue
            p = p_fail_before(cfg.decision_horizon_h, lo, pt, up, 0.9)
            fc = self.cost[a.criticality]
            due = self.now + int(max(inverse_cdf(cfg.p_accept, lo, pt, up, 0.9) - cfg.repair_job[0], 0.0) * HOUR_MS)
            if p >= cfg.p_urgent:
                score = p * fc / (cfg.repair_job[0] * cfg.repair_job[1])
                if open_j is None:
                    self._new_job(a.asset_id, "repair", "P1", risk, score, due, release=self.now + int(cfg.approval_delay_h * HOUR_MS))
                elif open_j.kind == "inspect" and open_j.committed is None:
                    open_j.kind, open_j.priority, open_j.risk, open_j.score, open_j.due_ms = "repair", "P1", risk, score, due
                    self.m["jobs_upgraded"] += 1
                elif open_j.kind != "corrective":
                    open_j.risk, open_j.score, open_j.due_ms = risk, score, due
            elif p >= cfg.p_inspect and open_j is None:
                self._new_job(a.asset_id, "inspect", "P2", risk, p * fc / (cfg.inspect_job[0] * cfg.inspect_job[1]), due,
                              release=self.now + int(cfg.approval_delay_h * HOUR_MS))
            elif open_j is not None and open_j.kind != "corrective":
                open_j.risk = risk

    # -- planning --------------------------------------------------------------------------------------------------
    def _windows(self, a: _Asset):
        cfg = self.cfg
        if a.status == "failed":
            return [(self.now, self.now + int(cfg.plan_horizon_h * HOUR_MS))]
        day0 = self.now - (self.now % DAY_MS)
        out = []
        for d in range(-1, int(cfg.plan_horizon_h // 24) + 2):
            s = day0 + d * DAY_MS + cfg.window_open_h * HOUR_MS
            e = day0 + (d + 1) * DAY_MS + cfg.window_close_h * HOUR_MS
            out.append((s, e))
        return out

    def _techs(self):
        cfg = self.cfg
        day0 = self.now - (self.now % DAY_MS)
        out = []
        for tid, skills, start_h, end_h in cfg.technicians:
            shifts = []
            for d in range(-1, int(cfg.plan_horizon_h // 24) + 2):
                s = day0 + d * DAY_MS + start_h * HOUR_MS
                e = s + ((end_h - start_h) % 24 or 24) * HOUR_MS
                shifts.append((s, e))
            out.append(S.Tech(tid, frozenset(skills), tuple(shifts)))
        return out

    def _plan(self):
        cfg = self.cfg
        dur = {"inspect": cfg.inspect_job, "repair": cfg.repair_job, "corrective": cfg.corrective_job}
        sjobs, running = [], []
        for j in self.jobs.values():
            if j.started_ms is not None:
                d, crew = dur[j.kind]
                if j.started_ms + d * HOUR_MS > self.now:
                    running.append(S.Assignment(j.job_id, j.asset_id, j.started_ms, j.started_ms + int(d * HOUR_MS), list(j.committed.techs)))
                continue
            a = self.assets[j.asset_id]
            d, crew = dur[j.kind]
            sjobs.append(S.Job(job_id=j.job_id, asset_id=j.asset_id, skill="mech", crew=crew, duration_h=d,
                               parts={"kit": 1} if j.kind in ("repair", "corrective") else {}, windows=self._windows(a), release_ms=max(j.release_ms, self.now),
                               due_ms=j.due_ms, priority_class=j.priority if j.kind != "corrective" else "P1", criticality=a.criticality,
                               failure_cost=self.cost[a.criticality], risk=j.risk if j.kind != "corrective" else None, score=j.score))
            j.committed = None
        # the planner sees the real replenishment pipeline (one-for-one orders already placed) and cannot order extra kits
        stock = S.PartStock("kit", self.kits, cfg.kit_lead_h, arrivals=tuple((ta, 1) for ta in sorted(self.kit_orders) if ta > self.now), orderable=False)
        p = S.Problem(t0_ms=self.now, horizon_h=cfg.plan_horizon_h, slot_h=cfg.slot_h, jobs=sjobs, techs=self._techs(),
                      parts={"kit": stock}, frozen=running, previous=dict(self.prev_plan), stability_weight=self.stability)
        sch = S.plan(p, self.sched_policy, time_limit_s=cfg.milp_time_limit_s)
        self.m["plans"] += 1
        self.m["schedule_violations"] += len(S.validate(p, sch))
        if self.sched_policy == "milp" and sch.solver.get("status") != 0:
            self.m["milp_non_optimal_plans"] += 1
        self.m["milp_dropped_in_assignment"] += int(sch.solver.get("dropped_in_exact_assignment") or 0)
        self.m["unscheduled_job_days"] += len(sch.unscheduled)
        planned = {x.job_id: x.start_ms for x in sch.assignments}
        for jid, st in planned.items():
            if jid in self.prev_plan:
                self.m["plan_comparisons"] += 1
                self.m["plan_changes"] += int(abs(self.prev_plan[jid] - st) >= cfg.slot_h * HOUR_MS)
        for jid in self.prev_plan:
            if jid in self.jobs and self.jobs[jid].started_ms is None and jid not in planned:
                self.m["plan_comparisons"] += 1
                self.m["plan_changes"] += 1                 # dropped from the plan
        horizon_commit = self.now + int(cfg.commit_h * HOUR_MS)
        self.prev_plan = {}
        for x in sch.assignments:
            if x.start_ms < horizon_commit:
                self.jobs[x.job_id].committed = x
            else:
                self.prev_plan[x.job_id] = x.start_ms
        tech_avail = sum(1 for t in p.techs for s, e in t.shifts for hh in range(int((e - s) // HOUR_MS))
                         if self.now <= s + hh * HOUR_MS < horizon_commit)
        self.m["tech_hours_available"] += tech_avail

    # -- execution -----------------------------------------------------------------------------------------------
    def _fail(self, a: _Asset):
        a.status, a.failed_at = "failed", self.now
        self.m["failures"] += 1
        self.m[f"failures_{a.criticality}"] += 1
        self.m["failure_cost"] += self.cost[a.criticality]
        j = self._open_job(a.asset_id)
        if j is not None and j.kind != "corrective":
            if j.committed is not None:
                self.m["late_jobs"] += 1
            del self.jobs[j.job_id]
        self._new_job(a.asset_id, "corrective", "P1", release=self.now + int(self.cfg.corrective_delay_h * HOUR_MS))
        self.ev.append(("failure", self.now, a.asset_id, a.criticality))

    def _renew(self, a: _Asset):
        a.traj_idx, a.age_h, a.status, a.failed_at = self._draw(), 0.0, "running", None

    def _hour(self):
        cfg = self.cfg
        dur = {"inspect": cfg.inspect_job, "repair": cfg.repair_job, "corrective": cfg.corrective_job}
        arrived = [t for t in self.kit_orders if t <= self.now]
        if arrived:
            self.kits += len(arrived)
            self.kit_orders = [t for t in self.kit_orders if t > self.now]
        for j in list(self.jobs.values()):                         # finishes
            if j.started_ms is None:
                continue
            d, crew = dur[j.kind]
            if self.now >= j.started_ms + d * HOUR_MS:
                a = self.assets[j.asset_id]
                del self.jobs[j.job_id]
                if j.kind == "inspect":
                    self.m["inspections"] += 1
                    a.status = "running"
                    if self.true_rul_h(a) <= cfg.inspect_detect_cycles * cfg.hours_per_cycle:
                        self._new_job(a.asset_id, "repair", "P1", risk=None, score=None, due=self.now + DAY_MS)
                    else:
                        self.m["inspections_no_fault"] += 1
                else:
                    if j.kind == "corrective":
                        self.m["corrective_repairs"] += 1
                        self.m["unplanned_downtime_h"] += (self.now - a.failed_at) / HOUR_MS
                    self._renew(a)
        for j in sorted(self.jobs.values(), key=lambda z: z.job_id):  # starts
            if j.committed is None or j.started_ms is not None or j.committed.start_ms > self.now:
                continue
            a = self.assets[j.asset_id]
            if j.kind != "corrective" and a.status == "failed":
                continue
            if j.kind in ("repair", "corrective"):
                if self.kits < 1:
                    self.m["parts_blocked"] += 1
                    j.committed = None
                    continue
                self.kits -= 1
                self.kit_orders.append(self.now + int(cfg.kit_lead_h * HOUR_MS))
            j.started_ms = self.now
            d, crew = dur[j.kind]
            self.m["tech_hours_busy"] += d * crew
            if j.kind == "repair":
                rul = self.true_rul_h(a)
                self.m["preventive_repairs"] += 1
                self.m["discarded_life_h"] += max(rul, 0.0)
                self.m["early_repairs"] += int(rul > cfg.unnecessary_cycles * cfg.hours_per_cycle)
                self.m["planned_downtime_h"] += d
                self.m["failure_cost"] += 0.0
            if j.kind == "inspect":
                self.m["planned_downtime_h"] += d
            if a.status == "running":
                a.status = "maintenance"
        for a in self.assets.values():                             # ageing and failures
            if a.status == "running":
                a.age_h += 1.0
                if self.true_rul_h(a) <= 0:
                    self._fail(a)
        self.now += HOUR_MS

    def run(self) -> SimResult:
        for _ in range(self.cfg.days):
            self._trigger()
            self._plan()
            for _ in range(24):
                self._hour()
        m = dict(self.m)
        m["planned_repair_cost"] = m["preventive_repairs"] * self.cfg.repair_cost
        m["inspection_cost"] = m["inspections"] * self.cfg.inspect_cost
        m["total_cost"] = m["failure_cost"] + m["planned_repair_cost"] + m["inspection_cost"]
        m["mean_discarded_life_h"] = m["discarded_life_h"] / m["preventive_repairs"] if m["preventive_repairs"] else None
        m["utilisation"] = m["tech_hours_busy"] / m["tech_hours_available"] if m["tech_hours_available"] else None
        m["plan_change_rate"] = m["plan_changes"] / m["plan_comparisons"] if m["plan_comparisons"] else 0.0
        m["approvals_per_day"] = m["jobs_created"] / self.cfg.days if self.trigger in ("risk", "threshold", "threshold_scored", "interval") else 0.0
        m["inspection_no_fault_rate"] = m["inspections_no_fault"] / m["inspections"] if m["inspections"] else None
        # terminal-state accounting: assets still failed at the end were down until the end (review finding data_scientist-1)
        still = [a for a in self.assets.values() if a.status == "failed" and a.failed_at is not None]
        m["assets_failed_at_end"] = len(still)
        m["unplanned_downtime_total_h"] = m["unplanned_downtime_h"] + sum((self.now - a.failed_at) / HOUR_MS for a in still)
        fleet_h = self.cfg.n_assets * self.cfg.days * 24.0
        m["availability"] = 1.0 - (m["unplanned_downtime_total_h"] + m["planned_downtime_h"]) / fleet_h
        return SimResult(self.policy, self.scenario, self.seed, m, self.ev)


def run(trajectories, cfg: SimConfig, policy: str, seed: int, scenario: str = "base") -> SimResult:
    return FleetSim(trajectories, cfg, policy, seed, scenario).run()


SCENARIOS = {
    "base": {},
    "tight_labour": {"technicians": (("M1", ("mech",), 20, 4), ("M3", ("mech",), 22, 6), ("M4", ("mech",), 22, 6))},
    "parts_shortage": {"kit_stock": 2, "kit_lead_h": 168.0},
    "degraded_predictions": {"prediction_widen": 1.5, "prediction_bias_h": 30.0},
    "approval_delay": {"approval_delay_h": 24.0},
    "adverse": {"technicians": (("M1", ("mech",), 20, 4), ("M3", ("mech",), 22, 6), ("M4", ("mech",), 22, 6)), "kit_stock": 3, "kit_lead_h": 168.0,
                "prediction_widen": 1.5, "prediction_bias_h": 30.0, "approval_delay_h": 12.0},
}


def scenario_config(name: str, base: SimConfig | None = None) -> SimConfig:
    return replace(base or SimConfig(), **SCENARIOS[name])
