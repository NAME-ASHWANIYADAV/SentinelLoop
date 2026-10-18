"""W3: wind inspection margin and sustain chosen on a pooled synthetic tuning set, checked on fresh fleets (SYNTHETIC).

Why (written before this script was run; the commit that adds this file is its date stamp):
W2 run 2 (product/evidence/wind_synthetic/w2.md) chose margin 1.25, sustain 6 on tuning fleets 40-45. Those fleets hold only
2.27 healthy turbine-years: nearly every setting gave 0 healthy alarm episodes, and 0 in 2.27 turbine-years cannot rule
out a rate of 1.32 per turbine-year, so W2's 1.0 limit could not be resolved. On the held-out W1 fleets (20-25) the
chosen setting gave 5.74 per turbine-year. Choosing another setting from that held-out comparison would turn the held-out
fleets into tuning data. W3 therefore pools both seen sets for tuning and checks the choice on fleets no run has used.

Protocol (fixed now):
- Tuning: fleets 40-45 and 20-25 (12 fleets, about 4.53 healthy turbine-years), the same 16-setting grid as W2, the same
  fleet design and the same service-equivalent replay (w2._one: the wind policy's data checks first, stuck runs anywhere in
  the scored window, sustain counted in operating points, commissioning on the first 14 days).
- Rule: among settings with <= 1.0 healthy alarm episode per calendar turbine-year (healthy = WT07, WT09, WT10; the
  drifting sensor WT08 is reported separately), pick the most detections, then the longest median lead. If no setting
  meets the limit, pick the lowest healthy rate, then the most detections, then the longest median lead.
- Held-out: fleets 60-65, never used before, evaluated for the chosen setting only. Its result is reported as it comes;
  it is not used to choose again.
- The chosen setting becomes the product default (nbm.INSPECT_MARGIN, nbm.SUSTAIN); a test ties the code to w3.json.
Synthetic data encode our own assumptions; this calibrates behaviour, not field performance.
Output: product/evidence/wind_synthetic/w3.{json,md}.
"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import w2_threshold_revisit as w2  # noqa: E402

TUNE_SEEDS, HELD_SEEDS = tuple(range(40, 46)) + tuple(range(20, 26)), tuple(range(60, 66))


def choose(T):
    ok = {k: v for k, v in T.items() if v["eps_per_year"] is not None and v["eps_per_year"] <= 1.0}
    if ok:
        return max(ok, key=lambda k: (ok[k]["detected"], ok[k]["median_lead"] or 0)), True
    return min(T, key=lambda k: (T[k]["eps_per_year"], -T[k]["detected"], -(T[k]["median_lead"] or 0))), False


def main():
    with ProcessPoolExecutor(max_workers=4) as ex:
        rows = list(ex.map(w2._one, [(m, s, seed) for m in w2.MARGINS for s in w2.SUSTAINS for seed in TUNE_SEEDS]))
    T = w2.summarise(rows)
    chosen, met = choose(T)
    with ProcessPoolExecutor(max_workers=4) as ex:
        held = list(ex.map(w2._one, [(chosen[0], chosen[1], seed) for seed in HELD_SEEDS]))
    H = w2.summarise(held)

    def row(k, v):
        lead = f"{v['median_lead']:.1f}" if v["median_lead"] is not None else "-"
        return (f"| {k[0]} | {k[1]} | {v['detected']}/{v['faults']} | {lead} | {v['eps']} / {v['years']:.2f} = {v['eps_per_year']:.2f} | "
                f"{v['eps_per_assessable_year']:.2f} | {v['drift_eps']} | {v['pre']} | {v['assessable']:.2f} |")
    hdr = ["| margin | sustain (operating points) | detected | median lead (days) | healthy alarm episodes / turbine-years = per turbine-year (the rule's unit) "
           "| per assessable turbine-year | drifting-sensor episodes | pre-onset alarms | assessable share |", "|---|---|---|---|---|---|---|---|---|"]
    y = T[chosen]["years"]
    lines = ["# W3 wind margin and sustain on a pooled tuning set (generated; SYNTHETIC; behaviour calibration only)", "",
             "Tuning: fleets 40-45 and 20-25 pooled (the fleets W2 used for tuning and for its held-out check). Held-out: fleets 60-65, used "
             "by no earlier run, chosen setting only. Rule fixed before running (script docstring): <= 1.0 healthy alarm episode per turbine-year, "
             "then most detections, then longest median lead; if none qualifies, the lowest rate.", "", "## Tuning (pooled)", ""] + hdr
    lines += [row(k, v) for k, v in sorted(T.items())]
    lines += ["", f"Chosen: margin {chosen[0]}, sustain {chosen[1]} ({'meets' if met else 'does NOT meet'} the 1.0 limit on the tuning set; "
                  f"{T[chosen]['eps']} episodes in {y:.2f} healthy turbine-years)", "",
              "## Held-out fleets 60-65 (chosen setting only)", ""] + hdr + [row(k, v) for k, v in sorted(H.items())]
    hy = H[chosen]["years"]
    lines += ["", f"Exposure: {y:.2f} healthy turbine-years for tuning, {hy:.2f} held out. Zero episodes in {hy:.2f} turbine-years would still "
                  f"allow {2.9957 / hy:.2f} per turbine-year at 95%.", "",
              "Caveats: the generator and the model share assumptions (KNOWN_LIMITATIONS E3); a slow drift of a single temperature sensor "
              "cannot be told apart from heating; these numbers say nothing about real turbines."]
    out = ROOT / "product" / "evidence" / "wind_synthetic"
    (out / "w3.md").write_bytes(("\n".join(lines) + "\n").encode("utf-8"))
    strip = lambda v: {kk: vv for kk, vv in v.items() if kk != "assess"}  # noqa: E731
    (out / "w3.json").write_bytes(json.dumps({"tuning": {f"{k[0]}|{k[1]}": strip(v) for k, v in T.items()}, "chosen": list(chosen),
                                              "meets_limit": met, "held_out": {f"{k[0]}|{k[1]}": strip(v) for k, v in H.items()}},
                                             indent=1, default=float).encode("utf-8"))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
