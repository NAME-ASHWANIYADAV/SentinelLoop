# Scoring Targets and Risk Register (Phase 1)

## 1. Official rubric targets (Case 1; weights OFFICIAL from the PDF; targets are INFERENCE)

| Round | Criterion (weight) | Target /10 | What must be visible | Hard? |
|---|---|---|---|---|
| 1 | Problem understanding (15%) | 8.3 | Closed-loop framing in the PDF's words; "mild imbalance" addressed; human only for exceptions | |
| 1 | Architecture clarity (20%) | 8.0 | One diagram in the PDF's chain data → features → model → agent → work order, plus the retrain/registry side loop | compression to one slide |
| 1 | Data engineering approach (15%) | 7.8 | Train-only regime scaling, drop list, rolling features, engine-level validation, leakage audit line | |
| 1 | ML approach & reasoning (20%) | 7.8 | Healthy-baseline health index + HGBR + conformalized quantile interval with reasons; why not LSTM; Robinson 2026 cited | Hard (both blind judges) |
| 1 | MLOps & agent logic (15%) | 8.0 | Severity rule table; gated promotion; drift trigger | |
| 1 | Dataset coverage (10%) | 7.7 | All four subsets by configuration with measured numbers | Hard |
| 1 | Communication quality (5%) | 7.8 | Readable at thumbnail scale; PDF terminology | |
| | **Round 1 weighted** | **≈7.9** | | |
| 2 | Working pipeline (20%) | 8.3 | `make demo` from a clean clone; lock file; tests; recorded run | |
| 2 | Data engineering quality (15%) | 7.8 | Reproducible seeds, schema checks, feature manifest, data hash in MLflow | |
| 2 | Model performance (15%) | 7.2 | Capped and raw RMSE, PHM08 with convention, PICP/MPIW per subset; literature band | Hard |
| 2 | MLOps in action (10%) | 7.8 | MLflow SQLite registry with aliases; drift alarm → retrain → gate accept AND reject | |
| 2 | Agent behavior (10%) | 8.3 | Unit-tested rules; decision confusion matrix; de-duplication; escalation measured | |
| 2 | Dataset coverage (10%) | 7.7 | Per-subset results table FD001–FD004 | Hard |
| 2 | Demo & explanation (20%) | 7.7 | Honest-metrics slide; decision-replay policy table; trade-offs articulated | Hard (one judge) |
| | **Round 2 weighted** | **≈7.8** | | |

## 2. Calendar (PLATFORM dates; capacity INFERENCE)

| Window | Dates | Work |
|---|---|---|
| Round 1 | now → 24 Oct 2026 23:59 IST | One-slide PDF (1–1.5 person-days); baseline re-run on each teammate's machine so the numbers are the team's own |
| Gap (shortlist unknown) | 25 Oct → 13 Nov | Build at low regret: baseline + end-to-end path (this session's Phases 3–4) |
| Round 2 | 14 Nov → 13 Dec 2026 | Experiments, red team, demo, 10-slide deck + annex; plan on ~50% availability (exams, UNKNOWN) |
| Finale | TBA | Presentation; live demo only if allowed |

Capacity: 3 students × ~13 h/week × 7 weeks ≈ 34 person-days; minimum complete submission 13–16 person-days; full blueprint 20–24 person-days (effort review). Fits even with two active members.

## 3. Risk register

| # | Risk | Likelihood | Impact | Control | Status |
|---|---|---|---|---|---|
| K1 | Registration/portal problem (listing shows contradictory deadlines) | medium | fatal | Team leader confirms registration and upload mechanics this week; submit by 23 Oct | OPEN (team action) |
| K2 | Commoditisation: looks like an FD001 notebook (HYPOTHESIS about the field) | high | high | Closed loop and leakage audit on the slide; decision-replay table; four subsets; cite Robinson 2026 | controlled by design |
| K3 | Environment fragility (observed: streamlit/plotly mismatch, LightGBM crash, pandas 3 pull) | high | medium | `.venv` with `requirements.lock.txt` (VERIFIED); HGBR not LightGBM; `make doctor`; fresh-clone rehearsal | controlled |
| K4 | MLflow registry misconfiguration (file store unsupported; stages deprecated) | medium | medium | SQLite backend and aliases (VERIFIED fact) | controlled |
| K5 | Deck-only judging: live demo never seen | high | medium | Deck carries every number; annex = repo + recorded clean-clone run + Dockerfile | controlled by plan |
| K6 | Over-claiming (coverage "guaranteed", novelty, cost savings) | medium | high | Claim-evidence matrix; coverage quoted as measured and as Robinson's published range; no cost claims from simulated data without sensitivity | controlled by process |
| K7 | Single laptop, OneDrive sync | medium | high | Git remote from day 1 (team action; this session does not commit unless asked) | OPEN (team action) |
| K8 | Exam overlap during Round 2 | medium | medium | Build the minimum complete submission during the gap; Round 2 window for experiments and polish | planned |
| K9 | Residual drift not computable live (labels unknown until failure) | certain | low | Feature drift live; residual drift retrospective; stated openly | designed in |
| K10 | Coverage below nominal on some subsets (literature 0.84–0.95) | likely | low | Report per subset; interval width used as "insufficient evidence" signal, not as a guarantee | designed in |
| K11 | 5 MB deck limit (Season 3 precedent, UNVERIFIED) | medium | medium | Compressed screenshots; recording hosted externally; check the portal | planned |
| K12 | IP clause (ideas become Tata Elxsi property) | certain | team decision | Acknowledge before submitting | OPEN (team action) |
