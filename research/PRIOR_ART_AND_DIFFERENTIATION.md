# SentinelLoop: prior art and differentiation

Tata Elxsi TELIPORT Season 4, Case Study 1 (predictive maintenance on NASA C-MAPSS; rule-based triage agent; MLflow; retraining; dashboard; no LLM).

Research date: 2026-10-18. Builds on `analysis/evidence/agent_outputs/competitor_cs1.json` and the `resources` field of `analysis/evidence/agent_outputs/specialist_cs1.json`; items already verified there are referenced, not re-verified.

Every important statement carries one of three labels:

- `verified_fact`: the page was fetched on 2026-10-18 and says what is claimed (or the prior research files record a fetch).
- `technical_inference`: a reasoned conclusion from verified facts; could be wrong.
- `unverified_assumption`: seen only in a search snippet, a repo description, or inferred from absence of evidence.

Nothing in this document claims that SentinelLoop is "first" or "globally novel". The honest framing is: each of the six candidate differentiators has published or public precedent in isolation; the combination, applied to C-MAPSS as one reproducible open-source package with reject paths and decision-level evidence, was not found in this search.

---

## 1. Scope and method

### 1.1 What was searched

| Channel | How | Coverage |
|---|---|---|
| Web search (general) | 30 queries (listed below), standard mode | Papers (arXiv, PHM Society, RESS, Scientific Reports, IJPHM), theses, vendor pages, blogs |
| GitHub search API | 7 queries against `api.github.com/search/repositories`, sorted by `updated` | Catches untagged, zero-star repos that the `cmapss` topic page misses |
| GitHub repo pages | 17 README pages fetched and read | Licence, stars, commit count, implemented vs planned features |
| Paper pages | 28 abstract/landing pages fetched; 2 PDFs read directly (Zhou 2020; Saxena 2009) | Verification of what each item actually does |
| Vendor docs | Microsoft Learn (2 pages), AWS (2 pages), MLflow docs, Kestra blueprint, Ewance brief | Reference architectures and gate tooling |
| Kaggle | 2 searches, one restricted to `kaggle.com` | Policy-simulation notebooks |

### 1.2 Queries used (verbatim)

Web search:
1. `C-MAPSS conformal prediction maintenance policy decision remaining useful life`
2. `predictive maintenance MLflow drift retraining dashboard C-MAPSS github`
3. `selective prediction remaining useful life abstain reject option prognostics`
4. `RUL prognostics robustness sensor noise missing data C-MAPSS`
5. `cost-sensitive predictive maintenance decision C-MAPSS maintenance scheduling RUL prediction cost`
6. `prognostics decision metrics beyond RMSE evaluation prognostic horizon alpha-lambda Saxena`
7. `audit trail traceability predictive maintenance decision model version explainable work order`
8. `champion challenger promotion gate MLflow retraining validation gate reject predictive maintenance`
9. `de Pater Mitici alarm-based predictive maintenance scheduling aircraft engines imperfect RUL prognostics`
10. `Nguyen Medjaher dynamic predictive maintenance framework deep learning failure prognostics C-MAPSS cost decision`
11. `adversarial robustness remaining useful life prediction C-MAPSS perturbation sensor attack`
12. `AWS predictive maintenance reference architecture turbofan SageMaker sample github NASA`
13. `Azure predictive maintenance solution guide remaining useful life turbofan Microsoft learn`
14. `kaggle NASA turbofan predictive maintenance notebook MLflow streamlit end-to-end`
15. `Lee Mitici deep reinforcement learning predictive aircraft maintenance probabilistic RUL prognostics C-MAPSS`
16. `prognostics data quality monitoring sensor fault detection input validation RUL model safe fallback`
17. `human-in-the-loop prognostics defer to expert uncertainty threshold RUL decision support escalation`
18. `out-of-distribution detection prognostics RUL C-MAPSS input monitoring unknown operating condition reject`
19. `PHM08 scoring function criticism limitations asymmetric score RUL evaluation metric critique`
20. `"SentinelLoop"`
21. `C-MAPSS missing sensors imputation RUL robustness evaluation masked sensor failure degradation`
22. `prescriptive maintenance decision support C-MAPSS open source dashboard work order generation github`
23. `prediction interval width threshold defer inspection maintenance decision RUL "too uncertain" human review prognostics`
24. `synthetic sensor fault injection evaluation predictive maintenance pipeline missing values noise drift test ML monitoring detects degraded inputs`
25. `kaggle turbofan RUL maintenance threshold simulation cost of late maintenance early replacement notebook policy comparison`
26. `mlflow.evaluate validation_thresholds MetricThreshold model validation gate documentation`
27. `Amazon Lookout for Equipment end of support discontinued date`
28. `prognostics alarm chattering hysteresis repeated maintenance alarms RUL decision stability rescheduling churn`
29. `turbofan RUL maintenance decision cost threshold simulation` (domain-restricted to kaggle.com)
30. `"C-MAPSS" maintenance policy evaluation replay test engines "lower bound" threshold policy comparison "wasted life" OR "unscheduled" per engine simulation`

GitHub API (`q=` value):
- `cmapss mlflow` (16 results, all read)
- `turbofan mlflow` (28 results; 21 read, 7 not rendered)
- `turbofan evidently OR cmapss evidently OR cmapss drift OR turbofan drift` (13 results, all read)
- `turbofan conformal OR cmapss conformal OR rul conformal` (5 results, all read)
- `cmapss "work order" OR turbofan "work order" OR cmapss triage OR turbofan "maintenance policy"` (0 results)
- `cmapss retrain OR turbofan retraining OR turbofan "champion" OR cmapss "challenger"` (2 results, neither relevant)
- `turbofan "fault injection" OR cmapss robustness OR cmapss "noise injection" OR turbofan "audit" OR cmapss "safety margin" OR cmapss "cost-sensitive"` (1 result)

### 1.3 Name check

`verified_fact`: a quoted search for "SentinelLoop" returned only programming tutorials on the "sentinel loop" control-flow idiom; no product, repo or paper with that name surfaced. `unverified_assumption`: the name is free for a hackathon entry (one search is not a trademark search).

---

## 2. Relevant prior work

Differentiator key: (1) policy evaluation by replay, (2) uncertainty-aware decisions with abstention/escalation, (3) sensor/failure stress testing, (4) gated retraining with accept and reject, (5) decision-level metrics beyond RMSE, (6) auditable actions.

Closeness scale: **Far** (one ingredient), **Near** (two or three ingredients, different framing), **Close** (same intent on C-MAPSS, missing pieces), **Very close** (would be hard to differentiate from).

### 2.1 Papers and theses

