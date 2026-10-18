"""Adapter: geared onshore wind turbines monitored through 10-minute SCADA, as platform assets.

The signal set is the subset of standard 10-minute SCADA averages that a normal-behaviour temperature model for the
drivetrain needs (wind speed, active power, rotor and generator speed, pitch, ambient and nacelle temperature, and
three drivetrain temperatures). Names are this platform's canonical names. Per-site tag mapping is PLANNED
(product/KNOWN_LIMITATIONS.md P12): an operator's SCADA export must be renamed to these names and converted to these
units before ingestion (product/DATA_CONTRACTS.md). Rated power, gear ratio, plausible ranges, job durations,
crews, parts and failure consequences are ILLUSTRATIVE assumptions for a generic ~2 MW geared turbine; none comes
from a turbine maker or an operator.

There is deliberately no generic `repair` job: a temperature anomaly says that a component behaves abnormally, not
which repair it needs, so an urgent anomaly becomes an urgent inspection and a person chooses the component job.
"""
from __future__ import annotations

import math

import numpy as np

from .. import registry
from ..models import AssetSpec, AssetTypeSpec, ConsequenceSpec, JobSpec, SignalSpec, WindowSpec
from ..timeutil import DAY_MS, HOUR_MS, iso

ASSET_TYPE_ID = "wind_turbine_geared"
SITE_ID = "wind-synthetic"
RATED_KW = 2050.0                 # illustrative ~2 MW class
GEAR_RATIO = 100.0                # illustrative; generator speed ~ gear ratio x rotor speed

# name: (unit, plausible min, plausible max, description)
SIGNAL_META = {
    "wind_speed": ("m_per_s", 0.0, 50.0, "nacelle anemometer wind speed, 10-min mean"),
    "active_power": ("kW", -150.0, RATED_KW * 1.25, "active power at the turbine terminals, 10-min mean"),
    "rotor_speed": ("rpm", 0.0, 30.0, "rotor speed, 10-min mean"),
    "generator_speed": ("rpm", 0.0, 2500.0, "generator speed, 10-min mean"),
    "pitch_angle": ("deg", -10.0, 95.0, "blade pitch angle, 10-min mean"),
    "ambient_temp": ("degC", -45.0, 55.0, "ambient air temperature, 10-min mean"),
    "nacelle_temp": ("degC", -45.0, 75.0, "nacelle air temperature, 10-min mean"),
    "gearbox_oil_temp": ("degC", -45.0, 110.0, "gearbox oil sump temperature, 10-min mean"),
    "gearbox_bearing_temp": ("degC", -45.0, 130.0, "gearbox high-speed-shaft bearing temperature, 10-min mean"),
    "generator_bearing_temp": ("degC", -45.0, 130.0, "generator drive-end bearing temperature, 10-min mean"),
}
SIGNALS = list(SIGNAL_META)
TARGETS = ["gearbox_bearing_temp", "gearbox_oil_temp", "generator_bearing_temp"]
OPTIONAL_SIGNALS = {"pitch_angle"}            # carried in the contract, not read by the model: its absence is not a data failure

CONSEQUENCE = {   # illustrative only: relative units, not an operator's figures
    "A": ConsequenceSpec(downtime_hours=1440, cost_per_failure=300.0, safety_impact=False, environmental_impact=False, cost_unit="illustrative units"),
    "B": ConsequenceSpec(downtime_hours=720, cost_per_failure=120.0, safety_impact=False, environmental_impact=False, cost_unit="illustrative units"),
    "C": ConsequenceSpec(downtime_hours=240, cost_per_failure=40.0, safety_impact=False, environmental_impact=False, cost_unit="illustrative units"),
}


def asset_type_spec() -> AssetTypeSpec:
    signals = [SignalSpec(name=n, unit=u, min=lo, max=hi, required=n not in OPTIONAL_SIGNALS, description=d) for n, (u, lo, hi, d) in SIGNAL_META.items()]
    jobs = {"inspect": JobSpec(duration_h=4.0, skill="wtg_technician", crew_size=2),
            "desk_review": JobSpec(duration_h=0.5, skill="reliability_engineer"),       # no climb: a person reviews data and context
            "instrument_check": JobSpec(duration_h=2.0, skill="scada_technician"),
            "hss_bearing_exchange": JobSpec(duration_h=12.0, skill="wtg_technician", parts={"hss_bearing_kit": 1}, crew_size=3),
            "generator_bearing_exchange": JobSpec(duration_h=24.0, skill="wtg_technician", parts={"generator_bearing_kit": 1}, crew_size=3),
            "gearbox_oil_service": JobSpec(duration_h=6.0, skill="wtg_technician", parts={"gearbox_oil_drum": 2}, crew_size=2)}
    return AssetTypeSpec(asset_type_id=ASSET_TYPE_ID, name="Geared onshore wind turbine (~2 MW class, 10-min SCADA)",
                         description="Drivetrain health from 10-minute SCADA temperatures; rated power, ranges, jobs and consequences are illustrative",
                         time_basis="timestamp", signals=signals, jobs=jobs)


def ensure_site_and_type(db, actor: str, site_id: str = SITE_ID, site_name: str = "Synthetic wind farm (SYNTHETIC data)", tz: str = "UTC"):
    if registry.get_site(db, site_id) is None:
        registry.create_site(db, site_id, site_name, tz, actor=actor)
    if registry.get_asset_type(db, ASSET_TYPE_ID) is None:
        registry.create_asset_type(db, asset_type_spec(), actor=actor)


def daylight_windows(start_ms: int, days: int, open_hour: int = 7, close_hour: int = 17) -> list[WindowSpec]:
    """Climbing work in daylight (illustrative). Wind-speed limits for climbing are not modelled here."""
    day0 = start_ms - start_ms % DAY_MS
    return [WindowSpec(start=iso(day0 + d * DAY_MS + open_hour * HOUR_MS), end=iso(day0 + d * DAY_MS + close_hour * HOUR_MS)) for d in range(days)]


def create_turbine(db, turbine: str, criticality: str, actor: str, site_id: str = SITE_ID, installed_at: str = "2012-06-01T00:00:00Z",
                   windows_from_ms: int | None = None, window_days: int = 0):
    spec = AssetSpec(asset_id=turbine, tag=f"{site_id}:{turbine}", name=f"Wind turbine {turbine}", asset_type_id=ASSET_TYPE_ID, site_id=site_id,
                     criticality=criticality, consequence=CONSEQUENCE[criticality], installed_at=installed_at,
                     operating_context={"rated_kw": RATED_KW, "note": "illustrative turbine"},
                     maintenance_windows=daylight_windows(windows_from_ms, window_days) if windows_from_ms and window_days else [])
    return registry.create_asset(db, spec, actor=actor)


def records(wide, turbine_col: str = "turbine", ts_col: str = "ts_ms") -> list[dict]:
    """Wide SCADA rows (one per turbine and 10-min stamp) -> data-contract records. Missing values are left out
    (absence is what the contract uses for missing data)."""
    out = []
    for row in wide[[turbine_col, ts_col] + [s for s in SIGNALS if s in wide.columns]].itertuples(index=False):
        d = row._asdict()
        ts = iso(int(d[ts_col]))
        for s in SIGNALS:
            v = d.get(s)
            if v is None or (isinstance(v, float) and math.isnan(v)) or (isinstance(v, np.floating) and np.isnan(v)):
                continue
            out.append({"asset": d[turbine_col], "timestamp": ts, "signal": s, "value": float(v), "unit": SIGNAL_META[s][0]})
    return out
