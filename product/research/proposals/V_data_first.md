# Initial vertical and asset class: the data-first proposal

Angle: **DATA-FIRST.** Pick the vertical and asset class where credible **real** public data with failure or maintenance labels exists under a usable licence. That lets SentinelLoop climb a validation ladder before it has any customer.

Written 2026-10-18. Every factual claim cites a URL listed under "Sources" (tags [Wn]). Claims taken from the team's research files without re-opening the underlying page are marked "(via R1-R5)". Anything I could not verify is marked **UNVERIFIED**. Statements marked *Judgement* are the team's analysis, not sourced facts.

**Tools note.** On my first call, WebSearch returned "web search budget is used up" (200 calls per turn, shared across agents), so I ran no web searches. WebFetch worked, and I used it only on known primary URLs (dataset landing pages, ministry pages, vendor home pages).
- The MNRE repowering policy is a scanned PDF. I read it by rendering its pages to images locally.
- The IEA Wind EDP summary is a PDF. I extracted its text with `pdftotext`.
- prescinto.ai failed TLS in WebFetch, so I read it with `curl` and recorded where it redirects.

No large data files were downloaded.

Data-type vocabulary (same as R4):
- **REAL FIELD**: measured on assets in commercial service.
- **REAL LAB**: measured on a test rig.
- **SIMULATED**: produced by a physics or system model.
- **SYNTHETIC**: produced by a statistical or rule-based generator.

---

## 1. Recommendation

| | |
|---|---|
| **Vertical** | Onshore wind-farm owner-operators in India and the O&M teams that serve them. Start with owners of ageing turbines that face repowering or life-extension decisions under MNRE's 2023 policy. |
| **Asset class** | Geared onshore wind turbine generators of about 2 MW, monitored through the 10-minute SCADA and fault/alarm logs they already record. Targets are SCADA-observable drivetrain faults (gearbox and its bearings, generator) and electrical faults (transformer). |
| **Geography** | India for customers, starting with Tamil Nadu: the MNRE policy table gives it the largest sub-2 MW fleet, 7,386.5 MW [W20]. The public validation data are European: Portugal, German offshore and the UK [W1][W3][W5][W6][W7]. |
| **Data type it rests on** | REAL FIELD SCADA, with fault labels taken from operator failure logbooks and service reports [W2][W4]. Not lab, not simulated. |

**One-line reason.** Of all the public datasets checked (R4 plus this stream), wind turbines are the only asset class with several **independent** real-field datasets that carry failure, fault, alarm or downtime labels under CC BY or CC BY-SA licences:
- 4 operators: EDP; two anonymised German offshore operators; Cubico; RES/TRIG.
- 5 or more turbine types.

Together they support a validation ladder of single-site, then cross-site, then long-horizon drift, then decision back-test, all before any customer exists. No other candidate vertical offers a public cross-site rung.

---

## 2. Why the data points to wind (candidate comparison)

Only real-field candidates are compared. Lab, simulated and synthetic sets cannot provide sim-to-real evidence (R4 sec. 6.2).

| Candidate (vertical, asset) | Public real labelled data | Independent sources | Licence | Cross-site test possible publicly? | Fit to SentinelLoop core | Verdict |
|---|---|---|---|---|---|---|
| **Wind farms, ~2 MW turbine drivetrain/electrical (SCADA)** | CARE to Compare: 44-45 fault-leading events plus 50-51 normal datasets, 36 turbines, 3 farms [W1][W3]. EDP failure logbook: 23 records with Component and Remarks [W4]. Hill of Towie: 2016-2026 alarm logs and operator-log downtime [W5]. Kelmarsh and Penmanshiel: 2016-2024 events data [W6][W7]. | 4 or more operators | CC BY 4.0 (HoT, Kelmarsh, Penmanshiel); CC BY-SA 4.0 (CARE; EDP per IEA summary) | **Yes**: 3 CARE farms plus 3 further farms | Anomaly index, drift, gating, triage and audit fit directly. RUL is weak. | **Chosen** |
| Heavy-truck fleets, anonymised engine "Component X" | SCANIA CX: 2,272 repaired and 21,278 censored train vehicles; 5-class validation labels [W10][W9] | 1 (Scania) | CC BY 4.0 [W9] | No | Best RUL-with-censoring fit | Rejected as the vertical; kept as an RUL method benchmark |
| Metro rail, train air-production-unit compressor | MetroPT-3: 4 air-leak failures [W11]; MetroPT2: 2 failures [W12]; MetroPT: 3 failures (via R4) | 1 (Porto metro) | CC BY 4.0 | No | Anomaly case study only | Rejected: 9 events in total |
| Data centres, hard drives | Backblaze: 21,609 lifetime failures, 354,415 drives in Q2 2026 [W13] | 1 | Custom: derivatives may be sold, the data may not [W13] | No (one operator, many models) | Survival and calibration stress test | Rejected: not industrial maintenance |
| Offshore oil wells, subsea/topside valves and chokes | 3W 2.0.0: 1,119 real instances, 525 of them undesirable events (via R4) | 1 (Petrobras) | Data CC BY 4.0 [W14] | No | Event detection | Rejected: mostly process events [W15] |

