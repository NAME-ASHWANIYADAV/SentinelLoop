# Customer discovery plan: Indian onshore wind O&M (SentinelLoop)

Written 2026-10-18 by the product team's technical writer. Every source below was accessed on 2026-10-18. Fact-checked on 2026-10-18: 48 cited URLs were re-opened (46 opened, 2 blocked) and the corrections are logged in section 12.3.

---

## 1. Status banner

> **NO INTERVIEWS HAVE BEEN CONDUCTED.**
>
> This is a discovery plan and a set of testable assumptions. Nobody in the target segment has been contacted, nobody has agreed to an interview, and no pain point below has been confirmed by a customer.
>
> - Every pain is either tagged with a published source or marked **ASSUMPTION TO TEST**.
> - Every recruiting channel is a channel the team *could* use. None has been used yet.
> - SentinelLoop has been run only on **simulated** NASA C-MAPSS data and on **synthetic** wind SCADA from the team's own generator (`product/evidence/wind_synthetic/`). It has not been run on any real wind data, public or private. The synthetic runs are behaviour checks, not performance evidence (`product/KNOWN_LIMITATIONS.md` E3).

---

## 0. How to read this document

**Evidence labels**

| Label | Meaning |
|---|---|
| **[Sourced]** + link | A published source supports the statement. "Vendor claim" means the source is the vendor's own marketing page. |
| **ASSUMPTION TO TEST (Ax)** | Our belief, not yet supported by evidence. `Ax` points to the assumption register (section 10). |
| **UNVERIFIED** | We looked and could not confirm it, or saw it only second-hand. |
| **Computed** | Arithmetic we ran on figures from a cited source. |
| **Judgement** | Team reasoning, not a sourced fact. |

**Data-type labels** (used whenever a dataset is mentioned):
- **real field data**: recorded on equipment in normal service;
- **real laboratory data**: recorded on test rigs;
- **simulated data**: produced by a physics simulator, e.g. NASA C-MAPSS;
- **synthetic data**: artificially generated or perturbed.

**Provenance of citations.** Each link carries one of two provenance tags.
- **No tag:** the writer opened the page in this session.
- **"(via R1)", "(via R2)", "(via R3)", "(via R5)" or "(via AR)":** the claim and URL come from a team research file. That file's researcher opened the page on 2026-10-18; the writer did not re-open it. AR is `research/V_adversarial_review_wind_choice.md`.

The Sources section (section 12) separates the two groups.

**Tool status in this session**
- **WebSearch was unavailable.** The single call returned a shared per-turn budget-exhausted message. No searches were run and no workaround was used.
- **WebFetch worked.** It was used only on known or primary URLs.
- **Two PDFs were read from WebFetch's saved copies:** the MNRE policy (a scanned image, read page by page) and the IEA Wind EDP summary. The NIWE AAP notice was read the same way.
- **Several wind reliability sources could not be opened:**
  - NREL: DNS failure.
  - IEA Wind Task 33 page: 404.
  - GWO standards page: 404.
  - IET, MDPI and Loughborough copies of SCADA condition-monitoring reviews: 403.
  - MeitY data-protection page: 403.

  Because of these gaps, wind-specific workflow facts are thinner than we would like. Many wind pains below are therefore marked as assumptions.

**Inputs.** This plan uses research files R1, R2 and R3, and takes R5 for privacy rules. It also builds on the judge's decision and its adversarial review:
- `research/R1_maintenance_workflows.md`
- `research/R2_pdm_adoption_failures.md`
- `research/R3_competitive_landscape.md`
- `research/R5_integration_standards.md` (privacy only)
- `research/V_judge_decision.md`
- `research/V_adversarial_review_wind_choice.md`

---

## 2. Target segment

### 2.1 Starting point and what changed

The judge chose **Indian onshore wind**, with **geared turbines of about 1.5-2.3 MW monitored through 10-minute SCADA and alarm logs** (`research/V_judge_decision.md`).

The adversarial review returned **reject as specified** (`research/V_adversarial_review_wind_choice.md`). It kept the asset class but rejected the vertical framing.

This plan keeps the asset class. It treats the vertical as a **hypothesis that discovery must test**, and it adopts the review's required changes:

