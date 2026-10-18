# Phase 0 — Requirements Matrix (extracted from the five TELIPORT Season 4 case-study PDFs)

Source files (all located and read in full, 21 pages total, including rendered tables):

| # | File | Pages | Rubric structure found in PDF |
|---|---|---|---|
| 1 | Case Study 1_ACTG_Predictive_Maintenance.pdf | 4 | Two rounds, each with 7 weighted criteria (weights sum to 100%) |
| 2 | Case Study 2_IDV_Battery_Energy_System.pdf | 3 | Single table, 7 weighted criteria (sum to 100%); no rounds |
| 3 | Case Study 3_MCV_Adaptive QoS Engine for Mixed Home Broadband Traffic.pdf | 3 | 5 criteria, **no weights** |
| 4 | Case Study 4_HLS_End-to-End Medical Device Labeling Automation Management.pdf | 8 | 7 criteria, **no weights** |
| 5 | Case Study 5_TBU_Vehicle Information using On-Device SLM or LLM.pdf | 3 | 7 criteria (some with sub-bullets), **no weights** |

Labels used below: **[SDR]** source-derived requirement (quoted or paraphrased from the PDF); **[AMB]** ambiguity or interpretation risk; **[INF]** technical inference (ours, not in PDF).

---

## Case Study 1 — Self-Healing Machines: Predictive Maintenance for a Connected Fleet

**Problem statement [SDR]:** Build a closed-loop system that ingests streaming/batch sensor data from a connected fleet, detects early degradation, predicts Remaining Useful Life (RUL), and automatically raises a maintenance work order, with a human stepping in only for exceptions.

**Intended users [SDR, implicit]:** fleet maintenance operations (trucks, buses, industrial compressors); reviewers expect the design "explained in a review".

**Required features / components [SDR]:**
- Data Engineering: read sensor data (batch or streaming), handle missing values and basic noise, build rolling-window features (averages, trends).
- Machine Learning: detect abnormal behaviour AND predict RUL (cycles left before failure).
- MLOps: experiment + model-version tracking, simple retraining flow on new data, basic monitoring view.
- Agents (non-LLM): rule-based Triage Agent that reads model output, decides severity, auto-creates a maintenance work order.

**Mandatory constraints / prohibited approaches [SDR]:**
- Handle mild class imbalance (failures rarer than normal readings).
- Pipeline runs end-to-end without manual steps once data is provided.
- Lightweight; **no LLM**; agent uses simple rules/thresholds.
- Open-source tools; design documented for review.
- Dataset is prescribed: NASA C-MAPSS (21 sensors + 3 operating settings, FD001–FD004). One subset is acceptable (FD001 suggested as a start); all four for a more challenging solution.

**Deliverables [SDR]:**
- Round 1 (Idea Submission) – Design deck: architecture diagram (data → features → model → agent → work order); data cleaning/feature approach; choice of anomaly-detection and RUL models with reasoning; Triage Agent logic.
- Round 2 (Detailed Submission) – Proof of Concept: working pipeline on chosen subset(s); trained model with RUL predictions; simple monitoring dashboard; agent auto-generating a work order + a demo retraining run.

**Evaluation criteria and exact weights [SDR]:**
- Round 1: Problem understanding 15 · Architecture clarity 20 · Data engineering approach 15 · ML approach & reasoning 20 · MLOps & agent logic 15 · Dataset coverage 10 · Communication quality 5.
- Round 2: Working pipeline 20 · Data engineering quality 15 · Model performance 15 · MLOps in action 10 · Agent behavior 10 · Dataset coverage 10 · Demo & explanation 20.

**Expected demonstration evidence [SDR]:** end-to-end run with minimal manual intervention; credible, sensibly interpreted metrics; functional MLOps elements; agent acting correctly and reliably on model output; depth/breadth of subsets tackled; convincing articulation of trade-offs.

**Data / compute / hardware / safety / compliance / integration [SDR + INF]:** public dataset, CPU-only feasible [INF]; no hardware; no compliance regime; suggested tools (optional): Python/Pandas/NumPy, scikit-learn (optionally TF/PyTorch), MLflow, Streamlit/Dash, plain Python agent.