*Judgement, statistical power.* Wind's labelled-event count is modest. With 44 fault events, a measured detection rate of 50-70% carries a 95% Wilson interval of about ±13-14 percentage points. With one farm's 11 events it is about ±24-25 points (computed locally). So wind supports honest **interval-reported** claims, not precise accuracy claims. It is still the only vertical where one model can be tested on farms it never saw. That is the risk a first customer actually poses.

---

## 3. Public real data available (what each rung can prove)

| Dataset | Data type | Assets and period | Labels relevant to maintenance | Licence and access | Source |
|---|---|---|---|---|---|
| **CARE to Compare** (Fraunhofer IEE), Zenodo v6, 2025-07-09 | REAL FIELD | 36 turbines, 3 farms, about 89 turbine-years. Farm A is EDP onshore Portugal; B and C are anonymised German offshore. Features: 86 / 257 / 957. 10-minute averages. | Zenodo v6: 45 datasets with a labelled anomaly leading to a fault, 50 normal. Paper v2: 44 and 51, with per-farm counts A=11, B=6, C=27. Status IDs 0-5 per timestamp. Farm A event starts come from the EDP fault logbook. B and C starts come from "data analysis, feedback of the wind farm operator, service report documents and expert knowledge". Named examples: gearbox bearing damage (event 51) and transformer-cell high temperature (events 7, 19, 34). | CC BY-SA 4.0; direct download, 5.5 GB zip | [W1][W2][W3] |
| **EDP Open Data, Wind Farm 1** | REAL FIELD | 5 turbines, 10-minute SCADA, 2016-01 to 2017-12. Signals include "temperatures inside nacelle throughout the drivetrain". | Failure logbook: 23 records, 2016-03-03 to 2017-08-21, fields Turbine_ID, Component, Timestamp, Remarks. Operation logs: 256,231 records (training) and 62,604 (testing). | CC-BY-SA. Sign-in needed. The turbine location file is under NDA. **Partially verified**: IEA Wind summary only; EDP pages returned 403 to R4. | [W4] |
| **Hill of Towie** (RES on behalf of TRIG), Zenodo v2.1.0, 2026-09-08 | REAL FIELD | 21 Siemens SWT-2.3-VS-82. 10-minute SCADA and alarm logs, Jan 2016 to Apr 2026. About 1 Hz fastlog and LiDAR, Jan-Apr 2026. | Alarm logs; per-10-minute shutdown duration "derived from SCADA data and RES operator logs" (to Aug 2024); AeroUp retrofit install dates (rollout 2021-2023). No dedicated failure records stated. | CC BY 4.0; 29.7 GB | [W5] |
| **Kelmarsh** (Cubico), Zenodo v4, 2025-08-12 | REAL FIELD | 6 Senvion MM92 (12.3 MW site). 10-minute SCADA plus events data, 2016 to end-2024, from Cubico's Greenbyte secondary SCADA. | Events data only; no curated failure list stated | CC BY 4.0; 3.8 GB | [W6] |
| **Penmanshiel** (Cubico), Zenodo v3, 2025-08-13 | REAL FIELD | 14 Senvion MM82 (28.7 MW site); same data types and period as Kelmarsh | Events data only | CC BY 4.0; 7.5 GB | [W7] |
| Kelmarsh provenance audit (third party), Zenodo, 2026-10-06 | Derived | Reconstruction of the Kelmarsh 2023 and 2024 Turbine_Data files; replication on Penmanshiel v3 | Flags structural and export defects; findings not checked by me | CC BY 4.0 | [W8] |
| SCANIA Component X v3 (method benchmark only) | REAL FIELD | Swedish truck fleet; anonymised component; 14 anonymised variables; irregular sampling | 2,272 repaired / 21,278 not repaired (train); 5-class proximity-to-failure validation labels | CC BY 4.0, public | [W9][W10] |

