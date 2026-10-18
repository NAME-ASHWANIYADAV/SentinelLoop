"""Adapter: NASA C-MAPSS simulated turbofan engines as platform assets.

C-MAPSS has no timestamps: rows are flight cycles. The adapter maps cycle k of an engine to
installed_at + k * hours_per_cycle (default 3 h, a DECLARED ASSUMPTION, not a property of the data) and marks the
asset type `time_basis = cycle_index`, which every assessment carries. Fleet loading aligns every engine's last
observed cycle on one instant (END_MS), which is how the official test files behave: engines of different ages,
all observed "now". Criticality, failure consequences, maintenance windows and job definitions are ILLUSTRATIVE
assumptions for exercising the platform; none comes from an airline or an engine maker.

Sensor meanings and units follow the C-MAPSS documentation as commonly reproduced in the literature (Saxena et al.,
PHM08); they were not re-verified against the original document in this workspace.
"""
from __future__ import annotations

import numpy as np

from ... import data as cdata
from ...config import SUBSETS
from .. import ingest, registry
from ..models import AssetSpec, AssetTypeSpec, ConsequenceSpec, JobSpec, SignalSpec, WindowSpec
from ..timeutil import HOUR_MS, DAY_MS, iso, parse_ts

ASSET_TYPE_ID = "cmapss_turbofan"
SITE_ID = "cmapss-sim"
START_MS = parse_ts("2026-01-01T00:00:00Z")
END_MS = parse_ts("2026-03-01T00:00:00Z")

SIGNAL_META = {
    "os1": ("altitude setting (kft)", "kft"), "os2": ("Mach number setting", "Mach"), "os3": ("throttle resolver angle setting", "TRA_pct"),
    "s1": ("T2 total temperature at fan inlet", "degR"), "s2": ("T24 total temperature at LPC outlet", "degR"),
    "s3": ("T30 total temperature at HPC outlet", "degR"), "s4": ("T50 total temperature at LPT outlet", "degR"),
    "s5": ("P2 pressure at fan inlet", "psia"), "s6": ("P15 total pressure in bypass duct", "psia"), "s7": ("P30 total pressure at HPC outlet", "psia"),
    "s8": ("Nf physical fan speed", "rpm"), "s9": ("Nc physical core speed", "rpm"), "s10": ("epr engine pressure ratio P50/P2", "ratio"),
    "s11": ("Ps30 static pressure at HPC outlet", "psia"), "s12": ("phi ratio of fuel flow to Ps30", "pps_per_psi"),
    "s13": ("NRf corrected fan speed", "rpm"), "s14": ("NRc corrected core speed", "rpm"), "s15": ("BPR bypass ratio", "ratio"),
    "s16": ("farB burner fuel-air ratio", "ratio"), "s17": ("htBleed bleed enthalpy", "enthalpy_units"), "s18": ("Nf_dmd demanded fan speed", "rpm"),
    "s19": ("PCNfR_dmd demanded corrected fan speed", "rpm"), "s20": ("W31 HPT coolant bleed", "lbm_per_s"), "s21": ("W32 LPT coolant bleed", "lbm_per_s"),
}
CONSEQUENCE = {   # illustrative only
    "A": ConsequenceSpec(downtime_hours=72, cost_per_failure=1_000_000, safety_impact=True, environmental_impact=False, cost_unit="illustrative units"),
    "B": ConsequenceSpec(downtime_hours=48, cost_per_failure=400_000, safety_impact=False, environmental_impact=False, cost_unit="illustrative units"),
    "C": ConsequenceSpec(downtime_hours=24, cost_per_failure=150_000, safety_impact=False, environmental_impact=False, cost_unit="illustrative units"),
}


def _ranges(data_dir) -> dict:
    """Plausibility ranges for the data contract: union of all available C-MAPSS training files, +-25% of the span."""
    lo, hi = {}, {}
    for s in SUBSETS:
        try:
            ds = cdata.load_subset(s, data_dir)
        except Exception:
            continue
        for c in cdata.OS_COLS + cdata.SENSORS:
            lo[c] = min(lo.get(c, np.inf), float(ds.train[c].min()))
            hi[c] = max(hi.get(c, -np.inf), float(ds.train[c].max()))
    out = {}
    for c in lo:
        span = max(hi[c] - lo[c], abs(hi[c]) * 0.01, 1e-3)
        out[c] = (lo[c] - 0.25 * span, hi[c] + 0.25 * span)
    return out