**Ambiguities / interpretation risks [AMB]:**
- "Detect abnormal behavior" is separate from RUL: an anomaly-detection component is expected in addition to RUL regression.
- "Dataset coverage" (10% in both rounds) rewards tackling more than FD001; the scoring of "varying complexity" is qualitative.
- "Streaming" is optional ("batch or streaming") but a replayed stream is the natural way to show the closed loop and retraining trigger.
- "Model performance … sensibly interpreted metrics" implies judges will check the metric choice (RMSE vs NASA asymmetric score, RUL capping) rather than only the number.

---

## Case Study 2 — Reusable Digital Platform for Designing Battery Energy System

**Problem statement [SDR]:** Create an innovative digital platform that helps students and engineers virtually design, test, compare and improve battery energy system configurations, making cross-discipline interactions and trade-offs understandable while supporting safe, efficient, reliable, affordable systems.

**Intended users [SDR]:** students and engineers designing battery energy systems.

**Required features / components [SDR, "Solution Goal" + "Key Points"]:**
- Configure, visualize, analyze and compare designs from cell to system level.
- Integrate electrical, thermal, mechanical, sensing, protection, control and energy-management considerations in one workflow.
- Consistent parameter/result exchange between subsystem models so design changes propagate to system-level impacts.
- Identify interface conflicts, incompatible assumptions, safety-limit violations and performance trade-offs.
- Traceability between requirements, component selections, assumptions, models, results and validation evidence; recommend a balanced design with stated risks/limitations.
- Select a manageable scope (small cell group, module, cooling arrangement or monitoring function); define application, requirements, operating conditions.
- Use datasheets, simple calculations, simulations or safe low-voltage experiments.
- **Compare at least two design options against a basic starting design.**
- Measure a few indicators: usable energy, temperature, charging time, mass, size or estimated cost.
- Document assumptions, data sources, safety precautions, results, limitations.
- Present a simple prototype or visual demonstration; explain recommended next step.

**Mandatory constraints / prohibited approaches [SDR]:** scope must remain manageable (full pack is too large); safety emphasised ("safe low-voltage experiments", "safety-limit violations"). No prohibited tools stated.

**Deliverables [SDR]:** no round structure given; "simple prototype or visual demonstration" plus documentation.

**Evaluation criteria and exact weights [SDR]:** Problem understanding 15 · Desirability 15 · Technical feasibility 20 · Engineering quality 15 · Prototype & evidence 15 · Innovation 10 · Business viability 10.

**Expected demonstration evidence [SDR]:** "Working demonstration or model with measurable and repeatable results"; "sound calculations, assumptions and understanding of system interactions".

**Data / compute / hardware / safety / compliance / integration [SDR + INF]:** no dataset given; relies on datasheets/public data and simulation [INF]; no hardware required but "safe low-voltage experiments" are allowed; no compliance regime beyond safety limits.

**Ambiguities / interpretation risks [AMB]:**
- "Reusable digital platform" vs "manageable scope": the platform ambition (multi-physics, traceability) is large, while the key points allow a narrow scope. Judges may weight either.
- "Engineering quality" and "Technical feasibility" (35% combined) are judged by domain experts; a software team must defend battery physics it did not originate.
- "Desirability" and "Business viability" (25%) are non-technical and presentation-driven.
- No benchmark or ground truth is specified, so "measurable and repeatable results" will be simulation results whose credibility depends on model fidelity and validation against published data.

---

## Case Study 3 — Adaptive QoS Engine for Mixed Home Broadband Traffic

**Problem statement [SDR]:** Create an intent-aware QoS controller that classifies broad traffic categories without reading private payloads, estimates link capacity, applies queueing and shaping policies, verifies whether the policy improved user experience, and supports a temporary user intent (e.g. prioritise a work call) while retaining fairness.

**Intended users [SDR]:** residential households (video conferencing, gaming, voice, adaptive video, downloads, updates, backups); the student deliverable is a "technically credible reference implementation", not a commercial product.