| # | Item | URL | Type | Covers | How close | Evidence label |
|---|---|---|---|---|---|---|
| P1 | Lee & Mitici, "Deep reinforcement learning for predictive aircraft maintenance using probabilistic RUL prognostics", RESS 230 (2023) 108908. CNN + MC-dropout RUL distributions; DRL policy vs "replace at mean-estimated RUL"; reports cost -29.3%, 95.6% of unscheduled maintenance prevented, wasted engine life 12.81 cycles. CC-BY PDF on the TU Delft portal; 219 Scopus citations. | https://research.tudelft.nl/en/publications/deep-reinforcement-learning-for-predictive-aircraft-maintenance-u | paper | (1)(2)(5) | **Close** on metrics (unscheduled-maintenance rate and wasted life are two of our five), far on method (DRL, not rules; no replay harness released) | verified_fact for the numbers; dataset is "aircraft turbofan engines", C-MAPSS not named on the abstract page (unverified_assumption that it is C-MAPSS) |
| P2 | de Pater, Reijns & Mitici, "Alarm-based predictive maintenance scheduling for aircraft engines with imperfect RUL prognostics", RESS 221 (2022) 108341. Alarms triggered by the evolution of prognostics; scheduling only after an alarm so tasks are not "rescheduled multiple times"; safety factor to absorb RUL error; 20 aircraft x 2 engines; CNN RUL; ILP; engine-failure costs 7.4% of total cost. | https://ideas.repec.org/a/eee/reensy/v221y2022ics0951832022000175.html | paper | (1)(5) | **Close**: this is the "safety-margin policy" and the "decision stability" idea in peer-reviewed form | verified_fact (abstract); full text paywalled; dataset not named on page |
| P3 | Mitici, de Pater, Barros & Zeng, "Dynamic predictive maintenance for multiple components using data-driven probabilistic RUL prognostics: the case of turbofan engines", RESS 234 (2023). Optimal replacement time close to the lower bound of the 99% CI; 53% cost reduction vs time-based. | https://research.tudelft.nl/en/publications/dynamic-predictive-maintenance-for-multiple-components-using-data/ | paper | (1)(2)(5) | **Close**: peer-reviewed basis for the interval-lower-bound policy | verified_fact (from prior research file) |
| P4 | Mitici, de Pater, Zeng & Barros, "Predictive maintenance planning using renewal reward processes and probabilistic RUL prognostics - analysing the influence of accuracy and sharpness", ESREL 2023. Early in life accuracy and sharpness are low so maintenance is scheduled far ahead; when the RUL distribution skews to zero, replace immediately. | https://rpsonline.com.sg/proceedings/esrel2023/html/P064.html | paper | (2)(5) | Near: implicitly a "wait when too uncertain" rule, but no explicit escalation or abstention metric | verified_fact |
| P5 | Nguyen & Medjaher, "A new dynamic predictive maintenance framework using deep learning for failure prognostics", RESS 188 (2019). LSTM gives failure probabilities over horizons to decide when to order parts and maintain; compared against periodic and ideal PdM; discusses imperfect prognostics. 294 citations (Semantic Scholar). | https://doi.org/10.1016/j.ress.2019.03.018 | paper | (1)(5) | Near: the canonical "prognostics to decision" framework; C-MAPSS use not confirmed from the abstract | verified_fact (abstract via Semantic Scholar API); HAL page blocked by an access check |
| P6 | Kamariotis, Tatsis, Chatzi, Goebel & Straub, "A metric for assessing and optimizing data-driven prognostic algorithms for predictive maintenance", RESS 242 (2024), arXiv 2306.03759. Judges a prognostic algorithm by long-run expected maintenance cost per unit time under a stated PdM policy, estimated from run-to-failure data; used to optimise heuristic policies and hyperparameters; tested on four algorithms on "a simulated turbofan engine degradation problem". | https://arxiv.org/abs/2306.03759 | paper | (1)(5) | **Close** for (5): this is the academic version of "evaluate the policy, not the regressor" | verified_fact (abstract); dataset not named on the page |
| P7 | Saxena, Celaya, Saha, Saha & Goebel, "Evaluating algorithm performance metrics tailored for prognostics", IEEE Aerospace 2009 (and the 2010 IJPHM "Metrics for offline evaluation of prognostic performance"). Introduces prognostics-specific metrics (prognostic horizon, alpha-lambda, relative accuracy, convergence) and shows they rank algorithms differently from conventional metrics. | https://c3.ndc.nasa.gov/dashlink/static/media/publication/2009_IEEEAerospace_MetricsEvaluation.pdf ; https://c3.ndc.nasa.gov/dashlink/resources/279 | paper | (5) | Near: standard "beyond RMSE" reference; metrics are accuracy-over-time, not maintenance-decision outcomes | verified_fact (PDF pages 1-3 read; abstract says new metrics "rank these algorithms in a different manner"); metric names from the NASA library README and search summaries |
| P8 | NASA `PrognosticsMetricsLibrary` (MATLAB): alpha-lambda, relative accuracy, convergence; 30 stars, 30 commits. | https://github.com/nasa/prognosticsmetricslibrary | repo | (5) | Far: MATLAB, no maintenance-decision metrics | verified_fact; licence not shown on page |
| P9 | Sharp, "Simple metrics for evaluating and conveying prognostic model performance to users with varied backgrounds", PHM Conf 2013: weighted error bias, weighted prediction spread, confidence-interval coverage, confidence convergence horizon. | https://papers.phmsociety.org/index.php/phmconf/article/view/2317 | paper | (5) | Far | verified_fact |
| P10 | Robinson, "RUL estimation for aircraft engines with risk-aware prediction intervals via conformalized quantile regression", IJPHM 17(1) 2026. GB + asymmetric CQR; coverage 88-92% at 90% nominal on FD001-FD004; no concrete work-order procedure. | https://www.papers.phmsociety.org/index.php/ijphm/article/view/4724 | paper | (2) | Near | verified_fact (prior research) |
| P11 | Javanmardi & Hullermeier, "Conformal prediction intervals for RUL estimation", IJPHM 2023 / arXiv 2212.14612; code `alireza-javanmardi/conformal-RUL-intervals` (no licence). | https://arxiv.org/abs/2212.14612 | paper+repo | (2) | Near | verified_fact (prior research) |
| P12 | Ozcan, "Interpretable ensemble RUL prediction enables dynamic maintenance scheduling for aircraft engines", Scientific Reports 15:39795 (2025). LightGBM/CatBoost ensemble, all four subsets; scheduling layer triggers when predicted RUL < tunable threshold (15 cycles); optional quantile-based triggering; no quantitative scheduling outcomes in the visible text; author states gains are "benchmark-specific" and need confirmation "under alternative risk-aware policies". | https://pmc.ncbi.nlm.nih.gov/articles/PMC12615660/ | paper | (1) | Near: a threshold scheduler on C-MAPSS without decision metrics; its own limitations section is a list of what our harness would add | verified_fact (first 100k chars read) |
| P13 | Gevrek, "Cost-driven predictive maintenance strategy based on varying prediction horizons", METU MSc thesis (2025). LSTM on C-MAPSS; horizons 1-50 cycles scored by economic impact (maintenance vs failure cost); handles repeated failure warnings; SHAP. | https://ii.metu.edu.tr/node/1479 | thesis | (1)(5) | Near | verified_fact (listing page; no numbers) |
| P14 | Choo & Shin, "Integrating ML-based RUL predictions with cost-optimal block replacement", IJPHM 16(1) 2025. RUL + Weibull + block replacement with minimal repair; CMAPSS case study. | https://www.papers.phmsociety.org/index.php/ijphm/article/view/4242 | paper | (1)(5) | Far | verified_fact (abstract) |
| P15 | Khorasgani, Wang, Gupta & Farahat, "An offline deep RL for maintenance decision-making", arXiv 2109.15050 (2021). Recommends continue/repair actions to maximise profit; C-MAPSS case study. | https://arxiv.org/abs/2109.15050 | paper | (1) | Far | verified_fact (abstract) |
| P16 | Basora, Viens, Arias Chao & Olive, "A benchmark on uncertainty quantification for deep learning prognostics", arXiv 2302.04730 (2023). N-CMAPSS; BNN/MC-dropout/ensembles/heteroscedastic; no abstention. | https://arxiv.org/abs/2302.04730 | paper | (2) | Far | verified_fact |
| P17 | Pugnana, Mougan & Nielsen, "Model agnostic explainable selective regression via uncertainty estimation", arXiv 2311.09145 (2023). Selective regression on 69 tabular datasets; package `doubt`; no RUL data. | https://arxiv.org/abs/2311.09145 | paper | (2) | Far: the general method behind "abstain when uncertain" for regression | verified_fact |
| P18 | Mode, Calyam & Hoque, "False data injection attacks in IoT and deep learning enabled predictive analytics", arXiv 1910.01716 / IEEE NOMS 2020. Two FDIA types on C-MAPSS sensors; LSTM/GRU/CNN; attacks on "even a few" sensors defeat RUL; no detection or mitigation proposed. | https://arxiv.org/abs/1910.01716v4 | paper | (3) | Near: stress-tests the model but not the system's self-detection | verified_fact |
| P19 | Zhou, Canady, Li & Gokhale, "Overcoming adversarial perturbations in data-driven prognostics through semantic structural context-driven deep learning", PHM Conf 2020. C-MAPSS; classification + RUL regression; "a framework that can formalize the security and resilience testing in data-driven prognostics settings"; defence = randomisation + structural context. | https://papers.phmsociety.org/index.php/phmconf/article/view/1182 | paper | (3) | Near: frames "resilience testing" of prognostics on C-MAPSS | verified_fact (PDF pages 1-2 read) |
| P20 | Chen et al., "A prediction method for the RUL of equipment for missing data", Complexity 2021. Binary mask simulates packet loss on C-MAPSS; GAIN imputation + MSDCNN-LSTM; RMSE and score. | https://ideas.repec.org/a/hin/complx/2122655.html | paper | (3) | Far: robustness of the model, no detection | verified_fact |
| P21 | Wang, Wang, Cai, Hu & Si, "Robust uncertainty quantification for online RUL prediction with randomly missing and partially faulty sensor data", RESS 262 (2025) 111177. Diffusion imputation + conformal prediction + deep metric learning. | https://pure.nwpu.edu.cn/en/publications/robust-uncertainty-quantification-for-online-remaining-useful-lif/ | paper | (2)(3) | Near: combines missing/faulty sensors with conformal intervals; dataset not stated on page; no decision layer | verified_fact (abstract) |
| P22 | Adams et al., "The impact of sensor faults on condition monitoring of a hydraulic actuator", PHM Conf 2025. Open-source fault-injection package for time series; ensembles more robust than simple models. | https://papers.phmsociety.org/index.php/phmconf/article/view/4415 | paper | (3) | Far: hydraulic dataset, classifier robustness | verified_fact |
| P23 | Sharma, "Uncertainty-aware deep learning framework for RUL prediction in turbofan engines with learned aleatoric uncertainty", arXiv 2511.19124 (2025). FD001-FD004 RMSE 16.22/19.29/16.84/19.98; 93.5-95.2% coverage at 95%; "risk-aware maintenance scheduling" as motivation only. | https://arxiv.org/abs/2511.19124 | paper | (2) | Far | verified_fact; a search snippet attributing a 20-100 cycle threshold sweep with 4% FPR/FNR to a turbofan paper could not be tied to this abstract (unverified_assumption) |
| P24 | Patel & Adisha, "XAgentMaint: explainable agentic systems for predictive maintenance in industrial digital twin environments", ASI Conf 2026 (Kennesaw). RAG + ReAct agent + XGBoost on C-MAPSS FD001-FD004; "a logged decision trail accompanies each explanation to support regulatory auditability"; RMSE 14.8 on FD001. | https://digitalcommons.kennesaw.edu/asi/2026/proceedings/13 | paper | (6) | Near on intent, but LLM-based (disallowed by the case) and the trail contents are not described | verified_fact |
| P25 | Hsu, Frusque & Fink (PHM 2023) and Sanchez et al. (arXiv 2601.10269): healthy-phase residual anomaly detection on C-MAPSS, ~20-cycle detection delay. | https://papers.phmsociety.org/index.php/phmconf/article/view/3444 | papers | (5) partial | Far | verified_fact (prior research) |
| P26 | arXiv 2607.16493 (2026): leakage-audited chunk splits for sliding-window PdM. | https://arxiv.org/abs/2607.16493 | paper | (5) partial | Far | verified_fact (prior research) |
| P27 | Ziyad et al., "An optimized and safety-aware maintenance framework: a case study on aircraft engine", arXiv 2209.02678 (2022). Simulation-based optimisation of a maintenance threshold; 13% extra savings from tailored strategies. | https://arxiv.org/abs/2209.02678 | paper | (1)(5) | Far: dataset and cost values not on the abstract page | verified_fact (abstract); search snippet details (lambda sweep, failure probability 0.28) are unverified_assumption |
| P28 | Baranowski & Bauer, "Optimization of PdM schedules under uncertainty: a scenario-based theoretical framework", arXiv 2605.30222 (2026). Integrated scenario policies vs "single-trigger rules" on expected cost and tail risk; synthetic example. | https://arxiv.org/abs/2605.30222 | paper | (1) | Far | verified_fact |
| P29 | Kim & Jang, "Chance-constrained selection of sequential intervention strategies from counterfactual estimates", arXiv 2608.13209 (2026). One simulated "equipment maintenance" environment with a crew-hour budget. | https://arxiv.org/abs/2608.13209 | paper | (1) | Far; C-MAPSS use is from a search snippet only | verified_fact (abstract); C-MAPSS link unverified_assumption |

