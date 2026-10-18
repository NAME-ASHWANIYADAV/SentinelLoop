# Phase 3 — Common Scoring Model (weights fixed BEFORE any agent results were read)

These are OUR cross-case comparison weights. They are **not** official competition weights. The official rubrics (Phase 0) are used separately for the "official-score potential" estimate.

| # | Dimension (0–10 each) | Weight | Why this weight |
|---|---|---|---|
| 1 | Fit with our demonstrated technical skills | 8% | Matters, but we are told not to over-favour existing skills |
| 2 | Ability to deliver a complete working prototype | 12% | A finished pipeline is the single most judge-visible difference between submissions |
| 3 | Ability to produce objectively measurable results | 10% | Numbers against a baseline are what survive a skeptical review |
| 4 | Ability to demonstrate reliably in front of judges | 10% | A demo that fails forfeits the "Demo"-type criteria regardless of quality |
| 5 | Potential for meaningful technical differentiation | 9% | Needed to beat other competent teams, but only if it is achievable |
| 6 | Availability and quality of data | 8% | No data → no evidence |
| 7 | Feasibility with free tools / ordinary computers | 7% | Hard constraint from the team background |
| 8 | Engineering depth / ability to defend decisions | 8% | Final-presentation survival |
| 9 | Clarity of alignment with the official rubric | 10% | Weighted, specific rubrics let us target marks; vague rubrics add variance |
| 10 | Low risk of implementation failure / incomplete delivery | 8% | Scored as 10 = very low risk |
| 11 | Explainability to technical and non-technical evaluators | 4% | Real but secondary |
| 12 | Potential for compelling, reproducible evidence | 6% | Reproducibility is explicitly demanded by two of the PDFs |
| | **Total** | **100%** | |

## Two-part evaluation
- **A. Official-score potential (0–10):** expected performance against the actual rubric in the PDF, using exact criteria and weights where given (Cases 1 and 2) or an unweighted mean where none are given (Cases 3, 4, 5). Estimated independently by the specialist agent for the case and by two blind judges who scored all five cases without seeing any specialist analysis.
- **B. Execution-adjusted winning potential (0–10):** whether THIS team can realistically build and demonstrate the solution better than a typical competent student team, after the adversarial review and fact-checks.

## Sensitivity schemes (applied after scores are in)
1. **Base** – weights above.
2. **Equal** – every dimension 8.33%.
3. **Ambition-weighted** – differentiation 20, engineering depth 15, measurable results 12, prototype 10, rubric alignment 8, data 8, demo 7, skill fit 5, free tools 5, low risk 4, reproducible 4, explainability 2.
4. **Safety-weighted** – prototype 18, demo reliability 15, low risk 15, free tools 10, data 10, rubric alignment 10, measurable 8, skill fit 6, reproducible 4, depth 2, differentiation 1, explainability 1.
5. **Rubric-only** – official-score potential alone (judges + specialist mean).
6. **Judges-only** – blind judges' execution-adjusted scores alone (removes specialist advocacy bias).

If the top candidate changes under any scheme, the report must say so and explain why.

## Penalties and rewards (applied in dimension scoring, not as extra terms)
Penalise: unrealistic scope; inaccessible hardware/paid software; generic AI wrappers; unverifiable performance claims; high integration complexity; weak baselines; demo fragility; slide-only novelty; unvalidatable features.
Reward: complete reproducible pipeline; baseline-vs-improved comparisons; honest metrics; engineering reasoning; failure handling and observability; reliable polished live demo; requirement→implementation→evidence traceability; distinctive but achievable innovation.
