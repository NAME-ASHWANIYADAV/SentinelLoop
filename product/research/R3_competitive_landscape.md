# R3 Competitive Landscape: SentinelLoop

Research stream R3. Written 2026-10-18. Every URL below was opened in this session with WebFetch on 2026-10-18, or, for three PDFs, fetched by WebFetch and read locally with `pdftotext`. Search-result snippets that were not followed up by opening the page are marked **UNVERIFIED**. Vendor statements are labelled **vendor claim**. Anything I concluded myself is labelled **analysis** and is not a sourced fact.

## Contents
0. Method, labels and data-provenance vocabulary
1. Summary of findings
2. Commercial predictive-maintenance and asset-performance-management (APM) products
3. CMMS and EAM products
4. Open-source tools
5. Data provenance: what each player trains on, compared with SentinelLoop
6. The incumbent non-software alternatives
7. Features the market already treats as standard
8. Where a small team could be different, and where it cannot compete
9. Gaps and unverified items
10. Sources

---

## 0. Method, labels and data-provenance vocabulary

- **Search method.** WebSearch to find candidate pages, then WebFetch on the vendor's own page wherever one loaded. Where the vendor page failed (HTTP 403/404/410, empty render, or a sign-in wall), I used a trade-press or primary-filing page instead and say so. No prices or market shares are given unless the vendor publishes them.
- **Labels.** *Vendor claim*: a statement on a vendor's own page or press release, not checked independently. *UNVERIFIED*: seen only in a search snippet or secondary summary, or not found. *Analysis*: my own reasoning.
- **Data-provenance vocabulary** (used throughout and in section 5):
  - **Real field data**: recorded from equipment in normal service at a customer site.
  - **Real laboratory data**: recorded from physical test rigs run under controlled conditions, often accelerated to failure (for example the IMS and FEMTO bearing sets).
  - **Simulated data**: produced by a physics or thermodynamic simulator (for example NASA C-MAPSS, which is all SentinelLoop has ever used).
  - **Synthetic data**: artificially generated or perturbed data, including faults injected into otherwise clean data (for example SentinelLoop's stress-test corruptions).

---

## 1. Summary of findings

1. **The core analytics SentinelLoop offers are standard in commercial products.** Vendors already document anomaly detection against learned normal behaviour, time-to-failure or remaining useful life (RUL), sensor-health checks and automatic work orders: Siemens Senseye, GE Vernova SmartSignal, AVEVA Predictive Analytics, Honeywell Forge APM, IBM Maximo Predict, SAP APM, Aspen Mtell, C3 AI Reliability, Falkonry, AWS IoT SiteWise and Microsoft Fabric (sections 2 and 7).
2. **Gated retraining is no longer unusual either.** AWS IoT SiteWise added scheduled retraining in September 2025, with automatic or manual promotion of new model versions and visible precision, recall and AUC. GE SmartSignal monitors six data pathologies and repairs bad sensor data. These overlap SentinelLoop's input-quality monitor and its promotion gate.
3. **Three products have been retired or closed to new customers, and three companies have changed hands.**
   - Retired or closed: Amazon Lookout for Equipment (support ended 7 Oct 2026; closed to new customers 7 Oct 2025), Azure AI Anomaly Detector (retired 1 Oct 2026) and Amazon Monitron (closed to new customers 31 Oct 2024).
   - Ownership changes: Autodesk closed its MaintainX acquisition on 3 Aug 2026. Hexagon's software unit spun off as Octave, and HxGN EAM is now Octave Attune EAM. Emerson has owned all of AspenTech since 12 Mar 2025.
   - Pending: Bosch announced a planned acquisition of Uptake on 19 Mar 2026.
4. **The strongest competitors bundle three things a student team cannot supply:** their own certified sensors, large stores of field data, and human analysts. All three are vendor claims: Augury reports 1.1B+ machine hours, SmartSignal reports data from 19,500+ assets and 370+ digital-twin blueprints, and SKF, KCF, Augury and GE run analyst teams.
5. **The incumbent alternative is still mostly no predictive software at all.** In the 2020 Plant Engineering study (n=171, US-centred, sponsored by a maintenance-services firm), 76% of plants used preventive maintenance and 60% run-to-failure. For tracking work, 50% used a CMMS, 47% spreadsheets and 46% paper. The average plant outsourced 20% of its maintenance, and 36% of plants that outsource gave an agreement with the manufacturer or supplier as a reason. For turbofans, the only asset SentinelLoop has modelled, OEM risk-transfer contracts paid per flight hour (Rolls-Royce TotalCare, GE TrueChoice) include engine health monitoring.
6. **Open-source CMMS tools have little predictive capability, but their licences shape what can be built on them.**
   - Odoo Maintenance (LGPL-3) estimates the next failure only from mean time between failures (MTBF). Atlas CMMS (AGPL-3.0) does not mention meters or IoT. openMAINT (AGPL) keeps its mobile app proprietary.
   - ThingsBoard changed licence from version 4.4: it is now Business Source License 1.1, with free production use capped at 100 devices on one server for commercial use.
   - Odoo's hosted plans offer the external API only on Custom pricing plans. The self-hosted code does expose XML-RPC and JSON-RPC routes.
7. **Possible differentiation (analysis; none of it validated with a customer):** an auditable, re-derivable decision layer with published calibration and explicit escalation, sitting between existing condition-monitoring outputs and a CMMS, and shipped as a free add-on for open-source CMMS tools. None of the vendor pages I opened document re-derivable analytic decisions or publish interval coverage. That absence from marketing pages does not show the capability is absent from the products.

---

## 2. Commercial predictive-maintenance and APM products

Categories used: **(A)** sensor hardware with analytics and often human analysts; **(B)** software-only APM or analytics on existing historian or IoT data; **(C)** vertical fleet analytics; **(D)** cloud building blocks; **(E)** India-based or India-linked companies (A7, A8 and E1–E3).

### Compact overview

| # | Product | Cat. | Hardware needed? | Deployment (as documented) | Documented work-order / EAM link | Status note |
|---|---|---|---|---|---|---|
| A1 | Augury Machine Health | A | Yes (Halo sensors) | Installed sensors; hosting not stated | SAP PM, IBM Maximo, Infor EAM, MaintainX, Limble (partner page) | — |
| A2 | SKF Axios + SKF remote analysis | A | Yes | Cloud ML service (with AWS) | Not stated in opened source | Launched Nov 2022 |
| A3 | Tractian | A | Yes (Smart Trac Ultra) | Cellular sensors + own CMMS | SAP, IBM Maximo, NetSuite, Power BI | — |
| A4 | KCF Technologies SMARTdiagnostics | A | Yes | Gateway → cloud | PLC integration; EAM not stated | $199 trial published |
| A5 | Petasense ARO Cloud | A | Yes | Cloud | Historians, CMMS | — |
| A6 | Nanoprecise MachineDoctor | A | Yes | Cellular (e-SIM) | Not found | — |
| A7 | Infinite Uptime PlantOS | A/E | Yes, or third-party sensors | 90-day rollout; outcome-based offer | Open API and MCP | — |
| A8 | Presage Insights | A/E | Yes | Not stated | Not stated | Seed round 2025 |
| B1 | Siemens Senseye PdM | B | No (sensors optional) | Cloud; Azure | Historians, IoT, databases | Siemens-owned since 1 Jun 2022 |
| B2 | Aspen Mtell | B | No | Not stated on page | EAM/ERP; Emerson AMS vibration | Emerson-owned since 12 Mar 2025 |
| B3 | GE Vernova SmartSignal / APM | B | No | On-prem, cloud, turnkey service | APM Connect, SAP and Maximo adapters | — |
| B4 | AVEVA Predictive Analytics / PI System | B | No | Edge, on-prem, cloud (PI) | PI System | — |
| B5 | Honeywell Forge APM | B | No | On-prem or cloud | CMMS connectivity, work-order requests | — |
| B6 | IBM Maximo Health / Predict / Monitor | B | No | Red Hat OpenShift; SaaS or client-managed | Maximo Manage | Health stand-alone dropped in 9.1 |
| B7 | C3 AI Reliability | B | No | Not stated | Direct work-order creation | — |
| B8 | Falkonry (IFS) | B | No | Edge, cloud, on-prem, air-gap, sovereign | IFS EAM (planned) | IFS deal Aug 2023; closing UNVERIFIED |
| B9 | Avathon (ex-SparkCognition) | B | No | Not stated | Not stated | Renamed 11 Nov 2024 |
| B10 | SAP Asset Performance Management | B | No | Cloud on SAP BTP | Requires SAP EAM | — |
| C1 | Uptake Fleet | C | No (telematics) | Web application (inference) | Telematics connectors | Bosch acquisition planned |
| D1 | Amazon Lookout for Equipment | D | No | AWS | Back-end service | **Support ended 7 Oct 2026** |
| D2 | Amazon Monitron | D | Yes | AWS | — | **Closed to new customers 31 Oct 2024** |
| D3 | AWS IoT SiteWise anomaly detection | D | No | AWS (3 regions) | — | GA 28 Jul 2025 |
| D4 | Azure AI Anomaly Detector | D | No | Azure | — | **Retired 1 Oct 2026** |
| D5 | Microsoft Fabric RTI anomaly detection | D | No | Fabric | Activator / eventstreams | **Preview** |
| D6 | Azure IoT Operations | D | No | Arc-enabled Kubernetes at the edge | Event Hubs, Fabric | Data plane only |
| E1 | Altizon DFX | E | No | Not stated | PLCs, sensors, ERP | — |
| E2 | Tata Elxsi smart-manufacturing platform | E | Not stated | Not stated | ERP, MES (Tether Factory) | Interview only |

Detail per product follows.

### A1. Augury: Machine Health (and Process Health)
- **Category:** A, sensor-based machine-health monitoring sold with AI and reliability experts. The site's umbrella brand is an "Industrial AI Workforce" of role-based agents, one of which is a Reliability Agent.
- **What it does (own site):** Machine Health has sub-offerings for critical, hazardous, ultra-low-RPM and supporting equipment, plus an Auguscope product. Process Health is a separate process-optimisation product.
- **Assets and industries:** Pumps, motors, compressors, bearings, fans and blowers, gearboxes, chillers, conveyors, extruders, mills, mixers and seamers. Industries: food and beverage, CPG, chemicals, cement and building materials, metals and mining, pulp and paper, glass, pharma, plastics, steel, oil and gas, energy and commercial services.
- **Data inputs:** The Halo R4000 sensor measures tri-axial vibration (±60 g), environmental and surface temperature, and tri-axial magnetic flux, fusing them at millisecond resolution. It connects over BLE and NFC. A Cassia X2000 gateway takes up to 64 sensors and uplinks over Wi-Fi, Ethernet/PoE or cellular. The sensor runs edge AI, adjusts sampling to the machine's schedule and covers slow, intermittent and variable-speed equipment. The battery is field-replaceable and rated up to 5 years (vendor claim).
- **Deployment:** Physical sensors installed on site, described as anything from self-serve to white-glove. Augury services sensors and ships replacements. Cloud hosting is not described on the pages opened (UNVERIFIED).
- **Integrations (partners page):** SAP PM (diagnostics sent into PM workflows), IBM Maximo, Infor EAM, MaintainX, Limble, Microsoft Azure, PTC and AVEVA. OEM partners include Bently Nevada, Baker Hughes, Schneider Electric, Trane and Carrier. Search snippets described the mechanism as webhooks into the CMMS API with status flowing back, but the help article returned 404 (UNVERIFIED).
- **Vendor claims:** 1.1B+ hours of real machine readings; 170+ manufacturers in 40+ countries; 310% ROI in a Forrester TEI study; named a Leader in the Verdantix 2025 Green Quadrant for Industrial AI Analytics.
- **Documented limitations:** None stated. The product depends on Augury's own hardware.
- Sources: https://www.augury.com/ ; http://www.augury.com/?p=7721 (Halo R4000 page) ; https://www.augury.com/partners/

### A2. SKF: Axios, and SKF condition-monitoring services
- **Category:** A, bearing OEM with wireless sensors, a cloud ML service and analyst services.
- **SKF Axios (trade news of the Nov 2022 launch):**
  - A fully automated condition-monitoring solution made of sensors, gateways and a machine-learning service, built with AWS. It detects anomalies and sends push notifications.
  - It is aimed at manufacturers that want affordable wireless monitoring on more machines.
  - SKF says its vibration analysts and engineers remain integral to the offer.
  - The opened source does not say which quantities the sensors measure. Vibration and temperature appear only in search snippets (UNVERIFIED). The SKF product page rendered almost empty.
- **SKF services page:**
  - A *Remote Analysis* package delivered by certified vibration analysts: monthly analysis and diagnostic reports, weekly and daily alarm reviews, database enhancements and alarm adjustments.
  - Mechanical services: ultrasound, thermography, balancing, alignment, motion amplification and oil sampling. Engineering services include root-cause failure analysis.
  - Vendor claims: more than $200M of unplanned downtime saved for hundreds of customers, and ROI within a few months.
- **Relevance:** SKF is the clearest example of a vibration-analysis service contract, discussed in section 6.
- Sources: https://www.bindt.org/News/november-2022/skf-announces-launch-of-skf-axios-powered-by-aws/ ; https://us.promo.skf.com/acton/media/22336/connected-technologies-services

### A3. Tractian
- **Category:** A, wireless sensors plus the vendor's own CMMS.
- **What it does (plans page):**
  - Condition monitoring with vibration analysis and reliability/root-cause analysis.
  - A CMMS with a mobile app, work orders, parts inventory and preventive maintenance.
  - Electrical and energy monitoring (current and voltage) and custom dashboards.
  - AI failure diagnostics. Alarms state the problem, its severity and the recommended next steps.
- **Hardware (spec sheet linked from the plans page):** Smart Trac Ultra. 4G/LTE cellular; range up to 330 ft with obstacles and 3,300 ft line of sight; battery 3–5 years; −40°F to 250°F; Class 1 Div 1 (ATEX, IECEx, NFPA); IP69K. The plans page does not list the measured quantities. Vibration, temperature, runtime and RPM come from a search summary (UNVERIFIED).
- **Integrations:** Oracle NetSuite, SAP, Power BI and IBM Maximo.
- **Prices:** Not published. The page offers a price-estimate tool.
- Source: https://tractian.com/en/plans

### A4. KCF Technologies: SMARTsensing / SMARTdiagnostics
- **Category:** A, sensors with a cloud analytics platform and services.
- **Hardware:**
  - Wireless high-definition vibration sensor that captures full-spectrum data as often as every minute, powered by an off-the-shelf CR123A battery.
  - IoT HUB with 7 synchronous channels, for third-party, IEPE, legacy and OEM sensors and for PLC-triggered capture.
  - Piezo sensing at 96,000 samples per second, down to 2 RPM (vendor claim).
  - Motor current and electrical signature analysis (MCSA/ESA).
  - A base-station gateway uploads to the cloud. A hazardous-location base station uses KCF's Dart Wireless mesh.
- **Software:** SMARTdiagnostics. Listed fault classes: bearing, gear, belt, chain, coupling, drive, pump, imbalance, lubrication, overheating, looseness and resonance. Models are said to be trained on billions of industrial data points (vendor claim).
- **Services:** SENTRYsolutions appears in the navigation, but the page does not describe its scope. Installation is offered.
- **Industries:** Automotive, chemicals, food and beverage, forest products, metals, mining, oil and gas, utilities and wastewater.
- **Published price:** A $199 trial covering 48 sensors and a base station for 30 days (vendor-published).
- Source: https://kcftech.com/solutions/smartsensing-suite/

### A5. Petasense
- **Category:** A.
- **Hardware:** Vibration Mote; a transmitter line with sensors for VFD-driven assets (VSX), vibration, temperature, ultrasound, pressure and current; wired options.
- **Software:** ARO Cloud (Asset Reliability & Optimization), with digital twins, failure-mode detection, alerts and dashboards on web and mobile.
- **Integrations:** Process historians and CMMS.
- **Industries:** Power generation, pharma, oil and gas, data centres and critical facilities.
- Claims of predicting failures before they happen are vendor claims. A Bangalore office was mentioned only in a 2018 search snippet (UNVERIFIED).
- Source: https://petasense.com/

### A6. Nanoprecise: MachineDoctor
- **Category:** A.
- **Press release, 7 Sep 2023, Edmonton dateline:** MachineDoctor LUX is a "6-in-1", e-SIM cellular, light-harvesting sensor with a lithium-ion battery. Its lifespan is given as up to 10 years (vendor claim). Zone 0 certification was then still pending. The release mentions an energy-efficiency and health analytics platform, and makes no RUL claim.
- **Sensing modalities:** The six modalities (vibration, acoustic emission, temperature, humidity, RPM, magnetic flux) appeared only in a search snippet of the vendor site, which rendered empty (UNVERIFIED).
- Source: https://www.newswire.ca/news-releases/nanoprecise-announces-world-s-first-light-energy-harvesting-predictive-maintenance-sensor-808894693.html

### A7. Infinite Uptime: PlantOS (Indian-origin)
- **Company:** Founded 2016 per its About page; TechCrunch says December 2015. Headquartered in Alpharetta, Georgia, USA, with its Asia-Pacific office in Pune and Indian entities registered in Pune and Mumbai. Also has offices in Dubai and Australia. TechCrunch (22 May 2023) reported a Pune base and an $18.85M Series B3 extension led by Tiger Global, with named clients including Vedanta, JSW Steel, Hyundai, Ceat and Adani.
- **What it does (own site):**
  - A prescriptive AI platform for heavy manufacturing, sold as "Production Outcomes as a Service".
  - It combines vibration, temperature, PLC/DCS, historian, inspection and oil-analysis data.
  - Each prescription names the asset, the fault, the action and the severity. Operators validate prescriptions digitally, and that feeds back into the models.
  - Hardware: wired piezo/MEMS sensors and wireless MEMS tags. It also ingests existing third-party sensors.
- **Integrations:** Open API and MCP.
- **Industries:** Steel, cement, metals and mining, pulp and paper, chemicals and fertiliser, tyre and rubber, food and beverage, pharma, and energy/oil and gas.
- **Deployment:** A 90-day rollout plan, with a first prescription in about two weeks (vendor claim).
- **Vendor claims (inconsistent across the site):** about 1,000 plants (946 in the FAQ), 28 countries (26 in the FAQ), 99.97% "user-validated" accuracy and 167,837 downtime hours saved.
- No prices are published.
- Sources: https://www.infinite-uptime.com/about-us ; https://infinite-uptime.com ; https://techcrunch.com/2023/05/22/tiger-global-india-infinite-uptime-funding/

### A8. Presage Insights (India)
- **Funding:** ₹5.6 crore seed round led by YourNest, reported 18 Sep 2025. Mohali, Punjab.
- **What it does:** IoT sensors with AI analytics and machine digital twins. It is positioned as affordable Industry 4.0 for small and mid-size plants.
- **Clients:** Adani and Abbott Healthcare.
- **Vendor claims:** up to 40% less unplanned downtime; ₹50–75 lakh saved per plant per year.
- **Unverified details:** Sensor types, protocols (MQTT/Modbus) and failure-mode counts appeared only in directory snippets (UNVERIFIED). Deployment status is inconsistent within the article ("deployed" versus "piloted").
- Source: https://www.industrialautomationindia.in/news/presage-insights-raises-5-6-crore-predictive-maintenance-india

### B1. Siemens: Senseye Predictive Maintenance
- **Category:** B, cloud software-as-a-service.
- **Ownership:** Siemens has owned Senseye outright since 1 Jun 2022 (announced 8 Jun 2022). Senseye is headquartered in Southampton, UK.
- **What it does (own page):**
  - Uses existing machine-condition and operations data from historians, IoT middleware and databases. No new hardware is needed; sensors are optional.
  - Combines AI with human expertise to model machine and maintainer behaviour, forecast failures, estimate RUL, highlight risks and rank priorities.
- **Assets and industries:** Any asset type across sites. Named industries include automotive, process and discrete manufacturing, with cases in steel, dairy, pulp and paper, food and beverage, aluminium and pharma.
- **Integrations:** Historians, IoT platforms and databases. Search snippets also mention an Azure Marketplace listing and an Azure-powered Industrial Copilot package (UNVERIFIED; the trade article returned 403).
- **Documented limitations:** Assets have to be onboarded and data connected first.
- **Vendor claims:** up to 50% less unplanned downtime and up to 30% higher maintenance-staff productivity.
- Sources: https://www.siemens.com/us/en/products/services/digital-enterprise-services/analytics-artificial-intelligence-services/predictive-services/senseye-predictive-maintenance/how-it-works.html ; https://news.siemens.co.uk/news/siemens-acquires-senseye-predictive-maintenance-and-asset-intelligence-for-industrial-companies

### B2. AspenTech (Emerson): Aspen Mtell
- **Category:** B.
- **Ownership:** AspenTech has been a wholly owned Emerson subsidiary since 12 Mar 2025.
- **What it does (own page):** AI failure prediction beyond plain anomaly detection, with the vendor claiming failure patterns can be detected up to 90 days ahead. Embedded FMEA suggests corrective actions. Industry asset templates and sensor groups are provided.
- **Integrations:** Integrates with EAM and ERP workflows and with Emerson AMS vibration monitoring.
- **Industries:** Metals and mining; oil and gas, upstream and refining (YPF and OCP Ecuador cases).
- **Deployment:** Not stated on the page.
- **Vendor claims:** 30% lower maintenance cost and 20% higher uptime.
- **Unverified mechanism:** Search snippets from ARC and a partner describe "anomaly agents" and "failure agents" that learn from confirmed inspections and post failure-coded work orders into the EAM. I did not open those pages (UNVERIFIED).
- Sources: https://www.aspentech.com/en/products/apm/aspen-mtell ; https://www.emerson.com/en-us/news/2025/emerson-completes-acquisition-of-remaining-outstanding-shares-of-aspentech

### B3. GE Vernova: SmartSignal and APM
- **Category:** B.
- **What SmartSignal does (brochure):**
  - Anomaly detection compares live readings with each machine's predicted normal values (load, temperatures, pressures, vibration, ambient conditions) rather than with fixed thresholds.
  - Diagnostics match anomalies against precursor signatures drawn from OEM-agnostic data on 19,500+ assets (vendor claim).
  - Time-to-action forecasting estimates when an alarm limit will be reached.
  - Sensor Health Monitoring covers six data pathologies, and Virtual Signal Repair fills in corrupted data.
  - Out-of-the-box digital-twin blueprints number 370+ (vendor claim), covering rotating, fixed, electrical and mobile assets.
- **Deployment:** On-prem software, cloud subscription, a turnkey service, or as a pillar of GE Vernova APM. GE Industrial Managed Services offers 24×7 monitoring centres.
- **Vendor claims:** $1.6B+ of losses avoided, $500K average saving per case and a 3.4-month average ROI.
- **Integrations (APM documentation):** APM Connect, Maximo Adapters and SAP Adapters.
- Sources: https://gevernova.com/software/sites/default/files/2024-10/brochure-ai-powered-predictive-analytics-smartsignal.pdf ; https://gevernova.com/software/resources/brochure/ai-powered-predictive-analytics-smartsignal ; https://www.gevernova.com/software/documentation/cloud-apm/usw/apm-connect-first-time-deployment.html

### B4. AVEVA: Predictive Analytics and PI System
- **Category:** B, analytics, with PI System as the data infrastructure underneath.
- **Predictive Analytics (own page):**
  - Alerts when an asset departs from normal operation, with weeks or months of warning claimed.
  - Time-to-failure forecasts; fault diagnostics with per-sensor contribution; prescriptive actions from the AVEVA Asset Library (vendor claim of 22,000+ hours of experience).
  - Alert workflows and case management; a no-code environment and templates; custom Python models can be brought in.
  - Cases: PETRONAS, Ontario Power Generation, SCG Chemicals and Votorantim, all with vendor-claimed savings.
- **PI System (own page):**
  - PI Server stores and contextualises real-time data and runs analytics and notifications.
  - Connectivity through "hundreds" of connectors (PI Interfaces, PI Connectors, AVEVA Adapters).
  - Hybrid deployment across edge, on-prem and the CONNECT cloud, with open APIs and an SDK.
- Sources: https://www.aveva.com/en/products/predictive-analytics/ ; https://www.aveva.com/en/products/aveva-pi-system/

### B5. Honeywell: Forge Asset Performance Management
- **Category:** B.
- **What it does (product information note, date not shown):**
  - Real-time machinery analytics that detect developing health problems and predict time to failure.
  - First-principles thermodynamic performance models for pumps, compressors, turbines and heat exchangers, alongside pattern-recognition and ML models and fault-symptom models.
  - Automatically cleanses corrupt data before analytics run.
  - Inputs: OPC, real-time, historical and event data, plus relational data such as lab and oil analysis.
  - Outputs include prediction and RUL trending.
  - CMMS connectivity and work-order requests.
  - Extensible through Python, a Honeywell scripting language and C#.
- **Deployment:** On-prem or cloud (29 Apr 2025 Aker BP press release, covering five North Sea assets).
- Sources: https://process.honeywell.com/content/dam/process/en/documents/document-lists/PINForgeAPMR1-v1.pdf ; https://www.honeywell.com/us/en/press/2025/04/honeywell-technology-to-drive-process-automation-for-aker-bp-operations

### B6. IBM Maximo Application Suite: Health, Predict, Monitor
- **Category:** B and EAM. Maximo Manage is the EAM; see section 3.
- **Predict (predictive model templates, Maximo APM Predictive Maintenance Insights documentation):**
  - Failure probability within a prediction window, and predicted failure dates. Both need IoT sensor data, meter data and past failure history.
  - Anomaly detection and failure-contribution breakdown.
  - An end-of-life failure-probability curve built from asset retirement data.
- **Health 9.1 (what's new):**
  - Health levels, custom and condition scores, and dashboards combining Health, Predict, Monitor and Manage.
  - Work queues for data-quality problems such as a missing installation date.
  - Health stand-alone is **no longer offered**; existing users must move to Manage with Health.
- **Monitor (8.7 documentation):**
  - Dashboards; anomaly detectors for outliers, gaps and flat lines that raise alerts.
  - Requires the IoT tool, Db2 Warehouse and MongoDB.
  - Supervised detectors in offline mode may need retraining after an upgrade.
- **Deployment:** Runs on Red Hat OpenShift, either on infrastructure the customer runs or on a managed OpenShift service. Cloud Pak for Data supplies Db2 Warehouse.
- **Analysis:** This is enterprise-scale infrastructure and well beyond a small plant's IT.
- Sources: https://www.ibm.com/docs/SSC5CS/com.ibm.pm.doc/config/c_predictive_model_templates.html ; https://www.ibm.com/docs/SS7PRM_cd/com.ibm.ah.doc/overview/whats_new_91.html ; https://www.ibm.com/docs/en/SSRHPA_8.7.0/appsuite/admin/deploy_monitor.html ; https://www.ibm.com/docs/en/SSRHPA_cd/appsuite/overview/c_technical_overview.html

### B7. C3 AI Reliability
- **Category:** B.
- **What it does (own page):**
  - Inputs: sensor data, maintenance records, parts inventory, documents and diagrams, unified on the C3 Agentic AI Platform.
  - Outputs: failure predictions from time-series foundation models and ML; ranked risk alerts with key drivers; failure-mode and root-cause recommendations; work orders created directly; embedded AI search and chat.
- **Cases:** Holcim, Shell and Dow (vendor claims).
- **Vendor claims:** 50% less downtime, 99% less alert noise, and deployment in about six months.
- The documentation site needs a sign-in, so documented limitations are UNVERIFIED.
- Sources: https://c3.ai/products/c3-ai-reliability/ (product page); https://docs.c3.ai/docs/reliability (opened; showed a sign-in page only)

### B8. Falkonry (IFS)
- **Category:** B, time-series AI.
- **Ownership:** IFS signed a definitive agreement on 31 Aug 2023, with closing expected in Q4 2023. IFS planned to embed Falkonry across ERP, EAM, MES and field service, and also to sell it stand-alone. I found no closing announcement (UNVERIFIED), and falkonry.com does not mention IFS.
- **What it does (own site):**
  - "Time Series AI" with pattern-recognition and anomaly-detection modules.
  - Takes high-speed PLC, fieldbus, SCADA and DCS data over Modbus and OPC UA, at up to 10 kHz for power-quality sensors.
  - Sensor-agnostic.
- **Deployment:** Edge, cloud, on-prem, air-gapped and sovereign.
- **Customers named on the site:** US Navy NSWC, US Department of Energy, Stelco, Ternium and Nucor.
- Sources: https://www.techtarget.com/searcherp/news/366550494/IFS-snaps-up-industrial-AI-provider-Falkonry ; https://falkonry.com/

### B9. Avathon (formerly SparkCognition)
- **Rebrand:** Announced in Bangalore on 11 Nov 2024, together with a plan to triple its Indian workforce within 24 months.
- **What it does (own site):** An industrial AI platform with knowledge, decision-intelligence and governance layers, a Renewable Suite and the AIRKOG knowledge-graph platform.
- **Industries:** Energy, aerospace, defence, manufacturing, mining and logistics.
- **Gaps:** The pages opened name no dedicated PdM or APM product and do not describe data inputs or deployment.
- Sources: https://avathon.com/press-release/avathon-aims-to-triple-workforce-in-india-within-24-months/ ; https://avathon.com/

### B10. SAP Asset Performance Management
- **What it does (own page):** Condition monitoring on IoT data with real-time anomaly detection; failure curves from failure probabilities; RUL estimates; FMEA and RCM; and balancing of risk against cost.
- **Prerequisite:** SAP EAM (S/4HANA Cloud, or ERP 6.0 EHP7 SP14/EHP8).
- **Deployment:** Cloud-native on SAP BTP.
- **Integrations:** SAP Cumulocity IoT can bring in sensor data.
- Source: https://www.sap.com/hk/products/scm/apm.html

### C1. Uptake: Fleet
- **Category:** C, predictive maintenance for vehicle fleets.
- **What it does (own site):** Sensor insights, risk explorer, remote diagnostics, warranty-claim identification, a mixed-fleet data hub and dashboards.
- **Assets:** Heavy and medium trucks, buses, and construction, mining and concrete equipment. Defence and federal pages are listed.
- **Connectors shown:** Platform Science, Trimble, CalAmp and Intellishift.
- **Ownership:** Bosch announced plans to acquire Uptake on 19 Mar 2026. Terms were not disclosed. The platform learns from completed repairs. Completion is UNVERIFIED.
- Sources: https://uptake.com/ ; https://www.trucknews.com/technology/bosch-to-acquire-uptake-technologies-to-boost-predictive-maintenance-capabilities/1003211395

### D. Cloud building blocks: current availability
- **D1 Amazon Lookout for Equipment: discontinued.**
  - AWS ended support on **7 Oct 2026**; the console and resources are no longer accessible. It stopped accepting new customers on **7 Oct 2025**.
  - What it did: trained a custom model on historical data (up to 300 sensors per model) from historians, SCADA or condition-monitoring systems, with optional failure labels. It targeted fixed industrial equipment with limited operating variability, and was a back-end service meant to plug into existing systems.
  - AWS's recommended successor is AWS IoT SiteWise anomaly detection, with migration scripts, plus partner solutions.
  - Sources: https://docs.aws.amazon.com/lookout-for-equipment/latest/ug/what-is.html ; https://aws.amazon.com/blogs/machine-learning/preserve-access-and-explore-alternatives-for-amazon-lookout-for-equipment/
- **D2 Amazon Monitron: closed to new customers.**
  - Closed to new customers on 31 Oct 2024. Devices were sold until July 2025, the 5-year device warranty is honoured, and no new features are planned.
  - Named partner alternatives: Tactical Edge, IndustrAI and Factory AI. No final shutdown date was stated.
  - Source: https://aws.amazon.com/blogs/machine-learning/maintain-access-and-consider-alternatives-for-amazon-monitron
- **D3 AWS IoT SiteWise native anomaly detection.**
  - Multivariate detection reached GA on 28 Jul 2025, needs no ML expertise, and runs in us-east-1, eu-west-1 and ap-southeast-2.
  - On 10 Sep 2025 AWS added scheduled retraining (every 30 days to yearly), automatic (service-managed) or manual (customer-managed) promotion, and visible precision, recall and AUC.
  - Sources: https://aws.amazon.com/about-aws/whats-new/2025/07/aws-iot-sitewise-multivariate-anomaly-detection/ ; https://aws.amazon.com/about-aws/whats-new/2025/09/aws-iot-sitewise-retraining-anomaly-detection-models
- **D4 Azure AI Anomaly Detector: retired.**
  - Retired on **1 Oct 2026**; new resources have been blocked since 20 Sep 2023.
  - Microsoft recommends Microsoft Fabric anomaly detection or the open-source microsoft/anomaly-detector package.
  - Source: https://learn.microsoft.com/en-in/azure/ai-services/anomaly-detector/whats-new
- **D5 Microsoft Fabric Real-Time Intelligence anomaly detection: Preview.**
  - Runs on Eventhouse tables, automatically recommends a model, monitors continuously and raises alerts.
  - Documented limitations: the table needs a numeric value column, a datetime column and a string column; each detector holds one model configuration; Eventhouse runs at most eight concurrent queries and extra queries can fail silently; enabling the Python plugin can take up to an hour.
  - Source: https://learn.microsoft.com/en-us/fabric/real-time-intelligence/anomaly-detection
- **D6 Azure IoT Operations.**
  - An edge data plane on Arc-enabled Kubernetes: MQTT broker, connectors (OPC UA, HTTP/REST) and data flows to Event Hubs, Fabric and ADLS. It can run offline for up to 72 hours.
  - It is plumbing, not a predictive-maintenance model. Its anomaly-detection example sends data to Fabric.
  - Source: https://learn.microsoft.com/en-us/azure/iot-operations/overview-iot-operations

### E. Other India-based or India-linked companies
- **E1 Altizon (Princeton, NJ and Pune).**
  - The DFX platform is positioned as an AI-native MES. It connects PLCs, sensors and ERP and applies ML for predictive maintenance.
  - Industries: beverages, bottled water, alcoholic beverages and packaged food. Customer logos include Pernod Ricard, Varun Beverages and JK Tyre (vendor claims).
  - The page does not mention the older Datonis platform.
  - Source: https://www.altizon.com/
- **E2 Tata Elxsi.** In an interview published 28 Mar 2025, Tata Elxsi described predictive maintenance as a key AI use case using breakdown history, power use and sound patterns. It also described a platform approach (sensor-based machine connection, data aggregation, built-in analytics) and a Tether Factory layer connecting ERP and MES. No product specifications were found. **Analysis:** the case-study sponsor is itself active in this space.
  - Source: https://www.tataelxsi.com/news-and-events/news/from-digital-twins-to-ai-enhanced-production-tata-elxsis-blueprint-for-industry-40
- **E3 Foreign vendors with Indian operations:** Avathon (B9, Bangalore hub, India hiring). Petasense's Bangalore office (UNVERIFIED). Nanoprecise's India presence (UNVERIFIED; only a +91 media contact in the press release).
- **Not found:** an Indian-government or independent census of predictive-maintenance adoption in Indian plants (UNVERIFIED gap).

---

## 3. CMMS and EAM products

| Product | Owner / status | What it does (own docs) | Predictive / condition features documented | API / integration point for an external predictor | Documented limits |
|---|---|---|---|---|---|
| **Fiix** | Rockwell Automation | Cloud CMMS | **Asset Risk Predictor** (Dec 2023 trade news): AI on sensor, machine-recipe and operating data, reportedly learns in as little as 7 days, gives a daily risk level and can auto-create Fiix work orders; sold stand-alone or integrated | REST API with application, access and secret keys; Java and JS SDKs; objects include Asset, WorkOrder, WorkOrderTask and WorkOrderStatus; batch and RPC calls; a free sandbox for Enterprise subscribers on request | API keys act as the user they are tied to (least privilege advised); API plan gating in third-party sources is UNVERIFIED |
| **UpKeep** | UpKeep | CMMS plus **Edge** IIoT | Edge sensors (temperature, humidity, current, vibration, pressure, gas and more) on a mesh gateway; threshold alerts auto-create work orders; AI health scores updated every 15 minutes | Edge REST API (HTTP Basic with a company API key): device types, devices, readings, alerts and incidents; responding to an incident creates a work order or request | The Edge page documents integration only with UpKeep's own CMMS; the main CMMS API was not documented in pages opened |
| **MaintainX** | **Autodesk** (closed 3 Aug 2026 per Autodesk 10-Q) | Cloud CMMS/EAM: work orders, PM, assets, inventory, reporting | AI troubleshooting and summaries; manual and **automated meters**; meter-triggered automations create work orders, change asset status or send email | REST API; automated meters can be created through the REST API | Meter automations are Premium; custom automations Enterprise; not on Basic or Essential; web only; legacy IoT meters (including Samsara) unsupported |
| **Limble** | Limble | Cloud CMMS: work orders, PM, assets, parts, compliance | Its "predictive maintenance" page describes dashboards and trend reports only; no sensors on the home page | Limble API V2 (OpenAPI spec, HTTP Basic with client ID and secret): assets, **asset fields** (numeric values with history; batch update of up to 100), tasks (work orders, PM, requests) and **webhooks**; region-specific hosts including a 21 CFR host | Third-party claims of plan gating UNVERIFIED |
| **eMaint** | Fluke Reliability | CMMS: assets, work orders, PM, dashboards, audit trails, e-signatures | Work orders generated automatically when an asset runs outside set limits; eMaint Condition Monitoring with AI analysis and IoT collection; Fluke IIoT vibration sensors | Data from ERP and SCADA/PLC/BMS systems; no API mentioned on the page opened | — |
| **SAP Plant Maintenance / S/4HANA Asset Management** (+ SAP APM, B10) | SAP | Maintenance notifications and orders; measuring points, counters and measurement documents | Readings recorded as measurement documents (from notifications, orders or completion confirmations); counters support performance-based maintenance | Measurement documents are the natural write target; the help page opened is the old 4.6C version, and the current S/4HANA OData API was not verified | SAP APM requires SAP EAM |
| **IBM Maximo Manage** | IBM (in MAS) | EAM | See B6 | REST/OSLC: post meter readings via the `MXMETERDATA` object structure (`/maximo/api/os/mxmeterdata`, header `x-method-override: SYNC`); Manage uses API keys; each reading date must be later than the previous one | Runs on OpenShift (B6) |
| **HxGN EAM → Octave Attune EAM** | **Octave** (Hexagon spin-off; trading from late May 2026) | Cloud EAM: asset hierarchies, work orders, labour scheduling, calibration, inventory, mobile, digital twin (2D/3D), embedded AI | Attune APM is the separate product for failure prediction | APIs not mentioned on the page opened | The "formerly Infor EAM" lineage is UNVERIFIED (infor.com page returned HTTP 410) |
| **Odoo Maintenance** | Odoo SA; module is LGPL-3 | Equipment register, corrective and preventive requests, calendar, Kanban, teams | **MTBF, MTTR and estimated next failure** computed from past requests (statistical, not condition-based) | Self-hosted code exposes `/xmlrpc/2/<service>` and `/jsonrpc` routes; hosted Odoo offers the external API only on Custom plans (not One App Free or Standard) | The request docs describe no API triggers or IoT; recurrence not covered on the requests page |

Sources for this table:
- Fiix: https://fiixlabs.github.io/api-documentation/guide.html ; https://www.bindt.org/News/december-2023/fiix-ai-software/
- UpKeep: https://upkeep.com/product/edge-iiot/capabilities/cmms-integration ; https://edge.onupkeep.com/edge-api/docs/
- MaintainX: https://www.getmaintainx.com/ ; https://help.getmaintainx.com/about-automations ; https://www.sec.gov/Archives/edgar/data/0000769397/000076939726000061/adsk-20260731.htm
- Limble: https://limble.com/ ; https://api.limblecmms.com/openapi.json
- eMaint: https://www.fluke.com/es-us/productos/software-de-fluke/emaint-cmms
- SAP: https://help.sap.com/saphelp_46c/helpdata/en/74/aba7a6786211d19d8d0000e8323350/content.htm ; https://www.sap.com/hk/products/scm/apm.html
- IBM Maximo Manage: https://www.ibm.com/support/pages/maximo-adding-meter-readings-using-rest-api
- Octave: https://www.octave.com/eam ; https://itbrief.co.uk/story/octave-rebrands-as-it-prepares-spin-off-from-hexagon ; https://itbrief.co.uk/story/octave-begins-trading-on-nasdaq-after-hexagon-spin-off ; https://www.inderes.fi/releases/hexagon-announces-update-on-planned-spin-off-of-octave
- Odoo: https://www.odoo.com/documentation/18.0/applications/inventory_and_mrp/maintenance.html ; https://www.odoo.com/documentation/18.0/applications/inventory_and_mrp/maintenance/add_new_equipment.html ; https://www.odoo.com/documentation/18.0/applications/inventory_and_mrp/maintenance/maintenance_requests.html ; https://raw.githubusercontent.com/odoo/odoo/18.0/addons/maintenance/__manifest__.py ; https://raw.githubusercontent.com/odoo/odoo/18.0/odoo/addons/base/controllers/rpc.py ; https://www.odoo.com/documentation/18.0/developer/reference/external_api.html

**Analysis: what this means for SentinelLoop's missing CMMS link.** Every CMMS above offers at least one documented way in for an external predictor: meter readings (Maximo, MaintainX), numeric asset fields with history (Limble), measurement documents (SAP), or direct work-order and request creation (Fiix, UpKeep, Odoo XML-RPC). SentinelLoop currently writes draft order records to JSON. The cheapest credible integration for a team using only free tools is a self-hosted Odoo Community instance, which needs no paid plan for the XML-RPC routes, or Atlas CMMS (section 4). A commercial CMMS integration would need a vendor sandbox. Fiix offers one, but only to Enterprise subscribers.

---

## 4. Open-source tools

| Tool | What it is (own docs) | Licence (as published) | Maintenance / predictive relevance | Notes |
|---|---|---|---|---|
| **Odoo Community: Maintenance module** | Equipment and maintenance-request tracking | **LGPL-3** (module manifest) | MTBF-based estimated next failure; corrective and preventive types | XML-RPC/JSON-RPC routes in the self-hosted code. Odoo's hosted plans restrict the external API to Custom plans. |
| **openMAINT** (Tecnoteca / PAT srl) | Open-source CMMS for property and facility management, built on CMDBuild; preventive and breakdown maintenance; follows UNI 10951 | **AGPL** | Facilities rather than rotating machinery | Mobile app and self-service portal are **proprietary**, provided with a paid maintenance service; IoT and APIs not mentioned on the page opened |
| **Atlas CMMS** (Grashjs/cmms) | Self-hosted CMMS: work orders with triggers, analytics, equipment and inventory, purchase orders; Java Spring Boot, React and React Native, Postgres; Docker Compose | **AGPL-3.0**, dual-licensed (a commercial licence key unlocks white-labelling and "advanced features") | No meters or IoT in the README | 836 stars at access; API served under `/api` with no dedicated API docs linked |
| **ThingsBoard** | IoT platform: device management, rule chains, alarms, dashboards | **Business Source License 1.1 from v4.4.0** (earlier versions Apache 2.0). Change date: four years after publication, then Apache 2.0 | Rule-engine alarms on telemetry | Free production use only for non-commercial use (≤1,000 devices) or commercial use (≤100 devices on one server), with ThingsBoard branding kept and a free licence key. **Analysis:** a commercial product built on ThingsBoard ≥4.4 beyond 100 devices needs a commercial licence. |
| **OpenRemote** | IoT platform: asset types, rules (when-then, flow, JavaScript, Groovy), MQTT/HTTP/WebSocket, edge gateway, multi-tenant realms; Docker | **AGPL-3.0** | Energy management, fleet telematics; no maintenance features described | ~1.9k stars |
| **Eclipse Ditto** | Digital-twin framework/middleware; HTTP API; connects to Eclipse Hono, MQTT, AMQP, Kafka and webhooks | EPL-2.0 (linked from the footer; not stated in page text) | No analytics or predictive maintenance | Twin-state layer only |
| **Eclipse BaSyx** | Asset Administration Shell (AAS) middleware; Java, C++ and C# SDKs; OPC UA and MQTT data providers; Docker | Not stated on the page (UNVERIFIED; EPL-2.0 linked only in general legal resources) | Reference AAS implementation used by the IDTA submodel template repository | Relevant if a customer requires AAS/Industry 4.0 interoperability |
| **NASA ProgPy** | Python prognostics framework: models, state estimation, prediction with uncertainty propagation; optional data-driven extra (LSTM given as an example) | NASA licence PDFs linked; the badge decodes to "NOSA" (exact licence UNVERIFIED) | Physics models for batteries, centrifugal pump, pneumatic valve, DC motor, ESC, powertrain, propeller, small rotorcraft and thrown object; **no turbofan model** in the list | v1.8 (May 2025) per the citation file; 135 stars |
| **microsoft/anomaly-detector** | `time-series-anomaly-detector` pip package (0.4.0), the open-source route Microsoft points to after retiring Azure Anomaly Detector | MIT | General time-series anomaly detection | README barely documented; 34 stars |

Sources:
- Odoo: https://raw.githubusercontent.com/odoo/odoo/18.0/addons/maintenance/__manifest__.py ; https://www.odoo.com/documentation/18.0/developer/reference/external_api.html
- openMAINT: https://tecnoteca.com/en/products/openmaint
- Atlas CMMS: https://github.com/Grashjs/cmms
- ThingsBoard: https://github.com/thingsboard/thingsboard ; https://raw.githubusercontent.com/thingsboard/thingsboard/master/LICENSE
- OpenRemote: https://github.com/openremote/openremote ; https://raw.githubusercontent.com/openremote/openremote/master/LICENSE.txt
- Eclipse: https://eclipse.dev/ditto/ ; https://eclipse.dev/basyx/
- NASA ProgPy: https://github.com/nasa/progpy ; https://nasa.github.io/progpy/ ; https://nasa.github.io/progpy/api_ref/progpy/IncludedModels.html
- microsoft/anomaly-detector: https://github.com/microsoft/anomaly-detector

**Not checked:** other open-source predictive-maintenance frameworks (for example Apache StreamPipes and PHM toolkits on PyPI). They are left out rather than described from memory.

**Analysis.** The open-source ecosystem splits in two:
- IoT and twin plumbing: ThingsBoard, OpenRemote, Ditto, BaSyx.
- CMMS: Odoo, openMAINT, Atlas.

None of the pages opened documents a condition-based prediction-to-work-order loop on the open-source CMMS side. That gap is real, but small: anyone can wire a ThingsBoard alarm or Python script into an Odoo request. Copyleft licences (AGPL for Atlas, openMAINT and OpenRemote) and ThingsBoard's BUSL change limit how a commercial product can embed these tools.

---

## 5. Data provenance: what each player trains on, compared with SentinelLoop

| Player | Data type behind its models (as stated) | Status of the statement |
|---|---|---|
| Augury | 1.1B+ hours of "real machine readings" | Vendor claim (field data, per the vendor) |
| GE Vernova SmartSignal | OEM-agnostic data from 19,500+ assets; 370+ blueprints | Vendor claim (field) |
| KCF | "Billions of industrial data points" from thousands of assets | Vendor claim (field) |
| AVEVA | Asset Library with 22,000+ hours of experience | Vendor claim |
| Infinite Uptime | Operator-validated prescriptions across ~1,000 plants | Vendor claim (field) |
| Honeywell | First-principles thermodynamic models plus data-driven models | Vendor description (physics plus field) |
| AWS Lookout for Equipment / SiteWise | The customer's own historical data and optional failure labels | AWS documentation (customer field data) |
| NASA C-MAPSS (FD001–FD004) | **Simulated**: degradation generated by the C-MAPSS simulator | NASA PCoE repository |
| NASA "Turbofan Engine Degradation Simulation-2" (N-CMAPSS) | **Synthetic/simulated**: run-to-failure trajectories generated with C-MAPSS under realistic flight conditions | NASA PCoE repository |
| NASA PCoE IMS Bearing; FEMTO Bearing (PRONOSTIA); Milling | **Real laboratory data** (experimental run-to-failure or wear tests) | NASA PCoE repository |
| **SentinelLoop today** | **Simulated** C-MAPSS only; stress tests add **synthetic** faults; no field or lab data | `product/PRODUCT_STATUS.md` (local) |

Sources: the vendor URLs in section 2 ; https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/ ; https://docs.aws.amazon.com/lookout-for-equipment/latest/ug/what-is.html

**Analysis.** Every commercial competitor says its models learn from real field data, its own or the customer's. SentinelLoop's numbers (RMSE, coverage, detection rates) say nothing about field performance. The cheapest next step up is real laboratory data (IMS, FEMTO), which brings vibration signals and real bearing degradation. It is still not field data and should never be called that.

---

## 6. The incumbent non-software alternatives

### 6.1 Spreadsheets and paper
- **2020 Plant Engineering study** (sponsored by Advanced Technology Services, a maintenance-services firm; n=171; margin of error ±7.5% at 95%; data collected 28 Jan–16 Feb 2020; respondents responsible for maintenance; 22% outside the US):
  - Tools used to monitor or manage maintenance (multiple answers allowed): CMMS 50%, in-house spreadsheets or schedules (for example Excel) 47%, paper records of maintenance rounds 46%.
  - In the chart text extraction, IIoT/cloud reads 9% and EAM 8% (PARTIALLY VERIFIED; taken from the chart layout).
- **Earlier years:** A secondary compilation of the 2016–2020 editions gives CMMS 50–62%, spreadsheets 45–55% and paper 39–46%. The publisher of that compilation discloses no vendor affiliation.
- **Caveats:** The sample is US-centred and self-selected. No comparable Indian survey was found (UNVERIFIED gap).
- Sources: https://www.advancedtech.com/wp-content/uploads/2020/03/2020-ATS_Plant-Engineering-Maintenance-Study-Results.pdf ; https://reliamag.com/topics/guides/cmms-adoption-statistics

### 6.2 Fixed-interval (time-based) preventive maintenance and run-to-failure
- **Strategy shares, 2020 Plant Engineering study:** preventive 76%, run-to-failure 60%, CMMS 52%. The chart extraction also reads predictive maintenance with analytical tools at 41% and RCM at 22% (PARTIALLY VERIFIED; chart layout). Respondents could choose several.
- **US DOE FEMP taxonomy:** reactive (fix when broken), preventive (time-based actions), predictive (fix before it breaks) and RCM (a combination of the three plus root-cause analysis). The page itself gives no savings figures for them.
- **NIST (Thomas & Weiss, IJPHM 2021):** survey of US discrete manufacturers in NAICS 333–336; 71 usable responses.
  - Predictive-heavy plants had about 18.5% less downtime and 87.3% fewer defects than preventive-heavy plants, but about 212.3% higher direct maintenance costs.
  - Total maintenance-related costs and losses in US manufacturing were estimated at about $222.0B (2016).
  - The authors call the group comparisons anecdotal because the groups are small.
- **Historical root of the critique of age-based overhaul:** Nowlan & Heap, *Reliability-Centered Maintenance* (United Airlines, 1978; 520 pages; DTIC AD-A066579). The share of items with age-related failure patterns is widely quoted, but I could not open the primary report (the DTIC page returned 403), so those percentages are **UNVERIFIED** here.
- Sources: https://www.energy.gov/femp/operations-and-maintenance-challenges-and-solutions ; https://pmc.ncbi.nlm.nih.gov/articles/PMC9890517/ ; https://www.chemicalprocessing.com/articles/2011/preventative-maintenance-resource-resurfaces/

### 6.3 Vibration-analysis service contracts
- **SKF Remote Analysis:** certified analysts, monthly diagnostic reports, weekly and daily alarm reviews and alarm adjustments, plus on-site mechanical services (section A2).
- **Similar human-analyst layers in other offers:** GE Industrial Managed Services (24×7 monitoring centres, or a fully outsourced turnkey option); KCF SENTRYsolutions (scope not described on the page); Augury, which presents its AI as powered by reliability experts.
- **Outsourcing evidence, 2020 Plant Engineering study:** the average plant outsources 20% of maintenance. Reasons (n=146): lack of time or manpower 48%, lack of staff skills 41%, too many specialised skills required 39%, agreement with the manufacturer or supplier 36%.
- Sources: https://us.promo.skf.com/acton/media/22336/connected-technologies-services ; https://gevernova.com/software/sites/default/files/2024-10/brochure-ai-powered-predictive-analytics-smartsignal.pdf ; https://www.advancedtech.com/wp-content/uploads/2020/03/2020-ATS_Plant-Engineering-Maintenance-Study-Results.pdf

### 6.4 OEM service: the default for turbofans
- **Rolls-Royce TotalCare:** a "premium risk transfer service" in which Rolls-Royce takes time-on-wing and shop-visit cost risk for planned and unplanned events. The customer pays per engine flying hour. The service includes advanced engine health monitoring, predictive maintenance planning, workscope management and off-wing repair and overhaul.
- **GE Aerospace TrueChoice Flight Hour:** full engine maintenance paid per flight hour or per cycle, with risk transfer and guaranteed spare-engine availability. It includes comprehensive remote diagnostics and trend monitoring.
- **Analysis:** For the one asset class SentinelLoop has modelled (turbofan engines), the engine maker already sells health monitoring inside a risk-transfer contract. A third-party student tool has no realistic route to that customer. SentinelLoop's commercial relevance depends on moving to industrial rotating equipment, where condition monitoring is not locked inside OEM contracts.
- Sources: https://www.rolls-royce.com/products-and-services/civil-aerospace/services/totalcare.aspx ; https://www.geaerospace.com/commercial/services/true-choice/flight-hour

---

## 7. Features the market already treats as standard

Compiled from the vendor documents above. A ✓ means the opened page documents the feature; it says nothing about how well the feature performs.

| Capability | Documented by (examples) | SentinelLoop has it? |
|---|---|---|
| Anomaly detection against learned normal behaviour | SmartSignal, AVEVA, Senseye, Falkonry, Maximo Monitor, SiteWise, Fabric (preview), C3 AI | ✓ (healthy-baseline health index) |
| Time-to-failure, RUL or time-to-alarm | Senseye (RUL), AVEVA (time to failure), Honeywell (RUL trending), SAP APM (RUL), IBM Predict (failure dates), SmartSignal (time to action) | ✓ (RUL with a 90% interval) |
| Sensor-health / data-quality monitoring | SmartSignal (six data pathologies, virtual repair), Honeywell (automatic cleansing), Maximo Monitor (gaps, flat lines), Maximo Health (data-quality work queues) | ✓ (input-quality monitor with escalation) |
| Automatic work-order creation from alerts | Fiix ARP, UpKeep Edge, MaintainX automations, eMaint, C3 AI, Honeywell, Tractian, Augury partners | Partial (JSON drafts only; no CMMS) |
| Scheduled retraining with gated or manual promotion | AWS SiteWise (Sept 2025); IBM Monitor (retrain after upgrade) | ✓ (promotion gate showing both accept and reject) |
| Human validation feeding back into models | Infinite Uptime (operator validation), Senseye (AI plus human expertise); Aspen Mtell inspection loop (UNVERIFIED) | Partial (escalation label only; no review loop) |
| Prescriptive actions or FMEA libraries | Aspen Mtell, AVEVA Asset Library, SAP APM (FMEA/RCM), Infinite Uptime | ✗ |
| GenAI copilots | Verdantix 2025: most of 19 vendors have shipped or are piloting them | ✗ (deliberately; the case rules out LLMs) |
| Own certified sensors | Augury, Tractian, KCF, Nanoprecise, Petasense, SKF, Infinite Uptime | ✗ |
| Human analyst service | SKF, GE IMS, Augury, KCF | ✗ |

Verdantix 2025 Green Quadrant (analyst firm, third party): 19 vendors were evaluated. The nine Leaders were ABB, Augury, AVEVA, C3 AI, Cognite, GE Vernova, IBM, Seeq and SymphonyAI. Entry required at least 10 named asset-heavy customers and at least $5M of industrial-AI analytics revenue. Verdantix judges end-to-end agentic autonomy not yet proven at market scale.
Source: https://www.verdantix.com/insights/blog/verdantix-industrial-ai-green-quadrant--vendors-seize-the-industrial-ai-opportunity

---

## 8. Where a small team could be different, and where it cannot compete (analysis)

This section is my analysis. It rests on the sourced facts above, but no customer has validated any of it.

### 8.1 Where SentinelLoop cannot compete, and should not try
1. **Sensors and certified hardware.** ATEX/IECEx, Class 1 Div 1, IP69K, Zone 0 and battery engineering (Tractian, Augury, KCF, Nanoprecise). A student team with no hardware budget cannot match these.
2. **Field-failure data and failure-mode libraries.** Competitors claim billions of data points, 19,500+ assets, 370+ blueprints and FMEA libraries. SentinelLoop has zero field data, and its accuracy results are on simulated engines.
3. **Human diagnosis at scale.** Certified vibration analysts and 24×7 monitoring centres (SKF, GE IMS, Augury, KCF) are part of what buyers pay for.
4. **OEM risk-transfer contracts.** For aero engines the OEM bundles health monitoring with a price per flight hour (6.4). SentinelLoop's C-MAPSS turbofan demo targets a market closed to third parties.
5. **Enterprise breadth and installed base.** SAP, IBM MAS (on OpenShift, with Db2 and MongoDB), Octave, Honeywell and AVEVA PI with hundreds of connectors. A small team cannot match integration breadth, security certifications or procurement trust.
6. **Claims of novelty for standard features.** Anomaly detection, RUL, sensor-health checks, automatic work orders and gated retraining are all documented elsewhere (section 7). AWS SiteWise's promotion modes make "gated retraining" ordinary. SmartSignal's sensor-health monitoring overlaps SentinelLoop's input-quality escalation.
7. **Point accuracy.** No independent benchmark compares vendor accuracy, and SentinelLoop's own numbers are ordinary even on C-MAPSS. No accuracy-based positioning is defensible.

### 8.2 Where differentiation is plausible (hypotheses to test with customers)
1. **Audit-grade, re-derivable decisions.**
   - SentinelLoop records which rules fired, which model version was used and a hash of the inputs, and re-derives every decision. Its replay matched all 3,409 stored decisions and detected deliberate tampering.
   - None of the analytics-vendor pages opened describes re-deriving an analytic decision from stored inputs. CMMS tools do document user-action audit trails (eMaint audit trails and e-signatures; Limble's separate 21 CFR host shows that regulated maintenance buyers exist).
   - **Caveats:** marketing pages may simply omit the capability. SentinelLoop has no e-signatures and no 21 CFR Part 11 controls. Whether buyers will pay for decision re-derivation is unknown.
2. **Published calibration and explicit abstention.**
   - Vendors sell time-to-failure and time-to-action outputs. The pages opened publish ROI claims, not interval coverage or calibration evidence.
   - Possible product property: every prediction carries an interval whose coverage is measured and reported per asset class, and the system escalates instead of acting when inputs are untrustworthy.
   - **Caveats:** calibration measured on simulated data does not carry over. The property only becomes credible once measured on lab data first, then field data.
3. **A vendor-neutral decision layer between existing monitoring and the CMMS.**
   - Many plants already have alarms from sensors, historians, or a vendor such as Augury, Tractian or SKF, and a CMMS that can take meters or work orders (section 3).
   - The layer would take third-party anomaly or health signals and turn them into escalation-aware, evidence-carrying work-order drafts.
   - This would compete with no one's sensors. Its rivals are built-in alert-to-work-order automations (MaintainX, UpKeep, Fiix) and the integration services vendors already sell, so the advantage is narrow.
4. **Back-testing maintenance policies before go-live.** SentinelLoop's policy-replay harness scores alternative maintenance rules against history: late-order rate, discarded life and alert volume. None of the vendor pages opened describes testing a maintenance rule against history before deployment (UNVERIFIED absence). Whether reliability engineers want this is unknown.
5. **A free, self-hosted add-on for open-source CMMS.**
   - The tool would turn condition data into requests in Odoo Community (LGPL-3; MTBF-only prediction today) or Atlas CMMS (AGPL-3.0; no meters).
   - This suits the team's free-tools-only constraint and could reach small plants that use spreadsheets or paper (6.1).
   - **Licence check:** an Odoo module and an AGPL-linked service each carry obligations. Hosted Odoo restricts the external API to Custom plans.
6. **Gaps left by retired cloud services (narrow).** Lookout for Equipment and Azure Anomaly Detector are gone, but AWS SiteWise and Microsoft Fabric have taken their place. Only builders who want self-hosted, open tooling are left unserved.

### 8.3 Positioning this analysis supports, and claims to avoid
- **Supported:** "An auditable maintenance-decision layer that turns condition signals into reviewed, evidence-carrying work orders, demonstrated so far only on simulated data."
- **Avoid:** "predictive maintenance platform"; "self-healing machines" as a product claim; "first"; any comparative accuracy claim; any statement implying field validation.

### 8.4 What would change this assessment (next evidence to collect)
- Interviews with 10 or more maintenance or reliability engineers, ideally in Indian plants, on whether decision re-derivation, calibration and pre-deployment back-testing affect buying decisions. Whether such needs exist is currently UNVERIFIED.
- A rerun on real laboratory vibration data (IMS or FEMTO from NASA PCoE) to see whether the calibration and escalation behaviour survives off simulated data.
- One working integration with a free CMMS (self-hosted Odoo Community), with the order lifecycle closed by an outcome record.

---

## 9. Gaps and unverified items
- **Vendor pages that did not load:**
  - C3 AI documentation (sign-in wall)
  - nanoprecise.io (empty render)
  - skf.com/axios (near-empty)
  - Augury help articles (404)
  - infor.com/hexagon-eam (410)
  - Hexagon newsroom (403; read via mirror)
  - IFS/Falkonry ARC page (403)
  - Fiix/Rockwell press release (404; trade copy used)
  - Siemens Senseye product sheet PDF (404)
  - DOE O&M guide PDF (500 / too large)
  - DTIC Nowlan & Heap (403)
  - Tata Elxsi expo page (DNS failure)
- **Not verified in this session:**
  - Completion of IFS–Falkonry and Bosch–Uptake
  - Exact Halo/Axios/Tractian/Nanoprecise sensing specifications, where marked
  - Petasense and Nanoprecise India offices
  - Presage protocols
  - Plan-gating of the Fiix, UpKeep and Limble APIs (only third-party claims seen)
  - Current SAP S/4HANA measurement-document API
  - Eclipse BaSyx and ProgPy licences
- **Not researched:** Indian maintenance-practice surveys; Indian CMMS vendors; other Azure partner PdM offerings; open-source PdM toolkits beyond ProgPy and microsoft/anomaly-detector.
- **Dates to recheck:** Chart percentages in the 2020 Plant Engineering PDF beyond the summary page come from layout-based text extraction. The Honeywell product information note carries no date.

---

## 10. Sources (all accessed 2026-10-18)

### Commercial PdM / APM vendors
1. https://www.augury.com/
2. http://www.augury.com/?p=7721 (Augury Halo R4000 page)
3. https://www.augury.com/partners/
4. https://www.bindt.org/News/november-2022/skf-announces-launch-of-skf-axios-powered-by-aws/
5. https://us.promo.skf.com/acton/media/22336/connected-technologies-services
6. https://tractian.com/en/plans
7. https://kcftech.com/solutions/smartsensing-suite/
8. https://petasense.com/
9. https://www.newswire.ca/news-releases/nanoprecise-announces-world-s-first-light-energy-harvesting-predictive-maintenance-sensor-808894693.html
10. https://www.infinite-uptime.com/about-us
11. https://infinite-uptime.com
12. https://techcrunch.com/2023/05/22/tiger-global-india-infinite-uptime-funding/
13. https://www.industrialautomationindia.in/news/presage-insights-raises-5-6-crore-predictive-maintenance-india
14. https://www.siemens.com/us/en/products/services/digital-enterprise-services/analytics-artificial-intelligence-services/predictive-services/senseye-predictive-maintenance/how-it-works.html
15. https://news.siemens.co.uk/news/siemens-acquires-senseye-predictive-maintenance-and-asset-intelligence-for-industrial-companies
16. https://www.aspentech.com/en/products/apm/aspen-mtell
17. https://www.emerson.com/en-us/news/2025/emerson-completes-acquisition-of-remaining-outstanding-shares-of-aspentech
18. https://gevernova.com/software/sites/default/files/2024-10/brochure-ai-powered-predictive-analytics-smartsignal.pdf (fetched by WebFetch; text read with pdftotext)
19. https://gevernova.com/software/resources/brochure/ai-powered-predictive-analytics-smartsignal
20. https://www.gevernova.com/software/documentation/cloud-apm/usw/apm-connect-first-time-deployment.html
21. https://www.aveva.com/en/products/predictive-analytics/
22. https://www.aveva.com/en/products/aveva-pi-system/
23. https://process.honeywell.com/content/dam/process/en/documents/document-lists/PINForgeAPMR1-v1.pdf (fetched by WebFetch; text read with pdftotext)
24. https://www.honeywell.com/us/en/press/2025/04/honeywell-technology-to-drive-process-automation-for-aker-bp-operations
25. https://www.ibm.com/docs/SSC5CS/com.ibm.pm.doc/config/c_predictive_model_templates.html
26. https://www.ibm.com/docs/SS7PRM_cd/com.ibm.ah.doc/overview/whats_new_91.html
27. https://www.ibm.com/docs/en/SSRHPA_8.7.0/appsuite/admin/deploy_monitor.html
28. https://www.ibm.com/docs/en/SSRHPA_cd/appsuite/overview/c_technical_overview.html
29. https://c3.ai/products/c3-ai-reliability/
30. https://docs.c3.ai/docs/reliability (opened; sign-in page only)
31. https://www.techtarget.com/searcherp/news/366550494/IFS-snaps-up-industrial-AI-provider-Falkonry
32. https://falkonry.com/
33. https://avathon.com/press-release/avathon-aims-to-triple-workforce-in-india-within-24-months/
34. https://avathon.com/
35. https://www.sap.com/hk/products/scm/apm.html
36. https://uptake.com/
37. https://www.trucknews.com/technology/bosch-to-acquire-uptake-technologies-to-boost-predictive-maintenance-capabilities/1003211395
38. https://www.altizon.com/
39. https://www.tataelxsi.com/news-and-events/news/from-digital-twins-to-ai-enhanced-production-tata-elxsis-blueprint-for-industry-40
40. https://www.verdantix.com/insights/blog/verdantix-industrial-ai-green-quadrant--vendors-seize-the-industrial-ai-opportunity

### Cloud building blocks
41. https://docs.aws.amazon.com/lookout-for-equipment/latest/ug/what-is.html
42. https://aws.amazon.com/blogs/machine-learning/preserve-access-and-explore-alternatives-for-amazon-lookout-for-equipment/
43. https://aws.amazon.com/blogs/machine-learning/maintain-access-and-consider-alternatives-for-amazon-monitron
44. https://aws.amazon.com/about-aws/whats-new/2025/07/aws-iot-sitewise-multivariate-anomaly-detection/
45. https://aws.amazon.com/about-aws/whats-new/2025/09/aws-iot-sitewise-retraining-anomaly-detection-models
46. https://learn.microsoft.com/en-in/azure/ai-services/anomaly-detector/whats-new
47. https://learn.microsoft.com/en-us/fabric/real-time-intelligence/anomaly-detection
48. https://learn.microsoft.com/en-us/azure/iot-operations/overview-iot-operations

### CMMS / EAM
49. https://fiixlabs.github.io/api-documentation/guide.html
50. https://www.bindt.org/News/december-2023/fiix-ai-software/
51. https://upkeep.com/product/edge-iiot/capabilities/cmms-integration
52. https://edge.onupkeep.com/edge-api/docs/
53. https://www.getmaintainx.com/
54. https://help.getmaintainx.com/about-automations
55. https://www.sec.gov/Archives/edgar/data/0000769397/000076939726000061/adsk-20260731.htm
56. https://limble.com/
57. https://api.limblecmms.com/openapi.json
58. https://www.fluke.com/es-us/productos/software-de-fluke/emaint-cmms
59. https://help.sap.com/saphelp_46c/helpdata/en/74/aba7a6786211d19d8d0000e8323350/content.htm
60. https://www.ibm.com/support/pages/maximo-adding-meter-readings-using-rest-api
61. https://www.octave.com/eam
62. https://itbrief.co.uk/story/octave-rebrands-as-it-prepares-spin-off-from-hexagon
63. https://itbrief.co.uk/story/octave-begins-trading-on-nasdaq-after-hexagon-spin-off
64. https://www.inderes.fi/releases/hexagon-announces-update-on-planned-spin-off-of-octave
65. https://www.odoo.com/documentation/18.0/applications/inventory_and_mrp/maintenance.html
66. https://www.odoo.com/documentation/18.0/applications/inventory_and_mrp/maintenance/add_new_equipment.html
67. https://www.odoo.com/documentation/18.0/applications/inventory_and_mrp/maintenance/maintenance_requests.html
68. https://www.odoo.com/documentation/18.0/developer/reference/external_api.html

### Open source
69. https://raw.githubusercontent.com/odoo/odoo/18.0/addons/maintenance/__manifest__.py
70. https://raw.githubusercontent.com/odoo/odoo/18.0/odoo/addons/base/controllers/rpc.py
71. https://tecnoteca.com/en/products/openmaint
72. https://github.com/Grashjs/cmms
73. https://github.com/thingsboard/thingsboard
74. https://raw.githubusercontent.com/thingsboard/thingsboard/master/LICENSE
75. https://github.com/openremote/openremote
76. https://raw.githubusercontent.com/openremote/openremote/master/LICENSE.txt
77. https://eclipse.dev/ditto/
78. https://eclipse.dev/basyx/
79. https://github.com/nasa/progpy
80. https://nasa.github.io/progpy/
81. https://nasa.github.io/progpy/api_ref/progpy/IncludedModels.html
82. https://github.com/microsoft/anomaly-detector

### Datasets, incumbent practice, standards bodies and government sources
83. https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/
84. https://www.advancedtech.com/wp-content/uploads/2020/03/2020-ATS_Plant-Engineering-Maintenance-Study-Results.pdf (fetched by WebFetch; text read with pdftotext)
85. https://reliamag.com/topics/guides/cmms-adoption-statistics
86. https://pmc.ncbi.nlm.nih.gov/articles/PMC9890517/
87. https://www.energy.gov/femp/operations-and-maintenance-challenges-and-solutions
88. https://www.chemicalprocessing.com/articles/2011/preventative-maintenance-resource-resurfaces/
89. https://www.rolls-royce.com/products-and-services/civil-aerospace/services/totalcare.aspx
90. https://www.geaerospace.com/commercial/services/true-choice/flight-hour

### Local files read (not web sources)
- `C:\Users\HP\OneDrive\Desktop\tata\README.md`, `FINAL_HANDOFF.md`, `product\PRODUCT_STATUS.md`, `research\PRIOR_ART_AND_DIFFERENTIATION.md` (sections 3–4)