### 2.2 Repositories, notebooks and vendor material

Star counts are reported because the brief asks for activity, not as a quality signal; most of the closest matches have zero stars.

| # | Item | URL | Type | Covers | How close | Evidence label |
|---|---|---|---|---|---|---|
| R1 | `sik04/AI-Driven-Digital-Twin-Predictive-Maintainence` ("IntelliTwin"). MIT, 0 stars, 70 commits, pushed 2026-10-17. HistGradientBoosting + LSTM; FD002 primary, FD001 control, FD004 robustness; K-means(6) regimes; 30-cycle causal windows; "decision-aware, condition-adaptive conformal RUL calibration" at 90% nominal; "sequential maintenance simulator" with a "Python replay engine, 18-case deterministic validation suite, cost scenario infrastructure"; four matched control policies on FD002 validation engines over 5 seeds; 10,000-draw bootstrap. Status: "Confirmatory held-out test execution: NOT STARTED; RQ1-RQ4 outcomes: PENDING". No MLflow, dashboard, drift, retraining, escalation. | https://github.com/sik04/AI-Driven-Digital-Twin-Predictive-Maintainence | repo | (1)(2)(5) | **Very close** on (1)+(2)+(5) as a research design: replay simulator, conformal intervals, cost scenarios, policy controls. No results yet, no operational layer, no agent, no reject paths. | verified_fact (README and raw README read); the policy names, cost values and decision metrics are not disclosed in the README |
| R2 | `fredyfanta3443-ops/predict-maintenance`. No licence shown, 0 stars, 1 commit, pushed 2026-09-28. FD001 train, FD003 as fault-mode stress test; LightGBM; nightly rule "open a service work order when predicted flights left < k = 15" (cost cliff at k = 8); unplanned failure = 10x planned service; condition-based servicing cuts cost ~37% (95% bootstrap range 21-49%) vs fixed schedule; thresholds "chosen on some engines and scored on others"; failures per 100 engines reported; drift report (method unspecified) fires ALERT on FD003 (13 of 14 sensors); on ALERT "fall back to the one-sensor rule and retrain"; FD001->FD003 without retraining: RMSE 23.8 and 44 of 100 engines fail; one open work order per engine, safe reruns; FastAPI + React dashboard; MLflow on SQLite; no tests; README admits the model is "not yet proven better than a simple one-sensor rule". | https://github.com/fredyfanta3443-ops/predict-maintenance | repo | (1)(3)(4)(5)(6) partial | **Close**: a single-threshold cost policy with failures-per-100-engines, a drift alarm with a safe fallback, work orders and MLflow. Missing: interval/escalation, policy comparison, promotion gate, stability metric, four subsets, tests. | verified_fact (README + MODEL_CARD read) |
| R3 | `luciforge/Engine-RUL-ML`. Apache-2.0, 0 stars, 8 commits, pushed 2026-04-07. FD001-FD004; LR/RF/XGBoost(Optuna)/LSTM/CoxPH + a threshold-rule baseline; MLflow registry (Postgres or SQLite); Evidently `DataDriftPreset` report; `CostPolicy` picks the lowest expected-cost action among replace/inspect/continue (defaults 5,000 / 500 / 50,000 for a missed failure); `ServiceAlert` urgency; 19 robustness tests for sensor corruption; no drift-triggered retraining, no promotion gate, no dashboard. | https://github.com/luciforge/Engine-RUL-ML | repo | (3)(5)(6) partial | **Close** on cost-sensitive action selection and corruption tests; missing replay evaluation, intervals, gate, audit schema | verified_fact (README) |
| R4 | `Mohith26/aerohealth`. No licence shown, 0 stars, 7 commits, pushed 2026-09-08. LightGBM on all four subsets (RMSE 15.0/30.3/14.9/30.8; PHM 380/20,231/468/22,207, run of 2026-08-05); alert rule "predicted RUL <= 30" scored against the true failure cycle: alert precision/recall 0.95/0.76, 0.91/0.85, 0.94/0.85, 0.85/0.74 and median lead time 15/11.5/14/13 cycles; MLflow runs; FastAPI. No intervals, drift, retraining, dashboard. | https://github.com/Mohith26/aerohealth | repo | (1)(5) partial | **Close** on decision metrics: alert precision/recall and lead time per subset is half of our policy table, for one fixed policy | verified_fact (README) |
| R5 | `mateus-aleixo/turbofan-rul`. MIT, 0 stars, 24 commits, pushed 2026-10-12. LightGBM/LSTM/Transformer on FD001-FD004 (LightGBM RMSE 12.12/13.96/12.27/14.89); CQR with Mondrian calibration per regime and predicted-RUL band; coverage 0.87-0.89 at 90%; widths 11-19 cycles near failure vs 36-45 healthy; API reports nominal and measured coverage; `risk_band` label; "has not been certified as a maintenance tool"; ONNX on AWS Lambda. Consumed by `mateus-aleixo/maintenance-qa-agent` (LLM Q&A with a conformal "answer/decline" gate). | https://github.com/mateus-aleixo/turbofan-rul | repo | (2) | Near: the best public interval machinery found, but intervals do not drive any maintenance decision | verified_fact (both READMEs) |
| R6 | `nithya-prakash/PredictiveMaintenanceAI`. MIT, 0 stars, 27 commits, pushed 2026-10-08. FD001; RF RUL + LR "failure within 30" + IsolationForest; 90% interval coverage 91% (+/-31.2 cycles; method not stated); intervals not used for decisions; drift = mean shift of last 200 vectors vs training std (README admits healthy engines trigger it); Streamlit replay; Postgres logging; k8s manifests "never applied"; no retraining. | https://github.com/nithya-prakash/PredictiveMaintenanceAI | repo | (2)(3)(6) partial | Near | verified_fact |
| R7 | `vaibhav07772/turbofan-rul-mlops`. Licence not shown, 1 star, 16 commits, pushed 2026-10-13. RF/XGB/GB; RUL capped 125 + 3-class health (HEALTHY > 50, WARNING 20-50, CRITICAL < 20); MLflow (SQLite + DagsHub) registry auto-versions each retrain; Evidently (Wasserstein, KS, chi-square) drift tab; Pandera 26-column schema; every prediction written to a JSONL audit log; Streamlit admin dashboard with an audit-log view; Prometheus. No retraining trigger or promotion gate (listed as roadmap). | https://github.com/vaibhav07772/turbofan-rul-mlops | repo | (4)(6) partial | Near: closest public "audit log" on C-MAPSS, but the log holds predictions and classes, not decision evidence (interval, rules fired, model alias) | verified_fact |
| R8 | `ohmatheus/Turbofan-ML-lifecycle`. Licence not shown, 0 stars, 115 commits, pushed 2025-11-28. RF; drift signals = RMSE delta vs baseline, KS > 0.1, PSI > 0.1; any warning triggers retraining; the new bundle is hot-reloaded "without a restart" and the README describes no validation or gate; MLflow used for tracking only; BentoML, Prometheus, Grafana. | https://github.com/ohmatheus/Turbofan-ML-lifecycle | repo | (4) partial | Near: drift-triggered retraining on C-MAPSS exists publicly, with no gate; this is the anti-pattern SentinelLoop's reject path answers | verified_fact |
| R9 | `StepanTitanyan/C-MAPSS_Drift-Anomaly_Distinction`. MIT, 0 stars, 7 commits, pushed 2026-04-20. FD001, 7 sensors; Gaussian GRU trained on healthy windows; URD score (deviation, uncertainty inflation, stationarity incl. frozen sensors); generators inject 5 synthetic anomaly types and 4 drift types; classifier labels events anomaly vs drift; self-reported ROC-AUC 0.86. | https://github.com/StepanTitanyan/C-MAPSS_Drift-Anomaly_Distinction | repo | (3) | **Close** for (3): synthetic drift and sensor-freeze injection with measured detection, on C-MAPSS; not wired to RUL decisions or an agent | verified_fact |
| R10 | `cymmerman/ml-pipeline-deployment`. No licence shown, 0 stars, 6 commits, pushed 2026-06-06. FD001, 9 sensors; IsolationForest + SHAP; KS drift per sensor with severity and a plain-English recommendation; WebSocket replay that injects one of four progressive fault modes; every prediction written to a SQLite audit log. | https://github.com/cymmerman/ml-pipeline-deployment | repo | (3)(6) partial | Near | verified_fact |
| R11 | `jon-gomezz/nasa-predictive-maintenance`. No licence, 0 stars, 9 commits, pushed 2026-04-14. FD001/FD002; binary "failure within 30 cycles"; "cost-sensitive" = `scale_pos_weight` ~5.5; blind-test recall 80% (FD001) and 97% (FD002, 9 false alarms on 198 healthy engines); red/green alert. | https://github.com/jon-gomezz/nasa-predictive-maintenance | repo | (5) partial | Far: class weighting, not a cost model | verified_fact |
| R12 | `Shiverion/AeroRUL`. No licence shown, 0 stars, 9 commits, pushed 2026-08-11. FD001-FD004; XGB/LSTM/TCN/Transformer/Weibull AFT; split conformal 90% (coverage 89-96% FD001/FD003, 76-80% FD002/FD004, flagged as optimistic); a "decision layer" producing text like "ground for inspection" whose rules are not documented; React dashboard with risk tiers and uncertainty bands; README reports a capped-label evaluation bug (FD002 RMSE 15.2 -> 27.7). | https://github.com/Shiverion/AeroRUL | repo | (2)(6) partial | Near | verified_fact |
| R13 | `RudraTrivedi14/turbofan-prognostics-mlops` (pushed 2026-10-10) and `jai-krishna-0921/predictive-maintenance-mlops` (Apache-2.0, 6 commits). Both describe drift detection, auto-retraining and (for the second) a Vertex AI "promotion gate" on the PHM08 score, but READMEs show these are roadmap/scaffold only. | https://github.com/RudraTrivedi14/turbofan-prognostics-mlops ; https://github.com/jai-krishna-0921/predictive-maintenance-mlops | repos | (4) claimed | Far (not built) | verified_fact |
| R14 | `RaviSingh48/Predictive-Maintenance-ML` (IsolationForest + XGBoost + MLflow + Streamlit; 3 commits; no rules), `aezzahir/...`, `ajazhussainsiddiqui/cmapss-rul-mlops`, `fiza-pathan/predictive-maintenance-mlops`, `Atharvadahitule/...`, `hamza100x/rul-predictor`, `CCao666/predictive-maintenance-mlops` (Kafka), `Krishna4396/...` (PySpark+Kafka), `ToprakKS/AeroGuard-Industrial-MLOps` (Kafka+K8s). | see Section 8 | repos | generic | Far: the "RUL model + FastAPI + Streamlit + MLflow screenshot" shape | verified_fact for R14 README; others description-only (unverified_assumption) |
| R15 | `HariniSuresh6/turbofan-rul-data-pipeline` ("activation-based drift detection"), `Rifatsarkar3/Mamba` ("conformal intervals and a bounded-drift projection"), `DK-Krishna2001/DriftGuard-NASA-CMAPSS-Turbofan-Drift-Monitor` (no description), `AmmarHafeez/industrial-maintenance-mlops` (drift reporting). | see Section 8 | repos | (3)(2) claimed | Unknown | unverified_assumption (descriptions only) |
| R16 | `Isuruigi/ml-monitoring-system`. MIT, 0 stars, 7 commits. Generic Evidently 0.4 + MLflow 2.9.2 + FastAPI + Next.js; "smart triggers" for retraining; no validation/approval gate described; no dataset named. | https://github.com/Isuruigi/ml-monitoring-system | repo | (4) partial | Far (now verified; was unverified in the prior research) | verified_fact |
| R17 | Kestra blueprint "Drift-triggered champion/challenger retraining". Evidently 0.7.23 `DataDriftPreset` (KS/chi-square), `drift_share_threshold` 0.3; challenger trained on 70% of the new batch, both scored by MAE on 30%; verdicts BOOTSTRAP / STABLE / PROMOTE / HOLD; HOLD fails the run and keeps the champion; old champion archived; salary CSV (~3,000 rows); MLflow only suggested as an extension; HOLD presented as an expected outcome, not a captured run. | https://kestra.io/blueprints/evidently-drift-champion-challenger-retrain | tutorial | (4) | **Close** for (4) as a pattern (both PROMOTE and HOLD paths exist); not PdM, not C-MAPSS, no safety gate | verified_fact |
| R18 | Ewance challenge brief "Automate retraining with a drift-triggered MLflow pipeline": Evidently + Airflow + MLflow registry; "promote-on-win" gate plus a human approval step; "audit-ready retraining process"; no dataset; reject path implied, not required. | https://ewance.com/en/challenges/automate-retraining-with-a-drift-triggered-mlflow-pipeline-mlops-and-ml-engineering-master/ | course brief | (4)(6) | Near | verified_fact |
| R19 | MLflow model validation: `mlflow.validate_evaluation_results(candidate_result, validation_thresholds=...)` with `MetricThreshold(threshold=..., greater_is_better=...)`; failure raises `ModelValidationFailedException`; moved out of `mlflow.models.evaluate()` in 2.18.0. API source lists `min_absolute_change` / `min_relative_change` for candidate-vs-baseline checks. | https://mlflow.org/docs/latest/ml/evaluation/ | official doc | (4) | Commonplace tooling: the gate primitive is built in | verified_fact for the docs page; baseline-comparison parameters seen in API source via search (technical_inference that they are present in MLflow 3.x; verify in the pinned version) |
| R20 | `awslabs/predictive-maintenance-using-machine-learning`. Apache-2.0, 110 stars, 20 commits. SageMaker demo on NASA turbofan data; MXNet stacked BiLSTM; Lambda-triggered Batch Transform on schedule or S3 put; results to S3 "for use in a dashboard". No drift, retraining automation, work orders or decision logic. | https://github.com/awslabs/predictive-maintenance-using-machine-learning | vendor repo | none of (1)-(6) | Far | verified_fact |
| R21 | Azure IoT "Predictive Maintenance solution accelerator" (archived doc, `is_archived: true`, dated 2019-03-08): RUL regression from 4 sensors (9, 11, 14, 15) on the public turbofan set; IoT Hub + Stream Analytics + ML workspace; no work orders, retraining or drift. The "aircraft engine monitoring for predictive maintenance in aerospace" solution-idea URL cited in the prior research now serves the "Microsoft for Manufacturing" hub page (updated 2026-07-27), so that reference design is no longer published at that address. | https://learn.microsoft.com/en-us/previous-versions/azure/iot-accelerators/iot-accelerators-predictive-walkthrough ; https://learn.microsoft.com/en-us/azure/architecture/solution-ideas/articles/aircraft-engine-monitoring-for-predictive-maintenance-in-aerospace | vendor doc | none | Far | verified_fact (both fetched today); this resolves the prior research's unverified_assumption about the Azure page |
| R22 | Amazon Lookout for Equipment: "On October 7, 2026, AWS will discontinue support"; managed anomaly detection on sensor data with notifications and human feedback. | https://aws.amazon.com/lookout-for-equipment/ | vendor page | (3)(6) partial | Far; retired | verified_fact |
| R23 | Kaggle: two searches (one domain-restricted) found no notebook that simulates maintenance policies or compares late-maintenance vs early-replacement cost on C-MAPSS; results were EDA/RUL notebooks and dataset mirrors. | https://www.kaggle.com/datasets/behrad3d/nasa-cmaps | notebooks | none | n/a | unverified_assumption (Kaggle's notebook search is poorly indexed by web search) |
| R24 | Prior-research items retained: AI Kavach (`adityapotdar23/Predictive-Maintenance`, hackathon winner, tree models + React + alerts, no MLOps), TurboGuard (dual-LSTM + Streamlit), IEEE-IES lab repo (RMSE 12.9-13.4 on FD001), kpeters notebooks (GPL-3.0), `aun151214/predictive-maintenance-cmapss`, GitHub topic `cmapss` (53 repos). | see `competitor_cs1.json` | repos | generic | Far | verified_fact (prior research) |