**Required features / components [SDR, "Expected Output and Acceptance Evidence"]:**
- Traffic-class and link-capacity estimator.
- Dynamic QoS policy engine and enforcement module.
- Dashboard: latency, jitter, loss, throughput, queue depth, fairness.
- Automated baseline-versus-optimized experiments.
- API or UI for temporary service intent.
- Architecture diagram (device, edge, network, data, analytics, UI).
- Setup guide with prerequisites, exact versions, commands, configuration, verification steps.
- Automated/scripted demonstration that resets the environment, introduces the condition, collects evidence, generates a result report.
- Known-limitations section (real hardware, certification, scale testing, proprietary integration).
- Decomposition into independently testable modules with inputs, outputs, state transitions, failure handling, success conditions.
- Where AI is used: compare with a deterministic baseline and show measurable improvement.

**Mandatory constraints / prohibited approaches [SDR]:**
- Do not decrypt application traffic.
- Use Linux traffic control or another open, inspectable enforcement mechanism.
- Support IPv4 and, where available, IPv6.
- Policy rollback; prevent starvation of low-priority traffic.
- Classifiers must expose confidence and allow correction of misclassification.
- Document third-party licences; no redistribution contrary to licence.
- Generated data and impairment settings must be included for reproducibility.
- Emulated hardware capabilities must be labelled as emulation with model and limitations.
- No credentials/keys in source control; example secrets clearly fictitious.
- Automated remediation bounded, observable, reversible; failure returns to a known safe state.

**Deliverables [SDR]:** no round structure; the acceptance-evidence list above.

**Evaluation criteria [SDR, no weights]:** Accuracy of classification and link estimation · Reduction in interactive latency, jitter and packet loss · Fairness and absence of starvation · Adaptation speed and policy stability · CPU overhead, reproducibility and clarity of results.

**Expected demonstration evidence [SDR]:** scripted, reproducible baseline-vs-optimized experiments with the three illustrative scenarios (ISO download during a call; WAN drop 100→20 Mbps; three TVs + gaming device) or added generic scenarios.

**Data / compute / hardware / safety / compliance / integration [SDR + INF]:** no dataset given; traffic must be generated or ethically collected and included; Linux kernel features (tc/netem/namespaces) required [INF]; no physical router required because emulation is permitted if labelled.

**Ambiguities / interpretation risks [AMB]:**
- Unweighted criteria: all five are measurable, which favours teams that produce numbers, but relative importance is unknown.
- "Accuracy of classification" needs labelled ground truth; with generated traffic the labels are known by construction, which judges may view as easy or as fair depending on realism.
- "Adaptation speed and policy stability" implies time-series evidence of controller behaviour, not just before/after averages.
- Windows-based teams must run Linux (VM/WSL2) and tc/netem; environment fragility is a demo risk.

---

## Case Study 4 — End-to-End Labeling Automation Management for Medical Devices

**Problem statement [SDR]:** Design innovative, scalable, compliant solutions that transform the end-to-end medical device labeling lifecycle using AI/ML, GenAI, RPA, computer vision, smart workflows and cloud, to accelerate regulatory compliance, reduce human effort and cycle time, minimise errors and enhance patient safety.

**Intended users [SDR]:** Regulatory Affairs, Product Owners, Labeling Engineers, Quality Assurance, Manufacturing, Supply Chain, Clinical Teams, IT & Digital Transformation Teams; regulators EU MDR, US FDA, global submissions.

**Required features / components [SDR]:** the PDF lists ten "Potential Approaches" (GenAI authoring, AI compliance checker, change-impact engine, CV artwork validation, regulatory-intelligence bot, translation validation, prompt-to-label, predictive quality analytics, AR verification, agentic ecosystem) as options, and ten problem areas that "Proposed Solutions should explicitly address" (manual process time, regulatory updates, symbol management, multiple sources of truth, expertise dependency, manual redlining, repetitive review, traceability, variant explosion, human error). The traditional 18-step business process from Product/Design Information to Production Implementation is "in scope".

**Mandatory constraints / prohibited approaches [SDR]:** none stated explicitly. "Expectation: New Approach using AI with artifacts or supported data."

**Deliverables [SDR]:** no round structure; "Recommended Steps" are: process map; root-cause/FMEA/value-stream analysis → Automation Opportunity Matrix; technology applicability; design & development of labels using AI; system architecture and automation workflow; measure time reduction, error reduction, compliance improvement, cost savings.

**Evaluation criteria [SDR, no weights]:** Understanding of labeling problem · Regulatory/compliance awareness · Innovation ideas considering Label Design using AI · AI/automation platform · End-to-end process coverage · Accuracy & validation approach · Traceability & auditability.

