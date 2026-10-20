# Competitive Landscape

SentinelLoop product team. Written 2026-10-18 by the technical writer from `product/research/R3_competitive_landscape.md` (R3) and `product/research/R5_integration_standards.md` (R5), with every web claim re-opened in this session.

---

## How to read this document

**Method.**
- I re-opened every web page cited below on 2026-10-18, using WebFetch, or `curl` with `pdftotext` for PDFs and machine-readable API specs.
- Where R3 or R5 made a claim that I could not re-open, I either dropped it or marked it **UNVERIFIED (this session)** and pointed to the research file.
- WebSearch was not available. Its one attempt was refused because the shared per-turn search budget was used up. So this document adds no vendors beyond R3, R5, the wind proposals and the pages I could reach by known URL. Wind-specific coverage in particular is **incomplete**; see section 10.

**Fact-check pass (2026-10-18, separate reviewer).**
- A fact-checker re-opened 47 of the cited URLs with WebFetch (PDFs read locally with `pdftotext`), plus 2 new primary sources: [S87] for the Avathon rebrand and [S88] for UL 4143. WebSearch was again unavailable, so no claim was checked by searching.
- Every opened page supported the claim it backs, apart from the wording corrections below. Corrections made: the Avathon former name now has a source; UL 4143 now has a source; quotation marks removed where the words were not verbatim (Falkonry "at 100Hz", OpenOA "not yet validated"); SKF's "Remote Analysis" described as a service category, not a product name; Siemens Gamesa's single-component wording quoted exactly; INOX Green's >13 GW qualified as the page qualifies it; NIST cost figure given as "relative to shipments"; the CARE paper's 44 described as datasets with a labelled event; "no independent benchmark exists" changed to "none found, UNVERIFIED"; internal study names S1/S1c tied to their files so they are not confused with source [S1].
- Checked locally: the document claims no interviews, customers, pilots, LOIs or field results. Every SentinelLoop result cited matches `product/CLAIM_EVIDENCE_MATRIX.md` or `product/evidence/scheduling/tuned_baselines.md` and is labelled simulated or synthetic.

**Phase 9 update (2026-10-18, after the adversarial review).**
- Stale descriptions of SentinelLoop itself were corrected against the code, tests and `product/evidence/`: the CMMS connector, the wind model, the audit chain and the platform's lack of a re-derivation command, competition-only retraining and the promotion gate's pre-registered result, and the scheduling results, which now quote the corrected S2 evaluation and keep S1c as history.
- No competitor fact was added or changed, and no web page was opened in this update.
- Indian OEM and SCADA-analytics alternatives remain unverified (OPEN, section 10).

**Final handoff audit update (2026-10-18).**
- The abstention claim (sections 1, 8.1 and 8.2 item 3) now says only what claim P4 supports, with its limits: the competition pipeline's result depended on a fleet-level rule the platform lacks, a single-sensor bias is caught only on some engines, and slow sensor drift on a wind turbine is taken for component heating.
- The wind summaries now carry the alarm burden counted as the pilot criterion B3 counts it (about 13 episodes per turbine-year on synthetic data), and the wind statuses match `FINAL_PRODUCT_HANDOFF.md` §2.
- No competitor fact was added or changed, and no web page was opened.

**Labels.**
- **Vendor claim.** A statement on the vendor's own page that nobody has checked independently. All fleet sizes, accuracy figures, lead times, ROI and savings numbers below are vendor claims.
- **UNVERIFIED.** Not confirmed from a primary page opened in this session.
- **Analysis.** My reasoning or the team's. It is not a sourced fact and no customer has validated it.
- **Local evidence.** A file in this repository. It is cited by path and is not a web source.

**Data provenance vocabulary.** These are the same four terms used across the product documents.
- **Real field data.** Recorded from equipment in normal service.
- **Real laboratory data.** Recorded from physical test rigs.
- **Simulated data.** Produced by a physics or thermodynamic simulator, for example NASA C-MAPSS.
- **Synthetic data.** Generated or perturbed by our own code, for example injected faults or the illustrative wind fleet.

**State of the vertical decision (do not read it as settled).**
- The judge chose Indian onshore wind owner-operators. The target assets are geared turbines of about 1.5-2.3 MW, monitored only through 10-minute SCADA and alarm logs (`product/research/V_judge_decision.md`).
- The adversarial review **rejected** that choice and listed required changes (`product/research/V_adversarial_review_wind_choice.md`).
- The decision record then kept wind as **PROVISIONAL and GATED** on G0 (public-data test) and G1 (access conversations), with the band narrowed to 2.0-2.3 MW geared (`product/INITIAL_MARKET_AND_ASSET_CHOICE.md`; `DECISION_LOG.md` PD-10). G0 is pre-registered but not run, and no G1 conversation has been held. The team lead's keep-or-switch decision is open.
- This document therefore covers general industrial predictive maintenance and also the wind and renewables players that matter if wind is confirmed.
- The bus runner-up is touched on only where a product overlaps (Uptake Fleet).

**Where this file lives.** The task assigned the path `product/COMPETITIVE_LANDSCAPE.md`. This is a new file; no existing file was changed.

---

## 1. Summary