---

## 3. What competing solutions already do (commonplace features)

Everything in this section should be treated as table stakes. Claiming any of it as innovation would be scored as naive by a judge who knows the field.

| Feature | Status | Evidence |
|---|---|---|
| C-MAPSS loading, dropping near-constant sensors, RUL cap 125, rolling mean/std/slope features, K-means(6) regime normalisation for FD002/FD004 | **Commonplace** | kpeters, IntelliTwin, aerohealth, vaibhav07772, AeroRUL, Sharma 2025 (verified_fact) |
| Engine-level train/validation splits described as leakage prevention | **Commonplace in the better repos** | RudraTrivedi14, vaibhav07772, mateus-aleixo, StepanTitanyan, fredyfanta ("a row-level split would have reported 6.5 flights of error, which the document calls false"), jon-gomezz (verified_fact) |
| GBM / RF / XGBoost / LSTM / Transformer RUL regressors with FD001 RMSE 12-16 | **Commonplace** | dozens; mateus-aleixo reports LightGBM 12.12 on FD001 and beating deep models on 3 of 4 subsets (verified_fact) |
| Reporting both RMSE and the PHM08 asymmetric score; stating the cap | **Commonplace among the stronger repos; many still mis-evaluate against capped labels** | aerohealth, AeroRUL (self-reported bug), jai-krishna (verified_fact) |
| Split-conformal or CQR prediction intervals on RUL, coverage 87-96% at 90% nominal | **Commonplace since 2023** | Javanmardi, Robinson, mateus-aleixo (Mondrian CQR), AeroRUL, nithya-prakash, IntelliTwin (verified_fact) |
| IsolationForest / autoencoder anomaly score on healthy-phase windows | **Commonplace** | nithya-prakash, RaviSingh48, cymmerman, StepanTitanyan, TurboGuard, Hsu 2023 (verified_fact) |
| Fixed point-RUL threshold alerts (RUL <= 30 or <= 15; HEALTHY/WARNING/CRITICAL bands at 50/20) | **Commonplace** (this is the "generic agent") | aerohealth, vaibhav07772, Ozcan 2025, fredyfanta k = 15, jon-gomezz (verified_fact) |
| A single-threshold cost policy with a failure:service cost ratio and a savings figure vs fixed schedule | **Exists publicly on C-MAPSS** | fredyfanta (10x, ~37% savings, bootstrap CI) (verified_fact); peer-reviewed analogues P1-P6 |
| Alert precision/recall and median lead time scored against the true failure cycle | **Exists publicly on all four subsets** | aerohealth (verified_fact) |
| Expected-cost action selection (replace / inspect / continue) from configurable costs | **Exists publicly** | luciforge `CostPolicy` (verified_fact) |
| MLflow tracking + registry (SQLite), FastAPI serving, Streamlit or React dashboard | **Commonplace** | 16 repos for `cmapss mlflow`, 28 for `turbofan mlflow` (verified_fact) |
| Evidently `DataDriftPreset` drift report or KS/PSI drift tab | **Commonplace** | vaibhav07772, luciforge, ohmatheus, cymmerman, nithya-prakash (verified_fact) |
| Drift-triggered retraining with hot reload and no validation gate | **Exists publicly on C-MAPSS** | ohmatheus (verified_fact) |
| Champion/challenger gate with PROMOTE / HOLD verdicts | **Commonplace as an MLOps pattern; not found on C-MAPSS** | Kestra blueprint, Ewance brief, MLflow `validate_evaluation_results` (verified_fact) |
| Per-prediction audit log (JSONL or SQLite) | **Exists publicly on C-MAPSS** | vaibhav07772, cymmerman (verified_fact) |
| Synthetic fault / drift / sensor-freeze injection into C-MAPSS streams with a detector scored by ROC-AUC | **Exists publicly** | StepanTitanyan, cymmerman (verified_fact) |
| Cross-subset "stress test" (train FD001, test FD003) with a drift alarm and a safe fallback rule | **Exists publicly** | fredyfanta (verified_fact) |
| Streaming replay of test engines over WebSocket / Kafka | **Commonplace** | cymmerman, CCao666, Krishna4396, ToprakKS, nithya-prakash (verified_fact / descriptions) |
| LLM-based "agentic" maintenance assistants | **Emerging, and disallowed by the case** | XAgentMaint, mateus-aleixo/maintenance-qa-agent, Turbomind-AI (verified_fact) |