**Expected demonstration evidence [SDR + AMB]:** not explicitly defined; "artifacts or supported data" and "measure and evaluate" imply a demonstrable system with measured gains, but a design-level submission is not excluded by the text.

**Data / compute / hardware / safety / compliance / integration [SDR + INF]:** references are FDA labeling requirements, EU MDR 2017/745, ISO 20417:2026 and ISO 15223-1 (ISO texts are paid), IMDRF N52, EC UDI page, FDA UDI guidance. No dataset or sample labels are supplied; realistic artefacts must be sourced or synthesised [INF]. Integration with PLM/ERP/SAP is described as the real-world context but not mandated.

**Ambiguities / interpretation risks [AMB]:**
- The broadest and least specified brief of the five: "end-to-end process coverage" rewards breadth, while "accuracy & validation approach" rewards depth; both cannot be maximised in a hackathon.
- No weights, no prototype mandate and no dataset make the scoring more subjective and presentation-sensitive than Cases 1–3.
- Regulatory correctness is judged by domain experts; any hallucinated rule or symbol is a visible failure.
- Paid standards (ISO 15223-1 symbol library, ISO 20417) cannot be redistributed; the demo must rely on freely accessible sources.

---

## Case Study 5 — Natural Language Vehicle Information using On-Device SLM/LLM (VehicleGPT)

**Problem statement [SDR]:** Design a practical AI-on-Edge solution that runs an SLM/LLM inside the vehicle, continuously consumes vehicle data streams, events and logs, and makes them searchable via natural-language queries; it must understand questions, retrieve information, identify trends and anomalies and present explanations without cloud connectivity.

**Intended users [SDR]:** drivers, service engineers, fleet operators, validation teams.

**Required features / components [SDR, "Key points" + "Expected Output"]:**
- Recreation of driving scenarios and error-condition sequences (CARLA or other simulation, or simulated/recorded data).
- Vehicle data collection and storage from CAN/CAN-FD, SOME/IP services, Android Vehicle HAL, QNX services/logs, ADAS, camera feeds, diagnostic logs; retention of real-time and historical data.
- Expected output: high-level system architecture (hardware + software) with engineering justification; data-collection strategy; SLM/LLM selection rationale; search and retrieval workflow; historical data storage approach; edge deployment architecture; user interaction design; reasoning for AI model, OS, architecture and communication protocols.

**Mandatory constraints / prohibited approaches [SDR]:**
- No cloud dependency.
- Model must run on embedded hardware with limited resources (~2 GB RAM, ~2 ARM A5X cores); demonstration permitted on automotive ARM boards, Raspberry Pi 4/5 with AI HAT, ARM virtual environments (cuttlefish, QEMU), AWS Graviton or equivalent.
- Response time under 2 seconds for common queries.
- Historical data searchable for at least several weeks.
- Safety-critical vehicle functions isolated from the AI system.

**Deliverables [SDR]:** no round structure; the "Expected Output" list is architecture-centric; a demonstration is implied by the hardware list and by the Edge Performance criteria.

**Evaluation criteria [SDR, no weights]:** System Architecture (completeness of HW/SW, logical integration of simulation and user interface) · AI Capability (understanding NL queries; accuracy of responses and summaries) · Data Integration (support for multiple automotive protocols and data sources) · Search & Analytics (find historical events, trends, anomalies; explain causes) · Edge Performance (memory footprint; query latency; scalability from reference board/Raspberry Pi/VM to vehicle HPC) · Privacy & Security (local-only processing; protection of vehicle and driver data) · Innovation & Practicality (ease of deployment in production SDVs; value for the four user groups).

**Expected demonstration evidence [SDR + INF]:** example queries in the PDF (range reduction over two weeks, largest efficiency drop, ADAS disengagements yesterday, events before a battery-overheating warning, city vs highway consumption) define the acceptance behaviour; memory footprint and latency must be measured on constrained hardware or an equivalent emulation [INF].

**Data / compute / hardware / safety / compliance / integration [SDR + INF]:** no dataset given; CARLA is suggested (GPU-heavy [INF]); access to ARM hardware is not guaranteed but VM/QEMU/Graviton alternatives are explicitly permitted; multiple automotive protocols are listed, of which only some can be exercised without vehicle hardware [INF].