**India-specific public data: none found.** NIWE's "Open Datasets" page lists 10 wind-monitoring-station datasets, a 150 m wind-atlas dataset and 20 technical reports. It lists no turbine SCADA, operational or failure data [W22]. The validation ladder therefore runs on European turbines. See risk 3.

---

## 4. The validation ladder this enables (before any customer)

*Judgement.* These are proposed gates, not results. Nothing below has been run.

| Rung | Data | Question answered | Pass evidence to publish |
|---|---|---|---|
| W0 (done) | C-MAPSS, SIMULATED | Does the pipeline work end to end? | Existing results; README and FINAL_HANDOFF |
| W1 single-site, real labels | CARE Farm A (11 events plus normal datasets) [W2]; EDP logbook [W4] | Does the healthy-baseline index flag faults before the logged fault start, at a stated false-alarm rate? | Detection with Wilson interval, lead time, false alarms per turbine-year on normal datasets, CARE score [W1] |
| W2 cross-site, real labels | CARE Farms B and C (offshore; 257 and 957 features) [W2][W3] | Does the method transfer to an unseen farm and schema without hand-retuning? | Same metrics per farm, plus whether conformally calibrated thresholds hold their nominal false-alarm rate on held-out normal datasets |
| W3 long-horizon drift and interventions | Hill of Towie 2016-2026 with AeroUp dates [W5]; Kelmarsh and Penmanshiel 2016-2024 [W6][W7] | Does the age-matched drift monitor fire on **documented** changes (retrofits) and stay quiet otherwise? Does the promotion gate behave correctly across real seasons and years? | Change-point hit rate on retrofit dates; gate accept/reject log |
| W4 decision back-test | HoT operator-log downtime and alarm logs [W5]; EDP operation logs [W4] | How many downtime episodes did an escalation precede? What escalation load per operator shift would the agent create? | Escalations per shift against the alarm budget in R1 (about 1 per 10 minutes, IChemE, via R1); precision of escalations |
| W5 customer shadow back-test | One Indian owner's exported historical SCADA plus failure log (offline files) | Do W1-W4 results hold on Indian turbines? | Same report on the customer's data, no OT connection |
| W6 live read-only shadow | Customer, read-only | Prospective performance | Prospective log, audit chain |

The CARE normal datasets matter here. False alarms are a central adoption barrier:
- R2 cites Hoffmann & Lasch 2025 (via R2).
- An offshore-wind modelling study found that the cost of investigating false alarms "can reduce or change the cost benefit" of condition monitoring [W31].

CARE is the only real-field set checked that ships explicitly normal comparison datasets alongside its fault events [W1][W3].

---

## 5. Fit with the current system

Mapping is *Judgement* unless cited. SentinelLoop modules are named per README and FINAL_HANDOFF (local).

- **Healthy-baseline anomaly index** (FINAL_HANDOFF D10). This is the same idea as the normal-behaviour models that wind SCADA monitoring uses. CARE is built to evaluate exactly this, with its Coverage, Accuracy, Reliability and Earliness score [W1]. **Strong fit.**
- **Regime normalisation** (D14). C-MAPSS has 6 operating conditions; a turbine's operating regime is set by wind speed, power and pitch. CARE's status IDs (0 normal, 2 idling; 1, 3, 4, 5 not normal) give a ready mask for trustworthy operation [W2]. **Strong fit.**
- **Input-quality escalation.** Status codes, curtailment and service-mode periods are real-data equivalents of the injected faults in E3. HoT's operator-derived downtime marks periods that are not normal [W5]. **Good fit.**
- **Age-matched drift monitor and gated retraining** (D17, D22, D24). Real reasons to retrain exist in wind data:
  - component replacements (EDP logbook timestamps [W4]);
  - aerodynamic retrofits with known install dates (HoT AeroUp [W5]).
  
  These give ground-truth change points that C-MAPSS never had. **Good fit; better test conditions than today.**
