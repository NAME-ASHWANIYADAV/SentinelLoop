"""Render the Round 1 submission from stored artefacts (never typed numbers).

    .venv/Scripts/python.exe submission/make_round1_slide.py --team "Team name (College)" [--deck] [--allow-placeholder]

Outputs (submission/):
  SentinelLoop_Round1_CaseStudy1.pdf / .png   one 16:9 slide (the Unstop listing says "a single slide (PDF format)")
  SentinelLoop_Round1_design_deck.pdf         the same content as a 4-page design deck at 11-16 pt (the case-study PDF says
                                              "design and Architecture slides deck"); upload whichever the form permits.
Numbers: artifacts/<subset>/metrics.json (pipeline) and artifacts/baseline/<subset>/metrics.json (E0); the pre-review copies under
experiments/results/e0_baseline/ are the fallback. The script refuses to write a placeholder team name unless --allow-placeholder.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]
SUBSETS = ["FD001", "FD002", "FD003", "FD004"]
BLUE, ORANGE, GREEN, GREY, DARK = "#1f4e79", "#c55a11", "#2e7d32", "#333333", "#0b2545"


def load_numbers() -> dict:
    out = {}
    for s in SUBSETS:
        pm = ROOT / "artifacts" / s / "metrics.json"
        bm = ROOT / "artifacts" / "baseline" / s / "metrics.json"
        if not bm.exists():
            bm = ROOT / "experiments" / "results" / "e0_baseline" / f"{s}_metrics.json"
        p = json.loads(pm.read_text(encoding="utf-8")) if pm.exists() else {}
        b = json.loads(bm.read_text(encoding="utf-8")) if bm.exists() else {}
        out[s] = {"rmse_c": p.get("hgbr_rmse_capped", b.get("hgbr_rmse_capped")), "rmse_r": p.get("hgbr_rmse_raw", b.get("hgbr_rmse_raw")),
                  "phm08": p.get("hgbr_phm08", b.get("hgbr_phm08")), "picp": p.get("picp_test_capped"), "mpiw": p.get("mpiw_test"),
                  "esc": p.get("escalation_share_test"), "naive": b.get("naive_rmse_capped"), "rf": b.get("rf_rmse_capped"),
                  "cv_leaky": b.get("cv_rmse_last_cycle_naive_protocol"), "cv_honest": b.get("cv_rmse_random_truncation_protocol"),
                  "source": str(pm if pm.exists() else bm)}
    return out


def fmt(x, nd=1):
    return "n/a" if x is None else f"{x:.{nd}f}"


def rng(vals, nd=1):
    vals = [v for v in vals if v is not None]
    return "n/a" if not vals else f"{min(vals):.{nd}f}–{max(vals):.{nd}f}"


def content(n: dict) -> dict:
    """All slide text, built from the stored numbers. Shared by the one-page and the deck renderers."""
    res_line = "  ·  ".join(f"{s} {fmt(n[s]['rmse_c'])} / {fmt(n[s]['rmse_r'])}" for s in SUBSETS)
    picp_line = " / ".join(fmt(n[s]["picp"], 2) for s in SUBSETS)
    return {
        "title": "SentinelLoop  ·  Self-Healing Machines: Predictive Maintenance for a Connected Fleet",
        "thesis": ["Closed-loop prognostics: RUL with a calibrated 90% interval; a deterministic Triage Agent raises work orders",
                   "from the interval lower bound, escalates untrustworthy inputs to a human, retrains only through a gate,",
                   "and keeps every decision auditable.  No LLM · open-source Python · all four C-MAPSS subsets · one command."],
        "problem": ["PROBLEM (in the case study's words): a fleet streams sensor data; today failures are found after breakdowns or by fixed service intervals.",
                    "Needed: ingest → clean → detect abnormal behaviour → predict Remaining Useful Life → create the work order automatically → involve a human only for exceptions.",
                    "Ground rules we design to: mild imbalance (failures are rare), no manual steps once data is provided, lightweight rules (no LLM), documented design."],
        "arch_main": [("C-MAPSS SENSOR STREAM", "21 sensors + 3 settings\nbatch file or cycle-by-cycle replay"),
                      ("CLEAN", "per-unit fill + quality flag\ndrop list · operating-regime\nscaling (fit on train only)"),
                      ("FEATURES", "causal rolling mean / std / slope\nover 20 cycles (never look ahead)"),
                      ("MODELS", "health index on a healthy baseline\nHistGradientBoosting RUL\n+ conformal 90% interval"),
                      ("TRIAGE AGENT (rules)", "severity from the interval LOWER\nbound; quality, drift and width\nchecks → escalate to a human"),
                      ("WORK ORDER", "one open order per machine\naction · due-by cycle · sensors\naudit chain · SQLite / JSON")],
        "arch_loop": [("DRIFT MONITOR", "age-matched PSI per feature\nsettings = critical columns"),
                      ("RETRAIN ON NEW DATA", "`sentinelloop retrain`: new file\nor drift alarm → challenger"),
                      ("PROMOTION GATE", "validation RMSE ≤ +2% · coverage\n≥ 0.85 · late orders not worse"),
                      ("MLflow REGISTRY", "SQLite backend · champion alias\nreject logged with reasons")],
        "loop_note": "the retraining flow shows both outcomes: a promoted challenger and a rejected one, each with its reasons",
        "data": ["Every fit on training engines only: constant-sensor drop list,",
                 "KMeans operating regimes (6 on FD002/FD004, purity 100%),",
                 "per-regime scaling of every sensor.",
                 "Missing values: per-unit fill + a quality flag the agent reads.",
                 "Noise: rolling-window features (EMA available; hurt FD004, so off).",
                 "Causal windows: same arithmetic in batch and stream (tested bitwise).",
                 "Honest validation: engine-level folds with random truncation.",
                 "The leakage-prone 'last cycle of a held-out engine' protocol",
                 f"reports RMSE {rng([n[s]['cv_leaky'] for s in SUBSETS])}; the honest one {rng([n[s]['cv_honest'] for s in SUBSETS])}.",
                 "We report the honest one, against capped AND raw truth.",
                 "Every artefact carries the data SHA-256, config hash, MLflow run id."],
        "rules": [("Condition (L = interval lower bound)", "Severity", "Action"),
                  ("L ≤ 10 cycles", "CRITICAL", "stop & repair, order"),
                  ("L ≤ 25", "HIGH", "maintenance order"),
                  ("L ≤ 50", "MEDIUM", "plan maintenance"),
                  ("sustained anomaly, RUL healthy", "WATCH", "monitor"),
                  ("interval wider than calibrated limit,", "ESCALATE", "inspection, human"),
                  ("> 10% imputed, setting out of range,", "", ""),
                  ("fleet drift on HIGH/CRITICAL, conflict", "", "")],
        "agent": ["One open order per machine; a higher severity upgrades it and",
                  "pulls its due-by cycle earlier. Every decision stores inputs,",
                  "thresholds, rules fired and model version in a hash-chained",
                  "audit log that re-derives 100% of decisions. Mild imbalance:",
                  "the anomaly baseline is healthy behaviour; thresholds are set",
                  "on validation engines, never on test. MLOps: MLflow (SQLite)",
                  "tracks params, metrics, data hash, versions; `retrain` trains",
                  "a challenger on new data, gates it, promotes or rejects it with",
                  "the reasons logged. One command runs everything:",
                  "python -m sentinelloop run --subset all"],
        "ml": ["Anomaly: healthy-baseline health index (RMS of the two largest",
               "standardised deviations from each engine's early life); names",
               "the sensors; armed after the window fills; 'mild imbalance'.",
               "RUL: HistGradientBoosting (CPU, seconds, retrains live) with",
               "conformalized quantile regression intervals calibrated on",
               "held-out engines (Romano et al. 2019; CQR on C-MAPSS as in",
               "Robinson, IJPHM 2026; cited, not claimed). Coverage is measured",
               "per subset and stated as marginal, never as a guarantee.",
               "Why not an LSTM: published deep models reach ≈ 11–13 RMSE on",
               f"FD001 vs our {fmt(n['FD001']['rmse_c'])}; explainability, retraining in seconds",
               "and a decision-level evaluation (late orders, discarded life,",
               "escalation share) matter more for a closed loop. RandomForest",
               "and naive-mean baselines are logged alongside."],
        "coverage": ["All four subsets through configuration (6 regimes on FD002/FD004; two fault modes on FD003/FD004).",
                     "Already running on a CPU laptop, official last-cycle test protocol, RMSE vs RUL capped at 125 / raw:",
                     res_line,
                     f"90% interval coverage {picp_line} (FD004 below nominal, reported) · naive mean {rng([n[s]['naive'] for s in SUBSETS])} · RandomForest {rng([n[s]['rf'] for s in SUBSETS])} · PHM08 score with its convention printed."],
        "footer": ["Tools: Python 3.12 · pandas · scikit-learn · MLflow · Streamlit · pytest suite. Dataset: NASA C-MAPSS (Saxena et al., PHM08; archive verified by checksum, not redistributed). Simulated data; no cost saving is claimed.",
                   "Round 2 adds: policy-replay evaluation of the agent, stress tests on corrupted inputs, the live retraining flow (promote and reject), the monitoring dashboard, a 10-slide deck, the repository and a recorded clean-clone run."],
    }


def box(ax, x, y, w, h, title, body, fc, ec, fs_title, fs_body):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.004,rounding_size=0.008", fc=fc, ec=ec, lw=1.0, transform=ax.transAxes))
    ax.text(x + w / 2, y + h - 0.012, title, ha="center", va="top", fontsize=fs_title, fontweight="bold", color=DARK, transform=ax.transAxes)
    ax.text(x + w / 2, y + h / 2 - 0.012, body, ha="center", va="center", fontsize=fs_body, color=GREY, transform=ax.transAxes, linespacing=1.15)


def arrow(ax, x0, y0, x1, y1, color=BLUE):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0), xycoords="axes fraction", textcoords="axes fraction", arrowprops=dict(arrowstyle="->", lw=1.3, color=color))


def bullets(ax, x, y, lines, fs, dy, color=GREY, mono_last=False):
    for i, line in enumerate(lines):
        kw = {"family": "monospace", "fontsize": fs - 0.4} if (mono_last and i == len(lines) - 1) else {"fontsize": fs}
        ax.text(x, y - i * dy, line, va="top", color=color, transform=ax.transAxes, **kw)


def render_one_page(c: dict, team: str, out: Path, meta: dict) -> None:
    fig = plt.figure(figsize=(13.333, 7.5))
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_axis_off(); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.add_patch(FancyBboxPatch((0, 0.885), 1, 0.115, boxstyle="square,pad=0", fc=DARK, ec=DARK, transform=ax.transAxes))
    ax.text(0.012, 0.972, c["title"], fontsize=14.5, fontweight="bold", color="white", va="center", transform=ax.transAxes)
    for i, l in enumerate(c["thesis"]):
        ax.text(0.012, 0.936 - i * 0.017, l, fontsize=8.4, color="white", va="center", transform=ax.transAxes)
    ax.text(0.988, 0.936, team, fontsize=8.8, color="white", va="center", ha="right", fontweight="bold", transform=ax.transAxes)
    ax.text(0.988, 0.917, "Case Study 1 · Round 1 idea submission · TELIPORT Season 4", fontsize=7.6, color="#d0d8e8", va="center", ha="right", transform=ax.transAxes)
    # problem strip
    ax.add_patch(FancyBboxPatch((0.012, 0.806), 0.976, 0.072, boxstyle="round,pad=0.002,rounding_size=0.006", fc="#f3f6fa", ec="#b8c4d6", lw=0.8, transform=ax.transAxes))
    for i, l in enumerate(c["problem"]):
        ax.text(0.02, 0.866 - i * 0.021, l, fontsize=7.8, color=DARK if i == 0 else GREY, va="center", transform=ax.transAxes, fontweight="bold" if i == 0 else "normal")
    # architecture
    ax.text(0.5, 0.789, "Architecture — data → features → model → agent → work order (every fit on training engines only; batch or cycle-by-cycle replay through the same code)",
            fontsize=8.6, fontweight="bold", color=BLUE, ha="center", va="center", transform=ax.transAxes)
    xs = [0.012, 0.178, 0.344, 0.51, 0.676, 0.842]; w, y0, h = 0.146, 0.70, 0.075
    for i, (t, b) in enumerate(c["arch_main"]):
        fc = "#fdebd9" if i in (3, 4) else "#e8eef6"
        box(ax, xs[i], y0, w, h, t, b, fc, ORANGE if i in (3, 4) else BLUE, 7.6, 7.0)
        if i < 5:
            arrow(ax, xs[i] + w, y0 + h / 2, xs[i + 1], y0 + h / 2)
    lx = [0.19, 0.39, 0.59, 0.79]; lw_, ly, lh = 0.17, 0.613, 0.058
    for i, (t, b) in enumerate(c["arch_loop"]):
        box(ax, lx[i], ly, lw_, lh, t, b, "#e9f5ea", GREEN, 7.4, 6.9)
        if i < 3:
            arrow(ax, lx[i] + lw_, ly + lh / 2, lx[i + 1], ly + lh / 2, GREEN)
    arrow(ax, 0.417, 0.70, 0.275, ly + lh, GREEN); arrow(ax, 0.79 + lw_ / 2, ly + lh, 0.583, 0.70, GREEN)
    ax.text(0.5, 0.602, c["loop_note"], fontsize=6.9, color=GREEN, ha="center", va="center", style="italic", transform=ax.transAxes)
    # three columns
    top, bottom = 0.585, 0.118
    for x, wcol, ec in ((0.012, 0.318, BLUE), (0.339, 0.33, ORANGE), (0.678, 0.31, BLUE)):
        ax.add_patch(FancyBboxPatch((x, bottom), wcol, top - bottom, boxstyle="round,pad=0.002,rounding_size=0.006", fc="white", ec=ec, lw=1.0, transform=ax.transAxes))
    ax.text(0.022, 0.573, "Data engineering approach", fontsize=9.2, color=BLUE, fontweight="bold", va="center", transform=ax.transAxes)
    bullets(ax, 0.022, 0.552, c["data"], 8.0, 0.0235)
    ax.text(0.349, 0.573, "Triage Agent logic (deterministic) and MLOps", fontsize=9.2, color=ORANGE, fontweight="bold", va="center", transform=ax.transAxes)
    ty = 0.552
    for i, (cond, sev, act) in enumerate(c["rules"]):
        bold = i == 0
        col = {"CRITICAL": "#b91c1c", "HIGH": "#ea580c", "MEDIUM": "#ca8a04", "WATCH": "#2563eb", "ESCALATE": "#6a1b9a"}.get(sev, DARK)
        ax.text(0.349, ty, cond, fontsize=7.9, color=DARK if bold else GREY, va="top", fontweight="bold" if bold else "normal", transform=ax.transAxes)
        if sev:
            ax.text(0.536, ty, sev, fontsize=7.9, color=col, va="top", fontweight="bold", transform=ax.transAxes)
            ax.text(0.592, ty, act, fontsize=7.9, color=DARK if bold else GREY, va="top", fontweight="bold" if bold else "normal", transform=ax.transAxes)
        ty -= 0.0215
    bullets(ax, 0.349, ty - 0.004, c["agent"], 8.0, 0.0235, mono_last=True)
    ax.text(0.688, 0.573, "ML approach & reasoning", fontsize=9.2, color=BLUE, fontweight="bold", va="center", transform=ax.transAxes)
    bullets(ax, 0.688, 0.552, c["ml"], 8.0, 0.0235)
    # coverage strip
    ax.add_patch(FancyBboxPatch((0.012, 0.03), 0.976, 0.082, boxstyle="round,pad=0.002,rounding_size=0.006", fc="#f3f6fa", ec="#b8c4d6", lw=0.8, transform=ax.transAxes))
    ax.text(0.02, 0.102, "Dataset coverage and measured status", fontsize=8.6, color=BLUE, fontweight="bold", va="center", transform=ax.transAxes)
    for i, l in enumerate(c["coverage"]):
        ax.text(0.02, 0.084 - i * 0.0165, l, fontsize=7.6, color=DARK if i == 2 else GREY, va="center", fontweight="bold" if i == 2 else "normal", transform=ax.transAxes)
    for i, l in enumerate(c["footer"]):
        ax.text(0.012, 0.021 - i * 0.012, l, fontsize=6.3, color=GREY, va="center", transform=ax.transAxes)
    fig.savefig(out.with_suffix(".pdf"), format="pdf", metadata=meta)
    fig.savefig(out.with_suffix(".png"), format="png", dpi=150)
    plt.close(fig)


def render_deck(c: dict, team: str, out: Path, meta: dict) -> None:
    def page(title, blocks):
        fig = plt.figure(figsize=(13.333, 7.5))
        ax = fig.add_axes([0, 0, 1, 1]); ax.set_axis_off()
        ax.add_patch(FancyBboxPatch((0, 0.9), 1, 0.1, boxstyle="square,pad=0", fc=DARK, ec=DARK, transform=ax.transAxes))
        ax.text(0.02, 0.95, title, fontsize=20, fontweight="bold", color="white", va="center", transform=ax.transAxes)
        ax.text(0.98, 0.95, team, fontsize=11, color="white", va="center", ha="right", transform=ax.transAxes)
        y = 0.86
        for head, lines, fs, dy in blocks:
            if head:
                ax.text(0.03, y, head, fontsize=14, fontweight="bold", color=BLUE, va="top", transform=ax.transAxes); y -= 0.045
            for l in lines:
                ax.text(0.04, y, l, fontsize=fs, color=GREY, va="top", transform=ax.transAxes); y -= dy
            y -= 0.02
        ax.text(0.02, 0.025, "SentinelLoop · TELIPORT Season 4 · Round 1 design deck · simulated NASA C-MAPSS data · no LLM", fontsize=9, color=GREY, transform=ax.transAxes)
        return fig

    arch = [f"{t}: {b.replace(chr(10), ' ')}" for t, b in c["arch_main"]]
    loop = [f"{t}: {b.replace(chr(10), ' ')}" for t, b in c["arch_loop"]]
    rules = [f"{cond:<52} {sev:<10} {act}" for cond, sev, act in c["rules"]]
    with PdfPages(out) as pdf:
        pdf.infodict().update(meta)
        pdf.savefig(page("SentinelLoop — Self-Healing Machines (Case Study 1)", [("Thesis", c["thesis"], 13, 0.04), ("Problem", c["problem"], 11.5, 0.038), ("Architecture: data → features → model → agent → work order", arch, 11, 0.034), ("Side loop: drift → retrain → gate → registry", loop + [c["loop_note"]], 11, 0.034)]))
        pdf.savefig(page("Data engineering and ML approach", [("Data engineering approach", c["data"], 12.5, 0.038), ("ML approach and reasoning", c["ml"], 12.5, 0.038)]))
        pdf.savefig(page("Triage Agent logic and MLOps", [("Rule table (deterministic, on the 90% interval lower bound L)", rules, 11.5, 0.036), ("Work orders, audit, retraining", c["agent"], 12.5, 0.038)]))
        pdf.savefig(page("Dataset coverage, measured status, next steps", [("Coverage and measured results (official test protocol)", c["coverage"], 12, 0.04), ("Tools and Round 2", c["footer"], 11, 0.045)]))
    plt.close("all")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--team", default="Team ______  ·  ______ College")
    ap.add_argument("--out", default=str(ROOT / "submission" / "SentinelLoop_Round1_CaseStudy1"))
    ap.add_argument("--deck", action="store_true", help="also render the 4-page design-deck variant")
    ap.add_argument("--allow-placeholder", action="store_true")
    args = ap.parse_args()
    if ("___" in args.team or "to be filled" in args.team.lower() or "placeholder" in args.team.lower()) and not args.allow_placeholder:
        sys.exit("refusing to render a placeholder team name; pass --team \"Team name · College\" (or --allow-placeholder for a draft)")
    n = load_numbers()
    c = content(n)
    meta = {"Title": "SentinelLoop - TELIPORT Season 4 Round 1 - Case Study 1", "Author": args.team, "Subject": "Self-Healing Machines: Predictive Maintenance for a Connected Fleet (design submission)", "Creator": "matplotlib"}
    out = Path(args.out)
    render_one_page(c, args.team, out, meta)
    words = sum(len(" ".join(v if isinstance(v, list) else [str(v)]).split()) for k, v in c.items() if k not in ("arch_main", "arch_loop", "rules")) \
        + sum(len((t + " " + b).split()) for t, b in c["arch_main"] + c["arch_loop"]) + sum(len(" ".join(r).split()) for r in c["rules"])
    print(f"wrote {out.with_suffix('.pdf')} ({out.with_suffix('.pdf').stat().st_size // 1024} KB, ~{words} words) and {out.with_suffix('.png')}")
    if args.deck:
        deck = out.with_name("SentinelLoop_Round1_design_deck.pdf")
        render_deck(c, args.team, deck, meta)
        print(f"wrote {deck} ({deck.stat().st_size // 1024} KB, 4 pages)")
    # the content plan is generated from the same text so the two can never drift apart
    plan = ["# Round 1 — single-slide content (GENERATED by make_round1_slide.py; do not edit by hand)", "",
            "Platform rule (Unstop listing): one slide, PDF, one problem statement, due 24 Oct 2026 23:59 IST. The case-study PDF calls the Round 1 submission a 'design and Architecture slides deck'; the one-page PDF is the primary file and `SentinelLoop_Round1_design_deck.pdf` (4 pages, same content) is the variant to upload if the form accepts several pages. Rubric: Problem understanding 15 · Architecture clarity 20 · Data engineering approach 15 · ML approach & reasoning 20 · MLOps & agent logic 15 · Dataset coverage 10 · Communication quality 5.", "",
            f"## Title band\n{c['title']}\n\n" + "\n".join(c["thesis"]), "", "## Problem (15%)\n" + "\n".join(c["problem"]), "",
            "## Architecture (20%)\n" + "\n".join(f"- **{t}**: {b.replace(chr(10), ' ')}" for t, b in c["arch_main"]) + "\n\nSide loop:\n" + "\n".join(f"- **{t}**: {b.replace(chr(10), ' ')}" for t, b in c["arch_loop"]) + f"\n\n_{c['loop_note']}_", "",
            "## Data engineering approach (15%)\n" + "\n".join(c["data"]), "",
            "## Triage Agent logic and MLOps (15%)\n| " + " | ".join(c["rules"][0]) + " |\n|---|---|---|\n" + "\n".join("| " + " | ".join(r) + " |" for r in c["rules"][1:]) + "\n\n" + "\n".join(c["agent"]), "",
            "## ML approach & reasoning (20%)\n" + "\n".join(c["ml"]), "", "## Dataset coverage (10%)\n" + "\n".join(c["coverage"]), "", "## Footer\n" + "\n".join(c["footer"]), "",
            "Sources: " + "; ".join(f"{s}: `{Path(n[s]['source']).relative_to(ROOT).as_posix()}`" for s in SUBSETS if n[s]["source"] != "None")]
    (ROOT / "submission" / "round1_slide_content.md").write_text("\n".join(plan) + "\n", encoding="utf-8")
    print("numbers from:", {s: n[s]["source"] for s in SUBSETS})


if __name__ == "__main__":
    main()
