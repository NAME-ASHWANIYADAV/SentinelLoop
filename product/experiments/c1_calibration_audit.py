"""C1: calibration audit of the 90% RUL intervals on out-of-fold predictions (SIMULATED data: NASA C-MAPSS).

Part 1 - where coverage holds: coverage and width of [lower, upper] against the capped target, by subset, by true-RUL
band, and by operating regime (FD002/FD004; regime = rounded operating settings joined from the raw training files).
Part 2 - alternative calibration methods on an engine-level split (odd units calibrate, even units evaluate, then
swapped and averaged): as-is CQR; a global conformal re-correction; Mondrian (group-conditional) re-correction by
predicted-RUL band; Mondrian by regime (FD002/FD004). Rows within an engine are dependent, so the conformal
guarantee is only approximate here; the comparison is descriptive.
Output: product/evidence/calibration/c1.{json,md}.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OOF = ROOT / "experiments" / "results" / "oof"
RAW = ROOT / "data" / "raw"
OUT = ROOT / "product" / "evidence" / "calibration"
ALPHA = 0.10
TRUE_BANDS = [(0, 25), (25, 50), (50, 100), (100, 126)]
PRED_BANDS = [(-1e9, 25), (25, 50), (50, 100), (100, 1e9)]


def load(subset):
    o = pd.read_csv(OOF / f"{subset}_full.csv")
    cols = ["unit", "cycle", "os1", "os2", "os3"] + [f"s{i}" for i in range(1, 22)]
    raw = pd.read_csv(RAW / f"train_{subset}.txt", sep=r"\s+", header=None, names=cols, usecols=range(26))
    raw["regime"] = (raw["os1"].round(0).astype(int).astype(str) + "/" + (raw["os2"].round(2) + 0.0).astype(str) + "/" + raw["os3"].round(0).astype(int).astype(str))
    return o.merge(raw[["unit", "cycle", "regime"]], on=["unit", "cycle"], how="left")


def cov(df, lo="lower", hi="upper"):
    inside = (df["rul"] >= df[lo]) & (df["rul"] <= df[hi])
    return float(inside.mean()), float((df[hi] - df[lo]).mean()), int(len(df))


def band(v, bands):
    for i, (a, b) in enumerate(bands):
        if a <= v < b:
            return i
    return len(bands) - 1


def qhat(scores):
    s = np.sort(np.asarray(scores))
    n = len(s)
    if n == 0:
        return 0.0
    k = min(n, int(math.ceil((n + 1) * (1 - ALPHA))))
    return float(s[k - 1])


def recalibrate(cal, ev, group=None):
    """Conformalised re-correction: widen (or shrink) both bounds by the (1-alpha) quantile of max(lo - y, y - hi)."""
    sc = np.maximum(cal["lower"] - cal["rul"], cal["rul"] - cal["upper"])
    ev = ev.copy()
    if group is None:
        q = qhat(sc)
        ev["lo2"], ev["hi2"] = ev["lower"] - q, ev["upper"] + q
    else:
        qs = {g: qhat(sc[cal[group] == g]) for g in cal[group].unique()}
        qg = qhat(sc)
        q = ev[group].map(lambda g: qs.get(g, qg))
        ev["lo2"], ev["hi2"] = ev["lower"] - q, ev["upper"] + q
    return ev


def main():
    res = {"data_class": "SIMULATED (NASA C-MAPSS out-of-fold predictions)", "nominal": 1 - ALPHA, "subsets": {}}
    lines = ["# C1 calibration audit (generated; SIMULATED: C-MAPSS out-of-fold predictions)", "",
             f"Nominal coverage {1 - ALPHA:.0%}, target = capped RUL (cap 125). Coverage / mean width (cycles) / rows.", ""]
    for subset in ("FD001", "FD002", "FD003", "FD004"):
        d = load(subset)
        d["tband"] = d["rul"].map(lambda v: band(v, TRUE_BANDS))
        d["pband"] = d["point"].map(lambda v: band(v, PRED_BANDS))
        r = {"overall": cov(d), "by_true_rul": {f"{a}-{min(b, 125)}": cov(d[d.tband == i]) for i, (a, b) in enumerate(TRUE_BANDS)}}
        if d["regime"].nunique() > 2:
            r["by_regime"] = {g: cov(gg) for g, gg in d.groupby("regime")}
        methods = {}
        odd = d["unit"] % 2 == 1
        for name, grp in (("as_is", "none"), ("global_conformal", None), ("mondrian_pred_band", "pband")) + ((("mondrian_regime", "regime"),) if "by_regime" in r else ()):
            parts = []
            for cal, ev in ((d[odd], d[~odd]), (d[~odd], d[odd])):
                if grp == "none":
                    e = ev.copy(); e["lo2"], e["hi2"] = e["lower"], e["upper"]
                else:
                    e = recalibrate(cal, ev, grp)
                parts.append(e)
            e = pd.concat(parts)
            methods[name] = {"overall": cov(e, "lo2", "hi2"), "by_true_rul": {f"{a}-{min(b, 125)}": cov(e[e.tband == i], "lo2", "hi2")
                                                                             for i, (a, b) in enumerate(TRUE_BANDS)},
                             "worst_regime": min((cov(g, "lo2", "hi2")[0], k) for k, g in e.groupby("regime")) if "by_regime" in r else None}
        r["methods"] = methods
        res["subsets"][subset] = r
        lines += [f"## {subset}", "", "| slice | coverage | mean width | rows |", "|---|---|---|---|",
                  f"| all | {r['overall'][0]:.3f} | {r['overall'][1]:.1f} | {r['overall'][2]} |"]
        lines += [f"| true RUL {k} | {v[0]:.3f} | {v[1]:.1f} | {v[2]} |" for k, v in r["by_true_rul"].items()]
        if "by_regime" in r:
            cs = sorted(r["by_regime"].items(), key=lambda kv: kv[1][0])
            lines.append(f"| regimes (n={len(cs)}): worst {cs[0][0]} | {cs[0][1][0]:.3f} | {cs[0][1][1]:.1f} | {cs[0][1][2]} |")
            lines.append(f"| regimes: best {cs[-1][0]} | {cs[-1][1][0]:.3f} | {cs[-1][1][1]:.1f} | {cs[-1][1][2]} |")
        lines += ["", "Recalibration on an engine split (coverage overall; coverage in true RUL 0-25; mean width):", "",
                  "| method | coverage | coverage RUL 0-25 | coverage RUL 25-50 | width | worst regime coverage |", "|---|---|---|---|---|---|"]
        for name, m in methods.items():
            wr = f"{m['worst_regime'][0]:.3f} ({m['worst_regime'][1]})" if m["worst_regime"] else "-"
            lines.append(f"| {name} | {m['overall'][0]:.3f} | {m['by_true_rul']['0-25'][0]:.3f} | {m['by_true_rul']['25-50'][0]:.3f} | {m['overall'][1]:.1f} | {wr} |")
        lines.append("")
    (OUT / "c1.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    (OUT / "c1.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