- **Conformal intervals** (CQR). Reuse them to calibrate *alarm thresholds* on normal periods, giving a false-alarm rate that is nominal under exchangeability. RUL intervals cannot be validated with statistical strength on 44 events (sec. 2). **Partial fit; the module must change role.**
- **RUL point model.** Wind turbines are repaired, not run to failure. The public sets give time-to-fault windows, not unit lifetimes [W2]. **Weak fit.** If the RUL method needs real-label evidence, use SCANIA CX as an out-of-vertical method benchmark [W10].
- **Triage agent and work orders.** The EDP logbook's Component and Remarks fields [W4] and HoT's operator logs [W5] are the closest public analogue to the work-order history R4 found missing everywhere else. **Good fit.** The lower-bound RUL trigger must be replaced by a persistence and severity rule.
- **Hash-chained audit log.** Independent wind-analytics vendors sell owner-side evidence. Clir advertises reconciling OEM availability calculations into "dispute-ready reports" (vendor claim) [W28]. MNRE's life-extension route requires a turbine to be "assessed and certified ... as per the UL 4143" standard [W20]. *Judgement, unvalidated with any customer:* a re-derivable decision record may be valued by owners who contract O&M to an OEM or service provider.

---

## 6. What must change in the system

1. **Data adapters** for 10-minute SCADA with timestamps and turbine IDs, replacing cycles and engine IDs. Each farm needs a signal-mapping file: features run 86, 257 and 957 per CARE farm [W2]. Kelmarsh and Penmanshiel ship signal mappings [W6][W7].
2. **Label handling and leakage control.** CARE Farm A marks the 14 days before each fault as status 4 and the 3 days after as status 3 [W2]. Status must never be a model input around events; use it only as an evaluation mask. Split by turbine and by farm, never by random time window. This continues the leakage discipline of E0/H7.
3. **Evaluation target change.** Move from last-cycle RMSE to event metrics: detection with Wilson interval, lead time, false alarms per turbine-year on normal datasets, and the CARE score [W1]. RUL metrics stay on C-MAPSS. Optionally add SCANIA CX as the RUL method benchmark [W10].
4. **Conformal false-alarm control.** Calibrate per-farm alarm thresholds on held-out normal windows. Report achieved versus nominal false-alarm rate on unseen normal datasets.
5. **Triage rules for wind.** Replace the RUL-lower-bound trigger with three parts:
   - persistence (N consecutive 10-minute windows);
   - a mapping from residual sensor group to component (gearbox, generator, transformer);
   - an escalation budget per operator shift, with the alarm-rate benchmark from R1 as the ceiling.
6. **Maintenance-aware retraining.** Reset or re-baseline after logged replacements or retrofits [W4][W5]. Gate challengers on held-out turbines and farms, not held-out time slices of the same turbine.
7. **Work-order schema** with a wind component taxonomy and an external ID for idempotent upsert into a CMMS (MaintainX and Odoo patterns via R5). Free-text Remarks feed the component mapping [W4].
8. **Licence and provenance hygiene.**
   - Record dataset versions and hashes.
   - Keep EDP raw data (sign-in, NDA location file [W4]) out of the repository.
   - Attribute CC BY and CC BY-SA sources. Share any redistributed derived data from CARE or EDP under CC BY-SA.
   - Use the Kelmarsh reconstructed 2023-2024 files, or exclude those years [W8].
9. **Offline-first ingestion** of CSV or Parquet exports for the first customer, so a pilot needs no OT connection. R5 sets out the read-only OT patterns and India's CERT-In and DPDP duties (via R5).

---

## 7. India relevance and the pilot access path

**Market facts (sourced):**
- India's cumulative installed wind capacity is **59,201.07 MW as on 30.09.2026**. The page heading says 31 Aug 2026, so the date is inconsistent on the page [W16]. IWTMA reports 59.20 GW operational as of September 2026 (industry association) [W24].
- MNRE's "National Repowering & Life Extension Policy for Wind Power Projects - 2023" was issued 7 Dec 2023 and supersedes the 2016 policy [W19][W20]. It states:
  - Capacity was 44.29 GW in October 2023.
  - "Most of the Wind-turbines installed in India up to the year 2000 are of sub MW capacity".
  - NIWE estimates repowering potential at **25.406 GW** for turbines below 2 MW. The state table totals 25,396.65 MW, a small inconsistency in the source.
  - Tamil Nadu has 7,386.5 MW below 2 MW.
  - Eligibility includes turbines below 2 MW and, on commercial or voluntary grounds, turbines older than 15 years.
  - Life-extension refurbishment "may be done by suitable modifications in the turbine components such as gearbox, blades, generator, controller". Turbines must be "assessed and certified ... as per the UL 4143: Wind Turbine Generator Lifetime Extension standard". Total life must not exceed 40 years.
  - It recognises "Aggregation Projects" of turbines "owned by multiple owners with shared common infrastructure" [W20].
