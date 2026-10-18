# Initial vertical and asset class: the decision-value-first proposal

Written 2026-10-18 for the SentinelLoop product team. Angle: **DECISION-VALUE-FIRST**. The aim is to find the vertical and asset class where better prioritisation and scheduling of maintenance under uncertainty, with limited technicians and spare parts, changes a real decision the most, and where incumbents are weakest.

**Method and tool status.**
- WebFetch worked. **WebSearch did not:** the shared per-turn budget of 200 searches was already used up by the R1-R5 streams, so I ran no web searches. New evidence comes only from pages I fetched directly at known or discoverable primary URLs: ASRTU/CIRT documents, Scania's dataset paper, the UCI APS page, Uptake, Tata Motors Fleet Edge and Odoo source.
- Everything else comes from the research files R1-R5 in this folder and is tagged [R1]-[R5] with the URL that stream opened.
- Labels used throughout:
  - **UNVERIFIED**: not checked against a page I opened.
  - **Vendor claim**: a statement on a vendor's own page.
  - **Analysis**: my own reasoning, not a sourced fact.
  - **Computed**: arithmetic I did on published figures.
- Data-type vocabulary follows R4: real field, real laboratory, simulated, synthetic. I add **real field administrative statistics** for aggregate figures that operators report about themselves.

---

## 1. Proposal (exactly one pair)

