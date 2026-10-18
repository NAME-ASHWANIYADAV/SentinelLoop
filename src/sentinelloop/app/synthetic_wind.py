"""Synthetic 10-minute SCADA for a small fleet of geared wind turbines, with labelled faults (SYNTHETIC data only).

Purpose: behaviour testing of the platform (does a known injected fault get flagged, are sensor problems reported as
data problems, are unfamiliar conditions out of scope). It is NOT evidence about real turbines: the physics is a
deliberately simple, declared approximation, and a model that does well here can still fail on field data.

Model (all parameters below are assumptions):
- Wind: a farm-level and a turbine-level AR(1) Gaussian process mapped through the normal CDF to a Weibull(k, c)
  marginal, with a mild diurnal modulation.
- Power: cubic between cut-in (3 m/s) and rated (12 m/s), rated up to cut-out (25 m/s), 1.5% noise; rotor speed
  rises linearly with wind to its rated speed; generator speed = gear ratio x rotor speed; pitch opens above rated.
- Temperatures: ambient with a diurnal cycle; nacelle and drivetrain temperatures follow ambient plus a
  load-dependent rise through first-order thermal lags (time constants 40-90 min), plus small noise and a small
  per-turbine offset. Values are rounded to 0.1 degC like typical SCADA exports.
- Component faults add heat that grows as ((t - start)/(failure - start))^2.5, scaled by load, to the affected
  temperatures; after the failure instant the turbine is stopped for the rest of the record.
- Sensor faults (stuck, dropout, drift, offset, spike) are applied after the physics and labelled separately.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

import numpy as np
import pandas as pd
from scipy.signal import lfilter
from scipy.stats import norm

from .adapters.wind import GEAR_RATIO, RATED_KW, SIGNALS
from .timeutil import DAY_MS, parse_ts

STEP_MS = 10 * 60 * 1000
PER_DAY = 144
COMPONENT_EFFECT = {          # component -> {temperature: share of the fault heat}
    "hss_bearing": {"gearbox_bearing_temp": 1.0, "gearbox_oil_temp": 0.25},
    "generator_bearing": {"generator_bearing_temp": 1.0},
    "oil_cooler": {"gearbox_oil_temp": 1.0, "gearbox_bearing_temp": 0.5},
}


@dataclass(frozen=True)
class Fault:
    turbine: str
    component: str                 # hss_bearing | generator_bearing | oil_cooler
    start_day: float
    fail_day: float
    peak_heat_c: float = 18.0      # extra temperature at full load at the failure instant


@dataclass(frozen=True)
class SensorFault:
    turbine: str
    signal: str
    kind: str                      # stuck | dropout | drift | offset | spike
    start_day: float
    end_day: float
    magnitude: float = 0.0


@dataclass(frozen=True)
class FleetSpec:
    n_turbines: int = 4
    days: int = 30
    seed: int = 0
    start: str = "2026-01-05T00:00:00Z"
    ambient_mean_c: float = 27.0
    ambient_diurnal_amp_c: float = 4.0
    weibull_k: float = 2.0
    weibull_c: float = 7.5
    faults: tuple = ()
    sensor_faults: tuple = ()


@dataclass
class Generated:
    scada: pd.DataFrame
    labels: list
    sensor_fault_labels: list
    meta: dict = field(default_factory=dict)


def _lag(x: np.ndarray, tau_steps: float, x0: float) -> np.ndarray:
    a = float(np.exp(-1.0 / tau_steps))
    y, _ = lfilter([1 - a], [1, -a], x, zi=[a * x0])
    return y


def _ar1(rng, n: int, phi: float) -> np.ndarray:
    e = rng.normal(0.0, np.sqrt(1 - phi ** 2), n)
    y, _ = lfilter([1.0], [1, -phi], e, zi=[phi * rng.normal()])
    return y


def _turbine(rng, spec: FleetSpec, z_farm: np.ndarray, hours: np.ndarray, faults: list) -> dict:
    n = len(z_farm)
    z = 0.9 * z_farm + np.sqrt(1 - 0.81) * _ar1(rng, n, 0.97)
    u = np.clip(norm.cdf(z), 1e-9, 1 - 1e-9)
    wind = spec.weibull_c * (-np.log(1 - u)) ** (1 / spec.weibull_k)
    wind = wind * (1 + 0.12 * np.sin(2 * np.pi * (hours - 15) / 24))
    wind = np.clip(wind + rng.normal(0, 0.15, n), 0, None)
    cut_in, rated_v, cut_out = 3.0, 12.0, 25.0
    p = np.where(wind < cut_in, 0.0, np.where(wind < rated_v, (wind ** 3 - cut_in ** 3) / (rated_v ** 3 - cut_in ** 3), 1.0))
    p = np.where(wind > cut_out, 0.0, p)
    running = p > 0
    p = np.where(running, np.clip(p + rng.normal(0, 0.015, n), 0.0, 1.01), 0.0)
    rotor = np.where(running, np.minimum(16.8, 6.0 + (wind - cut_in) * 1.35), rng.uniform(0.0, 0.8, n))
    rotor = rotor + np.where(running, rng.normal(0, 0.08, n), 0.0)
    pitch = np.where(running, np.maximum(0.0, (wind - rated_v) * 2.2), 85.0) + rng.normal(0, 0.3, n)

    off = rng.normal(0, 0.4, 4)                                           # small per-turbine thermal offsets
    amb = spec.ambient_mean_c + spec.ambient_diurnal_amp_c * np.sin(2 * np.pi * (hours - 9) / 24) + 1.2 * _ar1(rng, n, 0.995)
    load = p * RATED_KW
    stopped = np.zeros(n, dtype=bool)
    heat = {k: np.zeros(n) for k in ("gearbox_bearing_temp", "gearbox_oil_temp", "generator_bearing_temp")}
    t_day = np.arange(n) / PER_DAY
    for f in faults:
        frac = np.clip((t_day - f.start_day) / max(f.fail_day - f.start_day, 1e-9), 0.0, 1.0)
        active = (t_day >= f.start_day) & (t_day < f.fail_day)
        h = np.where(active, f.peak_heat_c * frac ** 2.5, 0.0) * (0.3 + 0.7 * p)
        for sig, share in COMPONENT_EFFECT[f.component].items():
            heat[sig] += share * h
        stopped |= t_day >= f.fail_day
    load = np.where(stopped, 0.0, load)
    p_eff = np.where(stopped, 0.0, p)
    rotor = np.where(stopped, 0.0, rotor)
    pitch = np.where(stopped, 90.0, pitch)
    nacelle = _lag(amb + 6.0 + off[0] + 4.0 * p_eff, 12.0, amb[0] + 6.0) + rng.normal(0, 0.25, n)
    oil = _lag(amb + 12.0 + off[1] + 0.012 * load + heat["gearbox_oil_temp"], 9.0, amb[0] + 12.0) + rng.normal(0, 0.3, n)
    brg = _lag(amb + 15.0 + off[2] + 0.016 * load + heat["gearbox_bearing_temp"], 4.0, amb[0] + 15.0) + rng.normal(0, 0.35, n)
    gen = _lag(amb + 10.0 + off[3] + 0.010 * load + heat["generator_bearing_temp"], 6.0, amb[0] + 10.0) + rng.normal(0, 0.3, n)
    return {"wind_speed": np.round(wind, 2), "active_power": np.round(load + np.where(load > 0, 0, rng.uniform(-8, 0, n)) * (~stopped), 1),
            "rotor_speed": np.round(rotor, 2), "generator_speed": np.round(np.where(rotor > 0, rotor * GEAR_RATIO + rng.normal(0, 2.0, n), 0.0), 1),
            "pitch_angle": np.round(pitch, 1), "ambient_temp": np.round(amb, 1), "nacelle_temp": np.round(nacelle, 1),
            "gearbox_oil_temp": np.round(oil, 1), "gearbox_bearing_temp": np.round(brg, 1), "generator_bearing_temp": np.round(gen, 1)}


def _apply_sensor_fault(rng, cols: dict, sf: SensorFault):
    n = len(cols[sf.signal])
    t_day = np.arange(n) / PER_DAY
    m = (t_day >= sf.start_day) & (t_day < sf.end_day)
    if not m.any():
        return
    v = cols[sf.signal].astype(float)
    i0 = int(np.argmax(m))
    if sf.kind == "stuck":
        v[m] = v[max(i0 - 1, 0)]
    elif sf.kind == "dropout":
        v[m] = np.nan
    elif sf.kind == "drift":
        v[m] = v[m] + sf.magnitude * (t_day[m] - sf.start_day) / max(sf.end_day - sf.start_day, 1e-9)
    elif sf.kind == "offset":
        v[m] = v[m] + sf.magnitude
    elif sf.kind == "spike":
        idx = np.flatnonzero(m)
        pick = idx[rng.random(len(idx)) < 0.02]
        v[pick] = v[pick] + sf.magnitude
    else:
        raise ValueError(f"unknown sensor fault kind {sf.kind!r}")
    cols[sf.signal] = v


def generate(spec: FleetSpec) -> Generated:
    start_ms = parse_ts(spec.start)
    n = spec.days * PER_DAY
    ts = start_ms + np.arange(n, dtype=np.int64) * STEP_MS
    hours = ((ts // 3_600_000) % 24).astype(float) + ((ts // 60_000) % 60) / 60.0
    seqs = np.random.SeedSequence(spec.seed).spawn(spec.n_turbines + 2)
    farm_rng = np.random.default_rng(seqs[0])
    z_farm = _ar1(farm_rng, n, 0.995)
    names = [f"WT{i + 1:02d}" for i in range(spec.n_turbines)]
    frames, labels, sf_labels = [], [], []
    for i, name in enumerate(names):
        rng = np.random.default_rng(seqs[i + 1])
        faults = [f for f in spec.faults if f.turbine == name]
        cols = _turbine(rng, spec, z_farm, hours, faults)
        for sf in (s for s in spec.sensor_faults if s.turbine == name):
            _apply_sensor_fault(rng, cols, sf)
            sf_labels.append({**asdict(sf), "start_ms": int(start_ms + sf.start_day * DAY_MS), "end_ms": int(start_ms + sf.end_day * DAY_MS),
                              "data_class": "SYNTHETIC"})
        for f in faults:
            labels.append({"turbine": name, "component": f.component, "fault_start_ms": int(start_ms + f.start_day * DAY_MS),
                           "failure_ms": int(start_ms + f.fail_day * DAY_MS), "peak_heat_c": f.peak_heat_c, "data_class": "SYNTHETIC"})
        frames.append(pd.DataFrame({"turbine": name, "ts_ms": ts, **{s: cols[s] for s in SIGNALS}}))
    unknown = {f.turbine for f in spec.faults} - set(names) | {s.turbine for s in spec.sensor_faults} - set(names)
    if unknown:
        raise ValueError(f"faults refer to unknown turbines: {sorted(unknown)}")
    meta = {"data_class": "SYNTHETIC", "generator": "sentinelloop.app.synthetic_wind", "generator_version": "1", "start_ms": int(start_ms),
            "rated_kw": RATED_KW, "spec": asdict(spec),
            "note": "simple declared physics for behaviour tests; not evidence about real turbines"}
    return Generated(pd.concat(frames, ignore_index=True), labels, sf_labels, meta)