- India's O&M market includes large service providers. INOX Green claims more than 13 GW of renewable O&M assets, 11 GW of them wind, and lists "Predictive Maintenance" as a service heading (vendor claims) [W25].

**Pilot access path (*Judgement*, sequenced for a student team with no customer):**
1. **Weeks 0-10: public ladder W1-W4.** Free tools, laptop-scale. The largest single file to handle is CARE's 5.5 GB zip [W3]; HoT can be taken year by year [W5]. Publish a reproducible benchmark report with intervals and negative results. This report becomes the credibility artefact a first customer can check.
2. **Institutional on-ramp.** Apply to the NIWE Academic Associate Programme. It is open to Indian UG/PG students with at least 60% marks, runs 2 weeks to 6 months unpaid, and lists "Machine Learning /AI and data analysis" among its internship domains [W23]. NIWE is MNRE's autonomous R&D institute in Chennai, with a test station at Kayathar [W21]. Whether NIWE would share any turbine operational data is **UNVERIFIED**.
3. **First prospects.** Owners of ageing sub-2 MW turbines in Tamil Nadu facing repower-or-extend decisions [W20]. Offer a free **offline back-test** on their exported SCADA history and failure log (rung W5). Vendors already sell this way: Turbit offers "Request a backtest" (vendor page) [W27]. Networking venue: IWTMA's Windergy India events [W24]; whether owners attend is **UNVERIFIED**.
4. **Read-only shadow (W6)** only after W5 succeeds. Sign a DPDP data-processing contract if operator logs contain staff names (via R5).
5. **Check data rights first.** Whether Indian owners, rather than the OEM or O&M contractor, control SCADA exports under typical O&M contracts is **UNVERIFIED**. Ask this in the first conversation.

---

## 8. Competitive context in wind (all vendor claims)

- **ONYX Insight**: CMS hardware for drivetrain, blades and pitch plus the Cortex software. Claims 32,000+ turbines monitored and faults caught "up to 24 months" ahead. No India mention on the page [W26].
- **Turbit**: AI monitoring. Claims 3,500+ turbines, 12k+ neural networks in production, and a "Request a backtest" offer [W27].
- **Clir**: performance monitoring with anomaly detection and OEM availability reconciliation. Claims "350+ GW" across solar, BESS and wind [W28].
- **IBM Maximo Renewables**: turbine prognosis visualisations, digital-twin loss analysis, and work orders created automatically via Maximo Manage [W30]. prescinto.ai now redirects to this page (observed via curl) [W29]. Whether IBM acquired Prescinto is **UNVERIFIED** from a primary announcement.
- **INOX Green** (India O&M provider): "Predictive Maintenance" heading, no method described [W25].

*Judgement.* Wind SCADA analytics is a contested market, and SentinelLoop cannot win on detection accuracy or fleet size. The wedge must be what the public data can prove:
- calibrated false-alarm control;
- cross-farm transfer reported with intervals;
- re-derivable decisions for owner-side evidence;
- zero hardware and offline-first ingestion.

None of this is validated with customers.

---

## 9. Biggest risks

1. **Few labelled events.** 44-45 fault events in CARE [W1][W3], and the EDP logbook overlaps CARE Farm A [W2][W4]. Detection claims will carry wide intervals (sec. 2). RUL cannot be validated on public wind data at useful strength.
2. **Label quality.**
   - Farm A event starts are fault-logbook start timestamps only. The authors note the "true" anomaly start can differ [W2].
   - B and C statuses "may be inconsistent", and missing values were replaced with 0 [W2].
   - Kelmarsh 2023-2024 files have reported structural defects [W8].
3. **Domain shift to India.**
   - Public data cover Senvion MM82 and MM92, Siemens SWT-2.3 and anonymised German offshore turbines [W2][W5][W6][W7].
   - India's ageing fleet is largely sub-2 MW and sub-MW for pre-2000 installs [W20].
   - No Indian turbine SCADA is public [W22].
   - Which turbine models dominate India's fleet is **UNVERIFIED**.
