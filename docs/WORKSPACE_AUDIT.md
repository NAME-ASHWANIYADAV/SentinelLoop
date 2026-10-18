# Workspace Audit (Phase 0)

Audited 2026-10-18. Project root: `C:\Users\HP\OneDrive\Desktop\tata` (not a git repository). All paths below are relative to it.

Status vocabulary: **VERIFIED** (checked or executed in this session), **PARTIALLY VERIFIED**, **PROPOSED** (planned, not built), **BLOCKED**.

## 1. Official problem statements

| Artefact | Exists | Valid | Checked |
|---|---|---|---|
| `Case Study 1_ACTG_Predictive_Maintenance.pdf` (4 pages) | yes | yes | VERIFIED: read in full in the prior session (text + rendered pages); faithful transcription in `analysis/00_requirements_matrix.md` |
| `Case Study 2_IDV_Battery_Energy_System.pdf` (3 pages) | yes | yes | VERIFIED (same) |
| `Case Study 3_MCV_Adaptive QoS Engine ….pdf` (3 pages) | yes | yes | VERIFIED (same) |
| `Case Study 4_HLS_End-to-End Medical Device Labeling ….pdf` (8 pages) | yes | yes | VERIFIED (same) |
| `Case Study 5_TBU_Vehicle Information using On-Device SLM or LLM.pdf` (3 pages) | yes | yes | VERIFIED (same) |

## 2. Prior analysis (from the case-selection session)

| Artefact | Exists | Valid | Checked |
|---|---|---|---|
| `analysis/TELIPORT_S4_case_selection_report.md` (≈9.7k words) | yes | yes | VERIFIED: passed a critic pass; recommends Case 1 with risk-adjusted 7.86 vs 7.26 (Case 3); treated as PROVISIONAL here |
| `analysis/00_requirements_matrix.md` | yes | yes | VERIFIED against rendered PDF pages (weights for Cases 1 and 2; no weights in 3, 4, 5) |
| `analysis/01_scoring_model.md` | yes | yes | VERIFIED: cross-case weights, fixed before results |
| `analysis/evidence/agent_outputs/*.json` (26 files: 5 specialists, 2 judges, 3 reviewers, 12 fact-checks, 2 competitor analyses, 2 matrices) | yes | yes | VERIFIED present; contents used by `final_matrix.py` |
| `analysis/evidence/cmapss_baseline.py` | yes | yes | VERIFIED: executed four times (specialist, fact-checker on all subsets, two FD001 re-runs); numbers agree within 0.4 RMSE |
| `analysis/evidence/cmapss_baseline_rerun.log` | yes | yes | VERIFIED: FD001 RMSE 14.18 capped / 15.42 raw, NASA 308; FD002 16.22/27.90/1234; FD003 14.08/15.71/458; FD004 17.88/28.92/1919 |
| `analysis/evidence/final_matrix.py`, `parse_results.py` | yes | yes | VERIFIED: re-runnable against `agent_outputs/` |
| `analysis/evidence/wsl2_tc_testbed_check.sh` | yes | yes | PARTIALLY VERIFIED: executed once by a reviewer on this machine's WSL2 (Case 3 evidence); not re-run here |
| `analysis/evidence/pybamm_ecm_smoke_test.py` | yes | partial | PARTIALLY VERIFIED: ran, but only the discharge step executed (Case 2 evidence) |
| `analysis/evidence/local_reproduction_notes.md` | yes | yes | VERIFIED: verbatim reviewer measurements |

No source code, model files, configs, tests, experiment results or logs for the solution itself existed before this session. Nothing is overwritten; the solution is built alongside `analysis/`.

## 3. Dataset

| Artefact | Exists | Valid | Checked |
|---|---|---|---|
| `data/raw/pcoe_turbofan.zip` | yes (copied from the research download) | yes | VERIFIED: 12,429,152 bytes, md5 `a83e8f128c59fc5614a4ca2e42a2e30c` = the S3 ETag recorded during research |
| `data/raw/CMAPSSData.zip` | yes | yes | VERIFIED: 12,425,978 bytes, md5 `79a22f36e80606c69d0e9e4da5bb2b7a` |
| `data/raw/train_FD001..004.txt`, `test_FD001..004.txt`, `RUL_FD001..004.txt`, `readme.txt`, `Damage Propagation Modeling.pdf` | yes | yes | VERIFIED: 26 columns; units FD001 100/100, FD002 260/259, FD003 100/100, FD004 249/248 (readme states 248/249, the files are authoritative); sha256 prefixes recorded in `docs/REPRODUCIBILITY.md` once written |
| Licence | — | — | VERIFIED: data.nasa.gov page says "License not specified"; PCoE asks for acknowledgement and citation of Saxena et al. (PHM08). We cite, do not redistribute the archive in the submission, and provide the download script instead |

## 4. Environment (as found)

| Item | State | Status |
|---|---|---|
| Python | 3.12.1 at `C:\Python312` | VERIFIED |
| numpy 1.26.4, pandas 2.2.0, scikit-learn 1.4.0, scipy 1.15.3, mlflow 2.15.1, matplotlib 3.9.2, pyarrow 24.0.0, joblib 1.3.2 | installed system-wide | VERIFIED |
| streamlit | installed but `import streamlit` fails (plotly 4.14.3 incompatibility) | VERIFIED broken |
| pytest, evidently, river | not installed | VERIFIED missing |
| lightgbm 4.7.0 | installed; crashed with an access violation during research | VERIFIED unreliable: not used |
| CPUs / disk | 12 logical CPUs; 21 GB free on C: | VERIFIED |
| Project venv `.venv` with pinned packages (`requirements.lock.txt`) | being created | see `PROJECT_STATUS.md` |

## 5. Competition facts

See `docs/OFFICIAL_REQUIREMENTS.md` (Phase 1). As of this audit no official Tata Elxsi page was found; Unstop and GradPartners listings exist and are being read.

## 6. What is reused

- Requirements matrix and PDF transcriptions (source of truth for criteria).
- The verified baseline script as the reference for the Phase 3 baseline numbers.
- The blueprint in the selection report (Sections D and E) as the starting design, subject to Phase 2 revision.
- The agent outputs as prior-art research input for `research/PRIOR_ART_AND_DIFFERENTIATION.md`.