| | |
|---|---|
| **Vertical** | Indian public bus operators that maintain their own fleets: State Transport Undertakings (STUs/SRTUs), which run diesel buses from depots with in-house divisional and central workshops. Start with one depot or division of a single STU. |
| **Asset class** | Major powertrain aggregates of diesel buses: the **engine, fuel-injection (FI) pump and gearbox**, which are changed for new or reconditioned units. These are the items STUs already track by life in kilometres [CIRT-P&P]. |
| **Decision changed** | Each night and each week, given limited mechanic-hours, docking bays and reconditioned aggregates on hand, the depot chooses which buses to pull off the road for an aggregate change or inspection, and which to leave in service. Upstream, the central workshop chooses how many reconditioned aggregates to keep ready per depot. |
| **Geography** | India: one STU depot or division first, reached through CIRT Pune (ASRTU's technical arm) or directly through a depot. |

The two numbers that make this decision-value-first:
1. STUs held an average of 12,817 buses off the road on a typical day in 2021-22, plus 22,983 spare buses, against 130,104 buses held (STU-owned plus hired). That is about 9.9% off the road and 17.7% held as spares (computed from [CIRT-P&P] p.101).
2. They reported 164,139 breakdowns in the year [CIRT-P&P] p.117, about 450 a day (computed).

The capacity that has to absorb all this is about 80,900 workshop and maintenance staff, or 0.81 per bus [CIRT-P&P] p.141.

---

## 2. Why this is where decision value is largest

### 2.1 What the decision looks like (analysis, grounded in the sources cited)

Prioritisation under uncertainty creates value only when five conditions all hold. STU depot maintenance meets each of them.

| Condition for decision value | STU diesel-bus aggregates | Evidence |
|---|---|---|
| **A recurring, discrete timing decision with real alternatives** (act now, defer to the next window, or inspect) | Buses come back to the depot every day. Preventive maintenance is run as a "scheduled periodical maintenance course", and even the ITS-equipped KSRTC Mysore division bases preventive maintenance on ITS-recorded kilometres. | [CIRT-P&P] p.7 (fuel-measure text); [ASRTU-BP] KSRTC Mysore ITS case |
| **Capacity is the binding constraint** (bays, mechanics, parts) | 0.81 workshop/maintenance staff per bus; 12,817 buses off road on an average day; spare-part stock ranges from about 7 days to over 8 months of consumption across STUs. | [CIRT-P&P] p.141, p.101, p.201-205 |
| **Asymmetric consequences** (an on-road failure costs far more than a planned change) | A breakdown cancels scheduled kilometres; CIRT tracks cancelled km by cause, including "breakdown" and "want of bus". Scania's own cost model for a fleet component prices a missed failure at 200-500 against 7-10 for an unnecessary check. For the APS dataset the costs are 500 against 10. | [CIRT-P&P] p.102-103; [Scania-CX]; [UCI-APS] |
| **Many interchangeable units, so ranking is the real decision** | Large STUs run thousands of buses: KSRTC (Karnataka) has 8,352, MSRTC 16,058 and APSRTC 10,853, as on 31-10-2023. | [ASRTU-Fleet] PDF p.5 |
| **Life is genuinely uncertain, so calibrated intervals matter** | Reported aggregate lives vary widely. New engines last about 9-11 lakh km; reconditioned engines about 2.4-4.4 lakh km. Reconditioned FI pumps range from 1.62 to 3.46 lakh km depending on the STU and make. | [CIRT-P&P] p.152-153 |

**What changes with SentinelLoop (analysis).** Today the depot reacts to breakdowns and follows kilometre-based schedules. With SentinelLoop, every bus would carry a calibrated probability of an aggregate failing before its next docking. The depot could then spend its limited mechanic-hours and reconditioned aggregates on the buses with the highest expected avoided cost, and the central workshop could size its aggregate pool against a forecast. This is exactly the use for which R2 found that success depends on decision-led rather than data-led design (Golightly et al. 2018) [R2].

### 2.2 The decision is cost-asymmetric, according to the data owner itself

- **SCANIA Component X.**
  - **Cost model.** The paper defines five validation and test classes by time before failure: more than 48, 48-24, 24-12, 12-6 and 6-0 time steps. Its cost matrix charges 200-500 for predicting too late and 7-10 for predicting too early.
  - **Motivation.** The authors motivate the dataset by maintenance strategy, resource allocation and fleet management. They note that a missed failure can mean a breakdown or "costly adjustments to the transportation plan" [Scania-CX].
  - **Status of the costs.** These are challenge costs set by Scania, not measured economics.
- **UCI APS Failure at Scania Trucks.** An unnecessary workshop check costs 10 and a missed faulty truck costs 500 [UCI-APS].
- **Analysis.** Both are real field datasets whose publisher has already written down the decision cost. That is rare, and it lets SentinelLoop be evaluated on decision cost rather than RMSE. R3 found no vendor that publishes interval coverage or calibration, so decision-cost reporting is a credible way to stand apart [R3].

### 2.3 Indian STU facts (real field administrative statistics, self-reported by STUs and compiled by CIRT)

**Source.** "State Transport Undertakings: Profile and Performance 2021-22", Central Institute of Road Transport (CIRT), Pune, published July 2024, hosted by ASRTU [CIRT-P&P].

**Fleet.**
- STUs owned 126,541 buses as on 31 March 2022.
- CIRT says STUs cannot replace buses in time, mainly for lack of funds (p.8).

**Utilisation (reporting STUs, 2021-22; p.101).**
- Average buses held: 115,113 STU-owned plus 14,991 hired.
- Off road: 12,817. Spare: 22,983. On road: 94,204.
- Fleet utilisation: 72.4% (rural 72.3%, hill 85.5%, urban 69.5%).
- Nine STUs were below 60% (p.8).

**Reliability (p.117).**
- 164,139 breakdowns in total: 39,799 rural, 532 hill and 123,808 urban.
- Published rate: 0.17 per 10,000 effective km (rural 0.05, hill 0.06, urban 0.95).
- **Data-quality caution (computed).** The counts and rates do not reconcile exactly. Dividing urban breakdowns by urban effective km (10,167.21 lakh km, p.101) gives about 1.22 per 10,000 km, not 0.95. Breakdown definitions and reporting also probably differ between STUs (analysis).

**Maintenance staff (p.141).**
- 80,900 workshop and maintenance staff, 0.81 per bus, out of 588,177 total staff.

**Cancelled km by cause (pp.102-103).** CIRT tracks cancellations by cause: want of crew, want of bus, breakdown, accident and other.
- Karnataka SRTC: of 484.33 lakh cancelled km, 9.32 lakh were for want of bus and 1.65 lakh for breakdown. "Other reasons" (420.04 lakh) dominated.
- **Honest counterpoint (analysis).** For this STU, cancellations caused by maintenance are a small share of all cancellations. Most of the decision value probably lies in the off-road and spare-bus share (capital tied up) and in on-road reliability, not in cancelled km.

**Spare-part inventory, months-days of consumption on 31.3.2022 (pp.201-205).**

| STU | Spare-part stock |
|---|---|
| MSRTC | 6-02 |
| APSRTC | 1-03 |
| TSRTC | 1-29 |
| GSRTC | 3-24 |
| KSRTC (Karnataka) | 4-16 |
| NWKRTC | 5-02 |
| KKRTC | 8-11 |
| TNSTC Villupuram | 0-07 |
| TNSTC Kumbakonam | 3-04 |

Holdings range from about a week to over eight months of consumption. That spread points to parts planning without a demand forecast (analysis).

**Aggregate lives (p.152-153, columns for MSRTC, APSRTC and TSRTC).**
- New engines: about 9-11 lakh km. Reconditioned engines: about 2.37-4.43 lakh km.
- FI pump, new: about 5.7-8.5 lakh km. FI pump, reconditioned: about 1.0-3.5 lakh km.
- Gearbox: about 9-11 lakh km new and 3.5-4.5 lakh km reconditioned.
- Lives are reported separately by make (Tata, Leyland and others).

**Mixed fleets (real field administrative statistics) [ASRTU-Fleet].**
- Karnataka SRTC's 8,302 diesel buses on 31-10-2023: Tata 2,542, Ashok Leyland 3,975, Eicher 1,291, Volvo 365, Scania 74, Benz 20 and Corona 35. It also ran 50 Olectra e-buses (pp.56-57).
- Kalyana Karnataka RTC: Tata 977, Ashok Leyland 3,142, Eicher 704, Volvo 2 and Corona 17 (p.54).
- The national make-wise table lists 13 make categories, from Tata, Ashok Leyland, Eicher and Volvo down to "any other make". It counts 12,742 hired buses under GCC/NCC within a diesel grand total of 130,792.

**Spares procurement [ASRTU-RC] [ASRTU-VDRS].**
- ASRTU runs common rate contracts for Leyland and Tata bus spare parts. They cover about 15,000 items in 68 procurement groups, and tenders are invited once every four months for 12-13 groups.
- ASRTU's own pages give two inconsistent figures for annual member spending: about Rs 8,000 million on the rate-contract page and Rs 2,000 crore on the VDRS page.
- CIRT tests spare parts and runs training and research or consultancy work for STUs [ASRTU-About].
- **Analysis.** Replenishment through four-monthly tender cycles makes a forecast of aggregate demand worth having.

**Scale (ASRTU self-statements, mutually inconsistent).**
- 70 members (including 15 associate members), operating about 150,000 buses and carrying 70 million passengers a day [ASRTU-About].
- Elsewhere: 62 STUs and 1.47 lakh buses [ASRTU-VDRS].

**Digital maturity signals.**
- Even after an ITS rollout, KSRTC Mysore reports preventive maintenance based on ITS-recorded kilometres, with savings of Rs 2.19 lakh on lubricants and filters [ASRTU-BP].
- The same compendium cites the VEMAS software for spotting low-KMPL vehicles [CIRT-P&P] p.7.
- Neither source describes condition-based or capacity-aware maintenance prioritisation.

### 2.4 General maintenance evidence that applies here [R1]
- **Parts delays.** CMMS work orders encode waiting states explicitly (Maximo WMATL "waiting on material", WSCH "waiting to schedule"). In a practitioner case, at least 10% of kits marked complete were missing parts, and parts sat for at least two weeks between arrival and execution [R1: IBM support page; Assetivity case].
- **Priority by pressure, not logic.** Priority is often set by "who yells loudest". Formal criticality-by-urgency matrices such as RIME exist to replace that. In one single-site case, enforcing RIME raised schedule compliance from 63% to 77% [R1: Reliabilityweb].

---

## 3. Why incumbents are weakest here

| Incumbent type | What it does (sourced) | Where it falls short for STU depot aggregate decisions |
|---|---|---|
| **OEM telematics**, e.g. Tata Motors Fleet Edge | Trip planning, track and trace, vehicle health with fault-code details, service history, driving scorecards. Lite plan Rs 1,095 a year, Prime Rs 4,015 a year. Claims 7 lakh+ vehicles (vendor claim) [FleetEdge]. | The page describes no predictive maintenance, workshop scheduling, spare-parts planning or mixed-make support. Karnataka SRTC runs at least seven makes [ASRTU-Fleet], so a single-OEM portal covers part of the fleet at most (analysis). Fleet Edge export or API options are **UNVERIFIED**. |
| **Fleet predictive-maintenance vendors**, e.g. Uptake Fleet (Bosch acquisition announced 19 Mar 2026; completion UNVERIFIED [R3]) | Sensor insights, a "Risk Explorer" to prioritise, remote diagnostics, warranty recovery and a mixed-fleet data hub. Covers buses, heavy and medium trucks, and mining equipment [Uptake]. | Its named connectors (Platform Science, Trimble, CalAmp, Intellishift) are telematics providers. The page does not mention India, work orders, parts or scheduling [Uptake]. Whether Uptake operates in India is **UNVERIFIED**. This is the strongest direct competitor, and it does prioritise risk. |
| **Plant PdM/APM vendors** (Augury, Tractian, KCF, SmartSignal, Senseye, Infinite Uptime, Presage) | Sensor-plus-analytics or historian-based APM for fixed plant assets [R3]. | They are built around plant historians or their own sensors on rotating plant equipment. None opened in R3 targets road-bus aggregates [R3]. Analysis: they are not present in this vertical. |
| **CMMS / fleet-maintenance software** (Odoo Fleet, Fleetio, MaintainX and others) | Odoo Fleet (LGPL-3) records vehicles, services with odometer, cost, vendor and state, and costs by vehicle [Odoo-Fleet] [Odoo-Fleet-Svc]. Commercial CMMSs auto-create work orders from meter or condition alerts [R3]. | Kilometre or time-triggered PM and rule-based alerts only. No calibrated failure probability and no capacity-constrained ranking is described [R3] [Odoo-Fleet]. The Fleetio page returned 403, so its features are **UNVERIFIED**. |
| **STU in-house practice and ITS** | Kilometre-based PM courses, KMPL monitoring software (VEMAS), ITS MIS reports covering breakdowns and missed trips [CIRT-P&P] [ASRTU-BP]. | Records lives and breakdowns but does not forecast them per bus (analysis, based on what these documents describe). |
| **OEM annual maintenance contracts and gross-cost-contract (GCC) operators** | ASRTU notices show e-bus procurement with "Operation and Maintenance" under GCC (MTC Chennai, 220 e-buses) and a 10-year AMC (UPSRTC) [ASRTU-Home]. Tata Motors lists a "Fleetcare" service [FleetEdge]. | Where maintenance is outsourced, the operator or OEM owns the decision. That segment is **excluded** from this proposal. The in-house diesel segment is where the STU itself decides. |

**Net assessment (analysis).** For mixed-make, in-house-maintained diesel STU fleets in India, no product among those opened sits between kilometre-based PM, single-make OEM fault codes and the depot's daily pull decision. The closest functional rival is Uptake's Risk Explorer, which on its own page shows no India presence and no work-order or parts scheduling. Absence from a marketing page does not prove a product lacks the capability.

---

## 4. Candidates compared on decision value (analysis; facts cited per cell)

Scores run from 1 (weak) to 3 (strong). The scoring is mine; the facts in the cells are cited.

| Candidate (vertical, asset) | Recurring constrained decision | Cost asymmetry | Many interchangeable units | Incumbent weakness | Real public data for the decision | Reachable by a student team | Total |
|---|---|---|---|---|---|---|---|
| **STU depots, diesel-bus powertrain aggregates (chosen)** | 3: daily pull and dock choice, 0.81 staff per bus [CIRT-P&P] | 3: breakdowns and cancelled km [CIRT-P&P]; Scania cost matrices [Scania-CX] [UCI-APS] | 3: thousands of buses per STU [ASRTU-Fleet] | 3: see section 3 | 2: Scania real field truck data with censoring, but no Indian per-bus data | 2: CIRT and depot route (section 7) | **16** |
| Metro rolling stock, train air-production units (MetroPT) | 3: overnight depot slots (UNVERIFIED for India) | 3 | 2: tens to hundreds of trainsets | 1: rolling-stock OEM and maintainer contracts (UNVERIFIED) | 2: real field, only 2-4 failures per release [R4] | 1 | 12 |
| Wind farms, turbine drivetrains (CARE, Kelmarsh) | 3: crane and weather windows (UNVERIFIED) | 3 (UNVERIFIED) | 2 | 1: OEM full-service contracts and SCADA analytics (UNVERIFIED) | 2: real anomaly labels, no RUL or work orders [R4] | 1 | 12 |
| Indian plants, rotating equipment (pumps, motors) | 2 | 2 | 2 | 1: sensor-bundled vendors including Indian ones [R3] | 1: only lab data or the anonymous Kaggle pump set [R4] | 2 | 10 |
| Long-haul truck fleets (India) | 2: workshop visits | 3 [Scania-CX] | 3 | 2: OEM telematics [FleetEdge]; Uptake [Uptake] | 3: Scania Component X and APS [R4] | 1: fragmented owners (UNVERIFIED) | 14 |
| Turbofans (current C-MAPSS asset) | 3 | 3 | 2 | 0: OEM pay-per-flight-hour contracts include health monitoring [R3] | 0: simulated only [R4] | 0 | 8 |
| Data-centre hard drives (Backblaze) | 1: hot-swap, redundancy (analysis) | 1 | 3 | 2 | 3: real field, very large [R4] | 1 | 11 |

Trucks score close. They are kept as the **data analogue** and the first expansion, not the initial vertical. Indian truck fleet ownership is not sourced, and no single reachable owner with a depot workshop was identified.

---

## 5. Public real data available for this pair

| Dataset | Type | Use for this pair | Licence / access | Source |
|---|---|---|---|---|
| SCANIA Component X (v3) | **Real field** (trucks, anonymised engine component) | Primary sim-to-real test: time-to-repair with censoring (2,272 repaired, 21,278 censored in train), 5-class proximity labels and Scania's cost matrix for decision-cost evaluation | CC BY 4.0, about 1.65 GB, direct download | [R4]: researchdata.se; [Scania-CX] |
| APS Failure at Scania Trucks (UCI) | **Real field** (truck air-pressure system, which supplies braking and gear changes) | Cost-weighted triage-threshold test with costs of 10 (false positive) and 500 (false negative); snapshots, no time index | CC BY 4.0, 54 MB | [UCI-APS]; [R4] |
| CIRT Profile and Performance 2021-22 | **Real field administrative statistics** (aggregate, self-reported by STUs) | Priors and sanity checks: aggregate lives by make, breakdown rates, off-road and spare shares, inventory months, staff per bus | Copyright CIRT, all rights reserved; cite figures only | [CIRT-P&P] |
| ASRTU Fleet Handbook 2024 | **Real field administrative statistics** | Fleet size, make mix and fuel mix per STU, used to size the pilot and the mixed-make problem | Published by ASRTU | [ASRTU-Fleet] |
| MetroPT-3 / MetroPT / MetroPT2 | **Real field** (rail compressed-air unit, 2-4 failures per release) | Secondary: anomaly-index and drift checks on a vehicle compressed-air system; too few events for accuracy claims | CC BY 4.0 | [R4] |
| Backblaze Drive Stats | **Real field** (IT hardware) | Scale and calibration stress test of conformal-under-censoring code only | Custom open terms | [R4] |
| NASA C-MAPSS | **Simulated** | Current development data only; no claims | No licence stated | [R4] |

**Not available publicly (gap).** Per-bus Indian data: job cards, aggregate-change registers, breakdown logs or telematics. None was found, and none was searched for in this stream because WebSearch was unavailable. This is **UNVERIFIED** absence. A pilot partner has to supply it (section 7).

---

## 6. Fit with the current system

**Strong fit.**
- The project already frames itself as "Predictive Maintenance for a Connected Fleet" (README).
- Its design question is the decision every fleet operator faces per unit: do nothing, watch, schedule, stop now, or send a human (docs/SYSTEM_DESIGN.md).
- Several existing pieces carry over directly:
  - the calibrated 90% interval;
  - the deterministic Triage Agent with human escalation;
  - the policy-replay harness, which scores late-order rate and discarded life against history;
  - the promotion gate;
  - the hash-chained audit log.
- A bus fleet is many similar units that come back to one depot, which matches the C-MAPSS population structure.

**Gaps.**
- SentinelLoop has never seen real data.
- It models cycles, not kilometres or calendar time.
- It has no censoring-aware model. The C-MAPSS training engines all run to failure, and docs/KNOWN_LIMITATIONS.md item 2 treats test truncation only as an evaluation problem.
- Its replay assumes a work order is acted on immediately, with no lead times or scheduling constraints (KNOWN_LIMITATIONS item 12). That is exactly the assumption this vertical breaks.
- Its fleet-level rule escalates 25-36% of healthy units while a fleet alarm is active (README). At depot scale that would be a flood. R1 warns that escalations compete with operators' alarm budgets [R1].

---

## 7. Pilot access path (concrete, free, no customer access today)

1. **Weeks 0-6, no access needed.** Re-run the pipeline on SCANIA Component X as a time-to-event problem. Report:
   - interval coverage under censoring on the official validation and test splits;
   - Scania's cost-matrix score against a kilometre-style (time-step) fixed-interval baseline;
   - the same for APS with costs of 10 and 500.

   Publish this as the product's first real-field evidence. It is still trucks, not Indian buses.
2. **First contact: CIRT Pune**, ASRTU's technical arm, which runs research and consultancy work and training for STUs [ASRTU-About]. CIRT's publications list a data contact (databank@cirtindia.com) [CIRT-P&P]. Propose a free, read-only back-test study: 2-3 years of anonymised aggregate-change registers, breakdown logs and docking records from one or two depots. The output would be a report on how many breakdowns a capacity-limited pull list would have pre-empted. Whether CIRT accepts student collaborations is **UNVERIFIED**.
3. **Parallel contact: one depot or division of an STU near the team.** Karnataka SRTC, BMTC and MSRTC are among the largest by fleet [ASRTU-Fleet]. Approach the divisional mechanical engineer or depot manager with the same read-only offer. Then run 8-12 weeks in **shadow mode**: a weekly pull list and an aggregate-demand forecast, compared with what actually happened. There is no write access to any system, no vehicle CAN/OBD connection and no OT exposure. Data would be spreadsheet or register exports. Whether depot records are digital is **UNVERIFIED**.
4. **Paid pilot route, later.** STUs buy through GeM, as ASRTU notices for UPSRTC tenders and GeM supplies show [ASRTU-Home]. DPIIT-recognised startups can claim EMD, turnover and experience relaxations through GeM Startup Runway and CPPP [R2: startupindia.gov.in].
5. **Integration target for the pilot.** A self-hosted Odoo Community instance running the Fleet module (LGPL-3; vehicles, services with odometer, cost and state) [Odoo-Fleet] [Odoo-Fleet-Svc] and the Maintenance module (maintenance.request with priority 0-3) [R5]. Both are free and need no vendor sandbox.

---

## 8. What must change in the system

1. **Time base and target.** Move from cycles to kilometres or operating time. Replace run-to-failure RUL regression with a time-to-event model that handles right-censoring (Scania's `in_study_repair` and `length_of_study_time_step`), and add a conformal interval method that is valid under censoring.
2. **Features from records, not dense sensors.**
   - Ingest irregular, sparse inputs: Scania's histograms and counters [R4]; depot job cards, aggregate-change dates and km, make, model and emission norm, route type, and breakdown logs.
   - Make the age-matched drift monitor work on kilometre-age.
3. **A capacity- and parts-constrained decision layer** (the core change).
   - Replace per-unit thresholds and one open order per unit with a nightly ranking: P(aggregate failure before next docking) × consequence. Consequence can be proxied by route type and spare-bus availability.
   - The ranking is solved subject to the depot's mechanic-hours, bays and reconditioned aggregates on hand.
   - Outputs: a pull list with evidence, a deferral list with risk, and an aggregate-demand forecast for the central workshop.
   - This also removes the "acted on immediately" replay assumption (KNOWN_LIMITATIONS item 12).
4. **Decision-cost evaluation.**
   - Score policies with Scania's cost matrix and the APS 10/500 costs, plus a parametrised depot cost model (breakdown, tow, cancelled km and an off-road day against an early change). The real Indian costs are **UNVERIFIED**.
   - Back-test against the kilometre-based PM baseline the STUs use [ASRTU-BP].
5. **Mixed-make calibration.** Use make and model as covariates and report coverage per make (Mondrian/group-conditional conformal). CIRT shows that lives differ by make [CIRT-P&P].
6. **Escalation budget.** Cap human escalations per depot shift. Redesign the fleet-level rule, which escalated 25-36% of healthy units, so that a fleet alarm triggers a data-quality check rather than mass escalation.
7. **Integration and safety.**
   - Write only to a CMMS or fleet module, starting with Odoo Fleet and Maintenance.
   - Never write to vehicle ECUs or telematics.
   - Import CSVs from registers.
   - Pseudonymise mechanic and driver identities in the audit chain, because DPDP treats them as personal data [R5].
8. **Remove turbofan-specific logic.** C-MAPSS operating-regime normalisation and the RUL cap of 125 become configurable or are dropped.

---

## 9. Biggest risks

1. **No per-bus Indian data in hand.** Depot records may be paper registers with missing or wrong fields. R1 shows this is common in real CMMS data [R1: Hodkiewicz & Ho; Lukens et al.]. The first pilot may be mostly data cleaning.
2. **Transfer gap.** Scania Component X is anonymised truck data (histograms and counters, irregular sampling) [R4]. Good results there do not show performance on Indian buses.
3. **Low ability to pay and slow procurement.** CIRT describes STUs as in "severe financial crunch" and unable to replace buses for lack of funds [CIRT-P&P] p.8-9. Public procurement cycles are long (analysis).
4. **The segment may shrink.** New e-buses are increasingly procured under GCC operation and maintenance or 10-year AMCs, which move the maintenance decision to operators and OEMs [ASRTU-Home]. 12,742 diesel buses were already hired under GCC/NCC [ASRTU-Fleet].
5. **Noisy outcome measures.** Breakdown definitions and reporting vary: rates differ 19-fold between urban and rural, and counts and rates do not reconcile (computed, section 2.3). Maintenance causes are a small share of cancelled km at Karnataka SRTC [CIRT-P&P]. Value may have to be shown in off-road days and spare-bus share, which are harder to attribute to the tool.
6. **Incumbents can close the gap.** OEM telematics already collects fault codes and service history [FleetEdge]. Uptake already offers risk prioritisation for buses and trucks, and Bosch's planned ownership could bring it to India [Uptake] [R3].
7. **Labour relations and personal data.** Pull lists implicitly rate mechanics' and drivers' work. Under DPDP, technician identities are personal data [R5]. How unions would react is **UNVERIFIED**.
8. **System behaviour at depot scale.** The current fleet rule's escalation volume and the instability of tuned lower-bound thresholds across seeds (README E1) would be visible to depot staff immediately.

---

## 10. Alternatives rejected

| Option | Reason rejected |
|---|---|
| Turbofan engines (the current C-MAPSS asset) | OEMs sell health monitoring inside pay-per-flight-hour contracts (Rolls-Royce TotalCare, GE TrueChoice) [R3]. All data is simulated [R4]. |
| Indian manufacturing plants, rotating equipment (pumps, motors, fans) | Incumbents bundle sensors, field data and analysts, Indian ones included (Infinite Uptime, Presage) [R3]. No public field data with work orders exists, only lab rigs and an anonymous Kaggle pump set [R4]. The team has no hardware. |
| Wind farms, turbine drivetrains | The decision value is high, but the public real data has anomaly labels only, with no RUL or work orders (CARE to Compare, Kelmarsh, Hill of Towie) [R4]. OEM service and SCADA-analytics incumbency in India is **UNVERIFIED**, and the Suzlon pages returned no service content or HTTP 500. |
| Metro rolling stock, air-production units (MetroPT) | Only 2-4 failure events per release [R4]. There are few units per operator. Rolling-stock maintenance contracts and OEM digital services are likely incumbents (**UNVERIFIED**). Access is hard for a student team. |
| E-bus fleets under GCC/AMC | The maintenance decision belongs to the operator or OEM under the contract [ASRTU-Home], not to the STU. |
| Long-haul truck fleets in India | The best data fit (Scania) [R4], but ownership structure and depot workshops are unsourced (**UNVERIFIED**). OEM telematics already reaches owners [FleetEdge]. Kept as the first expansion. |
| Data-centre hard drives (Backblaze) | Real and large [R4], but not industrial maintenance. Redundancy and hot-swap make deferral cheap (analysis), so prioritisation changes little. |
| Offshore oil wells (Petrobras 3W) | Labels are mostly process and flow-assurance events, not maintenance [R4]. Inaccessible to the team. |

---

## 11. Gaps and UNVERIFIED items

- **WebSearch was unavailable** (shared budget exhausted). I could not search for:
  - CAG audit reports on STU maintenance;
  - MoRTH's "Review of Performance of SRTUs" (morth.gov.in is a JavaScript single-page app that returned only a shell);
  - Indian bus-telematics and ITMS vendors' maintenance features;
  - Ashok Leyland iAlert features (the URL redirected to the home page);
  - Indian truck fleet structure;
  - PM e-Bus Sewa contract terms.
- **Pages that failed:**
  - Fleetio (403);
  - tatamotors.com/fleet-edge (403; the fleetedge.tatamotors.com page worked);
  - Suzlon service page (500);
  - ASRTU "Standing Committee IT" PDF (larger than 10 MB).
- **Unknown about depots:** whether STU depot records (job cards, aggregate registers) are digital, and in what system. The breakdown definitions used by CIRT.
- **Unknown costs:** the real rupee cost of a breakdown, a tow, a cancelled km or an off-road day for an STU. None was found, so the depot cost model must be elicited in the pilot.
- **Uptake:** completion of the Bosch acquisition [R3] and any India presence.
- **Fleet Edge:** whether it has a data export or API.
- **Unconfirmed reach:** CIRT's willingness to host a student back-test study, and the responsiveness of its data contact.
- **Parsing caution:** CIRT and ASRTU figures were extracted from PDF text. Values quoted are from rows whose column alignment I checked. Some STU-level cancelled-km columns (UPSRTC and GSRTC) were ambiguous and are not used.

---

## Sources

All accessed 2026-10-18. "Opened" means fetched in this session with WebFetch, or with curl for HTML pages and PyMuPDF/pdftotext on the PDFs WebFetch saved.

**Opened in this session**
- [CIRT-P&P] Central Institute of Road Transport, "State Transport Undertakings: Profile and Performance 2021-22" (July 2024), hosted by ASRTU: https://www.asrtu.org/resource/front/uploads/PROFILE_PERFORMANCE-2021-22.pdf (pp.7-9 overview; p.101 utilisation of fleet; pp.102-103 STU-level utilisation and cancelled km; p.117 quality of service; p.141 manpower; pp.152-153 aggregate lives; pp.201-205 inventory position)
- [ASRTU-Fleet] ASRTU, "SRTU Fleet Handbook-2024 (Make wise & Type wise)", fleet as on 31-10-2023: https://www.asrtu.org/resource/front/uploads/STUs%20Fleet%20Book%202024.pdf
- [ASRTU-BP] ASRTU, Best Practices manual (KSRTC Mysore ITS case): https://www.asrtu.org/resource/front/uploads/Best-Practice.pdf
- [ASRTU-Home] ASRTU home page (latest notifications: GeM tenders, GCC e-bus O&M, 10-year AMC, rate contracts): https://www.asrtu.org/
- [ASRTU-About] ASRTU at a Glance: https://www.asrtu.org/page/about
- [ASRTU-RC] ASRTU Rate Contracting: https://www.asrtu.org/service/rate
- [ASRTU-VDRS] ASRTU Vendor Development Registration Scheme: https://www.asrtu.org/service/vdrs
- ASRTU download section (document index): https://www.asrtu.org/download
- [Scania-CX] Kharazian et al., SCANIA Component X dataset paper (arXiv v1, HTML): https://arxiv.org/html/2401.15199v1
- [UCI-APS] UCI, APS Failure at Scania Trucks: https://archive.ics.uci.edu/dataset/421/aps+failure+at+scania+trucks
- [Uptake] Uptake home page: https://uptake.com/
- [FleetEdge] Tata Motors Fleet Edge: https://fleetedge.tatamotors.com/
- [Odoo-Fleet] Odoo 19 Fleet module manifest: https://raw.githubusercontent.com/odoo/odoo/19.0/addons/fleet/__manifest__.py
- [Odoo-Fleet-Svc] Odoo 19 fleet.vehicle.log.services model: https://raw.githubusercontent.com/odoo/odoo/19.0/addons/fleet/models/fleet_vehicle_log_services.py
- Attempted, no usable content:
  - https://morth.nic.in/ (redirects to http://morth.gov.in/, a JavaScript shell)
  - https://www.fleetio.com/features/preventive-maintenance (403)
  - https://www.tatamotors.com/fleet-edge/ (403)
  - https://www.ashokleyland.com/en/ialert (redirected to home page)
  - https://www.suzlon.com/ (no O&M content)
  - https://www.suzlon.com/our-businesses/project-service-solutions/ (500)
  - https://www.asrtu.org/resource/front/uploads/Standing%20Committee%20IT.pdf (over 10 MB)

**From the research streams, opened by R1-R5 (cited as [R1]-[R5])**
- [R1] IBM Maximo statuses: https://www.ibm.com/support/pages/node/1112013 ; Assetivity parts case: https://www.assetivity.com.au/articles/asset-management/coordinating-activity-between-maintenance-and-supply-a-case-study/ ; RIME: https://reliabilityweb.com/en/articles/ranking-index-for-maintenance-expenditures ; priority by emotion: https://reliabilityweb.com/articles/entry/work_prioritization_emotion_vs._logic ; Hodkiewicz & Ho 2016: https://www.emerald.com/insight/content/doi/10.1108/JQME-04-2015-0013/full/html ; Lukens et al. 2019: https://papers.phmsociety.org/index.php/phmconf/article/download/836/phmc_19_836 ; alarm benchmarks: https://www.icheme.org/media/17392/lc-0151_21-lead-process-safety-metrics-alarm-rationalisation-final.pdf
- [R2] Golightly et al. 2018: https://ideas.repec.org/a/spr/infsem/v16y2018i3d10.1007_s10257-017-0343-1.html ; Startup India procurement: https://www.startupindia.gov.in/content/sih/en/public_procurement.html
- [R3] Rolls-Royce TotalCare: https://www.rolls-royce.com/products-and-services/civil-aerospace/services/totalcare.aspx ; GE TrueChoice: https://www.geaerospace.com/commercial/services/true-choice/flight-hour ; Bosch-Uptake: https://www.trucknews.com/technology/bosch-to-acquire-uptake-technologies-to-boost-predictive-maintenance-capabilities/1003211395 ; Infinite Uptime: https://www.infinite-uptime.com/about-us ; Presage Insights: https://www.industrialautomationindia.in/news/presage-insights-raises-5-6-crore-predictive-maintenance-india ; CMMS auto work orders: https://help.getmaintainx.com/about-automations
- [R4] SCANIA Component X: https://researchdata.se/catalogue/dataset/2024-34/3 ; MetroPT-3: https://archive.ics.uci.edu/dataset/791/metropt+3+dataset ; CARE to Compare: https://zenodo.org/records/15846963 ; Backblaze: https://www.backblaze.com/cloud-storage/resources/hard-drive-test-data ; NASA PCoE repository: https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/ ; Petrobras 3W: https://github.com/petrobras/3W
- [R5] Odoo maintenance model: https://raw.githubusercontent.com/odoo/odoo/19.0/addons/maintenance/models/maintenance.py ; DPDP Act 2023: https://prsindia.org/files/bills_acts/bills_parliament/2023/Digital_Personal_Data_Protection_Act,_2023.pdf

**Local files read (not web sources)**
- C:\Users\HP\OneDrive\Desktop\tata\README.md
- C:\Users\HP\OneDrive\Desktop\tata\FINAL_HANDOFF.md
- docs/SYSTEM_DESIGN.md
- docs/KNOWN_LIMITATIONS.md
- product/research/R1-R5