1. **The analytics SentinelLoop offers or has prototyped are standard features of commercial products.** Vendors document all of them: anomaly detection against learned normal behaviour, time-to-failure or time-to-action, sensor-health checks, work orders raised from analytics (SentinelLoop raises each one awaiting a person's approval, PENDING_APPROVAL, `app/decision.py`, `app/workorders.py`), and scheduled retraining with gated promotion (in SentinelLoop only in the frozen competition pipeline; the product platform has none, `PRODUCT_REQUIREMENTS.md` FR-H3). Examples are GE Vernova SmartSignal, AVEVA, Honeywell, IBM Maximo, C3 AI, Aspen Mtell, Siemens Senseye and AWS IoT SiteWise ([S13], [S14], [S15], [S16], [S18], [S11], [S9], [S35]).
2. **The wind market has specialised incumbents with large fleets (vendor claims).**
   - ONYX Insight says it is "Monitoring 32,000+ turbines globally" and has an office in Bengaluru, India [S24][S25].
   - Turbit says it monitors 3,500+ turbines and sells a paid backtest on OEM SCADA exports. It asks for at least 3 years of history per turbine [S26][S27].
   - Clir reconciles OEM availability calculations into "dispute-ready reports" [S28].
   - IBM Maximo Renewables creates and prioritises work orders automatically and has a Gujarat-headquartered customer [S29][S30].
   - In India, INOX Green says it operates "11 GW of Wind O&M assets" and lists predictive maintenance as a service [S85].
3. **OEMs sell full-scope wind service, including life extension and multibrand coverage (vendor claims).** Siemens Gamesa offers to "maintain and run every aspect" of a wind farm, runs a "Life Extension program" and serves "all turbines, no matter the make" [S83]. Vestas lists maintenance, fleet optimisation and digital services [S84].
4. **The incumbent alternative in general industry is still mostly no predictive software.** The 2020 Plant Engineering study was sponsored by a maintenance-services firm and had 171 respondents. Of these plants, 76% use preventive maintenance and 60% run-to-failure. For managing maintenance, 50% use a CMMS, 47% in-house spreadsheets and 46% paper records [S77]. No comparable Indian or wind-sector survey was found (**UNVERIFIED gap**).
5. **For a small team, the cheapest place to integrate is open source.**
   - Commercial CMMS APIs sit on upper paid tiers: UpKeep Enterprise, MaintainX Premium and Enterprise, Limble Premium+ and Enterprise, eMaint Enterprise, and Fiix Enterprise "for an additional cost" [S42][S46][S49][S52][S40].
   - Self-hosted Odoo Community ships the maintenance app under LGPL-3 and a current JSON-2 API [S57][S58][S60].
6. **Our own evidence cuts both ways.**
   - Where it may differentiate us (local evidence, all on **simulated** data):
     - decisions re-derived from the audit log: 3,409 re-derived, 0 mismatches. This is a competition-pipeline result, valid within one run; the product platform has no re-derivation command (`TECHNICAL_DEBT.md` F11);
     - measured escalation on bad inputs. This is a competition-pipeline result on injected faults, and its zero silent wrong orders depended on a fleet-level rule the product platform does not have (`CLAIM_EVIDENCE_MATRIX.md` P4; section 8.2 item 3);
     - interval coverage reported, including where it misses.
   - Where it argues against us:
     - In our own simulated scheduling study, no rule wins everywhere (S2, `SCHEDULING_EVALUATION.md` conclusion 3; tuned on FD001 engines, evaluated on FD003 engines). The risk-ranked greedy policy is cheaper under tight labour (9.4-17.2 units, on 4-7 of 8 seeds). The tuned threshold rule is cheaper under degraded predictions (8.9-22.1 units). In the other sustainable scenarios the two are within 4.1 units, with per-seed differences spanning zero, and under approval delay a third policy (RISK_EDD) is cheapest. We cannot claim that our ranking layer beats simple rules.
     - History: the earlier S1c study had found that no risk-based policy beat the tuned threshold rule in any of five scenarios (`product/evidence/scheduling/tuned_baselines.md`). S2 overturns that in part (`SCHEDULING_EVALUATION.md` §6.0, claim 3). S1c tuned and evaluated on the same 200 engines, left downtime out of the cost, and ranked two fleet-collapse scenarios, parts shortage and adverse, in which a broken asset costs nothing (section 8.1).
   - The wind alarm setting was chosen on synthetic data only. On fresh held-out synthetic turbines it gave 0.44 healthy alarm episodes per turbine-year, but on 2.27 turbine-years the 95% interval runs up to about 2.45, so it does not exclude the proposed pilot ceiling of 2. An earlier run's setting (sustain 6 instead of 18) gave 5.74 on other synthetic fleets, so the rate is sensitive to persistence; drifting sensors still raise alarms (39 episodes on the fresh fleets). Counted the way the pilot's alarm-burden criterion counts (drifting-sensor turbines included), the fresh fleets give about 13 episodes per turbine-year, far above the proposed ceiling of 2 (`product/evidence/wind_synthetic/w3.md`, `w2.md`; `KNOWN_LIMITATIONS.md` E7, M1; `PILOT_ACCEPTANCE_CRITERIA.md` B3).
7. **Where we cannot compete:** sensors and CMS hardware, field-data scale, human analysts, OEM risk-transfer and full-scope service contracts, enterprise breadth, and point-accuracy claims (section 8.3).
8. **We have no validated reason to buy over incumbents.** The alternatives most likely to matter to an Indian owner have **not** been verified: OEM full-service contracts that may hold the SCADA and the work orders, and Indian SCADA-analytics vendors. This item is **OPEN** and needs sourced web research (section 10; `KNOWN_LIMITATIONS.md` C2).

---

## 2. Commercial predictive-maintenance and APM products

Categories:
- **(A)** sensor hardware plus analytics, often sold with analysts;
- **(B)** software-only APM or analytics on existing historian, SCADA or IoT data;
- **(C)** vertical fleet analytics;
- **(W)** wind or renewables specialists;
- **(D)** cloud building blocks.

Every capability statement comes from the vendor's own page and is a **vendor claim** unless stated otherwise.

### 2.1 General industrial

| Product (owner) | Cat. | Documented capabilities (vendor claims) | Inputs | Deployment | Integration | Source URL |
|---|---|---|---|---|---|---|
| Augury Machine Health | A | "Prescriptive AI machine diagnostics" for pumps, motors, compressors, gearboxes, fans and similar. Role-based AI agents (the "Industrial AI Workforce"). Human "CAT II/III Vibration Analysts". Claims "1.1B+ hours of real machine readings", "170+" manufacturers, "40+ Countries" and a Forrester-attributed "310%" ROI | Own Halo R4000 sensor: tri-axial vibration (±60 g), environment and surface temperature, tri-axial magnetic flux. BLE to a Cassia X2000 gateway (up to 64 sensors) with Wi-Fi or cellular. Batteries "up to 5 years" | Sensors installed on site, with installation services | Diagnostics into SAP PM. Repairs triggered from alerts in IBM Maximo. Work orders from alerts in Infor EAM ("Automatically"), MaintainX and Limble. Azure, PTC, AVEVA Connect | [S1] https://www.augury.com/ ; [S2] http://www.augury.com/?p=7721 ; [S3] https://www.augury.com/partners/ |
| Tractian | A | Vibration analysis, AI failure detection, root-cause analysis, its own CMMS (work orders, parts, PM, app), and electrical and current monitoring. No prices published ("Estimate your price") | Own wireless sensor: 4G/LTE, IP69K, −40°F to 250°F, "Class 1 Div 1 (ATEX, IECEx, NFPA compliant)", battery 3-5 years | Cellular sensors plus Tractian's own CMMS (hosting not stated) | SAP, Oracle NetSuite, Power BI, Maximo | [S4] https://tractian.com/en/plans |
| KCF Technologies SMARTdiagnostics | A | Fault library "as of February 2026": bearing, gear, belt, coupling, drive, pump, imbalance, lubrication, looseness and more. $199 trial: 30 days, 48 sensors and a base station | Wireless vibration sensor capturing full spectrum "up to every minute". Piezo at "96,000 samples per second", down to "2 RPM". MCSA/ESA. IoT HUB with 7 channels for third-party sensors | Base station to the SMARTdiagnostics cloud | PLC-triggered capture; third-party, OEM and legacy sensors | [S5] https://kcftech.com/solutions/smartsensing-suite/ |
| Petasense ARO Cloud | A | Digital twins, AI failure-mode detection, web and mobile | Vibration, temperature, ultrasound, pressure and current transmitters; VFD monitoring; wired options | Cloud | Process historians and CMMS | [S6] https://petasense.com/ |
| Infinite Uptime PlantOS (US HQ; Indian entities in Pune and Mumbai) | A | Prescriptive AI for heavy industry: names the fault, the fix and whether the fix worked. Operators validate prescriptions. Claims are inconsistent on the page: 1,000 plants in the banner against 946 in a status widget; "99.97% Accuracy" with no definition | Own wired and wireless MEMS/piezo sensors, plus third-party sensors, PLC and historian data, inspections and oil analysis | 90-day rollout; first prescription in about 2 weeks | Open API and MCP into enterprise systems | [S7] https://infinite-uptime.com ; [S8] https://www.infinite-uptime.com/about-us |
| Siemens Senseye Predictive Maintenance (Siemens subsidiary since 1 Jun 2022; HQ Southampton) | B | Forecasts machine failure, prioritises risk, gives "remaining useful life and priorities across your plant". The current page gives no quantified results | Existing data from "legacy machines, historians, IoT platforms or new sensors"; no new hardware needed | "cloud-based"; hosting details not given | Historians, IoT platforms, databases | [S9] https://www.siemens.com/us/en/products/services/digital-enterprise-services/analytics-artificial-intelligence-services/predictive-services/senseye-predictive-maintenance/how-it-works.html ; [S10] https://news.siemens.co.uk/news/siemens-acquires-senseye-predictive-maintenance-and-asset-intelligence-for-industrial-companies |
| Aspen Mtell (Emerson subsidiary since 12 Mar 2025) | B | Failure patterns detected "up to 90 days in advance". Embedded FMEA prescribes corrective action. Industry asset templates. Claims 30% lower maintenance cost and 20% more uptime | Not detailed on the page | Not described on the page | EAM and ERP workflows; Emerson AMS vibration monitoring | [S11] https://www.aspentech.com/en/products/apm/aspen-mtell ; [S12] https://www.emerson.com/en-us/news/2025/emerson-completes-acquisition-of-remaining-outstanding-shares-of-aspentech |
| GE Vernova SmartSignal / APM | B | Compares readings with each machine's predicted normal values "not by thresholds on actual values". Diagnostics against precursor signatures from "OEM-agnostic data from over 19,500" assets. Time-to-action forecasting. Sensor Health Monitoring and Virtual Signal Repair. "over 370 Digital Twins". New blueprints being built for "wind and solar". Claims $1.6B+ of losses avoided and a 3.4-month average ROI | Load, temperatures, pressures, vibration, ambient | On-prem software, cloud subscription, or a pillar of GE Vernova APM. GE Industrial Managed Services offers "24x7 asset monitoring" or a "turnkey outsourced offering" | Part of GE Vernova APM (connector details in R3, not re-opened in this session) | [S13] https://gevernova.com/software/sites/default/files/2024-10/brochure-ai-powered-predictive-analytics-smartsignal.pdf |
| AVEVA Predictive Analytics | B | Anomalies "weeks or months before failure". Time-to-failure forecasting. Per-sensor fault contribution. Prescriptive actions from an Asset Library ("more than 22,000 hours of experience"). Custom Python models. No-code templates | Sensor data (sources not detailed); AVEVA PI System listed as a related product | Not detailed on the page | AVEVA PI System | [S14] https://www.aveva.com/en/products/predictive-analytics/ |
| Honeywell Forge APM | B | First-principles thermodynamic models plus pattern recognition, ML and fault-symptom models. Automatic data cleansing. Prediction and RUL trending. FMEA rules. Extensible with Python and C# | OPC DA/A&E/HDA, historians, relational data such as lab and oil analysis | Honeywell cloud or the client's cloud (product note, undated) | "CMMS Connectivity & Work Order Requests"; SAP PM and IBM named | [S15] https://process.honeywell.com/content/dam/process/en/documents/document-lists/PINForgeAPMR1-v1.pdf |
| IBM Maximo Health / Predict | B | Predict templates: failure probability in a window and predicted failure dates, both from "IoT sensor data, meter data, and past failure history". Anomaly detection, failure-contribution breakdown, and an end-of-life curve from retirement data. Health 9.1: health and custom scores, data-quality work queues. Health stand-alone is "no longer offered" | IoT, meters, failure history, retirement data | Maximo Application Suite (OpenShift per R3; not re-opened here) | Maximo Manage (section 3) | [S16] https://www.ibm.com/docs/SSC5CS/com.ibm.pm.doc/config/c_predictive_model_templates.html ; [S17] https://www.ibm.com/docs/SS7PRM_cd/com.ibm.ah.doc/overview/whats_new_91.html |
| C3 AI Reliability | B | Time-series foundation models and ML, "ranked critical risk alerts", failure-mode recommendations and "direct work order creation". Claims "50%" less downtime, "99%" less alert noise and "6 Months" to deploy | Sensor data, maintenance records, parts inventory, documents and diagrams | C3 Agentic AI Platform | Work-order creation (target systems not named on the page) | [S18] https://c3.ai/products/c3-ai-reliability/ |
| Falkonry | B | "Time Series AI": pattern recognition and anomaly scoring | PLCs via Modbus and OPC UA; SCADA and DCS at 100 Hz; "Physics Sensors 10kHz power quality" | "Edge, Cloud, On-Premises, Air Gap, Sovereign" | Data-source integrations. The page does not mention IFS (the IFS deal status is **UNVERIFIED**; see R3) | [S19] https://falkonry.com/ |
| SAP Asset Performance Management | B | **UNVERIFIED (this session):** the page returned HTTP 403 twice. R3 reports anomaly detection, failure curves, RUL, FMEA and RCM on SAP BTP, and that SAP EAM is required | — | — | — | [S20] https://www.sap.com/hk/products/scm/apm.html (403) |
| Altizon DFX (Princeton NJ and Pune) | B | "AI-Native MES"; predictive maintenance listed under Applied AI | PLCs, sensors, ERP | Not stated | ERP | [S21] https://www.altizon.com/ |
| Avathon ("formerly known as SparkCognition"; rebrand announced in Bangalore on 11 Nov 2024 [S87]) | B | Knowledge, decision-intelligence and governance layers; a "Renewable Suite" mentioned in an Ørsted quote. **No predictive-maintenance product is named on the page** | Not documented | Not documented | Partners NVIDIA, Microsoft, AWS, Google Cloud, Dell | [S22] https://avathon.com/ ; [S87] https://avathon.com/press-release/avathon-aims-to-triple-workforce-in-india-within-24-months/ |
| Uptake Fleet (Bosch "planned acquisition" announced 19 Mar 2026) | C | Sensor analytics, risk explorer, remote diagnostics, warranty-claim identification, mixed-fleet data hub. Covers buses, trucks, construction and mining | Fleet telematics (not detailed) | Web portal | Platform Science, Trimble, CalAmp, Intellishift | [S23] https://uptake.com/ |

### 2.2 Wind and renewables specialists

| Product (owner) | Cat. | Documented capabilities (vendor claims) | Inputs | Deployment | Integration | Source URL |
|---|---|---|---|---|---|---|
| ONYX Insight (HQ Nottingham; office in Bengaluru, India) | W, A | ecoCMS drivetrain CMS (with retrofits), ecoPITCH, ecoBLADE; ONYX Cortex workflow. Faults caught "up to 24 months ahead". "Monitoring 32,000+ turbines globally"; country count inconsistent (35+ vs 45+). Engineering and consultancy covering "180+ platforms" | Vibration plus oil particle counting; connects "15 different CMS hardware types". The page does not mention SCADA | Sensors installed on turbines (ecoPITCH "from just ½ day installation per turbine") | Not described on the page | [S24] https://www.onyxinsight.com/ ; [S25] https://onyxinsight.com/company/our-locations/ |
| Turbit | W, B | "12k+ Neural Networks In Production"; 3,500+ turbines, 30,000+ asset-years, 40+ customers. Backtest (paid, "small one-time price"): one neural network trained per turbine, replayed on history. Targets main-bearing exchanges, gearbox damage, generator failures and underperformance. Each event reported with severity, root-cause prediction and the date it became detectable | SCADA history: "3+ years ... per turbine", 5+ preferred. Exports from Vestas, Siemens Gamesa, Nordex, Enercon and GE; Bazefield and Greenbyte platforms | Not stated | Turbit Blue (insurance workflows), Turbit Datahub | [S26] https://www.turbit.com/ ; [S27] https://www.turbit.com/backtest |
| Clir | W, B | Real-time portfolio monitoring, benchmarking and anomaly detection. "reconciles OEM calculations" of availability; "dispute-ready reports" for bonus or liquidated-damages claims. "Built on 350+ GW of assets across solar, BESS and wind" | "real operating data" (not detailed) | Not stated | Not stated | [S28] https://www.clir.eco/ |
| IBM Maximo Renewables | W, B | Solar, wind and battery APM. "Enhanced turbine prognosis visualizations" and "Digital twin-based loss analysis". Work orders "Automatically create[d], track[ed], and prioritize[d]" through Maximo Manage | Near-real-time performance data; pre-trained models for causes of underperformance | Integrated with Maximo Application Suite; free trial and demo offered | Maximo Manage | [S29] https://www.ibm.com/products/maximo/renewables |
| IBM case study: KP Group (Gujarat, India) | — | Customer evidence (vendor case study): "over 5.7 GW of installed capacity", a managed portfolio "exceeding 1.4 GW", "over 70 sites across India". The O&M described covers "solar and hybrid power plants": anomaly detection on 9,000+ strings and automated hourly reporting. **It is not evidence of wind-turbine use** | — | — | Maximo Renewables | [S30] https://www.ibm.com/case-studies/kp-group |
| Power Factors Unity | W, B | Local and Central SCADA, power plant controller, energy management, APM, and Field Service Management (work orders, scheduling, inventory, KPIs). "600+" customers. The page does not mention Greenbyte or Bazefield, and its GW figure did not render | SCADA | Not stated | Own field-service module | [S31] https://www.powerfactors.com/ |

INOX Green, Siemens Gamesa and Vestas sell services, not software products. They are covered under section 6.4.

### 2.3 Cloud building blocks: current status

| Service | Status (as documented) | What remains relevant | Source URL |
|---|---|---|---|
| Amazon Lookout for Equipment | Closed to new customers 7 Oct 2025; **discontinued 7 Oct 2026** | AWS points builders to IoT SiteWise and provides migration scripts | [S32] https://aws.amazon.com/blogs/machine-learning/preserve-access-and-explore-alternatives-for-amazon-lookout-for-equipment/ |
| Amazon Monitron | **Closed to new customers 31 Oct 2024**; devices sold to existing customers until July 2025; five-year device warranty | AWS names partner alternatives: Tactical Edge, IndustrAI, Factory AI | [S33] https://aws.amazon.com/blogs/machine-learning/maintain-access-and-consider-alternatives-for-amazon-monitron |
| AWS IoT SiteWise anomaly detection | Multivariate detection GA on 28 Jul 2025, "without requiring machine learning expertise"; regions us-east-1, eu-west-1, ap-southeast-2 | Since 10 Sep 2025: scheduled retraining (30 days to 1 year), automatic or manual promotion, and precision, recall and AUC shown to the user. **This makes "gated retraining" a standard feature** | [S34] https://aws.amazon.com/about-aws/whats-new/2025/07/aws-iot-sitewise-multivariate-anomaly-detection/ ; [S35] https://aws.amazon.com/about-aws/whats-new/2025/09/aws-iot-sitewise-retraining-anomaly-detection-models |
| Azure AI Anomaly Detector | No new resources since 20 Sep 2023; **retired 1 Oct 2026** | Microsoft recommends Fabric or the open-source `microsoft/anomaly-detector` | [S36] https://learn.microsoft.com/en-in/azure/ai-services/anomaly-detector/whats-new |
| Microsoft Fabric Real-Time Intelligence anomaly detection | **Preview** | Documented limits: needs numeric, datetime and string columns; one model per detector; at most eight concurrent Eventhouse queries, and extra queries "might silently fail"; enabling the Python plugin can take up to an hour | [S37] https://learn.microsoft.com/en-us/fabric/real-time-intelligence/anomaly-detection |

---

## 3. CMMS and EAM products

The "integration point" column says where an external predictor such as SentinelLoop could write. It comes from R5 and was re-checked here.

| Product (owner) | Category | Documented capabilities | Condition inputs it accepts | Deployment | Integration point for an external predictor; API plan gating | Source URL |
|---|---|---|---|---|---|---|
| Fiix ("a Rockwell Automation Company") | Cloud CMMS | Work orders and requests, assets, parts, analytics, offline mobile with meter readings. Fiix AI and the Fiix MAX assistant. Asset Risk Predictor (Dec 2023 trade news): learns failure signs in "as little as seven days", gives a daily risk level, and can create work orders automatically when connected to a CMMS. It is sold stand-alone or integrated | Sensor data, machine recipe and operating environment (Asset Risk Predictor) | Cloud | CRUD and RPC API with Java and JS SDKs. Application, Access and Secret keys; the keys act as their user. `WorkOrder` needs a site ID and status ID; assets link through `WorkOrderAsset`. Sandbox only for active Enterprise subscribers. **Custom API integrations: Enterprise only, "for an additional cost"**. The Free plan excludes integrations and the audit trail | [S38] https://fiixsoftware.com/ ; [S39] https://fiixlabs.github.io/api-documentation/guide.html ; [S40] https://fiixsoftware.com/pricing/ ; [S41] https://www.bindt.org/News/december-2023/fiix-ai-software/ |
| UpKeep | Cloud CMMS plus Edge IIoT | Edge sensors on a mesh gateway. Thresholds raise alerts that "auto-create work orders". AI health scores; insights "updated every 15 minutes" | Temperature, humidity, vibration, current, pressure, water, gas, light (UpKeep Edge) | Cloud | REST at `api.onupkeep.com/api/v2/`. Organisation API token (bearer) recommended; legacy session token. **"enabled only for accounts on the Enterprise Plan"** | [S42] https://developers.onupkeep.com/ ; [S43] https://upkeep.com/product/edge-iiot/capabilities/cmms-integration |
| MaintainX (banner: "MaintainX joins Autodesk") | Cloud CMMS/EAM | Work orders, PM, inventory, AI troubleshooting and summaries. Meter-triggered automations create work orders, change asset status or send email. These need Premium; custom automations need Enterprise; web only; legacy IoT meters (including Samsara) unsupported. Published prices: Basic $0, Essential $20, Premium $65 per user per month billed annually; Enterprise custom | Meters and meter readings, including automated meters created through the REST API | Cloud | Public OpenAPI (downloaded without an account): "API access is available on Premium and Enterprise plans". `/workrequests`, `/workorders/external/{externalId}` (idempotent upsert on our own ID), `/meterreadings` | [S44] https://www.getmaintainx.com/ ; [S45] https://help.getmaintainx.com/about-automations ; [S46] https://www.getmaintainx.com/pricing ; [S47] https://api.getmaintainx.com/v1/openapi.json |
| Limble | Cloud CMMS | Work orders, PM, assets, parts, digital audit records. Pricing table lists "Anomaly Detection" and "IoT Sensor Integrations*" (additional costs may apply) for Premium+ and Enterprise. No prices or trial shown | Numeric asset fields with history; IoT sensor integrations (upper tiers) | Cloud; regional hosts | Public OpenAPI 3.1 "Limble API V2", HTTP Basic: `/v2/tasks`, `/v2/assets/fields` (with history and batch update), `/v2/webhooks`; list limit 1000. **Open REST API on Premium+ and Enterprise only** | [S48] https://limble.com/ ; [S49] https://limble.com/pricing ; [S50] https://api.limblecmms.com/openapi.json |
| eMaint (Fluke Reliability) | CMMS/EAM | Work orders (offline mobile), PM, "a comprehensive audit trail and password-protected e-signatures". Work orders generated automatically when an asset runs outside limits. Condition monitoring with Fluke IIoT vibration sensors | ERP, SCADA, PLC and BMS data | Cloud (prepaid annual plans) | **"Access to eMaint APIs" on Enterprise only**; "Sandbox Staging Account" on Professional; demo only. API mechanism (JWT, record operations): R5 local check of a Postman collection, **not re-opened in this session** | [S51] https://www.fluke.com/es-us/productos/software-de-fluke/emaint-cmms ; [S52] https://www.emaint.com/pricing/ |
| IBM Maximo Manage (in Maximo Application Suite) | EAM | Work orders and assets; Health and Predict add-ons (section 2.1) | Meter readings | MAS | Post readings to `MXMETERDATA` at `/maximo/api/os/mxmeterdata` with `x-method-override: SYNC`; each new reading must be dated after the last one. MAS Manage auth: API key or SAML; maxauth, BASIC and FORM "Unsupported". R5 found a 14-day trial; developer licence "Not under consideration" (not re-opened here) | [S53] https://www.ibm.com/support/pages/maximo-adding-meter-readings-using-rest-api ; [S54] https://ibm-maximo-dev.github.io/maximo-restapi-documentation/authentication/auth |
| SAP S/4HANA Plant Maintenance | ERP/EAM | Maintenance notifications and orders (R5) | Measurement documents (R3; current API **UNVERIFIED**) | On-prem or cloud | Sandbox `API_MAINTNOTIFICATION`: a local `curl` in this session returned HTTP 401, "Failed to resolve API Key variable", so a key is required. Whether a free SAP account gets a key and can write: **UNVERIFIED** (R5) | [S55] https://sandbox.api.sap.com/s4hanacloud/sap/opu/odata/sap/API_MAINTNOTIFICATION/$metadata |
| Octave Attune EAM ("Formerly HxGN EAM") | Cloud EAM | Asset hierarchies, work orders, labour scheduling, calibration, inventory, mobile, 2D CAD and 3D digital twin, an embedded AI assistant. Separate "Octave Attune APM" (formerly HxGN APM) predicts failures. The page does not mention Infor EAM | Not stated | "cloud-based" | APIs not mentioned on the page | [S56] https://www.octave.com/eam |
| Odoo Maintenance (Odoo SA; module LGPL-3) | ERP with maintenance app | Equipment register; corrective and preventive requests; priority 0-3. `estimated_next_failure` is "Computed as Latest Failure Date + MTBF", which is statistical and not condition-based | None for condition data; requests and dates only | Self-hosted Community, or Odoo Online | JSON-2 API: `POST /json/2/<model>/<method>` with a bearer API key; keys last at most three months; target `maintenance.request`. XML-RPC/JSON-RPC removal is scheduled for Odoo 22 (fall 2028). **Odoo Online: external API on Custom plans only**; the `rpc` addon is LGPL-3 and `auto_install` in self-hosted code | [S57] https://www.odoo.com/documentation/19.0/developer/reference/external_api.html ; [S58] https://raw.githubusercontent.com/odoo/odoo/19.0/addons/maintenance/__manifest__.py ; [S59] https://raw.githubusercontent.com/odoo/odoo/19.0/addons/maintenance/models/maintenance.py ; [S60] https://raw.githubusercontent.com/odoo/odoo/19.0/addons/rpc/__manifest__.py |
| ERPNext Asset Maintenance (Frappe) | ERP with asset maintenance | Time-based plans (task periodicity), generated maintenance logs, a separate Asset Repair workflow. **No condition-based or predictive features documented** | None documented | Self-hosted or Frappe hosting (not detailed) | REST: `POST /api/resource/:doctype`; token `api_key:api_secret`, session, or OAuth bearer. Licence GPL-3.0 per R5 (not re-opened here) | [S61] https://docs.frappe.io/erpnext/user/manual/en/asset-maintenance ; [S62] https://docs.frappe.io/framework/user/en/api/rest |

**Analysis.**
- Every CMMS above documents at least one way in for an external predictor: requests or work orders, meters, or numeric asset fields.
- On the commercial SaaS products, that way in sits behind an upper paid tier.
- SentinelLoop now has one CMMS connector, for Odoo through JSON-2 (`src/sentinelloop/app/integration.py`; `DECISION_LOG.md` PD-20).
  - It is shadow by default and synchronises only approved work. It never changes CMMS stages or deletes records.
  - It is tested only against a contract test double of Odoo's documented API (`tests/test_app_integration.py`). The real Odoo sandbox (`sandbox/odoo/`, `tests/test_app_odoo_sandbox.py`) has **not** been run, so compatibility with real Odoo is unproven (`KNOWN_LIMITATIONS.md` S1).
  - There is no MaintainX, Limble, Maximo or SAP adapter, and no contract test against their specs.
- For a team limited to free tools, the credible first integration is self-hosted Odoo Community, then contract tests against the MaintainX and Limble public specs. A contract test proves that our request shapes are valid. It is not proof of integration, and we must not call it that (R5 §2.2).

---

## 4. Open-source options

### 4.1 Software

| Tool | Category | Documented capabilities | Inputs | Deployment | Integration | Licence | Source URL |
|---|---|---|---|---|---|---|---|
| Odoo Community, Maintenance | CMMS module | See section 3. Next failure from MTBF only | Requests and dates | Self-hosted | JSON-2 API (bearer key) | LGPL-3 (module and `rpc` addon) | [S57] https://www.odoo.com/documentation/19.0/developer/reference/external_api.html ; [S58] https://raw.githubusercontent.com/odoo/odoo/19.0/addons/maintenance/__manifest__.py |
| ERPNext | ERP with time-based asset maintenance | See section 3 | Plans and logs | Self-hosted | REST `/api/resource/:doctype` | GPL-3.0 per R5 (**not re-opened**) | [S61] https://docs.frappe.io/erpnext/user/manual/en/asset-maintenance ; [S62] https://docs.frappe.io/framework/user/en/api/rest |
| Atlas CMMS (Grashjs/cmms) | Self-hosted CMMS | Work orders with triggers, analytics, equipment and inventory, purchase orders; Java Spring Boot, React, React Native; 836 stars at access | **No IoT, meter or sensor features mentioned** | `docker-compose up -d` | Mobile apps call `/api`; no dedicated API reference linked | AGPLv3, or a commercial licence: a `LICENSE_KEY` unlocks white-labelling, branding and "advanced features" | [S63] https://github.com/Grashjs/cmms |
| openMAINT (Tecnoteca / PAT srl) | Property and facility CMMS on CMDBuild | Preventive and breakdown maintenance. The mobile app and self-service portal are **proprietary** (for Maintenance Service subscribers) | APIs and IoT not mentioned | Tomcat 10, Java 17, PostgreSQL 17.x; "16 GB of RAM", "4-core", "150 GB" per instance; Docker optional | Not documented on the pages | AGPL | [S64] https://tecnoteca.com/en/products/openmaint ; [S65] https://www.openmaint.org/en/download/latest-version |
| ThingsBoard | IoT platform | Device management, rule chains, alarms, dashboards (R3; product page not re-opened) | Telemetry | Self-hosted | — | **BUSL 1.1 from v4.4.0**, changing to Apache 2.0 after four years. Free production use: non-commercial up to 1,000 devices, or commercial up to 100 devices on one server; branding and a no-charge key required | [S66] https://raw.githubusercontent.com/thingsboard/thingsboard/master/LICENSE |
| OpenRemote | IoT platform | Device management and auto-provisioning; custom asset types; when-then, flow, JavaScript and Groovy rules; multi-tenant realms; edge gateway; about 1.9k stars. **No maintenance-workflow features** | MQTT broker, HTTP/REST, WebSocket | Docker Compose | Manager APIs | AGPL-3.0-or-later (licence file header) | [S67] https://github.com/openremote/openremote ; [S68] https://raw.githubusercontent.com/openremote/openremote/master/LICENSE.txt |
| Eclipse Ditto | Digital-twin framework | Synchronous and asynchronous twin APIs; reported, desired and current state; per-call access checks. **No analytics** | Devices via Eclipse Hono or MQTT brokers | Self-hosted | AMQP 0.9.1 and 1.0, Kafka 2.x, HTTP webhooks, MQTT 3.1.1 and 5 | EPL-2.0 (footer link) | [S69] https://eclipse.dev/ditto/ |
| NREL OpenOA | Wind plant operational assessment (Python) | Long-term AEP with uncertainty (MonteCarloAEP), turbine gross energy, electrical losses, EYA gap analysis, wake losses; static yaw misalignment, which the README says has not been validated on turbines with known misalignment. **Not a fault-detection tool** | Turbine SCADA, met tower, revenue meter, reanalysis (MERRA-2, ERA5); QA, filtering, imputation | Python 3.9-3.12 library; 254 stars | PlantData schema | BSD-3-Clause | [S70] https://github.com/NREL/OpenOA |
| RES wind-up | Wind turbine uplift assessment (Python) | Pre/post yield-uplift with reference-based detrending, uncertainty and diagnostic plots. **Not a fault-detection tool** | SCADA (power, wind speed, yaw, pitch, RPM, downtime) plus reference data | PyPI `res-wind-up`, Python 3.10-3.13; 29 stars | — | BSD-3-Clause | [S71] https://github.com/resgroup/wind-up |
| NASA ProgPy | Prognostics framework | Included models: batteries, centrifugal pump, pneumatic valve, DC motor, ESC, powertrain, propeller load, small rotorcraft, thrown object. **No turbofan or wind-turbine model** | User models and data | Python library | — | **UNVERIFIED** (R3 saw a NOSA badge) | [S72] https://nasa.github.io/progpy/api_ref/progpy/IncludedModels.html |
| microsoft/anomaly-detector | Time-series anomaly-detection package | `time-series-anomaly-detector` 0.4.0. The README is still template text, so documentation is minimal; 34 stars | Time series | pip | — | MIT | [S73] https://github.com/microsoft/anomaly-detector |

**Analysis.**
- The open-source ecosystem splits three ways:
  - CMMS: Odoo, ERPNext, Atlas, openMAINT;
  - IoT and twin plumbing: ThingsBoard, OpenRemote, Ditto;
  - wind performance analysis: OpenOA, wind-up.
- None of the pages opened documents a condition-based, SCADA-driven fault warning that feeds a CMMS work request. That gap is real but small: a competent team can wire an alarm or a script into an Odoo request.
- Licences constrain a commercial product. Atlas, openMAINT and OpenRemote are AGPL. ThingsBoard from v4.4.0 is BUSL, free for commercial use only up to 100 devices.

### 4.2 Open data (real field; for evaluation, not products)

| Dataset | Provenance | Content | Licence | Source URL |
|---|---|---|---|---|
| CARE to Compare v6 (Fraunhofer IEE, Zenodo) | **Real field** 10-minute SCADA | 95 datasets from 36 turbines on 3 farms: 45 anomaly-leading events and 50 normal datasets. Farm A: 5 turbines, onshore Portugal (EDP). Farms B and C: anonymised offshore Germany. 5.5 GB. The record warns that Min, Max and Std statistics are often implausible. Paper v2 counts 44 datasets with a labelled anomaly event (A = 11, B = 6, C = 27), against 45 on the record. The 10-minute resolution is stated in the paper, not on the record. Autoencoder CARE score 0.66; a score equals accuracy if accuracy is below 0.5 | CC BY-SA 4.0 | [S74] https://zenodo.org/records/15846963 ; [S75] https://arxiv.org/html/2404.10320v2 |
| Hill of Towie v2.1.0 (Zenodo) | **Real field** | 21 Siemens SWT-2.3-VS-82 turbines. 10-minute SCADA and alarm logs, Jan 2016 to Apr 2026; downtime series to Aug 2024. **No failure labels stated** | CC BY 4.0 | [S76] https://zenodo.org/records/22662930 |

Competitors train on fleets far larger than these. Section 5 compares them.

---

## 5. Data provenance: what competitors say they learn from, and what we have

| Player | Data behind its models (as stated) | Provenance and status |
|---|---|---|
| Augury | "1.1B+ hours of real machine readings" [S1] | Vendor claim; field data per the vendor |
| GE Vernova SmartSignal | "OEM-agnostic data from over 19,500" assets; "over 370 Digital Twins" [S13] | Vendor claim; field data per the vendor |
| ONYX Insight | "Monitoring 32,000+ turbines globally" [S24] | Vendor claim; field data per the vendor |
| Turbit | "30,000+ asset-years"; 3,500+ turbines [S26] | Vendor claim; field data per the vendor |
| Clir | "350+ GW of assets across solar, BESS and wind" [S28] | Vendor claim; field data per the vendor |
| Infinite Uptime | ~1,000 plants (946 in a status widget) [S7] | Vendor claim; internally inconsistent |
| AWS IoT SiteWise | The customer's own data; precision, recall and AUC shown for review [S35] | Customer field data |
| **SentinelLoop today** | NASA C-MAPSS (simulated) for every RUL result. Stress tests inject **synthetic** faults. The wind anomaly model has been run only on **synthetic** SCADA from our own generator (`product/evidence/wind_synthetic/w1.md`, `w2.md`, `w3.md`). The product branch's wind adapter uses **illustrative** parameters for "a generic ~2 MW geared turbine; none comes from a turbine maker or an operator" (`src/sentinelloop/app/adapters/wind.py`) | **Simulated** and **synthetic** only. No real field or real laboratory data has been run (`product/CLAIM_EVIDENCE_MATRIX.md`, P15 BLOCKED) |

**Analysis.**
- Every commercial competitor says it learns from real field data, either its own or the customer's.
- The nearest real field data we can reach without a customer is CARE Farm A: 11 onshore events on 5 turbines.
- At n = 11, a 95% Wilson interval on a detection rate is ±23-25 percentage points; at n = 44 it is ±13-14 points (computed locally in this session). Any detection claim we publish must carry that interval.

---

## 6. Non-software alternatives

These are what most buyers do today instead of buying software.

### 6.1 Spreadsheets and paper
- **2020 Plant Engineering maintenance study** [S77]:
  - Methodology: sponsored by Advanced Technology Services (advancedtech.com); 171 respondents; margin of error ±7.5% at 95% confidence; data collected 28 Jan-16 Feb 2020; sample drawn from Plant Engineering email recipients.
  - Tools used to monitor or manage maintenance: CMMS 50%, "in-house spreadsheets/schedules" 47%, "paper records of maintenance rounds" 46%.
  - Caveats: the sample is self-selected, the sponsor sells maintenance services, and the sector is general manufacturing, not wind.
- **No Indian or wind-sector survey of maintenance tooling was found** (**UNVERIFIED gap**).

### 6.2 Fixed-interval preventive maintenance and run-to-failure
- **Shares.** 76% of facilities follow a preventive strategy, 60% use run-to-failure and 52% use a CMMS [S77].
- **Definitions.** US DOE FEMP gives reactive ("Fix/replace when broken"), preventive ("Time-based actions"), predictive ("Fix it before it breaks") and RCM, which it describes as a combination of the three plus root-cause analysis. The page gives no savings figures for these strategies [S79].
- **Evidence on the trade-off.** NIST (Thomas and Weiss, IJPHM 2021) had 71 usable responses from US manufacturers. Compared with preventive-heavy plants, predictive-heavy plants had about 18.5% less unplanned downtime and 87.3% fewer defects, but about 212.3% higher direct maintenance costs relative to shipments. The authors call the group comparisons "anecdotal evidence" because the groups are small [S78].
- **False alarms.** May and McMillan (2013) argue that investigating false alarms offshore "will incur costs" and that false alarms "may alter the cost benefit of condition monitoring systems" [S86]. This is why false-alarm rate on CARE's normal datasets is a first-class metric for us.
- **Our own simulated comparison (local evidence, SIMULATED, our cost model).** In the corrected S2 evaluation, fixed-interval maintenance is the most expensive policy other than run-to-failure in every sustainable scenario: 69-173 units above the tuned threshold rule, worse on 8 of 8 seeds (`SCHEDULING_EVALUATION.md` conclusion 5). It is not a safe fallback. These are our assumptions about costs and lead times on C-MAPSS-derived trajectories. They say nothing about any real fleet.
  - History: in the earlier S1c study, fixed-interval and run-to-failure each cost more than the tuned threshold rule on 8 of 8 seeds in its five scenarios (`product/evidence/scheduling/tuned_baselines.md`). Run-to-failure wins when failures are cheap: with the S1 runs re-priced in base, it was the cheapest policy in 6 of 9 settings at a quarter of the failure cost and 3 of 9 at half (`SCHEDULING_EVALUATION.md` §6.5). The S1c cost excluded downtime, and two of its scenarios, parts shortage and adverse, are fleet collapse, in which a broken asset costs nothing, so their rankings do not follow (`KNOWN_LIMITATIONS.md` E4; `ADVERSARIAL_REVIEW.md` data_scientist-2).

### 6.3 Vibration and condition-monitoring service contracts
- **SKF Services, "Remote Analysis" category** [S80] (vendor claims; the page lists Remote Analysis as a service category, not a named product):
  - "Certified & experienced vibration analysts", "Monthly analysis & machine diagnostic reports", "Weekly & daily alarm reviews" and alarm adjustments.
  - Mechanical services: thermography, oil sampling, ultrasound, balancing, alignment.
  - Claims to have saved customers "over $200M" and to return investment "within a few months".
- **Other analyst layers** (vendor claims):
  - GE Industrial Managed Services: "24x7 asset monitoring" or a "turnkey outsourced offering" [S13];
  - Augury: "CAT II/III Vibration Analysts" [S1];
  - ONYX: engineering and consultancy covering "180+ platforms" [S24].
- **Outsourcing is common in general manufacturing.** The average facility outsources 20% of maintenance. Reasons given: lack of time or manpower 48%, lack of staff skills 41%, too many specialised skills 39%, "Agreement with manufacturer/supplier" 36% [S77].

### 6.4 OEM and O&M service contracts
- **Turbofans** (the only asset SentinelLoop has modelled). Both engine makers sell health monitoring inside risk-transfer contracts paid per flying hour (vendor pages):
  - Rolls-Royce TotalCare: "$ per engine flying hour", with "Advanced engine health monitoring" and predictive maintenance planning [S81];
  - GE Aerospace TrueChoice Flight Hour: paid per flight hour or cycle, with "Comprehensive remote diagnostics and trend monitoring" and guaranteed spare engines [S82].
  - **Analysis:** a third-party student tool has no realistic route into that market.
- **Wind OEMs** (vendor claims):
  - Siemens Gamesa can "maintain and run every aspect of your onshore or offshore wind farm", or help with "a particular aspect – blades, generators or gearboxes, for example". It cites "average turbine availability of 98% over the last decade", offers a "Life Extension program" and applies its service to "all turbines, no matter the make" [S83].
  - Vestas lists maintenance, parts and repair, fleet optimisation, and digital services with "industry-leading analytics tools" [S84].
- **India O&M** (vendor claims). INOX Green says it "controls and operates" more than 13 GW of renewable O&M assets across 12 Indian states, "including 11 GW of Wind O&M assets". The page says the 13 GW figure combines subsidiaries, M&A investments and partnerships. It lists WTG operation, DISCOM coordination, reactive maintenance and "Predictive Maintenance". The page describes no method [S85].
- **Not reached.** Suzlon service pages returned 404 or 500 to the adversarial reviewer (`V_adversarial_review_wind_choice.md`, S27). Suzlon's O&M scope in India is **UNVERIFIED**.
- **Not verified (OPEN).** No source opened describes the service scope or SCADA-access terms of any other wind OEM servicing Indian turbines. The adversarial review names Suzlon, Envision and Inox as ones to check (`product/evidence/adversarial/review_full.md` buyer-10; summary row in `ADVERSARIAL_REVIEW.md`). INOX Green's service list is known only from its own page [S85]. Its SCADA-access terms, INOX Wind's OEM contract scope, and anything about Envision are unverified. This needs sourced web research before any pilot conversation (section 10).
- **Analysis.** In wind, the open question for us is whether owners or their OEM and O&M contractors control the SCADA exports and the work orders. That question is still **UNVERIFIED**. If contractors control them, our buyer is the crowded O&M market above, not the owner.

---

## 7. Integration points (from R5, re-checked where possible)

| Need | Documented route | What we can do with free tools | Source |
|---|---|---|---|
| Write a reviewed request into a CMMS | Odoo `maintenance.request` through JSON-2. MaintainX `/workrequests` and `/workorders/external/{externalId}`. Limble `/v2/tasks` and `/v2/assets/fields`. Maximo `MXMETERDATA` | Self-hosted Odoo Community (free). Contract tests against MaintainX and Limble public specs (free; not an integration) | [S57], [S47], [S50], [S53] |
| SAP | `API_MAINTNOTIFICATION` sandbox needs an API key (HTTP 401 without one) | Blocked until an SAP account and key are confirmed (**UNVERIFIED**) | [S55] |
| Read wind data | Exports of 10-minute SCADA history from OEM systems or platforms. Turbit accepts Vestas, Siemens Gamesa, Nordex, Enercon and GE exports, plus Bazefield and Greenbyte (vendor page) | File-based ingestion, which SentinelLoop already does | [S27] |
| Read plant data live | OPC UA, MQTT/Sparkplug B, historian REST (PI Web API) through a DMZ, read-only and enforced on the server side | Documented in R5 §3; not re-opened here | R5 (local file) |
| Standards we must not claim | No IEC 62443 certification or security level, no SIL, not "NIST compliant", no DPDP or CERT-In compliance claim | Use R5's recommended wording: "Designed with reference to ...; not assessed or certified. Advisory only." | R5 §5 (local file) |

---

## 8. Positioning: where a small team can be different, and where it cannot

### 8.1 Evidence we already hold (local, all on simulated or synthetic data)

| Property | What was measured | Status (PD-03) and data | Evidence file |
|---|---|---|---|
| Decisions can be re-derived | **Competition pipeline:** 3,409 stored decisions re-derived with 0 mismatches; in-place tampering detected. Re-running a subset deletes its history (TECHNICAL_DEBT B2).<br>**Product platform:** an HMAC-chained audit log with an anchor. Tests show it detects edits, reordering and truncation (`tests/test_app_foundation.py`). `admin verify-audit` fails without an anchor (PD-22). Each assessment stores its inputs, policy and model ID (`app/health.py`). The chain covers audit events, not state tables, and the platform has no re-derivation command | Competition: IMPLEMENTED_AND_TESTED on C-MAPSS (simulated). Platform audit chain: IMPLEMENTED_AND_TESTED; not field validated | `product/CLAIM_EVIDENCE_MATRIX.md` P6, P20; `app/auditlog.py` |
| Abstention on bad input | **Competition pipeline:** detection of 98-100% on three injected fault types, with zero per-engine false alarms. Single-sensor bias is a detection floor on two subsets. Escalation share 0.13 in an FD001 run. The full agent issued no silent wrong order in 20 corruption scenarios, but most of that zero comes from a fleet-level rule that also escalates 25-36% of healthy engines while a fleet alarm is active; per-engine evidence alone leaves 0-12% silent wrong orders (E3, `docs/EXPERIMENT_RESULTS.md`).<br>**Product platform:** its own data-quality and scope gates, tested on synthetic data (`tests/test_app_ingest.py`, `tests/test_app_health.py` (needs the git-ignored C-MAPSS files), `tests/test_app_wind.py`). A data failure withholds the prediction and raises an instrument-check order awaiting approval (PENDING_APPROVAL); a whole-feed delay raises no instrument check, though a pending latched inspection is still raised (`tests/test_app_rereview_decision.py`). The gates have not been stress-tested the way E3 tested the competition pipeline, the platform has no fleet-level rule (P8), and slow single-sensor drift on a wind turbine raises inspections, not instrument checks (KL M1) | SIMULATED; injected (synthetic) faults | `CLAIM_EVIDENCE_MATRIX.md` P4; `PRODUCT_STATUS.md`; `VALIDATION_LADDER.md` |
| Interval coverage reported, including misses | Coverage 0.85-0.94 across FD001-FD004, with FD004 at 0.85 against 0.90 nominal. Raw-truth coverage 0.58-0.87. Near failure (true RUL 25-50 cycles) coverage is 0.81-0.87 (C1). The RUL model's P(failure) is not calibrated: shown about 0.55 where about 0.92 was observed (C2). "Calibrated" may not be said without the qualifier | SIMULATED; general coverage claim NOT_SUPPORTED | `CLAIM_EVIDENCE_MATRIX.md` P1, P2; `product/evidence/calibration/c1.md`, `c2.md` |
| Promotion gate | **Pre-registered test (E4 primary run): 4 of 8 outcomes as expected, so H4 is NOT SUPPORTED.** The challenger trained on sensor-offset data, expected to be rejected, was promoted on FD002-FD004, and the more-data challenger was rejected on FD001.<br>Post-hoc secondary run (D21): label-corrupted challengers rejected on 4 of 4 subsets; 9 of 12 outcomes as expected; the sensor-offset challenger still promoted on FD003 and FD004 | IMPLEMENTED_AND_TESTED on simulated "new data", **in the competition pipeline only**; the gate's selectivity is NOT_SUPPORTED by its own pre-registered test. The product platform has no retraining or promotion gate; for wind it is PLANNED (FR-H3) | `CLAIM_EVIDENCE_MATRIX.md` P7; `submission/CLAIM_EVIDENCE_MATRIX.md` C13, C14; `PRODUCT_REQUIREMENTS.md` FR-H3 |
| Decision metrics, measured | S1: 384 runs (8 seeds, 120 days, 8 policies, 6 scenarios), reporting cost, failures, unplanned downtime, late jobs, plan-change rate and approvals per day. S2 part A reproduces all 384 runs and adds RISK_EDD and a sustainable parts scenario (504 runs), with terminal downtime (assets still broken at day 120) now counted | SIMULATED | `product/evidence/scheduling/summary.md` (S1, history); `SCHEDULING_EVALUATION.md` §4.1; `product/evidence/scheduling_v2/summary.md` |
| Same metrics against **tuned** baselines | **Current (S2):** tuned on FD001 engines, evaluated on disjoint FD003 engines, with terminal downtime counted. **No rule wins everywhere:**<br>• tight labour: RISK_GREEDY is cheaper than the tuned threshold rule by 9.4-17.2 units, on 4-7 of 8 seeds;<br>• degraded predictions: the tuned threshold rule is cheaper by 8.9-22.1 units; the risk rule is cheaper on 0-1 of 8 seeds;<br>• base, parts_tight and approval delay: the two are within 4.1 units and the per-seed differences span zero; under approval delay RISK_EDD is the cheapest policy.<br>The MILP is never the cheapest policy; under tight labour it cuts unplanned downtime by about 38% at a higher unpriced cost.<br>Caveats:<br>• In "degraded predictions" re-tuning moves the threshold from 100 h to 130 h, exactly the scenario's constant +30 h bias, so that robustness holds by construction (data_scientist-12). Noise, per-asset bias and drift were not simulated.<br>• "Parts shortage" and "adverse" are fleet collapse, in which a broken asset costs nothing. They are reported, not ranked (data_scientist-2).<br>**History (S1c), overturned in part by S2:** no risk-based policy beat the tuned threshold rule on mean cost in any of 5 scenarios. S1c tuned and evaluated on the same engines and left downtime out of the cost | SIMULATED | `SCHEDULING_EVALUATION.md` conclusions 3, 5 and 6, §6.0; `product/evidence/scheduling_v2/summary.md`; history: `product/evidence/scheduling/tuned_baselines.md` |
| Wind | An anomaly-only normal-behaviour model with per-turbine commissioning; adapter parameters are illustrative. It gives no RUL and no failure probability.<br>On **synthetic** data (our own generator; a behaviour check, not performance):<br>• alarm setting margin 1.25, sustain 18 operating points (3 h of operation), chosen by W3 on pooled tuning fleets: 72/72 injected faults flagged and 0.22 healthy alarm episodes per turbine-year;<br>• **fresh held-out fleets: 36/36 flagged and 0.44 healthy alarm episodes per turbine-year (1 in 2.27 turbine-years); the 95% interval runs up to about 2.45, so the proposed pilot ceiling of 2 is not excluded**;<br>• the rate is sensitive to persistence: an earlier run's setting (sustain 6) gave 5.74; drifting sensors still raise alarms (39 episodes on the fresh fleets);<br>• **counted the way the pilot's alarm-burden criterion counts (drifting-sensor turbines included), about 13 episodes per turbine-year on the fresh fleets, far above the proposed ceiling of 2** (`KNOWN_LIMITATIONS.md` E7; `PILOT_ACCEPTANCE_CRITERIA.md` B3);<br>• assessments possible 59% of the time on the fresh fleets.<br>The flagged-fault counts are set by the generator, which shares the model's assumptions (KL E3).<br>No real wind data has been run. The G0 test on CARE is pre-registered (Amendment 1: Farm A against an internal baseline, with the pooled 0.66 autoencoder bar as a secondary bar; Amendment 2: product alarms counted at sustain 18, no pass/fail criterion changed). It is **BLOCKED** on download approval | Wind asset type, ingestion, data-quality gates and per-turbine commissioning: IMPLEMENTED_NOT_FIELD_VALIDATED (`FINAL_PRODUCT_HANDOFF.md` §2; matrix P11). Alarm results: SIMULATED, SYNTHETIC data only (matrix P11). Real data: BLOCKED (P15) | `src/sentinelloop/app/nbm.py`; `product/evidence/wind_synthetic/w3.md`; `product/evidence/g0/PREREGISTRATION.md` §10, §11 |

### 8.2 Where differentiation is plausible (hypotheses; none validated with a customer)

1. **We publish our own evaluation, including where we lose.**
   - Competitor pages opened in this session publish outcome or lead-time claims without a stated method. Examples: "up to 24 months ahead" (ONYX [S24]), "99.97% Accuracy" (Infinite Uptime [S7]), "50%" downtime reduction (C3 AI [S18]), "$1.6B+" of losses avoided (GE [S13]) and "98%" availability (Siemens Gamesa [S83]).
   - None of those pages publishes a false-alarm rate, interval coverage or a confidence interval on detection. That absence is on marketing pages only and does **not** show the products lack the measurement.
   - Turbit already lets a customer judge detection on their own history. It is a paid backtest that walks through each event [S27]. So "evaluate on your own data" is not new. What we could add is a pre-registered protocol that reports the false-alarm rate on normal periods and gives Wilson intervals with every rate.
   - Evidence today: the corrected S2 scheduling evaluation (`SCHEDULING_EVALUATION.md`; `product/evidence/scheduling_v2/`), in which no rule wins everywhere and the tuned threshold rule is cheapest under degraded predictions. It replaces the internal S1 study (`product/evidence/scheduling/summary.md`) and the S1c tuned-baseline study (`product/evidence/scheduling/tuned_baselines.md`), which are kept as history. (S1, S1c and S2 are internal study names, not source tag [S1].) The adversarial review found defects in S1 and S1c: uncounted terminal downtime, fleet-collapse scenarios ranked, and tuning and evaluation on the same engines. Some earlier claims were withdrawn as a result, among them the MILP downtime savings under parts shortage and adverse conditions. Publishing that correction is itself part of this hypothesis.
2. **Decisions that can be re-derived, for owner-side evidence.**
   - Audit trails as such are common. eMaint documents "a comprehensive audit trail and password-protected e-signatures" [S51], and Fiix lists the audit trail among the features its Free plan excludes [S40]. Clir already sells "dispute-ready reports" from OEM availability reconciliation [S28].
   - The narrower property, re-deriving an analytic decision from the stored inputs, rules and model version, is not documented on any page opened.
   - Our evidence is a competition-pipeline result: 3,409 decisions re-derived with 0 mismatches, valid within one run, because a re-run deletes the subset's history (`TECHNICAL_DEBT.md` B2). The product platform stores each assessment's inputs reference, feature hash, model checksum and policy hash, and records each assessment in its HMAC-chained audit log (`app/health.py`), but has no re-derivation command (`TECHNICAL_DEBT.md` F11; `CLAIM_EVIDENCE_MATRIX.md` P6). It cannot demonstrate this property today.
   - Whether an owner, an O&M contractor or a UL 4143 life-extension assessor would pay for this is **UNVERIFIED**. (UL 4143 is "Wind Turbine Generator - Life Time Extension (LTE)"; its published scope covers LTE "rules and procedures" for onshore turbines and does not mention SCADA [S88].)
3. **Explicit abstention instead of silent repair.**
   - SmartSignal monitors sensor health and repairs signals ("Virtual Signal Repair") [S13], and Honeywell "automatically cleanses data" [S15]. Data-quality handling is therefore standard.
   - Our difference, if there is one, is narrow and untested with a customer. When the data checks fail, the platform withholds any prediction (DATA_QUALITY_FAILURE: no prediction from that window is used, `app/states.py`) and raises an instrument-check order awaiting approval (PENDING_APPROVAL); a whole-feed delay raises no instrument check, though a pending latched inspection is still raised. A criticality-A turbine that is out of scope or whose model is unavailable gets a desk review by a person (`app/decision.py`). This is tested on synthetic fixtures only, and the platform's gates have not been stress-tested the way E3 tested the competition pipeline.
   - The limits. The competition pipeline's zero silent wrong orders depended on a fleet-level rule the platform does not have; without it, 0-12% of corrupted engines got a silent wrong order. A +2σ bias on one sensor was detected on only 4-96% of engines. On a wind turbine, slow drift of one temperature sensor cannot be told apart from component heating: it raises inspections, not instrument checks (39 alarm episodes on the fresh W3 fleets) (`CLAIM_EVIDENCE_MATRIX.md` P4, P8; `KNOWN_LIMITATIONS.md` M1).
4. **SCADA-only, no hardware, self-hosted, free-tier integration.**
   - This does not compete with CMS sensors (ONYX, Augury, KCF, Tractian).
   - Commercial CMMS APIs sit on paid tiers; MaintainX's API tier, for example, is Premium at $65 per user per month billed annually [S46]. Self-hosted Odoo Community exposes the JSON-2 API without a pricing plan [S57][S60].
   - Turbit is also SCADA-only [S27], so "no hardware" alone is not a difference.
   - Demand from small Indian owners for a free self-hosted tool is **UNVERIFIED**.
5. **Capacity-constrained ranking (crane or technician budgets).** This is a hypothesis only.
   - The scheduler handles technicians, skills, shifts, parts and windows, but it has **no crane resource**, no weather limits and no multi-day jobs (`KNOWN_LIMITATIONS.md` P8).
   - For wind, orders are ranked within a priority class by an anomaly score labelled "not a probability". No risk is stated (`app/decision.py`).
   - In our own simulation (S2, `SCHEDULING_EVALUATION.md` conclusion 3), no rule wins everywhere. The risk-ranked greedy policy beats the tuned threshold rule only under tight labour (9.4-17.2 units). The tuned threshold rule is cheaper under degraded predictions, and elsewhere the two are within 4.1 units (under approval delay the probabilistic trigger with an earliest-due-date queue is cheapest). The earlier S1c finding that a tuned threshold rule matched or beat every risk-based policy is overturned in part (`SCHEDULING_EVALUATION.md` §6.0, claim 3).
   - This cannot be a selling point until real-data evidence says otherwise.

### 8.3 Where we cannot compete

| Area | Why (sourced) |
|---|---|
| Sensors and certified hardware | ONYX ecoCMS, ecoPITCH and ecoBLADE, connecting "15 different CMS hardware types" [S24]; Augury Halo [S2]; Tractian Class 1 Div 1 [S4]; KCF piezo at 96,000 samples per second [S5]. We have no hardware and no hardware budget |
| Field-data scale | ONYX 32,000+ turbines [S24]; Turbit 30,000+ asset-years [S26]; Augury 1.1B+ hours [S1]; GE 19,500+ assets [S13]; Clir 350+ GW [S28] (all vendor claims). We have zero field data |
| Human analysts and engineering | SKF certified analysts [S80]; Augury CAT II/III analysts [S1]; GE 24×7 monitoring centres [S13]; ONYX engineering and consultancy [S24] |
| OEM full-scope service and life extension | Siemens Gamesa covers "every aspect" of a farm, runs a Life Extension program and is multibrand [S83]; Vestas offers "lifetime management" [S84]. For turbofans, risk-transfer contracts paid per flying hour [S81][S82] |
| Indian O&M scale and presence | INOX Green 11 GW of wind O&M [S85]; ONYX Bengaluru office [S25]; IBM Maximo Renewables with a Gujarat-headquartered customer [S30]; Infinite Uptime entities in Pune and Mumbai [S8] |
| Enterprise breadth | IBM Maximo Renewables plus Manage [S29]; Octave Attune EAM and APM [S56]; AVEVA PI [S14] |
| Paid customer backtests | Turbit already sells one on major-OEM exports [S27] |
| Gated retraining as a novelty | AWS SiteWise has scheduled retraining with automatic or manual promotion and visible metrics [S35] |
| RUL with intervals in wind | Public wind data carry anomaly labels, not run-to-failure RUL labels [S74][S76]. Our headline capability does not transfer (judge and adversarial review) |
| Accuracy-based positioning | We found no independent benchmark comparing these vendors (**UNVERIFIED**: WebSearch was unavailable, so this is absence of evidence, not evidence of absence). Our in-class wind evidence would rest on n = 11 events (±23-25 points) [S75] |

### 8.4 Positioning statement the evidence supports today

> "An auditable, abstaining maintenance-decision layer that turns condition signals into reviewed, evidence-carrying work requests, and publishes its own evaluation, including where simple rules beat it. Demonstrated so far only on simulated and synthetic data."

Avoid: "predictive maintenance platform", "first", "only", "AI that prevents failures", any comparative accuracy claim, and any wording that implies field validation or a working CMMS integration.

---

## 9. Claims we must NOT make about competitors

1. **"No competitor offers re-derivable decisions, calibration or false-alarm reporting."** We only know that the marketing pages opened in this session do not document them [S1]-[S31].
2. **"We are more accurate than X", or any number for X's accuracy.** We found no independent benchmark (**UNVERIFIED**; WebSearch was unavailable), and we have no comparable accuracy result of our own. Vendor figures such as "99.97%" [S7] are undefined vendor claims.
3. **"Competitors have no audit trail."** eMaint documents audit trails and e-signatures [S51]; Fiix's pricing page lists an audit trail as a feature (excluded from its Free plan) [S40]; Limble advertises "instant digital audit records" [S48].
4. **"Wind specialists are not in India."** ONYX lists a Bengaluru office [S25]. IBM Maximo Renewables has a Gujarat-headquartered customer [S30], although that case describes solar and hybrid O&M, not wind turbines.
5. **"KP Group uses IBM for wind-turbine monitoring."** The case study describes solar and hybrid plant O&M [S30].
6. **"INOX Green uses machine learning" or any description of its method.** The page lists "Predictive Maintenance" and describes no method [S85].
7. **"Turbit's backtest is free", or "our free backtest is unique".** Turbit's is paid, at a "small one-time price" [S27]; offering ours free differs only on price.
8. **"ONYX or Turbit cannot use SCADA" or "they only use vibration".** ONYX's page names vibration and oil and does not mention SCADA [S24]; Turbit works on SCADA [S27]. Say only what each page shows.
9. **Restating a vendor's fleet, accuracy, ROI or availability number without the label "vendor claim".** This covers ONYX 32,000+ turbines, Turbit 3,500+, INOX Green 11 GW, Clir 350+ GW, Siemens Gamesa 98% and GE $1.6B+.
10. **Using numbers that are no longer on the vendor page.** R3 quoted Senseye's "up to 50%" downtime reduction; the current page gives no quantified results [S9]. Re-check before reuse.
11. **"Amazon Lookout for Equipment or Azure Anomaly Detector is an option."** Both are discontinued or retired [S32][S36]. Equally, do not say "AWS has no predictive-maintenance service"; SiteWise anomaly detection is GA [S34].
12. **"We are the only ones with gated retraining or sensor-health checks."** AWS SiteWise [S35]; SmartSignal [S13]; Honeywell [S15].
13. **"Bosch owns Uptake" or "IFS owns Falkonry".** Bosch announced a "planned acquisition" [S23]. Falkonry's site does not mention IFS, and the deal's closing is **UNVERIFIED**.
14. **"Octave Attune EAM is the former Infor EAM."** The page says "Formerly HxGN EAM" only [S56].
15. **"Avathon sells a wind predictive-maintenance product."** No such product is named on its page [S22].
16. **"Odoo or ERPNext has predictive maintenance."** Odoo estimates the next failure from MTBF [S59]; ERPNext is time-based only [S61]. Equally, do not say "Odoo has no free API": self-hosted Community has the JSON-2 route; only Odoo Online restricts it to Custom plans [S57][S60].
17. **"ThingsBoard is Apache-licensed."** From v4.4.0 it is BUSL 1.1 with device caps [S66].
18. **Any competitor price we have not seen published.** Published prices we may quote, as vendor-published: MaintainX $0, $20 and $65 per user per month billed annually [S46], and the KCF $199 trial [S5]. Tractian, Limble and eMaint publish none [S4][S49][S52].
19. **"OEM service contracts do not monitor condition."** Siemens Gamesa cites "advanced analytics and remote diagnostics" [S83]; Rolls-Royce and GE include health monitoring and remote diagnostics [S81][S82].
20. **Any statement about a competitor's customers, revenue, India market share or adoption that is not on a page we opened.** No market-size or share figures appear in this document, deliberately.

---

## 10. Gaps and UNVERIFIED items

- **WebSearch was unavailable.** Wind-specific competitors may be missing: other Indian SCADA analytics firms, OEM digital-service products in India, Bachmann, Romax, Greenbyte as a separate product, and others. Whether India-specific SCADA analytics for ageing turbines is already saturated is **UNVERIFIED**. The judge listed this as a condition that could change the vertical choice.
- **SAP APM** pages returned HTTP 403, and SAP account and sandbox write access is unverified.
- **GE SmartSignal connectors** (APM Connect, Maximo and SAP adapters) and **IBM MAS on OpenShift** come from R3 and were not re-opened.
- **eMaint API mechanism** and the **ERPNext and NASA ProgPy licences** were not re-opened, or are unverified.
- **Suzlon O&M scope**, the **Indian fleet model mix and gearless share**, and **who controls SCADA exports and work orders** for Indian turbines are all unverified.
- **No Indian or wind-sector survey** of maintenance tooling (spreadsheets, CMMS, PM intervals) was found.
- **OPEN: Indian OEM and SCADA-analytics alternatives have NOT been verified** (`ADVERSARIAL_REVIEW.md` buyer-10; `KNOWN_LIMITATIONS.md` C2).
  - Not verified: the service scope and SCADA-access terms of Suzlon, Envision, INOX Wind or any other OEM servicing Indian turbines; INOX Green's SCADA-access terms (only its own service list was read [S85]); and whether the OEM full-service contract holds the SCADA exports and the work orders.
  - Not verified: Indian SCADA-analytics vendors for mid-life turbines.
  - Not done: a buyer-side comparison (cost, data access, contractual fit) against the OEM contract and Turbit's backtest.
  - These need sourced web research, which was not possible in the Phase 9 update either (no WebSearch). **No competitor fact was added in that update.**
- **Product-branch capabilities: updated in Phase 9 against the code** (2026-10-18). Statements about SentinelLoop in sections 1, 3, 5, 6.2, 8.1 and 8.2 now cite the code, tests and evidence:
  - work-order workflow: `app/workorders.py`;
  - scheduler: `app/scheduler.py`;
  - REST API: `app/api.py`;
  - audit chain: `app/auditlog.py`, `tests/test_app_foundation.py`;
  - Odoo connector: `app/integration.py`, `tests/test_app_integration.py`;
  - wind model: `app/nbm.py`, `product/evidence/wind_synthetic/w3.md`;
  - assessment provenance and re-derivation: `app/health.py`, `TECHNICAL_DEBT.md` F11;
  - scheduling results: `SCHEDULING_EVALUATION.md` (S2), `product/evidence/scheduling_v2/summary.md`;
  - promotion gate and abstention (competition pipeline): `CLAIM_EVIDENCE_MATRIX.md` P4, P7; `docs/EXPERIMENT_RESULTS.md` E3, E4;
  - abstention on the platform: `app/states.py` (DATA_QUALITY_FAILURE uses no prediction), `app/decision.py` (instrument-check and desk-review orders), `KNOWN_LIMITATIONS.md` M1.

  None of these has been field validated.
- **R3 vendors not re-checked and therefore omitted:** Nanoprecise, Presage Insights, SKF Axios, Tata Elxsi, Azure IoT Operations, Maximo Monitor. See R3 for what was found earlier.

---

## Sources

All web sources were accessed on **2026-10-18** and opened in this session. Access method: WebFetch unless noted; "pdftotext" means WebFetch saved the PDF and the text was read locally; "curl" means a local HTTP request and file inspection. Every capability statement drawn from a vendor's own page is a vendor claim.

**Commercial PdM / APM (general industrial)**
- [S1] Augury home page: https://www.augury.com/ (accessed 2026-10-18)
- [S2] Augury Halo R4000 page: http://www.augury.com/?p=7721 (accessed 2026-10-18)
- [S3] Augury partners page: https://www.augury.com/partners/ (accessed 2026-10-18)
- [S4] Tractian plans page: https://tractian.com/en/plans (accessed 2026-10-18)
- [S5] KCF Technologies SMARTsensing suite: https://kcftech.com/solutions/smartsensing-suite/ (accessed 2026-10-18)
- [S6] Petasense home page: https://petasense.com/ (accessed 2026-10-18)
- [S7] Infinite Uptime home page: https://infinite-uptime.com (accessed 2026-10-18)
- [S8] Infinite Uptime About Us: https://www.infinite-uptime.com/about-us (accessed 2026-10-18)
- [S9] Siemens Senseye "how it works": https://www.siemens.com/us/en/products/services/digital-enterprise-services/analytics-artificial-intelligence-services/predictive-services/senseye-predictive-maintenance/how-it-works.html (accessed 2026-10-18)
- [S10] Siemens UK news, Senseye acquisition: https://news.siemens.co.uk/news/siemens-acquires-senseye-predictive-maintenance-and-asset-intelligence-for-industrial-companies (accessed 2026-10-18)
- [S11] Aspen Mtell product page: https://www.aspentech.com/en/products/apm/aspen-mtell (accessed 2026-10-18)
- [S12] Emerson news, AspenTech acquisition completed: https://www.emerson.com/en-us/news/2025/emerson-completes-acquisition-of-remaining-outstanding-shares-of-aspentech (accessed 2026-10-18)
- [S13] GE Vernova SmartSignal brochure (PDF; pdftotext): https://gevernova.com/software/sites/default/files/2024-10/brochure-ai-powered-predictive-analytics-smartsignal.pdf (accessed 2026-10-18)
- [S14] AVEVA Predictive Analytics: https://www.aveva.com/en/products/predictive-analytics/ (accessed 2026-10-18)
- [S15] Honeywell Forge APM product information note (PDF; pdftotext; undated): https://process.honeywell.com/content/dam/process/en/documents/document-lists/PINForgeAPMR1-v1.pdf (accessed 2026-10-18)
- [S16] IBM Maximo predictive model templates: https://www.ibm.com/docs/SSC5CS/com.ibm.pm.doc/config/c_predictive_model_templates.html (accessed 2026-10-18)
- [S17] IBM Maximo Health 9.1 what's new: https://www.ibm.com/docs/SS7PRM_cd/com.ibm.ah.doc/overview/whats_new_91.html (accessed 2026-10-18)
- [S18] C3 AI Reliability: https://c3.ai/products/c3-ai-reliability/ (accessed 2026-10-18)
- [S19] Falkonry home page: https://falkonry.com/ (accessed 2026-10-18)
- [S20] SAP APM: https://www.sap.com/hk/products/scm/apm.html and https://www.sap.com/products/scm/apm.html (both returned HTTP 403; no claim rests on them) (accessed 2026-10-18)
- [S21] Altizon home page: https://www.altizon.com/ (accessed 2026-10-18)
- [S22] Avathon home page: https://avathon.com/ (accessed 2026-10-18)
- [S23] Uptake home page: https://uptake.com/ (accessed 2026-10-18)

**Wind and renewables**
- [S24] ONYX Insight home page: https://www.onyxinsight.com/ (accessed 2026-10-18)
- [S25] ONYX Insight locations: https://onyxinsight.com/company/our-locations/ (accessed 2026-10-18)
- [S26] Turbit home page: https://www.turbit.com/ (accessed 2026-10-18)
- [S27] Turbit backtest page: https://www.turbit.com/backtest (accessed 2026-10-18)
- [S28] Clir home page: https://www.clir.eco/ (accessed 2026-10-18)
- [S29] IBM Maximo Renewables: https://www.ibm.com/products/maximo/renewables (accessed 2026-10-18)
- [S30] IBM case study, KP Group: https://www.ibm.com/case-studies/kp-group (accessed 2026-10-18)
- [S31] Power Factors home page: https://www.powerfactors.com/ (accessed 2026-10-18)

**Cloud building blocks**
- [S32] AWS blog, Lookout for Equipment end of support: https://aws.amazon.com/blogs/machine-learning/preserve-access-and-explore-alternatives-for-amazon-lookout-for-equipment/ (accessed 2026-10-18)
- [S33] AWS blog, Amazon Monitron: https://aws.amazon.com/blogs/machine-learning/maintain-access-and-consider-alternatives-for-amazon-monitron (accessed 2026-10-18)
- [S34] AWS What's New, SiteWise multivariate anomaly detection GA: https://aws.amazon.com/about-aws/whats-new/2025/07/aws-iot-sitewise-multivariate-anomaly-detection/ (accessed 2026-10-18)
- [S35] AWS What's New, SiteWise retraining: https://aws.amazon.com/about-aws/whats-new/2025/09/aws-iot-sitewise-retraining-anomaly-detection-models (accessed 2026-10-18)
- [S36] Microsoft Learn, Azure AI Anomaly Detector what's new: https://learn.microsoft.com/en-in/azure/ai-services/anomaly-detector/whats-new (accessed 2026-10-18)
- [S37] Microsoft Learn, Fabric RTI anomaly detection: https://learn.microsoft.com/en-us/fabric/real-time-intelligence/anomaly-detection (accessed 2026-10-18)

**CMMS / EAM**
- [S38] Fiix home page: https://fiixsoftware.com/ (accessed 2026-10-18)
- [S39] Fiix API guide: https://fiixlabs.github.io/api-documentation/guide.html (accessed 2026-10-18)
- [S40] Fiix pricing (vendor pricing page): https://fiixsoftware.com/pricing/ (accessed 2026-10-18)
- [S41] BINDT news, Fiix Asset Risk Predictor (trade press): https://www.bindt.org/News/december-2023/fiix-ai-software/ (accessed 2026-10-18)
- [S42] UpKeep developer documentation: https://developers.onupkeep.com/ (accessed 2026-10-18; first 100,000 characters read)
- [S43] UpKeep Edge CMMS integration: https://upkeep.com/product/edge-iiot/capabilities/cmms-integration (accessed 2026-10-18)
- [S44] MaintainX home page: https://www.getmaintainx.com/ (accessed 2026-10-18)
- [S45] MaintainX help, automations: https://help.getmaintainx.com/about-automations (accessed 2026-10-18)
- [S46] MaintainX pricing (vendor pricing page): https://www.getmaintainx.com/pricing (accessed 2026-10-18)
- [S47] MaintainX public OpenAPI (curl; about 1.39 MB; grepped locally): https://api.getmaintainx.com/v1/openapi.json (accessed 2026-10-18)
- [S48] Limble home page: https://limble.com/ (accessed 2026-10-18)
- [S49] Limble pricing (vendor pricing page): https://limble.com/pricing (accessed 2026-10-18)
- [S50] Limble public OpenAPI (curl; grepped locally): https://api.limblecmms.com/openapi.json (accessed 2026-10-18)
- [S51] Fluke eMaint CMMS page (Spanish-language US page): https://www.fluke.com/es-us/productos/software-de-fluke/emaint-cmms (accessed 2026-10-18)
- [S52] eMaint pricing (vendor pricing page): https://www.emaint.com/pricing/ (accessed 2026-10-18)
- [S53] IBM support, Maximo meter readings via REST: https://www.ibm.com/support/pages/maximo-adding-meter-readings-using-rest-api (accessed 2026-10-18)
- [S54] IBM Maximo REST API documentation, authentication: https://ibm-maximo-dev.github.io/maximo-restapi-documentation/authentication/auth (accessed 2026-10-18)
- [S55] SAP API sandbox, API_MAINTNOTIFICATION metadata (curl: HTTP 401, "Failed to resolve API Key variable request.header.apikey"): https://sandbox.api.sap.com/s4hanacloud/sap/opu/odata/sap/API_MAINTNOTIFICATION/$metadata (accessed 2026-10-18)
- [S56] Octave Attune EAM: https://www.octave.com/eam (accessed 2026-10-18)
- [S57] Odoo 19 external API documentation: https://www.odoo.com/documentation/19.0/developer/reference/external_api.html (accessed 2026-10-18; read in two parts)
- [S58] Odoo 19 maintenance module manifest: https://raw.githubusercontent.com/odoo/odoo/19.0/addons/maintenance/__manifest__.py (accessed 2026-10-18)
- [S59] Odoo 19 maintenance models: https://raw.githubusercontent.com/odoo/odoo/19.0/addons/maintenance/models/maintenance.py (accessed 2026-10-18)
- [S60] Odoo 19 rpc addon manifest: https://raw.githubusercontent.com/odoo/odoo/19.0/addons/rpc/__manifest__.py (accessed 2026-10-18)
- [S61] ERPNext Asset Maintenance: https://docs.frappe.io/erpnext/user/manual/en/asset-maintenance (accessed 2026-10-18)
- [S62] Frappe REST API: https://docs.frappe.io/framework/user/en/api/rest (accessed 2026-10-18)

**Open source**
- [S63] Atlas CMMS repository: https://github.com/Grashjs/cmms (accessed 2026-10-18)
- [S64] openMAINT product page: https://tecnoteca.com/en/products/openmaint (accessed 2026-10-18)
- [S65] openMAINT download and requirements: https://www.openmaint.org/en/download/latest-version (accessed 2026-10-18)
- [S66] ThingsBoard LICENSE: https://raw.githubusercontent.com/thingsboard/thingsboard/master/LICENSE (accessed 2026-10-18)
- [S67] OpenRemote repository: https://github.com/openremote/openremote (accessed 2026-10-18)
- [S68] OpenRemote LICENSE.txt: https://raw.githubusercontent.com/openremote/openremote/master/LICENSE.txt (accessed 2026-10-18; first 100,000 characters read)
- [S69] Eclipse Ditto: https://eclipse.dev/ditto/ (accessed 2026-10-18)
- [S70] NREL OpenOA repository: https://github.com/NREL/OpenOA (accessed 2026-10-18)
- [S71] RES wind-up repository: https://github.com/resgroup/wind-up (accessed 2026-10-18)
- [S72] NASA ProgPy included models: https://nasa.github.io/progpy/api_ref/progpy/IncludedModels.html (accessed 2026-10-18)
- [S73] microsoft/anomaly-detector repository: https://github.com/microsoft/anomaly-detector (accessed 2026-10-18)

**Open data (real field)**
- [S74] Zenodo, CARE to Compare v6: https://zenodo.org/records/15846963 (accessed 2026-10-18)
- [S75] arXiv 2404.10320v2, CARE to Compare paper (HTML): https://arxiv.org/html/2404.10320v2 (accessed 2026-10-18)
- [S76] Zenodo, Hill of Towie v2.1.0: https://zenodo.org/records/22662930 (accessed 2026-10-18)

**Non-software alternatives, studies and service offers**
- [S77] CFE Media / Plant Engineering, 2020 Industrial Maintenance Report, sponsored by ATS (PDF; pdftotext): https://www.advancedtech.com/wp-content/uploads/2020/03/2020-ATS_Plant-Engineering-Maintenance-Study-Results.pdf (accessed 2026-10-18)
- [S78] Thomas and Weiss (NIST), IJPHM 2021, PMC copy: https://pmc.ncbi.nlm.nih.gov/articles/PMC9890517/ (accessed 2026-10-18)
- [S79] US DOE FEMP, O&M challenges and solutions: https://www.energy.gov/femp/operations-and-maintenance-challenges-and-solutions (accessed 2026-10-18)
- [S80] SKF connected technologies services: https://us.promo.skf.com/acton/media/22336/connected-technologies-services (accessed 2026-10-18)
- [S81] Rolls-Royce TotalCare: https://www.rolls-royce.com/products-and-services/civil-aerospace/services/totalcare.aspx (accessed 2026-10-18)
- [S82] GE Aerospace TrueChoice Flight Hour: https://www.geaerospace.com/commercial/services/true-choice/flight-hour (accessed 2026-10-18)
- [S83] Siemens Gamesa wind service: https://www.siemensgamesa.com/global/en/home/products-and-services/service-wind.html (accessed 2026-10-18)
- [S84] Vestas services: https://www.vestas.com/en/services (accessed 2026-10-18)
- [S85] INOX Green home page: https://www.inoxgreen.com/ (accessed 2026-10-18)
- [S86] Strathprints 54903, May and McMillan (2013), abstract: https://strathprints.strath.ac.uk/54903/ (accessed 2026-10-18)

**Added in the fact-check pass**
- [S87] Avathon press release, rebrand from SparkCognition and India workforce plan (vendor press release, dated 11 Nov 2024): https://avathon.com/press-release/avathon-aims-to-triple-workforce-in-india-within-24-months/ (accessed 2026-10-18)
- [S88] UL Standards, UL 4143 product page (standards body; title and scope only): https://www.shopulstandards.com/ProductDetail.aspx?productId=UL4143 (accessed 2026-10-18)

**Attempted without result**
- WebSearch, one query ("wind turbine SCADA analytics predictive maintenance India owner operators software"): refused because the shared per-turn search budget was exhausted. No workaround was used.
- Fact-check pass, 2026-10-18: WebSearch ("SparkCognition rebrands as Avathon") refused for the same reason; https://avathon.com/about/ returned HTTP 404; https://www.sparkcognition.com/ failed with an expired certificate; https://www.shopulstandards.com/ProductDetail.aspx?productId=UL4143_1_S_20210827 did not show UL 4143. No claim rests on these.

**Local files (not web sources)**
- `product/research/R3_competitive_landscape.md`; `product/research/R5_integration_standards.md`
- `product/research/V_judge_decision.md`; `product/research/V_adversarial_review_wind_choice.md`
- `product/CLAIM_EVIDENCE_MATRIX.md`; `product/PRODUCT_STATUS.md`
- `product/evidence/scheduling/summary.md`; `product/evidence/scheduling/tuned_baselines.md`; `product/evidence/scheduling/downtime_sensitivity.md`
- `product/experiments/s1c_tuned_baselines.py`; `src/sentinelloop/app/sim.py` (lines 64-67, 214, 413); `src/sentinelloop/app/adapters/wind.py` (module docstring)
- `git log` on branch `product/platform` (12 commits, read 2026-10-18)
- Phase 9 update:
  - code: `src/sentinelloop/app/integration.py`, `auditlog.py`, `health.py`, `decision.py`, `nbm.py`, `states.py`;
  - tests: `tests/test_app_integration.py`, `tests/test_app_foundation.py`;
  - evidence: `product/evidence/wind_synthetic/w2.md`, `w3.md`, `product/evidence/g0/PREREGISTRATION.md` §10, §11, `product/evidence/scheduling_v2/summary.md` (S2), `docs/EXPERIMENT_RESULTS.md` (E3, E4), `submission/CLAIM_EVIDENCE_MATRIX.md` C13, C14;
  - documents: `product/KNOWN_LIMITATIONS.md`, `product/DECISION_LOG.md` PD-10, PD-20, PD-22, PD-27, `product/ADVERSARIAL_REVIEW.md`, `product/evidence/adversarial/review_full.md` (buyer-7, buyer-10), `product/SCHEDULING_EVALUATION.md` (S2), `product/TECHNICAL_DEBT.md` B2, F11, `product/PRODUCT_REQUIREMENTS.md` FR-H3.
- Wilson intervals computed locally with Python on 2026-10-18 (n = 11: half-width 0.234-0.254; n = 44: 0.133-0.142)
