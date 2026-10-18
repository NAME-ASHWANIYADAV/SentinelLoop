# Submission package (SentinelLoop, TELIPORT Season 4, Case Study 1)

| File | What it is | How it was made | Status |
|---|---|---|---|
| `SentinelLoop_Round1_CaseStudy1.pdf` (+ `.png`) | Round 1 single-slide idea submission (16:9, one page, about 80 KB, PDF metadata set) | `python submission/make_round1_slide.py --team "<Team> · <College>" --deck` | rendered with a placeholder team name; **re-render with the real names before upload** (the script refuses placeholders unless `--allow-placeholder`) |
| `SentinelLoop_Round1_design_deck.pdf` | The same Round 1 content as a 4-page design deck at 11–20 pt | same command (`--deck`) | upload instead of the one-pager only if the portal form accepts several pages (the case-study PDF says "design and Architecture slides deck"; the Unstop listing says "a single slide") |
| `round1_slide_content.md` | The slide's text, generated from the same script (never edited by hand) | same command | current |
| `SentinelLoop_Round2_deck.pptx` | Round 2 10-slide deck, every number read from `artifacts/` and `experiments/results/` | `NODE_PATH=submission/deck_build/node_modules node submission/make_round2_deck.js --team "<Team> · <College>" --apply-theme <pptx-skill>/scripts/apply_theme.js` (after `npm install` in `submission/deck_build`) | structure validated (`validate.py`: all checks passed); **visual check in PowerPoint is a team action** (no LibreOffice on the build machine); team name placeholder on slide 1 |
| `round2_deck_content.md` | The deck's content plan with rubric mapping and evidence ids | written in Phase 8 | final |
| `CLAIM_EVIDENCE_MATRIX.md` | Every claim with its status, artefact and regeneration command (C1–C25) | written in Phase 8 | final |
| `make_round1_slide.py`, `make_round2_deck.js`, `deck_build/package.json` | Generators | — | re-run after any change to the artefacts |

Supporting evidence a judge may ask for: `docs/NUMBERS.md` (generated digest of every number), `docs/EXPERIMENT_RESULTS.md`, `docs/RED_TEAM_REVIEW.md`, `docs/KNOWN_LIMITATIONS.md`, `docs/REPRODUCIBILITY.md`, `docs/DEMO_RUNBOOK.md`, `docs/DEMO_SCRIPT.md`, `experiments/results/run_all_phase6.log`.

Not in this folder (team actions): the recorded clean-clone run (`recording_*.mp4`), the repository link, the portal registration.