4. **Data access and rights at the customer.** O&M is concentrated in large providers [W25], and owner control of SCADA exports is **UNVERIFIED**.
5. **Strong incumbents** with large fleets, CMS hardware and analysts (sec. 8, vendor claims).
6. **SCADA-only physics limit.** 10-minute averages [W2] are coarser than vibration CMS. Lead times may be shorter than CMS vendors claim (ONYX "up to 24 months", vendor claim [W26]). The actual CARE lead-time distribution is **UNVERIFIED** (not computed).
7. **Licence obligations.** CC BY-SA share-alike on CARE and EDP [W3][W4]. Whether a trained model is "adapted material" is unsettled. Get legal review before commercial use (not legal advice). EDP access needs sign-in, and its primary page was blocked (403 in R4).
8. **The headline changes.** The product's current story is "RUL with a 90% interval". In wind the honest headline becomes "calibrated early warning with auditable triage". Re-messaging and re-evaluation work is required, and claims must not drift back to RUL without evidence.
9. **Power-sector cyber regulation.** CEA's draft power-sector cyber-security regulations (Aug 2024) may apply to generation assets; their finalisation is **UNVERIFIED** (via R2/R5). An offline-first pilot reduces exposure but does not remove it.

---

## 10. Alternatives rejected

| Option | Reason |
|---|---|
| Heavy-truck fleets, anonymised engine "Component X" (SCANIA CX) | Strongest real RUL labels: 2,272 repaired and 21,278 censored train vehicles, CC BY 4.0 [W9][W10]. But there is one source, the component name and all 14 variables are anonymised [W10], no cross-site rung exists, and fleet buyers sit outside plant maintenance; fleet PdM incumbents such as Uptake Fleet exist (via R3). Keep it as the RUL-with-censoring method benchmark. |
| Rail transit operators, train air-production-unit compressors (MetroPT-3, MetroPT, MetroPT2) | Real, CC BY 4.0 and well documented, but there are only 4, 3 and 2 failures from one operator [W11][W12] (MetroPT via R4). That is far too few for any accuracy statistic, and there is no cross-site test. |
| Data-centre operators, hard-disk drives (Backblaze) | The largest real failure set: 21,609 lifetime failures [W13]. But it is IT hardware, not industrial maintenance; terms forbid selling the data itself [W13]; and it comes from one operator. Useful only as a calibration stress test. |
| Offshore oil and gas, wells and subsea valves (Petrobras 3W) | 525 real labelled undesirable events (via R4), data CC BY 4.0 [W14]. But the classes are mostly flow-assurance and process events (hydrate, slugging, scaling) rather than equipment maintenance [W15]. One operator. Customer access for an Indian student team is unrealistic (*Judgement*). |
| Process-plant rotating equipment (bearings, pumps, gearboxes) | Only lab data, with absent, non-commercial or conflicting licences (FEMTO, XJTU-SY, CWRU, Paderborn, SKAB), or an anonymous Kaggle pump set of unknown licence (via R4). No real field labels. |
| Turbofan engines (current C-MAPSS asset) | SIMULATED only, and N-CMAPSS is also simulated (via R4). OEMs sell engine health monitoring inside per-flight-hour contracts (via R3). |
| Industrial hydraulic systems (UCI Hydraulic) | Clean CC BY 4.0 labels, but REAL LAB data from one rig (via R4). No field rung. |

---

## 11. UNVERIFIED items (collected)

- Whether Indian wind owners control SCADA exports under OEM or third-party O&M contracts.
- Which turbine makes and models dominate India's operating fleet.
- Whether NIWE would share turbine operational data with interns.
- Whether owners attend Windergy India.
- Whether IBM acquired Prescinto (only the redirect was observed).
- The component distribution of all CARE events: only 4 events were named on the page.
- The CARE lead-time distribution.
- The EDP licence and access terms beyond the IEA Wind summary.
- Finalisation of CEA's power-sector cyber regulations.
- How CC BY-SA applies to trained models.

---

## Sources

All accessed 2026-10-18.