| Review objection | Re-checked by the writer in this session | How this plan responds |
|---|---|---|
| In-class labelled public data is thin | CARE paper v2: Farm A (onshore Portugal) has 5 turbines, 11 anomaly datasets and 11 normal datasets. Farms B and C are offshore Germany ([arXiv 2404.10320v2](https://arxiv.org/html/2404.10320v2)). The Zenodo v6 page (45 anomaly / 50 normal, CC BY-SA 4.0, real field data) states no rated power or turbine model ([Zenodo 15846963](https://zenodo.org/records/15846963)). | Discovery must find out whether Indian fleets have usable history (A1-A4). Public data cannot stand in for that. |
| Band logic does not match MNRE eligibility | The MNRE policy (clause 5) makes a turbine eligible if any one condition holds ([MNRE policy 2023](https://cdnbbsr.s3waas.gov.in/s3716e1b8c6cd17b771da77391355749f3/uploads/2023/12/202312131874296229.pdf)):<br>(i) not compliant with the Ministry's quality control order;<br>(ii) design life completed;<br>(iii) rated capacity below 2 MW;<br>(iv) commercial or voluntary choice after 15 years of installation.<br>The 25.406 GW potential and the state table count only turbines below 2 MW. | A 2.05-2.3 MW turbine cannot qualify through rating (iii). It can still qualify through quality-control-order non-compliance (i), completed design life (ii) or age (iv). A note under clause 5 also covers turbines replaced within design life because of malfunction, workmanship or safety issues (judgement from the clause text). The plan does **not** rely on the repowering hook to justify the segment. |
| Tamil Nadu is not where the band is | The MNRE table, read from the scanned page, gives the 1.5-2 MW column as ([MNRE policy 2023](https://cdnbbsr.s3waas.gov.in/s3716e1b8c6cd17b771da77391355749f3/uploads/2023/12/202312131874296229.pdf)):<br>- Gujarat 1,805.35 MW<br>- Andhra Pradesh 1,701.2 MW<br>- Tamil Nadu 1,473.5 MW<br>- Karnataka 1,417.05 MW<br>Together these four are 70.6% of the 9,065.35 MW band (computed). Only 19.9% of Tamil Nadu's 7,386.5 MW below 2 MW is in the band; 55.5% is below 1 MW (computed). | Tamil Nadu is the **recruiting start**, justified only by proximity. NIWE ([NIWE AAP notice](https://niwe.res.in/static/pdf/NIWE-AAP_Internship_Programme.pdf)), IWPA ([windpro.org](https://www.windpro.org/)) and the Windergy India fair ([windergy.in](https://www.windergy.in/)) are all in Chennai. Interviews must also cover Gujarat and Andhra Pradesh, by phone or video. |
| The policy decision does not use condition data | The policy Annex gives an *indicative* method for valuing old assets in aggregation projects. It values an old asset by its PPA value: the NPV of tariff times average annual generation, minus O&M cost ([MNRE policy 2023](https://cdnbbsr.s3waas.gov.in/s3716e1b8c6cd17b771da77391355749f3/uploads/2023/12/202312131874296229.pdf)). Life extension is assessed and certified by a certification agency under UL 4143, or under any such standard issued by the BIS. | Decision value must come from a **maintenance decision a respondent confirms they make** (A5-A11), not from the policy. |
| NIWE is not a door to owners | The AAP is unpaid and on-site, with daily attendance. Interns work on NIWE's projects. Publication needs the Director General's approval, with the NIWE guide as second co-author. The intern agreement (Annexure III) also says the intern will not publish reports or papers using information obtained during the internship. Interns sign a data-protection declaration ([NIWE AAP notice](https://niwe.res.in/static/pdf/NIWE-AAP_Internship_Programme.pdf)). | NIWE is reclassified as an **optional internship with publication and data limits** (section 9), not as a route to customers. |
| Access must be the first gate | (review recommendation) | The data-access gate (section 9.4, A1) runs **before** the broader persona interviews. |

### 2.2 Segment definition used for discovery

| Element | Definition | Status |
|---|---|---|
| Asset class | Onshore, **geared** wind turbines of about 1.5-2.3 MW. Already recorded data only: 10-minute SCADA plus alarm and event logs. No new hardware. Fault focus: drivetrain (gearbox and its bearings, generator) and transformer. | Whether the Indian 1.5-2.3 MW fleet is mostly geared is **UNVERIFIED** (A2). |
| Organisations to interview | Organisations that **plan, carry out or pay for** maintenance on those turbines in India:<br>(a) owners and IPPs with an asset-management team;<br>(b) independent O&M service providers;<br>(c) OEM service arms.<br>Discovery must establish which of these controls the SCADA exports and the work orders. | Who controls data and work orders is **UNVERIFIED** (A1, A3). |
| Buyer hypothesis | The owner/IPP asset-management team **or** an independent O&M provider. We do not know which. | **ASSUMPTION TO TEST (A13)** |
| Secondary sub-segment | Owners of older turbines who face repair-vs-repower or life-extension choices under the MNRE 2023 policy. | Whether these owners still spend on condition-driven maintenance is **ASSUMPTION TO TEST (A11)**. |
| Geography | India. Recruiting starts in Chennai, Tamil Nadu (proximity only). Interviews must also include Gujarat and Andhra Pradesh, which lead the 1.5-2 MW band. | Band figures are sourced (table above). Regional differences in O&M practice are **UNVERIFIED**. |
| Out of scope | Offshore wind; gearless (direct-drive) turbines; solar; new installations under warranty. | Judgement |

**Scale context**
- India's wind operational capacity was 59.20 GW as of Sept 2026 ([IWTMA](https://www.indianwindpower.com/)).
- One Indian O&M provider claims "11 GW of Wind O&M assets" across 12 states, within more than 13 GW of renewable O&M assets held "along with its subsidiaries, strategic M&A investments and partnerships" ([INOX Green](https://www.inoxgreen.com/), vendor claim). That is about 18.6% of 59.20 GW (computed). INOX Green's page carries the INOX GFL group logo and does not call itself independent. It names no turbine OEM, so whether it services only INOX-group turbines or several OEMs' turbines is **UNVERIFIED**. The figure shows that dedicated O&M providers can hold a large book of Indian wind assets. It does **not** show what share of maintenance is controlled by owners, by OEMs or by independent providers; that share is **UNVERIFIED** (A1, A3).

**If the segment fails.** If the access gate fails (section 9.4), the judge and the reviewer both point to re-tabling the runner-up, Indian State Transport Undertaking bus depots (`research/V_judge_decision.md`; `research/V_adversarial_review_wind_choice.md`). This plan does not cover that segment.

---

## 3. User personas

All seven personas are **hypotheses**. Job titles in Indian wind O&M are **UNVERIFIED**. The mapping of the requested generic roles onto wind roles is an **ASSUMPTION TO TEST (A20)**.

### 3.1 Wind turbine technician (site technician)

| Item | Content | Evidence |
|---|---|---|
| Who | Climbs turbines, maintains and repairs them, and restarts them after faults. The employer may be the owner, an independent O&M provider or the OEM service arm. | Duties: [Sourced] [US BLS, Wind Turbine Technicians](https://www.bls.gov/ooh/installation-maintenance-and-repair/wind-turbine-technicians.htm) (US government occupational profile, not India). Indian employer mix: **ASSUMPTION TO TEST (A3)** |
| Goals | Restore turbines safely; complete routine maintenance; avoid wasted climbs; keep service records. | BLS: technicians inspect, lubricate and troubleshoot; routine maintenance happens about one to three times a year; technicians must keep records of all services they perform ([BLS](https://www.bls.gov/ooh/installation-maintenance-and-repair/wind-turbine-technicians.htm)) |
| Decisions | What the cause is on site; repair or replace a part; whether the turbine can be restarted; what to record at close-out. | Judgement, based on BLS duties |
| Current tools | Monitoring equipment, usually in the nacelle, that raises alerts and can be reached on or off site. Computers to diagnose electrical faults. Fall-protection harness. | [BLS](https://www.bls.gov/ooh/installation-maintenance-and-repair/wind-turbine-technicians.htm). Indian job-card format (paper, app, CMMS): **ASSUMPTION TO TEST (A12)** |

**Pains**

| # | Pain | Evidence |
|---|---|---|
| T-P1 | Remote monitoring can show a problem, but technicians must still travel to site to repair it. Any alert that sends a crew up a tower and finds nothing costs a trip and a climb. | Travel requirement: [Sourced] [BLS](https://www.bls.gov/ooh/installation-maintenance-and-repair/wind-turbine-technicians.htm). Cost of a wasted climb in India: **ASSUMPTION TO TEST (A8)** |
| T-P2 | Hazardous, tiring work: heights, a confined nacelle, extreme temperatures and on-call duty. Repeat or unnecessary climbs add exposure. | [Sourced] [BLS](https://www.bls.gov/ooh/installation-maintenance-and-repair/wind-turbine-technicians.htm). Indian conditions: **UNVERIFIED** |
| T-P3 | Diagnosis often takes longer than the repair itself. | [Sourced, not wind-specific, old secondary citation] Sexton et al. 2019 citing Kegg 1984 ([PHM 2019](https://papers.phmsociety.org/index.php/phmconf/article/download/790/phmc_19_790)) (via R1). Wind: **ASSUMPTION TO TEST (A16)** |
| T-P4 | Close-out coding is hard. Long code lists push people to "miscellaneous" or familiar codes, and delay between the job and data entry loses detail. | [Sourced, general industry] [Sexton, Hodkiewicz & Brundage 2019](https://papers.phmsociety.org/index.php/phmconf/article/download/790/phmc_19_790) (via R1). Wind India: **ASSUMPTION TO TEST (A15)** |
| T-P5 | Turbine event streams are large. EDP's public Wind Farm 1 operation log holds 256,231 records for 5 turbines from 1 Jan 2016 to 31 Aug 2017, about 84 records per turbine per day (computed). These are operation-log entries, not all actionable alarms. | Log size: [Sourced] [IEA Wind summary of EDP Open Data](https://iea-wind.org/wp-content/uploads/2024/07/EDP-OpenData-Details.pdf) (real field data, Portugal). Whether Indian teams ignore part of their alarm stream: **ASSUMPTION TO TEST (A7)** |
| T-P6 | Frequent false alarms erode trust and slow responses. | [Sourced, laboratory study with 80 students, not a plant] [Wiczorek & Meyer 2019](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2019.00519/full) (via R2; re-opened by the fact-checker). The "cry wolf" effect is stated in the paper's background from earlier literature. The experiment itself varied the aid's sensitivity and feedback, not the false-alarm rate, so it is not direct evidence for this pain. [Sourced, interviews at 15 European firms] [Hoffmann & Lasch 2025](https://link.springer.com/article/10.1007/s41471-024-00204-3) (via R2). Wind India: **ASSUMPTION TO TEST (A7)** |

### 3.2 O&M planner / scheduler (may be the site in-charge)

| Item | Content | Evidence |
|---|---|---|
| Who | Decides what work happens next week and arranges parts, people, permits and lifting equipment. In a wind farm this may be the same person as the site in-charge. | Generic role: [Sourced] [SMRP 2018 workshop](https://pemac.org/sites/default/files/2018_SMRP_BPMW_Full_Day.pdf); [Palmer via Accendo review](https://accendoreliability.com/review-maintenance-planning-scheduling-handbook-doc-palmer/) (via R1). Wind role merger: **ASSUMPTION TO TEST (A20)** |
| Goals | Keep turbines available; complete scheduled maintenance on time; avoid jobs stalling for parts or permits. | Generic: SMRP metrics on planned work, schedule compliance and backlog ([SMRP 2018](https://pemac.org/sites/default/files/2018_SMRP_BPMW_Full_Day.pdf), via R1) |
| Decisions | Which jobs go into the weekly plan, in what order; when to request a crane; whether to defer a job. | Generic: [SMRP 2018](https://pemac.org/sites/default/files/2018_SMRP_BPMW_Full_Day.pdf) (via R1). Crane decision: **ASSUMPTION TO TEST (A6)** |
| Current tools | CMMS, spreadsheets or paper. In a 2020 US-centred survey (n=171), plants used CMMS 50%, in-house spreadsheets 47% and paper records 46% (multiple answers allowed) ([Plant Engineering 2020 study](https://www.advancedtech.com/wp-content/uploads/2020/03/2020-ATS_Plant-Engineering-Maintenance-Study-Results.pdf), via R3; survey of *Plant Engineering* recipients at manufacturing facilities, 22% of respondents outside the US; sponsored by ATS, advancedtech.com). A Gujarat-headquartered renewable company previously tracked work orders offline in spreadsheets before adopting IBM Maximo Renewables ([IBM KP Group case](https://www.ibm.com/case-studies/kp-group), vendor claim; the Maximo deployment covers solar and hybrid plants, wind is not mentioned in that context). | Indian wind O&M tooling: **ASSUMPTION TO TEST (A12)** |

**Pains**

| # | Pain | Evidence |
|---|---|---|
| P-P1 | Jobs wait for parts and materials. CMMS products ship statuses for this, such as "waiting on material". | [Sourced, general industry] [IBM Maximo statuses](https://www.ibm.com/support/pages/node/1112013); [Assetivity case](https://www.assetivity.com.au/articles/asset-management/coordinating-activity-between-maintenance-and-supply-a-case-study/) (via R1). Wind India: **ASSUMPTION TO TEST (A6)** |
| P-P2 | Reactive work breaks the weekly schedule. | [Sourced, general industry] [SMRP 2018](https://pemac.org/sites/default/files/2018_SMRP_BPMW_Full_Day.pdf) (via R1) |
| P-P3 | Priorities are often set by whoever pushes hardest rather than by a rule. | [Sourced, practitioner, general industry] [Reliabilityweb](https://reliabilityweb.com/articles/entry/work_prioritization_emotion_vs._logic) (via R1). Wind India: **ASSUMPTION TO TEST (A5)** |
| P-P4 | Major-component jobs (gearbox, generator, main bearing, transformer) depend on scarce cranes and specialist crews, so they compete for a limited budget. | **ASSUMPTION TO TEST (A6)**. No wind-specific source opened. |
| P-P5 | Wind and weather restrict when climbing and lifting can be done, so high-wind months compress maintenance windows. | **ASSUMPTION TO TEST (A17)**. No source opened. |
| P-P6 | Shutdowns may need coordination with the distribution utility. | INOX Green lists coordination with DISCOMs as part of its O&M service ([INOX Green](https://www.inoxgreen.com/), vendor page). Whether this constrains maintenance timing: **ASSUMPTION TO TEST (A17)** |
| P-P7 | Major work is planned by season. It is pushed into the low-wind months and kept out of the high-generation months (assumed to be the south-west monsoon months in India), so the cost of downtime changes through the year. | **ASSUMPTION TO TEST (A24)**. No source opened. The adversarial review's O&M persona raised it as outside knowledge, not as a source (`product/ADVERSARIAL_REVIEW.md`, om_manager-13). |
| P-P8 | Turbines are curtailed or derated on instruction from the grid operator or DISCOM. Curtailed periods change what downtime costs, and they can look like turbine behaviour in the data. | **ASSUMPTION TO TEST (A23)**. No source opened. Same origin as P-P7. |

### 3.3 Reliability / performance engineer (central team at an IPP or O&M provider)

| Item | Content | Evidence |
|---|---|---|
| Who | Analyses fleet data to find emerging faults and repeat failures and to explain under-performance. Sets monitoring rules. | Generic role: [Keeter](https://reliabilityweb.com/articles/entry/priority_vs_criticality); [Lukens et al. 2019](https://papers.phmsociety.org/index.php/phmconf/article/download/836/phmc_19_836) (via R1). Existence of this role in Indian wind organisations: **ASSUMPTION TO TEST (A20)** |
| Goals | Catch drivetrain and transformer problems before secondary damage; reduce repeat failures; keep monitoring credible. | Judgement |
| Decisions | Which turbines to investigate; alarm thresholds; root cause; whether to recommend an inspection. | Judgement |
| Current tools | SCADA exports and historians; condition-monitoring vendor portals; spreadsheets or scripts. For example, ONYX Insight sells CMS sensing plus software and says it connects 15 CMS hardware types ([ONYX Insight](https://www.onyxinsight.com/), vendor claim). | Indian toolset: **ASSUMPTION TO TEST (A14)** |

**Pains**

| # | Pain | Evidence |
|---|---|---|
| R-P1 | When a fault started is uncertain. The CARE dataset's authors say the start of anomalous behaviour is often unclear and mislabelled ground truth cannot be fully ruled out. For Farms B and C (offshore Germany) they also say the status is often logged only when it changes, which can fail after a brief communication error. | [Sourced] [CARE paper v2](https://arxiv.org/html/2404.10320v2) (real field data, Portugal and Germany) |
| R-P2 | Failure records are thin. EDP's public failure log has 23 records for 5 turbines (Mar 2016 to Aug 2017), each with Turbine_ID, Component, Timestamp and a short Remarks text. | [Sourced] [IEA Wind EDP summary](https://iea-wind.org/wp-content/uploads/2024/07/EDP-OpenData-Details.pdf) (real field data). Indian record depth: **ASSUMPTION TO TEST (A4, A15)** |
| R-P3 | Maintenance work-order fields are often missing or wrong. Cleaning assumptions go undocumented. | [Sourced, general industry] [Hodkiewicz & Ho 2016](https://www.emerald.com/insight/content/doi/10.1108/JQME-04-2015-0013/full/html); [Lukens et al. 2019](https://papers.phmsociety.org/index.php/phmconf/article/download/836/phmc_19_836) (via R1) |
| R-P4 | SCADA, alarm logs and work records are held by different parties (owner, O&M provider, OEM), so joining them takes effort. | **ASSUMPTION TO TEST (A1, A4)** |
| R-P5 | Wind fault results rarely compare across studies, because most data are released only for the research that uses them. | [Sourced] [CARE paper v2](https://arxiv.org/html/2404.10320v2) |
| R-P6 | Investigating false alarms in a remote site costs money, which may change the cost-benefit of condition monitoring. | [Sourced, offshore wind modelling study; abstract only] [May & McMillan 2013](https://strathprints.strath.ac.uk/54903/). Onshore India: **ASSUMPTION TO TEST (A8)** |

### 3.4 Maintenance manager (head of O&M at an owner or O&M provider)

| Item | Content | Evidence |
|---|---|---|
| Goals | Availability, cost, safety and contract KPIs. SMRP frames the manager's questions as: is work managed effectively, is reliability adequate, are labour, materials and money used well? | [Sourced, generic] [SMRP 2018](https://pemac.org/sites/default/files/2018_SMRP_BPMW_Full_Day.pdf) (via R1) |
| Decisions | Staffing; contracts and subcontractors; spares; which tools and services to adopt; deferral policy. | Judgement; adoption ownership in maintenance or production per [Wagner & Hellingrath 2021](https://papers.phmsociety.org/index.php/ijphm/article/download/2933/1736) (via R2) |
| Current tools | Monthly KPI reports, CMMS dashboards, contractor reports, monitoring-vendor reports. | **ASSUMPTION TO TEST (A12, A14)** |

**Pains**

| # | Pain | Evidence |
|---|---|---|
| M-P1 | Contracted availability figures can be disputed. A vendor sells reconciliation of OEM availability calculations and "dispute-ready reports". | [Sourced, vendor claim, no India mention] [Clir](https://www.clir.eco/). Indian owner-OEM disputes: **ASSUMPTION TO TEST (A9)** |
| M-P2 | The return on predictive maintenance is uncertain, and benefits appear only in the medium to long term. | [Sourced, interviews] [Hoffmann & Lasch 2025](https://link.springer.com/article/10.1007/s41471-024-00204-3) (via R2; the fact-checker could not open it, as Springer redirected to a login). [Sourced, consultancy, IoT in general, not PdM] [Bain 2018](https://www.bain.com/about/media-center/press-releases/2018/bain-predicts-the-iot-market-will-more-than-double-by-2021/) names "uncertain returns on investment" as one of three main IoT adoption barriers. It does not mention a medium- to long-term horizon (via R2; re-opened by the fact-checker). |
| M-P3 | Pilots stall before scale-up. How often this happens depends on the survey: from 7% to more than 70% of companies. | [Sourced, consultancy surveys] [WEF 2019](https://www3.weforum.org/docs/WEF_4IR_Beacons_of_Technology_and_Innovation_in_Manufacturing_report_2019.pdf?lng=en); [LNS Research 2021](https://blog.lnsresearch.com/pilot-purgatory-in-industrial-transformation-is-fake-news) (via R2) |
| M-P4 | PdM-specific KPIs are missing, and maintenance is not treated as strategic. | [Sourced, interviews] [Hoffmann & Lasch 2025](https://link.springer.com/article/10.1007/s41471-024-00204-3) (via R2) |
| M-P5 | Alerts from several sources (OEM, CMS vendor, SCADA) arrive with no common ranking. | **ASSUMPTION TO TEST (A5, A7)** |

### 3.5 Plant / operations manager → in wind: asset manager or owner's representative

There is no factory-style plant manager at a wind farm. The closest role is the owner's asset manager, who answers for generation against the PPA. This mapping is an **ASSUMPTION TO TEST (A20)**.

| Item | Content | Evidence |
|---|---|---|
| Goals | Generation and revenue against the PPA; asset value; O&M contract performance. | Judgement. PPA framing: [MNRE policy 2023](https://cdnbbsr.s3waas.gov.in/s3716e1b8c6cd17b771da77391355749f3/uploads/2023/12/202312131874296229.pdf) |
| Decisions | Approve major repairs; choose repair, repowering or life extension for old turbines; renew or retender O&M contracts. | Repowering and life-extension routes: [MNRE policy 2023](https://cdnbbsr.s3waas.gov.in/s3716e1b8c6cd17b771da77391355749f3/uploads/2023/12/202312131874296229.pdf). Who decides: **ASSUMPTION TO TEST (A11, A13)** |
| Current tools | Generation and availability reports, PPA terms, O&M contract reports. For repowering: a Detailed Project Report submitted to the State or Central Nodal Agency. | DPR route: [MNRE policy 2023](https://cdnbbsr.s3waas.gov.in/s3716e1b8c6cd17b771da77391355749f3/uploads/2023/12/202312131874296229.pdf). Report tooling: **ASSUMPTION TO TEST (A12)** |

**Pains and context**

| # | Pain or context | Evidence |
|---|---|---|
| A-P1 | The policy's *indicative* asset valuation for aggregation repowering uses tariff, the 3-year average delivered generation and O&M cost. Component condition does not appear. Where no SERC/CERC tariff order sets O&M cost, the policy's default is 2% of the turbine's original capital cost in the first year, escalated 5% a year. | [Sourced] [MNRE policy 2023, Annex](https://cdnbbsr.s3waas.gov.in/s3716e1b8c6cd17b771da77391355749f3/uploads/2023/12/202312131874296229.pdf) |
| A-P2 | Life extension must be assessed and certified by a certification agency under UL 4143, and total life cannot exceed 40 years from commissioning. | [Sourced] [MNRE policy 2023](https://cdnbbsr.s3waas.gov.in/s3716e1b8c6cd17b771da77391355749f3/uploads/2023/12/202312131874296229.pdf). UL 4143's published scope: rules and procedures for life extension, a process that rates risk by relating failure-mode severity to confidence, and on-shore turbines only. The scope does not say whether SCADA or condition evidence is used ([UL 4143 page](https://www.shopulstandards.com/ProductDetail.aspx?productId=UL4143)). Whether assessors ask for SCADA history: **ASSUMPTION TO TEST (A10)** |
| A-P3 | "Aggregation projects" group turbines owned by multiple owners with shared common infrastructure. Decisions may need several owners to agree. | Definition: [MNRE policy 2023](https://cdnbbsr.s3waas.gov.in/s3716e1b8c6cd17b771da77391355749f3/uploads/2023/12/202312131874296229.pdf). Whether multi-owner sites complicate maintenance decisions: **ASSUMPTION TO TEST (A18)** |
| A-P4 | Under an O&M contract the owner may not hold SCADA exports or maintenance records, so condition evidence is hard to get. | **ASSUMPTION TO TEST (A1)** |
| A-P5 | Shortfalls are hard to attribute between wind resource, grid and turbine faults. | **ASSUMPTION TO TEST (A9)** |

### 3.6 IT/OT security

| Item | Content | Evidence |
|---|---|---|
| Goals | Protect control systems; meet Indian cyber-security obligations. | CERT-In Directions 2022 cover SCADA/OT incidents, 6-hour reporting and 180-day log retention ([CERT-In Directions](https://www.cert-in.org.in/PDF/CERT-In_Directions_70B_28.04.2022.pdf), via R5). The CEA draft Cyber Security in Power Sector Regulations 2024 exist ([Indian Infrastructure report](https://indianinfrastructure.com/2024/08/21/cea-notifies-draft-cea-cyber-security-in-power-sector-regulations-2024/), via R2). Their final status is **UNVERIFIED**. |
| Decisions | Whether any data may leave; in what form; who may access remotely; what a vendor must provide. | NIST recommends a cross-functional OT security team, a DMZ, and authenticated, logged remote maintenance ([NIST SP 800-82r3](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-82r3.pdf), via R1) |
| Current tools | Firewalls/DMZ, vendor security questionnaires. CISA and 11 partner agencies list 12 security elements OT owners should demand when buying, e.g. logging, SBOM, no default passwords, data protection to and from vendors. | [CISA Secure by Demand](https://www.ic3.gov/CSA/2025/250113.pdf) (via R2) |

**Pains**

| # | Pain | Evidence |
|---|---|---|
| S-P1 | Some firms judge the risk of networking plants as too high, and cite data manipulation and intrusion. | [Sourced, interviews] [Hoffmann & Lasch 2025](https://link.springer.com/article/10.1007/s41471-024-00204-3) (via R2) |
| S-P2 | Security is the top concern in IoT purchasing, and customers say they would buy more if it were addressed. | [Sourced, consultancy survey] [Bain 2018](https://www.bain.com/about/media-center/press-releases/2018/bain-predicts-the-iot-market-will-more-than-double-by-2021/) (via R2) |
| S-P3 | Indian wind owners may have no dedicated OT security function. The decision may then fall to an OEM or the O&M provider. | **ASSUMPTION TO TEST (A13)** |
| S-P4 | An offline, read-only copy of exported files is acceptable where a live connection is not. | **ASSUMPTION TO TEST (A19)** |

### 3.7 Buyer / finance

| Item | Content | Evidence |
|---|---|---|
| Goals | Predictable O&M cost; returns on spend; clean procurement. | Judgement |
| Decisions | Approve spend; qualify vendors; fund (or refuse) pilots. | Formal finance sign-off for PdM is **UNVERIFIED** (R2 found no source) |
| Current tools | Budgets; tariff-order O&M norms; vendor qualification. Large buyers may qualify vendors by invitation through e-procurement platforms. Example: Tata Steel UK via SAP Ariba ([Tata Steel UK](https://www.tatasteeluk.com/suppliers/ariba), via R2; UK business, not wind). | Wind buyer process: **ASSUMPTION TO TEST (A13)** |

**Pains**

| # | Pain | Evidence |
|---|---|---|
| F-P1 | Value and ROI alignment and the cost to scale are the main reasons pilots stall. | [Sourced, consultancy] [WEF 2019](https://www3.weforum.org/docs/WEF_4IR_Beacons_of_Technology_and_Innovation_in_Manufacturing_report_2019.pdf?lng=en) (via R2) |
| F-P2 | Published downtime-reduction figures are weak evidence. A NIST survey-based estimate uses 71 usable US responses (85 received). Its downtime and defect differences come from comparing groups of respondents, so they are associational, not causal. R2 adds that most other figures in circulation are self-reported or vendor-extrapolated, and that this is the only government-sourced estimate it found. | NIST figures: [Sourced] [Thomas & Weiss 2021](https://pmc.ncbi.nlm.nih.gov/articles/PMC9890517/) (via R2; re-opened by the fact-checker). "Most other figures" and "only" are **R2's synthesis** of several sources, not a statement in Thomas & Weiss (`research/R2_pdm_adoption_failures.md`, section 3). |
| F-P3 | Spending on older turbines may be squeezed while repowering is being considered. | **ASSUMPTION TO TEST (A11)** |
| F-P4 | Central-government buyers can relax prior-turnover, prior-experience and EMD requirements for DPIIT-recognised startups (GFR 2017). This applies only if the buyer is a ministry, department or CPSE. | [Sourced] [Startup India procurement](https://www.startupindia.gov.in/content/sih/en/public_procurement.html) (via R2). Whether any target buyer is a CPSE: **UNVERIFIED** |

---

## 4. Current-workflow map: work request to close-out (Indian onshore wind, as hypothesised)

**Status of this map.** No wind-specific CMMS workflow for India was found in a source opened in this session.
- The **stages** are the generic work-order lifecycle from R1:
  - [SMRP 2018](https://pemac.org/sites/default/files/2018_SMRP_BPMW_Full_Day.pdf) (via R1);
  - [IBM Maximo statuses](https://www.ibm.com/support/pages/node/1112013) (via R1);
  - [Lukens et al. 2019](https://papers.phmsociety.org/index.php/phmconf/article/download/836/phmc_19_836) (via R1).
- **Wind-specific details** are sourced where possible. Otherwise they are marked as assumptions.
- **Interviews must redraw this map** from what respondents describe they did last time.

### 4.1 Stages

| Stage | What happens (hypothesis) | Who (hypothesis) | Records created | Known or suspected delays | Evidence |
|---|---|---|---|---|---|
| **0. Detection** | A fault stops a turbine and raises a controller alarm, or scheduled maintenance, an inspection, a CMS alert, an analytics vendor's alert or an owner's own SCADA review finds a problem. | Turbine controller; OEM or O&M remote monitoring; CMS vendor; reliability engineer | Alarm log; operation log; vendor alert | Alarm volume; false alerts | Nacelle monitoring raises alerts and can be reached off site ([BLS](https://www.bls.gov/ooh/installation-maintenance-and-repair/wind-turbine-technicians.htm)). Alarm logs exist as a record type ([Hill of Towie dataset](https://zenodo.org/records/22662930), real field data, Scotland), as do turbine operation logs ([IEA EDP summary](https://iea-wind.org/wp-content/uploads/2024/07/EDP-OpenData-Details.pdf), real field data; Portugal per the [CARE Zenodo page](https://zenodo.org/records/15846963)). CMS vendor alerting: [ONYX Insight](https://www.onyxinsight.com/) (vendor claim). Who watches alarms in India: **ASSUMPTION TO TEST (A3)** |
| **1. Remote triage / reset** | Someone decides whether to reset remotely, dispatch a technician, or log for later. | OEM or O&M control room, or site in-charge | Possibly none, or a log entry | Unknown | **ASSUMPTION TO TEST (A3, A16)**. No source opened. |
| **2. Work request** | A job is raised in a CMMS, spreadsheet, register or message. | Site in-charge, technician, remote operator | Work request | Request may never be formalised | Generic: SMRP says no maintenance work without a work order ([SMRP 2018](https://pemac.org/sites/default/files/2018_SMRP_BPMW_Full_Day.pdf), via R1). Indian renewable-company example of spreadsheet work orders before Maximo: [IBM KP Group](https://www.ibm.com/case-studies/kp-group) (vendor claim, solar/hybrid). Indian wind tooling: **ASSUMPTION TO TEST (A12)** |
| **3. Approval and priority** | Request screened; priority set. | Site in-charge, O&M manager; owner for large jobs | Priority, approval | Approval wait (no quantitative source anywhere, per R1) | Generic priority methods and the "loudest voice" problem: [Reliabilityweb RIME](https://reliabilityweb.com/en/articles/ranking-index-for-maintenance-expenditures); [Reliabilityweb](https://reliabilityweb.com/articles/entry/work_prioritization_emotion_vs._logic) (via R1). Wind priority drivers (lost generation, season, curtailment): **ASSUMPTION TO TEST (A5, A23, A24)** |
| **4. Planning** | Parts, tools, crew, permits; for major components, crane and heavy-lift logistics. | Planner or site in-charge; storeroom; OEM for parts | Job plan, parts reservation | Parts waits; crane availability; OEM parts lead time | Parts waits (generic): [Assetivity](https://www.assetivity.com.au/articles/asset-management/coordinating-activity-between-maintenance-and-supply-a-case-study/) (via R1). Crane and OEM parts: **ASSUMPTION TO TEST (A6)** |
| **5. Scheduling** | Job slotted against crews, wind and weather windows, the season, and grid or DISCOM coordination. | Scheduler or site in-charge; operations | Schedule | Weather; season; curtailment; plant/grid condition; reactive work breaking the plan | Generic "waiting on plant condition" status: [IBM Maximo](https://www.ibm.com/support/pages/node/1112013) (via R1). DISCOM coordination listed as an O&M service: [INOX Green](https://www.inoxgreen.com/) (vendor). Weather windows: **ASSUMPTION TO TEST (A17)**. Seasonal planning and curtailment: **ASSUMPTION TO TEST (A23, A24)** |
| **6. Execution** | Isolation and permits, climb, repair or replace, test, restart. | Technicians; supervisor; EHS | Permit; job card | Travel to remote sites; climbing limits | Climbing, fall protection, travel to site: [BLS](https://www.bls.gov/ooh/installation-maintenance-and-repair/wind-turbine-technicians.htm). Energy isolation and permit-to-work (generic): [OSHA 1910.147](https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.147); [HSE HSG250](https://www.hse.gov.uk/pubns/books/hsg250.htm) (via R1). India: OSH Code 2020 ([PIB factsheet](https://static.pib.gov.in/WriteReadData/specificdocs/documents/2025/nov/doc20251122702801.pdf), via R1) |
| **7. Close-out** | Record what was done, the component, the cause and the downtime. | Technician; supervisor | Service record; failure-log entry; downtime classification | Missing or vague codes; data entered late | Technicians must keep service records ([BLS](https://www.bls.gov/ooh/installation-maintenance-and-repair/wind-turbine-technicians.htm)). A public wind failure log carries Turbine_ID, Component, Timestamp and short Remarks ([IEA EDP summary](https://iea-wind.org/wp-content/uploads/2024/07/EDP-OpenData-Details.pdf)). Hill of Towie derives downtime from SCADA combined with operator logs ([Zenodo 22662930](https://zenodo.org/records/22662930)). Indian close-out detail: **ASSUMPTION TO TEST (A15)** |
| **8. Review and reporting** | Availability and generation reports; reconciliation with OEM or contractor figures; possibly insurance claims. | O&M manager; asset manager; OEM | Monthly report; availability statement | Disputes over figures | Vendor sells OEM-availability reconciliation ([Clir](https://www.clir.eco/), vendor claim). A vendor markets integration into insurance ([Turbit](https://www.turbit.com/), vendor claim). India: **ASSUMPTION TO TEST (A9, A25)** |
| **9. Major asset decision** (occasional) | For old turbines: repair, repower or life-extend. | Owner; SNA/CNA; certification agency; DISCOM | DPR; certification | DISCOM consent; transmission; PPA moratorium | Routes, actors and consent steps: [MNRE policy 2023](https://cdnbbsr.s3waas.gov.in/s3716e1b8c6cd17b771da77391355749f3/uploads/2023/12/202312131874296229.pdf). Role of condition evidence: **ASSUMPTION TO TEST (A10, A11)** |

### 4.2 Where a product could intervene (hypotheses, none validated)

SentinelLoop's evidence today is on **simulated** C-MAPSS data and **synthetic** wind data only. These are candidate entry points that the interviews must confirm or kill. They are not capabilities shown on real wind data.

**What the product computes for wind today** (synthetic data only; `product/INITIAL_MARKET_AND_ASSET_CHOICE.md` section 1):
- It gives advisory anomaly flags on drivetrain temperatures, with policy-default due dates.
- Within a priority class, orders are ranked by deviation and consequence, a score labelled "not a probability".
- It gives no failure probability and no stated risk (`DECISION_LOG.md` PD-11). IP2's "interval" and IP3's "risk" are therefore not available for wind.
- The scheduler has no crane resource (`KNOWN_LIMITATIONS.md` P8). IP3's crane budget is a hypothesis to test, not a feature.

**Why season and curtailment matter to the product** (from the code, not from customers):
- The wind model makes no statement about a turbine unless power is above 5% of rated on at least half of the scoring window, the last 48 ten-minute points or 8 h (`src/sentinelloop/app/nbm.py`, `OP_FRAC`, `min_operating_frac`).
- Even on synthetic data, assessments were possible only 54-59% of the time (`product/evidence/wind_synthetic/w2.md`).
- Curtailment and derating setpoints are not in the data contract (`KNOWN_LIMITATIONS.md` M3).
- Downtime cost is a single figure per server deployment: one decision file per `serve --decision-config`, shared by every site that server holds (PD-24; `src/sentinelloop/app/admin.py`, `api.py`), with no seasonal variation.

Low-wind months and curtailed periods therefore reduce how often the product can say anything. If downtime costs vary with the season, they also change what a flag is worth (judgement; A17, A23, A24).

| ID | Intervention point | Stage | What it would change for whom | Depends on assumptions |
|---|---|---|---|---|
| IP1 | A **ranked list** of turbines showing early drivetrain or transformer anomalies from 10-minute SCADA, replacing per-alarm handling | 0-3 | Reliability engineer and O&M manager get one ordered queue instead of scattered alerts | A5, A7, A14 |
| IP2 | An **evidence pack** attached to each work request: trends, interval, data-quality flags | 2-3 | Planner and site in-charge can judge the request before dispatching a climb | A8, A16 |
| IP3 | **Capacity-constrained inspection ranking** under an explicit technician and crane budget, with a deferral list and its risk | 4-5 | Planner decides what fits next week | A6, A17 |
| IP4 | **Structured close-out capture** (component, finding, "nothing found"), so future alerts can be scored | 7 | Technician records less, in a consistent shape; reliability engineer gets labels | A15 |
| IP5 | An **alert budget**: false alerts per turbine per month, measured and capped | 0-1 | Technicians and managers can see whether alerts deserve trust | A7, A8 |
| IP6 | A **re-derivable decision record** (what was flagged, when, on what data) for contract or insurance discussions. The platform stores each assessment's inputs reference, feature hash, model checksum and policy hash, but has no re-derivation command, so it cannot demonstrate this today (`TECHNICAL_DEBT.md` F11; the 3,409-decision re-derivation is a competition-pipeline result) | 8 | O&M manager and asset manager can show evidence to an OEM, contractor or insurer | A9, A25 |
| IP7 | An **evidence summary for a life-extension assessor** | 9 | Asset manager supplies history to the certification agency | A10 (doubtful; UL 4143 scope does not mention SCADA) |

---

## 5. Existing alternatives and their limitations

**Sources.** Generic entries come from R3 (via R3). Wind-specific entries come from pages the writer opened. All vendor capability statements are **vendor claims**.

**What is already standard.** R3 found that anomaly detection, RUL or time-to-failure, sensor-health checks, automatic work orders and gated retraining are already documented by many vendors (`research/R3_competitive_landscape.md`, section 7). A small team cannot claim these as differentiators.

| Alternative | What it is | Evidence | Limitations relevant to this segment (sourced, or labelled analysis) |
|---|---|---|---|
| **Do nothing new:** time-based maintenance plus fixing faults as they occur | Routine maintenance a few times a year; repair after fault stops | BLS routine-maintenance frequency ([BLS](https://www.bls.gov/ooh/installation-maintenance-and-repair/wind-turbine-technicians.htm)). Generic US survey: preventive 76%, run-to-failure 60% ([Plant Engineering 2020](https://www.advancedtech.com/wp-content/uploads/2020/03/2020-ATS_Plant-Engineering-Maintenance-Study-Results.pdf), via R3) | Faults are found only once they stop the turbine. Secondary damage and crane lead time are not addressed (analysis). It costs nothing new, which is its strength. |
| **OEM service contract** | The OEM maintains turbines and may monitor them remotely | Turbofan analogue: OEM health monitoring inside risk-transfer contracts ([Rolls-Royce TotalCare](https://www.rolls-royce.com/products-and-services/civil-aerospace/services/totalcare.aspx), via R3). Indian wind OEM contracts: **UNVERIFIED** | The owner may not see the data or the reasoning (**ASSUMPTION A1**). Third parties may be shut out of the data path (analysis). |
| **Dedicated O&M provider** | Full-service O&M by a specialist O&M firm, which may or may not be tied to an OEM | INOX Green: more than 13 GW renewable O&M, 11 GW wind, 12 states, "2000+ Team Strength"; lists "Predictive Maintenance" as a service but describes no method ([INOX Green](https://www.inoxgreen.com/), vendor claim). The page carries the INOX GFL group logo and does not call itself independent; its relationship to the INOX Wind OEM is **UNVERIFIED** on the page opened. A truly independent (non-OEM) Indian wind O&M provider has **not** been identified from a source opened in this session. | Bundled, so the owner buys outcomes, not tools. The provider could be a buyer, a channel or a competitor (analysis). |
| **Wind CMS hardware plus analytics** | Drivetrain sensing, software and engineering services | ONYX Insight: 32,000+ turbines monitored, faults caught up to 24 months ahead, 15 CMS hardware types ([ONYX](https://www.onyxinsight.com/), vendor claims). Bengaluru office ([ONYX locations](https://onyxinsight.com/company/our-locations/)) | Needs CMS hardware (analysis). Already present in India. |
| **Wind SCADA-AI vendor** | Neural networks on existing SCADA; alarms; O&M assistant; insurance integration | Turbit: 3,500+ turbines, 40+ customers ([Turbit](https://www.turbit.com/), vendor claims). Paid one-off backtest on historical SCADA from major OEMs; at least 3 years per turbine, 5+ ideal; targets gearbox, generator and main-bearing events ([Turbit backtest](https://www.turbit.com/backtest), vendor) | No India mention on the home page ([Turbit](https://www.turbit.com/)). It offers the same kind of retrospective backtest SentinelLoop would propose, so this is direct overlap (analysis). |
| **Renewables APM/EAM** | Work orders, prioritisation and prognosis visuals for wind and solar | IBM Maximo Renewables: automatically create, track and prioritise work orders via Maximo Manage; turbine prognosis visualisations ([IBM Maximo Renewables](https://www.ibm.com/products/maximo/renewables), vendor). Indian customer KP Group, Gujarat, with more than 1.4 GW managed across 70+ sites ([IBM KP Group](https://www.ibm.com/case-studies/kp-group), vendor; solar/hybrid focus) | Enterprise infrastructure: Maximo Application Suite runs on Red Hat OpenShift ([IBM docs](https://www.ibm.com/docs/en/SSRHPA_cd/appsuite/overview/c_technical_overview.html), via R3). Shows that at least one Indian renewable company already buys a global APM, for solar and hybrid plants (analysis). |
| **Performance and contract analytics** | Portfolio monitoring, anomaly detection, OEM availability reconciliation | Clir: dispute-ready reports; solar, BESS and wind ([Clir](https://www.clir.eco/), vendor) | No India mention on the page. Aimed at investors and asset managers, not technicians (analysis). |
| **General APM / PdM platforms** | Normal-behaviour models, time-to-failure, work-order links | Senseye ([Siemens](https://www.siemens.com/us/en/products/services/digital-enterprise-services/analytics-artificial-intelligence-services/predictive-services/senseye-predictive-maintenance/how-it-works.html)); GE Vernova SmartSignal ([brochure](https://gevernova.com/software/sites/default/files/2024-10/brochure-ai-powered-predictive-analytics-smartsignal.pdf)); AVEVA ([page](https://www.aveva.com/en/products/predictive-analytics/)) (all via R3; vendor claims) | Need onboarding and data connection. Not wind-specific on the pages R3 opened (via R3). |
| **Cloud building blocks** | Managed anomaly detection | AWS IoT SiteWise added scheduled retraining with automatic or manual promotion in Sept 2025 ([AWS](https://aws.amazon.com/about-aws/whats-new/2025/09/aws-iot-sitewise-retraining-anomaly-detection-models), via R3). Amazon Lookout for Equipment support ended 7 Oct 2026 ([AWS](https://aws.amazon.com/blogs/machine-learning/preserve-access-and-explore-alternatives-for-amazon-lookout-for-equipment/), via R3) | Need cloud connectivity and in-house ML staff (analysis). AWS has withdrawn managed products in this space: Lookout for Equipment (discontinued 7 Oct 2026; new customers closed 7 Oct 2025, confirmed on the AWS page above) and, per R2, Monitron (closed to new customers 31 Oct 2024; not re-opened). That is one vendor, not a general exit. |
| **Spreadsheets, paper and in-house scripts** | Owner's or provider's own trending | Generic: spreadsheets 47%, paper 46% ([Plant Engineering 2020](https://www.advancedtech.com/wp-content/uploads/2020/03/2020-ATS_Plant-Engineering-Maintenance-Study-Results.pdf), via R3). An Indian renewable company used spreadsheets before Maximo ([IBM KP Group](https://www.ibm.com/case-studies/kp-group), vendor; solar/hybrid) | Depends on individuals. Hard to audit (analysis). Indian wind prevalence: **ASSUMPTION A12** |
| **Human analyst services** | Certified analysts review data and alarms | SKF Remote Analysis ([SKF](https://us.promo.skf.com/acton/media/22336/connected-technologies-services), via R3) | Recurring cost. Not documented for Indian wind (via R3; **UNVERIFIED**). |

**Analysis, not validated.** R3's plausible differentiators are audit-grade re-derivable decisions (the platform has no re-derivation command yet, `TECHNICAL_DEBT.md` F11), published calibration (what we would publish includes misses: the RUL model's P(failure) is not calibrated, `product/evidence/calibration/c2.md`, and the wind thresholds have no nominal false-alarm rate, `KNOWN_LIMITATIONS.md` M4) and explicit abstention, a vendor-neutral layer between monitoring and the CMMS, and backtesting maintenance policies (`research/R3_competitive_landscape.md` 8.2). The Turbit backtest offer above already covers part of the backtesting idea in wind. Discovery must find out whether any respondent values the rest. The interview guide never asks about these features directly.

---

## 6. Stakeholder map

Influence and interest ratings are **ASSUMPTIONS TO TEST**. They are not findings. Generic evidence on who decides PdM purchases:
- Bain reports that OT staff were the key decision-makers or influencers in 85% of IoT purchases ([Bain 2021](https://www.bain.com/insights/selling-iot-solutions-to-experts/), via R2).
- A reference model built from 11 practitioner interviews places project ownership in maintenance or production, with management as sponsor and IT supporting the architecture ([Wagner & Hellingrath 2021](https://papers.phmsociety.org/index.php/ijphm/article/download/2933/1736), via R2).
- Finance's sign-off role is **UNVERIFIED** (R2).

| Group | Stakeholder | Likely home | Role in adoption (hypothesis) | What they would need to see (hypothesis) | Evidence status |
|---|---|---|---|---|---|
| **Buyer** | O&M head / maintenance manager | Owner/IPP or O&M provider | Champion and budget holder for tools | Fewer wasted climbs; earlier major-component planning; low false-alert rate | A13 |
| **Buyer** | Asset manager / owner's representative | Owner/IPP | Economic buyer for owner-side evidence | Evidence that holds up in contract or insurance discussions; generation protected | A9, A13 |
| **Operator / user** | Reliability or performance engineer | IPP or O&M provider central team | Evaluator and daily user | Measured detection and false-alarm rates on their own history | A14 |
| **Operator / user** | Planner / site in-charge | Site | Daily user of ranked lists | Fits the weekly planning rhythm; explains each item | A5, A6 |
| **Operator / user** | Technicians | Site (employer varies) | End user; source of close-out data | Fewer climbs that find nothing; little extra data entry | A8, A15 |
| **IT/OT security** | IT/OT security or SCADA administrator | Owner, O&M provider or OEM | Gatekeeper with veto over data movement | Offline, read-only data flow; CISA-style security pack | A19; [CISA](https://www.ic3.gov/CSA/2025/250113.pdf) (via R2) |
| **Safety** | EHS / site safety officer | Owner or O&M provider | Gatekeeper for any change to climb or permit routines | No new site work; nothing that pressures crews to climb in unsafe conditions | Generic permit and isolation rules: [OSHA](https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.147); [HSE](https://www.hse.gov.uk/pubns/books/hsg250.htm) (via R1). India: [OSH Code factsheet](https://static.pib.gov.in/WriteReadData/specificdocs/documents/2025/nov/doc20251122702801.pdf) (via R1). Wind India role: **UNVERIFIED** |
| **Finance** | Finance / procurement | Owner or O&M provider | Approver; vendor qualification | Payback logic built on their own cost figures; vendor qualification documents | Sign-off mechanics **UNVERIFIED** (R2) |
| External | OEM service arm | OEM | Data holder; possible blocker or partner | Unknown | A1 |
| External | O&M provider (independent or OEM-group) | e.g. [INOX Green](https://www.inoxgreen.com/) (vendor page; INOX GFL group logo; independence **UNVERIFIED**) | Buyer, channel or competitor | Unknown | A13 |
| External | Certification agency (UL 4143 life extension) | Third party | Possible consumer of evidence | Unknown | A10; [MNRE policy](https://cdnbbsr.s3waas.gov.in/s3716e1b8c6cd17b771da77391355749f3/uploads/2023/12/202312131874296229.pdf) |
| External | State or Central Nodal Agency; DISCOM | Government / utility | Repowering consents; not a maintenance buyer | Not applicable to maintenance | [MNRE policy](https://cdnbbsr.s3waas.gov.in/s3716e1b8c6cd17b771da77391355749f3/uploads/2023/12/202312131874296229.pdf) |
| External | NIWE | MNRE institute, Chennai | Training, certification, policy database (§11); **not** an owner door | Not applicable | Departments, training and Vayumitra: [NIWE](https://niwe.res.in/). Policy §11: [MNRE policy](https://cdnbbsr.s3waas.gov.in/s3716e1b8c6cd17b771da77391355749f3/uploads/2023/12/202312131874296229.pdf) |
| External | Insurers | Financial | Possible evidence consumer | Unknown | A vendor markets insurance integration ([Turbit](https://www.turbit.com/), vendor claim). India **UNVERIFIED** |

---

## 7. Adoption barriers and purchasing criteria (from R2)

### 7.1 Barriers

Each R2 barrier is mapped to its likely wind form (hypothesis) and to the interview questions that probe it.

| Barrier | R2 evidence | Likely wind/India form (hypothesis) | Probed by | Assumption |
|---|---|---|---|---|
| No failure labels; censoring by preventive maintenance | Interviewees lack run-to-failure data ([Hoffmann & Lasch](https://link.springer.com/article/10.1007/s41471-024-00204-3)). Machines are repaired before failure ([van Dinter et al.](https://agris.fao.org/search/fr/records/669f707f00eb85b7d72cf732)). NASA generated simulated degradation data with C-MAPSS because suitable run-to-failure validation data are scarce ([NASA data.gov](https://catalog.data.gov/dataset/simulating-degradation-data-for-prognostic-algorithm-development); simulated data). (All via R2; the data.gov page was re-opened by the fact-checker.) | Few recorded drivetrain events per fleet; vague close-out | R2, R3, T4 | A4, A15 |
| False alarms and alert fatigue | Offshore wind modelling ([May & McMillan](https://strathprints.strath.ac.uk/54903/)); trust falls with false alarms, as stated in the background of a student laboratory study ([Wiczorek & Meyer](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2019.00519/full), via R2; see T-P6) | Unproductive climbs; alarms ignored | T3, T5, R6, M5 | A7, A8 |
| Security and OT review | Top concern in IoT purchases ([Bain 2018](https://www.bain.com/about/media-center/press-releases/2018/bain-predicts-the-iot-market-will-more-than-double-by-2021/)); networking judged too risky ([Hoffmann & Lasch](https://link.springer.com/article/10.1007/s41471-024-00204-3)) (via R2) | Data cannot leave the SCADA network, or only via the OEM | S1-S4 | A19 |
| Integration with CMMS and processes | Underestimated by vendors ([Bain 2018](https://www.bain.com/about/media-center/press-releases/2018/bain-predicts-the-iot-market-will-more-than-double-by-2021/), via R2) | Work tracked in OEM systems, spreadsheets or messaging | P1, T4, C4 | A12 |
| Unclear ROI | Interviews ([Hoffmann & Lasch](https://link.springer.com/article/10.1007/s41471-024-00204-3)); WEF ([2019](https://www3.weforum.org/docs/WEF_4IR_Beacons_of_Technology_and_Innovation_in_Manufacturing_report_2019.pdf?lng=en)) (via R2) | No one can price a prevented gearbox failure | M2, F2 | A21 |
| Pilot purgatory | 7% to more than 70% stuck, depending on survey ([WEF](https://www3.weforum.org/docs/WEF_4IR_Beacons_of_Technology_and_Innovation_in_Manufacturing_report_2019.pdf?lng=en); [LNS](https://blog.lnsresearch.com/pilot-purgatory-in-industrial-transformation-is-fake-news), via R2) | Trials with no owner for scale-up | M3, F4 | A13 |
| Change management and skills | Reluctance, scarce data specialists, missing PdM KPIs ([Hoffmann & Lasch](https://link.springer.com/article/10.1007/s41471-024-00204-3)); Indian Industry 4.0 barriers: resistance to change, unclear benefits ([Goswami & Daultani 2022](https://www.emerald.com/insight/content/doi/10.1108/TQM-06-2021-0179/full/html)) (via R2) | Site teams follow OEM procedures; little analytics capacity | M1, R1 | A14, A20 |
| Explanations do not automatically build trust | Local explanations lowered trust in an online experiment ([Pedraza 2024](https://minds.wisc.edu/handle/1793/85271), MS thesis, via R2); design should be decision-led ([Golightly et al. 2018](https://ideas.repec.org/a/spr/infsem/v16y2018i3d10.1007_s10257-017-0343-1.html), via R2) | Engineers trust their own trend plots and OEM advice | R1, R6 | A14 |
| Data control by others | Not covered in R2 | OEM or O&M provider holds SCADA and records | O3, S2 | A1 |

### 7.2 Purchasing criteria buyers are reported to use

| Criterion | R2 evidence | What discovery must learn |
|---|---|---|
| Bottom-line value, not technology | McKinsey: work "bottom-line value backwards" ([McKinsey 2018](https://karriere.mckinsey.de/~/media/mckinsey/business%20functions/operations/our%20insights/how%20digital%20manufacturing%20can%20escape%20pilot%20purgatory/digital-manufacturing-escaping-pilot-purgatory.pdf), via R2) | Which cost lines respondents actually track for turbine failures (M2, F2) |
| Small, low-risk pilot on suitable assets | [Deloitte 2017](https://www.deloitte.com/us/en/insights/industry/manufacturing-industrial-products/industry-4-0/using-predictive-technologies-for-asset-maintenance.html); [Hoffmann & Lasch](https://link.springer.com/article/10.1007/s41471-024-00204-3) (via R2) | How their last trial was set up and judged (F4, M3) |
| Decision-led design | [Golightly et al. 2018](https://ideas.repec.org/a/spr/infsem/v16y2018i3d10.1007_s10257-017-0343-1.html) (via R2) | Which decisions they make weekly and monthly (P1, P4, M6) |
| Security assurance | 12 CISA elements ([CISA](https://www.ic3.gov/CSA/2025/250113.pdf)); IEC 62443 ([ISA](https://www.isa.org/62443)) (via R2) | What their last security review asked for (S3) |
| Integration and data portability | [Bain 2018](https://www.bain.com/about/media-center/press-releases/2018/bain-predicts-the-iot-market-will-more-than-double-by-2021/); [CISA](https://www.ic3.gov/CSA/2025/250113.pdf) (via R2) | Where work orders and SCADA exports live (C4, R4) |
| Reference customers and scale | Vendor case studies lead with fleet size and payback, e.g. [Siemens Senseye case](https://assets.new.siemens.com/siemens/assets/api/uuid:5803c43a-d25f-4b59-871c-ccfd43067abb/Automotivev2_original.pdf) (vendor, via R2) | Whom they asked for references last time (F5) |
| Risk transfer | Senseye "ROI Lock" refund offer ([ABI Research](https://www.abiresearch.com/market-research/insight/7780896-siemens-snaps-up-senseye-to-expand-its-pre?hsLang=en), via R2) | Whether past contracts included guarantees or penalties (M4) |
| Payback period | Buyers' *required* payback: **UNVERIFIED** (R2) | Payback rule used in their last approval (F1, F2) |
| Procurement route | Pilot then subscription; vendor qualification; GFR startup relaxations for central-government buyers ([Startup India](https://www.startupindia.gov.in/content/sih/en/public_procurement.html), via R2) | Steps the last new supplier went through (F5) |

---

## 8. Interview guide

### 8.1 Rules for every interview

1. **Do not describe SentinelLoop, its features, or "AI", "prediction", "RUL" or "early warning"** before the last five minutes. If asked what we are building, say we are a student team studying how wind maintenance decisions are made, and offer to explain at the end. At the end, answer truthfully and briefly: we have a prototype tested only on simulated data and are not selling anything.
2. **Ask about past behaviour, not opinions or the future.** "Tell me about the last time…" rather than "Would you…?" or "How important is…?". The Mom Test handbook frames customer conversations around avoiding biased feedback ([momtestbook.com](https://www.momtestbook.com/)). Its specific rules were not visible on the page opened, so the rules here are our own protocol.
3. **Avoid leading questions.** A leading question includes or implies the desired answer. Participants tend to mirror the interviewer's wording, and leading questions shut out unexpected insights. Do not restate answers in your own words, suggest answers, name things for the respondent, or assume how they feel ([Schade, NN/g 2017](https://www.nngroup.com/articles/leading-questions/)).
4. **One interviewer asks; a second takes verbatim notes.** Record audio only with explicit spoken consent.
5. **Ask for artefacts, not secrets.** Ask the respondent to describe the record or screen they used. Do **not** accept SCADA files, contracts or customer data during discovery. Data sharing belongs to a later, formal step with a written agreement.
6. **Use neutral follow-up probes:**
   - "What happened next?"
   - "Who else was involved?"
   - "How did you decide?"
   - "How long did that take?"
   - "What did that cost, roughly, and how do you know?"
   - "What else did you try?"
   - "Can you describe the screen or sheet you used?"
   - Silence. Let the respondent keep talking.
7. **Separate facts from opinions in notes.** Tag each note F (fact about past behaviour), O (opinion), or Q (quote). Tag the assumption IDs (section 10) each note supports or contradicts.

**Leading versus non-leading rewrites**

| Leading (do not use) | Why it leads | Non-leading (use) |
|---|---|---|
| "Wouldn't earlier gearbox warnings help you?" | Suggests the answer and the solution | "Tell me about the last gearbox problem on your turbines. When did anyone first notice something?" |
| "Are false alarms a big problem for you?" | Names the problem and assumes it matters | "When did a crew last go up a turbine and find nothing wrong? What had sent them?" |
| "How much would you pay for a tool that ranks inspections?" | Hypothetical, future, describes our product | "What did your team spend on monitoring or analysis services last year, and who approved it?" |
| "You said the OEM figures were wrong. Why do you distrust them?" | Restates in our words and assumes a feeling | "You mentioned the OEM figures…?" (pause) |
| "Do you struggle to get SCADA data from your O&M contractor?" | Assumes a struggle | "When did you last need SCADA data for a turbine? How did you get it?" |

### 8.2 Opening script (all respondents)

> "Thank you for your time. We are a student team studying how wind-farm maintenance decisions are made in India. There are no right answers; we want to hear what actually happened in specific recent situations. We will not ask for confidential documents or data. With your permission we will take notes; we will not record audio unless you agree. We will not quote you by name. You can stop at any time. Is that all right?"

### 8.3 Core questions (all personas)

- **C1.** Tell me about your role. What did a typical week look like last month?
- **C2.** Walk me through the last time a turbine you look after stopped unexpectedly. What happened first, and then what?
- **C3.** Who else was involved in that event, and what did each of them do?
- **C4.** What records were made about that event, and where are they kept now?

### 8.4 Persona-specific questions

**Technician (T)**
- **T1.** Think of the last fault call-out you attended. How did you learn about it, and what information did you have before you reached the turbine?
- **T2.** On that job, how did the time spent finding the cause compare with the time spent fixing it?
- **T3.** When did a crew last climb a turbine and find nothing that needed work? What had triggered the visit?
- **T4.** After the last job you finished, what did you write down or enter, where, and how long after the job?
- **T5.** Which turbine alarms or messages did your team deal with most often last month? What did you do with them?
- **T6.** Tell me about the last time you noticed something on a turbine before any alarm appeared. What did you do with what you noticed?

**Planner / scheduler / site in-charge (P)**
- **P1.** How did you decide what went into last week's work plan? Walk me through it.
- **P2.** Tell me about the last planned job that slipped. What held it up?
- **P3.** The last time a major component had to be replaced, how were the parts, lifting equipment and crew arranged, and how long did each step take?
- **P4.** When two jobs last competed for the same people or equipment, how was the order decided, and who decided?
- **P5.** Before you last scheduled an inspection instead of waiting, what information did you look at?
- **P6.** Over the last year, how, if at all, did wind or weather change when you could schedule work?
- **P7.** Over the last 12 months, in which months did your team do its major planned work? How were those months chosen, and who chose them?
- **P8.** In the last month, were any turbines stopped or limited for a reason other than a fault or maintenance? How did you find out, and where is that recorded?

**Reliability / performance engineer (R)**
- **R1.** When did you last analyse turbine data to look for a developing problem? Which data and tools did you use, and what did you find?
- **R2.** For the last component failure you investigated, how did you work out when the problem started?
- **R3.** Which data sources did you have to combine for that investigation, and what was missing or inconsistent?
- **R4.** How far back does the 10-minute SCADA history go for the turbines you look after? Where is it stored, and who can export it?
- **R5.** Tell me about the last change you made to an alarm limit or monitoring rule. What prompted it, and how did you check it?
- **R6.** The last time a monitoring system or an analyst flagged a problem that turned out not to be real, what happened next?
- **R7.** Think of the last period when turbines were stopped or limited on an outside instruction. How did you tell that period apart from a turbine problem in the SCADA data?

**Maintenance manager / head of O&M (M)**
- **M1.** Which numbers did you report upward last month, and to whom?
- **M2.** Tell me about the most expensive unplanned outage in the last 12 months. How was its cost worked out?
- **M3.** The last time a new tool, service or contractor was added to your O&M operation, how did that come about, and who had to agree?
- **M4.** What happened the last time availability or performance figures from the OEM or contractor differed from your own?
- **M5.** Last week, how many alerts or reports arrived from monitoring sources, and what happened to each kind?
- **M6.** When did you last decide to defer a repair? What did you weigh up?
- **M7.** How was the lost generation from the last two unplanned outages valued? What went into each figure?
- **M8.** What does your current O&M or OEM contract say about turbine availability, and what happened the last time that clause was applied?

**Asset manager / owner's representative (O)**
- **O1.** Walk me through how the last decision on a major repair to an older turbine was made.
- **O2.** Has your organisation looked at repowering or life extension for any turbines? If so, what happened, who was involved, and what information was asked for?
- **O3.** Under your current O&M arrangement, who holds the SCADA data and the maintenance records? When did you last ask for either, and what happened?
- **O4.** How was the last quarter's generation shortfall explained to you, and by whom?
- **O5.** What did you check before you last approved spending on a turbine?

**IT/OT security (S)**
- **S1.** The last time someone outside the company asked for turbine or SCADA data, what did the process look like from start to finish?
- **S2.** How does data leave the SCADA system today? Who exports it, in what form, and where does it go?
- **S3.** What did your last security review of a new software product or service ask the supplier for?
- **S4.** When were your remote-access rules for wind-farm control systems last changed, and what triggered the change?

**Buyer / finance (F)**
- **F1.** Tell me about the last O&M-related purchase you approved or reviewed. Which documents did you need?
- **F2.** How was the expected benefit of that purchase estimated, and was it checked afterwards?
- **F3.** How was the O&M budget for older turbines set last year, compared with newer ones?
- **F4.** What happened the last time a supplier proposed a pilot or trial?
- **F5.** Which qualification steps did the last new supplier go through, and how long did they take?

**Optional expert respondents (X)** (certification agency, consultant, insurer)
- **X1.** In the last turbine assessment you took part in, which records did you ask the owner for?
- **X2.** Which of those records were hardest to get, and why?

**Closing (all)**
- **Z1.** Is there anything about how maintenance decisions get made here that I should have asked and did not?
- **Z2.** Who else should we speak to, and would you be willing to introduce us? (Record only what the respondent actually agrees to. Never record a referral as agreed unless it was.)

That makes 51 questions in total: 4 core, 43 persona-specific, 2 optional expert and 2 closing. P7, P8, R7, M7 and M8 were added after the adversarial review (om_manager-13), to cover season, curtailment and contract availability terms. They test assumptions A23, A24 and A25. Each interview uses the 4 core questions, 4-6 questions for the respondent's persona, and the closing.

### 8.5 Note template (one per interview)

| Field | Content |
|---|---|
| Respondent code | e.g. W-07 (no names in shared notes) |
| Persona; organisation type | Owner/IPP, O&M provider, OEM service, other |
| State or region; fleet models mentioned | As stated by respondent |
| Facts (F) | Past events, with dates and numbers as stated |
| Opinions (O) | Clearly separated |
| Quotes (Q) | Verbatim, short |
| Assumptions touched | e.g. A1 contradicts; A7 supports |
| Follow-ups and referrals | Only what was actually agreed |

### 8.6 Consent and personal data

- Interview notes containing names and contacts are digital personal data under the Digital Personal Data Protection Act 2023 ([DPDP Act](https://prsindia.org/files/bills_acts/bills_parliament/2023/Digital_Personal_Data_Protection_Act,_2023.pdf), via R5).
- Per R5, most operative provisions of the DPDP Rules 2025 apply about 18 months after publication on 13 Nov 2025 ([DPDP Rules](https://www.meity.gov.in/static/uploads/2025/11/53450e6e5dc0bfa85ebd78686cadad39.pdf), via R5; R5's date calculation). The publication date and the 18-month figure are **UNVERIFIED** in this document: the MeitY PDF returned 403 to the fact-checker on 2026-10-18, and WebSearch was unavailable. Confirm before relying on any date.
- The team should still apply notice, consent, minimisation and deletion from day one (judgement):
  - store names separately from coded notes;
  - delete audio after transcription;
  - share only anonymised syntheses.
- This is not legal advice.

---

## 9. Recruiting plan

**Nothing in this section has happened.** No organisation or person has been contacted, and no one has agreed to anything. The channels listed exist (sourced). Whether they produce respondents is untested.

### 9.1 Channels

| # | Channel | Who it might reach | How the team could use it | Cost / constraint | Source |
|---|---|---|---|---|---|
| 1 | **Indian Wind Power Association (IWPA)**, Chennai | Possibly wind power producers (inferred from the name only; **UNVERIFIED**). Membership composition is not stated on the home page. | Email the secretariat asking whether a short research note could go to members, or whether a member meeting allows student attendance | Free to ask; outcome unknown | [windpro.org](https://www.windpro.org/): Chennai address, membership link, events section, contact emails |
| 2 | **Indian Wind Energy Association (InWEA)**, New Delhi | Claims 350+ members. Ran regional webinars on repowering older wind farms in 2021. | Ask whether members' O&M heads could be told about the study | Free to ask | [inwea.org](https://www.inwea.org/) |
| 3 | **IWTMA** (manufacturers' association), New Delhi | Members shown by logo include OEMs such as Suzlon, INOX Wind, Envision, Siemens Gamesa, Vestas and GE Vernova, plus component suppliers | Reach OEM service teams, the likely data holders (A1) | Conflict risk: OEMs may see owner-side analytics as competition (judgement) | [IWTMA](https://www.indianwindpower.com/) |
| 4 | **Windergy India** trade fair, Chennai | Project developers, asset owners, buyers, investors, advisers | Walk the floor; short conversations; collect introductions. The 2026 edition (7-9 Oct 2026, Chennai Trade Centre, organised by IWTMA and PDA Ventures) has already passed. The next edition's dates are **UNVERIFIED**. | Visitor terms unknown | [windergy.in](https://www.windergy.in/) |
| 5 | **NIWE National Training Course on Wind Energy Technology**, Chennai | About 50 participants from SNAs, OEMs, suppliers, developers and investors, IPPs, consultants, financial and insurance institutions, and government. Covers O&M of wind farms. | Attend the 31st course (3-5 Feb 2027; register by 22 Jan 2027). Talk with participants during breaks; never pitch. | Rs 5,900 student fee incl. GST, or Rs 17,700 professional; non-residential | [NIWE NTC-31](https://niwe.res.in/national-training/NTC-31/) |
| 6 | **NIWE Academic Associate Programme** | NIWE scientists; NIWE projects only | Optional internship for domain learning, **not** for customer access. Unpaid, on-site, daily attendance, applications by the 15th of each month. Publication needs DG approval and the NIWE guide as second co-author; the intern agreement also bars publishing reports or papers using information obtained during the internship. Data-protection declaration required. | Time cost; publication limits | [NIWE AAP](https://niwe.res.in/static/pdf/NIWE-AAP_Internship_Programme.pdf) |
| 7 | **Vayumitra Skill Development Programme** (MNRE/NIWE) | Trainers and participants; possibly technician-level | Ask trainers whether they know technicians willing to speak about past jobs. Contact route **UNVERIFIED**. | Unknown | [vsdp.niwe.res.in](https://vsdp.niwe.res.in) |
| 8 | **Named organisations from verified pages** | INOX Green (wind O&M provider in the INOX GFL group; independence UNVERIFIED); KP Group (Gujarat-headquartered renewable company and IBM customer; its Maximo case covers solar and hybrid plants) | Cold email or LinkedIn to O&M or asset-management staff, asking for a 30-minute research conversation | Response rate unknown | [INOX Green](https://www.inoxgreen.com/); [IBM KP Group](https://www.ibm.com/case-studies/kp-group) |
| 9 | **LinkedIn and alumni networks** | Wind O&M engineers, site in-charges, SCADA engineers in Tamil Nadu, Gujarat, Andhra Pradesh and Karnataka | Search by role and region; ask college alumni offices and faculty for introductions | Free; sample bias towards English-speaking, online staff (judgement) | Method only; no source claimed |
| 10 | **Competitor alumni as experts** | Former staff of SCADA or CMS analytics vendors with Indian presence, e.g. ONYX's Bengaluru office | Expert calls on how Indian customers buy | Ask nothing confidential about a former employer | [ONYX locations](https://onyxinsight.com/company/our-locations/) |

### 9.2 Sample quotas (planned)

| Persona | Minimum | Notes |
|---|---|---|
| Technician | 3 | At least one employed by an OEM or O&M provider |
| Planner / site in-charge | 3 | At least one outside Tamil Nadu |
| Reliability / performance engineer | 2 | IPP or O&M provider central team |
| Maintenance manager / O&M head | 3 | Mix of owner and O&M provider |
| Asset manager / owner's representative | 2 | At least one with turbines 15+ years old (policy-eligible by age) |
| IT/OT security | 1 | Any organisation type |
| Buyer / finance | 1 | Any organisation type |
| Expert (certifier, consultant, insurer) | 1-2 | Optional |
| **Total** | **16-17** | Across at least 3 states and at least 5 organisations |

### 9.3 Timeline (planned; nothing started)

| Weeks | Activity | Exit condition |
|---|---|---|
| 0 | Finalise guide; dry-run two mock interviews within the team; set up anonymised note store | Guide reviewed for leading questions |
| 1-4 | **Data-access gate** (9.4): 3-5 conversations with owners, IPPs or O&M providers | Gate passed or failed, and written up |
| 3-8 | Persona interviews to quota (only if the gate passes, or if the team decides to continue knowingly) | Quotas met, or saturation reached |
| 9 | Synthesis: update the assumption register with evidence counts; redraw the workflow map | Written synthesis; go/no-go recommendation |

### 9.4 First gate: data access (from the adversarial review)

- **Pass.** At least one organisation states, in a conversation, that it can lawfully share **at least 3 years of 10-minute SCADA plus a failure or work-order log** for turbines of a stated model. The 3-year bar matches what a SCADA-AI vendor asks for its own backtest ([Turbit backtest](https://www.turbit.com/backtest), vendor). A statement of ability is not an agreement to share; any actual sharing needs a written agreement later.
- **Fail.** In at least 3 of the first 5 conversations, the data is controlled by an OEM or contractor and sharing is contractually barred or refused.
- **On fail:** re-table the runner-up segment, per `research/V_adversarial_review_wind_choice.md` section 7.

### 9.5 Outreach message (template, to be sent only after review)

> "Hello [name], we are a student team at [college] studying how wind-farm maintenance decisions are made in India: how faults are found, planned and recorded. We are not selling anything and will not ask for confidential data. Would you be willing to talk for 30 minutes about a few recent maintenance situations from your own experience? We will share an anonymised summary of what we learn."

Do not mention SentinelLoop, AI or prediction in outreach (judgement, to keep answers unbiased; see 8.1).

---

## 10. Assumption register

Every assumption is **untested**. Priority: H means the segment or product fails if it is false.

| ID | Assumption | Pri. | How to test | Evidence that would falsify it |
|---|---|---|---|---|
| A1 | Owners or IPPs (or an O&M provider willing to work with us) control, and can lawfully share, the 10-minute SCADA and alarm logs. | H | Gate conversations (9.4); questions O3, R4, S1, S2 | In ≥3 of the first 5 conversations the OEM or contractor controls the data and sharing is barred |
| A2 | Most Indian 1.5-2.3 MW turbines in the target states are **geared**. | H | Ask respondents which models they run (C1, R4). Check NIWE's §11 database or the ALMM list if accessible. | The majority of named models in that band are direct-drive |
| A3 | Alarm handling and remote resets are visible to the owner or O&M team, not only to the OEM. | M | C2, T1, M5 | Respondents cannot describe alarm handling because the OEM does it unseen |
| A4 | At least 3 years of 10-minute SCADA history is retained per turbine. | H | R4 | Typical retention is under 3 years, or only aggregated daily data survive |
| A5 | Someone ranks turbines or jobs for attention at least weekly, and the ranking is contested. | H | P1, P4, M6 | Work is purely reactive or OEM-scheduled, with no local ranking decision |
| A6 | Major-component work is limited by crane, crew or parts availability, so early notice changes plans. | H | P3, P4 | Lifting and parts are readily available, or lead time is set by the OEM regardless of notice |
| A7 | Teams receive more alarms or alerts than they act on, and ignore some. | M | T5, M5, R6 | Respondents act on all alerts and report no backlog |
| A8 | Unproductive climbs or site visits are common enough to cost something respondents can estimate. | M | T3, R6, M2 | Wasted climbs are rare or negligible in cost |
| A9 | Owners and O&M providers or OEMs disagree about availability or performance figures, and evidence would matter. | M | M4, O4 | No such disagreements in the past 12 months |
| A10 | Life-extension assessors under UL 4143 ask for SCADA or condition history. | L | X1, X2, O2 | Assessors rely only on inspection and design documents |
| A11 | Owners of older (policy-eligible) turbines still spend on condition-driven repairs rather than only planning repowering. | M | O1, O2, F3 | Older turbines get minimal spend pending repowering |
| A12 | Work orders exist in a digital form (CMMS or spreadsheet) that could take or give records. | M | C4, T4, P1 | Records are mainly paper or messaging only |
| A13 | A buyer with budget authority exists in an owner/IPP or an O&M provider, and can fund a small paid pilot. | H | M3, F1, F4, F5 | No respondent can name a past purchase of an analysis tool or service, or every purchase goes through the OEM |
| A14 | Respondents do not already use a SCADA-AI or CMS service that covers the same need. | H | R1, M5 | Most respondents already use ONYX, Turbit, OEM analytics or similar and report the need as met |
| A15 | Close-out records name the component and date well enough to reconstruct events. | M | T4, R2, R3 | Records lack the component or date in most cases |
| A16 | Technicians arrive with little diagnostic information, and diagnosis is a large share of job time. | M | T1, T2 | Technicians report good pre-arrival diagnosis from OEM tools |
| A17 | Weather windows or grid/DISCOM coordination constrain when work can be done. | H (raised from L at the request of review finding om_manager-13: these constraints decide when work can be done and what downtime costs, so G1 must collect them) | P6, P2, P7 | Respondents report no such constraint |
| A18 | Multi-owner (aggregation) sites complicate maintenance decisions. | L | O1, M3 | Single-owner sites dominate, or there is no coordination issue |
| A19 | IT/OT security would accept an offline, read-only copy of exported files for analysis. | H | S1-S3 | Any data leaving the site is refused, or only OEM channels are allowed |
| A20 | The seven generic personas map onto real, distinct wind O&M roles in India. | M | C1 in all interviews | Roles are merged (one site in-charge does everything) or absent (no reliability engineer) |
| A21 | Respondents can attach a cost to a prevented major-component failure. | M | M2, F2 | No respondent tracks or can estimate failure cost |
| A22 | Tamil Nadu is a workable place to start recruiting, even though it is third in the 1.5-2 MW band. | L | Response rates by channel (section 9) | Fewer than 3 Tamil Nadu respondents after 4 weeks while other states respond |
| A23 | Where turbines are curtailed or derated on grid or DISCOM instruction, the site keeps a record that can be exported with the SCADA history: setpoints, instruction logs or status codes. Without one, the product sees curtailed periods only as idle, out-of-scope time or as changed load-temperature behaviour (`KNOWN_LIMITATIONS.md` M3; section 4.2). | H | P8, R7, S2 | Curtailment is frequent, and no record of it exists outside the turbine controller or the grid operator |
| A24 | Major maintenance is planned by season (into low-wind months, away from high-generation months), so what a flag is worth depends on the time of year. The product's own assessability also falls in low-wind periods (section 4.2). If this holds, downtime cost needs seasonal values (one figure per server deployment today, from one decision file per `serve`, with no seasonal variation; PD-24), and the pilot's months must be agreed with the partner (`PILOT_PROTOCOL.md`). | M | P7, M7, P6 | Respondents plan major work without regard to season, and value downtime the same all year |
| A25 | O&M or OEM contracts carry turbine availability guarantees, penalties or bonuses that shape when maintenance is done and who decides it, so evidence about turbine condition matters in contract discussions. | M | M8, M4, O3 | Respondents' contracts carry no availability terms, or the terms have never been applied and do not affect maintenance planning |

**Decision rule after synthesis (pre-registered):**
- **Proceed** with the wind segment only if A1, A13 and A19 are supported by at least one organisation each, and A5 or A6 is supported by at least 3 respondents.
- **Re-scope** if A14 shows the need is already met for most respondents.
- **Switch** if the 9.4 gate fails.

---

## 11. Evidence gaps

1. **Who controls data and work orders** in Indian wind O&M (owner, OEM or independent provider). Not found in any source (A1, A3).
2. **Indian fleet composition:** model mix, geared versus direct-drive share and age in the 1.5-2.3 MW band. MNRE gives capacity by rating band only ([MNRE policy](https://cdnbbsr.s3waas.gov.in/s3716e1b8c6cd17b771da77391355749f3/uploads/2023/12/202312131874296229.pdf)).
3. **Wind-specific O&M workflow in India:** CMMS use, job-card format, remote-reset practice, crane logistics, weather windows. No source opened. Every wind workflow detail in section 4 beyond the cited items is an assumption.
4. **Failure rates and cost per drivetrain or transformer event** on Indian turbines. Not found. The reliability databases we tried (NREL: DNS failure; IEA Wind Task 33 page: 404) could not be opened.
5. **SCADA condition-monitoring reviews** (IET, MDPI and Loughborough copies) returned 403, so the state of the art in SCADA-based wind condition monitoring rests on vendor pages and the CARE paper only.
6. **Labelled public data matching the target fleet:** the rated power and drivetrain type of CARE Farm A are not stated ([Zenodo](https://zenodo.org/records/15846963); [arXiv](https://arxiv.org/html/2404.10320v2)). EDP's primary licence terms returned 403 to the reviewer (via AR).
7. **Whether UL 4143 assessments use SCADA history:** the published scope does not say ([UL 4143 page](https://www.shopulstandards.com/ProductDetail.aspx?productId=UL4143)).
8. **Finance sign-off and required payback** for PdM purchases: no verified source (R2).
9. **Final status of the CEA power-sector cyber-security regulations:** the draft only was seen (via R2).
10. **Indian competitor penetration:** which Indian owners already use ONYX, Turbit, OEM analytics or IBM Maximo Renewables for wind. Only vendor pages were seen; no customer lists for India.
11. **State repowering policies** (e.g. a Tamil Nadu-specific policy): not checked. WebSearch was unavailable.
12. **Next Windergy India dates and visitor terms:** UNVERIFIED.
13. **Vayumitra contact route and trainee profile:** the page did not show the numbers or roles in detail ([vsdp.niwe.res.in](https://vsdp.niwe.res.in)).
14. **Technician certification norms in India** (e.g. GWO training): the GWO standards page returned 404.
15. **IWPA membership composition:** not stated on the home page ([windpro.org](https://www.windpro.org/)).
16. **DPDP applicability details** to research interviews: legal review not done. The MeitY page returned 403 in this session.
17. **WebSearch was unavailable** for the whole session, so no broad search for Indian wind O&M studies, surveys or theses was possible. A follow-up search pass is needed before this plan is finalised.
18. **Curtailment, seasonal planning and contract availability terms in India:**
    - how often turbines are curtailed or derated, and whether a record of it can be exported;
    - how the season shapes maintenance planning and the value of downtime;
    - what availability guarantees or penalties O&M and OEM contracts carry, and whether they shape maintenance.

    No source opened (A17, A23, A24, A25). Added after the adversarial review (om_manager-13). The monsoon framing in P-P7 is the reviewer's outside knowledge, not a source.

---

## 12. Sources

All accessed **2026-10-18**.

### 12.1 Opened by the writer in this session (WebFetch)

1. US Bureau of Labor Statistics, Occupational Outlook Handbook, Wind Turbine Technicians (government). https://www.bls.gov/ooh/installation-maintenance-and-repair/wind-turbine-technicians.htm
2. MNRE, National Repowering & Life Extension Policy for Wind Power Projects 2023 (government; scanned PDF read page by page from WebFetch's saved copy). https://cdnbbsr.s3waas.gov.in/s3716e1b8c6cd17b771da77391355749f3/uploads/2023/12/202312131874296229.pdf
3. NIWE, Academic Associate Programme notice (government institute; PDF read from WebFetch's saved copy). https://niwe.res.in/static/pdf/NIWE-AAP_Internship_Programme.pdf
4. NIWE home page (government institute). https://niwe.res.in/
5. NIWE, 31st National Training Course on Wind Energy Technology (government institute). https://niwe.res.in/national-training/NTC-31/
6. NIWE / MNRE, Vayumitra Skill Development Programme (government). https://vsdp.niwe.res.in
7. Zenodo, CARE To Compare v6, Fraunhofer IEE (dataset landing page; real field data; CC BY-SA 4.0). https://zenodo.org/records/15846963
8. Gück, Roelofs et al., CARE to Compare paper v2 (arXiv preprint). https://arxiv.org/html/2404.10320v2
9. Zenodo, Hill of Towie wind farm open dataset v2.1.0 (dataset landing page; real field data; CC BY 4.0). https://zenodo.org/records/22662930
10. IEA Wind, EDP OpenData Details (secondary summary of a real field dataset; PDF read from WebFetch's saved copy). https://iea-wind.org/wp-content/uploads/2024/07/EDP-OpenData-Details.pdf
11. UL Standards, UL 4143 product page (standards body; scope only). https://www.shopulstandards.com/ProductDetail.aspx?productId=UL4143
12. May & McMillan 2013, Strathprints record (peer-reviewed conference; abstract). https://strathprints.strath.ac.uk/54903/
13. Indian Wind Power Association (industry association). https://www.windpro.org/
14. Indian Wind Energy Association (industry association). https://www.inwea.org/
15. Indian Wind Turbine Manufacturers Association (industry association). https://www.indianwindpower.com/
16. Windergy India 2026 (trade fair). https://www.windergy.in/
17. INOX Green home page (vendor claims). https://www.inoxgreen.com/
18. ONYX Insight home page (vendor claims). https://www.onyxinsight.com/
19. ONYX Insight office locations (vendor). https://onyxinsight.com/company/our-locations/
20. Turbit home page (vendor claims). https://www.turbit.com/
21. Turbit backtest page (vendor). https://www.turbit.com/backtest
22. IBM Maximo Renewables (vendor). https://www.ibm.com/products/maximo/renewables
23. IBM case study, KP Group (vendor). https://www.ibm.com/case-studies/kp-group
24. Clir home page (vendor). https://www.clir.eco/
25. A. Schade, "Avoid Leading Questions to Get Better Insights from Participants", Nielsen Norman Group, 17 Dec 2017 (practitioner). https://www.nngroup.com/articles/leading-questions/
26. R. Fitzpatrick, The Mom Test, book home page (practitioner). https://www.momtestbook.com/

**Attempted, not usable** (no claims rest on these):
- https://www.meity.gov.in/data-protection-framework (403)
- https://ietresearch.onlinelibrary.wiley.com/doi/10.1049/iet-rpg.2016.0248 (403)
- https://www.mdpi.com/1996-1073/12/2/201 (403)
- https://repository.lboro.ac.uk/articles/journal_contribution/Using_SCADA_data_for_wind_turbine_condition_monitoring_a_review/9227969 (403)
- https://www.nrel.gov/docs/fy13osti/59111.pdf (DNS failure)
- https://www.globalwindsafety.org/standards (404)
- https://iea-wind.org/task-33/ (404)
- WebSearch: one call, refused because the per-turn budget was exhausted.

### 12.2 Cited from team research files (opened by those researchers on 2026-10-18; not re-opened by the writer)

**From R1** (`research/R1_maintenance_workflows.md`)
- https://pemac.org/sites/default/files/2018_SMRP_BPMW_Full_Day.pdf
- https://www.ibm.com/support/pages/node/1112013
- https://papers.phmsociety.org/index.php/phmconf/article/download/836/phmc_19_836
- https://papers.phmsociety.org/index.php/phmconf/article/download/790/phmc_19_790
- https://www.emerald.com/insight/content/doi/10.1108/JQME-04-2015-0013/full/html
- https://reliabilityweb.com/en/articles/ranking-index-for-maintenance-expenditures
- https://reliabilityweb.com/articles/entry/priority_vs_criticality
- https://reliabilityweb.com/articles/entry/work_prioritization_emotion_vs._logic
- https://accendoreliability.com/review-maintenance-planning-scheduling-handbook-doc-palmer/
- https://www.assetivity.com.au/articles/asset-management/coordinating-activity-between-maintenance-and-supply-a-case-study/
- https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-82r3.pdf
- https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.147
- https://www.hse.gov.uk/pubns/books/hsg250.htm
- https://static.pib.gov.in/WriteReadData/specificdocs/documents/2025/nov/doc20251122702801.pdf

**From R2** (`research/R2_pdm_adoption_failures.md`)
- https://link.springer.com/article/10.1007/s41471-024-00204-3
- https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2019.00519/full
- https://ideas.repec.org/a/spr/infsem/v16y2018i3d10.1007_s10257-017-0343-1.html
- https://papers.phmsociety.org/index.php/ijphm/article/download/2933/1736
- https://www.bain.com/insights/selling-iot-solutions-to-experts/
- https://www.bain.com/about/media-center/press-releases/2018/bain-predicts-the-iot-market-will-more-than-double-by-2021/
- https://www3.weforum.org/docs/WEF_4IR_Beacons_of_Technology_and_Innovation_in_Manufacturing_report_2019.pdf?lng=en
- https://blog.lnsresearch.com/pilot-purgatory-in-industrial-transformation-is-fake-news
- https://karriere.mckinsey.de/~/media/mckinsey/business%20functions/operations/our%20insights/how%20digital%20manufacturing%20can%20escape%20pilot%20purgatory/digital-manufacturing-escaping-pilot-purgatory.pdf
- https://www.deloitte.com/us/en/insights/industry/manufacturing-industrial-products/industry-4-0/using-predictive-technologies-for-asset-maintenance.html
- https://pmc.ncbi.nlm.nih.gov/articles/PMC9890517/
- https://agris.fao.org/search/fr/records/669f707f00eb85b7d72cf732
- https://catalog.data.gov/dataset/simulating-degradation-data-for-prognostic-algorithm-development
- https://minds.wisc.edu/handle/1793/85271
- https://www.emerald.com/insight/content/doi/10.1108/TQM-06-2021-0179/full/html
- https://www.ic3.gov/CSA/2025/250113.pdf
- https://www.isa.org/62443
- https://indianinfrastructure.com/2024/08/21/cea-notifies-draft-cea-cyber-security-in-power-sector-regulations-2024/
- https://www.startupindia.gov.in/content/sih/en/public_procurement.html
- https://www.tatasteeluk.com/suppliers/ariba
- https://assets.new.siemens.com/siemens/assets/api/uuid:5803c43a-d25f-4b59-871c-ccfd43067abb/Automotivev2_original.pdf
- https://www.abiresearch.com/market-research/insight/7780896-siemens-snaps-up-senseye-to-expand-its-pre?hsLang=en

**From R3** (`research/R3_competitive_landscape.md`)
- https://www.advancedtech.com/wp-content/uploads/2020/03/2020-ATS_Plant-Engineering-Maintenance-Study-Results.pdf
- https://www.rolls-royce.com/products-and-services/civil-aerospace/services/totalcare.aspx
- https://www.ibm.com/docs/en/SSRHPA_cd/appsuite/overview/c_technical_overview.html
- https://www.siemens.com/us/en/products/services/digital-enterprise-services/analytics-artificial-intelligence-services/predictive-services/senseye-predictive-maintenance/how-it-works.html
- https://gevernova.com/software/sites/default/files/2024-10/brochure-ai-powered-predictive-analytics-smartsignal.pdf
- https://www.aveva.com/en/products/predictive-analytics/
- https://aws.amazon.com/about-aws/whats-new/2025/09/aws-iot-sitewise-retraining-anomaly-detection-models
- https://aws.amazon.com/blogs/machine-learning/preserve-access-and-explore-alternatives-for-amazon-lookout-for-equipment/
- https://us.promo.skf.com/acton/media/22336/connected-technologies-services

**From R5** (`research/R5_integration_standards.md`)
- https://prsindia.org/files/bills_acts/bills_parliament/2023/Digital_Personal_Data_Protection_Act,_2023.pdf
- https://www.meity.gov.in/static/uploads/2025/11/53450e6e5dc0bfa85ebd78686cadad39.pdf
- https://www.cert-in.org.in/PDF/CERT-In_Directions_70B_28.04.2022.pdf

**Local team files read** (not web sources):
- `product/research/R1_maintenance_workflows.md`
- `product/research/R2_pdm_adoption_failures.md`
- `product/research/R3_competitive_landscape.md`
- `product/research/R5_integration_standards.md` (DPDP section)
- `product/research/V_judge_decision.md`
- `product/research/V_adversarial_review_wind_choice.md`
- `product/research/proposals/V_data_first.md` (searched)

**Local computations** (Python, 2026-10-18) from the MNRE table and the IEA EDP summary:
- band shares;
- state shares of the 1.5-2 MW band;
- EDP operation-log records per turbine-day (256,231 / (5 × 609 days) ≈ 84);
- the INOX Green share of 59.20 GW.

### 12.3 Fact-check log (2026-10-18)

**Method.** An independent fact-checker re-opened cited URLs with WebFetch on 2026-10-18 and compared each page with the claims it supports. Scanned or binary PDFs were read from WebFetch's saved copies. WebSearch was unavailable: the shared per-turn search budget was already used up. No interviews, customers, pilots or results are claimed anywhere in this document, and the status banner (section 1) is accurate. (Later update: section 4.2 now cites results on SYNTHETIC wind data from the product's own generator. They are labelled SYNTHETIC; no interview, customer, pilot or real-data result is claimed.)

**Re-opened and consistent with the claims (after the corrections below).** All accessed 2026-10-18.
- IWTMA, 59.20 GW as of Sept 2026; "Members" logos; New Delhi address: https://www.indianwindpower.com/
- INOX Green, >13 GW, 11 GW wind, 12 states, 2000+ team, Predictive Maintenance, DISCOM coordination: https://www.inoxgreen.com/
- ONYX Insight, 32,000+ turbines, up to 24 months, 15 CMS hardware types: https://www.onyxinsight.com/
- ONYX Bengaluru office: https://onyxinsight.com/company/our-locations/
- Turbit, 3500+ turbines, 40+ customers, insurance integration, no India mention: https://www.turbit.com/
- Turbit backtest, one-time fee, minimum 3 years and 5+ ideal, main bearing, gearbox and generator events: https://www.turbit.com/backtest
- CARE v6, 45 anomaly and 50 normal datasets, CC BY-SA 4.0, no rated power stated: https://zenodo.org/records/15846963
- CARE paper v2, Farm A with 5 turbines, 11 anomaly and 11 normal datasets; unclear anomaly starts; data released only for its own research: https://arxiv.org/html/2404.10320v2
- Hill of Towie v2.1.0, CC BY 4.0, alarm logs, downtime from SCADA plus RES operator logs: https://zenodo.org/records/22662930
- IEA Wind EDP summary, 256,231 log records for 2016-01-01 to 2017-08-31; 23-record failure log for 2016-03-03 to 2017-08-21: https://iea-wind.org/wp-content/uploads/2024/07/EDP-OpenData-Details.pdf
- MNRE policy 2023 (scanned): clause 5; 25.406 GW; state table; UL 4143; 40-year cap; aggregation projects; DPR; DISCOM consent; Annex O&M default of 2% escalated at 5%; §11 NIWE database: https://cdnbbsr.s3waas.gov.in/s3716e1b8c6cd17b771da77391355749f3/uploads/2023/12/202312131874296229.pdf
- NIWE AAP notice: https://niwe.res.in/static/pdf/NIWE-AAP_Internship_Programme.pdf
- NIWE home: https://niwe.res.in/
- NIWE NTC-31, 3-5 Feb 2027, register by 22 Jan 2027, Rs 5,900 and Rs 17,700, 50 participants: https://niwe.res.in/national-training/NTC-31/
- Vayumitra: https://vsdp.niwe.res.in
- Windergy India 2026, 7-9 Oct 2026, Chennai Trade Centre, IWTMA and PDA Ventures: https://www.windergy.in/
- InWEA, 350+ members, three regional repowering webinars in May 2021: https://www.inwea.org/
- IWPA, Chennai address: https://www.windpro.org/
- IBM KP Group: https://www.ibm.com/case-studies/kp-group
- IBM Maximo Renewables: https://www.ibm.com/products/maximo/renewables
- IBM Maximo work-order statuses: https://www.ibm.com/support/pages/node/1112013
- Clir: https://www.clir.eco/
- UL 4143 scope: https://www.shopulstandards.com/ProductDetail.aspx?productId=UL4143
- BLS wind turbine technicians: https://www.bls.gov/ooh/installation-maintenance-and-repair/wind-turbine-technicians.htm
- NN/g leading questions, Amy Schade, 17 Dec 2017: https://www.nngroup.com/articles/leading-questions/
- The Mom Test home page: https://www.momtestbook.com/
- May & McMillan 2013 (abstract): https://strathprints.strath.ac.uk/54903/
- Sexton, Hodkiewicz & Brundage 2019, Kegg 1984 citation and "miscellaneous" codes: https://papers.phmsociety.org/index.php/phmconf/article/download/790/phmc_19_790
- Wiczorek & Meyer 2019: https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2019.00519/full
- Thomas & Weiss 2021, 71 usable responses: https://pmc.ncbi.nlm.nih.gov/articles/PMC9890517/
- Plant Engineering 2020, n=171; CMMS 50%, spreadsheets 47%, paper 46%; preventive 76%, run-to-failure 60%: https://www.advancedtech.com/wp-content/uploads/2020/03/2020-ATS_Plant-Engineering-Maintenance-Study-Results.pdf
- Bain 2021, 85% OT: https://www.bain.com/insights/selling-iot-solutions-to-experts/
- Bain 2018: https://www.bain.com/about/media-center/press-releases/2018/bain-predicts-the-iot-market-will-more-than-double-by-2021/
- WEF 2019, >70% in pilot purgatory; value/ROI alignment and cost to scale: https://www3.weforum.org/docs/WEF_4IR_Beacons_of_Technology_and_Innovation_in_Manufacturing_report_2019.pdf?lng=en
- LNS 2021, 7%: https://blog.lnsresearch.com/pilot-purgatory-in-industrial-transformation-is-fake-news
- Deloitte 2017, pilot on one or two well-suited assets: https://www.deloitte.com/us/en/insights/industry/manufacturing-industrial-products/industry-4-0/using-predictive-technologies-for-asset-maintenance.html
- CISA Secure by Demand, 13 Jan 2025, 12 elements, 11 partners: https://www.ic3.gov/CSA/2025/250113.pdf
- CERT-In Directions, 6 hours, 180 days, SCADA/OT listed: https://www.cert-in.org.in/PDF/CERT-In_Directions_70B_28.04.2022.pdf
- CEA draft cyber-security regulations, 21 Aug 2024: https://indianinfrastructure.com/2024/08/21/cea-notifies-draft-cea-cyber-security-in-power-sector-regulations-2024/
- Startup India GFR relaxations, central buyers only: https://www.startupindia.gov.in/content/sih/en/public_procurement.html
- Tata Steel UK Ariba, vendor qualification by invitation: https://www.tatasteeluk.com/suppliers/ariba
- ABI Research, Senseye ROI Lock: https://www.abiresearch.com/market-research/insight/7780896-siemens-snaps-up-senseye-to-expand-its-pre?hsLang=en
- Rolls-Royce TotalCare: https://www.rolls-royce.com/products-and-services/civil-aerospace/services/totalcare.aspx
- AWS Lookout for Equipment, discontinued 7 Oct 2026: https://aws.amazon.com/blogs/machine-learning/preserve-access-and-explore-alternatives-for-amazon-lookout-for-equipment/
- AWS IoT SiteWise retraining, 10 Sept 2025: https://aws.amazon.com/about-aws/whats-new/2025/09/aws-iot-sitewise-retraining-anomaly-detection-models
- NASA data.gov C-MAPSS degradation data: https://catalog.data.gov/dataset/simulating-degradation-data-for-prognostic-algorithm-development

**Could not be opened by the fact-checker** (claims stay as cited, with provenance via R2 or R5):
- https://link.springer.com/article/10.1007/s41471-024-00204-3 (Hoffmann & Lasch 2025): redirected to a Springer login.
- https://www.meity.gov.in/static/uploads/2025/11/53450e6e5dc0bfa85ebd78686cadad39.pdf (DPDP Rules 2025): 403. The date claim in 8.6 is now marked UNVERIFIED.

**Not re-opened** (still rest on R1, R2, R3 or R5 alone): SMRP 2018, Lukens et al. 2019, Hodkiewicz & Ho 2016, Reliabilityweb pages, Accendo/Palmer, Assetivity, NIST SP 800-82r3, OSHA 1910.147, HSE HSG250, PIB OSH Code factsheet, Golightly et al. 2018, Wagner & Hellingrath 2021, McKinsey 2018, van Dinter et al., Pedraza 2024, Goswami & Daultani 2022, ISA 62443, Siemens Senseye case and how-it-works pages, GE Vernova SmartSignal, AVEVA, IBM OpenShift docs, SKF, DPDP Act (PRS).

**Corrections made**
1. INOX Green was called an "independent" O&M provider in 2.2, 5, 6 and 9.1. Its page carries the INOX GFL group logo and does not call itself independent. The label was removed and the independence marked UNVERIFIED. The inference that "independent O&M providers control a large share of maintenance" was withdrawn.
2. MNRE eligibility (2.1): the judgement said a 2.05-2.3 MW turbine qualifies only through age (iv) or design life (ii). Clause 5 also allows (i), non-compliance with the quality control order, and a note covers turbines replaced early because of malfunction. Corrected.
3. The MNRE Annex valuation is an *indicative* method in the aggregation-project context; this was added in 2.1 and A-P1. The life-extension standard is UL 4143 "or any such standards issued by the BIS"; added.
4. NIWE AAP: the intern agreement (Annexure III) also bars publishing reports or papers using information obtained during the internship. Added in 2.1 and 9.1. The NIWE guide must be *second* co-author.
5. CARE status logging (R-P1): the "logged only when it changes" remark applies to Farms B and C (offshore Germany). Scope added.
6. May & McMillan (R-P6): the abstract says false-alarm costs "may alter the cost benefit" of condition monitoring. "Erode the case" was softened to match, and the source was labelled abstract-only.
7. Wiczorek & Meyer (T-P6, 7.1): the "cry wolf" effect is in the paper's background, not its experiment, which did not vary the false-alarm rate. Labelled.
8. Bain 2018 (M-P2) covers IoT in general and names uncertain ROI as a barrier. It does not say benefits are medium- to long-term, which rests on Hoffmann & Lasch via R2. Attribution split.
9. Thomas & Weiss (F-P2): "most figures are self-reported or vendor-extrapolated" and "only government-sourced estimate" are R2's synthesis, not statements in the paper. Re-attributed. The 71 usable of 85 responses and the associational design were confirmed.
10. "Large vendors have exited this space" (5) rested on two AWS products. It was reworded to one vendor's withdrawals.
11. KP Group was called an "IPP" and evidence that "Indian IPPs" buy APM. The IBM page says Gujarat-headquartered and active in solar, wind, hybrid and green hydrogen, with the Maximo case covering solar and hybrid plants. Reworded to "renewable company" and "at least one".
12. IWTMA members (9.1): Nordex is not named in text on the page; its logo has the alt text "NGC". It was replaced with GE Vernova, which is named.
13. IWPA (9.1): "wind power producers" is not stated on the page. Marked as inferred from the name and UNVERIFIED.
14. EDP summary (4.1, stage 0): it describes an *operation* log, not an alarm log, and does not name Portugal. Split the citation; Portugal is sourced to the CARE Zenodo page.
15. UL 4143 scope (A-P2): the page does not use the words "risk-based". Reworded to the page's own description.
16. NASA C-MAPSS (7.1): the data.gov page says simulated degradation *data* were generated because validation data are scarce. It does not say C-MAPSS itself was built for that reason. Reworded.
17. Plant Engineering 2020 (3.2): the sponsor is named as ATS, the "maintenance-services firm" description was removed, and the sample was noted as manufacturing facilities with 22% of respondents outside the US.
18. DPDP Rules date (8.6): marked UNVERIFIED because the source was blocked to the fact-checker.
