"""Maintenance scheduling under technicians, skills, shifts, spare parts and asset maintenance windows.

Time is split into slots of `slot_h` hours from t0. A job needs `crew` technicians holding its skill, on shift and
free for every slot it occupies; it must start and end inside one maintenance window of its asset; it may not start
before its release time or before its parts are available (stock on hand at t0; anything beyond that arrives
`lead_time_h` after t0 - an order is assumed to be placed at t0, a declared simplification). Nothing is assumed
available that is not in the problem: no shift means no capacity, no window means the job cannot be scheduled.

Objective (shared by every policy so they can be compared): the expected loss of each job's start time,
    failure_cost x P(failure before the job ends)                       when the job carries a risk interval,
    failure_cost x floor[class] x (hours from t0 to the job's end) / H  otherwise (a declared surrogate for delay),
plus, for work left unscheduled, failure_cost x max(P(failure before the horizon ends), floor[class]) x 1.5, and a tiny
tie-break towards earlier starts.

Policies: `edd` (earliest due date first), `criticality_first` (criticality A>B>C, then priority class, then due date),
`risk_greedy` (priority class, then expected loss avoided per technician-hour), all list schedulers that put each job at
its earliest feasible start; and `milp`, a time-indexed mixed-integer programme solved with HiGHS (scipy.optimize.milp).
The MILP uses aggregated per-skill capacity; specific technicians are assigned afterwards by an exact pass, and any job
that pass cannot staff is reported unscheduled. "Optimal" therefore means optimal for that model within the reported
gap, never optimal for the real plant. `validate` checks any schedule independently of the policy that produced it.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field

import numpy as np

from .risk import p_fail_before
from .timeutil import HOUR_MS, iso

FLOOR = {"P1": 0.5, "P2": 0.1, "P3": 0.02}
CRIT_RANK = {"A": 0, "B": 1, "C": 2}
CLASS_RANK = {"P1": 0, "P2": 1, "P3": 2}
EPS = 1e-6


@dataclass(frozen=True)
class Tech:
    tech_id: str
    skills: frozenset
    shifts: tuple            # ((start_ms, end_ms), ...)


@dataclass(frozen=True)
class PartStock:
    """Stock on hand at t0, known future deliveries, and whether the planner may order more (then any quantity is
    assumed to arrive lead_time_h after t0 - a declared simplification). With orderable=False only known deliveries count."""
    part_id: str
    on_hand: int
    lead_time_h: float
    arrivals: tuple = ()            # ((time_ms, qty), ...)
    orderable: bool = True


@dataclass
class Job:
    job_id: str
    asset_id: str
    skill: str
    crew: int
    duration_h: float
    parts: dict
    windows: list            # [(start_ms, end_ms)] asset maintenance windows
    release_ms: int
    due_ms: int | None
    priority_class: str
    criticality: str
    failure_cost: float
    risk: tuple | None = None   # (lower_h, point_h, upper_h, level, as_of_ms): RUL interval in hours measured from as_of
    score: float | None = None


@dataclass
class Assignment:
    job_id: str
    asset_id: str
    start_ms: int
    end_ms: int
    techs: list


@dataclass
class Problem:
    t0_ms: int
    horizon_h: float
    slot_h: float
    jobs: list
    techs: list
    parts: dict = field(default_factory=dict)       # part_id -> PartStock
    frozen: list = field(default_factory=list)      # Assignments already committed (they keep their technicians)
    previous: dict = field(default_factory=dict)    # job_id -> start_ms in the previous plan (stability preference)
    stability_weight: float = 0.0                   # 0 = no preference for keeping previous starts

    @property
    def n_slots(self) -> int:
        return int(math.floor(self.horizon_h / self.slot_h))

    def t(self, slot: int) -> int:
        return int(self.t0_ms + round(slot * self.slot_h * HOUR_MS))


@dataclass
class Schedule:
    policy: str
    assignments: list
    unscheduled: dict
    objective: float
    stats: dict
    solver: dict


# ---- costs ------------------------------------------------------------------------------------------------------
def start_cost(p: Problem, j: Job, start_ms: int) -> float:
    end_h_from_t0 = (start_ms - p.t0_ms) / HOUR_MS + j.duration_h
    if j.risk is not None:
        lo, pt, up, lvl, as_of = j.risk
        t = (start_ms - as_of) / HOUR_MS + j.duration_h
        c = j.failure_cost * p_fail_before(t, lo, pt, up, lvl)
    else:
        c = j.failure_cost * FLOOR[j.priority_class] * end_h_from_t0 / max(p.horizon_h, 1e-9)
    return c + EPS * (start_ms - p.t0_ms) / HOUR_MS


def unscheduled_cost(p: Problem, j: Job) -> float:
    if j.risk is not None:
        lo, pt, up, lvl, as_of = j.risk
        pr = p_fail_before((p.t(p.n_slots) - as_of) / HOUR_MS + j.duration_h, lo, pt, up, lvl)
    else:
        pr = 0.0
    return 1.5 * j.failure_cost * max(pr, FLOOR[j.priority_class])


def objective(p: Problem, assignments, unscheduled) -> float:
    by = {j.job_id: j for j in p.jobs}
    return float(sum(start_cost(p, by[a.job_id], a.start_ms) for a in assignments if a.job_id in by) +
                 sum(unscheduled_cost(p, by[jid]) for jid in unscheduled if jid in by))


# ---- feasibility helpers ---------------------------------------------------------------------------------------
def _k(p: Problem, j: Job) -> int:
    return max(1, int(math.ceil(j.duration_h / p.slot_h - 1e-9)))


def part_available(p: Problem, stock: PartStock, t_ms: int) -> float:
    """Units that can have been delivered by t_ms (on hand + known arrivals; unlimited after the lead time if orderable)."""
    if stock.orderable and t_ms >= p.t0_ms + int(round(stock.lead_time_h * HOUR_MS)):
        return math.inf
    return stock.on_hand + sum(q for ta, q in stock.arrivals if ta <= t_ms)


def _parts_fit(p: Problem, j: Job, start_ms: int, placed: dict) -> bool:
    """Would starting j at start_ms keep cumulative consumption within availability at every later consumption instant?"""
    for part, q in j.parts.items():
        stock = p.parts[part]
        uses = placed.get(part, [])
        for tau in sorted({start_ms} | {s for s, _ in uses if s >= start_ms}):
            used = sum(qq for s, qq in uses if s <= tau) + q
            if used > part_available(p, stock, tau):
                return False
    return True


def _missing_part(p: Problem, j: Job) -> str | None:
    for part in j.parts:
        if part not in p.parts:
            return f"part {part} is not stocked and has no known lead time"
    return None


def _window_starts(p: Problem, j: Job) -> tuple[list[int], str | None]:
    k = _k(p, j)
    rel = max(0, int(math.ceil((j.release_ms - p.t0_ms) / (p.slot_h * HOUR_MS) - 1e-9)))
    starts, any_window, long_enough = set(), False, False
    for ws, we in j.windows:
        a = max(rel, int(math.ceil((ws - p.t0_ms) / (p.slot_h * HOUR_MS) - 1e-9)))
        b = min(p.n_slots, int(math.floor((we - p.t0_ms) / (p.slot_h * HOUR_MS) + 1e-9)))
        if b > max(rel, 0) and a < p.n_slots and we > p.t0_ms:
            any_window = True
            if b - a >= k:
                long_enough = True
                starts.update(range(a, b - k + 1))
    if not any_window:
        return [], "no maintenance window of the asset falls inside the planning horizon after the release time"
    if not long_enough:
        return [], f"no window long enough for a {j.duration_h} h job"
    return sorted(starts), None


def _tech_slots(p: Problem, tech: Tech) -> np.ndarray:
    on = np.zeros(p.n_slots, dtype=bool)
    for s, e in tech.shifts:
        for i in range(p.n_slots):
            if p.t(i) >= s and p.t(i + 1) <= e:
                on[i] = True
    return on


def _busy_from_frozen(p: Problem, on_shift: dict) -> dict:
    busy = {t: np.zeros(p.n_slots, dtype=bool) for t in on_shift}
    for a in p.frozen:
        for i in range(p.n_slots):
            if p.t(i) < a.end_ms and p.t(i + 1) > a.start_ms:
                for t in a.techs:
                    if t in busy:
                        busy[t][i] = True
    return busy


# ---- greedy list scheduling ------------------------------------------------------------------------------------
ORDER = {
    "edd": lambda j: (j.due_ms if j.due_ms is not None else math.inf, j.job_id),
    "criticality_first": lambda j: (CRIT_RANK.get(j.criticality, 9), CLASS_RANK.get(j.priority_class, 9),
                                    j.due_ms if j.due_ms is not None else math.inf, j.job_id),
    "risk_greedy": lambda j: (CLASS_RANK.get(j.priority_class, 9), -(j.score or 0.0), j.due_ms if j.due_ms is not None else math.inf, j.job_id),
}


def _place(p: Problem, j: Job, starts: list[int], placed_parts: dict, on_shift: dict, busy: dict, asset_busy: dict, load: dict):
    k = _k(p, j)
    qualified = [t for t in p.techs if j.skill in t.skills]
    order = list(starts)
    prev = p.previous.get(j.job_id) if p.stability_weight > 0 else None
    if prev is not None:
        ps = int(round((prev - p.t0_ms) / (p.slot_h * HOUR_MS)))
        if ps in starts:
            order = [ps] + [s for s in starts if s != ps]      # keep yesterday's start if it is still feasible
    for s in order:
        if not _parts_fit(p, j, p.t(s), placed_parts):
            continue
        ab = asset_busy.get(j.asset_id)
        if ab is not None and ab[s:s + k].any():
            continue
        free = [t for t in qualified if on_shift[t.tech_id][s:s + k].all() and not busy[t.tech_id][s:s + k].any()]
        if len(free) >= j.crew:
            free.sort(key=lambda t: (len(t.skills), load[t.tech_id], t.tech_id))
            return s, [t.tech_id for t in free[:j.crew]]
    return None, None


def _why_not(p: Problem, j: Job, starts, placed_parts, on_shift) -> str:
    qualified = [t for t in p.techs if j.skill in t.skills]
    if not qualified:
        return f"no technician with skill {j.skill}"
    k = _k(p, j)
    staffed = [s for s in starts if sum(on_shift[t.tech_id][s:s + k].all() for t in qualified) >= j.crew]
    if not staffed:
        return f"no {j.crew} technician(s) with skill {j.skill} on shift during the asset's windows"
    if not any(_parts_fit(p, j, p.t(s), placed_parts) for s in staffed):
        info = "; ".join(f"{x}: on hand {p.parts[x].on_hand}, known deliveries {len(p.parts[x].arrivals)}, "
                         + (f"lead time {p.parts[x].lead_time_h:.0f} h" if p.parts[x].orderable else "no further orders possible")
                         for x in j.parts if x in p.parts)
        return f"parts not available in time within the horizon ({info})"
    return "capacity in the asset's windows is taken by work placed earlier by this policy"


def plan_greedy(p: Problem, policy: str) -> Schedule:
    t_start = time.time()
    on_shift = {t.tech_id: _tech_slots(p, t) for t in p.techs}
    busy = _busy_from_frozen(p, on_shift)
    load = {t.tech_id: 0 for t in p.techs}
    asset_busy: dict = {}
    for a in p.frozen:
        ab = asset_busy.setdefault(a.asset_id, np.zeros(p.n_slots, dtype=bool))
        for i in range(p.n_slots):
            if p.t(i) < a.end_ms and p.t(i + 1) > a.start_ms:
                ab[i] = True
    placed_parts: dict = {}
    assignments, unscheduled = [], {}
    for j in sorted(p.jobs, key=ORDER[policy]):
        starts, reason = _window_starts(p, j)
        if reason:
            unscheduled[j.job_id] = reason
            continue
        preason = _missing_part(p, j)
        if preason:
            unscheduled[j.job_id] = preason
            continue
        s, crew = _place(p, j, starts, placed_parts, on_shift, busy, asset_busy, load)
        if s is None:
            unscheduled[j.job_id] = _why_not(p, j, starts, placed_parts, on_shift)
            continue
        k = _k(p, j)
        for tid in crew:
            busy[tid][s:s + k] = True
            load[tid] += k
        asset_busy.setdefault(j.asset_id, np.zeros(p.n_slots, dtype=bool))[s:s + k] = True
        for part, q in j.parts.items():
            placed_parts.setdefault(part, []).append((p.t(s), q))
        assignments.append(Assignment(j.job_id, j.asset_id, p.t(s), p.t(s) + int(round(j.duration_h * HOUR_MS)), crew))
    return _finish(p, policy, assignments, unscheduled, {"method": f"greedy list scheduling ({policy})", "time_s": round(time.time() - t_start, 4)})


def _finish(p: Problem, policy, assignments, unscheduled, solver) -> Schedule:
    tech_hours = sum(len(a.techs) * (a.end_ms - a.start_ms) / HOUR_MS for a in assignments)
    avail = sum(int(_tech_slots(p, t).sum()) * p.slot_h for t in p.techs)
    late = sum(1 for a in assignments for j in p.jobs if j.job_id == a.job_id and j.due_ms is not None and a.start_ms > j.due_ms)
    stats = {"n_jobs": len(p.jobs), "n_scheduled": len(assignments), "n_unscheduled": len(unscheduled), "n_late_vs_due": late,
             "technician_hours_assigned": round(tech_hours, 2), "technician_hours_available": round(avail, 2),
             "utilisation": round(tech_hours / avail, 4) if avail else None}
    return Schedule(policy, sorted(assignments, key=lambda a: (a.start_ms, a.job_id)), unscheduled, objective(p, assignments, unscheduled), stats, solver)


# ---- MILP --------------------------------------------------------------------------------------------------------
def plan_milp(p: Problem, time_limit_s: float = 30.0, mip_rel_gap: float = 1e-4) -> Schedule:
    from scipy.optimize import Bounds, LinearConstraint, milp
    from scipy.sparse import lil_matrix

    t_start = time.time()
    on_shift = {t.tech_id: _tech_slots(p, t) for t in p.techs}
    frozen_busy = _busy_from_frozen(p, on_shift)
    skills = sorted({s for t in p.techs for s in t.skills} | {j.skill for j in p.jobs})
    cap = {s: np.zeros(p.n_slots) for s in skills}
    total = np.zeros(p.n_slots)
    for t in p.techs:
        avail = on_shift[t.tech_id] & ~frozen_busy[t.tech_id]
        total += avail
        for s in t.skills:
            cap[s] += avail
    var_job, var_slot, costs = [], [], []
    unscheduled, starts_of = {}, {}
    for j in p.jobs:
        starts, reason = _window_starts(p, j)
        if reason:
            unscheduled[j.job_id] = reason
            continue
        if not any(j.skill in t.skills for t in p.techs):
            unscheduled[j.job_id] = f"no technician with skill {j.skill}"
            continue
        missing = [x for x in j.parts if x not in p.parts]
        if missing:
            unscheduled[j.job_id] = f"part {missing[0]} is not stocked and has no known lead time"
            continue
        starts_of[j.job_id] = starts
        prev = p.previous.get(j.job_id) if p.stability_weight > 0 else None
        ps = None if prev is None else int(round((prev - p.t0_ms) / (p.slot_h * HOUR_MS)))
        for s in starts:
            pen = 0.0 if ps is None or s == ps else p.stability_weight * FLOOR[j.priority_class] * j.failure_cost
            var_job.append(j.job_id); var_slot.append(s); costs.append(start_cost(p, j, p.t(s)) + pen)
    jobs_in = [j for j in p.jobs if j.job_id in starts_of]
    n_x = len(costs)
    n = n_x + len(jobs_in)
    if n == 0:                                  # nothing the optimiser could place: a valid, empty plan
        return _finish(p, "milp", [], unscheduled, {"method": "time-indexed MILP, HiGHS via scipy.optimize.milp", "status": 0,
                                                     "status_text": "no schedulable jobs", "mip_gap": 0.0, "n_variables": 0, "n_constraints": 0,
                                                     "time_s": round(time.time() - t_start, 3), "caveat": "optimal (trivially) for the aggregated model"})
    c = np.array(costs + [unscheduled_cost(p, j) for j in jobs_in])
    rows, lb, ub = [], [], []
    n_part_rows = sum(len(s.arrivals) + 2 for s in p.parts.values())
    A = lil_matrix((len(jobs_in) + (len(skills) + 1) * p.n_slots + n_part_rows + len({j.asset_id for j in jobs_in}) * p.n_slots, n))
    r = 0
    idx_by_job: dict = {}
    for i, (jid, s) in enumerate(zip(var_job, var_slot)):
        idx_by_job.setdefault(jid, []).append((i, s))
    jmap = {j.job_id: j for j in jobs_in}
    for u, j in enumerate(jobs_in):                                   # each job starts once or is left unscheduled
        for i, _ in idx_by_job[j.job_id]:
            A[r, i] = 1
        A[r, n_x + u] = 1
        lb.append(1); ub.append(1); r += 1
    for s_name in skills + ["__all__"]:                               # aggregated capacity per skill and in total
        for tslot in range(p.n_slots):
            for i, (jid, s) in enumerate(zip(var_job, var_slot)):
                j = jmap[jid]
                if (s_name == "__all__" or j.skill == s_name) and s <= tslot < s + _k(p, j):
                    A[r, i] = j.crew
            lb.append(-np.inf); ub.append(float(total[tslot] if s_name == "__all__" else cap[s_name][tslot])); r += 1
    for part, stock in p.parts.items():                               # cumulative use <= deliveries, checked before each increase
        checks = {int(math.ceil((ta - p.t0_ms) / (p.slot_h * HOUR_MS) - 1e-9)) - 1 for ta, _ in stock.arrivals}
        if stock.orderable:
            lead_slot = int(math.ceil(stock.lead_time_h / p.slot_h - 1e-9))
            checks = {c for c in checks if c < lead_slot - 1} | {min(lead_slot, p.n_slots) - 1}
        else:
            checks |= {p.n_slots - 1}
        for cslot in sorted(c for c in checks if 0 <= c < p.n_slots):
            for i, (jid, s) in enumerate(zip(var_job, var_slot)):
                q = jmap[jid].parts.get(part, 0)
                if q and s <= cslot:
                    A[r, i] = q
            lb.append(-np.inf); ub.append(float(part_available(p, stock, p.t(cslot)))); r += 1
    for asset in sorted({j.asset_id for j in jobs_in}):              # one job at a time per asset
        for tslot in range(p.n_slots):
            for i, (jid, s) in enumerate(zip(var_job, var_slot)):
                j = jmap[jid]
                if j.asset_id == asset and s <= tslot < s + _k(p, j):
                    A[r, i] = 1
            lb.append(-np.inf); ub.append(1.0); r += 1
    A = A[:r].tocsr()
    res = milp(c, constraints=[LinearConstraint(A, lb, ub)], integrality=np.ones(n), bounds=Bounds(0, 1),
               options={"time_limit": float(time_limit_s), "mip_rel_gap": float(mip_rel_gap), "disp": False})
    solver = {"method": "time-indexed MILP, HiGHS via scipy.optimize.milp", "status": int(res.status), "status_text": str(res.message),
              "mip_gap": None if getattr(res, "mip_gap", None) is None else float(res.mip_gap), "n_variables": int(n), "n_constraints": int(r),
              "time_s": None, "caveat": "optimal (within the reported gap) only for the time-indexed model with aggregated per-skill capacity; "
                                      "technicians are then assigned exactly and any job that cannot be staffed is reported unscheduled"}
    if res.x is None:
        g = plan_greedy(p, "risk_greedy")
        solver.update({"fallback": "risk_greedy (no feasible MILP solution within the time limit)", "time_s": round(time.time() - t_start, 3)})
        return Schedule("milp", g.assignments, g.unscheduled, g.objective, g.stats, solver)
    x = np.round(res.x).astype(int)
    chosen = []
    for u, j in enumerate(jobs_in):
        picks = [s for i, s in idx_by_job[j.job_id] if x[i] == 1]
        if picks:
            chosen.append((picks[0], j))
        else:
            unscheduled[j.job_id] = "left unscheduled by the optimiser: capacity, parts or windows are better used by other work"
    # exact technician assignment in start order
    busy = {t: frozen_busy[t].copy() for t in frozen_busy}
    load = {t.tech_id: 0 for t in p.techs}
    assignments, dropped = [], 0
    for s, j in sorted(chosen, key=lambda z: (z[0], CLASS_RANK.get(z[1].priority_class, 9))):
        k = _k(p, j)
        free = [t for t in p.techs if j.skill in t.skills and on_shift[t.tech_id][s:s + k].all() and not busy[t.tech_id][s:s + k].any()]
        if len(free) < j.crew:
            unscheduled[j.job_id] = "optimiser slot could not be staffed by specific technicians (aggregated-capacity relaxation)"
            dropped += 1
            continue
        free.sort(key=lambda t: (len(t.skills), load[t.tech_id], t.tech_id))
        crew = [t.tech_id for t in free[:j.crew]]
        for tid in crew:
            busy[tid][s:s + k] = True
            load[tid] += k
        assignments.append(Assignment(j.job_id, j.asset_id, p.t(s), p.t(s) + int(round(j.duration_h * HOUR_MS)), crew))
    solver.update({"dropped_in_exact_assignment": dropped, "time_s": round(time.time() - t_start, 3)})
    return _finish(p, "milp", assignments, unscheduled, solver)


def plan(p: Problem, policy: str, time_limit_s: float = 30.0) -> Schedule:
    if policy == "milp":
        return plan_milp(p, time_limit_s=time_limit_s)
    if policy not in ORDER:
        raise ValueError(f"unknown policy {policy!r}; choose from {sorted(ORDER) + ['milp']}")
    return plan_greedy(p, policy)


# ---- independent validation ------------------------------------------------------------------------------------
def validate(p: Problem, s: Schedule) -> list[str]:
    jobs = {j.job_id: j for j in p.jobs}
    techs = {t.tech_id: t for t in p.techs}
    out = []
    all_a = list(p.frozen) + list(s.assignments)
    for a in s.assignments:
        j = jobs.get(a.job_id)
        if j is None:
            out.append(f"{a.job_id}: not a job of this problem"); continue
        if a.end_ms - a.start_ms < int(round(j.duration_h * HOUR_MS)) - 1:
            out.append(f"{a.job_id}: shorter than its duration")
        if a.start_ms < j.release_ms:
            out.append(f"{a.job_id}: starts before its release time")
        if not any(ws <= a.start_ms and a.end_ms <= we for ws, we in j.windows):
            out.append(f"{a.job_id}: outside every maintenance window of {j.asset_id}")
        if len(a.techs) != j.crew:
            out.append(f"{a.job_id}: crew of {len(a.techs)} but the job needs {j.crew}")
        for tid in a.techs:
            t = techs.get(tid)
            if t is None:
                out.append(f"{a.job_id}: unknown technician {tid}"); continue
            if j.skill not in t.skills:
                out.append(f"{a.job_id}: technician {tid} lacks skill {j.skill}")
            if not any(ss <= a.start_ms and a.end_ms <= se for ss, se in t.shifts):
                out.append(f"{a.job_id}: technician {tid} not on shift for the whole job")
    for i, a in enumerate(all_a):
        for b in all_a[i + 1:]:
            if a.start_ms < b.end_ms and b.start_ms < a.end_ms:
                for tid in set(a.techs) & set(b.techs):
                    out.append(f"technician {tid} double-booked on {a.job_id} and {b.job_id}")
                if a.asset_id == b.asset_id:
                    out.append(f"asset {a.asset_id} has overlapping jobs {a.job_id} and {b.job_id}")
    for part, stock in p.parts.items():
        uses = sorted((a.start_ms, jobs[a.job_id].parts.get(part, 0)) for a in s.assignments if a.job_id in jobs and jobs[a.job_id].parts.get(part))
        used = 0
        for tau, q in uses:
            used += q
            if used > part_available(p, stock, tau):
                out.append(f"part {part}: {used} used by {iso(tau)} but only {part_available(p, stock, tau)} can have been delivered")
                break
    for a in s.assignments:
        for part in jobs[a.job_id].parts if a.job_id in jobs else {}:
            if part not in p.parts:
                out.append(f"{a.job_id}: part {part} has no stock record")
    return out