`technical_inference`: the modal public C-MAPSS repo in 2026 is more capable than the prior research's "generic student implementation" hypothesis assumed. Conformal intervals, Evidently, engine-level splits and PHM08 reporting are now routine in zero-star repos pushed in the last six months. Differentiation therefore cannot rest on having intervals or drift reports; it must rest on what is done with them and on evidence that is checkable.

---

## 4. What SentinelLoop will do differently

For each differentiator: the closest prior item, what it already does, and the precise delta. The delta is always integration- or evidence-level, not scientific novelty.

### (1) Maintenance-policy evaluation by cycle-by-cycle replay

- **Closest prior**: IntelliTwin (R1) has a replay engine, cost scenarios and four matched control policies, with results pending; Lee & Mitici (P1) report unscheduled-maintenance rate and wasted life for DRL vs mean-RUL replacement; de Pater et al. (P2) evaluate an alarm + safety-factor policy and note it stops repeated rescheduling; Kamariotis et al. (P6) define cost-per-unit-time as the metric; fredyfanta (R2) scores one threshold policy by failures per 100 engines and cost; aerohealth (R4) scores one alert rule by precision/recall and lead time.
- **Already done elsewhere**: replaying run-to-failure data to score a policy (P1, P2, P6, R1); single-threshold policies tuned on validation engines (R2); lead time and alert precision/recall (R4).
- **SentinelLoop delta** (`technical_inference` that this exact bundle is absent from public C-MAPSS work):
  - Four named policies evaluated on *identical* predictions per subset: A point-RUL threshold (the commonplace agent), B fixed safety margin on the point estimate (P2's safety factor), C interval-lower-bound threshold (P3's finding), D cost-sensitive threshold chosen on validation engines under a stated failure:service cost ratio (R2/P6 framing). Thresholds for B-D are chosen on validation engines only.
  - Five decision metrics reported together: late-order rate (order after true failure or never), discarded life (true cycles remaining at first order), lead time, alert volume (orders per engine), and decision stability (severity flips and re-issued orders per engine). Stability is the metric no public C-MAPSS repo reports; P2 argues for it qualitatively.
  - Zero-leakage replay: the true RUL at each replayed test cycle is `RUL_final + (T_last - t)`, so no synthetic labels are needed (already in the prior research; it matches how aerohealth and the THULab mirror expand labels).
  - One command (`make replay`) regenerates the table for FD001-FD004; it is the lead artefact of the demo, not a footnote.

### (2) Uncertainty-aware decisions with abstention and escalation to a human

- **Closest prior**: P3 (replace near the lower bound of the 99% CI), P10 (asymmetric CQR motivated by late-maintenance cost), P4 (when sharpness is low, maintenance is scheduled far ahead, i.e. an implicit "wait"), R5 (best public interval machinery; `risk_band` but no decision), P17 (selective regression in general), R5's sibling `maintenance-qa-agent` (a conformal gate that declines to answer, but for an LLM Q&A tool).
- **Already done elsewhere**: conformal RUL intervals with measured coverage (many); the lower bound as a trigger (P3, in a cost-optimisation model).
- **SentinelLoop delta**: no item found applies abstention or escalation to RUL work orders. Two searches for selective prediction / reject option in prognostics (queries 3, 17, 18, 23) returned only general reject-option literature and qualitative statements that "a wide interval should steer decision-makers away from risky actions". SentinelLoop will (a) make escalation a rule with stated inputs (interval width above a validation-chosen bound; data-quality flags; active drift; anomaly and RUL disagreement), (b) report the escalation share per subset and (c) test the claim that escalations concentrate on the engines where the point model is worst. (c) is what turns "we have a human-in-the-loop flag" into evidence. `technical_inference`: judges have seen intervals; they have not seen a measured escalation policy.

### (3) Failure and sensor-stress testing of the whole pipeline

