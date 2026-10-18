# Final Validation (Phase 9, 2026-10-18)

Everything below was executed in this workspace on the final code; nothing is inferred.

| Check | Command | Result | Record |
|---|---|---|---|
| Full test suite | `.venv/Scripts/python.exe -m pytest tests -q` | **114 passed in 79.7 s, exit 0** (unit tests on synthetic frames; integration tests on the real data incl. the FD001 pipeline, stream = batch bitwise, the retraining flow, MLflow on SQLite, the CLI parser) | `experiments/results/test_full_final.log` |
| Environment and data | `python -m sentinelloop doctor` | `doctor: OK` (Python 3.12.1; 12 C-MAPSS files; both archive checksums OK) | console |
| Audit re-derivation | `python -m sentinelloop audit` | 3,409 decisions, 0 mismatches, every chain valid | console; `experiments/results/e6_audit_check/summary.json` |
| Evidence run | `python experiments/run_all.py` from a clean `artifacts/` and empty OOF cache | ALL DONE in 55.0 min; every `summary.json` and `metrics.json` regenerated | `experiments/results/run_all_phase6.log` |
| Numbers digest | `python experiments/numbers_digest.py` | `docs/NUMBERS.md` regenerated; every number in README, results, deck plan, demo script and claim matrix copied from it | `docs/NUMBERS.md` |
| Demo commands | `run --subset FD001 --fast --stream-units 3 --out-dir artifacts_demo`; `retrain --subset FD003 --simulate-new-data --fast --out-dir artifacts_demo` | 19 s and 20 s; the live gate promoted the FD003 challenger (RMSE 14.95 → 13.98, coverage 0.91 → 0.94); `artifacts/` untouched | console |
| Dashboard | `.claude/launch.json` → Streamlit on port 8501, built-in browser | Fleet tiles, Model & monitoring (decision-vs-truth table, both E4 runs), Experiments (frontier tables, subset filter), Audit verify (510 records, 0 mismatches) render on the final artefacts | browser session |
| Round 1 slide | `python submission/make_round1_slide.py --team "…" --allow-placeholder --deck` | one page, 80 KB, PDF metadata; 4-page variant 59 KB; rendered PNG inspected (no overflow) | `submission/` |
| Round 2 deck | `node submission/make_round2_deck.js … --apply-theme …` + pptx skill `validate.py` | 10 slides, 79 KB; "All validations PASSED"; heuristic text-fit check: 0 flags | `submission/SentinelLoop_Round2_deck.pptx` |

Not validated here (team actions): the PPTX viewed in PowerPoint (no LibreOffice on this machine), the portal upload form, the recorded run, a fresh-machine install (the lock file was corrected for a fresh machine but not exercised on one).

Determinism note: two consecutive pipeline runs were identical on this machine in Phase 4 (pre-review code); after the feature-arithmetic change (D23) the full run was executed once; `tests/test_stream.py` and `tests/test_pipeline_smoke.py` check bitwise equality between the batch and stream paths on every run.
