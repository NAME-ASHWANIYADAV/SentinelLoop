"""Build product/ADVERSARIAL_REVIEW.md from the review workflow's structured output and the resolution map below.

Input: the workflow result (persona reviews and verifier verdicts), saved as product/evidence/adversarial/review.json.
Every finding is listed with its original and verified severity and its resolution: FIXED (code change + test),
PARTIAL (part fixed, rest OPEN), DOCS (documents corrected in this phase), OPEN (tracked in KNOWN_LIMITATIONS.md).
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "product" / "evidence" / "adversarial" / "review.json"

T_LATCH = "tests/test_app_remediation.py"
T_SEC = "tests/test_app_remediation_security.py"
RES = {
    "om_manager-1": ("FIXED", "whole-feed delays are data_delivery_delay with no order at the asset; assess_at: latest_reading and assess-range for export sites; 26 h assessment-age limit for wind", T_LATCH),
    "om_manager-2": ("PARTIAL", "desk_review instead of a climb; reasoned rejections suppress re-raising. Bulk re-commissioning after a model change: OPEN", T_LATCH),
    "om_manager-3": ("OPEN", "status/alarm/curtailment signals are not in the contract (KNOWN_LIMITATIONS M3); PILOT_PROTOCOL no longer promises them", "DOCS"),
    "om_manager-4": ("OPEN", "no cranes, weather limits, travel or multi-day jobs in the scheduler (KNOWN_LIMITATIONS P8); site-local console times fixed", "DOCS"),
    "om_manager-5": ("FIXED", "maintenance clears a latch only through its completed work order; clear-risk records reasoned dismissals only", T_LATCH),
    "om_manager-6": ("FIXED", "deferred orders return for approval on their date; deferred list in the console", T_LATCH + ", tests/test_console.py"),
    "om_manager-7": ("FIXED", "anomaly-only urgent wording makes no failure-time claim", T_LATCH),
    "om_manager-8": ("DOCS", "assessability measured (W2) and defined over operating hours in the pilot criteria; season to be stated in the pilot plan", "product/evidence/wind_synthetic/w2.md"),
    "om_manager-9": ("FIXED", "anomaly-ranked scores within a class; site decision config at serve (downtime cost)", T_LATCH),
    "om_manager-10": ("OPEN", "no OEM-serviced workflow (responsible party, OEM ticket, service-report import): KNOWN_LIMITATIONS P9", "-"),
    "om_manager-11": ("PARTIAL", "pitch_angle optional. Per-site tag mapping (FR-B3): OPEN", T_LATCH),
    "om_manager-12": ("DOCS", "acceptance criteria restated as work orders per turbine-year by type; W2 reports episodes", "product/PILOT_ACCEPTANCE_CRITERIA.md"),
    "om_manager-13": ("DOCS", "discovery plan: curtailment and seasonal-planning assumptions and questions added; A17 raised", "product/CUSTOMER_DISCOVERY.md"),
    "om_manager-14": ("DOCS", "status documents synchronised with the code", "-"),
    "om_manager-15": ("PARTIAL", "site-local times and a site list fixed; role scoping per site and O&M reporting: OPEN", "tests/test_console.py"),
    "data_scientist-1": ("FIXED", "terminal downtime counted; S2 re-run; the parts-shortage and adverse MILP downtime claims withdrawn", "tests/test_app_sim.py, product/evidence/scheduling_v2"),
    "data_scientist-2": ("FIXED", "collapse scenarios flagged and not ranked; sustainable parts_tight scenario; priced-downtime objective", "product/evidence/scheduling_v2"),
    "data_scientist-3": ("DOCS", "PD-09 and RELIABILITY corrected: the platform ships the probabilistic trigger; a point-threshold trigger is PLANNED", "-"),
    "data_scientist-4": ("PARTIAL", "C2 calibration audit; the console labels P(failure) model-implied and not calibrated. Recalibration in the bundle: OPEN", "product/evidence/calibration/c2.md"),
    "data_scientist-5": ("DOCS", "the recommended default pair corrected to an evaluated combination", "product/SCHEDULING_EVALUATION.md"),
    "data_scientist-6": ("FIXED", "episodes per turbine-year reported; margin and sustain revisited on separate synthetic fleets before G0 (W2)", "product/evidence/wind_synthetic/w2.md"),
    "data_scientist-7": ("FIXED", "pre-registration amendment 1 (before any data) fixes the adapter, gates, multiplicity, TP timing and lead time; external timestamp needs the team", "product/evidence/g0/PREREGISTRATION.md"),
    "data_scientist-8": ("DOCS", "P17 restated as scheduler-dependent", "-"),
    "data_scientist-9": ("FIXED", "S2 tunes on FD001 engines and evaluates on FD003 engines", "product/evidence/scheduling_v2"),
    "data_scientist-10": ("DOCS", "synthetic numbers removed from the ladder's evidence column", "-"),
    "data_scientist-11": ("FIXED", "amendment 1: Farm A primary with an internal baseline computed by the same code; pooled score secondary", "product/evidence/g0/PREREGISTRATION.md"),
    "data_scientist-12": ("DOCS", "the fixed-interval fallback statement corrected", "-"),
    "data_scientist-13": ("FIXED", "nbm.gate(): the harness gates like the service; W2 uses it", "tests/test_app_wind.py"),
    "data_scientist-14": ("DOCS", "write-up errors corrected", "-"),
    "security-1": ("FIXED", "same as om_manager-5", T_LATCH),
    "security-2": ("FIXED", "future instants refused; back-dated assessments stored as replays that never move the state", T_LATCH),
    "security-3": ("FIXED", "console binds 127.0.0.1 (.streamlit/config.toml)", T_SEC),
    "security-4": ("FIXED", "verify-audit fails without an anchor unless waived; drill checks against the backup's anchor; claims reworded (state tables not covered)", T_SEC),
    "security-5": ("PARTIAL", "no role coercion; machine-credential completions never clear latches. Splitting the integration role and assignment checks: OPEN", T_LATCH),
    "security-6": ("FIXED", "withdrawn/deferred/completed orders mirrored onto CMMS requests; no adoption on first send; explicit field allowlist", T_SEC),
    "security-7": ("FIXED", "allowlist at every dispatch; no credentials, queries or fragments in URLs; config keys allowlisted; config admin-only", T_SEC),
    "security-8": ("FIXED", "CSV capped at 200,000 readings and parsed off the event loop (streaming parse: OPEN)", T_SEC),
    "security-9": ("DOCS", "THREAT_MODEL E1 lists exactly which services re-check roles", "-"),
    "security-10": ("PARTIAL", "rate-limit exemption by exact path. /ready and OpenAPI stay unauthenticated (accepted, documented)", "-"),
    "security-11": ("FIXED", "no server paths or exception text in reasons", "tests/test_app_failure_injection.py"),
    "security-12": ("FIXED", "API text rendered in code spans (follow-up review: escaping alone allowed autolinks)", T_SEC),
    "security-13": ("PARTIAL", "registration hashes bundle.pkl. Signed manifests: OPEN", T_SEC),
    "security-14": ("DOCS", "security documents synchronised; OSV advisories deduplicated", "-"),
    "technician-1": ("FIXED", "not_inspected, instrument checks, desk reviews, machine roles and older orders keep the latch", T_LATCH),
    "technician-2": ("FIXED", "same as om_manager-5; cleared assets show AWAITING_ASSESSMENT", T_LATCH),
    "technician-3": ("FIXED", "same as om_manager-6", T_LATCH),
    "technician-4": ("FIXED", "reasoned rejections suppress the same condition for a policy period", T_LATCH),
    "technician-5": ("FIXED", "job card shows why, due date, parts, skill, crew and assignees", "tests/test_console.py"),
    "technician-6": ("FIXED", "same as om_manager-7", T_LATCH),
    "technician-7": ("PARTIAL", "hand-back, bring-back from deferral and a reprioritise route. Raising a follow-up job and a shift editor in the console: OPEN", T_LATCH),
    "technician-8": ("PARTIAL", "plain-language states and signal descriptions. Deviations in degC against expected: OPEN", "-"),
    "technician-9": ("FIXED", "times in the site's time zone", "tests/test_console.py"),
    "technician-10": ("PARTIAL", "downtime required, return to service, flags shown for review. Instrument-specific finding codes and re-commissioning prompts: OPEN", "tests/test_console.py"),
    "technician-11": ("OPEN", "no offline or mobile mode, English only (KNOWN_LIMITATIONS P7)", "-"),
    "technician-12": ("OPEN", "no 'my jobs' view; technician resources not linked to users (KNOWN_LIMITATIONS P10)", "-"),
    "technician-13": ("FIXED", "last_assessed_at and ASSESSMENT_OVERDUE", T_LATCH),
    "technician-14": ("DOCS", "workflow and requirement documents synchronised", "-"),
    "technician-15": ("FIXED", "waiting time on each pending card", "-"),
    "buyer-1": ("DOCS", "README carries a product status banner; the competition summary is labelled history", "README.md"),
    "buyer-2": ("DOCS", "claim matrix, ladder, requirements, architecture, workflows synchronised", "-"),
    "buyer-3": ("DOCS", "matrix marks competition-pipeline-only capabilities", "-"),
    "buyer-4": ("DOCS", "wind message changed to advisory anomaly flags; ranked-list and crane-budget language marked as hypotheses", "-"),
    "buyer-5": ("DOCS", "commercial limitations listed; pilot commercial terms to agree", "product/KNOWN_LIMITATIONS.md"),
    "buyer-6": ("FIXED", "serve --decision-config; /ready says whether parameters are site-configured", T_LATCH),
    "buyer-7": ("DOCS", "summaries carry the unfavourable part of their evidence", "-"),
    "buyer-8": ("FIXED", "same as data_scientist-11", "product/evidence/g0/PREREGISTRATION.md"),
    "buyer-9": ("PARTIAL", "assessability measured in W2 and reported by G0. Expected range on real data: unknown until G0", "-"),
    "buyer-10": ("OPEN", "Indian OEM and SCADA-analytics alternatives not verified (needs web research); stale self-descriptions fixed", "-"),
    "buyer-11": ("DOCS", "decision-log references fixed; Phase 5-9 decisions logged", "product/DECISION_LOG.md"),
    "buyer-12": ("FIXED", "console shows the model's training-data class", "-"),
    "buyer-13": ("DOCS", "product description states design intent, not field operation", "-"),
    "safety-1": ("FIXED", "same as technician-1; an urgent condition during lower-priority work gets its own P1", T_LATCH),
    "safety-2": ("FIXED", "same as om_manager-5", T_LATCH),
    "safety-3": ("FIXED", "same as security-2", T_LATCH),
    "safety-4": ("FIXED", "same as security-6", T_SEC),
    "safety-5": ("FIXED", "INSPECTION_PENDING label and an inspection order while scope or model failures hide a latched inspection", T_LATCH),
    "safety-6": ("FIXED", "same as om_manager-6", T_LATCH),
    "safety-7": ("FIXED", "same as technician-13", T_LATCH),
    "safety-8": ("PARTIAL", "error-isolation and suspect-fraction tests added; RELIABILITY evidence column corrected", T_LATCH),
    "safety-9": ("PARTIAL", "technician listings limited to planner, RE, admin. Pseudonymisation, deletion and opaque audit actors: OPEN", "-"),
    "safety-10": ("DOCS", "THREAT_MODEL covers the CMMS write path and the console; worst case restated", "-"),
    "safety-11": ("FIXED", "integrity failures always reported", "-"),
    "safety-12": ("DOCS", "explicit exclusion: not part of any safety function, no SIL, no protection-layer credit", "product/RELIABILITY_AND_SAFETY.md"),
}
FOLLOW_UPS = [
    ("MEDIUM", "fail-open latch start: an unknown latch start let older work clear a latch", "FIXED 6abeb26: fails closed; migration 0007 backfills"),
    ("MEDIUM", "lost-mapping recovery could adopt planted records after a shadow-to-live switch", "FIXED c0f172a: recovery needs a logged earlier delivery"),
    ("MEDIUM", "markdown escaping left GFM autolinks", "FIXED c0f172a: API text rendered in code spans"),
]


def main():
    d = json.loads(SRC.read_text(encoding="utf-8"))
    v = {x["id"]: x for x in d["verdicts"]}
    allf = [(r["persona"], f) for r in d["reviews"] for f in r["findings"]]
    missing = [f["id"] for _, f in allf if f["id"] not in RES]
    assert not missing, missing
    counts = {}
    for _, f in allf:
        counts[f["severity"]] = counts.get(f["severity"], 0) + 1
    vc = {}
    for x in d["verdicts"]:
        vc[x["verdict"]] = vc.get(x["verdict"], 0) + 1
    after = {}
    for x in d["verdicts"]:
        after[x["corrected_severity"]] = after.get(x["corrected_severity"], 0) + 1
    st = {}
    for _, f in allf:
        st[RES[f["id"]][0]] = st.get(RES[f["id"]][0], 0) + 1
    L = ["# Adversarial review (Phase 9)", "",
         "**Generated** by `product/scripts/build_adversarial_review.py` from the workflow's structured output (`product/evidence/adversarial/review.json`) "
         "and the resolution map in that script.", "",
         "## Method", "",
         "- Six independent reviewers, each read-only, each required to cite file and line quotes or command output for every finding:",
         "  1. head of O&M at an Indian wind IPP;", "  2. senior reliability engineer / data scientist;", "  3. IT/OT security assessor;",
         "  4. site technician and shift planner;", "  5. sceptical buyer (CFO) and investor;", "  6. functional-safety and compliance auditor.",
         "- Two adversarial verifiers then tried to refute every critical and high finding.",
         "- The personas are role-played reviewers, not real customers, technicians or auditors. Their findings were checked against the code; their opinions about Indian O&M practice are labelled outside knowledge in the raw output.",
         "- Medium and low findings were not adversarially verified.", "",
         f"**Findings:** {sum(counts.values())} in total ({', '.join(f'{counts.get(k, 0)} {k}' for k in ('critical', 'high', 'medium', 'low'))}).",
         f"**Verification of the {len(d['verdicts'])} critical/high findings:** {', '.join(f'{n} {k}' for k, n in sorted(vc.items()))}; "
         f"severity after verification: {', '.join(f'{n} {k}' for k, n in sorted(after.items()))}.",
         f"**Resolution of all findings:** {', '.join(f'{n} {k}' for k, n in sorted(st.items()))}.", "",
         "## Bottom line from each reviewer", ""]
    for r in d["reviews"]:
        L += [f"**{r['persona']}.** {r['overall_verdict']}", ""]
    L += ["## Critical and high findings", "", "| id | title | severity → verified | verifier | resolution | evidence |", "|---|---|---|---|---|---|"]
    for p, f in allf:
        if f["severity"] in ("critical", "high"):
            vv = v.get(f["id"], {})
            r = RES[f["id"]]
            L.append(f"| {f['id']} | {f['title']} | {f['severity']} → {vv.get('corrected_severity', '?')} | {vv.get('verdict', '-')} | **{r[0]}**: {r[1]} | {r[2]} |")
    L += ["", "## Medium and low findings (not adversarially verified)", "", "| id | severity | title | resolution | evidence |", "|---|---|---|---|---|"]
    for p, f in allf:
        if f["severity"] in ("medium", "low"):
            r = RES[f["id"]]
            L.append(f"| {f['id']} | {f['severity']} | {f['title']} | **{r[0]}**: {r[1]} | {r[2]} |")
    L += ["", "## Follow-up automated security reviews of the fixes", "", "| severity | finding | resolution |", "|---|---|---|"]
    L += [f"| {a} | {b} | {c} |" for a, b, c in FOLLOW_UPS]
    L += ["", "## What the review changed in the product's position", "",
          "- The latching guarantee (PD-08) was not true as built: four separate paths cleared or hid an urgent warning without an inspection. All four are fixed and covered by regression tests.",
          "- The simulated scheduling advantages under parts shortage were an artefact of right-censored downtime and fleet collapse. They are withdrawn; see `SCHEDULING_EVALUATION.md` (S2).",
          "- The model-implied failure probability is not calibrated on the team's own simulated data (C2). It is labelled as such wherever it is shown.",
          "- On synthetic data the original wind thresholds gave more false-alarm episodes than the proposed pilot ceiling. Thresholds were revisited on separate synthetic fleets before any real data (W2), and the G0 pre-registration was amended before download.",
          "- Several status documents had drifted from the code. They were synchronised in this phase, and the claim matrix marks what exists only in the frozen competition pipeline.", ""]
    (ROOT / "product" / "ADVERSARIAL_REVIEW.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"written: {sum(counts.values())} findings; resolution {st}")


if __name__ == "__main__":
    main()
