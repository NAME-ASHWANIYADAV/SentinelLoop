# R2: Why predictive-maintenance projects fail or stall, and what evidence buyers need

Research stream R2 for the SentinelLoop product team. Prepared 2026-10-18.

## How to read this file

- Every factual claim carries a bracketed source number that points to the **Sources** section at the end. Every URL listed there was opened in this session on 2026-10-18.
- **UNVERIFIED** means one of two things: I could not open a primary source for the claim, or I saw it only in a search-result snippet or a secondary summary. Such claims are kept only as leads and are never used as evidence.
- Each source has an evidence-type tag:
  - **[PR]**: peer-reviewed journal or conference paper.
  - **[GOV/STD]**: government agency or standards body.
  - **[CONS]**: management consultancy or analyst firm. These are not peer-reviewed and are usually based on client work.
  - **[VEND]**: vendor-authored or vendor-sponsored. These are marketing claims and are labelled as such.
  - **[TRADE]**: trade press.
  - **[THESIS]**: student thesis, not peer-reviewed.
- Each data-bearing source also has a data-type tag:
  - **FIELD**: real operational data from industry.
  - **LAB**: real data from a laboratory or test rig, or a human-subjects lab experiment.
  - **SIM**: output of a physics or simulation model, such as NASA C-MAPSS.
  - **SYN**: synthetic or generated data.
  - **SURVEY/INTERVIEW**: self-reported opinions.
- **Inference** marks statements that are my own reasoning for SentinelLoop rather than sourced facts. They are confined to Section 6.

### Tooling limits during this session (stated for transparency)

- WebSearch and WebFetch were available. The shared WebSearch budget for this turn ran out near the end of the research. A few planned look-ups therefore could not be made, and they are listed under "Gaps".
- Several primary sources blocked automated access, timed out or returned 403. They appear only in "Leads not verified" and are not used as evidence. They are:
  - the McKinsey article on analytics-based maintenance strategy;
  - the PwC Predictive Maintenance 4.0 PDFs;
  - the MDPI paper on the N-CMAPSS dataset and the MDPI Achouch et al. review;
  - the defense.gov copy of the CISA guide (an identical IC3 copy was used instead);
  - Control Engineering and the Emerson ISA-18.2 articles;
  - the DOE FEMP O&M Best Practices Guide;
  - the Terho & Jalkala customer-reference paper.

---

## 1. Executive summary

1. **Pilot purgatory is documented, but how large it is depends on who asks the question.**
   - McKinsey's 2018 survey had more than 700 respondents in 7 countries. Fewer than a third had moved critical digital-manufacturing use cases into large-scale rollout. Across industries, an average of 66% were at pilot stage but only 25% at rollout [1] [CONS, SURVEY].
   - The 2019 WEF/McKinsey Lighthouse report put more than 70% of industrial companies in "pilot purgatory". It also found that 56% of pilots ran 1-2 years and 28% ran more than 2 years [2] [CONS, SURVEY].
   - LNS Research disputes the framing. In its own surveys, only 13% (2019) and 7% (2021) of manufacturers described themselves as stuck in pilot [3] [CONS, SURVEY].
2. **Lack of failure labels is the most consistently reported technical barrier.**
   - Industrial interviewees report having no run-to-failure data [4] [PR, INTERVIEW].
   - Reviews say machines are usually repaired before they fail [7] [PR], and that frequent preventive maintenance limits run-to-failure data [42] [PR].
   - NASA states that it built C-MAPSS as a **simulation** precisely because fielded systems are either prevented from running to failure or lack instrumentation when they do [8] [GOV, SIM].
   - Failure records from preventive-maintained equipment are right-censored, and this corrupts interval optimisation [6] [PR, FIELD].
3. **False alarms are an economic problem as well as a usability problem.**
   - A modelling study of offshore wind found that false-alarm investigation costs can change the cost-benefit of condition monitoring [34] [PR].
   - Human-factors research links frequent false alarms to falling operator trust and slower responses (the "cry wolf" effect) [10] [PR, LAB].
   - Interviewees say early PdM systems cannot be trusted blindly because of false and missed alarms [4] [PR, INTERVIEW].
4. **Security, integration and uncertain ROI are the top non-technical blockers in independent surveys.**
   - Bain's 2018 survey of more than 600 executives ranked security, integration and ROI as the top concerns. Customers said they would buy more IoT and pay about 22% more on average if security concerns were addressed [25] [CONS, SURVEY].
   - The WEF cites alignment on value/ROI and the cost to scale as the main reasons pilots stall [2].
5. **The evidence vendors put forward is mostly self-reported.**
   - It takes the form of named or anonymised reference customers, fleet scale, months to ROI and advance-warning time. For example, a Siemens/Senseye automotive case study reports more than 10,000 machines, ROI in under 3 months and up to 6 months of warning [39] [VEND].
   - One vendor went as far as offering an ROI guarantee (Senseye "ROI Lock"): the subscription is refunded if eligible customers do not reach ROI within 12 months [38] [CONS reporting a VEND offer].
   - The only government-sourced benefit estimate found is from NIST, based on 71 survey responses. Plants relying more on predictive than on preventive maintenance reported 18.5% less unplanned downtime and 87.3% fewer defects. The authors treat this as associational and call for more research [13] [PR/GOV, SURVEY].
6. **Purchasing typically means a pilot first, then a subscription, after formal vendor qualification and a security review.**
   - Marketplace listings price PdM software as 12-month subscriptions per sensor or per asset band [36] [37] [VEND].
   - Large industrial buyers qualify vendors by invitation only through e-procurement platforms (Tata Steel UK via SAP Ariba) [47].
   - Indian central-government buyers can relax prior-turnover, prior-experience and EMD requirements for DPIIT-recognised startups (GFR 2017 Rules 170(i), 173(i)) [30] [GOV].
   - CISA and 11 partner agencies now publish 12 security elements that OT owners should demand when buying [15] [GOV].
7. **Operations and maintenance drive the decision, while management sponsors it and IT/OT security gates it.**
   - Bain found OT staff were the key decision-makers or influencers in 85% of IoT purchases [24] [CONS].
   - A PdM process reference model built from 11 practitioner interviews places project ownership in maintenance, technical planning or production. Management (business owner, asset manager, COO) acts as the sponsor that makes the crucial decisions, and IT/production-IT supports the architecture [23] [PR, INTERVIEW].
   - No verified source was found that describes a finance sign-off step specifically. That point is **UNVERIFIED**.
