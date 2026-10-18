"""W2: revisit the wind model's inspection margin and sustain length before G0 (SYNTHETIC; behaviour calibration only).

Adversarial review data_scientist-6: on synthetic data the W1 settings (margin 1.25, sustain 6) gave 4-5 alarm
episodes per healthy turbine-year, above the proposed pilot ceiling of 2. This grid is evaluated on TUNING fleets
(seeds 40-45) that W1 never used; the chosen setting is then checked on the W1 fleets (seeds 20-25) as held-out
synthetic data. Each fleet: 10 turbines x 60 days; WT01-WT06 one component fault each (3 components x 2 severities),
WT07 a stuck sensor, WT08 a slow bearing-sensor drift, WT09-WT10 healthy. Commissioning on the first 14 days.
Rule (fixed before running): among settings with <= 1.0 alarm episode per healthy turbine-year (WT07, WT09, WT10;
the drifting sensor is reported separately), pick the highest detection count, then the longest median lead.
Synthetic data encode our own assumptions; this calibrates behaviour, not field performance.
Run 2 (after the Phase 9 re-review fixes): the replay gates exactly like the service (the wind policy's platform data checks
run first, nbm.evaluate(policy=...)), a stuck run anywhere in the scored window is a data failure, and sustain counts
operating points. The rule is unchanged. Episodes per ASSESSABLE turbine-year are reported next to the calendar figure the
rule uses (re-review wind-eval-migrations-07). Run 1's output is kept as w2_run1.{json,md}.
Output: product/evidence/wind_synthetic/w2.{json,md}.
"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from sentinelloop.app import nbm, policy as policymod, synthetic_wind as sw  # noqa: E402
from sentinelloop.app.adapters import wind  # noqa: E402

OUT = ROOT / "product" / "evidence" / "wind_synthetic"
MARGINS, SUSTAINS = (1.25, 1.5, 2.0, 2.5), (6, 12, 18, 36)
HEALTHY = ("WT07", "WT09", "WT10")
POLICY = policymod.load(ROOT / "configs" / "platform.yaml").for_type(wind.ASSET_TYPE_ID).assessment
_B = {}


def fleet(seed):
    rng = np.random.default_rng(seed)
    faults = []
    for i, (comp, heat) in enumerate([(c, h) for c in ("hss_bearing", "generator_bearing", "oil_cooler") for h in (6.0, 18.0)]):
        st = float(rng.uniform(25, 35))
        faults.append(sw.Fault(f"WT{i + 1:02d}", comp, st, st + float(rng.uniform(10, 20)), peak_heat_c=heat))
    sf = (sw.SensorFault("WT07", "gearbox_oil_temp", "stuck", 30.0, 31.0), sw.SensorFault("WT08", "gearbox_bearing_temp", "drift", 30.0, 45.0, 8.0))
    return sw.generate(sw.FleetSpec(n_turbines=10, days=60, seed=seed, faults=tuple(faults), sensor_faults=sf))


def base_bundle():
    if "b" not in _B:
        train = sw.generate(sw.FleetSpec(n_turbines=6, days=60, seed=3)).scada
        _B["b"], _ = nbm.fit(train)
    return _B["b"]


def variant(b, margin, sustain):
    k = margin / nbm.INSPECT_MARGIN
    return replace(b, thr_inspect={t: v * k for t, v in b.thr_inspect.items()}, thr_urgent={t: v * k for t, v in b.thr_urgent.items()}, sustain=sustain)


def _one(args):
    margin, sustain, seed = args
    b = variant(base_bundle(), margin, sustain)
    g = fleet(seed)
    ev = nbm.evaluate(b, g.scada, g.labels, step_points=6, baseline_days=14, policy=POLICY)
    healthy_eps = sum(ev["per_turbine"][t]["alarm_episodes"] for t in HEALTHY)
    healthy_years = sum(ev["per_turbine"][t]["years"] for t in HEALTHY)
    healthy_years_ok = sum(ev["per_turbine"][t]["assessable_years"] for t in HEALTHY)
    return {"margin": margin, "sustain": sustain, "seed": seed, "detected": sum(d["detected"] for d in ev["detections"]), "faults": len(ev["detections"]),
            "leads": [d["lead_days"] for d in ev["detections"] if d["detected"]], "healthy_episodes": healthy_eps, "healthy_years": healthy_years, "healthy_years_ok": healthy_years_ok,
            "drift_episodes": ev["per_turbine"]["WT08"]["alarm_episodes"], "pre_onset_alarms": sum(d["alarms_before_onset"] for d in ev["detections"]),
            "assessable_share": ev["summary"]["assessable_share"]}


def summarise(rows):
    out = {}
    for r in rows:
        k = (r["margin"], r["sustain"])
        o = out.setdefault(k, {"detected": 0, "faults": 0, "leads": [], "eps": 0, "years": 0.0, "years_ok": 0.0, "drift_eps": 0, "pre": 0, "assess": []})
        o["detected"] += r["detected"]; o["faults"] += r["faults"]; o["leads"] += r["leads"]; o["eps"] += r["healthy_episodes"]
        o["years"] += r["healthy_years"]; o["years_ok"] += r["healthy_years_ok"]; o["drift_eps"] += r["drift_episodes"]; o["pre"] += r["pre_onset_alarms"]; o["assess"].append(r["assessable_share"])
    for o in out.values():
        o["eps_per_year"] = o["eps"] / o["years"] if o["years"] else None
        o["eps_per_assessable_year"] = o["eps"] / o["years_ok"] if o["years_ok"] else None
        o["median_lead"] = float(np.median(o["leads"])) if o["leads"] else None
        o["assessable"] = float(np.mean(o["assess"]))
    return out


def main():
    tune = [(m, s, seed) for m in MARGINS for s in SUSTAINS for seed in range(40, 46)]
    with ProcessPoolExecutor(max_workers=4) as ex:
        rows = list(ex.map(_one, tune))
    T = summarise(rows)
    ok = {k: v for k, v in T.items() if v["eps_per_year"] is not None and v["eps_per_year"] <= 1.0}
    chosen = max(ok, key=lambda k: (ok[k]["detected"], ok[k]["median_lead"] or 0)) if ok else None
    held = []
    # held-out settings: the chosen one, the W1 setting (1.25, 6) and run 1's choice (1.25, 12), each once. Only the chosen one
    # is the result; the others are reported for comparison (post hoc) and were not used to choose.
    compare = [k for k in dict.fromkeys([chosen, (1.25, 6), (1.25, 12)]) if k is not None]
    if chosen:
        with ProcessPoolExecutor(max_workers=4) as ex:
            held = list(ex.map(_one, [(m, s_, seed) for (m, s_) in compare for seed in range(20, 26)]))
    H = summarise(held)

    def row(k, v):
        return (f"| {k[0]} | {k[1]} | {v['detected']}/{v['faults']} | {v['median_lead']:.1f} | {v['eps']} / {v['years']:.2f} = {v['eps_per_year']:.2f} | "
                f"{v['eps_per_assessable_year']:.2f} | {v['drift_eps']} | {v['pre']} | {v['assessable']:.2f} |" if v["median_lead"] is not None else
                f"| {k[0]} | {k[1]} | {v['detected']}/{v['faults']} | - | {v['eps']} / {v['years']:.2f} = {v['eps_per_year']:.2f} | {v['eps_per_assessable_year']:.2f} | {v['drift_eps']} | {v['pre']} | {v['assessable']:.2f} |")
    hdr = ["| margin | sustain (10-min points) | detected | median lead (days) | healthy alarm episodes / turbine-years = per turbine-year (the rule's unit) | per assessable turbine-year | drifting-sensor episodes | pre-onset alarms | assessable share |",
           "|---|---|---|---|---|---|---|---|---|"]
    lines = ["# W2 inspection margin and sustain revisited (generated; SYNTHETIC; behaviour calibration only)", "",
             "Tuning fleets: seeds 40-45 (never used by W1). Held-out check: the W1 fleets (seeds 20-25). Rule fixed before running: "
             "<= 1.0 healthy alarm episode per turbine-year, then most detections, then longest median lead. Run 2: the replay gates like the "
             "service (wind policy data checks first; stuck runs anywhere in the scored window; sustain counts operating points). Run 1: w2_run1.md.",
             "", "## Tuning fleets", ""] + hdr
    lines += [row(k, v) for k, v in sorted(T.items())]
    lines += ["", f"Chosen: margin {chosen[0]}, sustain {chosen[1]}" if chosen else "No setting met the false-alarm rule.", ""]
    if chosen:
        lines += [f"## Held-out W1 fleets (seeds 20-25): the chosen setting ({chosen[0]}, {chosen[1]}); for comparison only (post hoc, not used "
                  "to choose): the W1 setting (1.25, 6) and run 1's choice (1.25, 12)", ""] + hdr
        lines += [row(k, v).replace(f"| {k[0]} | {k[1]} |", f"| {k[0]} | {k[1]}{' (chosen)' if k == tuple(chosen) else ''} |", 1)
                  for k, v in sorted(H.items())]
        y = T[tuple(chosen)]["years"]
        lines += ["", f"Exposure: the tuning fleets hold {y:.2f} healthy turbine-years. Zero episodes in that exposure has a one-sided 95% upper "
                  f"bound of {2.9957 / y:.2f} episodes per turbine-year, so the rule's 1.0 limit cannot be resolved on these fleets; the held-out rate "
                  "is the better estimate of synthetic behaviour, and only real data (G0) can estimate the field rate."]
    lines += ["", "Caveats: the generator and the model share assumptions (KNOWN_LIMITATIONS E3); a slow drift of a single temperature sensor "
                  "still cannot be told apart from heating; these numbers say nothing about real turbines."]
    (OUT / "w2.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (OUT / "w2.json").write_text(json.dumps({"tuning": {f"{k[0]}|{k[1]}": {kk: vv for kk, vv in v.items() if kk != "assess"} for k, v in T.items()},
                                             "chosen": chosen, "held_out": {f"{k[0]}|{k[1]}": {kk: vv for kk, vv in v.items() if kk != "assess"}
                                                                           for k, v in H.items()}}, indent=1, default=float), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
