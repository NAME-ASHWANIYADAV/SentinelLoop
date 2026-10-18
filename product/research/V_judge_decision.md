# Initial vertical and asset class: judge's decision

Written 2026-10-18 for the SentinelLoop product team. Role: judge of three independent proposals (DATA-FIRST, ACCESS-FIRST, DECISION-VALUE-FIRST) for the first (vertical, asset class) pair.

**Tool status.** WebSearch was unavailable: the first call returned "this turn's web search budget is used up" (shared 200-call per-turn limit), so I ran no searches. WebFetch worked, and I used it only on primary URLs named in the proposals or known in advance. Five PDFs came back as binary through WebFetch, so I extracted them locally:
- pdftotext for the CIRT STU profile, the NIWE internship notice, the India Cooling Action Plan and the IEA Wind EDP summary.
- The MNRE repowering policy is a scanned image. I rendered its pages to PNG and read them directly, so the table values below come from the scanned page itself.

**Labels.**
- **Verified (judge)**: I opened the source in this session and it says what is written.
- **UNVERIFIED**: I did not confirm it in this session, including claims carried over from a proposal that I did not re-open.
- **Vendor claim**: a statement from a vendor's own page.
- **Judgement**: my reasoning, not a sourced fact.

**Data types** follow R4: real field, real laboratory, simulated, synthetic. I add *real field administrative statistics* for aggregate figures that operators self-report.

---

## 1. Verdict

**Chosen: the DATA-FIRST proposal (wind), narrowed and strengthened with elements from the other two.**

| | |
|---|---|
| **Vertical** | Indian onshore wind-farm owner-operators of ageing turbines that are eligible for repowering or life extension under MNRE's National Repowering & Life Extension Policy 2023. Start in Tamil Nadu, using NIWE (Chennai) as the institutional door. |
| **Asset class** | Geared onshore wind turbines in the roughly 1.5-2.3 MW class, monitored only through the 10-minute SCADA and alarm/event logs they already record (no new hardware). Targets are faults visible in SCADA: the drivetrain (gearbox and its bearings, generator) and the transformer. |
| **Runner-up** | DECISION-VALUE-FIRST: Indian State Transport Undertaking depots, diesel-bus powertrain aggregates (engine, FI pump, gearbox). |
| **Primary validation dataset** | CARE to Compare v6 (Fraunhofer IEE, Zenodo 15846963), real field, CC BY-SA 4.0. Supported by EDP Wind Farm 1, Hill of Towie, Kelmarsh and Penmanshiel (all real field). |

**The decision is close, and it depends on how the criteria are weighted.**
- On an unweighted sum, wind and buses tie at 19/30 and chillers score 17/30 (section 2).
- I break the tie on two criteria: availability of real labelled data in the same asset class, and technical fit. With no customer access, the team's next 3-6 months can only produce evidence on public data, and the product's stated weakness is that it "has only ever seen simulated C-MAPSS data" (README.md).
- Wind is the only option where public real field data come in the same asset class and the same data form (10-minute SCADA) that a first Indian customer would export.
- The bus option's public data are trucks (SCANIA Component X), in a different data form (anonymised histograms and counters) from what an STU depot would hand over (job cards and registers).

**Narrowing from 2 MW to 1.5-2.3 MW (my addition).**
- The public onshore data cover machines of about 2.05-2.3 MW (Kelmarsh MM92, Penmanshiel MM82, Hill of Towie SWT-2.3-VS-82).
- MNRE's own table makes 1.5-2 MW the largest sub-2 MW band nationally: 9,065.35 MW of a 25,396.65 MW table total, about 35.7% (computed). Verified (judge), scanned policy pp.1-2.
- Targeting this band keeps the domain shift smaller than targeting the sub-MW pre-2000 fleet.
- Whether Indian 1.5-2 MW machines are geared, and which models dominate, is **UNVERIFIED**.

---

## 2. Scores (1-5; competition 5 = least crowded; regulation 5 = lightest)

| Option | Data | Access | Decision value | Technical fit | Competition | Regulatory | Sum |
|---|---|---|---|---|---|---|---|
| **A. DATA-FIRST: Indian onshore wind owner-operators / geared ~2 MW turbines via SCADA** | **4** | **2** | **4** | **4** | **2** | **3** | **19** |
| B. ACCESS-FIRST: Indian campuses / water-cooled central chilled-water plants | 1 | 4 | 2 | 2 | 3 | 5 | 17 |
| C. DECISION-VALUE-FIRST: Indian STU depots / diesel-bus powertrain aggregates | 3 | 2 | 4 | 3 | 4 | 3 | 19 |