def asset_type_spec(hours_per_cycle: float = 3.0, data_dir="data/raw") -> AssetTypeSpec:
    rng = _ranges(data_dir)
    signals = [SignalSpec(name=c, unit=SIGNAL_META[c][1], min=rng.get(c, (None, None))[0], max=rng.get(c, (None, None))[1], required=True,
                          description=SIGNAL_META[c][0]) for c in cdata.OS_COLS + cdata.SENSORS]
    jobs = {"inspect": JobSpec(duration_h=4.0, skill="engine_mechanic"),
            "repair": JobSpec(duration_h=24.0, skill="engine_mechanic", parts={"hpc_module_kit": 1}, crew_size=2),
            "replace": JobSpec(duration_h=16.0, skill="engine_mechanic", parts={"spare_engine": 1}, crew_size=3),
            "instrument_check": JobSpec(duration_h=2.0, skill="avionics_technician")}
    return AssetTypeSpec(asset_type_id=ASSET_TYPE_ID, name="Turbofan engine (NASA C-MAPSS, simulated)",
                         description="Simulated engines from NASA C-MAPSS; time basis is the flight cycle; jobs and durations are illustrative assumptions",
                         time_basis="cycle_index", usage_hours_per_cycle=hours_per_cycle, signals=signals, jobs=jobs)


def ensure_site_and_type(db, actor: str, hours_per_cycle: float = 3.0, data_dir="data/raw", site_id: str = SITE_ID):
    if registry.get_site(db, site_id) is None:
        registry.create_site(db, site_id, "C-MAPSS simulated fleet", "UTC", actor=actor)
    if registry.get_asset_type(db, ASSET_TYPE_ID) is None:
        registry.create_asset_type(db, asset_type_spec(hours_per_cycle, data_dir), actor=actor)


def cycle_to_ms(installed_ms: int, cycle: int, hours_per_cycle: float) -> int:
    return int(installed_ms + round(cycle * hours_per_cycle * HOUR_MS))


def ms_to_cycle(installed_ms: int, ts_ms: int, hours_per_cycle: float) -> int:
    return int(round((ts_ms - installed_ms) / (hours_per_cycle * HOUR_MS)))


def daily_windows(start_ms: int, days: int, open_hour: int = 20, close_hour: int = 6) -> list[WindowSpec]:
    day0 = start_ms - start_ms % DAY_MS
    return [WindowSpec(start=iso(day0 + d * DAY_MS + open_hour * HOUR_MS), end=iso(day0 + (d + 1) * DAY_MS + close_hour * HOUR_MS)) for d in range(days)]


def asset_spec(asset_id: str, criticality: str, installed_ms: int, site_id: str = SITE_ID, windows_days: int = 120) -> AssetSpec:
    return AssetSpec(asset_id=asset_id, tag=asset_id, name=f"Engine {asset_id}", asset_type_id=ASSET_TYPE_ID, site_id=site_id, location="line maintenance base",
                     criticality=criticality, consequence=CONSEQUENCE[criticality], installed_at=iso(installed_ms),
                     maintenance_windows=daily_windows(max(installed_ms, START_MS), windows_days),
                     operating_context={"source": "NASA C-MAPSS simulation", "illustrative": True})


def unit_records(unit_df, asset_id: str, installed_ms: int, hours_per_cycle: float) -> list[dict]:
    recs = []
    cols = cdata.OS_COLS + cdata.SENSORS
    for row in unit_df.sort_values("cycle").itertuples(index=False):
        cyc = int(getattr(row, "cycle"))
        ts = iso(cycle_to_ms(installed_ms, cyc, hours_per_cycle))
        for c in cols:
            v = getattr(row, c)
            recs.append({"asset": asset_id, "timestamp": ts, "signal": c, "value": None if v != v else float(v), "unit": SIGNAL_META[c][1], "_cycle": cyc})
    return recs


def load_fleet(db, subset: str, split: str, actor: str, units=None, hours_per_cycle: float = 3.0, data_dir="data/raw", site_id: str = SITE_ID,
               id_prefix: str | None = None, end_ms: int = END_MS, criticality_seed: int = 42) -> list[str]:
    """Register the engines of one C-MAPSS file as assets and ingest their readings; returns asset ids."""
    ensure_site_and_type(db, actor, hours_per_cycle, data_dir, site_id)
    ds = cdata.load_subset(subset, data_dir)
    df = ds.test if split == "test" else ds.train
    all_units = sorted(int(u) for u in df["unit"].unique())
    units = all_units if units is None else [int(u) for u in units]
    rng = np.random.default_rng(criticality_seed)
    crit = {u: str(c) for u, c in zip(all_units, rng.choice(["A", "B", "C"], size=len(all_units), p=[0.2, 0.5, 0.3]))}
    ids = []
    for u in units:
        g = df[df.unit == u]
        n = int(g["cycle"].max())
        installed = int(end_ms - round(n * hours_per_cycle * HOUR_MS))
        asset_id = f"{(id_prefix + '-') if id_prefix else ''}{subset}-{split[:2]}-{u:03d}"
        if registry.get_asset(db, asset_id) is None:
            registry.create_asset(db, asset_spec(asset_id, crit[u], installed, site_id), actor=actor)
        res = ingest.ingest_records(db, unit_records(g, asset_id, installed, hours_per_cycle), source=f"cmapss:{subset}:{split}:unit{u}", actor=actor)
        if res.status == "rejected":
            raise RuntimeError(f"ingestion of {asset_id} rejected: {res.errors[:3]}")
        ids.append(asset_id)
    return ids
