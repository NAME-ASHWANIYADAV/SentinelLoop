"""W1: behaviour of the wind normal-behaviour model on SYNTHETIC SCADA (validation-ladder rung 2; not field evidence).

Train on a healthy synthetic fleet (seed 3). Evaluate on 6 independent synthetic fleets (seeds 20-25), each of
8 turbines x 60 days with one fault per faulted turbine: three components x two severities (peak heat 6 and 18 degC),
fault onset day 25-35, failure 10-20 days later, plus two healthy turbines per fleet and labelled sensor faults on
healthy turbines (stuck, drift, offset). Each turbine is commissioned on its first 14 days.
Reports detection, lead time and alarms on healthy turbines (false alarms per turbine-year).
Output: product/evidence/wind_synthetic/w1.{json,md}.
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from sentinelloop.app import nbm, synthetic_wind as sw  # noqa: E402

OUT = ROOT / "product" / "evidence" / "wind_synthetic"


def wilson(k, n, z=1.96):
    if n == 0:
        return [None, None]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(float(c - h), 3), round(float(c + h), 3)]


def main():
    train = sw.generate(sw.FleetSpec(n_turbines=6, days=60, seed=3)).scada
    b, info = nbm.fit(train)
    rows, healthy_alarm_evals, healthy_evals, healthy_days, sensor_rows = [], 0, 0, 0.0, []
    for seed in range(20, 26):
        rng = np.random.default_rng(seed)
        faults, sfaults = [], []
        for i, (comp, heat) in enumerate([(c, h) for c in ("hss_bearing", "generator_bearing", "oil_cooler") for h in (6.0, 18.0)]):
            start = float(rng.uniform(25, 35))
            faults.append(sw.Fault(f"WT{i + 1:02d}", comp, start, start + float(rng.uniform(10, 20)), peak_heat_c=heat))
        sfaults = [sw.SensorFault("WT07", "gearbox_oil_temp", "stuck", 30.0, 31.0), sw.SensorFault("WT08", "gearbox_bearing_temp", "drift", 30.0, 45.0, 8.0)]
        g = sw.generate(sw.FleetSpec(n_turbines=8, days=60, seed=seed, faults=tuple(faults), sensor_faults=tuple(sfaults)))
        ev = nbm.evaluate(b, g.scada, g.labels, step_points=6, baseline_days=14)
        for d, f in zip(ev["detections"], faults):
            rows.append({"seed": seed, "component": f.component, "peak_heat_c": f.peak_heat_c, "detected": d["detected"], "lead_days": d["lead_days"],
                         "alarms_before_onset": d["alarms_before_onset"]})
        for t in ("WT07", "WT08"):
            pt = ev["per_turbine"][t]
            sensor_rows.append({"seed": seed, "turbine": t, "fault": "stuck oil temp 1 day" if t == "WT07" else "bearing temp drift +8 degC over 15 days",
                                "data_quality_points": pt["data_quality"], "alarm_points": pt["alarm_points"]})
        # healthy exposure = pre-onset periods of faulted turbines (after commissioning) + WT07 outside [stuck day - 1, stuck day + 2];
        # WT08 (slow sensor drift) is reported separately
        for d, f in zip(ev["detections"], faults):
            healthy_alarm_evals += d["alarms_before_onset"]
            healthy_days += f.start_day - 14.0
        st = g.meta["start_ms"]
        w7 = ev["per_turbine"]["WT07"]["alarm_ms"]
        healthy_alarm_evals += sum(1 for t in w7 if not (29.0 <= (t - st) / 86_400_000 < 33.0))
        healthy_days += (60.0 - 14.0) - 4.0
    out = {"data_class": "SYNTHETIC", "train": {"seed": 3, "turbines": 6, "days": 60, **{k: v for k, v in info.items() if k != "training_turbine_offsets_z"}},
           "faults": rows, "sensor_faults": sensor_rows}
    summ = {}
    for comp in ("hss_bearing", "generator_bearing", "oil_cooler"):
        for heat in (6.0, 18.0):
            r = [x for x in rows if x["component"] == comp and x["peak_heat_c"] == heat]
            k = sum(x["detected"] for x in r)
            leads = [x["lead_days"] for x in r if x["detected"]]
            summ[f"{comp}@{heat:g}C"] = {"n": len(r), "detected": k, "wilson95": wilson(k, len(r)),
                                         "lead_days_median": round(float(np.median(leads)), 2) if leads else None,
                                         "lead_days_range": [min(leads), max(leads)] if leads else None,
                                         "alarms_before_onset": sum(x["alarms_before_onset"] for x in r)}
    out["summary"] = summ
    out["healthy_alarm_points"] = healthy_alarm_evals
    out["healthy_turbine_days"] = round(healthy_days, 1)
    out["healthy_alarm_hours_per_turbine_year"] = round(healthy_alarm_evals / (healthy_days / 365.25), 2) if healthy_days else None
    (OUT / "w1.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    lines = ["# W1 wind NBM on synthetic SCADA (generated; SYNTHETIC - behaviour check, not field evidence)", "",
             "Trained on 6 healthy synthetic turbines x 60 days (seed 3); evaluated on 6 fleets (seeds 20-25) x 8 turbines x 60 days; "
             "each turbine commissioned on its first 14 days; assessments every hour.", "",
             "| fault | n | detected | Wilson 95% | median lead (days) | lead range | alarm hours before onset |", "|---|---|---|---|---|---|---|"]
    for k, v in summ.items():
        lines.append(f"| {k} | {v['n']} | {v['detected']} | {v['wilson95']} | {v['lead_days_median']} | {v['lead_days_range']} | {v['alarms_before_onset']} |")
    lines += ["", f"Healthy exposure after commissioning: {healthy_days:.0f} turbine-days; alarm hours on it: {healthy_alarm_evals} "
                  f"({out['healthy_alarm_hours_per_turbine_year']} alarm hours per turbine-year).", "",
              "Sensor faults (on turbines without a component fault):", "", "| seed | turbine | sensor fault | data-quality points | alarm points |", "|---|---|---|---|---|"]
    for r in sensor_rows:
        lines.append(f"| {r['seed']} | {r['turbine']} | {r['fault']} | {r['data_quality_points']} | {r['alarm_points']} |")
    lines += ["", "Reading: the stuck sensor is reported as a data-quality problem; a slow sensor drift is NOT distinguishable from a heating "
                  "component by this model (no redundant temperature sensor) and raises alarms - a known limitation."]
    (OUT / "w1.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