### Why each score

**A. Wind (DATA-FIRST)**

- **Data 4.** Several independent real field datasets with fault labels exist under licences that allow commercial use (all verified, judge):
  - CARE to Compare: 36 turbines, 3 farms, 95 datasets; 45 fault-leading events and 50 normal datasets on the Zenodo v6 page; CC BY-SA 4.0.
  - EDP Wind Farm 1: failure logbook of 23 records with Turbine_ID, Component, Timestamp and Remarks; CC-BY-SA. This comes from the IEA Wind secondary summary.
  - Hill of Towie, Kelmarsh and Penmanshiel: CC BY 4.0, with alarm or events logs and downtime.

  It is not a 5, for three reasons:
  - Only 44-45 labelled events, and they are anomaly events, not RUL or work orders.
  - Share-alike on CARE and EDP.
  - The CC BY sets carry no curated failure list.
- **Access 2.** The public-data ladder needs no access, but a shadow pilot needs an Indian owner's SCADA export.
  - Whether owners rather than OEM or O&M contractors control those exports is **UNVERIFIED**.
  - One real institutional door was verified: NIWE's Academic Associate Programme (Chennai). It is unpaid, runs 2 weeks to 6 months, is open to UG/PG students with at least 60%, and lists "Machine Learning /AI and data analysis" as domain 7.
  - The MNRE policy (§11) tasks NIWE with collecting "performance related data for all the sites" to identify poor-performing sites for repowering.
  - Whether NIWE holds or would share turbine-level SCADA is **UNVERIFIED**.
- **Decision value 4.** Drivetrain and transformer faults are high-consequence, and the policy creates a documented assessment decision. Life extension requires assessment "as per the UL 4143" standard, and total life cannot "exceed 40 years" (verified, judge, policy p.3).
  - It is not a 5: the per-event cost is **UNVERIFIED**, and the owner may not control maintenance under OEM full-service contracts (**UNVERIFIED**).
- **Technical fit 4.** Multivariate 10-minute trajectories across fleets of identical turbines suit the healthy-baseline index (D10), regime normalisation (D14), drift monitoring and gated retraining.
  - RUL with intervals does not transfer: turbines are repaired, not run to failure, and 44-45 events cannot validate RUL. Conformal calibration therefore shifts to alarm thresholds (judgement).
- **Competition 2.** The field is crowded (vendor claims, verified pages):
  - ONYX Insight: "32,000+" turbines monitored, CMS hardware.
  - Turbit: "more than 3,500 turbines", and offers a "Request a backtest" route.
  - INOX Green: "11 GW of Wind O&M assets" and lists "Predictive Maintenance" as a service.

  India-specific density of third-party SCADA analytics is **UNVERIFIED**, since WebSearch was unavailable.
- **Regulatory 3.** These are power-generation assets. CEA's power-sector cyber regulations were draft per R2/R5, and their final status is **UNVERIFIED**. Offline, read-only back-tests avoid OT connections (judgement).

**B. Chillers (ACCESS-FIRST)**

- **Data 1.** No public real field chiller dataset with fault or maintenance labels was verified.
  - Building Data Genome 2 is real field meter data with no condition labels, under "Attribution-ShareAlike 4.0 Unported" (verified).
  - The LBNL/DOE FDD page states neither data origin nor licence and does not mention chillers (verified).
- **Access 4.** This is the only option with a door the team plausibly holds already: its own estate department. It is not a 5 because the campus may have no central chilled-water plant.
  - ICAP (verified) names chillers as preferred for "hotels, hospitals, malls, office complexes and airports", not campuses.
  - ICAP gives room ACs about 80% of installed refrigerant-based capacity.
