# R1: How industrial maintenance teams actually work

Research stream R1 for the SentinelLoop product team. Date of research and of every source access: 2026-10-18.
Web tools (WebSearch, WebFetch) were available and used. Every factual claim below carries the URL of a source that was opened in this session. Where a fact appeared only in a search-result snippet, or a source could not be opened, it is marked **UNVERIFIED**. Statements marked **Team inference** are our reasoning, not sourced facts.

Evidence labels used throughout:

- **Standard / body of knowledge**: the text of, or an official listing for, a standard or professional-body document.
- **Government**: a government agency or regulator.
- **Peer-reviewed**: journal or refereed conference paper.
- **Practitioner / trade**: consultancy articles, trade magazines, practitioner reviews. Useful, but secondary.
- **Vendor claim**: a vendor's own marketing or product page. Not independent.
- Data-type labels: **real field data** (recorded in operating plants), **real laboratory data**, **simulated data** (physics or system simulation, e.g. NASA C-MAPSS), **synthetic data** (artificially generated or invented examples), and **survey / self-reported data** (what managers say, not machine records).

---

## 0. Summary for the team

1. Maintenance work runs through a CMMS/EAM work order with a fixed lifecycle: request, approval, planning, scheduling, execution, close-out. Planners, schedulers, supervisors, crafts and storeroom staff each act on specific statuses ([SMRP 2018 workshop](https://pemac.org/sites/default/files/2018_SMRP_BPMW_Full_Day.pdf); [Lukens et al. 2019](https://papers.phmsociety.org/index.php/phmconf/article/download/836/phmc_19_836); [IBM Maximo status rules](https://www.ibm.com/support/pages/node/1112013)). A prediction only has value once it becomes a work order that goes through this pipeline.
2. Priority comes from two inputs: how critical the asset is and how urgent the work is. A common published method, RIME, combines the two in a lookup table and gives due-date codes from 1 to 30 days ([Reliabilityweb RIME case](https://reliabilityweb.com/en/articles/ranking-index-for-maintenance-expenditures); [Keeter, Priority vs Criticality](https://reliabilityweb.com/articles/entry/priority_vs_criticality)). In practice, priority is often set by whoever complains loudest ([Reliabilityweb](https://reliabilityweb.com/articles/entry/work_prioritization_emotion_vs._logic)).
3. Plants still do a lot of reactive work. In a NIST survey of 71 US manufacturing establishments, the average mix was 45.7% reactive, 31.8% preventive, 17.3% predictive and 4.7% other (2016 data, self-reported). The authors say the associations they report do not prove causation ([NIST AMS 100-34](https://nvlpubs.nist.gov/nistpubs/ams/NIST.AMS.100-34.pdf); [NIST page](https://www.nist.gov/el/applied-economics-office/manufacturing-machinery-maintenance); [Thomas and Weiss 2021](https://pmc.ncbi.nlm.nih.gov/articles/PMC9890517/)).
4. Work-order history is the data every plant has, and it is low quality. Structured fields are often missing or wrong. The free text holds the real information ([Hodkiewicz and Ho 2016](https://www.emerald.com/insight/content/doi/10.1108/JQME-04-2015-0013/full/html); [Lukens et al. 2019](https://papers.phmsociety.org/index.php/phmconf/article/download/836/phmc_19_836); [Sexton et al. 2019](https://papers.phmsociety.org/index.php/phmconf/article/download/790/phmc_19_790)). In one case study only about 20–30% of work orders carried cost data until the plant fixed its work process ([Lukens et al. 2019](https://papers.phmsociety.org/index.php/phmconf/article/download/836/phmc_19_836)).
5. Standards already define the pipeline SentinelLoop implements. ISO 13374 / MIMOSA OSA-CBM has six blocks: data acquisition, data manipulation, state detection, health assessment, prognostic assessment and advisory generation ([MIMOSA 2006](https://www.mimosa.org/wp-content/uploads/2006-08-28_Including_OSA-CBM_and_OSA-EAI_in_Integrated_System_Health_Management.pdf); [MIMOSA OSA-CBM page](https://www.mimosa.org/mimosa-osa-cbm/)). ISO 14224 defines the minimum failure data a work order should carry ([Selvik, ISO/TC 67 technical editor](https://standard.no/globalassets/fagomrader-sektorer/petroleum/rio_de_janeiro/4-collection_and_exchange_of_reliability_data-j_t_selvik.pdf)). The prognostics standard ISO 13381-1 was reissued in September 2025, and the 2015 edition is withdrawn ([SCC listing](https://ccn-scc.ca/standardsdb/standards/8189734); [ISS listing](https://iss.rs/en/project/show/iso:proj:51436)).
6. Work gets delayed by parts and materials, approvals, plant access and permits, schedule breaks from reactive work, and weak planning. CMMS status codes themselves encode these waits, for example "waiting on material" and "waiting on plant condition" ([IBM Maximo](https://www.ibm.com/support/pages/node/1112013); [Assetivity case study](https://www.assetivity.com.au/articles/asset-management/coordinating-activity-between-maintenance-and-supply-a-case-study/)).
7. Control rooms already suffer alarm overload. Benchmark guidance targets about one annunciated alarm per 10 minutes per console and defines a flood as more than 10 alarms in 10 minutes ([IChemE Safety Centre 2021](https://www.icheme.org/media/17392/lc-0151_21-lead-process-safety-metrics-alarm-rationalisation-final.pdf)). Any escalation SentinelLoop generates adds to that load.
8. Evidence on Indian practice is thin. We found small, regional academic surveys, the CII–JIPM TPM ecosystem, the government ZED scheme parameter "Planned Maintenance & Calibration", the new OSH Code, and a new national qualification for PdM data acquisition. We found **no** sourced quantitative evidence on maintenance mix, CMMS data quality, wrench time or work-order cycle time in Indian plants (Section 8).

---

## 1. Reference frameworks: what each standard gives us

| Framework | Edition / status (as verified) | What it contributes | Source(s) |
|---|---|---|---|
| **EN 13306** Maintenance terminology | EN 13306:2017. Approved by CEN on 16 July 2017; supersedes EN 13306:2010; written by CEN/TC 319. BSI lists BS EN 13306:2017 as current and under review. | Generic terms for the technical, administrative and managerial sides of maintenance. Clause 7 covers types of maintenance and clause 8 maintenance activities. Annex A is an overview of maintenance, and informative **Annex E is a criticality matrix**. Software-only maintenance is excluded. | [STN EN 13306:2018 preview (Slovak adoption of EN 13306:2017)](https://normy.normoff.gov.sk/norma/127326/nahlad); [BSI listing](https://knowledge.bsigroup.com/products/maintenance-maintenance-terminology) |
| EN 13306 definitions of condition-based and predictive maintenance | Wording seen only in a secondary glossary that does not cite the edition (**partially verified**) | Condition-based maintenance is preventive maintenance that includes assessing physical condition, analysing it, and any resulting maintenance actions. Predictive maintenance is condition-based maintenance carried out on a forecast derived from repeated analysis of degradation parameters. On this reading, an RUL-driven work order is predictive maintenance in EN 13306 terms. | [Techniques de l'Ingénieur glossary](https://techniques-ingenieur.fr/en/resources/article/ti095/preventive-maintenance-mt9571/v1/glossary-9) |
| **ISO 55000** Asset management, overview, principles, terminology | ISO 55000:2024 | Provides overview, terminology and principles for asset management systems, and the context for ISO 55001 (requirements) and ISO 55002 (guidance). The 2024 edition introduces outcomes, integration of management systems and a maturity concept. The ISO 55000 definition of "asset management" was **not seen** in an opened source (UNVERIFIED wording). | [ISO/TC 251 committee page](https://committee.iso.org/sites/tc251/home/projects/published/iso-55000.html) |
| **ISO 14224** Collection and exchange of reliability and maintenance (RM) data | ISO 14224:2016 (listing verified). The detailed field and taxonomy information comes from a Nov 2014 presentation describing the 2006 (2nd) edition, so 2016 wording may differ. "Edition 3" and "confirmed 2022" were seen only in search snippets (UNVERIFIED). | Three data categories: equipment (taxonomy, attributes), failure (cause, consequence), maintenance (action, resources, consequence, downtime). A 9-level taxonomy from industry down to part. Failure mode is normally recorded at equipment-unit level 6. Generic classes of failure mechanism and failure cause. A minimum mandatory dataset. Excludes direct cost data, laboratory test data and analysis methods. Scope is petroleum, petrochemical and natural gas, but its taxonomy is widely borrowed: SMRP recommends it as a model hierarchy. | [EVS listing](https://evs.ee/en/evs-en-iso-14224-2016); [Selvik (ISO/TC 67/WG4), 2014](https://standard.no/globalassets/fagomrader-sektorer/petroleum/rio_de_janeiro/4-collection_and_exchange_of_reliability_data-j_t_selvik.pdf); [SMRP 2018 workshop](https://pemac.org/sites/default/files/2018_SMRP_BPMW_Full_Day.pdf) |
| **ISO 17359** CM&D of machines, general guidelines | ISO 17359:2018 | General procedure for setting up a condition-monitoring programme, with references to the associated standards. Applies to all machines. The detailed steps sit in the paid text (UNVERIFIED). | [ASN listing](https://asn.sn/en/node/17332) |
| **ISO 13381-1** Prognostics, Part 1 | **ISO 13381-1:2025** (published 2025-09-01). The 2015 edition was withdrawn on 2 Sept 2025. Title is now "General guidelines and requirements". | Guidance **and requirements** for developing and applying prognosis processes, and shared prognostics concepts for developers, providers, users and manufacturers. SentinelLoop's RUL-with-interval output should be described in this standard's vocabulary. Clause-level content was not opened (UNVERIFIED). | [SCC listing](https://ccn-scc.ca/standardsdb/standards/8189734); [ISS listing](https://iss.rs/en/project/show/iso:proj:51436) |
| **ISO 13374-1** CM&D data processing, communication and presentation | ISO 13374-1:2003, confirmed 27 Mar 2025 | General guidelines for software specifications covering the processing, communication and presentation of CM&D information. | [ISS listing](https://iss.rs/en/project/show/iso:proj:21832) |
| **MIMOSA OSA-CBM** | Latest listed release 3.3.1 (29 June 2010) | Implements the ISO 13374 functional specification and adds data structures and interfaces. Six blocks: **Data Acquisition, Data Manipulation, State Detection, Health Assessment, Prognostics Assessment, Advisory Generation**. The block outputs carry data quality, health grade, future failures, recommendations, **evidence and explanation**. It does not prescribe algorithms. The companion OSA-EAI covers work management, the asset registry, and condition and reliability data. | [MIMOSA OSA-CBM](https://www.mimosa.org/mimosa-osa-cbm/); [MIMOSA 2006 presentation](https://www.mimosa.org/wp-content/uploads/2006-08-28_Including_OSA-CBM_and_OSA-EAI_in_Integrated_System_Health_Management.pdf) |
| **ISO 13373-1** Vibration CM, general procedures | ISO 13373-1:2002 ("confirmed 2024" seen only in a search snippet, UNVERIFIED) | Guidelines for vibration measurement and data collection, covering both continuous and periodic (non-continuous) monitoring. | [ASN listing](https://asn.sn/en/node/47636) |
| **SMRP Body of Knowledge / Best Practices** | The 7th edition is current and has 70+ metrics and guidelines, free to members. The metric numbers below come from a 2018 SMRP workshop based on the 5th edition, so numbering may have changed. | Five pillars: Business & Management, Manufacturing Process Reliability, Equipment Reliability, Organization & Leadership, Work Management. Each metric has 10 elements: definition, objectives, formula, component definitions, qualifications, sample calculation, best-in-class target, cautions, harmonization comments, references. | [SMRP Best Practices page](https://smrp.org/?p=57); [SMRP 2018 workshop](https://pemac.org/sites/default/files/2018_SMRP_BPMW_Full_Day.pdf) |
| **ANSI/ISA-18.2-2016 / IEC 62682 / EEMUA 191** (alarm management) | Seen through IChemE Safety Centre guidance (Nov 2021); the standards themselves were not opened | Alarm lifecycle and performance metrics (Section 6.4). | [IChemE Safety Centre](https://www.icheme.org/media/17392/lc-0151_21-lead-process-safety-metrics-alarm-rationalisation-final.pdf) |
| **NIST SP 800-82 Rev. 3** (OT security) | Sept 2023 | OT architecture (SCADA, PLC, historian, DMZ, Purdue levels), a cross-functional OT security team, and maintenance-tracking requirements for OT assets. | [NIST SP 800-82r3](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-82r3.pdf) |
| Safety of maintenance work | OSHA 29 CFR 1910.147 (US); HSE HSG250 (UK, 2005); India: OSH Code 2020 and Factories Act 1948 s.22 | Lockout/tagout, permit-to-work, and who may work on moving machinery (Section 2, EHS row, and Section 8). | [OSHA 1910.147](https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.147); [HSE HSG250](https://www.hse.gov.uk/pubns/books/hsg250.htm) |

**Team inference.** SentinelLoop's architecture already lines up with OSA-CBM: ingest and cleaning is DA/DM, the anomaly index and drift monitor are SD, the health index is HA, RUL with a conformal interval is PA, and the Triage Agent is AG. OSA-CBM expects each block to carry data quality and "evidence and explanation" with its output, which our audit record already does. Describing the product in this vocabulary costs nothing and makes it more credible to reliability engineers.

---

## 2. Roles and what each one decides

There is no single standard that defines job titles. The table combines the SMRP work-process description, the Gulati and Smith process as reproduced by Lukens et al., Palmer's planning principles (through a practitioner review), the BLS occupational description, NIST SP 800-82r3 for OT security, and the safety regulations.

| Role | What they decide / do | Evidence | Source(s) |
|---|---|---|---|
| **Requester (often an operator)** | Raises the work request. In SMRP's work-order audit the requester is one of the parties examined. | Body of knowledge | [SMRP 2018](https://pemac.org/sites/default/files/2018_SMRP_BPMW_Full_Day.pdf) |
| **Asset / resource coordinator, or approver** | Receives the request, **prioritizes it** and routes it to planning. Approvers work the queue of work orders in "created" status. | Peer-reviewed (citing Gulati and Smith 2013); body of knowledge | [Lukens et al. 2019](https://papers.phmsociety.org/index.php/phmconf/article/download/836/phmc_19_836); [SMRP 2018](https://pemac.org/sites/default/files/2018_SMRP_BPMW_Full_Day.pdf) |
| **Maintenance planner** | Plans the job and builds the work package: materials, tools, procedures, drawings, equipment history, time estimates, manpower and external resources such as cranes. In Palmer's model the planner works only on future work, is located apart from the crews so breakdowns do not pull them away, and stays out of breakdowns and jobs already started. SMRP tracks planner productivity and the craft-worker-to-planner ratio. | Practitioner review of Palmer's handbook; body of knowledge | [Accendo review of Palmer](https://accendoreliability.com/review-maintenance-planning-scheduling-handbook-doc-palmer/); [Lukens et al.](https://papers.phmsociety.org/index.php/phmconf/article/download/836/phmc_19_836); [SMRP 2018](https://pemac.org/sites/default/files/2018_SMRP_BPMW_Full_Day.pdf) |
| **Maintenance scheduler** | Works with the craft supervisor to decide **when** planned jobs are executed. Builds the weekly schedule from work orders in "ready to schedule" status. Schedule compliance is calculated weekly as part of scheduling, not necessarily inside the CMMS. | Peer-reviewed; body of knowledge | [Lukens et al.](https://papers.phmsociety.org/index.php/phmconf/article/download/836/phmc_19_836); [SMRP 2018](https://pemac.org/sites/default/files/2018_SMRP_BPMW_Full_Day.pdf) |
| **Craft supervisor** | Assigns who does each job, ensures quality, and ensures work details are recorded in the CMMS. Breakdown jobs go directly to the supervisor (Palmer). | Peer-reviewed; practitioner | [Lukens et al.](https://papers.phmsociety.org/index.php/phmconf/article/download/836/phmc_19_836); [Accendo](https://accendoreliability.com/review-maintenance-planning-scheduling-handbook-doc-palmer/) |
| **Maintenance technician / craft (mechanic, millwright)** | Diagnoses, disassembles, repairs or replaces, calibrates, lubricates, tests and runs initial batches. May use computerized diagnostics and vibration analysis. Often on call, on night or weekend shifts, with common overtime. Enters the close-out data: failure codes and free text. Sexton et al. show where this step goes wrong (Section 6.1). | Government; peer-reviewed | [BLS OOH](https://www.bls.gov/ooh/installation-maintenance-and-repair/industrial-machinery-mechanics-and-maintenance-workers-and-millwrights.htm); [Sexton et al. 2019](https://papers.phmsociety.org/index.php/phmconf/article/download/790/phmc_19_790) |
| **Storeroom / supply** | Holds MRO stock, kits and stages parts, expedites. SMRP's audit includes the storeroom attendant, and its metrics include stock-outs, inventory turns and inactive stock. Expediters follow up work orders in "waiting for material" status. | Body of knowledge; practitioner case | [SMRP 2018](https://pemac.org/sites/default/files/2018_SMRP_BPMW_Full_Day.pdf); [Assetivity 2024](https://www.assetivity.com.au/articles/asset-management/coordinating-activity-between-maintenance-and-supply-a-case-study/) |
| **Reliability engineer** | Decides strategy: criticality ranking, RCM/FMEA, PM and PdM programme content, bad-actor analysis, and data-quality fixes. In Keeter's description, criticality is assessed top-down (areas, then systems, then items) and the top-ranked items get RCM-type analysis. In the Lukens case study it was the reliability engineers who diagnosed and fixed the cost-capture process. No standards-body job definition was found (**UNVERIFIED as a formal role definition**). | Practitioner; peer-reviewed case | [Keeter](https://reliabilityweb.com/articles/entry/priority_vs_criticality); [Lukens et al.](https://papers.phmsociety.org/index.php/phmconf/article/download/836/phmc_19_836) |
| **Condition-monitoring analyst** | Collects route data and diagnoses faults. ISO 18436-2 certifies vibration personnel in Categories I–IV; the category content was seen only in a vendor flyer and a blog (**UNVERIFIED**). | Search snippet only | (no opened source) |
| **Maintenance manager** | SMRP frames the manager's three information needs: is work managed effectively (right work, efficiency, capacity versus input, improvement), is reliability at the needed level, and are labour, materials and money used well. Owns the metrics: maintenance cost as % of replacement asset value (RAV), planned work, schedule compliance, backlog, wrench time. | Body of knowledge | [SMRP 2018](https://pemac.org/sites/default/files/2018_SMRP_BPMW_Full_Day.pdf) |
| **Plant / operations manager** | Owns production. Decides when equipment can be released for maintenance; Maximo's "waiting on plant condition" status exists for this wait. Production impact enters priority-setting through the RIME work-type scale (e.g. "reduced production") and through criticality. No primary source spells out the operations manager's decision rights (**UNVERIFIED as a formal definition**). | Vendor documentation; practitioner | [IBM Maximo](https://www.ibm.com/support/pages/node/1112013); [Reliabilityweb RIME](https://reliabilityweb.com/en/articles/ranking-index-for-maintenance-expenditures) |
| **EHS (environment, health and safety)** | Controls hazardous energy and authorises work. Under OSHA 1910.147 the employer must have an energy-control programme (procedures, training, periodic inspection at least annually). An "authorized employee" applies the lock or tag and does the servicing; an "affected employee" operates or uses the machine. In petroleum, chemical and allied industries, permit-to-work systems are the norm (HSE HSG250). In India, Factories Act s.22 restricts who may examine, lubricate or adjust machinery in motion. The Act is now subsumed by the OSH Code 2020; see Section 8. | Government | [OSHA 1910.147](https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.147); [HSE HSG250](https://www.hse.gov.uk/pubns/books/hsg250.htm); [Factories Act s.22 (AdvocateKhoj)](https://www.advocatekhoj.com/library/bareacts/factories/22.php) |
| **IT / OT security** | NIST recommends a cross-functional OT security team: IT staff, control engineer, control system operator, security specialist and enterprise risk management, with safety experts recommended. Enterprise-to-operations traffic should pass through a DMZ, with separate IT and OT authentication. Remote maintenance tools must authenticate personnel, tear down connections after use, and log activity. This group will decide whether SentinelLoop can read historian data at all. | Government | [NIST SP 800-82r3](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-82r3.pdf) |

---

## 3. The work-order lifecycle

### 3.1 Stages, statuses and who acts

| Stage | What happens | Who | Typical CMMS status (IBM Maximo labels) | SMRP metric(s) (5th-ed. numbering) | Sources |
|---|---|---|---|---|---|
| 1. Work request / identification | Requests come from operators, PM/PdM inspections, or condition alarms. SMRP's rule is that no maintenance work is done and no parts are bought without a work order. | Requester, operator, PM/PdM technician | Created / WAPPR (waiting on approval) | 5.4.2 Proactive Work (counts corrective work identified from PM/PdM) | [SMRP 2018](https://pemac.org/sites/default/files/2018_SMRP_BPMW_Full_Day.pdf); [IBM](https://www.ibm.com/support/pages/node/1112013) |
| 2. Approval and prioritization | The coordinator or approver screens the request, sets priority (Section 4), and approves or cancels it. | Coordinator, approver, area or operations lead | WAPPR to APPR or CANCEL | n/a | [Lukens et al.](https://papers.phmsociety.org/index.php/phmconf/article/download/836/phmc_19_836); [SMRP 2018](https://pemac.org/sites/default/files/2018_SMRP_BPMW_Full_Day.pdf); [IBM](https://www.ibm.com/support/pages/node/1112013) |
| 3. Planning | Job plan, estimates, bill of materials, tools, permits, procedures. Parts are reserved or ordered. | Planner, storeroom | APPR (synonyms: WSCH waiting to schedule, WMATL waiting on material) | 5.3.1 Planned Work; 5.3.3/5.3.4 actual cost or hours vs estimate; 5.3.6 Planner Productivity; 5.4.8 Planned Backlog | [SMRP 2018](https://pemac.org/sites/default/files/2018_SMRP_BPMW_Full_Day.pdf); [Accendo](https://accendoreliability.com/review-maintenance-planning-scheduling-handbook-doc-palmer/) |
| 4. Scheduling | The weekly schedule is built from "ready to schedule" work, coordinated with operations for equipment release. | Scheduler, supervisor, operations | WSCH; WPCOND (waiting on plant condition) | 5.4.9 Ready Backlog; 5.4.3/5.4.4 Schedule Compliance (hours / work orders) | [SMRP 2018](https://pemac.org/sites/default/files/2018_SMRP_BPMW_Full_Day.pdf); [IBM](https://www.ibm.com/support/pages/node/1112013) |
| 5. Execution | Isolation (LOTO or permit), repair, test, return to service. | Crafts, supervisor, EHS | INPRG (in progress) | 5.6.1 Wrench Time; 5.4.1 Reactive Work (work that breaks the weekly schedule) | [SMRP 2018](https://pemac.org/sites/default/files/2018_SMRP_BPMW_Full_Day.pdf); [OSHA](https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.147) |
| 6. Completion and close-out | Labour, parts, failure codes (problem/cause/remedy, or object part/damage/cause/action) and free-text history are recorded. A supervisor reviews. Once closed, the record becomes history and its status cannot change. | Crafts, supervisor, planner | COMP, then CLOSE | 5.4.7 Work Order Cycle Time; 5.4.6 Work Order Aging; 5.4.12 PM & PdM Yield | [SMRP 2018](https://pemac.org/sites/default/files/2018_SMRP_BPMW_Full_Day.pdf); [IBM](https://www.ibm.com/support/pages/node/1112013) |
| 7. Backlog management | Workload is balanced against craft capacity using planned backlog, ready backlog and PM/PdM backlog. | Planner, scheduler, manager | n/a | 5.4.8, 5.4.9, 5.4.11 PM & PdM WOs overdue, 5.4.14 PM & PdM Compliance | [SMRP 2018](https://pemac.org/sites/default/files/2018_SMRP_BPMW_Full_Day.pdf) |

Notes:

- The IBM support article lists the allowed transitions. For example, from COMP the only allowed move is to CLOSE; CANCEL and CLOSE allow no further status change; WSCH, WMATL and WPCOND are synonyms of APPR. This is a support blog post by an IBM engineer, not formal product documentation, and real sites configure their own synonyms ([IBM](https://www.ibm.com/support/pages/node/1112013)).
- SMRP's advice: map the work-order system as a process flow diagram, let the status codes mirror the steps where people query the system, and do not use work-order type to encode urgency or priority ([SMRP 2018](https://pemac.org/sites/default/files/2018_SMRP_BPMW_Full_Day.pdf)).
- SAP PM uses a notification-to-order flow (notification, order, release, confirmation, technical completion "TECO", settlement, close). The SAP pages describing it could not be opened (HTTP 403), so the SAP flow and its status codes are **UNVERIFIED** here.
- The 2018 SMRP deck numbers some metrics inconsistently between slides (e.g. 5.3.5 appears as both "Planning Variance Index" and "Standing Work Orders"). Check against the current 7th edition before citing numbers.
- The often-quoted backlog benchmark of 2–4 weeks of ready backlog appeared only in vendor blogs that cite SMRP or IDCON second-hand. **UNVERIFIED**; the SMRP target sits in the members-only document.

### 3.2 Best-in-class targets SMRP published (labour distribution and yield)

From the SMRP 2018 workshop (body of knowledge, 5th edition basis) ([SMRP 2018](https://pemac.org/sites/default/files/2018_SMRP_BPMW_Full_Day.pdf)):

- Labour distribution targets: preventive maintenance about 15% of total hours, corrective work identified through PM about 15%, predictive maintenance about 15%, corrective work identified through PdM about 35%.
- PM/PdM yield: top performers average about 1 hour of corrective work found per hour of PM, and about 2.5 hours of corrective work per hour of PdM.
- Maintenance cost: top performers maintain reliable plants for under 3% of RAV, regardless of industry.
- The worked example uses illustrative plants A, B and C, giving proactive work of 64.5%, 25.1% and 5.7%. These are teaching examples (synthetic), not benchmark data.

**Team inference.** The PdM-yield idea is the metric a buyer will use to judge SentinelLoop: how many hours of real corrective work each PdM-generated order finds. Our simulated results cannot measure this.

---

## 4. How priorities are actually set

### 4.1 Criticality versus priority

- Priority is the order in which work should be done. Criticality ranks equipment by probability and consequence of failure. "Criticalness" is how essential an item is, which is fairly fixed. Criticality can fall when PM or condition monitoring makes failure unlikely ([Keeter](https://reliabilityweb.com/articles/entry/priority_vs_criticality)).
- EN 13306:2017 includes an informative Annex E criticality matrix ([STN EN 13306 preview](https://normy.normoff.gov.sk/norma/127326/nahlad)). Its content was not visible in the preview (**UNVERIFIED** detail).
- SMRP has a reliability metric "Systems Covered by Criticality Analysis" (3.1 in 5th-ed. numbering), and lists priority codes as static master data in the CMMS ([SMRP 2018](https://pemac.org/sites/default/files/2018_SMRP_BPMW_Full_Day.pdf)).
- In ISO 14224 failure records, the failure impact on safety, on operations and on equipment function (critical, degraded or incipient) are separate fields ([Selvik](https://standard.no/globalassets/fagomrader-sektorer/petroleum/rio_de_janeiro/4-collection_and_exchange_of_reliability_data-j_t_selvik.pdf)).

### 4.2 Priority matrices in use: RIME

- **RIME (Ranking Index for Maintenance Expenditures).** Equipment criticalness is scored 1–10 (safety/environmental protection highest, buildings and grounds lowest). Work type is scored 1–10 (an immediate threat to health, safety or environment highest, appearance work lowest). The two are multiplied, and a cross-functional team sets local policy on the result. To keep low-ranked work from stalling, schedule a fixed share of it or add points weekly ([Keeter](https://reliabilityweb.com/articles/entry/priority_vs_criticality)).
- **A RIME lookup-table case at a pharmaceutical site (Merck, introduced alongside SAP PM).** Work-request priority (row) and asset priority (column) give a work-order priority code: 0 means complete within 1 day, 1 within 2 days, 2 within 7 days, 3 within 30 days. Example: a process pump still running but below required throughput maps to code 1 (2 days). Results reported: adherence to RIME reached the 80% goal in six months, response times improved by 2–3 weeks per priority level, and schedule compliance rose from 63% to 77%. The site had to review work orders weekly because people were not following RIME ([Reliabilityweb RIME](https://reliabilityweb.com/en/articles/ranking-index-for-maintenance-expenditures); [Reliabilityweb, emotion vs logic](https://reliabilityweb.com/articles/entry/work_prioritization_emotion_vs._logic)). Practitioner case, single site, no author or date shown on the pages.
- **The actual behaviour that RIME replaces.** Priorities are set by emotion and pressure: who is yelling loudest, and every requester claiming an emergency ([Reliabilityweb](https://reliabilityweb.com/articles/entry/work_prioritization_emotion_vs._logic)).
- **5×5 risk matrices** (consequence × likelihood across safety, environment, production, quality and cost) appear widely, but every source found for them was a vendor blog or a white paper. Treat them as vendor practice, not a standard (**UNVERIFIED** as a norm).
- Score direction differs between implementations: in some, a higher number means more important; in RIME codes, a lower code means more urgent. This came from a search summary and is consistent with the two RIME sources above.

**Team inference.** Today SentinelLoop's Triage Agent sets urgency from the RUL lower bound alone. A plant would expect the order to carry (a) the asset's criticality class and (b) a work-type or urgency class, and to land on the site's own priority code, for example a RIME code with a due date. Without criticality, a RUL-driven order on a low-criticality pump would outrank a safety-critical inspection, which is exactly the "loudest voice" failure RIME exists to stop.

---

## 5. The mix of reactive, preventive, condition-based and predictive maintenance

### 5.1 Definitions to adopt

- **Preventive maintenance (SMRP):** actions on a time- or machine-run-based schedule that detect, preclude or mitigate degradation ([SMRP 2018](https://pemac.org/sites/default/files/2018_SMRP_BPMW_Full_Day.pdf)).
- **Predictive maintenance (SMRP):** a strategy based on assessing asset condition to determine the likelihood of failure, then acting to avoid it. Condition may be measured by CM technologies, statistical process control, performance indicators or human senses ([SMRP 2018](https://pemac.org/sites/default/files/2018_SMRP_BPMW_Full_Day.pdf)). SMRP's cost and hours metrics use the label "condition based maintenance" for this bucket.
- **Reactive work (SMRP 5.4.1):** work that interrupts the weekly schedule. **Proactive work (5.4.2):** PM, PdM and corrective work identified by them before failure ([SMRP 2018](https://pemac.org/sites/default/files/2018_SMRP_BPMW_Full_Day.pdf)).
- **EN 13306** treats predictive maintenance as a subset of condition-based maintenance, which is a subset of preventive maintenance (partially verified; see Section 1).

### 5.2 What plants actually do: the evidence

| Evidence | Finding | Data type | Caveats | Source |
|---|---|---|---|---|
| NIST Machinery Maintenance Survey (US manufacturers, NAICS 321–339 excl. 324/325; 71 usable responses from managers of machinery maintenance; 2016 data; published June 2020) | Average mix: **17.3% predictive, 31.8% preventive, 45.7% reactive, 4.7% other**. The top quartile on reactive reliance had 3.3× the downtime and 16× the defects of the bottom quartile. Within PM/PdM-reliant firms, the top half on predictive had 15% less downtime and an 87% lower defect rate. | Survey / self-reported | Small sample. The authors call the group comparisons anecdotal and the associations non-causal. Many surveyed quantities are "not formally tracked" by firms. | [NIST AMS 100-34](https://nvlpubs.nist.gov/nistpubs/ams/NIST.AMS.100-34.pdf); [NIST page](https://www.nist.gov/el/applied-economics-office/manufacturing-machinery-maintenance); [Thomas & Weiss 2021 (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC9890517/) |
| Same study, costs (US, 2016 dollars) | Maintenance activities cost $74.5B (incl. $57.3B direct maintenance, $16.3B from faults and failures, $0.9B buffer inventory). Preventable losses were $119.1B (incl. $18.1B downtime, $100.2B lost sales). A Monte Carlo total of $222.0B appears in the 2021 paper. | Survey-based estimate | US only; not transferable to India. Shown here only to explain why buyers care. | [NIST page](https://www.nist.gov/el/applied-economics-office/manufacturing-machinery-maintenance); [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC9890517/) |
| Sexton et al. (NIST/UWA) | Cite Thomas (2018): a large cross-section of SMEs still rely on reactive maintenance. | Peer-reviewed (secondary citation) | Points back to the NIST work | [Sexton et al. 2019](https://papers.phmsociety.org/index.php/phmconf/article/download/790/phmc_19_790) |
| SMRP "death spiral of reactive maintenance" | Postponed PM and ignored predictive results lead to more breakdowns, more reactive work, less planned work and higher injury rates. Poor data quality and no data analysis are named as contributors. | Body of knowledge (conceptual) | Qualitative | [SMRP 2018](https://pemac.org/sites/default/files/2018_SMRP_BPMW_Full_Day.pdf) |
| India: see Section 8 | No sourced mix percentages for Indian plants | n/a | n/a | n/a |

Not used: the frequently quoted US DOE/FEMP O&M Best Practices Guide figures (reactive maintenance costing several times more, cost per horsepower by strategy). The primary PDF was not opened in this session, so these are **UNVERIFIED** and excluded.

---

## 6. What data plants actually have

### 6.1 CMMS / EAM work-order history (real field data)

What it contains:

- **Master data**: locations or functional locations (SMRP suggests at most 5–6 hierarchy levels, with ISO 14224 as a model), equipment records, class and subclass, specifications, failure hierarchies, work-order types, status codes, priority codes, material items, bills of material. **Transactional data**: the work orders themselves. Transactional quality depends on master-data quality. SMRP's slogan is that bad data is worse than no data ([SMRP 2018](https://pemac.org/sites/default/files/2018_SMRP_BPMW_Full_Day.pdf)).
- **Failure codes**: hierarchies such as problem/cause/remedy or object part/damage/cause/action, ideally specific to each equipment subclass ([SMRP 2018](https://pemac.org/sites/default/files/2018_SMRP_BPMW_Full_Day.pdf)). ISO 14224's minimum failure record holds the record ID, equipment ID or location, failure date, failure mode (usually at level 6) and failure impact on equipment function. Further fields include failure mechanism, failure cause, subunit and maintainable item failed, **detection method**, operating condition at failure, and impacts on safety and operations. The 2006 edition listed 51 definitions in clause 3. These field lists come from a 2014 presentation on the 2006 edition, so check them against the 2016 text ([Selvik](https://standard.no/globalassets/fagomrader-sektorer/petroleum/rio_de_janeiro/4-collection_and_exchange_of_reliability_data-j_t_selvik.pdf)).
- **Free text**: short, jargon-heavy descriptions full of misspellings and abbreviations ([Sexton et al. 2019](https://papers.phmsociety.org/index.php/phmconf/article/download/790/phmc_19_790)).

Typical data quality (all peer-reviewed or professional-body sources):

- Historical work orders often have missing or incorrect functional location, failure mode, action and status fields. These can often be repaired using the free text plus knowledge of site practice. Analysts' cleaning assumptions are usually left undocumented. Evidence: heavy mobile equipment data from several organisations ([Hodkiewicz & Ho 2016, JQME 22(2)](https://www.emerald.com/insight/content/doi/10.1108/JQME-04-2015-0013/full/html)).
- Poor data quality is common at nearly all industrial organisations. The problems include CMMS configuration and usage, and the organisation's culture and motivation for capturing data. Structured fields are incomplete. NLP can fill breakdown indicators and failure modes from text, but dates, costs and detection methods are harder. The authors' framework comes from work with 120+ process and manufacturing organisations (GE Digital authors, so partly vendor perspective). Case: only about 20–30% of work orders had costs recorded. After the plant changed its process and tracked missing costs, it rose to over 90% within three years ([Lukens et al., PHM 2019](https://papers.phmsociety.org/index.php/phmconf/article/download/836/phmc_19_836)).
- Drop-down code lists lead to cluttered screens, "miscellaneous" codes, and technicians giving up the search for the right code and defaulting to a familiar one. Error modes include not observing or not remembering symptoms because of the delay between the job and data entry ([Sexton, Hodkiewicz & Brundage, PHM 2019](https://papers.phmsociety.org/index.php/phmconf/article/download/790/phmc_19_790)).
- Missing values in key fields limit KPI calculation, as seen in a study of historical HVAC work orders at one facility, where free text was mined with NIST's Nestor tool ([Conte et al., PHME 2021](https://papers.phmsociety.org/index.php/phme/article/view/2814)).
- Generic NLP pipelines need re-imagining for technical text: "Technical Language Processing" ([Brundage et al., Manufacturing Letters 2020, NIST record](https://www.nist.gov/node/1647801)).
- ISO 14224 lists the attributes of high-quality RM data: completeness against the specification, compliance with definitions, accurate input and transfer, enough population and surveillance time for statistical confidence, and relevance ([Selvik](https://standard.no/globalassets/fagomrader-sektorer/petroleum/rio_de_janeiro/4-collection_and_exchange_of_reliability_data-j_t_selvik.pdf)).

A free dataset the team could use: **MaintIE** (UWA). 1,067–1,076 expert double-annotated maintenance work-order texts (the README gives both numbers) plus 7,000 model-annotated, expert-reviewed texts, 8,076 in total. Sanitised (IDs, numbers and dates replaced). MIT licence. The README does not name the industry or explicitly say the texts are real work orders, so treat it as **likely real field data of unstated origin (partially verified)** ([GitHub nlp-tlp/maintie](https://github.com/nlp-tlp/maintie)).

### 6.2 Condition-monitoring route data (real field data)

- Vibration monitoring can be continuous (permanently installed) or periodic and non-continuous ([ISO 13373-1 listing](https://asn.sn/en/node/47636)).
- Portable route-based collectors support the "walk-around" part of condition monitoring, and data goes into the vendor's own software, e.g. Bently Nevada SCOUT200 into System 1 (**vendor claim**) ([Baker Hughes](https://www.bakerhughes.com/bently-nevada/monitoring-systems/portable-vibration-testers-diagnostic-systems)).
- Route frequency (monthly, quarterly and so on) and the share of assets on routes versus online systems were **not found** in any opened source (UNVERIFIED).
- SMRP counts the human senses as a valid condition-assessment method ([SMRP 2018](https://pemac.org/sites/default/files/2018_SMRP_BPMW_Full_Day.pdf)). Operator rounds and inspections are part of PdM by that definition.

### 6.3 SCADA, DCS, PLC and historian process data (real field data)

- In a SCADA control centre, the HMI, engineering workstations and **data historian** sit on a LAN. The control centre does centralized alarming, trend analysis and reporting. In NIST's glossary, a data historian is a centralized database supporting analysis with statistical process control techniques. Historians also serve as a supplemental source of event data in incident response ([NIST SP 800-82r3](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-82r3.pdf)).
- Security architecture: separate levels (Purdue 0–2 field, level 3 operations), boundary firewalls, a DMZ through which all enterprise-to-operations traffic passes, and unidirectional gateways as an option ([NIST SP 800-82r3](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-82r3.pdf)).

### 6.4 Alarms (real field data, and a human-factors constraint)

Benchmarks from IChemE Safety Centre guidance (Nov 2021), drawing on ISA-18.2/IEC 62682 and EEMUA 191, for large process plants with central control rooms (smaller plants should calibrate) ([IChemE](https://www.icheme.org/media/17392/lc-0151_21-lead-process-safety-metrics-alarm-rationalisation-final.pdf)):

- Annunciated alarms per 10 minutes per operator console: target about 1, about 2 sub-optimal, more than 2 poor.
- Alarm flood: more than 10 alarms in 10 minutes, ending when the rate falls below 5. Time in flood: target under 1%, poor above 2.5% (EEMUA).
- Stale alarms (active about 24 h or more): target under 5 (IEC/ISA) or under 10 (EEMUA).
- Top-10 most frequent alarms' share of total load, and chattering or fleeting alarms, are the main "bad actor" metrics.
- Priority distribution of annunciated alarms: about 80% low, 15% medium, 5% high.
- Poor stable-plant metrics mean operators stop believing alarms and learn to ignore them.

Per-day figures (150 / 300 alarms per operator per day) appeared only in a trade-article snippet: **UNVERIFIED**.

### 6.5 What plants often do not have

- Many quantities NIST asked about (downtime share, defects caused by maintenance, lost sales) are, for many firms, not formally tracked. NIST's estimates therefore carry wider error than Census-based ones ([NIST AMS 100-34](https://nvlpubs.nist.gov/nistpubs/ams/NIST.AMS.100-34.pdf)).
- **Team inference.** Run-to-failure trajectories with exact failure times, which is what C-MAPSS provides, do not exist in normal plant data. Plants intervene before failure, so failures are censored, and the "failure" label has to be reconstructed from work-order text and codes (Sections 6.1 and 6.5).

### 6.6 Data-type classification of everything referenced in this stream

| Data | Type |
|---|---|
| CMMS/EAM work orders, failure codes, free text | Real field data |
| Condition-monitoring route and online data | Real field data |
| SCADA/DCS/historian process data, alarm logs | Real field data |
| NIST Machinery Maintenance Survey | Survey / self-reported (not machine data) |
| SMRP sample plants A, B, C; "Speedy Mac Reliability Products" exercise | Synthetic teaching examples |
| MaintIE corpus | Likely real field text, origin unstated, sanitised (partially verified) |
| NASA C-MAPSS (SentinelLoop's only data so far) | Simulated data |
| Vendor result claims (e.g. Hitachi Energy for Tata Steel) | Vendor claims, no data published |

---

## 7. Where delays and failures in the process come from

| Delay source | Evidence | Source(s) |
|---|---|---|
| **Parts and materials** | A CMMS status exists for it (WMATL / "waiting for material"), and SMRP gives expediters that queue. Remote mining case: planned and preventive maintenance repeatedly slipped because parts were missing. Investigators found 23 contributing factors: stock-holding software trusted over maintenance input, automated vendor-held-inventory transactions with no check that parts arrived, non-technical planners missing materials, parts added after release not passed to supply, no proactive expediting, and an unsecured kitting area. In a stocktake, at least 10% of bins marked complete were missing parts, and parts sat at least two weeks between arrival and job execution. SMRP tracks stock-outs (5.5.33). | [IBM](https://www.ibm.com/support/pages/node/1112013); [SMRP 2018](https://pemac.org/sites/default/files/2018_SMRP_BPMW_Full_Day.pdf); [Assetivity 2024 (practitioner)](https://www.assetivity.com.au/articles/asset-management/coordinating-activity-between-maintenance-and-supply-a-case-study/) |
| **Approvals** | A dedicated status (WAPPR), and SMRP describes approvers working the "created" queue. **No quantitative source on approval delay was found.** | [IBM](https://www.ibm.com/support/pages/node/1112013); [SMRP 2018](https://pemac.org/sites/default/files/2018_SMRP_BPMW_Full_Day.pdf) |
| **Plant access, isolation, permits** | A dedicated status (WPCOND, waiting on plant condition). OSHA requires documented energy-control procedures before servicing. Permit-to-work is the control used in process industries. A trade guide names lockout/tagout, permits and remote equipment access as time sinks (practitioner). | [IBM](https://www.ibm.com/support/pages/node/1112013); [OSHA](https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.147); [HSE](https://www.hse.gov.uk/pubns/books/hsg250.htm); [Reliamag wrench time guide](https://reliamag.com/topics/guides/wrench-time-benchmarks-typical-good-and-world-class-rates) |
| **Scheduling broken by reactive work** | By SMRP's definition, reactive work is what interrupts the weekly schedule. Reactive work takes crew capacity away from proactive work. In the RIME case, enforcing priority discipline raised schedule compliance from 63% to 77%. | [SMRP 2018](https://pemac.org/sites/default/files/2018_SMRP_BPMW_Full_Day.pdf); [Reliabilityweb RIME](https://reliabilityweb.com/en/articles/ranking-index-for-maintenance-expenditures) |
| **Technician availability and productivity** | On call, nights and weekends, with common overtime (BLS). SMRP tracks craft-workers-on-shift ratio, overtime hours and wrench time. Wrench-time benchmarks: about 35% typical and about 55% best practice per Palmer, and 18–30% for most companies per Smith and Mobley (2007). These come through a trade guide, which notes that no ISO or EN standard sets a "world-class" figure and that the SMRP target is members-only. The main time sinks excluded from wrench time are travel, waiting for parts, tool searches and breaks (practitioner). | [BLS](https://www.bls.gov/ooh/installation-maintenance-and-repair/industrial-machinery-mechanics-and-maintenance-workers-and-millwrights.htm); [SMRP 2018](https://pemac.org/sites/default/files/2018_SMRP_BPMW_Full_Day.pdf); [Reliamag](https://reliamag.com/topics/guides/wrench-time-benchmarks-typical-good-and-world-class-rates) |
| **Planning quality** | Palmer: separate planners from daily firefighting, plan ahead of the crews, feed problems found on jobs back into the plan library. The book claims productivity gains of about 50% over unplanned work (through a review). SMRP tracks actual vs estimated hours and cost; variances should shrink as planning skill improves. | [Accendo](https://accendoreliability.com/review-maintenance-planning-scheduling-handbook-doc-palmer/); [SMRP 2018](https://pemac.org/sites/default/files/2018_SMRP_BPMW_Full_Day.pdf) |
| **Diagnosis time** | Sexton et al., citing Kegg (1984): diagnosis commonly takes longer than the repair itself. This is a secondary citation of an old source. | [Sexton et al. 2019](https://papers.phmsociety.org/index.php/phmconf/article/download/790/phmc_19_790) |
| **Close-out data quality (feeding the next decision)** | Missing failure modes, costs and status (Section 6.1). Supervisors are supposed to ensure work details are recorded. | [Lukens et al.](https://papers.phmsociety.org/index.php/phmconf/article/download/836/phmc_19_836); [Hodkiewicz & Ho](https://www.emerald.com/insight/content/doi/10.1108/JQME-04-2015-0013/full/html) |
| **Skills and workforce ageing** | The experienced workforce is ageing and fewer young people are entering the field, so tacit knowledge needs capturing (Sexton et al., citing others). For SMEs: shortages of skilled people, operators with weak machine knowledge, and slow contractor response, from a Malaysian SME survey cited in a book chapter. | [Sexton et al. 2019](https://papers.phmsociety.org/index.php/phmconf/article/download/790/phmc_19_790); [Burhanuddin et al. 2011 (IntechOpen)](https://www.intechopen.com/chapters/19341) |

---

## 8. Evidence on maintenance practice in Indian manufacturing

**Bottom line: some evidence exists, but it is thin, mostly qualitative or small-sample, and mostly paywalled. We found no sourced quantitative data on Indian plants' maintenance mix, CMMS adoption rates, work-order data quality, wrench time or work-order cycle time.**

### 8.1 MSMEs and SMEs

| Evidence | What it says | Quality | Source |
|---|---|---|---|
| Pai et al. 2018, *A Study on Usage of TPM in Selected SMEs* (IOP Conf. Ser. MSE 376, open access). Authors from colleges in Mangaluru and Mysuru. | 50 respondents (chief executives, engineers, managers, supervisors) from 50 manufacturing, process and service organisations, via Google Forms. 52% (26/50) said their organisation had adopted TPM. About 46% had heard of TPM. 71% said they keep proper maintenance records (computers, log books). 88% of the non-TPM organisations reported computerization being available. 46% thought TPM benefits only large firms. | Small, non-random, regional, self-reported survey. Location of firms is not explicitly stated. | [IOP open-access PDF](https://iopscience.iop.org/article/10.1088/1757-899X/376/1/012117/pdf) |
| Sidhu, Singh & Ahuja 2022, IJPMB 12(4) | Survey of 216 northern Indian SMEs. Reports implementation of breakdown, preventive, predictive and corrective maintenance, scheduling and planning, CMMS and TPM, all linked to performance gains. No percentages in the abstract. | Abstract only; full text paywalled | [Inderscience](https://www.inderscience.com/info/inarticle.php?artid=123709) |
| Sidhu, Singh & Ahuja 2023, IJPMB 15(1) | A three-phase implementation framework for maintenance practices in Indian SMEs (options field/profile methodology, AHP, fuzzy sets) | Abstract only; modelling, not prevalence | [Inderscience](https://www.inderscience.com/info/inarticle.php?artid=132690) |
| Ahuja & Khamba 2008, IJTPM 8(3) | Maintenance was historically treated as a secondary function in Indian industry. Practice is shifting from breakdown or reactive maintenance toward proactive TPM. | Abstract only; dated | [Inderscience](https://www.inderscience.com/info/inarticle.php?artid=17664) |
| Bisht & Sridhar 2021, J. Phys. Conf. Ser. 2115 | Expert questionnaires and interviews on barriers to Industry 4.0 in Indian MSMEs. The abstract does not mention maintenance. | Qualitative | [IOP](https://iopscience.iop.org/article/10.1088/1742-6596/2115/1/012024) |
| Government ZED (Zero Defect Zero Effect) certification for MSMEs | Lists 20 manufacturing parameters, including **No. 8 "Planned Maintenance & Calibration"**. Which certification levels (Bronze, Silver, Gold) require it was not legible. | Government (state MSME portal); official ZED guidelines not opened | [UP MSME portal](https://msme1connect.up.gov.in/zed-certification) |

### 8.2 Large plants

| Evidence | What it says | Quality | Source |
|---|---|---|---|
| CII TPM Club India | CII signed an MoU with the Japan Institute of Plant Maintenance (JIPM) in March 1998 and created TPM Club India. CII runs milestone certificates (e.g. "Strong Commitment" one year after kick-off) and an Excellence in Operational Technology award. A figure of "over 3,000 Indian companies started JIPM-TPM, ~90% quit" appeared only in a search summary and was **not found** in the opened CII pages (UNVERIFIED). | Industry body | [TPM Club India](https://tpmclubindia.org/about/); [CII TPM Bulletin](https://tpmclubindia.org/wp-content/uploads/2024/03/TPM-Bulletin-1.pdf) |
| JIPM awards to Indian plants (press) | Sundaram Auto Components, Mysuru: JIPM TPM Excellence Award (Feb 2022), with claims of +20% OEE, -50% lead time and -33% line defects over 2016–2021 (**company claims**). Tetra Pak, Chakan: reported in 2023 as the first site in India to receive JIPM's world-class TPM achievement award. | Trade press, company claims | [Mobility Outlook](https://mobilityoutlook.com/news/sundaram-auto-components-mysuru-plant-gets-tpm-excellence-award); [PrintWeek India](https://www.printweek.in/news/tetra-pak-factory-becomes-the-first-tpm-world-class-manufacturing-facility-in-india--57185) |
| Tata Steel, Jamshedpur | Online monitoring (TXpert Hub, CoreSense sensors) planned for five critical transformers: oil temperature, gas formation and load. No measured results published (**vendor claim**). | Vendor claim | [Hitachi Energy](https://www.hitachienergy.com/news-and-events/customer-stories/intelligent-transformers-from-hitachi-abb-power-grids-to-bolster-tata-steel-operations) |

### 8.3 Regulation and skills (government sources)

- **OSH Code 2020.** The PIB factsheet (22 Nov 2025) says the Code replaces 13 central labour laws with one. Factories employing 500 or more workers must constitute a safety committee with employer and worker representatives. The factory licence threshold rose from 10 to 20 workers (with power) and from 20 to 40 (without power) ([PIB factsheet](https://static.pib.gov.in/WriteReadData/specificdocs/documents/2025/nov/doc20251122702801.pdf)). Commencement on 21 Nov 2025 (S.O. 5321(E)), and the Factories Act being among the laws replaced, come from a secondary legal publisher ([Taxmann](https://www.taxmann.com/post/blog/govt-notifies-enforcement-of-occupational-safety-health-working-conditions-code)). Treat as **partially verified**.
- **Factories Act 1948 s.22** (now subsumed; whether the equivalent OSH Code rule keeps the same wording is UNVERIFIED). Examining, lubricating or adjusting machinery in motion was restricted to specially trained adult male workers in tight-fitting clothing, entered in a register and holding a certificate of appointment. Women and young persons were barred from cleaning, lubricating or adjusting prime movers or transmission machinery in motion ([AdvocateKhoj, secondary text of the Act](https://www.advocatekhoj.com/library/bareacts/factories/22.php)).
- **National Qualification "Predictive Maintenance Data Acquisition Engineer"**, NSQF Level 6, submitted by the Capital Goods and Strategic Skill Council and approved by NSQC on 8 May 2025. Training is 660 hours: 184 theory, 326 practical, 150 on the job. Modules cover designing, analysing and maintaining data acquisition systems and integrating PdM strategies. The file's own evidence-of-need section says there was no skill-gap study or recent market research ("industry driven"), 5 industry validations, and an estimated **96** persons to be trained and employed ([NQR qualification file](https://www.nqr.gov.in/qualification/file/QF-Predictive%20Maintenance%20Data%20Acquisition%20Engineer%20Eng.pdf)). This suggests the role is recognised but small-scale.

### 8.4 What we did not find (India)

- Any survey with percentages of reactive, preventive or predictive maintenance in Indian plants.
- Any study of CMMS or EAM work-order data quality in Indian plants.
- Any data on how Indian MSMEs record maintenance (paper log books vs spreadsheets vs CMMS), beyond the 71% "proper records" self-report in the 50-respondent survey.
- An Industry 4.0 or PdM baseline survey of Indian MSMEs. A Department of Telecommunications call for proposals for such a survey appeared in search results, but the document returned HTTP 403 (**UNVERIFIED**).
- Market-size figures for Indian predictive maintenance appeared only from commercial market-research firms in search snippets. Not opened, so **UNVERIFIED** and not used.

---

## 9. Implications for SentinelLoop (Team inference, not sourced fact)

1. **Write into the CMMS, do not replace it.** A SentinelLoop order should arrive as a *request* (status WAPPR or equivalent) that a coordinator approves and a planner plans, not as a scheduled job. The product is advisory generation in OSA-CBM terms, and its output sits upstream of the planner.
2. **Fill the fields plants use.** Each draft order should carry: equipment ID and location; a proposed ISO 14224-style failure mode at equipment-unit level; detection method = "condition monitoring / predictive model"; failure impact on function (incipient or degraded); evidence (sensor trends, interval width, drift flags); and a recommended latest-finish date derived from the RUL lower bound. This helps the planner, and it improves the data quality of the history we will later learn from.
3. **Add criticality and site priority codes.** Map (asset criticality × urgency from the RUL bound) to the site's priority code, RIME-style with due-date bands. Make the mapping a configurable table owned by the plant, not by us.
4. **Respect alarm budgets.** Escalations to humans compete with control-room alarms. Our E3 result, where the fleet rule escalates 25–36% of healthy engines while active, would look like a flood at plant scale. Report escalations per operator per shift against the about-1-per-10-minutes benchmark.
5. **Measure what buyers measure.** PdM yield (corrective hours found per PdM order), false-order rate, lead time gained before failure, and schedule disruption avoided. Simulated C-MAPSS results cannot show any of these. Saying so openly protects credibility.
6. **Data plan for real plants.** Expect messy work-order history and no run-to-failure labels. Failure events will have to be reconstructed from work-order text and codes. MaintIE is a free, MIT-licensed corpus to prototype work-order text processing without customer access.
7. **OT security first contact.** Expect the IT/OT team to require read-only access through a DMZ or unidirectional gateway, no write path to control systems, and logged remote access. Design for "historian export via DMZ" from the start.
8. **Indian segment.** Large plants with TPM programmes (CII/JIPM ecosystem) already have the planned-maintenance discipline and data a PdM tool needs. Many MSMEs may lack a CMMS (unproven; see Section 8.4). A discovery interview should establish this before any product bet.
9. **Discovery questions this research suggests** for the first interviews: Which CMMS or EAM do you use, if any, and who closes work orders? What share of orders carry a failure code that is not "other"? How do you set priority, and is there a criticality list? How many condition-monitoring alarms or reports do you already ignore per week? What would a planner need to see to accept a model-generated request? Who has to approve any connection to the historian?

---

## 10. Gaps and UNVERIFIED items (consolidated)

- Exact EN 13306:2017 definitions (only a secondary glossary seen); the content of EN 13306 Annex E.
- The ISO 55000:2024 definition of asset management; detailed clauses of ISO 17359:2018, ISO 13381-1:2025, ISO 13374 Parts 2–4, and ISO 18436-2 (all paywalled).
- Review or confirmation years for ISO 14224 (2022), ISO 17359 (2023) and ISO 13373-1 (2024), seen only in snippets.
- SMRP best-in-class targets for wrench time, ready backlog and planned work (members-only), and current 7th-edition metric numbering.
- SAP PM status flow (pages blocked).
- ISA-18.2 per-day alarm figures (150/300); US DOE/FEMP O&M guide cost figures (primary PDF not opened).
- Condition-monitoring route frequencies and online-versus-route coverage in typical plants.
- Any quantitative Indian evidence on maintenance mix, CMMS adoption, data quality, wrench time or delays; the CII "3,000 companies" TPM figure; Indian PdM market size.
- How much approval delay contributes to work-order cycle time (no source found anywhere).

---

## Sources

All accessed 2026-10-18. Type: Std = standard or official standards listing; BoK = professional body of knowledge; Gov = government; PR = peer-reviewed; Prac = practitioner or trade; Vend = vendor; Data = dataset.

| # | URL | Type | Used for |
|---|---|---|---|
| 1 | https://pemac.org/sites/default/files/2018_SMRP_BPMW_Full_Day.pdf | BoK (SMRP 2018 workshop, hosted by PEMAC) | Pillars, metric list, definitions, data quality, status codes, targets |
| 2 | https://smrp.org/?p=57 | BoK | Current Best Practices edition (7th), 70+ metrics |
| 3 | https://www.mimosa.org/mimosa-osa-cbm/ | Std | OSA-CBM / ISO 13374 relationship, version 3.3.1 |
| 4 | https://www.mimosa.org/wp-content/uploads/2006-08-28_Including_OSA-CBM_and_OSA-EAI_in_Integrated_System_Health_Management.pdf | Std (MIMOSA presentation) | Six OSA-CBM blocks and outputs; OSA-EAI domains |
| 5 | https://iss.rs/en/project/show/iso:proj:21832 | Std listing | ISO 13374-1 status |
| 6 | https://iss.rs/en/project/show/iso:proj:51436 | Std listing | ISO 13381-1:2015 withdrawal |
| 7 | https://ccn-scc.ca/standardsdb/standards/8189734 | Std listing | ISO 13381-1:2025 title, date, abstract |
| 8 | https://asn.sn/en/node/17332 | Std listing | ISO 17359:2018 scope |
| 9 | https://asn.sn/en/node/47636 | Std listing | ISO 13373-1 scope |
| 10 | https://evs.ee/en/evs-en-iso-14224-2016 | Std listing | ISO 14224 scope and data categories |
| 11 | https://standard.no/globalassets/fagomrader-sektorer/petroleum/rio_de_janeiro/4-collection_and_exchange_of_reliability_data-j_t_selvik.pdf | Std (ISO/TC 67/WG4 technical editor presentation) | ISO 14224 taxonomy, failure data fields, data quality |
| 12 | https://committee.iso.org/sites/tc251/home/projects/published/iso-55000.html | Std | ISO 55000:2024 scope and changes |
| 13 | https://knowledge.bsigroup.com/products/maintenance-maintenance-terminology | Std listing | BS EN 13306:2017 status |
| 14 | https://normy.normoff.gov.sk/norma/127326/nahlad | Std (national adoption preview) | EN 13306:2017 structure, Annex E criticality matrix |
| 15 | https://techniques-ingenieur.fr/en/resources/article/ti095/preventive-maintenance-mt9571/v1/glossary-9 | Prac (technical encyclopedia glossary) | CBM and predictive maintenance definitions (partial) |
| 16 | https://nvlpubs.nist.gov/nistpubs/ams/NIST.AMS.100-34.pdf | Gov | Maintenance mix 17.3/31.8/45.7/4.7; "not formally tracked" |
| 17 | https://www.nist.gov/el/applied-economics-office/manufacturing-machinery-maintenance | Gov | Summary findings and costs |
| 18 | https://pmc.ncbi.nlm.nih.gov/articles/PMC9890517/ | PR (IJPHM 2021) | Survey method, sample, limitations |
| 19 | https://papers.phmsociety.org/index.php/ijphm/article/download/2883/1748 | PR | Cross-check of the NIST paper text |
| 20 | https://www.emerald.com/insight/content/doi/10.1108/JQME-04-2015-0013/full/html | PR | Work-order data cleaning findings |
| 21 | https://papers.phmsociety.org/index.php/phmconf/article/download/836/phmc_19_836 | PR (GE Digital authors) | Data quality framework, work process, cost-capture case |
| 22 | https://papers.phmsociety.org/index.php/phmconf/article/download/790/phmc_19_790 | PR (NIST/UWA) | Data-entry error modes, SMEs reactive, diagnosis time |
| 23 | https://papers.phmsociety.org/index.php/phme/article/view/2814 | PR | Missing values in HVAC work orders |
| 24 | https://www.nist.gov/node/1647801 | Gov (NIST publication record) | Technical Language Processing |
| 25 | https://github.com/nlp-tlp/maintie | Data | MaintIE corpus size, licence |
| 26 | https://reliabilityweb.com/en/articles/ranking-index-for-maintenance-expenditures | Prac | RIME lookup table, codes, results |
| 27 | https://reliabilityweb.com/articles/entry/priority_vs_criticality | Prac | Criticality vs priority, RIME scales |
| 28 | https://reliabilityweb.com/articles/entry/work_prioritization_emotion_vs._logic | Prac | Emotional prioritization in practice |
| 29 | https://www.ibm.com/support/pages/node/1112013 | Vend (IBM support blog) | Maximo work-order statuses and transitions |
| 30 | https://accendoreliability.com/review-maintenance-planning-scheduling-handbook-doc-palmer/ | Prac | Palmer planning principles |
| 31 | https://reliamag.com/topics/guides/wrench-time-benchmarks-typical-good-and-world-class-rates | Prac | Wrench-time benchmarks and their provenance |
| 32 | https://www.assetivity.com.au/articles/asset-management/coordinating-activity-between-maintenance-and-supply-a-case-study/ | Prac | Parts delays case study |
| 33 | https://www.bls.gov/ooh/installation-maintenance-and-repair/industrial-machinery-mechanics-and-maintenance-workers-and-millwrights.htm | Gov | Technician duties and schedules |
| 34 | https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-82r3.pdf | Gov | Historian, SCADA, DMZ, OT team, maintenance tracking |
| 35 | https://www.icheme.org/media/17392/lc-0151_21-lead-process-safety-metrics-alarm-rationalisation-final.pdf | BoK (IChemE Safety Centre) | Alarm metrics and definitions |
| 36 | https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.147 | Gov | Lockout/tagout scope and roles |
| 37 | https://www.hse.gov.uk/pubns/books/hsg250.htm | Gov | Permit-to-work guidance |
| 38 | https://www.bakerhughes.com/bently-nevada/monitoring-systems/portable-vibration-testers-diagnostic-systems | Vend | Route-based walk-around collection (vendor claim) |
| 39 | https://www.intechopen.com/chapters/19341 | PR (book chapter) | SME maintenance issues (Malaysia) |
| 40 | https://iopscience.iop.org/article/10.1088/1757-899X/376/1/012117/pdf | PR (conference, open access) | Indian SME TPM survey |
| 41 | https://www.inderscience.com/info/inarticle.php?artid=123709 | PR (abstract) | 216 northern Indian SMEs |
| 42 | https://www.inderscience.com/info/inarticle.php?artid=132690 | PR (abstract) | Indian SME implementation framework |
| 43 | https://www.inderscience.com/info/inarticle.php?artid=17664 | PR (abstract) | Indian maintenance evolution toward TPM |
| 44 | https://iopscience.iop.org/article/10.1088/1742-6596/2115/1/012024 | PR (abstract) | Industry 4.0 barriers in Indian MSMEs |
| 45 | https://msme1connect.up.gov.in/zed-certification | Gov (state portal) | ZED parameters incl. Planned Maintenance & Calibration |
| 46 | https://tpmclubindia.org/about/ | Industry body | CII–JIPM MoU 1998 |
| 47 | https://tpmclubindia.org/?p=164 | Industry body | Same, cross-check |
| 48 | https://tpmclubindia.org/wp-content/uploads/2024/03/TPM-Bulletin-1.pdf | Industry body | CII TPM milestone certificates and awards |
| 49 | https://mobilityoutlook.com/news/sundaram-auto-components-mysuru-plant-gets-tpm-excellence-award | Prac (trade press) | JIPM award, company claims |
| 50 | https://www.printweek.in/news/tetra-pak-factory-becomes-the-first-tpm-world-class-manufacturing-facility-in-india--57185 | Prac (trade press) | JIPM world-class award in India |
| 51 | https://www.hitachienergy.com/news-and-events/customer-stories/intelligent-transformers-from-hitachi-abb-power-grids-to-bolster-tata-steel-operations | Vend | Tata Steel transformer monitoring (vendor claim) |
| 52 | https://static.pib.gov.in/WriteReadData/specificdocs/documents/2025/nov/doc20251122702801.pdf | Gov | OSH Code factsheet |
| 53 | https://www.taxmann.com/post/blog/govt-notifies-enforcement-of-occupational-safety-health-working-conditions-code | Prac (legal publisher) | OSH Code commencement notification |
| 54 | https://www.advocatekhoj.com/library/bareacts/factories/22.php | Prac (bare-act reproduction) | Factories Act s.22 text |
| 55 | https://www.nqr.gov.in/qualification/file/QF-Predictive%20Maintenance%20Data%20Acquisition%20Engineer%20Eng.pdf | Gov (National Qualification Register) | PdM Data Acquisition Engineer qualification |
| 56 | https://api.openalex.org/works?search=maintenance%20practices%20Indian%20SMEs&filter=open_access.is_oa:true&per-page=15&select=id,doi,title,publication_year,primary_location,open_access | Bibliographic index | Locating open-access Indian studies |
| 57 | https://api.openalex.org/works?search=condition%20monitoring%20adoption%20survey%20Indian%20industries&filter=open_access.is_oa:true&per-page=15&select=id,doi,title,publication_year,primary_location | Bibliographic index | Search for Indian CM adoption surveys (nothing relevant) |

Sources attempted but not readable in this session (not relied on): iso.org standard pages (HTTP 403), ANSI webstore previews (403), smrp.org press release (404), inderscienceonline.com and Emerald BIJ pages (403), stmjournals.nanoschool.in (403), dspace.bits-pilani.ac.in (connection refused), dot.gov.in baseline survey call (403), labour.gov.in notification (403), answers.sap.com (403), electropedia.org (403), aclanthology.org (connection reset), Emerson AMS flyer (empty response), AIChE product page (403), ojs.trp.org.in (login page only).
