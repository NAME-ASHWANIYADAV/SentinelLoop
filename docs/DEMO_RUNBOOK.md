# Demo Runbook (Phase 7, revised after the red-team review; numbers are filled from the final evidence run in `docs/EXPERIMENT_RESULTS.md`)

Target machine: the team's Windows laptop (or any machine with Python 3.11+; tested on 3.12.1). Everything is offline. Setup from a clean clone: about 10 minutes plus the evidence run (`experiments/run_all.py`, wall time recorded in `docs/REPRODUCIBILITY.md`). Commands are run from the project root; paths are relative to it.

## 0. One-time setup
```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.lock.txt
.venv/Scripts/python.exe -m pip install -e . --no-deps
.venv/Scripts/python.exe -m sentinelloop data --download      # or copy data/raw/ from the team share (checksummed)
.venv/Scripts/python.exe -m sentinelloop doctor               # must print "doctor: OK"
```

## 1. Produce the artefacts the demo shows (BEFORE the demo day; keep the folder and zip it)
```bash
.venv/Scripts/python.exe experiments/run_all.py                # E0, pipeline (all subsets, 5 streamed engines each), E1-E7, secondary E4, seed check
```
Then zip `artifacts/` and `experiments/results/` as `demo_evidence_<date>.zip`: it is the reset point and the fallback. The evidence shown in the deck was produced by exactly this command (log `experiments/results/run_all_phase6.log`).

## 2. Reset procedure (never deletes evidence)
Unzip `demo_evidence_<date>.zip` over the project at the SAME path (MLflow stores absolute artefact locations). Nothing in the demo writes into `artifacts/`: the live runs below use `--out-dir artifacts_demo`, which can be deleted at any time.

## 3. Deterministic demo scenario (scripted, about 7 minutes with slack; spoken lines in `docs/DEMO_SCRIPT.md`)
1. `python -m sentinelloop doctor` — environment and data checksums (10 s).
2. `python -m sentinelloop run --subset FD001 --fast --stream-units 3 --out-dir artifacts_demo` — the whole loop live into a scratch folder (about 10 s; the fast model is slightly worse than the shipped one and the presenter says so). Log lines to read aloud: prepare → models → monitors → agent (batch + stream) → done with metrics; the printed `max_width` is the calibrated width limit.
3. `python -m sentinelloop retrain --subset FD003 --simulate-new-data --fast --out-dir artifacts_demo` — the retraining flow when new data arrives (about 20 s): the champion is trained on 50 engines, 30 "new" engines arrive as a file under `artifacts_demo/incoming/`, a challenger is trained, gated and promoted or rejected with the reasons printed. (FD003 is used because its stored E4 runs show both a PROMOTE and the REJECT rows; the live outcome is whatever the gate decides, and the presenter reads the printed reasons either way.)
4. `python -m sentinelloop dashboard` → browser on http://localhost:8501 (reads the shipped `artifacts/`):
   - **Fleet** tab: metric tiles (RMSE capped/raw, PHM08, coverage, width, escalation share), severity bar, fleet table with quality and drift columns.
   - **Engine** tab: pick a CRITICAL engine from the fleet table (batch trace): RUL point with the 90% band, the dotted lower bound that drives the agent, anomaly score vs threshold, the latest decision with the rules fired, input quality and the top deviating features. The cycle-by-cycle stream table exists for engines 1–5 only (the ones replayed in stream mode).
   - **Work orders** tab: one open order per unit, action, due-by cycle, top sensors, MAINTENANCE vs INSPECTION.
   - **Model & monitoring** tab: conformal calibration (alpha, qhat, calibration rows), drift report (age-matched), quality, the decision-vs-truth table, and the retraining log with the PROMOTE and REJECT rows of both E4 runs (and the `cli` row if step 3 was run against `artifacts/`).
   - **Experiments** tab (filtered to the selected subset): E1 policy table and frontier, E2, E3 by fault, E4 primary and secondary, E5, E6, E7, seed sensitivity. The captions quote the pre-registered verdicts, including NOT SUPPORTED for H1, H2 and H4: the presenter owns them before a judge reads them.
   - **Audit** tab: "Verify hash chain and re-derive every decision" → mismatches 0, chain valid true (this tab shows the selected subset's log; the 3,409-decision figure in the deck is the total over the four subsets).
5. `python -m sentinelloop audit` in the terminal — the same check from the CLI over all four logs (5 s).
6. Optional: `python -m mlflow ui --backend-store-uri sqlite:///artifacts/mlflow.db` — registered models `sentinelloop-FD00x` (`champion` alias = the pipeline model) and `sentinelloop-FD00x-gated` (E4 scenarios; the alias is handed back to the champion after every scenario).

## 4. Fallbacks (never present a mock as a live result)
- Dashboard will not start: open `artifacts/FD001/metrics.json`, `decisions_test.csv`, `work_orders.json` directly; the numbers are the same.
- A live command fails: the shipped `artifacts/` and `experiments/results/` are untouched (the live runs write to `artifacts_demo/`); say "pre-computed on <date> with the same command" and continue in the dashboard.
- No projector/network: everything is local; the recorded clean-clone run, if the team records one before the demo, is the last resort and is labelled as a recording.

## 5. Checks before leaving for the demo
- `python -m pytest tests -q -m "not slow"` green (about 20 s); the full suite (`python -m pytest tests -q`) is the pre-submission check.
- Browser zoom 110%, light theme, window 1920×1080.
- `artifacts/` from the evidence run present (not a fast run); `experiments/results/*/summary.json` present; `artifacts_demo/` deleted.
- Terminal font ≥ 16 pt; commands in a text file to paste.