- **Decision value 2.** The case is comfort cooling with 2-4 chillers per plant, so there is little to prioritise between. ICAP frames the value mainly as energy efficiency (judgement).
- **Technical fit 2.** Hourly or manual logs on a handful of units give no fleet. The system's fleet logic and conformal calibration lose their statistical base (judgement).
- **Competition 3.** ICAP states "Chiller analytics software platforms are readily available" (verified), and Augury lists "Chillers" (vendor page, verified). The campus estate niche may be underserved (**UNVERIFIED**).
- **Regulatory 5.** It is not a safety function, there is no network connection, and the only personal data are pseudonymisable technician names (judgement, based on R5).

**C. Buses (DECISION-VALUE-FIRST)**

- **Data 3.** SCANIA Component X v3 is real field truck data under CC BY 4.0 with time-to-event files (verified). It is the strongest public per-unit repair-and-censoring set (R4).
  - It is adjacent (trucks, an anonymised component), not buses.
  - No per-bus Indian data are public (**UNVERIFIED**, as the proposal itself states).
  - The CIRT statistics are aggregate and "All rights reserved" (verified).
- **Access 2.** CIRT is a plausible door, but depot records may be on paper, approval sits with public bodies, and data sharing is **UNVERIFIED**.
- **Decision value 4.** The decision is recurring and capacity-constrained. CIRT 2021-22 (verified, judge) reports:
  - 72.4% fleet utilisation;
  - 12,817 buses off-road and 22,983 spare on an average day;
  - 164,139 breakdowns;
  - 80,900 workshop and maintenance staff.

  It is not a 5: the proposal itself reports that maintenance causes are a small share of cancelled km at KSRTC, and CIRT notes STUs are in "severe financial crunch" (verified).
