# Official Requirements, Deadlines and Submission Rules

Last checked 2026-10-18. Evidence classes: **OFFICIAL** (the case-study PDFs supplied by Tata Elxsi), **PLATFORM** (the Unstop competition listing, which is the registration platform but not Tata Elxsi's own site), **THIRD-PARTY** (GradPartners, HireToday, 9curry, a Season 3 blog), **INFERENCE**, **UNKNOWN**.

## 1. Timeline and format

| Item | Value | Class | Source |
|---|---|---|---|
| Competition period | 23 Sep 2026 – 30 Mar 2027 | PLATFORM | Unstop listing (fetched 2026-10-18) |
| Registration deadline | 23 Oct 2026, 23:59 IST (the same page also shows "10 Oct" and marks registration closed, flagged on the page itself as a typo/stale banner) | PLATFORM, conflicting | Unstop; GradPartners and 9curry also say 23 Oct |
| **Round 1: Idea Submission** | **23 Sep 2026 11:00 – 24 Oct 2026 23:59 IST**; "a single slide (PDF format)" on ONE chosen problem statement; assessors and a jury shortlist | PLATFORM | Unstop |
| **Round 2: Detailed Submission** | **14 Nov 2026 10:00 – 13 Dec 2026 23:59 IST**; "a 10-slide PPT, plus any multimedia or prototype"; shortlisted teams only; best teams become National Finalists | PLATFORM | Unstop |
| Round 3: Grand Finale | date "to be announced"; presentation to senior Tata Elxsi leaders | PLATFORM | Unstop |
| File size limit | Season 3 precedent: PPT/PPTX/PDF under 5 MB, only the team leader submits | THIRD-PARTY (Season 3) | frontlinesmedia blog |
| Team | 2–3 members, same college, cross-year/specialisation allowed; pre-final and final-year B.Tech/M.Tech/dual-degree | PLATFORM | Unstop (header contradicts itself with "Individual Participation") |
| IP | "Once submitted, the idea becomes the exclusive property of Tata Elxsi" | PLATFORM | Unstop |
| Judging criteria beyond the PDFs | none published | UNKNOWN | — |
| Prize | not listed (only a referral promotion) | UNKNOWN | — |

**Working assumptions (INFERENCE, to be confirmed by the team on the portal):** Round 1 = one slide in PDF, 24 Oct 2026; Round 2 = 10 slides + prototype/multimedia annex, 13 Dec 2026; a 5 MB limit is prudent; a repo link and a short recorded run are acceptable "multimedia or prototype".

## 2. Case Study 1 — official requirements (OFFICIAL, from the PDF)

Problem: closed-loop system that ingests fleet sensor data, detects early degradation, predicts Remaining Useful Life (RUL), and automatically raises a maintenance work order, with a human stepping in only for exceptions.

Layers to demonstrate:
- Data Engineering: read sensor data (batch or streaming), handle missing values and basic noise, rolling-window features (averages, trends).
- Machine Learning: detect abnormal behaviour and predict RUL (cycles left before failure).
- MLOps: track experiments and model versions; simple retraining flow when new data arrives; basic monitoring view.
- Agents (non-LLM): rule-based Triage Agent that reads model output, decides severity, automatically creates a maintenance work order. No LLM required.

Ground rules: handle mild imbalance; pipeline runs end-to-end without manual steps once data is provided; lightweight, no LLM, simple rules/thresholds; open-source tools; documented design.

Dataset: NASA C-MAPSS (21 sensors + 3 operating settings; FD001–FD004); one subset acceptable, all four "for a more challenging solution". Official link: data.nasa.gov/dataset/cmapss-jet-engine-simulated-data.

Round 1 (Idea Submission) – Design deck: architecture diagram (data → features → model → agent → work order); approach for cleaning data and building features; choice of anomaly-detection and RUL models with reasoning; logic the Triage Agent will use. *(Platform rule: this must fit on ONE slide, PDF.)*

Round 2 (Detailed Submission) – Proof of Concept: working pipeline on the chosen subset(s); trained model with RUL predictions; a simple monitoring dashboard; agent auto-generating a work order + a demo retraining run. *(Platform rule: 10-slide PPT plus multimedia/prototype.)*

Evaluation (exact weights):
- Round 1: Problem understanding 15% · Architecture clarity 20% · Data engineering approach 15% · ML approach & reasoning 20% · MLOps & agent logic 15% · Dataset coverage 10% · Communication quality 5%.
- Round 2: Working pipeline 20% · Data engineering quality 15% · Model performance 15% · MLOps in action 10% · Agent behavior 10% · Dataset coverage 10% · Demo & explanation 20%.

Suggested (optional) tools: Python/Pandas/NumPy (optionally PySpark); scikit-learn (optionally TensorFlow/PyTorch); MLflow; Streamlit or Dash; plain Python for the agent.

## 3. Requirement checklist (what the submission must contain)

| ID | Requirement | Where satisfied | Status (2026-10-18) |
|---|---|---|---|
| R1 | Read sensor data, batch or streaming | `data.py` loader with schema check; `stream.py` cycle-by-cycle replay (`--stream-units`) | VERIFIED: `tests/test_data.py`, `tests/test_stream.py` (stream equals batch); 5 engines replayed per subset in the full run |
| R2 | Handle missing values and basic noise | `clean.py`: per-unit forward/backward fill with an `n_imputed` flag the agent reads; constant-sensor drop list; rolling features absorb noise (EMA tested and disabled, D13) | VERIFIED: `tests/test_clean.py`; E3 missing-20% and 3σ-noise faults detected on 98–100% of corrupted engines |
| R3 | Rolling-window features (averages, trends) | `features.py`: causal rolling mean / std / OLS slope over 20 cycles | VERIFIED: look-ahead test in `tests/test_features.py`; ablation worth 1.6–2.7 RMSE (E7) |
| R4 | Detect abnormal behaviour | `anomaly.py`: healthy-baseline z-score health index (top-2 deviations, names the sensors); IsolationForest kept as ablation (D10) | VERIFIED: `tests/test_anomaly.py`; sustained-anomaly WATCH rule in the agent |
| R5 | Predict RUL | `models.py` HGBR point model + `conformal.py` CQR 90% interval | VERIFIED: official-protocol RMSE 13.9–15.4 capped on FD001–FD004; PICP 0.82–0.94 |
| R6 | Track experiments and model versions | MLflow on SQLite, aliases | VERIFIED: `artifacts/mlflow.db`, `champion` alias per subset, `tests/test_tracking.py` |
| R7 | Retraining flow when new data arrives | `python -m sentinelloop retrain --subset X --new-data <file>` (or `--simulate-new-data`, `--only-if-drift`): challenger on the stored champion's engines + new engines, gated on held-out validation engines, promoted or rejected with reasons in MLflow and `retrain_log.json` (D24); E4 scripted scenarios | VERIFIED: `tests/test_retrain_flow.py` (end-to-end on FD001); E4 and E4-secondary logs on all subsets |
| R8 | Basic monitoring view | Streamlit dashboard | VERIFIED: six-tab Streamlit dashboard checked in a browser on 2026-10-18 |
| R9 | Rule-based Triage Agent: severity + auto work order; human for exceptions | `agent.py` rule table + escalation | VERIFIED: `tests/test_agent.py`; 227 work orders in the full run; escalation share 0.07–0.15 |
| R10 | Handle mild imbalance | healthy-baseline anomaly reference (healthy behaviour is the majority), thresholds tuned on validation engines never on test; stress-test detection and false-alarm rates per fault (E3); RUL is regression so no class weighting | PARTIALLY VERIFIED: E3 detection 98–100% on 3/4 faults with 0 false alarms; no per-class recall is reported (none is defined for RUL regression) |
| R11 | End-to-end without manual steps | `python -m sentinelloop run --subset all`; `experiments/run_all.py` | VERIFIED: one command, 36–45 s per subset (`elapsed_s` in `artifacts/<subset>/metrics.json`), no manual step; `experiments/run_all.py` reproduces every artefact in 55 minutes (`run_all_phase6.log`) |
| R12 | No LLM; open-source tools; documented design | stack + README + diagrams | VERIFIED: no LLM package in `requirements.lock.txt`; `README.md`; `docs/SYSTEM_DESIGN.md` |
| R13 | Dataset coverage (FD001–FD004) | config-driven subsets | VERIFIED: all four subsets, per-subset metrics in `artifacts/<subset>/metrics.json` |
| R14 | Round 1: one-slide PDF with architecture, data approach, model choice, agent logic | `submission/round1_slide.pdf` | PARTIALLY VERIFIED: `submission/SentinelLoop_Round1_CaseStudy1.pdf` rendered (one page, 80 KB, metadata set) plus a 4-page variant; team/college names still a placeholder (the script refuses to render one without `--allow-placeholder`); portal page rule unconfirmed |
| R15 | Round 2: 10-slide PPT + prototype annex | `submission/round2_deck_content.md` (plan), `round2_deck.pptx`, repo, recorded run | PROPOSED: content plan final (`submission/round2_deck_content.md`); PPTX built in Phase 8; recording is a team action |

## 4. Unknowns requiring confirmation on the portal
1. Whether the 24 Oct 2026 Round 1 deadline and single-slide format apply to this team's registration (the listing contradicts itself on dates).
2. File-size limits and whether a video/repo link is accepted as "multimedia or prototype".
3. Whether judges run code or only read the deck and annexes.
4. Round 3 date and duration.