- **Closest prior**: StepanTitanyan (R9) injects 5 anomaly and 4 drift types incl. sensor freeze on FD001 and scores a detector; cymmerman (R10) injects progressive fault modes into a replay; luciforge (R3) has 19 corruption tests; fredyfanta (R2) runs FD001->FD003 as a fault-mode shift with a drift ALERT and a fallback rule; P18/P19 attack C-MAPSS RUL models (P19 explicitly calls for "resilience testing"); P20/P21 handle missing data with imputation.
- **Already done elsewhere**: injection of faults and drift (R9, R10, P22's package); measuring model RMSE under noise/missingness (P18, P20, prior-research arXiv 2603.00745 snippet); detector ROC-AUC on injected events (R9); one cross-subset shift with fallback (R2).
- **SentinelLoop delta**: none of the above closes the loop from injected input degradation to the *agent's* behaviour. SentinelLoop will inject (missing values, Gaussian noise, linear sensor drift, FD001->FD002 regime shift, FD001->FD003 fault-mode shift) into the replay and report, per injection: quality-flag and drift-alarm detection rate, false-alarm rate on clean same-subset windows (the strawman the prior research warned about), RMSE degradation, and the "silent wrong order" rate (orders issued on corrupted windows with no escalation flag). `technical_inference`: R2's fallback rule is the nearest public analogue and it reports no detection or false-alarm numbers.

### (4) Guarded retraining with a challenger promoted only through validation, regression and safety gates, shown accepting and rejecting

- **Closest prior**: Kestra blueprint (R17) has PROMOTE and HOLD verdicts on a salary dataset; MLflow ships `validate_evaluation_results` + `MetricThreshold` (R19); Ewance (R18) specifies promote-on-win plus human approval; on C-MAPSS, ohmatheus (R8) retrains on drift and hot-reloads with no gate, vaibhav07772 (R7) auto-versions with no gate, jai-krishna (R13) plans a PHM08 gate on Vertex AI, R2 retrains on ALERT with an unspecified gate.
- **Already done elsewhere**: the gate pattern itself (commonplace); drift-triggered retraining on C-MAPSS without a gate (R8).
- **SentinelLoop delta**: (a) the gate is three-part and the third part is decision-level: validation RMSE not worse, interval coverage >= a floor, and late-order rate from the replay harness not worse than the champion; (b) both outcomes are demonstrated from one command, with the reject reason logged and the `champion` alias unchanged after a reject; (c) the drift trigger's false-alarm rate on same-subset windows is reported alongside its true-positive on the regime shift. `technical_inference`: no public C-MAPSS repo found demonstrates a reject, and no gate found anywhere uses a maintenance-decision metric as a criterion (Kamariotis P6 proposes exactly that metric for model selection but releases no pipeline).

### (5) Decision-level metrics beyond RMSE

- **Closest prior**: Saxena 2009/2010 (P7) and the NASA library (P8) for prognostic horizon, alpha-lambda, relative accuracy, convergence; Sharp 2013 (P9); Kamariotis 2024 (P6) for cost per unit time; Lee & Mitici (P1) for unscheduled-maintenance rate and wasted life; aerohealth (R4) for alert precision/recall and lead time; PHM08 score critiques found only inside other papers (outlier sensitivity because of the exponential; dependence on test-set size; reliance on known end-of-life) rather than as a dedicated critique.
- **Already done elsewhere**: all of the individual metrics.
- **SentinelLoop delta**: cite P6, P7 and P1 as the sources and present the policy table as the primary result, with RMSE (capped and raw truth), PHM08 (convention printed) and coverage as secondary. Add two metrics not seen in C-MAPSS repos: decision stability (churn) and escalation share. Report a Kendall-tau style check of whether models ranked by RMSE are ranked the same by late-order rate, which is the empirical point P7 made in 2009 and no repo found makes. `unverified_assumption`: that judges will weight this; it maps directly to the rubric's "sensibly interpreted metrics" phrase, which is the strongest argument available.

### (6) Auditable actions

- **Closest prior**: vaibhav07772 (R7) JSONL per-prediction audit log and a dashboard audit tab; cymmerman (R10) SQLite audit log per prediction; R2 work orders with one-open-order-per-engine and safe reruns; XAgentMaint (P24) "logged decision trail" (LLM-based, contents undisclosed); Ewance (R18) "audit-ready retraining process"; MLflow lineage (commonplace).
- **Already done elsewhere**: logging predictions; logging model runs.
- **SentinelLoop delta**: every work order carries a fixed evidence schema: engine, subset, cycle, model name + registry alias + version, feature-manifest hash, data hash, `rul_point`, `rul_lower`, `rul_upper`, anomaly score, drift state, quality flags, rules fired (by id), policy id, severity, due-by cycle, escalate flag with reason, created-at. A determinism test regenerates a sampled order from its logged inputs and asserts an identical decision. `technical_inference`: no public item found records *which rules fired* and *which model alias* produced an order; R7's log stores the prediction and class only.

---

## 5. Why the difference matters for the official rubric

Round 2 criteria and weights as printed in the case PDF (from `specialist_cs1.json`): Working pipeline 20%, Data engineering quality 15%, Model performance 15% ("credible results with sensibly interpreted metrics"), MLOps in action 10%, Agent behavior 10%, Dataset coverage 10%, Demo & explanation 20%. Round 1 analogues: Problem understanding 15%, Architecture clarity 20%, Data engineering approach 15%, ML approach & reasoning 20%, MLOps & agent logic 15%, Dataset coverage 10%, Communication quality 5%.

| Criterion | Which differentiators serve it | Why the prior art makes this the right place to invest | Label |
|---|---|---|---|
| Working pipeline (20%) | (1) `make replay`, (4) `make retrain-demo`, (3) `make stress` | Every close repo found is either one commit (R2), roadmap-only (R13), "never applied" (R6) or results-pending (R1). A pipeline whose evidence tables regenerate from one command on a laptop is rarer than any model. | technical_inference |
| Data engineering quality (15%) | (3) injected missing values / noise / drift handled with flags; train-only fitting; schema validation | The case mandates cleaning of missing values and noise, yet C-MAPSS has none; only by injecting them can the layer be shown working. R9 and R10 inject faults but do not route them through cleaning and decisions. Pandera-style schema checks (R7) are commonplace and should be included, not claimed. | verified_fact for the case text (prior research); inference for the rest |
| Model performance (15%, "sensibly interpreted metrics") | (5) policy table + capped/raw RMSE + PHM08 convention + coverage; (2) escalation concentrating on worst engines | Public repos routinely mis-evaluate (R12 self-reported bug; prior-research 2.48-vs-14.22 trap). The phrase "sensibly interpreted" rewards exactly the P6/P7 argument that RMSE ranks models differently from decision cost. Model accuracy itself is crowded (R5 reaches 12.1 on FD001 with LightGBM). | technical_inference |
| MLOps in action (10%) | (4) gate with accept and reject; drift false-alarm rate; alias-based registry | Drift-triggered retraining without a gate exists on C-MAPSS (R8) and is the obvious failure mode a judge can probe ("does retraining ever make it worse?"). Showing a rejected challenger answers it. | verified_fact for R8; inference for judge behaviour |
| Agent behavior (10%) | (1) policy comparison, (2) escalation rule, (6) rules-fired trace | The commonplace agent is a point-RUL threshold (R4, R7, R2, P12). Comparing it against margin, lower-bound and cost-sensitive policies on the same predictions is the only way to show the agent "acts correctly and reliably" rather than "acts". | technical_inference |
| Dataset coverage (10%) | (1)(3)(4) run per subset; (3) uses FD001->FD002 and FD001->FD003 shifts as stress tests | Several repos cover all four subsets for RMSE (R3, R4, R5, R12); none reports decision metrics per subset or uses the subset structure as the drift/fault scenario with a false-alarm control. | verified_fact for coverage of those repos; inference for the gap |
| Demo & explanation (20%) | (1) one table and one plot; (5) trade-off language (coverage vs width vs discarded life); (6) click an order, see its evidence | Judges have seen RUL curves and MLflow screenshots (16-28 repos). A cycles-before-failure distribution per policy and an order whose evidence trail opens on click are explainable in under a minute and are not in any repo found. | technical_inference |
| Round 1: ML approach & reasoning (20%), MLOps & agent logic (15%) | citing P1-P3, P6, P10 as the basis and stating what is reused vs added | Openly citing Robinson, Mitici, Kamariotis and the TU Delft line shows "awareness of practical challenges" and pre-empts the "this is a reproduction" objection by naming what is reproduced. | technical_inference |

---

## 6. Experiments that can validate each difference

Each experiment states a falsifiable claim and a success criterion decided before running. If a criterion fails, the result is still reported; the harness is the deliverable.

| # | Differentiator | Experiment | Success criterion (pre-registered) | What falsifies it |
|---|---|---|---|---|
| E1 | (1) | For each subset, replay all official test engines cycle by cycle through clean -> features -> anomaly -> RUL + CQR interval -> agent. Run policies A (point threshold), B (fixed margin), C (interval lower bound), D (cost-sensitive threshold) on identical predictions; B-D thresholds chosen on validation engines only. Report late-order rate, median discarded life, mean lead time, orders per engine, severity flips per engine. | On at least 3 of 4 subsets, C has a strictly lower late-order rate than A with median discarded life no more than 1.5x that of A; D has the lowest expected cost under its own cost ratio; the table regenerates identically (same seed) from `make replay` on a clean clone in under 10 minutes per subset. | C fails to reduce late orders, or does so only by discarding more than 1.5x the life; or results are not reproducible. |
| E2 | (2) | Escalation rule: escalate when interval width > w* (w* chosen on validation engines to cap escalation share at 20%), or quality flags set, or drift active, or anomaly high while `rul_point` is high. Replay as in E1. Compare point-model absolute error and late-order rate for escalated vs non-escalated engines. | Per subset: median absolute error of escalated engines > that of non-escalated engines (one-sided Mann-Whitney, p < 0.05); late-order rate among non-escalated engines <= overall late-order rate of policy C; escalation share <= 20% on FD001/FD003 and <= 35% on FD002/FD004. | Escalations are statistically indistinguishable from random with respect to error, or escalation share needed to achieve the error separation exceeds the cap (the rule is then "escalate everything"). |
| E3 | (3) | Stress suite on the replay: (a) missing values at 1%, 5%, 20% of cells; (b) Gaussian noise at 0.1, 0.5, 1.0 x per-sensor training std; (c) linear drift on 3 sensors reaching 2 std by end of life; (d) FD001 champion fed FD002 windows; (e) FD001 champion fed FD003 windows; (f) control: clean FD001 windows. Measure quality-flag rate, drift-alarm rate, RMSE, and silent-wrong-order rate (CRITICAL/HIGH orders on corrupted windows without an escalation flag). | Drift or quality detection fires on (c), (d), (e) within 50 cycles of onset; false-alarm rate on (f) <= 5% of windows; silent-wrong-order rate under (a)-(e) <= the clean late-order rate of policy C; RMSE degradation under (b) at 0.5 std <= 25% relative. | The monitor misses (d) or (e), or fires on more than 5% of clean windows, or corrupted inputs produce confident wrong orders at a higher rate than clean inputs produce late orders. |
| E4 | (4) | Two scripted scenarios from `make retrain-demo`: ACCEPT: drift alarm on FD002 windows triggers retraining on FD001+FD002 engines; challenger passes (val RMSE <= champion, coverage >= 0.85, replay late-order rate <= champion) and receives the `champion` alias. REJECT: retraining on a deliberately degraded set (10% of engines, or labels shuffled within engine) produces a challenger that fails at least one gate; alias unchanged; reason logged. Also report drift-trigger false alarms on same-subset windows (E3-f). | Both outcomes reproduce deterministically; MLflow registry shows a new version in both cases but the alias moves only in ACCEPT; the reject log names the failed gate and the metric values; retrain + gate completes in under 3 minutes on CPU. | The degraded challenger passes all gates (gate too weak), or the legitimate challenger fails (gate too strict), or outcomes differ between runs. |
| E5 | (5) | Rank the models logged in MLflow (HGBR champion, RF, optional LightGBM/1D-CNN challenger) by official-test RMSE and separately by policy-C late-order rate and by cost under policy D, per subset. Compute Kendall tau between the rankings. | A tau < 1 on at least one subset (rankings differ), which replicates P7's 2009 finding on this data; if tau = 1 everywhere, report that RMSE was a sufficient proxy here. Either way the capped-vs-raw RMSE gap (prior research: ~12 points on FD002/FD004) is printed. | Nothing falsifies the reporting; the claim "decision metrics add information" is falsified if tau = 1 on all subsets and all policies. |
| E6 | (6) | Sample 50 work orders per subset from the SQLite store; for each, reload the model version and feature manifest named in the order, recompute from the logged inputs, and compare the decision. Pytest suite asserts schema completeness and determinism; dashboard opens an order's evidence trail. | 100% of sampled orders reproduce the same severity, due-by cycle and escalate flag; every order has all schema fields non-null; one open order per engine at any time (de-duplication test). | Any order fails to reproduce, or any order lacks a model alias / rules-fired list. |

`technical_inference`: E1-E4 are CPU-only, run on predictions the pipeline already produces, and fit the prior research's 10-11 person-day estimate if the agent and replay are written as pure functions with tests first.

---

## 7. Remaining uncertainty about novelty

Stated plainly so the deck never overclaims.

1. **Search breadth** (`verified_fact` about the method): 30 web queries, 7 GitHub API queries, 17 repo READMEs, 28 paper pages, in English only. Chinese-language venues surfaced (e.g. a 2024 article in 工程科学学报 and several HIT/NWPU records) and were not read. Non-English theses and Indian hackathon write-ups are likely under-indexed.
2. **GitHub coverage** (`verified_fact`): the API returned 16 + 28 + 13 + 5 repos for the four main queries; 7 of the 28 `turbofan mlflow` results were not rendered; the `cmapss` topic page has 53 repos of which the prior research saw 20. Untagged repos with names that mention neither "cmapss" nor "turbofan" (e.g. "jet-engine", "aero", "PdM") were not searched. R1 (IntelliTwin) was found only through the conformal query; similar projects may exist under other words.
3. **IntelliTwin may publish first** (`unverified_assumption`): R1 is active (pushed 2026-10-17), has a replay simulator, conformal calibration, cost scenarios and policy controls, and its held-out results are pending. If its results appear before the TELIPORT deadline, SentinelLoop's (1)+(2)+(5) story becomes "an open operational implementation of an idea that a concurrent research repo is also testing". That is survivable (SentinelLoop adds the agent, gates, stress tests and audit trail) but must be cited.
4. **Paywalled full texts** (`verified_fact`): P1, P2, P3, P5, P6, P21 were verified from abstracts only. Whether P1/P2 use C-MAPSS, and whether P2 already defines a churn metric, is unknown. The de Pater 2022 PDF on the TU Delft portal returned HTTP 403.
5. **Blocked or unparsed pages** (`verified_fact`): the HAL record for P5 and an MDPI Processes 2022 paper on prediction-interval-based "credibility criteria" for prognostics (candidate prior art for (2)) could not be fetched; the latter is known only from a search snippet.
6. **Repo claims vs code** (`verified_fact` about the method): READMEs were read, code was not. R2's drift method, R12's decision rules and R1's policy definitions are undocumented in their READMEs and could be closer to SentinelLoop than this document records. Self-reported numbers (R9's ROC-AUC, R2's savings) were not reproduced.
7. **Kaggle** (`unverified_assumption`): no policy-simulation notebook was found, but Kaggle notebooks are poorly indexed by web search; a direct Kaggle-site search by the team is advisable.
8. **TELIPORT entrants** (`unverified_assumption`): nothing is known about other Season 4 teams; the prior research found no official Season 4 page. The commonplace table in Section 3 is a proxy built from public repos pushed in 2025-2026, which is a reasonable but unproven model of what entrants will submit.
9. **Vendor material** (`verified_fact`): the Azure aircraft-engine solution-idea URL no longer serves that content and AWS Lookout for Equipment was discontinued on 2026-10-07, so vendor reference designs offer little live prior art; `technical_inference` that judges from an engineering-services firm may still expect the "data -> features -> model -> agent -> work order" shape of the retired Azure accelerator.
10. **Scientific novelty**: none of (1)-(6) is new to the prognostics literature. P1-P7 cover policy evaluation, lower-bound triggers, alarm stability and decision metrics in peer-reviewed form between 2009 and 2024. SentinelLoop's claim is limited to: an open, reproducible, four-subset, non-LLM implementation that evaluates its own agent as a policy, escalates measurably, survives injected faults measurably, rejects bad challengers visibly, and makes every order traceable. That claim is checkable by a judge in one command, which is the only kind of claim this search supports.

---

## 8. Sources

All URLs were fetched on 2026-10-18 unless marked "prior research" (fetched in the earlier session recorded in `competitor_cs1.json` / `specialist_cs1.json`) or "snippet only".

### Papers and theses
- Lee & Mitici 2023, RESS 230: https://research.tudelft.nl/en/publications/deep-reinforcement-learning-for-predictive-aircraft-maintenance-u and https://ideas.repec.org/a/eee/reensy/v230y2023ics0951832022005233.html
- de Pater, Reijns & Mitici 2022, RESS 221: https://ideas.repec.org/a/eee/reensy/v221y2022ics0951832022000175.html (TU Delft PDF https://research.tudelft.nl/files/111473542/1_s2.0_S0951832022000175_main.pdf returned 403)
- Mitici, de Pater, Barros & Zeng 2023, RESS 234 (prior research): https://research.tudelft.nl/en/publications/dynamic-predictive-maintenance-for-multiple-components-using-data/
- Mitici et al., ESREL 2023: https://rpsonline.com.sg/proceedings/esrel2023/html/P064.html
- Nguyen & Medjaher 2019, RESS 188: https://doi.org/10.1016/j.ress.2019.03.018 (abstract via https://api.semanticscholar.org/graph/v1/paper/DOI:10.1016/j.ress.2019.03.018 ; HAL page https://hal.archives-ouvertes.fr/hal-02134750 blocked)
- Kamariotis et al. 2024, RESS 242: https://arxiv.org/abs/2306.03759
- Saxena et al. 2009, IEEE Aerospace: https://c3.ndc.nasa.gov/dashlink/static/media/publication/2009_IEEEAerospace_MetricsEvaluation.pdf
- Saxena et al. 2010, IJPHM "Metrics for offline evaluation": https://c3.ndc.nasa.gov/dashlink/resources/279
- NASA PrognosticsMetricsLibrary: https://github.com/nasa/prognosticsmetricslibrary
- Sharp 2013, PHM Conf: https://papers.phmsociety.org/index.php/phmconf/article/view/2317
- Robinson 2026, IJPHM 17(1) (prior research): https://www.papers.phmsociety.org/index.php/ijphm/article/view/4724
- Javanmardi & Hullermeier 2023 (prior research): https://arxiv.org/abs/2212.14612 ; https://github.com/alireza-javanmardi/conformal-RUL-intervals
- Ozcan 2025, Scientific Reports: https://pmc.ncbi.nlm.nih.gov/articles/PMC12615660/
- Gevrek 2025, METU thesis: https://ii.metu.edu.tr/node/1479
- Choo & Shin 2025, IJPHM 16(1): https://www.papers.phmsociety.org/index.php/ijphm/article/view/4242
- Khorasgani et al. 2021: https://arxiv.org/abs/2109.15050
- Basora et al. 2023: https://arxiv.org/abs/2302.04730
- Pugnana, Mougan & Nielsen 2023: https://arxiv.org/abs/2311.09145
- Mode, Calyam & Hoque 2019/2020: https://arxiv.org/abs/1910.01716v4
- Zhou, Canady, Li & Gokhale 2020, PHM Conf: https://papers.phmsociety.org/index.php/phmconf/article/view/1182 (PDF read: https://papers.phmsociety.org/index.php/phmconf/article/download/1182/876)
- Chen et al. 2021, Complexity: https://ideas.repec.org/a/hin/complx/2122655.html
- Wang et al. 2025, RESS 262: https://pure.nwpu.edu.cn/en/publications/robust-uncertainty-quantification-for-online-remaining-useful-lif/
- Adams et al. 2025, PHM Conf: https://papers.phmsociety.org/index.php/phmconf/article/view/4415
- Sharma 2025: https://arxiv.org/abs/2511.19124
- Patel & Adisha 2026, ASI Conf (XAgentMaint): https://digitalcommons.kennesaw.edu/asi/2026/proceedings/13
- Ziyad et al. 2022: https://arxiv.org/abs/2209.02678
- Baranowski & Bauer 2026: https://arxiv.org/abs/2605.30222
- Kim & Jang 2026: https://arxiv.org/abs/2608.13209
- Chowdhury et al. 2026 (Bi-cLSTM; abstract only, no noise numbers on page): https://arxiv.org/abs/2603.00745
- Hsu, Frusque & Fink 2023 (prior research): https://papers.phmsociety.org/index.php/phmconf/article/view/3444
- Sanchez et al. 2026 (prior research): https://arxiv.org/abs/2601.10269v1
- Leakage-robust evaluation 2026 (prior research): https://arxiv.org/abs/2607.16493
- Zhang, Prakash & Tang 2026 (compressor RUL; lower-bound rule not on abstract page): https://arxiv.org/abs/2607.24809
- Alghtus et al. 2025 (pump fault diagnosis; not C-MAPSS): https://arxiv.org/abs/2508.15550
- MDPI Processes 10(3):473, prediction-interval credibility criteria (snippet only; fetch returned 403): https://www.mdpi.com/2227-9717/10/3/473/html
- Saxena et al. 2008 PHM08 damage-propagation paper (prior research): https://c3.ndc.nasa.gov/dashlink/static/media/publication/2008_IEEEPHM_CMAPPSDamagePropagation.pdf

### Repositories
- https://github.com/sik04/AI-Driven-Digital-Twin-Predictive-Maintainence (and raw README at https://raw.githubusercontent.com/sik04/AI-Driven-Digital-Twin-Predictive-Maintainence/main/README.md)
- https://github.com/fredyfanta3443-ops/predict-maintenance (and https://raw.githubusercontent.com/fredyfanta3443-ops/predict-maintenance/main/MODEL_CARD.md)
- https://github.com/luciforge/Engine-RUL-ML
- https://github.com/Mohith26/aerohealth
- https://github.com/mateus-aleixo/turbofan-rul and https://github.com/mateus-aleixo/maintenance-qa-agent
- https://github.com/nithya-prakash/PredictiveMaintenanceAI
- https://github.com/vaibhav07772/turbofan-rul-mlops
- https://github.com/ohmatheus/Turbofan-ML-lifecycle
- https://github.com/StepanTitanyan/C-MAPSS_Drift-Anomaly_Distinction
- https://github.com/cymmerman/ml-pipeline-deployment
- https://github.com/jon-gomezz/nasa-predictive-maintenance
- https://github.com/Shiverion/AeroRUL
- https://github.com/RudraTrivedi14/turbofan-prognostics-mlops
- https://github.com/jai-krishna-0921/predictive-maintenance-mlops
- https://github.com/RaviSingh48/Predictive-Maintenance-ML
- https://github.com/Isuruigi/ml-monitoring-system
- https://github.com/Chaitanyarai899/Maintenance-Prediction-Via-MLOps
- https://github.com/awslabs/predictive-maintenance-using-machine-learning
- Description-only (unverified): https://github.com/HariniSuresh6/turbofan-rul-data-pipeline ; https://github.com/Rifatsarkar3/Mamba ; https://github.com/DK-Krishna2001/DriftGuard-NASA-CMAPSS-Turbofan-Drift-Monitor ; https://github.com/AmmarHafeez/industrial-maintenance-mlops ; https://github.com/aezzahir/Engine_Remaining_Useful_Life-prediction-nasa-cmapss ; https://github.com/ajazhussainsiddiqui/cmapss-rul-mlops ; https://github.com/fiza-pathan/predictive-maintenance-mlops ; https://github.com/Atharvadahitule/TURBOFAN-PREDICTIVE-MAINTENANCE ; https://github.com/hamza100x/rul-predictor ; https://github.com/CCao666/predictive-maintenance-mlops ; https://github.com/Krishna4396/mlops-predictive-maintenance ; https://github.com/ToprakKS/AeroGuard-Industrial-MLOps ; https://github.com/Parnavip18/turbofan-rul-prediction ; https://github.com/DoctorNDJonathan/turbofan-rul-anomaly ; https://github.com/Say43/TurbofanRUL-NCMAPSS ; https://github.com/myler71/Turbomind-AI ; https://github.com/Sodz99/Remaining-Useful-Life-Estimation-of-Turbofan-Engines-with-Domain-Adaptive-Deep-Learning
- Prior research: https://github.com/topics/cmapss ; https://github.com/adityapotdar23/Predictive-Maintenance ; https://turboguard.readthedocs.io/en/latest/ ; https://github.com/IEEE-IES-Industrial-AI-Lab/Industrial-Predictive-Maintenance ; https://github.com/kpeters/exploring-nasas-turbofan-dataset ; https://github.com/aun151214/predictive-maintenance-cmapss

### GitHub API queries
- https://api.github.com/search/repositories?q=cmapss+mlflow&sort=updated&per_page=20
- https://api.github.com/search/repositories?q=turbofan+mlflow&sort=updated&per_page=20
- https://api.github.com/search/repositories?q=turbofan+evidently+OR+cmapss+evidently+OR+cmapss+drift+OR+turbofan+drift&sort=updated&per_page=20
- https://api.github.com/search/repositories?q=turbofan+conformal+OR+cmapss+conformal+OR+rul+conformal&sort=updated&per_page=20
- https://api.github.com/search/repositories?q=cmapss+%22work+order%22+OR+turbofan+%22work+order%22+OR+cmapss+triage+OR+turbofan+%22maintenance+policy%22&sort=updated&per_page=20
- https://api.github.com/search/repositories?q=cmapss+retrain+OR+turbofan+retraining+OR+turbofan+%22champion%22+OR+cmapss+%22challenger%22&sort=updated&per_page=20
- https://api.github.com/search/repositories?q=turbofan+%22fault+injection%22+OR+cmapss+robustness+OR+cmapss+%22noise+injection%22+OR+turbofan+%22audit%22+OR+cmapss+%22safety+margin%22+OR+cmapss+%22cost-sensitive%22&sort=updated&per_page=20

### Tooling, tutorials and vendor material
- MLflow model evaluation / validation: https://mlflow.org/docs/latest/ml/evaluation/ (API source for `MetricThreshold`: https://mlflow.org/docs/latest/api_reference/_modules/mlflow/models/evaluation/validation.html)
- MLflow registry aliases (prior research): https://mlflow.org/docs/latest/ml/model-registry/workflow/
- Evidently drift defaults (prior research): https://docs.evidentlyai.com/metrics/explainer_drift
- Kestra blueprint: https://kestra.io/blueprints/evidently-drift-champion-challenger-retrain
- Ewance challenge brief: https://ewance.com/en/challenges/automate-retraining-with-a-drift-triggered-mlflow-pipeline-mlops-and-ml-engineering-master/
- Azure IoT Predictive Maintenance accelerator (archived): https://learn.microsoft.com/en-us/previous-versions/azure/iot-accelerators/iot-accelerators-predictive-walkthrough
- Azure solution-idea URL (now serves the Manufacturing hub): https://learn.microsoft.com/en-us/azure/architecture/solution-ideas/articles/aircraft-engine-monitoring-for-predictive-maintenance-in-aerospace
- Amazon Lookout for Equipment: https://aws.amazon.com/lookout-for-equipment/
- AWS "Introducing Predictive Maintenance Using Machine Learning" (snippet only): https://aws.amazon.com/about-aws/whats-new/2019/07/introducing-predictive-maintenance-using-machine-learning
- Kaggle mirror (snippet only): https://www.kaggle.com/datasets/behrad3d/nasa-cmaps
- NASA PCoE repository and data.nasa.gov (prior research): https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/ ; https://data.nasa.gov/dataset/cmapss-jet-engine-simulated-data

## References named on the Round 1 slide and in the deck (added after the Phase 6 review)
- Y. Romano, E. Patterson, E. Candès, "Conformalized Quantile Regression", NeurIPS 2019 — the CQR method used for the 90% RUL intervals (verified as real and correctly attributed by the Phase 6 prior-art reviewer).
- Robinson, "Conformal prediction for remaining useful life", International Journal of Prognostics and Health Management 17(1), 2026 — CQR applied to C-MAPSS; the asymmetric variant; our pipeline's default is the symmetric CQR, with an asymmetric option (E7 ablation). Cited as design precedent, not claimed.
- A. Saxena, K. Goebel, D. Simon, N. Eklund, "Damage Propagation Modeling for Aircraft Engine Run-to-Failure Simulation", PHM08 — the C-MAPSS dataset and the PHM08 score (a1 = 13 early, a2 = 10 late).
- M. Mitici et al. (2023) and Lee & Mitici (2023), Reliability Engineering & System Safety — decision-level evaluation of RUL prognostics (lower-bound triggers, late-order and discarded-life style metrics); our E1 metrics follow this line of work.
- A. Kamariotis et al. (2024) — argues for decision-oriented metrics over RMSE for prognostics; our E5 is in this spirit.
- IntelliTwin (sik04, MIT licence, GitHub, 2026) — the closest open-source system found: policy replay of a maintenance agent on C-MAPSS (no stored results). Cited wherever the replay harness is presented.
Wording rule after the review: the strongest novelty wording used anywhere is "not found in our search (30 web queries, 7 GitHub API queries, 17 READMEs, 28 paper pages, 2026-10-17/18)"; nothing is called first, unique or state of the art.