- **Technical fit 3.** The fleet of similar units and the calibrated time-to-event decision fit well. But the depot data are records, not multivariate sensor trajectories, and the system needs censoring-aware models, a km time base and capacity-constrained ranking (proposal's own assessment, judgement).
- **Competition 4.** Uptake offers "Risk Explorer" prioritisation for buses and a planned Bosch acquisition, but its page does not mention India (verified). The Fleet Edge page returned HTTP 403, so its scope is **UNVERIFIED** in this session.
- **Regulatory 3.** Public-sector procurement, DPDP duties for mechanic and driver identities, and union sensitivity (judgement). The tool never touches the vehicle.

### Weighting sensitivity (computed)

| Weighting | Wind | Buses | Chillers | Winner |
|---|---|---|---|---|
| Equal weights | 19 | 19 | 17 | tie A/C |
| Data ×2 and technical fit ×2 (judge's choice) | 27 | 25 | 20 | **A** |
| Access ×2 | 21 | 21 | 21 | three-way tie |
| Decision value ×2 | 23 | 23 | 19 | tie A/C |
| Competition ×2 | 21 | 23 | 20 | C |

**Why I weight data and technical fit double.**
1. Access ties wind and buses at 2, so it cannot separate them.
2. Until a customer appears, every milestone the team can hit is an evidence milestone on public data. That needs labelled data in the same asset class and the same data form, and a pipeline that runs on it without a rewrite.
3. Competitive density matters more at the sales stage than at the evidence stage, but it is a real weakness of the choice and is listed as a switch condition.

If the team believes a customer pilot within 3 months matters more than real-data evidence, the access-weighted result (a three-way tie) favours chillers on speed, but they score lowest on data and decision value.

---

## 3. Verification of the key data claim (DATA-FIRST)

| Claim in proposal | Judge's check | Result |
|---|---|---|
| CARE to Compare: 36 turbines, 3 farms, 95 datasets, CC BY-SA 4.0, direct download | Zenodo record 15846963 opened: title "Wind Turbine SCADA Data For Early Fault Detection" (alt. "CARE To Compare Data"), v6, published 2025-07-09. Creators Christian Gück and Cyriana Roelofs (Fraunhofer IEE). Licence "Creative Commons Attribution Share Alike 4.0 International". One archive, CARE_To_Compare.zip, 5.5 GB, MD5 2547b58c21ac8c242d13232860cf500c, open download. | **Verified** |
| 45 fault-leading events / 50 normal (v6) vs 44 / 51 (paper v2; A=11, B=6, C=27) | The Zenodo page says 45 / 50. arXiv 2404.10320v2 gives 44 / 51 with the A=11, B=6, C=27 split. | **Verified; the discrepancy is real.** Count from the downloaded v6 files before quoting either number. |
| Features 86 / 257 / 957; Farm A onshore Portugal (5 turbines), B and C offshore Germany | Both pages agree. The paper gives 5 / 9 / 22 turbines per farm. | **Verified** |
| Labels: Farm A from the EDP fault logbook; B and C from service reports and operator feedback | The paper says B and C starts come from "data analysis, operator feedback, service reports, and expert knowledge". It warns that Farm A's "true" anomaly starts can differ, that B and C statuses "may be inconsistent", and that missing values were set to 0. | **Verified** |
| Status labelling around Farm A events (14 days before = status 4, 3 days after = status 3) | Stated in the paper. | **Verified.** Status must never be a model input near events. |
| Example events: gearbox bearing damage, transformer high temperature | The Zenodo page names a gearbox bearing damage (event 51, Farm A) and transformer-cell high temperature (events 34, 7, 19). | **Verified** |
| Data are real field | The paper says the data stem "from real-world operating wind farms" (anonymised). | **Verified: REAL FIELD** |
| CARE score benchmark | Weighted Coverage, Accuracy, Reliability and Earliness. Autoencoder 0.66; random 0.5; isolation forest below the 0.5 threshold. | **Verified.** Use these as the bars to beat. |
| Licence permits commercial use | The CC BY-SA 4.0 deed allows adaptation "even commercially". Adaptations must be distributed "under the same license as the original". | **Verified.** Whether trained model weights count as "adapted material" is a legal question: **UNVERIFIED** and needs legal review. |
| EDP logbook: 23 records (Turbine_ID, Component, Timestamp, Remarks), 256,231 operation-log records, sign-in needed, CC-BY-SA | IEA Wind PDF extracted locally: all four points confirmed. 5 turbines; 10-minute signals including drivetrain temperatures. | **Verified (secondary source).** The EDP primary page was not opened. |
| Hill of Towie: 21 Siemens SWT-2.3-VS-82, Jan 2016-Apr 2026, alarm logs, downtime, AeroUp dates, CC BY 4.0, 29.7 GB | Zenodo 22662930, v2.1.0, 2026-09-08 (RES curators). All points confirmed. Downtime is per 10-minute interval to Aug 2024. The page does not describe dedicated failure records. | **Verified.** That the downtime is "derived from operator logs" was not confirmed on the page I read: **UNVERIFIED**. |
| Kelmarsh (6 Senvion MM92, v4) and Penmanshiel (14 Senvion MM82, v3), CC BY 4.0, 2016-2024, 3.8 GB and 7.5 GB | Both Zenodo pages confirm. Neither describes failure labels. | **Verified.** The Kelmarsh 2023-2024 defect audit was not re-opened: **UNVERIFIED**. |
| No public Indian turbine SCADA at NIWE | The NIWE open-data page lists 10 wind-monitoring-station sets, a 150 m atlas and reports; no turbine SCADA. It states no open licence ("© All Rights Reserved"). | **Verified** |
| India wind capacity 59,201.07 MW as on 30.09.2026 | MNRE physical-progress page table. | **Verified** |
| Repowering potential 25.406 GW (turbines below 2 MW); TN 7,386.5 MW; table total 25,396.65 MW; UL 4143; 40-year cap; Aggregation Projects | Scanned policy read page by page. All confirmed (pp.1-3, 4). | **Verified** |
| Wilson half-widths about ±13-14 points (44 events) and about ±24-25 points (11 events) | Recomputed locally: n=44 at 50-70% gives 0.130-0.142; n=11 gives 0.234-0.254. | **Verified (computed)** |
| False alarms reduce the value of condition monitoring | Strathprints 54903: May and McMillan (2013) say chasing or ignoring false alarms "may reduce" the financial advantage of condition monitoring offshore. | **Verified** |

**Judge's correction to the DATA-FIRST proposal.** Its claim that wind is "the only vertical where a cross-site rung can be run on public data" holds, but only partly within the chosen asset class:
- CARE Farms B and C are offshore and anonymised, so the A→B/C transfer is onshore→offshore.
- The in-class cross-site test (onshore ~2 MW → unseen onshore farm) must use EDP/CARE Farm A for training and Kelmarsh, Penmanshiel or Hill of Towie for testing. Those farms have events, alarms and downtime but no curated failure list.
- So the in-class cross-site rung can measure false-alarm rate and alarm/downtime agreement, but not a labelled detection rate.

Report both rungs separately.

---

## 4. What is combined from the other proposals (still one vertical, one asset class)

1. **From DECISION-VALUE-FIRST: the decision layer.** Replace per-turbine thresholds with a weekly ranked inspection list under an explicit technician and crane budget, plus a deferral list with risk.
   - Score policies on decision cost in the existing policy-replay harness, not on RMSE.
   - Use group-conditional (Mondrian) conformal per farm and turbine model.
   - Redesign the fleet-level rule so it triggers a data-quality check instead of mass escalation. Today it escalates 25-36% of healthy C-MAPSS engines while active (README.md).
   - Keep SCANIA Component X (real field, CC BY 4.0) as the RUL-with-censoring method benchmark, outside the vertical.
2. **From ACCESS-FIRST: the pilot discipline.**
   - Make the first owner conversation a written go/no-go gate: does the owner control SCADA exports, and are there at least 12 months of 10-minute history and a fault or work log?
   - Keep the pilot offline and read-only (copies of exports only), with pre-registered shadow metrics: agreement, false alarms per turbine-week, misses, lead time.
   - Pseudonymise technician names in the audit chain (DPDP, per R5).
   - Run the work under an academic home (AICTE internship credit, per the ACCESS-FIRST proposal; the AICTE PDF was not re-opened by me, so **UNVERIFIED**) alongside the verified NIWE AAP route.
3. **Unchanged from DATA-FIRST:**
   - the validation ladder: W1 single-site, W2 cross-site, W3 long-horizon drift, W4 decision back-test, W5 customer back-test, W6 shadow;
   - event metrics with Wilson intervals;
   - conformal thresholds calibrated on normal datasets;
   - re-messaging from "RUL with a 90% interval" to "calibrated early warning with auditable triage" for this vertical.

---

## 5. First steps (judgement)

1. Download CARE v6 and check the MD5. Recount events per farm (45 vs 44). Run the healthy-baseline index on Farm A with turbine-wise splits, and report the CARE score against the 0.66 autoencoder and 0.5 random bars. Report negative results.
2. Calibrate alarm thresholds conformally on CARE normal datasets. Report achieved vs nominal false-alarm rate on unseen farms: Farm A→B/C (cross-asset) and A→Kelmarsh/Penmanshiel/HoT (in-class, false alarms only).
3. Run drift and retrain gates across the Hill of Towie AeroUp retrofit dates (2021-2023), and a decision back-test against its 10-minute downtime series.
4. Apply to NIWE AAP (Chennai; applications by the 15th of each month for a start the next month, per the notice). Use the published benchmark as the calling card.
5. In parallel, legal review of CC BY-SA obligations before any commercial use of CARE or EDP derivatives.

---

## 6. Conditions that would change the choice

- **Owners do not control their data.** If the first 3-5 owner conversations show that SCADA exports and failure logs are controlled by the OEM or O&M contractor and cannot be shared, the buyer becomes the O&M provider (e.g. INOX Green, 11 GW wind O&M, vendor claim). That door is crowded and hard. Switch to the runner-up.
- **The public ladder fails.** If the system cannot beat the 0.66 autoencoder bar, or falls below the 0.5 accuracy threshold on CARE, there is no credible real-data story in wind. Re-evaluate.
- **Licence blocks commercial use.** If legal review concludes that CC BY-SA share-alike attaches to trained models in a way that blocks the commercial product, and the CC BY sets (no curated failure labels) are not enough on their own, the data advantage shrinks to near the bus option.
- **The target fleet lacks usable SCADA.** If the target Indian 1.5-2 MW fleet turns out to lack usable 10-minute SCADA history, or is mostly gearless, the asset class must change. Indian model mix and drivetrain type are **UNVERIFIED**.
- **An STU offers digital records.** If an STU depot, via CIRT or directly, offers 2-3 years of digital per-bus aggregate-change and breakdown registers within 3 months, the bus option's access score rises to 3-4 and it overtakes wind on the equal-weight sum.
- **The campus has a chiller plant and the team wants a pilot in one season.** If the week-1 check finds a central chilled-water plant with at least 12 months of logs and estate approval, chillers are the fastest pilot. I would still not make them the initial vertical, given the data and decision-value scores, but they could run as a side case study.
- **Competition analysis changes.** If a working WebSearch pass shows India-specific SCADA analytics for ageing turbines is already saturated, or that STU depot prioritisation tools exist, re-score competition.

---

## 7. Items that remain UNVERIFIED

- Whether Indian wind owners, rather than OEM or O&M contractors, control SCADA exports.
- The model mix and gearbox presence of India's 1.5-2 MW fleet.
- Whether NIWE holds or would share turbine SCADA.
- India-specific competitor density.
- The final status of CEA cyber regulations.
- The EDP primary page; the Hill of Towie downtime derivation from operator logs; the Kelmarsh 2023-2024 defect audit.
- The Fleet Edge scope (HTTP 403).
- The AICTE internship policy, the ASRTU Fleet Handbook 2024 and the Scania Component X cost matrix in arXiv 2401.15199: all cited by proposals, none re-opened by me.
- The per-event cost of turbine drivetrain failures in India.

---

## Sources (all accessed 2026-10-18)

**Opened in this session (WebFetch):**
1. https://zenodo.org/records/15846963 (CARE to Compare v6; real field; CC BY-SA 4.0)
2. https://arxiv.org/html/2404.10320v2 (CARE paper v2)
3. https://creativecommons.org/licenses/by-sa/4.0/ (CC BY-SA 4.0 deed)
4. https://iea-wind.org/wp-content/uploads/2024/07/EDP-OpenData-Details.pdf (IEA Wind summary of EDP Open Data; extracted locally)
5. https://zenodo.org/records/22662930 (Hill of Towie v2.1.0; real field; CC BY 4.0)
6. https://zenodo.org/records/16807551 (Kelmarsh v4; real field; CC BY 4.0)
7. https://zenodo.org/records/16807304 (Penmanshiel v3; real field; CC BY 4.0)
8. https://researchdata.se/catalogue/dataset/2024-34/3 (SCANIA Component X v3; real field; CC BY 4.0)
9. https://archive.ics.uci.edu/dataset/421/aps+failure+at+scania+trucks (APS; real field; CC BY 4.0; costs 10/500)
10. https://mnre.gov.in/en/physical-progress/ (installed wind capacity 59,201.07 MW as on 30.09.2026)
11. https://cdnbbsr.s3waas.gov.in/s3716e1b8c6cd17b771da77391355749f3/uploads/2023/12/202312131874296229.pdf (MNRE National Repowering & Life Extension Policy 2023; scanned, read page by page)
12. https://niwe.res.in/Open_data_Set/open_wind_dataset/ (NIWE open datasets)
13. https://niwe.res.in/static/pdf/NIWE-AAP_Internship_Programme.pdf (NIWE AAP; extracted locally)
14. https://strathprints.strath.ac.uk/54903/ (May and McMillan 2013, false alarms in CBM)
15. https://www.turbit.com/ (vendor claims)
16. https://www.onyxinsight.com/ (vendor claims)
17. https://www.inoxgreen.com/ (vendor claims)
18. https://www.suzlon.com/ (no service figures on page)
19. https://faultdetection.lbl.gov/ (LBNL/DOE FDD data; origin and licence not stated)
20. https://raw.githubusercontent.com/buds-lab/building-data-genome-project-2/master/LICENSE (BDG2 licence)
21. https://ozonecell.nic.in/wp-content/uploads/2019/03/INDIA-COOLING-ACTION-PLAN-e-circulation-version080319.pdf (India Cooling Action Plan; extracted locally)
22. https://www.augury.com/ (vendor page, lists chillers)
23. https://www.asrtu.org/resource/front/uploads/PROFILE_PERFORMANCE-2021-22.pdf (CIRT STU Profile and Performance 2021-22; extracted locally; real field administrative statistics)
24. https://uptake.com/ (vendor page)
25. https://fleetedge.tatamotors.com/ (HTTP 403; content not read)

**WebSearch:** one attempt; refused because the shared per-turn budget was exhausted.

**Local files read:**
- C:\Users\HP\OneDrive\Desktop\tata\README.md
- C:\Users\HP\OneDrive\Desktop\tata\FINAL_HANDOFF.md
- product\research\R3_competitive_landscape.md (searched)
- product\research\R4_datasets.md (searched)
- product\research\R5_integration_standards.md (searched)
- product\research\V_decision_value_first.md (header and scoring)
- The three proposals as supplied to the judge.