8. **Large vendors have exited this market.**
   - AWS closed Amazon Monitron to new customers on 31 Oct 2024 [18].
   - AWS discontinued support for Amazon Lookout for Equipment on 7 Oct 2026 [19] [VEND/primary].
   - Neither notice states a reason.

---

## 2. Failure and stall mechanisms (detailed evidence)

### 2.1 Pilot purgatory and slow scaling

| Claim | Source | Type | Data |
|---|---|---|---|
| McKinsey Digital Manufacturing Global Expert Survey 2018: more than 700 respondents (companies with more than 50 employees and more than USD 10M revenue) in Brazil, China, France, Germany, India, Japan and the USA. 92% said they were level with or ahead of peers, yet fewer than one-third had moved critical use cases to large-scale rollout. | [1] | CONS | SURVEY |
| Same survey: in the "Intelligence" lever group, which explicitly includes predictive maintenance, about 70% of relevant solutions were at pilot stage or beyond but about 29% were at rollout. The industry average was 66% at pilot vs 25% at rollout. | [1] | CONS | SURVEY |
| Same report: 59% saw "lack of vision" as a significant obstacle (up from 15% in 2017). Only 25% had set up integrated lighthouse pilots to show benefits. | [1] | CONS | SURVEY |
| WEF (with McKinsey), Jan 2019: more than 70% of industrial companies are still in "pilot purgatory". Only 29% are deploying at scale, and 30% had yet to pilot. | [2] | CONS | SURVEY (attributed to the Forum's Jan 2018 work) |
| Pilot length (WEF 2019): 15% of pilots were under 1 year, 56% were 1-2 years and 28% were over 2 years. The report says most companies struggle to scale because of difficulty aligning on value/ROI, uncertainty about digital's value, and the cost to implement and scale. | [2] | CONS | SURVEY |
| Counterpoint: LNS Research (blog, Nov 2021) reports that 13% (2019) and 7% (2021) of manufacturers in its surveys described themselves as "stuck in pilot with unclear results". 57% said programmes met or exceeded expectations. No sample sizes are given. | [3] | CONS (analyst blog) | SURVEY |
| Bain 2018 (more than 600 executives): customers were running more proofs of concept than two years earlier but planned less extensive implementations, and complete solutions may take longer to deliver returns. | [25] | CONS | SURVEY |
| Condition-based maintenance (CBM) adoption is described as fragmented and slow despite technical progress. A study of 5 industrial organisations (2 followed longitudinally) found that CBM complements existing maintenance routines rather than replacing them. | [21] | PR (working seminar paper, 2026) | INTERVIEW/CASE |
| Interviewees at 15 European firms cite long implementation and approval processes as a barrier. | [4] | PR | INTERVIEW |

**Reading:** the independent (non-vendor) sources agree that scaling, not piloting, is the harder step, and that pilots often run longer than a year. The exact percentage "stuck" varies from 7% to more than 70%, depending on the survey wording and on who funds the survey.

### 2.2 No failure labels, no run-to-failure data, and censoring by preventive maintenance

| Claim | Source | Type | Data |
|---|---|---|---|
| Interviewees name the absence of run-to-failure data for model training as a constraint on PdM. | [4] Hoffmann & Lasch 2025, Schmalenbach J. Bus. Res. 77:27-55 | PR | INTERVIEW (15 European firms, 7 sectors) |
| A systematic review of 42 digital-twin PdM studies identifies limited failure data as a core obstacle, because machines are frequently repaired before failure. | [7] van Dinter, Tekinerdogan, Catal 2022, Inf. Softw. Technol. 151 | PR | literature |
| A 2025 review lists limited run-to-failure data due to frequent preventive maintenance as a challenge. It also notes that many generative and digital-twin approaches assume uniform sensor deployment, which rarely holds in practice. | [42] Ramzan & Recupero 2025, Operations Research Forum 6:181 | PR (open access) | literature |
| NASA's dataset record explains why it simulated degradation: systems that do run to failure often lacked warning instrumentation, and continuously monitored systems are prevented from running to failure. C-MAPSS simulates a large (~90,000 lb thrust class) commercial turbofan. | [8] | GOV | **SIM** |
| The NASA PCoE repository lists "Turbofan Engine Degradation Simulation" (C-MAPSS; four sets under different operating conditions and fault modes) and "Turbofan Engine Degradation Simulation-2", described as a synthetic dataset of run-to-failure trajectories for a small fleet under realistic flight conditions. | [9] | GOV | **SIM / SYN** |
| Equipment failure information is usually right-censored because of preventive maintenance. If censoring is not handled, the optimisation of the preventive interval is poor. | [6] Sánchez-Herguedas et al. 2022, Sensors 22(4):1432 | PR | **FIELD** (O-ring failures on large marine diesel engines of Spanish coastal surveillance vessels; data available on request) |
| The size and direction of the censoring effect in that case study could not be reliably extracted. My fetch summary and the search snippet disagreed. **UNVERIFIED**; read the full paper before quoting any number. | [6] | - | - |
| The PdM process reference model (PReMMa) includes an explicit data-labelling step: for unlabelled data, labels have to be specified. Data labelling was one of the steps added after the practitioner interviews. | [23] Wagner & Hellingrath 2021, IJPHM | PR | INTERVIEW (11 practitioners) |
| Historical CMMS work orders often have missing or incorrect functional location, failure mode, maintenance action and status fields. Cleaning assumptions are rarely documented. | [33] Hodkiewicz & Ho 2016, J. Quality in Maintenance Eng. 22(2):146-163 | PR | **FIELD** (heavy mobile equipment, several organisations) |

**Reading:** this is the central technical reason why RUL models trained on SIM data such as C-MAPSS do not transfer directly to plants:
- in the field, true failure times are mostly unobserved (censored);
- the "labels" that do exist come from noisy, free-text work orders.

### 2.3 Data quality and sensor issues

| Claim | Source | Type | Data |
|---|---|---|---|
| The main obstacles found were digital readiness, data quality and accessibility, technology integration and maintenance organisation. The detailed barriers include: no manufacturer specifications for CBM/PdM thresholds; no open interfaces for retrofitting sensors; and poor mobile-network coverage for real-time monitoring of mobile assets. | [4] | PR | INTERVIEW |
| Noisy, inconsistent or missing data introduces model errors and raises the risk of wrong maintenance actions. | [42] | PR | literature |
| A significant up-front effort in data cleansing and in mapping data to events may be required. | [40] Deloitte Insights 2017 | CONS | - |
| Maintenance text records are unstructured. Out-of-the-box NLP struggles with expert-generated technical language, and data quantity/quality has to be engineered for technical domains (NIST-affiliated "Technical Language Processing"). | [32] Dima et al. 2021, Applied AI Letters 2(3) | PR / GOV authors | method paper |
| Emory/Presenso study, reported 2018: 44% of maintenance and reliability respondents relied on manual statistical modelling (e.g. Excel), 23% on advanced statistical modelling and 12% on machine learning. The researchers found no urgency to upgrade legacy practices. The respondent count is not stated. | [45] | TRADE reporting an academic/vendor (Presenso) study | SURVEY |

### 2.4 False alarms and alert fatigue

| Claim | Source | Type | Data |
|---|---|---|---|
| Few studies examine condition-monitoring detection rates or false alarms, and many assume every designed-for fault is detected. Investigating or ignoring false positives offshore incurs costs that may change the cost-benefit of condition monitoring. | [34] May & McMillan 2013 (ESREL, CRC Press) | PR (conference) | modelling (Markov / time series) |
| Frequent false alarms reduce operators' trust in alarm systems and can lead to disuse and slower responses (the "cry wolf" phenomenon). Thresholds are usually set low under a fail-safe philosophy, so most alarms are false. | [10] Wiczorek & Meyer 2019, Frontiers in Psychology 10:519 | PR | **LAB** (80 students, simulated quality-control task; not a plant study) |
| Interviewees report false or missed alarms early in PdM deployments, and say the system cannot be relied on blindly at the start. | [4] | PR | INTERVIEW |
| ISA-18.2 (approved 2009; 2016 edition current per ANSI) defines an alarm as an indication that requires an operator response. Its numeric benchmarks are **UNVERIFIED**: roughly 1 alarm per 10 minutes per operator as "very likely acceptable" and a flood defined as more than 10 alarms in 10 minutes. These figures were seen only in vendor and training-site summaries; the standard is paywalled and the exida page opened [48] did not state them. | search snippets only | - | - |
| The claim that "false positives offset PdM savings" (McKinsey, analytics-based maintenance strategy) is **UNVERIFIED**: the article could not be opened, so it was seen only in a search snippet. | - | - | - |

### 2.5 Trust and explainability for technicians

| Claim | Source | Type | Data |
|---|---|---|---|
| A PRISMA-based systematic review of explainable PdM argues that operators must trust PdM as it moves into higher-consequence applications, and that XAI can increase user trust while performance is maintained. | [11] Cummins et al. 2024, IEEE Access 12:57574-57602 (arXiv 2401.07871) | PR | literature |
| In an online experiment (participants from aviation and transport/warehousing diagnosing Li-ion batteries with a PdM model):<br>- global explanations produced no significant change in trust or performance;<br>- local explanations decreased trust, self-efficacy and human-AI performance, and increased compliance errors;<br>- self-reported trust did not correlate with behavioural trust. | [12] Pedraza 2024, MS thesis, UW-Madison | THESIS | **LAB** (online experiment; battery data source not verified) |
| The review notes an unresolved tension between transparency and predictive performance, and that over-reliance on AI predictions without human oversight may undermine trust and adoption. | [42] | PR | literature |
| An interview study of 13 experts in remote condition monitoring, asset management and predictive analytics across sectors found these success themes:<br>- design should be **decision-led rather than data-led**;<br>- deployments need long-term resourcing;<br>- end-user organisations need technical competency;<br>- knowledge must be maintained across complex supply chains. | [5] Golightly, Kefalidou, Sharples 2018, Inf. Syst. e-Bus. Manag. 16(3):627-648 | PR | INTERVIEW |
| Machine operators and field technicians, as the future primary users, contribute to dashboard design. The authors say this improves acceptance and usability. | [23] | PR | INTERVIEW |

**Reading:** the evidence does not support "add SHAP and trust follows". Explanations can lower trust when they are poorly matched to the user. Long-run trust appears to come from decision-led design, involving users and a track record of not crying wolf.

### 2.6 Integration with CMMS/EAM and work processes

| Claim | Source | Type | Data |
|---|---|---|---|
| Bain 2018: integration is a top concern. Vendors have not made it easy to integrate IoT solutions into business processes or IT/OT systems, and vendors underestimate this concern. | [25] | CONS | SURVEY (more than 600 execs) |
| Interviewees cite compatibility problems between systems and unclear interface standards. A proposition in the same paper: PdM can streamline processes by linking to ordering and shift planning. | [4] | PR | INTERVIEW |
| A 2021 trade article by a practitioner gives four obstacles: undefined financial benefits, undefined operational benefits (maintenance must integrate with production data), poor programme execution (PdM is socio-technical) and lack of executive support. The author says culture and implementation were major roadblocks in more than 70% of his last 200 company visits. These are his own observations, not a controlled survey. | [46] Blanche, Plant Services, 19 Jan 2021 | TRADE | practitioner observation |
| Interoperability between AI and legacy systems is named as an integration challenge. | [42] | PR | literature |
| Vendor claim: the Siemens/Senseye customer's engineers can onboard new machines and integrate with other enterprise software on their own. | [39] | VEND | - |

### 2.7 OT cybersecurity review

| Claim | Source | Type | Data |
|---|---|---|---|
| Interviewees cite data-privacy and IT-security concerns (data manipulation, external intrusion). Some firms judge the risk of networking plants as too high. | [4] | PR | INTERVIEW |
| Security was the top concern in Bain's 2018 IoT survey. Enterprise customers said they would buy more IoT devices and pay about 22% more on average if security concerns were addressed. | [25] | CONS | SURVEY |
| CISA's *Secure by Demand: Priority Considerations for OT Owners and Operators when Selecting Digital Products* (13 Jan 2025) was co-authored by:<br>- US agencies: NSA, FBI, EPA, TSA;<br>- Five Eyes partners: Australia's ACSC, Canada's CCCS, NCSC-NZ, NCSC-UK;<br>- European partners: the European Commission's DG CONNECT, Germany's BSI, NCSC-NL.<br>The guide warns that threat actors target specific OT products, and tells owners to build security into procurement. | [15] (IC3 copy of the guide), [14], [16] | GOV | - |
| The 12 elements buyers should prioritise are:<br>1. configuration management;<br>2. logging in the baseline product (open formats);<br>3. open standards;<br>4. ownership (operator autonomy, minimal vendor dependency);<br>5. protection of data, including in transit to and from vendors;<br>6. secure by default (no default passwords, legacy protocols off);<br>7. secure communications;<br>8. secure controls;<br>9. strong authentication (role-based access control, phishing-resistant MFA);<br>10. threat modelling;<br>11. vulnerability management (free patches over a defined support period, SBOM, vulnerability disclosure programme);<br>12. upgrade and patch tooling. | [15] | GOV | - |
| NIST SP 800-82 Rev. 3, *Guide to OT Security* (Sept 2023), covers OT topologies, threats, vulnerabilities and countermeasures. The CSRC page notes that a Rev. 4 initial public draft is open for comment until 30 Nov 2026. | [17] | GOV/STD | - |
| The ISA/IEC 62443 series assigns duties across asset owners (2-1), service providers (2-4), system requirements and security levels (3-3), secure product development lifecycle (4-1) and component requirements (4-2). ISASecure runs conformance schemes, including Security Development Lifecycle Assurance for supplier processes. | [35] | STD | - |
| India, power sector: the CEA notified draft *Cyber Security in Power Sector Regulations, 2024* (21 Aug 2024). The draft makes vendors provide documented, tested recovery procedures and security patches for all system components through the contractual operating period. **Whether the final regulations were notified is UNVERIFIED.** | [43] | TRADE reporting GOV draft | - |
| Retrofitting unconnected legacy assets can increase cyber risk. | [40] | CONS | - |

### 2.8 Change management, skills and organisation

| Claim | Source | Type | Data |
|---|---|---|---|
| Organisational barriers reported by interviewees:<br>- maintenance is not treated as strategic;<br>- operational tasks crowd out strategic work;<br>- programmers and data specialists are scarce;<br>- employees are reluctant;<br>- knowledge of PdM benefits is limited and PdM-specific KPIs are missing. | [4] | PR | INTERVIEW |
| India, Goswami & Daultani 2022 (10 firms in 5 Make-in-India sectors): experts in all firms named resistance to change, unclear economic benefits, and coordination and collaboration problems as common Industry 4.0 barriers. | [31] The TQM Journal 34(6):1485-1505 | PR | INTERVIEW |
| Companies are mostly at the start of PdM implementation, owing to missing internal knowledge and systematic guidance. The authors cite innovation-averse mindsets, unclear scope and uncertain monetary benefits. Three interviewed experts said a structured process was critical to their success. | [23] | PR | INTERVIEW |
| Azima DLI "State of the Condition Monitoring Industry" (vendor survey; year not stated on page): 65% of respondents had a CM/PdM programme. Top negative factors were insufficient staff, limited in-house expertise, difficulty demonstrating ROI and limited budget support. | [44] | VEND survey via TRADE | SURVEY |
| Frontline staff were reluctant to change, and there was low urgency to modernise. | [45] | TRADE (academic/vendor study) | SURVEY |
| Process and organisational change is typically as important as the technology. | [40] | CONS | - |

### 2.9 Unclear ROI

| Claim | Source | Type | Data |
|---|---|---|---|
| ROI is unclear and benefits appear only in the medium to long term. PdM is perceived as disproportionately risky and unprofitable. The authors also warn that an excessive ROI focus causes long-term benefits to be ignored (their Proposition 2). | [4] | PR | INTERVIEW |
| NIST (Thomas & Weiss 2021):<br>- survey of US machinery-maintenance managers in NAICS 333-336, with 85 responses of which 71 were usable;<br>- estimated total US manufacturing maintenance costs and losses at about $222.0B per year (2016 dollars);<br>- the less-reactive half reported 52.7% less unplanned downtime and 78.5% fewer defects than the more-reactive half;<br>- the more-predictive half reported 18.5% less unplanned downtime and 87.3% fewer defects than the more-preventive half.<br>The authors call this anecdotal and say more research is needed. They also say estimating ROI is daunting, especially for small manufacturers. | [13] IJPHM 12(1) | PR / GOV | SURVEY |
| Uncertain ROI is among the top three concerns, mainly because heavy customisation means heavy up-front investment. | [25] | CONS | SURVEY |
| Consultancy claims (not independent evidence): PdM can cut maintenance-planning time by 20-50%, raise uptime and availability by 10-20%, and cut overall maintenance costs by 5-10%. Deloitte sources these to its own internal analysis of client work. Its case figures come from other reports, and some have no citation. | [40] Deloitte Insights, 9 May 2017 | CONS | client work |
| PwC/Mainnovation 2018 (268 companies; Belgium, Germany, Netherlands): 60% of respondents increased uptime, by 9% on average. 60% had concrete PdM 4.0 plans (49% in 2017). The results are self-reported. | [26], [27] | CONS | SURVEY |
| The figure of about 11% at the top PdM 4.0 maturity level in the 2017 PwC/Mainnovation study is **UNVERIFIED at primary level**: seen only in a secondary summary [28], and the PwC PDF returned 403. | [28] | secondary | SURVEY |
| Siemens "True Cost of Downtime 2024" (vendor-sponsored, see the note below):<br>- 181 online interviews (Apr 2019-Mar 2023) with maintenance, engineering and IT staff at large firms in automotive, FMCG, heavy industry, and oil and gas;<br>- unplanned downtime costs the Fortune Global 500 about $1.4T/year (11% of revenue);<br>- an average large plant loses 27 h/month (39 h in 2019);<br>- almost half of firms surveyed have PdM teams;<br>- full adoption could save $233B through a 40% cut in maintenance costs. | [41] | **VEND** | SURVEY + vendor deployment data, extrapolated |
| MaintainX "State of Industrial Maintenance 2025" (1,320 US/Canada maintenance professionals): 44% have adopted or are piloting AI, and 65% expect to implement AI maintenance by 2026. The page shows inconsistent dates (May vs Nov 2025). | [29] | **VEND** | SURVEY |

Note on the Siemens report [41]: the benefit figures come from Senseye deployments, and the Fortune Global 500 dollar figures are extrapolations from the survey sample. They are marketing estimates, not measurements.

**Widely repeated figures that could not be verified at source.** Do not quote these.
- "PdM reduces downtime 30-50% and extends machine life 20-40%" (attributed to McKinsey, 2017) is **UNVERIFIED**.
- The DOE/FEMP "10x ROI, 70-75% fewer breakdowns" figures are **UNVERIFIED**: the guide could not be retrieved.

### 2.10 Sensor and installation cost

| Claim | Source | Type | Data |
|---|---|---|---|
| Retrofitting older plants with sensors is very costly and uneconomical. Further costs come from IT infrastructure, data storage, software maintenance and vendor lock-in. | [4] | PR | INTERVIEW |
| Hardware price points for a discontinued wireless vibration and temperature product, AWS Monitron (US list):<br>- starter kit of 5 sensors plus gateway: $715;<br>- 5-pack of sensors: $575 (about $115 each);<br>- 5-pack of Ex-rated sensors: $800;<br>- gateway: $140 (Wi-Fi) or $180 (Ethernet);<br>- service: $50 per sensor per year.<br>The product has been closed to new customers since 31 Oct 2024. | [20], [18] | VEND (price list) | - |
| Example SaaS list prices (AWS Marketplace, 12-month contracts):<br>- Shoreline AI: $30,000 for a 25-sensor starter kit and $59,000 for 50 sensors;<br>- Sclera "Optima" asset-intelligence platform: $5,000 for up to 100 assets, up to $250,000 for up to 25,000 assets.<br>Neither listing offers a free trial. | [36], [37] | VEND (price list) | - |
| Installation labour, cabling and network costs per measurement point are **UNVERIFIED**: no primary source was found. | - | - | - |

### 2.11 Large-vendor exits (market signal)

- AWS closed Amazon Monitron (sensors plus PdM service) to new customers from 31 Oct 2024. Devices were sold until July 2025, and warranty and security fixes continue but no new features [18].
- AWS discontinued support for Amazon Lookout for Equipment (an ML anomaly-detection service for industrial sensor data) on 7 Oct 2026 [19].
- Neither notice gives a reason. Any explanation of why is **UNVERIFIED** speculation and is not offered here.

---

## 3. What evidence industrial buyers require before adopting or paying

### 3.1 What the sources say buyers and successful adopters look for

| Evidence need | What the source says | Source | Type |
|---|---|---|---|
| Quantified, bottom-line value | McKinsey advises approaching the opportunity "bottom-line value backwards" rather than technology-forward, with a phased roadmap and an ROI roadmap. | [1] | CONS |
| Quantified, bottom-line value | Plant Services: maintenance must monetise tangible and intangible benefits and tie them to production data. | [46] | TRADE |
| Quantified, bottom-line value | Hoffmann & Lasch call for PdM-specific KPIs and holistic direct-plus-indirect cost calculation. | [4] | PR |
| Small, low-risk pilot on suitable assets | Deloitte suggests piloting PdM on one or two well-suited assets, testing and learning before scaling. | [40] | CONS |
| Small, low-risk pilot on suitable assets | Interviewees describe small "lighthouse" projects with limited resources, a laboratory-style test field, and an agile, low-risk entry. | [4] | PR |
| Pilot results that show value quickly | WEF found pilots are usually 1-2 years and that ROI alignment blocks scaling. | [2] | CONS |
| Decision relevance, not data availability | Golightly et al.: design should be decision-led rather than data-led. | [5] | PR |
| Security assurance | The 12 CISA Secure by Demand elements, e.g. a threat model, SBOM, vulnerability disclosure programme, baseline logging, no default passwords and data protection to and from the vendor. | [15] | GOV |
| Security assurance | ISA/IEC 62443-4-1 / ISASecure SDLA covers the supplier development lifecycle. | [35] | STD |
| Security assurance | Indian power sector (draft): documented and tested recovery procedures, and patches for all components over the contract period. | [43] | GOV draft |
| Security assurance | Bain: customers would buy more and pay more if security concerns were addressed. | [25] | CONS |
| Integration effort and data portability | Bain finds integration, interoperability and data portability underestimated by vendors. | [25] | CONS |
| Integration effort and data portability | CISA asks for open standards and operator "ownership", meaning minimal dependency on the vendor. | [15] | GOV |
| Integration effort and data portability | Interviewees want open interfaces. | [4] | PR |
| Reference customers and scale | Vendor case studies lead with customer profile, fleet size, ROI time and warning lead-time, e.g. more than 10,000 machines, ROI in under 3 months, up to 6 months' warning, more than 500 concurrent users. | [39] | VEND |
| Reference customers and scale | ABI reports Nissan and Alcoa claim ROI in under 3 months. | [38] | CONS reporting customer/VEND claims |
| Risk transfer | Senseye "ROI Lock" (Jan 2022, with reinsurer SCOR): the subscription is refunded if eligible customers do not reach ROI within 12 months. | [38] | CONS reporting VEND offer |
| Measured downtime reductions | The only independent, measured cross-plant figures found are NIST's associational survey results: 18.5% less unplanned downtime for the predictive-leaning group vs the preventive-leaning group. Most other downtime figures are self-reported (PwC: 9% average uptime gain) or vendor-extrapolated (Siemens). | [13], [26], [41] | PR/GOV; CONS; VEND |
| Payback period | The vendor-reported payback figures found are under 3 months [39] [38] and 4-6 months in a Siemens aluminium case (search snippet only; **UNVERIFIED**). | [39], [38] | VEND |
| Payback period | No independent source on the payback period buyers *require* was found. **UNVERIFIED.** | - | - |
| Payback period | Interviewees say benefits appear only in the medium to long term. | [4] | PR |

### 3.2 Gap between the evidence buyers want and the evidence the market offers

- Most "measured reduction in downtime" numbers in circulation are either self-reported survey results [26] [13] or vendor deployment data extrapolated to whole populations [41].
- The peer-reviewed literature repeatedly notes missing PdM-specific KPIs [4] and the absence of validated, production-relevant benchmarks:
  - [42] notes the reliance on limited public data;
  - NASA's own rationale for simulated data is that field run-to-failure data are scarce [8].

---

## 4. How PdM software is typically purchased

| Topic | Evidence | Source | Type |
|---|---|---|---|
| Pilot then scale | Most firms pilot first; pilots often take 1-2 years; scaling is the hard step. | [1], [2] | CONS |
| Pilot then scale | Lighthouse or pilot projects by small teams, then rollout. | [4] | PR |
| Pilot then scale | A customer can start with one deployment and then roll out to all machines. | [38] | CONS |
| Subscription model | Senseye is sold as a "PdM subscription". | [38] | CONS/VEND |
| Subscription model | AWS Marketplace PdM listings are 12-month SaaS contracts priced per sensor or per asset tier, with no refunds on annual subscriptions in at least one listing. | [36], [37] | VEND |
| Subscription model | Monitron used a hardware purchase plus a per-sensor annual service fee. | [20] | VEND |
| Capex vs opex | How buyers classify these costs (hardware capex vs software opex) is **UNVERIFIED**: no accounting or buyer-survey source was opened. | - | - |
| Vendor qualification (private sector example) | Tata Steel UK: becoming a qualified vendor is by invitation only, through the SAP Ariba vendor qualification process. Certificates must be kept up to date. This is the UK business; the Indian process was not verified. | [47] | primary (buyer website) |
| Security in procurement | CISA tells OT owners to integrate the 12 security elements into procurement and to consider regulation, e.g. the EU NIS2 Directive and the Cyber Resilience Act. | [15] | GOV |
| Indian public-sector procurement | GFR 2017 Rule 170(i) relaxes EMD and Rule 173(i) relaxes prior turnover and prior experience for DPIIT-recognised startups, subject to quality and technical specifications. GFR applies to central ministries, departments and CPSEs. | [30] | GOV |
| Indian public-sector procurement | GeM "Startup Runway" and CPPP registration let startups claim these exemptions. Some states (Odisha, Gujarat, Haryana) have their own relaxations. | [30] | GOV |
| Procurement friction | Interviewees cite long implementation and approval processes. | [4] | PR |

---

## 5. Who signs off

| Role | Evidence | Source | Type |
|---|---|---|---|
| Operations / OT (maintenance, production, engineering) | Bain: OT people were the key decision-makers or influencers in 85% of IoT purchasing decisions; the rest were joint IT-OT. The methodology is not stated. | [24] Bain, 12 Jan 2021 | CONS |
| Project owner | PdM projects are managed by the maintenance department, technical planning and/or production (or the service department for customer-service projects). | [23] | PR (11 practitioner interviews) |
| Executive sponsor | Management (e.g. business owner, asset manager, COO) usually acts as project sponsor: it initiates, supports and makes crucial decisions, and ensures alignment with corporate strategy. | [23] | PR |
| IT / production-IT | Supports system-architecture design. | [23] | PR |
| IT / production-IT | The PReMMa model includes cybersecurity concepts in architecture design. | [23] | PR |
| IT / production-IT | The respondents vendors survey include IT alongside maintenance and engineering. | [41] | VEND |
| OT security | CISA addresses its procurement guidance to OT "owners and operators". | [15] | GOV |
| OT security | The Indian power-sector draft requires each responsible entity to set up an Information Security Division. | [43] | GOV draft |
| End users (operators, technicians) | Asked to contribute to dashboard design. This improves acceptance. | [23] | PR |
| Finance | No verified source describes finance's formal sign-off step for PdM. Its influence is implied by ROI being a top barrier [2] [25] [4]. **The sign-off mechanics are UNVERIFIED.** | - | - |
| Interviewee roles in barrier studies | Plant and maintenance managers, plus service providers. | [4] | PR |

---

## 6. Implications for SentinelLoop (Inference: team reasoning, not sourced fact)

1. **Simulated-only evidence will not count as buyer evidence.**
   - C-MAPSS is SIM data [8] [9], and buyers ask for pilot results on their own assets [40] [4].
   - Present all current results as a "simulation-validated method", never as a demonstrated downtime reduction.
2. **RUL needs labels the field rarely has.**
   - Failure times are censored by preventive maintenance [6] and buried in messy work orders [33]. The RUL head therefore cannot be the entry product at a plant without run-to-failure history.
   - The label-free healthy-baseline anomaly index and the drift monitor are a more realistic pilot entry point.
   - A censoring-aware (survival) formulation would be needed before RUL is claimed on field data.
3. **Alert budget is a product requirement.**
   - The README reports that the fleet-level rule escalates 25-36% of healthy engines while a fleet alarm is active.
   - Given the cry-wolf evidence [10] and the false-alarm cost evidence [34], a pilot should report false alarms per asset per month and the investigation cost, alongside detection.
4. **Explanations are not enough on their own.**
   - Local explanations can lower trust [12].
   - The deterministic triage rules and the hash-chained audit record are a better fit for "decision-led" design [5]. They should be shown to technicians early, as [23] recommends.
5. **Integration is part of the product.**
   - Work orders currently land in SQLite/Streamlit.
   - A CSV/API export in a CMMS-importable shape, plus a mapping to the buyer's failure codes, addresses the integration barrier [25] [4].
6. **A security pack is needed before any plant conversation.**
   - Prepare a one-page threat model, SBOM, logging description, data-flow statement (offline/on-prem, no inbound connection), patch policy and vulnerability-disclosure contact, mapped to the 12 CISA elements [15].
   - An offline "replay historical data" pilot avoids an OT network connection entirely and sidesteps the riskiest review [4].
7. **Do not quote headline ROI figures.**
   - Provide a cost model that takes the buyer's own downtime cost, false-alarm investigation cost and sensor cost.
   - Treat the NIST associational results [13] as the most defensible external reference.
8. **Route to market for a student team in India.**
   - DPIIT startup recognition unlocks the GFR relaxations on prior turnover, experience and EMD for central-government buyers [30].
   - Private buyers qualify vendors by invitation only [47], so a sponsor inside the plant (maintenance or reliability head) is a prerequisite [24] [23].
   - The incumbents' exits [18] [19] suggest buyers may weigh vendor longevity (an inference).

---

## 7. Leads not verified (do not cite without opening the primary source)

- McKinsey, "Establishing the right analytics-based maintenance strategy": false positives can offset PdM savings. The page timed out and only a search snippet was seen.
- McKinsey (2017, attributed): PdM reduces downtime by 30-50% and extends machine life by 20-40%. No primary source was found.
- DOE FEMP O&M Best Practices Guide Release 3.0 (2010): commonly cited PdM ROI and breakdown-reduction figures. The PDF could not be retrieved.
- PwC/Mainnovation 2017: about 11% of companies at maturity level 4. Seen only in a secondary summary [28]; the PwC PDF returned 403.
- ISA-18.2 / EEMUA 191 numeric alarm-rate benchmarks. Only vendor and training summaries were seen.
- Ingemarsdotter et al. 2021, J. Cleaner Production 296:126420 [22] identifies 19 challenges and 16 solutions in CBM at 3 OEMs. Only the abstract page was opened, so the list of challenges is UNVERIFIED.
- Terho & Jalkala 2017, Industrial Marketing Management 64:175-186 (customer reference marketing). The page was blocked, so its findings on reference customers are UNVERIFIED.
- Verdantix, "Best Practices: Transitioning to Predictive Maintenance" (256-manager survey). Paywalled and not opened.
- Arias Chao et al. 2021, Data 6(1):5 (N-CMAPSS) and its stated limitations of the original C-MAPSS (six cruise snapshots; fault onset independent of history). The MDPI page returned 403.
- Siemens aluminium case study claiming ROI in 4-6 months. Seen only in a search snippet.

## 8. Gaps

- No peer-reviewed source was verified on the payback period that industrial buyers *require*, as opposed to what vendors report.
- No verified source on the finance department's formal role or on capex/opex treatment of PdM spending.
- No India-specific peer-reviewed study of PdM (as opposed to Industry 4.0 in general) adoption barriers was verified.
- No field-measured false-alarm rates per asset from a deployed industrial PdM system were found.
- The final status of India's CEA power-sector cybersecurity regulations was not verified.
- No primary source on installation labour cost per measurement point was found.
- The WebSearch budget for the turn was exhausted before searches on Indian private-sector PdM pilots (e.g. startup programmes at large Indian manufacturers) could be run.

---

## Sources

All accessed 2026-10-18.

1. McKinsey & Company / Digital McKinsey, "Digital Manufacturing - escaping pilot purgatory" (Digital Manufacturing Global Expert Survey 2018). https://karriere.mckinsey.de/~/media/mckinsey/business%20functions/operations/our%20insights/how%20digital%20manufacturing%20can%20escape%20pilot%20purgatory/digital-manufacturing-escaping-pilot-purgatory.pdf
2. World Economic Forum with McKinsey, "Fourth Industrial Revolution: Beacons of Technology and Innovation in Manufacturing", White Paper, Jan 2019. https://www3.weforum.org/docs/WEF_4IR_Beacons_of_Technology_and_Innovation_in_Manufacturing_report_2019.pdf?lng=en
3. T. Comstock, "Pilot Purgatory in Industrial Transformation (IX) is Fake News", LNS Research blog, 9 Nov 2021. https://blog.lnsresearch.com/pilot-purgatory-in-industrial-transformation-is-fake-news
4. M. A. Hoffmann, R. Lasch, "Unlocking the Potential of Predictive Maintenance for Intelligent Manufacturing: a Case Study on Potentials, Barriers, and Critical Success Factors", Schmalenbach Journal of Business Research 77:27-55 (2025), doi:10.1007/s41471-024-00204-3. https://link.springer.com/article/10.1007/s41471-024-00204-3
5. D. Golightly, G. Kefalidou, S. Sharples, "A cross-sector analysis of human and organisational factors in the deployment of data-driven predictive maintenance", Information Systems and e-Business Management 16(3):627-648 (2018), doi:10.1007/s10257-017-0343-1 (IDEAS/RePEc record). https://ideas.repec.org/a/spr/infsem/v16y2018i3d10.1007_s10257-017-0343-1.html
6. A. Sánchez-Herguedas et al., "Optimisation of Maintenance Policies Based on Right-Censored Failure Data Using a Semi-Markovian Approach", Sensors 22(4):1432 (2022). https://pmc.ncbi.nlm.nih.gov/articles/PMC8875710/
7. R. van Dinter, B. Tekinerdogan, C. Catal, "Predictive maintenance using digital twins: A systematic literature review", Information and Software Technology 151 (2022), doi:10.1016/j.infsof.2022.107008 (AGRIS record). https://agris.fao.org/search/fr/records/669f707f00eb85b7d72cf732
8. NASA / Data.gov, "Simulating Degradation Data for Prognostic Algorithm Development" (C-MAPSS dataset record). https://catalog.data.gov/dataset/simulating-degradation-data-for-prognostic-algorithm-development
9. NASA Intelligent Systems Division, PCoE Data Set Repository. https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/
10. R. Wiczorek, J. Meyer, "Effects of Trust, Self-Confidence, and Feedback on the Use of Decision Automation", Frontiers in Psychology 10:519 (2019). https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2019.00519/full
11. L. Cummins et al., "Explainable Predictive Maintenance: A Survey of Current Methods, Challenges and Opportunities", arXiv:2401.07871 (published in IEEE Access 12, 2024). https://arxiv.org/abs/2401.07871v1
12. A. Pedraza, "'How can I trust it?' Exploring the role of explanations in predictive maintenance models", MS thesis, University of Wisconsin-Madison, 2024. https://minds.wisc.edu/handle/1793/85271
13. D. S. Thomas, B. A. Weiss, "Maintenance Costs and Advanced Maintenance Techniques in Manufacturing Machinery: Survey and Analysis", International Journal of Prognostics and Health Management 12(1) (2021), doi:10.36001/ijphm.2021.v12i1.2883. https://pmc.ncbi.nlm.nih.gov/articles/PMC9890517/
14. CISA, "CISA and US and International Partners Publish Guidance on Priority Considerations for Product Selection for OT Owners and Operators", alert, 13 Jan 2025. https://cisa.gov/news-events/alerts/2025/01/13/cisa-and-us-and-international-partners-publish-guidance-priority-considerations-product-selection-ot
15. CISA et al., "Secure by Demand: Priority Considerations for Operational Technology Owners and Operators when Selecting Digital Products", 13 Jan 2025 (IC3-hosted copy of the joint guide). https://www.ic3.gov/CSA/2025/250113.pdf
16. NCSC New Zealand, "Secure by Demand for OT owners and operators". https://www.ncsc.govt.nz/protect-your-organisation/secure-by-demand-for-ot-owners-and-operators/
17. NIST CSRC, SP 800-82 Rev. 3, "Guide to Operational Technology (OT) Security", Sept 2023. https://csrc.nist.gov/pubs/sp/800/82/r3/final
18. AWS Machine Learning Blog (S. Gillen), "Maintain access and consider alternatives for Amazon Monitron", 1 Oct 2024. https://aws.amazon.com/blogs/machine-learning/maintain-access-and-consider-alternatives-for-amazon-monitron
19. AWS, Amazon Lookout for Equipment product page (end-of-support notice). https://aws.amazon.com/lookout-for-equipment
20. AWS, Amazon Monitron pricing page. https://aws.amazon.com/monitron/pricing/
21. M. Öhman, J. Bokrantz, J. Holmström, "When Technology Never Quite Arrives: The Perpetual Emergence of Condition-Based Maintenance", 24th International Working Seminar on Production Economics, 2026 (Chalmers record). https://research.chalmers.se/en/publication/550931
22. E. Ingemarsdotter et al., "Challenges and solutions in condition-based maintenance implementation - A multiple case study", Journal of Cleaner Production 296:126420 (2021) (TU Delft record; abstract only). https://research.tudelft.nl/en/publications/challenges-and-solutions-in-condition-based-maintenance-implement/
23. C. Wagner, B. Hellingrath, "Supporting the Implementation of Predictive Maintenance - a Process Reference Model", International Journal of Prognostics and Health Management (2021). https://papers.phmsociety.org/index.php/ijphm/article/download/2933/1736
24. J. Murphy (Bain & Company), "Selling IoT Solutions to Experts", 12 Jan 2021. https://www.bain.com/insights/selling-iot-solutions-to-experts/
25. Bain & Company, press release "Bain predicts the IoT market will more than double by 2021", 8 Aug 2018. https://www.bain.com/about/media-center/press-releases/2018/bain-predicts-the-iot-market-will-more-than-double-by-2021/
26. Maintworld, "Predictive Maintenance 4.0 provides an average of nine percent uptime increase", 25 Sep 2018 (reporting the PwC/Mainnovation study). https://old.maintworld.com/Asset-Management/Predictive-Maintenance-4.0-provides-an-average-of-nine-percent-uptime-increase
27. Mainnovation, "Predictive Maintenance 4.0" publication page (268 companies, with PwC), 25 Sep 2018. https://www.mainnovation.com/publications/predictive-maintenance-4-0/
28. ReliaMag, "Predictive Maintenance Adoption Rates: What the Surveys Show" (secondary summary; used only to flag leads). https://reliamag.com/maintenance-and-reliability/predictive-maintenance-adoption-rates/
29. MaintainX newsroom, "State of Industrial Maintenance Report 2025" (vendor-sponsored). https://www.getmaintainx.com/newsroom/state-of-industrial-maintenance-report-2025
30. Startup India (DPIIT), "Procurement by Government". https://www.startupindia.gov.in/content/sih/en/public_procurement.html
31. M. Goswami, Y. Daultani, "Make-in-India and Industry 4.0: technology readiness of select firms, barriers and socio-technical implications", The TQM Journal 34(6):1485-1505 (2022), doi:10.1108/TQM-06-2021-0179. https://www.emerald.com/insight/content/doi/10.1108/TQM-06-2021-0179/full/html
32. NIST, "Adapting natural language processing for technical text" (Dima, Lukens, Hodkiewicz, Sexton, Brundage), Applied AI Letters 2(3), 2021. https://www.nist.gov/publications/adapting-natural-language-processing-technical-text
33. M. Hodkiewicz, M. T. Ho, "Cleaning historical maintenance work order data for reliability analysis", Journal of Quality in Maintenance Engineering 22(2):146-163 (2016), doi:10.1108/JQME-04-2015-0013. https://www.emerald.com/insight/content/doi/10.1108/JQME-04-2015-0013/full/html
34. A. May, D. McMillan, "Condition based maintenance for offshore wind turbines: the effects of false alarms from condition monitoring systems", in Safety, Reliability and Risk Analysis: Beyond the Horizon, CRC Press, 2013, pp. 783-789 (Strathprints record). https://strathprints.strath.ac.uk/54903/
35. ISA, "ISA/IEC 62443 Series of Standards". https://www.isa.org/62443
36. AWS Marketplace, Shoreline AI, "Asset Management with Predictive Maintenance & Emission Monitoring" listing. https://aws.amazon.com/marketplace/pp/prodview-lf7avea7ktj4e
37. AWS Marketplace, Sclera Holdings, "Optima - An Asset Intelligence Platform" listing. https://aws.amazon.com/marketplace/pp/prodview-nrwbmmqg5t4qa
38. ABI Research, "Siemens Snaps Up Senseye to Expand Its Predictive Maintenance Expertise", 29 Jul 2022. https://www.abiresearch.com/market-research/insight/7780896-siemens-snaps-up-senseye-to-expand-its-pre?hsLang=en
39. Siemens AG, "Global Automotive Manufacturer: Senseye Predictive Maintenance Increases OEE" (case study, 2023; vendor marketing). https://assets.new.siemens.com/siemens/assets/api/uuid:5803c43a-d25f-4b59-871c-ccfd43067abb/Automotivev2_original.pdf
40. E. Deuel, M. Chandramouli, C. Coleman, S. Damodaran, "Making maintenance smarter: Predictive maintenance and the digital supply network", Deloitte Insights, 9 May 2017. https://www.deloitte.com/us/en/insights/industry/manufacturing-industrial-products/industry-4-0/using-predictive-technologies-for-asset-maintenance.html
41. Siemens AG, "The True Cost of Downtime 2024" (vendor-sponsored report). https://assets.new.siemens.com/siemens/assets/api/uuid:1b43afb5-2d07-47f7-9eb7-893fe7d0bc59/TCOD-2024_original.pdf
42. F. Ramzan, D. R. Recupero, "A Literature Review on Enhancing Predictive Maintenance in Smart Manufacturing Industries: Fostering Human-Technology Collaboration and Overcoming Data Scarcity Limitations with Advanced AI Models", Operations Research Forum 6:181 (2025), doi:10.1007/s43069-025-00584-0. https://link.springer.com/article/10.1007/s43069-025-00584-0
43. Indian Infrastructure, "CEA notifies draft CEA (Cyber Security in Power Sector) Regulations, 2024", 21 Aug 2024. https://indianinfrastructure.com/2024/08/21/cea-notifies-draft-cea-cyber-security-in-power-sector-regulations-2024/
44. Reliable Plant, "Poll finds challenges with PdM sustainability can overshadow successes" (Azima DLI survey; vendor-sponsored). https://www.reliableplant.com/Articles/Print/23750?id=23750
45. Process Engineering, "Discovering that digital is essential for predictive maintenance", 12 Sep 2018 (Emory University / Presenso study). https://processengineering.co.uk/article/2024241/discovering-that-digital-is-essential-for-predictive-maintenance
46. K. M. Blanche, "4 obstacles to PdM success", Plant Services, 19 Jan 2021. https://www.plantservices.com/articles/2021/4-obstacles-to-pdm-success/
47. Tata Steel UK, "Ariba Suppliers Support Hub". https://www.tatasteeluk.com/suppliers/ariba
48. exida, "Alarm Management and ISA-18 - a Journey, Not a Destination" (white-paper page; opened, contained no numeric benchmarks). https://www.exida.com/Resources/Whitepapers/alarm-management-and-isa-18-a-journey-not-a-destination
