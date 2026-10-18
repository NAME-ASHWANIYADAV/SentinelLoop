# Problem Selection (Phase 1) — FINAL: Case Study 1

Decided 2026-10-18 after re-opening the prior recommendation under the now-known competition format. Evidence classes: OFFICIAL (case PDFs), PLATFORM (Unstop listing), THIRD-PARTY, INFERENCE, HYPOTHESIS (about other teams), UNKNOWN.

## 1. What changed since the prior report
The prior report (`analysis/TELIPORT_S4_case_selection_report.md`) assumed the deadline and format were unknown. The Unstop listing (PLATFORM) now gives: Round 1 = a single-slide PDF on one problem statement, window closing **24 Oct 2026 23:59 IST**; Round 2 = a 10-slide PPT plus any multimedia or prototype, **14 Nov–13 Dec 2026**; Round 3 finale date to be announced; teams of 2–3 from one college. No judging criteria exist beyond the PDFs.

Implications (INFERENCE): the first deliverable is due in six days and is a design artefact; Round 2 is a 30-day build window that probably overlaps end-semester exams (UNKNOWN); judges may never run code, so prototype evidence must be carried by the deck and an annex (repo, recording).

## 2. Method
Four fresh agents, none of which redid the prior research: an advocate for Case 1, an advocate for Case 3 (the only alternative that was competitive in the prior analysis), an effort-and-delivery reviewer against the real calendar, and an independent judge who read all three plus the prior blind-judge and reviewer outputs. Full outputs: `analysis/evidence/agent_outputs/phase1/`.

## 3. Case 1 vs Case 3 under the real format

| Dimension | Case 1 Predictive Maintenance | Case 3 Adaptive QoS |
|---|---|---|
| Round 1 one-slide content | Prescribed by the PDF (architecture diagram, cleaning/features, model choice with reasoning, agent logic) with seven weights; every element already exists; a reproduced number (FD001 RMSE 14.2) can be shown. Effort 1–1.5 person-days. Risk LOW. | PDF has no round structure; slide must be invented; strongest asset is a 638→41 ms latency measurement from one WSL2 run. Effort 1.5–2.5 person-days with a re-run first. Risk MEDIUM. |
| Round 2 minimum complete submission | 13–16 person-days (effort review); fits a 2- or 3-person team inside 30 days at ~50% availability | 20–26 person-days; fits only a 3-person team that pre-builds at risk during the 20-day gap before the shortlist; does not fit a 2-person team |
| Critical path | Environment lock → FD001 pipeline → agent → MLflow → dashboard → recorded run → deck; parallelisable into three tracks after the lock | Serial and wall-clock bound: netns topology → enforcement → harness → estimator tuning → verify/rollback → N≥10 runs; one root-enabled WSL2 machine; silent `tc` failures |
| Environment dependencies | pip-level only (lock file); VERIFIED working in `.venv` | root, kernel modules, no CAKE on WSL2, 82 ms idle timing spikes threatening the stability criterion (VERIFIED measurements) |
| Rubric expectation | Official weights; Round 1 ≈ 7.9, Round 2 ≈ 7.8 (INFERENCE) | Unweighted; 7.2–8.0 only if estimator and verify/rollback both land; 6.9–7.2 otherwise (INFERENCE) |
| Skill fit (adjusted) | 9.0 | 6.0 |
| Prior analysis | First under all eight views, both blind judges, all three reviewers (7.86 vs 7.26 risk-adjusted) | Second everywhere |
| Strongest argument | Lowest variance, evidence in hand, weights favour engineering completeness | Memorable hard-to-fake measurement; uncrowded system-level niche; prototype-as-annex format prescribed by its PDF; one-sentence executive story |

## 4. Decision
**Case Study 1 — Self-Healing Machines: Predictive Maintenance for a Connected Fleet. Confidence: high.** Not because its dataset is easy to access, but because (a) it is the only case whose Round 1 content is prescribed and already evidenced, (b) its Round 2 minimum fits the actual 30-day window for a two-person team, (c) its environment risks are already identified and fixed by a lock file, and (d) every prior input view ranks it first. The team must earn it by making the closed loop visible (agent acting on the uncertainty lower bound, gated retraining with accept and reject, leakage audit, four-subset coverage, decision-level evaluation) and citing Robinson (IJPHM 2026) as the ML baseline rather than claiming novelty.

The other three cases remain rejected for the reasons in the prior report Section H (Case 5: hardware-dependent edge claims and no vcan on WSL2; Case 2: unvalidated battery physics; Case 4: no dataset, no weights, regulatory-expert exposure).

## 5. Conditions that would flip the decision (all must be verified, not hoped)
1. A teammate demonstrates Linux networking fluency this week (runs `analysis/evidence/wsl2_tc_testbed_check.sh` under `wsl -u root`, explains the HTB/fq_codel/flower output unprompted, extends it to N=5 runs with p95 RTT) **and**
2. three active members with ≥12–15 h/week each from 25 Oct to 13 Dec with no exam clash are confirmed.
3. Alone, official Tata Elxsi guidance (not third-party) stating that Round 1 shortlisting rewards measured results over design soundness, or that shortlisting is relative within each case with Case 1 the largest pool, makes it a toss-up.

## 6. Verify on the portal this week (owner: team leader)
- Registration status (the listing shows contradictory 10 Oct / 23 Oct deadlines and "Registration Closed"); that a Round 1 file can be uploaded; whether only the team leader submits.
- Round 1 mechanics: single PDF, page-count enforcement, size limit (5 MB is the Season 3 precedent), template fields.
- Team facts: member count, weekly hours to 13 Dec, exam dates, any Linux `tc` experience.
- IP clause ("exclusive property of Tata Elxsi") accepted before investing the gap weeks.
- Submit by 23 Oct, leaving a day for portal problems.
