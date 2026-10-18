"""C2: is P(failure before the decision horizon) calibrated? (SIMULATED: C-MAPSS out-of-fold predictions)

Adversarial review data_scientist-4: C1 audited interval coverage only, while operators are shown P(failure) and the
due-date rule promises 'P(failure before the job ends) <= 5%'. Here, for every out-of-fold row (3 h per cycle, the
platform's C-MAPSS assumption): p = risk.p_fail_before(60 h); event = true RUL (raw) x 3 h <= 60 h.
Reported: reliability table (mean p vs observed rate per bin), Brier score and Brier skill against the base rate,
an isotonic recalibration fitted on odd engines and evaluated on even engines (and swapped), and the share of rows
whose true failure comes before t* = the due-date rule's latest-start horizon (nominal 5%).
Output: product/evidence/calibration/c2.{json,md}.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from sentinelloop.app.decision import inverse_cdf  # noqa: E402
from sentinelloop.app.risk import p_fail_before  # noqa: E402

OUT = ROOT / "product" / "evidence" / "calibration"
HPC, H = 3.0, 60.0
BINS = [0, 0.01, 0.05, 0.1, 0.3, 0.5, 0.7, 0.9, 1.0001]


def main():
    res, lines = {}, ["# C2 calibration of P(failure before 60 h) (generated; SIMULATED: C-MAPSS out-of-fold predictions, 3 h per cycle)", ""]
    for subset in ("FD001", "FD002", "FD003", "FD004"):
        d = pd.read_csv(ROOT / "experiments" / "results" / "oof" / f"{subset}_full.csv")
        lo, pt, up = d["lower"].to_numpy() * HPC, d["point"].to_numpy() * HPC, d["upper"].to_numpy() * HPC
        p = np.array([p_fail_before(H, a, b, c, 0.9) for a, b, c in zip(lo, pt, up)])
        y = (d["rul_raw"].to_numpy() * HPC <= H).astype(float)
        brier = float(np.mean((p - y) ** 2))
        base = float(np.mean((y.mean() - y) ** 2))
        rel = []
        for a, b in zip(BINS[:-1], BINS[1:]):
            m = (p >= a) & (p < b)
            if m.sum():
                rel.append({"bin": f"[{a:.2f},{min(b, 1):.2f})", "n": int(m.sum()), "mean_p": round(float(p[m].mean()), 3), "observed": round(float(y[m].mean()), 3)})
        odd = (d["unit"] % 2 == 1).to_numpy()
        q = np.empty_like(p)
        for fit, ev in ((odd, ~odd), (~odd, odd)):
            iso = IsotonicRegression(out_of_bounds="clip", y_min=0, y_max=1).fit(p[fit], y[fit])
            q[ev] = iso.predict(p[ev])
        brier_iso = float(np.mean((q - y) ** 2))
        tstar = np.array([inverse_cdf(0.05, a, b, c, 0.9) for a, b, c in zip(lo, pt, up)])
        true_h = d["rul_raw"].to_numpy() * HPC
        viol = {}
        for a, b in ((0, 25), (25, 50), (50, 100), (100, 10_000)):
            m = (d["rul_raw"] >= a).to_numpy() & (d["rul_raw"] < b).to_numpy()
            viol[f"true RUL {a}-{b if b < 10_000 else '+'}"] = round(float((true_h[m] < tstar[m]).mean()), 3) if m.sum() else None
        res[subset] = {"brier": round(brier, 4), "brier_base_rate": round(base, 4), "brier_skill": round(1 - brier / base, 3) if base else None,
                       "brier_isotonic_cv": round(brier_iso, 4), "reliability": rel, "due_rule_violation_rate": viol, "rows": int(len(d))}
        lines += [f"## {subset}", "", f"Brier {brier:.4f} (base rate {base:.4f}; skill {res[subset]['brier_skill']}); after isotonic recalibration "
                                       f"(engine split) {brier_iso:.4f}.", "", "| p bin | rows | mean p | observed rate |", "|---|---|---|---|"]
        lines += [f"| {r['bin']} | {r['n']} | {r['mean_p']} | {r['observed']} |" for r in rel]
        lines += ["", "Share of rows whose true failure comes before the due-date horizon t* (nominal 0.05):", ""]
        lines += [f"- {k}: {v}" for k, v in viol.items()] + [""]
    lines += ["Reading: where the observed rate differs from mean p, the number shown to operators is not a calibrated probability. "
              "The console labels it model-implied; the wind vertical shows no probability at all (PD-11)."]
    (OUT / "c2.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    (OUT / "c2.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