- [W1] arXiv abstract, Gück, Roelofs, Faulstich, "CARE to Compare: A real-world dataset for anomaly detection in wind turbine data": https://arxiv.org/abs/2404.10320
- [W2] arXiv full text v2 (10-minute resolution, per-farm event counts, label sources, status IDs): https://arxiv.org/html/2404.10320v2
- [W3] Zenodo, Wind Turbine SCADA Data For Early Fault Detection (CARE To Compare) v6: https://zenodo.org/records/15846963
- [W4] IEA Wind, EDP OpenData Details (PDF; text extracted locally with pdftotext): https://iea-wind.org/wp-content/uploads/2024/07/EDP-OpenData-Details.pdf
- [W5] Zenodo, Hill of Towie wind farm open dataset v2.1.0: https://zenodo.org/records/22662930
- [W6] Zenodo, Kelmarsh wind farm data v4: https://zenodo.org/records/16807551
- [W7] Zenodo, Penmanshiel wind farm data v3: https://zenodo.org/records/16807304
- [W8] Zenodo API, third-party Kelmarsh provenance audit record: https://zenodo.org/api/records/23196733
- [W9] Researchdata.se, SCANIA Component X v3 landing page: https://researchdata.se/catalogue/dataset/2024-34/3
- [W10] arXiv, SCANIA Component X paper v1 (HTML): https://arxiv.org/html/2401.15199v1
- [W11] UCI, MetroPT-3 dataset: https://archive.ics.uci.edu/dataset/791/metropt+3+dataset
- [W12] Zenodo, MetroPT2 v2: https://zenodo.org/records/7766691
- [W13] Backblaze, Hard Drive Test Data (Drive Stats): https://www.backblaze.com/cloud-storage/resources/hard-drive-test-data
- [W14] GitHub, petrobras/3W: https://github.com/petrobras/3W
- [W15] 3W dataset.ini (version 2.0.0, event classes): https://raw.githubusercontent.com/petrobras/3W/main/dataset/dataset.ini
- [W16] MNRE, Physical Progress: https://mnre.gov.in/en/physical-progress/
- [W17] MNRE, Wind Overview: https://mnre.gov.in/en/wind-overview/
- [W18] MNRE, Wind section navigation page: https://mnre.gov.in/en/wind/
- [W19] MNRE, Wind Policies and Guidelines list: https://mnre.gov.in/wind-policy-and-guidelines/
- [W20] MNRE, National Repowering & Life Extension Policy for Wind Power Projects - 2023 (scanned PDF, pages rendered and read locally): https://cdnbbsr.s3waas.gov.in/s3716e1b8c6cd17b771da77391355749f3/uploads/2023/12/202312131874296229.pdf
- [W21] NIWE home page: https://niwe.res.in/
- [W22] NIWE, Open Datasets: https://niwe.res.in/Open_data_Set/open_wind_dataset/
- [W23] NIWE Academic Associate Programme internship (PDF; text extracted locally): https://niwe.res.in/static/pdf/NIWE-AAP_Internship_Programme.pdf
- [W24] Indian Wind Turbine Manufacturers Association (Indian Wind Power): https://www.indianwindpower.com/
- [W25] INOX Green home page: https://www.inoxgreen.com/
- [W26] ONYX Insight home page: https://www.onyxinsight.com/
- [W27] Turbit home page: https://www.turbit.com/
- [W28] Clir home page: https://www.clir.eco/
- [W29] prescinto.ai (curl; redirected once to the IBM page below): https://www.prescinto.ai/
- [W30] IBM Maximo Renewables: https://www.ibm.com/products/maximo/renewables
- [W31] Strathprints, May & McMillan (2013), "Condition based maintenance for offshore wind turbines: the effects of false alarms from condition monitoring systems": https://strathprints.strath.ac.uk/54903/
- [W32] MNRE, Policies and Regulations (navigation only; no wind policy listed there): https://mnre.gov.in/en/policies-and-regulations/

Opened but returned no usable content:
- https://opendata-renewables.engie.com/ (DNS failure)
- https://www.suzlon.com/in-en/services (404)
- https://www.suzlon.com/ (no figures on the page)
- https://www.suzlon.com/our-businesses/project-service-solutions/ (500)

Team research files used ("via R1-R5"; underlying URLs are listed in each file):
- `product/research/R1_maintenance_workflows.md`
- `product/research/R2_pdm_adoption_failures.md`
- `product/research/R3_competitive_landscape.md`
- `product/research/R4_datasets.md`
- `product/research/R5_integration_standards.md`

Local (not web) sources:
- `README.md` and `FINAL_HANDOFF.md`, for SentinelLoop module names and decision IDs.
- Wilson intervals computed with Python on 2026-10-18.