**Ambiguities / interpretation risks [AMB]:**
- "~2 ARM A5X cores" is an unusual designation (likely Cortex-A5x class); interpret as a modest 64-bit ARM core pair.
- "Accuracy of responses" has no defined test set; the team must build its own labelled query set, which judges may or may not trust.
- "Support for multiple automotive protocols" could be read as adapters that exist in code versus protocols demonstrated live; honesty about emulation is essential.
- The expected output is design-heavy; it is unclear how much weight a working prototype carries versus a strong architecture document.

---

## Requirements-to-Evidence Matrix (what we must SHOW to earn strong marks)

| Case | Criterion (weight) | Evidence that earns strong marks | Evidence that is hard to produce for a student team |
|---|---|---|---|
| 1 | Working pipeline (20) | One command/`make` runs ingest → features → model → agent → work order on FD001+ with logs | — |
| 1 | Data engineering quality (15) | Unit-wise splits, documented cleaning, feature tests, reproducible seeds | — |
| 1 | Model performance (15) | RMSE and NASA score on the official test files with the official RUL_FD00x.txt labels; baseline vs improved table; capped-RUL rationale | Beating published state-of-the-art (not required; "credible" is the word used) |
| 1 | MLOps in action (10) | MLflow runs, registered versions, retraining triggered by new data, drift/monitoring view | — |
| 1 | Agent behavior (10) | Deterministic rules with test cases; work-order artefacts; severity escalation; exception path to human | — |
| 1 | Dataset coverage (10) | Results on FD001–FD004 with per-subset handling of operating regimes | Handling FD002/FD004 regimes well |
| 1 | Demo & explanation (20) | Live replay of a degrading engine, work order appears, retraining run, trade-off discussion | — |
| 2 | Technical feasibility (20) + Engineering quality (15) | Validated cell model (ECM/thermal) against published datasheet/dataset curves; stated assumptions; safety limits | Credibility of physics without lab validation; domain-expert scrutiny |
| 2 | Prototype & evidence (15) | Two alternatives vs baseline with repeatable simulated indicators | "Measurable and repeatable" from simulation only |
| 2 | Desirability (15) + Business viability (10) | User story, workflow value | Subjective |
| 2 | Innovation (10) | Understandable improvement over starting design | — |
| 3 | Accuracy of classification and link estimation | Confusion matrix on generated/known traffic, confidence outputs, correction UI; capacity-estimate error vs configured netem rate | Realistic encrypted-traffic generalisation |
| 3 | Reduction in latency/jitter/loss | Baseline vs optimized across ≥N repeated runs with CIs for 3 scenarios | Linux environment stability on Windows laptops |
| 3 | Fairness / no starvation | Jain's index, minimum bulk-throughput floor shown under load | — |
| 3 | Adaptation speed / stability | Time-series of policy changes after the 100→20 Mbps event; no oscillation | Controller tuning |
| 3 | CPU overhead / reproducibility / clarity | CPU% of controller, one-script reproduction, report generation | — |
| 4 | Accuracy & validation approach | Seeded-error label set with precision/recall of checks; human-approval gates | No public ground truth; regulatory expert judgement |
| 4 | Regulatory/compliance awareness | Correct citation of FDA 21 CFR 801 / MDR Annex I Ch. III / UDI / ISO 15223-1 symbols with provenance | Paid standards; hallucination risk |
| 4 | End-to-end process coverage | Demonstrated flow across the 18-step process | Breadth vs depth trade-off; PLM/ERP absence |
| 4 | Traceability & auditability | Requirement → label element → source → approval → change order links | — |
| 5 | Edge Performance | Measured RSS memory and p50/p95 latency on ARM/QEMU/Pi under 2 GB cap; sub-2 s for common queries | Hardware access; SLM latency on 2 cores |
| 5 | AI Capability + Search & Analytics | Labelled query set with accuracy; grounded answers with event references; trend/anomaly evidence | Defining "accuracy" credibly |
| 5 | Data Integration | Live CAN (SocketCAN vcan + DBC) and log ingestion; adapters for other protocols documented as proposed | SOME/IP, VHAL, QNX cannot be exercised live |
| 5 | Privacy & Security / Architecture | Local-only proof (network disabled), read-only gateway isolation diagram | — |
