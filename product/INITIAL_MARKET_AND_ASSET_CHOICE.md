# Initial market and asset choice (decision record)

| Field | Value |
|---|---|
| Date | 2026-10-18 |
| Written by | Technical writer, SentinelLoop product team |
| Status | **PROVISIONAL and GATED.** Not confirmed until gates G0 and G1 (section 7) pass. If G1 fails, the runner-up becomes the initial choice. |
| Inputs | Three proposals (DATA-FIRST, ACCESS-FIRST, DECISION-VALUE-FIRST), the judge's decision, and the adversarial review. The review's verdict was "reject as specified", with nine required changes. |
| Log entry | PD-10 in `product/DECISION_LOG.md`, recorded as PROVISIONAL and GATED. The team lead's decisions in section 12 are still open. |

**Labels used in this record**
- **[Sn]**: a source opened in this session (2026-10-18). The full list is in "Sources".
- **[Ln]**: a local project file read in this session.
- **UNVERIFIED**: not confirmed by any source opened in this session.
- **Vendor claim**: a statement taken from a vendor's own page.
- **Judgement**: reasoning, not a sourced fact.
- **Computed**: arithmetic run locally on figures from a cited source (Python, 2026-10-18).
- **PLANNED**: not done. Nothing in this record that describes work on real wind data or outreach has been done. Some of the system changes in section 9 have since been built; the implementation status note there says which.

**Data types.** **REAL FIELD** means measured on operating assets. **REAL LAB** means measured on a test rig. **SIMULATED** means produced by a physics or system model. **SYNTHETIC** means artificially generated or corrupted. **REAL FIELD ADMINISTRATIVE STATISTICS** means aggregate figures reported or estimated by an operator or a government body.

**Tool status.**
- WebSearch was unavailable. The one call made returned that the shared per-turn search budget was used up. No workaround was attempted, so nothing here comes from a search.
- WebFetch worked and was used only on primary or already known URLs.
- WebFetch returned five PDFs as binary and saved them: the IEA Wind EDP summary, the NIWE notice, the MNRE policy, the CIRT profile and the India Cooling Action Plan. Text was extracted locally with `pdftotext`.
- The MNRE policy is a scanned image. Its pages were rendered with `pdftoppm` and read visually.
- **Fact-check pass (2026-10-18).** A separate fact-check re-opened 37 of the 39 web sources (all except [S8], which returned 403 before, and [S11]) with WebFetch (PDFs extracted locally, the MNRE scan re-rendered and read). Corrections made are listed in "Fact-check log" at the end of this record.

---

## 1. Decision at a glance

**Read this first.**
1. The judge chose wind [L6]. The adversarial review rejected that choice as specified and listed nine required changes [L7]. This record applies all nine.
2. Two of those changes lower wind's scores: data from 4 to 3, and decision value from 4 to 3. After them, **wind no longer wins the score table.** Buses lead 25 to 24 under the judge's weights and 19 to 17 unweighted. Under the recorded scores, wind leads under none of the five weightings tested (computed, section 4).
3. Wind is still the initial choice, but only provisionally and for a fixed gate period of about four weeks, for two reasons:
   - The review's required changes set out conditions under which wind may be kept [L7 §7].
   - The two tests of those conditions are cheap. G0 is a falsification test on public data, which the review requires whatever vertical is chosen. G1 is an access test of 3-5 conversations.

   If G1 fails, the team switches to the runner-up. If G1 passes, the scores that are now uncertain (access, decision value) get evidence (section 7).
4. **Decision for the team lead.** Either keep the four-week wind gate or switch to the runner-up now, given the corrected table. This record does not make that call (section 12).

| | Recorded choice |
|---|---|
| **Vertical** | Onshore wind power generation in India. The target is the party that runs recurring maintenance on mid-life turbines and controls their SCADA history. Candidate types are an independent power producer's (IPP) asset-management team and an independent O&M provider. Which type, and whether either will share data, is **UNVERIFIED**; gate G1 decides. |
| **Asset class** | Geared onshore turbines of about **2.0-2.3 MW**, past commissioning but not repowering candidates under MNRE's 2023 policy. That policy makes turbines "below 2 MW" eligible [S16 p.2]. They are monitored only through existing 10-minute SCADA, alarm and event logs, and a failure or work-order log. No new hardware. Targets are faults visible in SCADA: the drivetrain (gearbox and its bearings, generator) and transformer over-temperature. The CARE record's version notes name events described as "gearbox bearing damage" (event 51, Farm A) and "high temperature in transformer cell" (events 34, 7 and 19) [S1]. |
| **Geography** | Customers in India, where installed wind capacity is 59,201.07 MW as on 30.09.2026 [S15]. **No first state is fixed.** No source opened gives the 2.0-2.3 MW fleet by state; MNRE's state table covers only turbines below 2 MW [S16 pp.1-2]. Tamil Nadu is not chosen on fleet grounds (objection 3, section 6). The validation data are European (Portugal, German offshore, UK) [S1][S3][S4][S5]. No Indian turbine SCADA is public [S18]. |
| **Decision the product would support** | **What the product computes today** (SYNTHETIC data only):<br>• advisory anomaly flags per turbine (INSPECTION_RECOMMENDED, URGENT_REVIEW) on drivetrain temperatures, with policy-default due dates;<br>• within a priority class, an anomaly-ranked order (deviation ratio × consequence / (duration × crew)), labelled "not a probability" (`src/sentinelloop/app/decision.py`).<br>The wind model gives no remaining life and no failure probability (PD-11). Transformer temperature is not modelled.<br>**Hypotheses, UNVERIFIED and not computed by the product:**<br>• a weekly inspection list under an explicit technician and **crane** budget. The scheduler has technicians, skills, shifts, parts and maintenance windows, but no cranes, weather or climbing-wind limits (`KNOWN_LIMITATIONS.md` P8);<br>• a controlled false-alarm rate. The thresholds are policy choices with no nominal rate (M4), chosen on synthetic data only. Fresh held-out synthetic fleets gave 0.44 healthy alarm episodes per turbine-year, but the 95% interval runs up to about 2.45, so the proposed pilot ceiling of 2 is not excluded; an earlier run's setting (sustain 6) gave 5.74, so the rate is sensitive to persistence; drifting, not failing, sensors still raised 39 alarm episodes on the fresh fleets (`KNOWN_LIMITATIONS.md` E7, M1);<br>• a deferral list with stated risk. Deferral exists, but no risk can be stated without a failure probability.<br>G1 must find a party that confirms it makes this decision. |
| **Product message in this vertical** | "Advisory anomaly flags for inspection, with auditable triage". It is not "calibrated early warning": the alarm thresholds are tuned on synthetic data and are not calibrated (`KNOWN_LIMITATIONS.md` M4). It is not "RUL with a 90% interval" either. RUL has not been validated on any wind data and remains a SIMULATED C-MAPSS result [L1][L3]. |
| **Primary validation data** | CARE to Compare v6 (Fraunhofer IEE): REAL FIELD, CC BY-SA 4.0, https://zenodo.org/records/15846963 [S1]. The in-class labelled part is **Farm A only**: 5 onshore turbines in Portugal, 11 anomaly events and 11 normal datasets per the paper [S2]. |
| **Runner-up** | Indian State Transport Undertaking (STU) depots, diesel-bus powertrain aggregates (section 10). |

**What changed compared with the judge's decision**

| Item | Judge [L6] | This record | Basis |
|---|---|---|---|
| Turbine band | 1.5-2.3 MW | 2.0-2.3 MW geared, mid-life | Review change 2, option (b) (see below) |
| Target owners | Ageing owners eligible for repowering or life extension | The party running maintenance on mid-life turbines and holding their SCADA | Review §3.1 (end-of-life objection) |
| Geography | Tamil Nadu first | India; first state open until G1 | Review change 3 |
| Decision supported | Policy-backed repowering and life-extension assessment | Inspection ranking under a technician and crane budget (UNVERIFIED hypothesis; the scheduler has no crane resource) | Review change 4 |
| NIWE | "Institutional door" | Optional internship with publication and data restrictions | Review change 5 |
| Access test | Later switch condition; 12-month export gate | First gate; at least 3 years of SCADA plus a failure or work-order log | Review change 6 |
| Data score | 4 | 3 | Review change 1 |
| Decision-value score | 4 | 3 | Review change 4 |

**Choice made by this record where the review offered two options (to be confirmed by the team lead).** Change 2 offered two ways to fix the band:
- (a) target "below 2 MW" turbines and admit that no public labelled data match them; or
- (b) target 2-2.3 MW geared fleets and drop the repowering-eligibility hook.

This record takes **(b)**, for three reasons:
1. It matches the rating of the public CC BY sets. Kelmarsh and Penmanshiel come to 2.05 MW per turbine (computed from farm capacities read from KMZ file names on the record pages) [S4][S5]. Hill of Towie uses the Siemens SWT-2.3-VS-82 [S3].
2. An early warning is worth more on a turbine with years of service ahead than on a candidate for scrapping (judgement, following the review [L7 §3.1]).
3. Option (a) would sell into decisions that do not use condition data. The policy's indicative valuation model uses generation, tariff, O&M expense, discount rate, decommissioning cost and scrap income, and no component condition [S16 p.10]. Life extension is "assessed and certified by the certification agency" under UL 4143 [S16 p.3].

The cost of (b): no verified figure describes the size, state distribution, model mix or gearbox share of India's 2.0-2.3 MW fleet (**UNVERIFIED**).

---

## 2. What this record does not claim

- **No market size is claimed.** This record states no TAM, SAM, SOM, revenue, price, willingness to pay, number of target turbines or number of target companies in India.
  - Two Indian figures are quoted: the national installed wind capacity [S15], and MNRE's state table for turbines below 2 MW [S16].
  - The table is used only to show why the sub-2 MW framing and the Tamil Nadu start were dropped.
- **No customer has been contacted.** No owner, IPP, O&M provider, OEM, certification body, NIWE, CIRT, STU or campus estate office has been contacted by the team for this work. Every outreach step in this record is PLANNED.
- **No SentinelLoop result on real wind data exists.** CARE and the other wind datasets have not been downloaded, and no model has been run on them. The wind anomaly model is IMPLEMENTED_AND_TESTED on SYNTHETIC SCADA from our own generator only (`product/evidence/wind_synthetic/w1.md`, `w2.md`, `w3.md`). Those runs are behaviour checks, not performance evidence (`KNOWN_LIMITATIONS.md` E3). No wind capability is validated on real data.
- **All existing SentinelLoop results are on SIMULATED NASA C-MAPSS data or SYNTHETIC wind data.** The stress tests inject SYNTHETIC faults into simulated engines. "No real sensor, real asset, real maintenance record or real user has ever touched the system" [L3].
- No competitor capability is asserted beyond what the competitor's own page says. Those statements are labelled vendor claims.

---

## 3. How the decision was made

1. Five research streams (R1-R5) surveyed maintenance workflows, adoption failures, competitors, datasets and integration standards. They live in `product/research/`.
2. Three independent proposals were written, each from one angle:
   - DATA-FIRST: wind [L8];
   - ACCESS-FIRST: campus chilled-water plants [L9];
   - DECISION-VALUE-FIRST: STU bus depots [L10].
3. A judge scored the three proposals and chose wind, narrowed and combined with elements of the other two [L6].
4. An adversarial reviewer attacked the choice and rejected it as specified, with required changes [L7].
5. This record applies the required changes, re-states the scores, defines the gates, and lists what remains UNVERIFIED.
   - Every external fact in it was re-opened in this session; see "Sources".
   - Where this record's check differs from an earlier file, this record says so.

---

## 4. Scoring of the three proposals

**Scale.** 1-5 per criterion. For competition, 5 means least crowded. For regulatory burden, 5 means lightest. The scores are the judge's [L6], except where the review's required corrections apply [L7]. Sums are computed.

| Option | Data | Access | Decision value | Technical fit | Competition | Regulatory | Sum (equal) | Sum (data and fit ×2) |
|---|---|---|---|---|---|---|---|---|
| A. Wind, judge's scores | 4 | 2 | 4 | 4 | 2 | 3 | 19 | 27 |
| **A. Wind, recorded (review changes 1 and 4 applied)** | **3** | **2** | **3** | **4** | **2** | **3** | **17** | **24** |
| A. Wind, sensitivity: access also 2→1 (review §5) | 3 | 1 | 3 | 4 | 2 | 3 | 16 | 23 |
| B. Campus chilled-water plants | 1 | 4 | 2 | 2 | 3 | 5 | 17 | 20 |
| C. STU bus-depot powertrain aggregates | 3 | 2 | 4 | 3 | 4 | 3 | 19 | 25 |

**Why each cell, in brief** (evidence detail in sections 5, 6 and 10)

| Option | Main evidence behind the scores |
|---|---|
| A. Wind | **Data 3.** REAL FIELD, commercially licensed, 10-minute SCADA: CARE (CC BY-SA 4.0) [S1], and Hill of Towie, Kelmarsh and Penmanshiel (CC BY 4.0) [S3][S4][S5]. But the in-class labelled evidence is only CARE Farm A: 11 events, 5 turbines, rating not stated [S2]. The CC BY sets carry no failure labels [S3][S4][S5]. **Access 2.** No verified door to any party holding Indian turbine SCADA. NIWE's internship is real but leads into NIWE's projects [S17]. **Decision value 3.** No party has confirmed a SCADA-driven decision; the policy's decisions do not use condition data [S16]. **Fit 4.** The healthy-baseline index, regime normalisation, drift and gated retraining carry over; RUL does not (judgement). **Competition 2.** ONYX (32,000+ turbines, Bengaluru office), Turbit (3,500+ turbines, paid backtests), INOX Green (11 GW wind O&M, "Predictive Maintenance") [S22]-[S26] (vendor claims). **Regulatory 3.** Generation assets; CEA cyber rules' final status UNVERIFIED (per R2/R5, not re-opened). |
| B. Chillers | **Data 1.** No public REAL FIELD chiller dataset with fault or maintenance labels was found. The LBNL FDD page states neither origin nor licence and does not mention chillers [S33]. BDG2 describes hourly meter readings and mentions no fault labels [S34][S39]. **Access 4.** The team's own estate department is the only door plausibly held already (judgement), but ICAP names chillers for "hotels, hospitals, malls, office complexes and airports", not campuses [S32]. **Decision value 2** and **fit 2.** 2-4 units per plant gives no fleet (judgement). **Competition 3.** ICAP: "Chiller analytics software platforms are readily available" [S32]; Augury lists chillers [S35] (vendor). **Regulatory 5.** Not a safety function; no network connection (judgement). |
| C. Buses | **Data 3.** SCANIA Component X: REAL FIELD trucks with repair and censoring labels, CC BY 4.0 [S12][S13]. It is adjacent (trucks, anonymised) and in a different data form from depot records. **Access 2.** CIRT is "the technical organ of ASRTU" and runs training and research/consultancy for STUs [S30]; data sharing is UNVERIFIED. **Decision value 4.** CIRT 2021-22: 72.4% fleet utilisation, 164,139 breakdowns, 80,900 workshop and maintenance staff [S29]. **Fit 3.** Needs a km time base, censoring-aware models and record-based inputs (judgement). **Competition 4.** Uptake's page lists a Buses industry and a generic "Risk Explorer" prioritisation feature, and does not mention India [S31] (vendor claim). **Regulatory 3** (judgement). |

**Weighting sensitivity, recorded scores** (computed)

| Weighting | Wind (recorded) | Buses | Chillers | Leader |
|---|---|---|---|---|
| Equal weights | 17 | 19 | 17 | Buses |
| Data ×2 and technical fit ×2 (judge's choice) | 24 | 25 | 20 | Buses |
| Access ×2 | 19 | 21 | 21 | Buses and chillers tie |
| Decision value ×2 | 20 | 23 | 19 | Buses |
| Competition ×2 | 19 | 23 | 20 | Buses |

**What the table does and does not show.**
- Under the recorded scores, wind leads under none of the weightings tested.
- The bus scores were **not** re-examined with the severity applied to wind; the review says so itself [L7 §5]. The bus data score of 3 rests on adjacent truck data in a different form. The test that cut wind's data score ("in-class labelled evidence") has not been applied to it.
- This record does not re-score buses, because the writer re-scoring the options would be re-arguing the decision. The open item is in section 12.
- If G1 passes, it would supply evidence for two of wind's uncertain scores: access (a party with shareable data) and decision value (a party confirming the decision). Scenario with access 3 and decision value 4: wind 19 equal and 26 weighted, against buses 19 and 25 (computed). That is a scenario, not a result.

---

## 5. Reasons wind is kept provisionally

Each reason is restated after the review; the reasons the review struck out are listed at the end.

1. **Only wind has public data in the same asset class and in the form a customer would likely export** (the "likely export" part is judgement).
   - The wind sets are REAL FIELD 10-minute SCADA under licences that allow commercial use: CARE under CC BY-SA 4.0 [S1][S9]; Hill of Towie, Kelmarsh and Penmanshiel under CC BY 4.0 [S3][S4][S5][S11].
   - The bus option's public data are trucks, with anonymised variables and some scaling and frequency modifications [S13].
   - The chiller option has no labelled public data that this record could verify [S33].
2. **A labelled falsification test can run now, with no customer.**
   - CARE Farm A provides 11 anomaly events and 11 normal datasets on 5 onshore turbines in Portugal [S2]. The farm has a gearbox: event 51 is a gearbox bearing damage [S1]. Its rated power is not stated [S1][S2].
   - The paper publishes the bars: autoencoder 0.66, random 0.5, and a rule that the score equals mean Accuracy when Accuracy is below 0.5 [S2].
   - The review requires this test whatever the vertical [L7 §7].
3. **False-alarm rate can be measured directly, and it matters.**
   - CARE ships normal datasets, and Accuracy on them carries double weight in the CARE score [S2].
   - May and McMillan (2013) note that investigating or ignoring false alarms offshore "will incur costs", which "may alter the cost benefit" of condition monitoring systems [S21].
4. **There are real change points for testing drift and retraining.**
   - Hill of Towie documents AeroUp retrofit dates: T13 on 29 September 2021, the rest between 14 July 2022 and 26 May 2023 [S3].
   - EDP's failure log names the failed component per record [S7].
5. **Technical fit with the parts of SentinelLoop that worked** (judgement):
   - the healthy-baseline health index (D10) and regime normalisation (D14);
   - age-matched drift monitoring (D17) and the promotion gate (D22, D24) [L2];
   - the conformal machinery, which shifts from RUL intervals to calibrating alarm thresholds on normal data.
   - *Status after the platform build:* the wind model reuses the healthy-baseline idea in a new normal-behaviour model with per-turbine commissioning (`app/nbm.py`, PD-12), not in the competition code. Drift monitoring and the promotion gate exist only in the competition pipeline, and drift monitoring and gated retraining for wind are PLANNED (FR-H3). The shipped wind thresholds use a max-healthy-score rule, not conformal calibration.
6. **No hardware is needed.** EDP's 10-minute signals include generator and rotor RPM, drivetrain temperatures, active power and pitch angles [S7].

**Reasons removed after the review** (no longer used):
- **"The policy creates the decision."** The repowering valuation and the UL 4143 certification do not consume SCADA early warnings [S16 pp.3, 10].
  - The policy text does say life-extension refurbishment may modify "gearbox, blades, generator, controller etc." [S16 p.1]. Whether a UL 4143 assessor would use SCADA evidence is UNVERIFIED.
- **"Tamil Nadu has the largest sub-2 MW fleet."** True as a number, but only 19.9% of it is 1.5-2 MW (computed from [S16]), and the chosen band is now above 2 MW.
- **"NIWE is the institutional door."** See objection 5.
- **"44-45 labelled events."** True for all of CARE, but 33-34 of those events are on offshore turbines. Only 11 are in class [S2].

---

## 6. Adversarial objections and how each is handled

Outcome codes:
- **Accepted, changed**: the record was changed.
- **Accepted as risk**: the record keeps the exposure and names it.
- **Answered**: the objection is met with evidence.

| # | Objection [L7] | Check in this session | Response | Outcome |
|---|---|---|---|---|
| 1 | In-class labelled evidence is far thinner than claimed: Farm A has 11 events and 11 normal datasets on 5 turbines; the rest are offshore. The EDP logbook covers the same turbines. | Confirmed: per farm, A 11/11, B 6/9, C 27/31 [S2]. Farm A's data come from the EDP platform [S1]. EDP's Wind Farm 1 signals, logs and failure records cover 5 selected turbines (the farm's location file lists 16 turbines) [S7], so the two are likely not independent (judgement). Wilson 95% half-width at n=11 is ±23-25 points; at n=44 it is ±13-14 (computed). About 38 events would give ±15 points and about 89 would give ±10 (computed at p=0.6). | Data re-scored 3. In-class claims are limited to Farm A. Farms B and C are reported as a separate cross-asset rung. All detection figures will carry Wilson intervals. Events are recounted from the v6 files (the Zenodo page says 45/50; the paper says 44/51) [S1][S2]. | **Accepted, changed**, with residual **risk accepted**: in-class detection claims will be imprecise. |
| 2 | The band rationale fails: the 2.05-2.3 MW public sets are unlabelled, and they sit above the "below 2 MW" line. | Confirmed: Kelmarsh and Penmanshiel come to 2.05 MW (computed) [S4][S5]; Hill of Towie is SWT-2.3-VS-82 [S3]. CARE states no rating [S1][S2]. The policy's eligibility includes "rated capacity below 2 MW" [S16 p.2]. | Band changed to 2.0-2.3 MW geared (option (b), section 1). The repowering hook is dropped. The Farm A rating is still unknown, so its in-class status rests on onshore location and a gearbox, not on rating. | **Accepted, changed**. **Risk accepted**: India's fleet in this band is UNVERIFIED in size, model mix and gearbox share. |
| 3 | The Tamil Nadu start rests on a number that is mostly outside the band. | Confirmed from the scanned table [S16 pp.1-2]. Of Tamil Nadu's 7,386.5 MW, 1,473.5 MW (19.9%) is 1.5-2 MW and 4,100 MW (55.5%) is below 1 MW (computed). In the 1.5-2 MW column, Gujarat (1,805.35) and Andhra Pradesh (1,701.2) lead and Tamil Nadu is third. The table and column totals add up (25,396.65 MW; 9,065.35 MW) (computed). The policy text says 25.406 GW [S16 p.1]. | Tamil Nadu is no longer chosen on fleet grounds, and no first state is fixed. Under option (b) the sub-2 MW table does not describe the target band at all. The first state is wherever G1 finds a qualifying party. | **Accepted, changed** |
| 4 | The "policy-backed decision" does not use what the product outputs; repowering candidates are end-of-life assets. | Confirmed. The indicative valuation model uses PLF, generation, O&M expense, tariff, discount rate, decommissioning cost and scrap income [S16 p.10]. Life extension is "assessed and certified by the certification agency" under UL 4143 [S16 p.3]. UL 4143's public scope is "rules and procedures" for lifetime extension of onshore turbines, using a risk approach [S20]. | The decision is replaced by a hypothesis: inspection ranking under a technician and crane budget. Decision value is re-scored 3 until G1 finds a party that confirms the decision. | **Accepted, changed**. **Risk accepted**: the decision itself is UNVERIFIED. |
| 5 | NIWE is a door into NIWE's own projects, not to owners or their SCADA. | Confirmed from the notice [S17]. Interns "work with scientists/engineers on NIWE's projects", from NIWE's office with daily attendance, unpaid. Publication needs the Director General's approval with a NIWE guide as second co-author. Interns sign a data-protection declaration. At most 25 interns at a time. Policy §11 has SNAs/CNA "along with SLDCs" supply data to NIWE [S16 p.7]. WT-MARUT is a supply-chain traceability portal, not an operational-data store [S19]. NIWE's open data are 10 wind-monitoring-station sets and a 150 m atlas, "© All Rights Reserved" [S18]. | NIWE is reclassified as an optional internship with publication and data restrictions. Before any work on NIWE data, the team gets written clarification on publication and reuse. NIWE is not on the critical path. | **Accepted, changed** |
| 6 | The user and buyer are unidentified; the 12-month gate is weaker than a competitor's own 3-year minimum. | Confirmed: Turbit's paid backtest needs at least 3 years of SCADA per turbine and calls 5+ years ideal [S23] (vendor claim). INOX Green claims "11 GW of Wind O&M assets" [S26] (vendor claim), about 18.6% of national capacity (computed with [S15]). Who controls SCADA exports remains UNVERIFIED. | Access becomes the **first gate (G1)**, with a 3-year minimum and a legal-sharing condition. If G1 fails, the team switches to the runner-up. | **Accepted, changed** |
| 7 | In wind the product loses its RUL headline and becomes a commoditised normal-behaviour model; competition in India is denser than stated. | Confirmed (vendor claims). ONYX: "32,000+ turbines monitored", faults "up to 24 months ahead", CMS hardware, a Bengaluru office [S24][S25]. Turbit: 3,500+ turbines, 40+ customers, paid backtest on exports from Vestas, Siemens Gamesa, Nordex, Enercon and GE, naming gearbox damage and generator failures [S22][S23]. Clir: "reconciles OEM calculations" and "dispute-ready reports" [S28]. IBM Maximo Renewables at KP Group (HQ Gujarat): the case study's O&M scope is "solar and hybrid power plants"; wind appears only in the company background, not in the deployment described [S27]. | Competition stays at 2. The differentiation hypotheses are reported achieved-vs-nominal false-alarm control, re-derivable audited triage, and offline-first vendor-neutral operation. All are **unvalidated**. The first one does not apply to the shipped threshold rule, which has no nominal rate (G0 Amendment 1, `PREREGISTRATION.md` §10.2); only a reported false-alarm rate remains. W5 is the same shape of offer as Turbit's backtest, so it is not a differentiator in itself. | **Accepted as risk** |
| 8 | Under the judge's own weights, one-point corrections erase wind's lead. | Confirmed (computed, section 4): buses 25 against wind 24 weighted, and buses lead under every weighting tested. | Stated at the top of this record. Wind is held only for the gate period, and the team lead is asked to confirm or switch (section 12). | **Accepted, changed** (status made provisional) |

**Required changes 7-9** [L7 §7]:

| Change | Response | Outcome |
|---|---|---|
| 7. Pre-register the falsification test and run it whatever the vertical. | This is gate G0 (section 7). The pre-registration was written before any download, and so was Amendment 1 (`product/evidence/g0/PREREGISTRATION.md`). Their date stamps are local git commits; the file's SHA-256 is still to be published externally (section 7). | **Accepted, changed**: pre-registered. The run is BLOCKED on download approval |
| 8. Licence hygiene. | The CC BY-SA 4.0 legal code applies share-alike when "You Share Adapted Material You produce" (§3(b)). §2(a)(2) and §8(a) leave uses that need no permission unregulated [S10]. Published CARE- or EDP-derived files stay CC BY-SA [S9]. Whether trained models or alerts count as shared Adapted Material is a legal question; this is not legal advice and the question is **UNVERIFIED**. EDP's primary page returned HTTP 403 [S8]; its CC-BY-SA label comes only from the IEA summary [S7]. | **Accepted**. Legal review is PLANNED before any commercial use. |
| 9. Precision of the Hill of Towie downtime data. | Confirmed: the record page says the per-10-minute downtime was calculated from a combination of SCADA data and RES operator logs, and that it ends August 2024 [S3]. | **Answered** |

---

## 7. Gates for the provisional period

Status: G0 is pre-registered, and its run is BLOCKED on download approval. G1 is PLANNED.

The timing runs from the team's start date, which is not yet set. The gates run in parallel.

### G0: falsification on public data (weeks 0-4; no access needed)

The protocol is `product/evidence/g0/PREREGISTRATION.md`. Its Amendment 1 (§10) was also written before any download, and governs where it conflicts with §§2-5. Amendment 2 (§11), also written before any download, governs where it conflicts with §10. It changes no pass/fail criterion; it changes the stuck-signal and gate-order definitions and the product alarm count (sustain 18 operating points). This section summarises the protocol; the pre-registration is authoritative.

1. **Get the data.** Download CARE v6 (one 5.5 GB zip) and check MD5 `2547b58c21ac8c242d13232860cf500c` [S1]. Recount anomaly and normal datasets per farm, because the Zenodo page and the paper disagree [S1][S2].
   - The download script `product/scripts/fetch_care.py` checks the MD5, records a SHA-256 and extracts only text members.
   - It is **NOT RUN**: the download awaits the user's approval (PD-26). No CARE file is on this machine.
2. **Pre-registration: done** (dated file, before any data). It fixes:
   - **Splits** (§10.4): each CARE dataset is trained on its own turbine's training part and scored on its prediction part. This is CARE's design and matches per-turbine commissioning (PD-12). There is no random time split.
     - This supersedes this record's earlier wording, "splits by turbine and by farm".
   - **No conformal calibration set** (§10.4). Thresholds come from a healthy validation slice: 1.25 × the maximum healthy rolling score (§2.4, §10.1).
   - **Metrics** (§4, §10.2):
     - the CARE score and its four parts;
     - event detection rate per farm with a Wilson 95% interval (§4); Farm A's must be quoted in any external use (§10.3);
     - lead time;
     - product alarm episodes (sustain 18 operating points, §11.1) per calendar and per assessable turbine-year on normal datasets;
     - assessability per farm.
   - "Achieved against nominal false-alarm rate" is withdrawn: the threshold rule has no nominal rate.
   - **Adapter, gate order, multiplicity and timing definitions** (§10.1-10.2; stuck signals and gate order as amended by §11.1).

   **Caveat on the date.** The date stamp is a local git commit only: the repository has no remote, so an outsider cannot yet check that the file predates the data. The team is asked to publish the file's SHA-256 externally before the download (`PREREGISTRATION.md` §10; `FINAL_PRODUCT_HANDOFF.md`).
3. **Rungs.** Report Farm A (in class) and Farms B/C (cross-asset, onshore to offshore) separately.
4. **Decision rule** (Amendment 1, §10.3). It replaces the earlier pooled rule taken from the judge's switch condition [L6 §6]. **Farm A is the primary decision.** G0 passes only if all three hold:
   1. Farm A's CARE score is above the Farm A score of an internal baseline, a power-binned z-threshold computed by the same metric code with the same gates;
   2. Farm A mean Accuracy is ≥ 0.5;
   3. the pooled CARE score over all 95 datasets is > 0.66, the published autoencoder result. This is kept as a secondary bar.

   A pooled pass with Farm A at or below the baseline is a **fail**. On a fail, the wind choice is re-tabled whatever G1's outcome.
   - The 0.66 figure is pooled: the paper's Figure 3 caption describes the benchmark as "over all 95 sub-datasets", and the paper gives no per-farm score table [S2] (fact-check, 2026-10-18). A Farm A-only score is therefore not directly comparable with 0.66 (judgement). That is why Amendment 1 decides Farm A against an internal baseline: the pooled score is decided mostly by offshore, cross-asset data.
   - With 11 in-class events, a pass or fail on detection is itself uncertain (±23-25 points). The pre-registration forbids re-tuning on the same events to turn a fail into a pass.
   - Any external use of G0 must quote the Farm A result with its interval, and must label the pooled result "mostly cross-asset (offshore)" (§10.3).

### G1: access and decision (weeks 1-4)

- Hold 3-5 conversations with Indian wind owners, IPP asset-management teams or independent O&M providers. None has been contacted yet.
- **Pass** if at least one party can show all three of:
  1. it can legally share at least 3 years of 10-minute SCADA plus a failure or work-order log, for turbines of a stated model and rating;
  2. it controls that export, or has the holder's written consent;
  3. a ranked inspection list under a technician or crane budget would feed a maintenance decision it actually makes.
- Record for each conversation: turbine model, rating, drivetrain type, who runs O&M, and who owns the SCADA export.
- **Fail**: no party meets all three. The team then re-scores both options with the same severity and switches to the runner-up.

### In parallel (PLANNED)

- **Runner-up readiness.** Run SCANIA Component X as the RUL-with-censoring method benchmark. Prepare, but do not send without the team lead's approval, a feasibility inquiry to CIRT about anonymised depot registers.
- **Licence review.** Ask for a review of CC BY-SA obligations, and try again to read EDP's primary terms.
- **NIWE (optional).** Apply to the Academic Associate Programme only if the team accepts its terms [S17]. Get written clarification on publication and reuse before touching NIWE data.

---

## 8. Real public datasets for validation

| Dataset | Data type | Licence | URL | Role | Limits |
|---|---|---|---|---|---|
| **CARE to Compare v6** (Fraunhofer IEE, published 2025-07-09) | REAL FIELD, anonymised | CC BY-SA 4.0 | https://zenodo.org/records/15846963 [S1]; paper https://arxiv.org/html/2404.10320v2 [S2] | **Primary.** Farm A (onshore Portugal, 5 turbines, 86 features) = in-class labelled rung. Farms B and C (offshore Germany, 9 and 22 turbines, 257 and 957 features) = cross-asset rung. 36 turbines and about 89 years of 10-minute SCADA in all [S1][S2]. | Rated power and model are not stated for any farm. Farm A's event starts are estimated back from logbook fault timestamps. B/C log missing values as 0 and record status only on change. Farm A's 14 days before each fault are set to status 4 and the 3 days after to status 3 [S2]. Share-alike on derivatives [S9]. |
| **EDP Wind Farm 1** (EDP Open Data) | REAL FIELD | CC-BY-SA per the IEA summary; primary terms UNVERIFIED (HTTP 403) | https://iea-wind.org/wp-content/uploads/2024/07/EDP-OpenData-Details.pdf [S7]; https://www.edp.com/en/innovation/open-data/data [S8] | Failure logbook for the CARE Farm A source turbines: 23 training records 2016-03-03 to 2017-08-21, plus a 2017 file of 12 records, 7 of which overlap. That makes 28 distinct records over 2016-2017 (computed). Operation logs: 256,231 + 62,604 records. 10-minute signals for 5 turbines [S7]. | Secondary source only. Sign-in needed. One item is marked "Restricted (NDA)" [S7]. Very likely the same turbines as CARE Farm A, so not independent (judgement). |
| **Hill of Towie** v2.1.0 (RES, published 2026-09-08) | REAL FIELD | CC BY 4.0 | https://zenodo.org/records/22662930 [S3] | In-class unlabelled rung: false-alarm rate, alarm and downtime agreement. Long-horizon drift with AeroUp retrofit dates. Decision back-test against downtime. 21 SWT-2.3-VS-82, SCADA and alarm logs Jan 2016-Apr 2026, about 1 Hz fastlog Jan-Apr 2026, 29.7 GB [S3]. | No dedicated failure or replacement records are described. Downtime ends August 2024 [S3]. Drivetrain type not stated on the page (UNVERIFIED). |
| **Kelmarsh** v4 (Cubico) | REAL FIELD | CC BY 4.0 | https://zenodo.org/records/16807551 [S4] | In-class unlabelled rung; 2016-2024 drift. 6 Senvion MM92, 10-minute SCADA and events data, 3.8 GB [S4]. | No failure labels described. A separate record publishes code to reconstruct the 2023 and 2024 turbine-data files after a structural-defect audit [S6]. Its findings were not read (UNVERIFIED), so the team uses the reconstructed files or excludes those years. |
| **Penmanshiel** v3 (Cubico) | REAL FIELD | CC BY 4.0 | https://zenodo.org/records/16807304 [S5] | In-class unlabelled rung; 2016-2024 drift. 14 Senvion MM82 (no WT03), 10-minute SCADA and events data, 7.5 GB [S5]. | No failure labels described. Not all signals cover the full period [S5]. The Kelmarsh audit record [S6] also runs on Penmanshiel v3 and lists a Penmanshiel replication; its findings were not read (UNVERIFIED). |
| **SCANIA Component X** v3 (method benchmark only, outside the vertical) | REAL FIELD, anonymised, with scaling and altered repair and readout frequencies | CC BY 4.0 | https://researchdata.se/catalogue/dataset/2024-34/3 [S12]; paper https://arxiv.org/html/2401.15199v1 [S13] | Tests RUL-with-censoring code: 2,272 repaired and 21,278 censored vehicles in `train_tte.csv` [S13]. | Trucks, not turbines. No wind claim may be drawn from it. |

**Ladder** (all rungs PLANNED). "In class" means onshore and geared. These W1-W6 are real-data rungs; in section 9 and in `product/evidence/wind_synthetic/`, W1-W3 name runs on the product's own synthetic generator.

| Rung | Data | Measurable | Not measurable |
|---|---|---|---|
| W1 single site, in class, labelled | CARE Farm A [S1][S2] | CARE score, detection rate (±23-25 points at n=11, computed), lead time, false-alarm rate on 11 normal datasets | Precise detection rate; any RUL |
| W2a cross-asset, labelled | CARE Farm A → Farms B and C [S2] | Transfer of the threshold calibration onshore → offshore | In-class transfer |
| W2b cross-site, in class, unlabelled | Farm A → Kelmarsh, Penmanshiel, Hill of Towie [S3][S4][S5] | False-alarm rate on unseen farms (against a nominal rate only if conformal thresholds are built; the shipped rule has none); alarm and downtime agreement | Labelled detection rate |
| W3 long-horizon drift | Hill of Towie 2016-2026 with AeroUp dates; Kelmarsh and Penmanshiel 2016-2024 [S3][S4][S5] | Drift alarms on documented change points; gate behaviour across years | Fault causation |
| W4 decision back-test | Hill of Towie downtime (to Aug 2024) and alarm logs [S3] | Escalation load per shift; share of downtime episodes preceded by an escalation | Rupee value (no cost data; UNVERIFIED) |
| W5 customer back-test | A G1 party's export of 3+ years | Whether W1-W4 hold on Indian turbines | Depends on G1 |
| W6 read-only shadow | G1 party, read-only | Prospective agreement, misses, lead time | Depends on W5 |

---

## 9. What the current system must change to serve this asset class

The IDs come from `product/TECHNICAL_DEBT.md` [L4] and the decision IDs D10-D24 [L2]. The rows were written as PLANNED, from the competition baseline. The implementation status note after the table gives the current status of each row.

| Area | Today (C-MAPSS) [L1][L3] | Change for wind SCADA | IDs |
|---|---|---|---|
| Time and schema | Cycle index; fixed 26-column C-MAPSS layout | 10-minute UTC timestamps and turbine IDs. Long-format readings contract (asset, timestamp, signal, value, unit, quality). One signal-mapping file per farm, since CARE farms have 86, 257 and 957 features [S1]. Offline CSV or Parquet import of exports; no OT connection for back-tests. | A1, A3, A7 |
| Asset registry | An asset is an integer `unit` | Farm, turbine, model, rating, drivetrain type, commissioning date, component taxonomy (gearbox, gearbox bearings, generator, transformer) | A2 |
| Labels and leakage | Run-to-failure labels; engine-level CV with a leakage audit | Status IDs are used only as an **evaluation mask**, never as model inputs near events. Normal operation is status 0 or 2; 1, 3, 4 and 5 are not [S2]. Farm A's status marks only faults, so power and wind speed must be checked too [S2]. Split by turbine and farm (superseded by G0 Amendment 1, `PREREGISTRATION.md` §10.4: each CARE dataset is trained on its own turbine's training part, with no random split). | (extends E0/H7 discipline) |
| Model target | HGBR RUL regression, capped at 125 cycles; thresholds at 10/25/50 cycles | A normal-behaviour residual model on the healthy-baseline index (D10). Regime normalisation (D14) keyed on wind speed, power and pitch. The RUL cap and cycle thresholds are not used for wind. | A4, A5 |
| Conformal role | CQR 90% RUL interval, marginal coverage, below nominal on FD004 | Conformal calibration of alarm thresholds on held-out normal windows, per farm and turbine model (group-conditional). Report achieved against nominal false-alarm rate on unseen farms. | C4 |
| Metrics | Last-cycle RMSE, PHM08, PICP and MPIW | CARE score (Coverage, Accuracy ×2, Reliability with alarm criticality ≥72, Earliness) [S2]. Detection with Wilson intervals; lead time; false alarms per turbine-year. RMSE stays a C-MAPSS-only metric. | E1 |
| Triage agent | Severity from the RUL lower bound; the fleet rule escalates 25-36% of healthy engines while active [L1] | Persistence across consecutive 10-minute windows; mapping from residual sensor group to component; escalation budget per shift. A weekly ranked inspection list under a technician and crane budget, plus a deferral list with risk. The fleet rule triggers a data-quality check instead of mass escalation. | B5 |
| Drift and retraining | Age-matched drift (D17); gate on RMSE, coverage and late rate (D22); `retrain` (D24); inference retrains instead of loading the approved model | Drift matched on season and operating regime. Re-baseline after logged replacements or retrofits (EDP component records, Hill of Towie AeroUp dates). Gate challengers on held-out turbines and farms. Inference loads the approved model version. | A6, C1, C2, B6 |
| Persistence and audit | Re-runs delete stored decisions and the audit log; the chain has no key | An append-only store before any back-test longer than one run. Keyed chain. Pseudonymised technician names (DPDP duty per R5; not re-opened, UNVERIFIED in this session). | B2, D6 |
| Work orders and outcomes | Draft JSON records; no lifecycle; no outcomes | A wind component taxonomy and an external ID for idempotent CMMS upsert. EDP's Component and Remarks fields train the component mapping [S7]. Outcome records for W6. | B1, B3, B4 |
| Provenance and licence | NASA data not redistributed | Record dataset versions and checksums. Attribute CC BY and CC BY-SA sources. Keep EDP raw data out of the repository. Keep CC BY-SA on published CARE- or EDP-derived files [S9][S10]. | — |
| Claims | Competition framing | Every wind claim starts as PLANNED in `CLAIM_EVIDENCE_MATRIX.md`. No RUL claim for wind without real-label evidence. | PD-03, E2 |

---

> **Implementation status note (updated 2026-10-18, after Phase 9 and the adversarial-review fixes).** This section was written from the competition baseline. The product platform on branch `product/platform` (`src/sentinelloop/app/`, `src/sentinelloop/console/`) has since implemented part of it. Nothing below has been run on real wind data. Status per row, with evidence:
> - **Time and schema: implemented.**
>   - Long-format readings contract with units, reason codes and suspect flags (`app/ingest.py`, `tests/test_app_ingest.py`). Batches are capped at 200,000 readings.
>   - Wind signal set and adapter (`app/adapters/wind.py`). `pitch_angle` is optional.
>   - Assessment instants and staleness (PD-17): future instants refused; back-dated assessments stored as replays; whole-feed delay reported as `data_delivery_delay`.
>   - PLANNED: per-site tag mapping (`KNOWN_LIMITATIONS.md` P12). The CARE adapter is specified in `PREREGISTRATION.md` §10.1, and its per-farm mapping files are written before scoring. That code is not written.
> - **Asset registry: implemented** (sites, asset types, assets with criticality, consequences, windows and config; `app/registry.py`).
>   - Component taxonomy: partial. The wind job types are inspect, desk review, instrument check, HSS-bearing exchange, generator-bearing exchange and gearbox-oil service.
> - **Labels and leakage: fixed for G0 in the pre-registration; no code yet** (the CARE adapter is not written, and no CARE file is on this machine).
>   - Splits (`PREREGISTRATION.md` §10.4): each CARE dataset is trained on its own turbine's training part and scored on its prediction part, which matches per-turbine commissioning (PD-12). There is no random time split. This supersedes the table's "split by turbine and farm".
>   - Status IDs are not model inputs (the inputs are listed in `PREREGISTRATION.md` §2.1). Only normal-status rows (status 0 or 2) are used for training (§2.3) and scored (§4).
>   - No information from the prediction part is used for fitting, thresholds, features or hyper-parameters (§2.5).
> - **Model target: implemented on SYNTHETIC data only.**
>   - Normal-behaviour ridge model of gearbox HSS-bearing, gearbox-oil and generator-bearing temperatures, with per-turbine commissioning (`app/nbm.py`, `tests/test_app_wind.py`, PD-11, PD-12).
>   - Transformer temperature is not modelled.
>   - Anomaly-only: no RUL and no failure probability.
>   - Alarm persistence is sustain 18 operating points (3 h of operation) with margin 1.25 (PD-15), the setting the W3 synthetic run chose under a rule committed before it ran. The W3 SYNTHETIC result (`product/evidence/wind_synthetic/w3.md`) is a behaviour check, not performance:
>     - pooled tuning fleets (4.53 healthy turbine-years): 0.22 healthy alarm episodes per turbine-year, 72/72 injected faults detected; the neighbouring settings give 1.32 (sustain 12) and 3.09 (sustain 6);
>     - **fresh held-out fleets 60-65: 0.44 per turbine-year (1 in 2.27 turbine-years), 36/36 detected; the 95% interval runs up to about 2.45, so the proposed pilot ceiling of 2 is not excluded**;
>     - an earlier run's setting (sustain 6, W2 run 2) gave 5.74 on its held-out fleets; drifting sensors gave 39 alarm episodes on the fresh fleets (`KNOWN_LIMITATIONS.md` M1);
>     - assessable share 0.59 on the fresh fleets (0.56-0.57 on the pooled tuning fleets).
> - **Conformal role: not implemented.** Thresholds come from held-out healthy data: inspect = 1.25 × the largest healthy rolling score, urgent = 3 × inspect. These are policy choices, not calibrated probabilities (`KNOWN_LIMITATIONS.md` M4). Conformal false-alarm control per farm: PLANNED. G0 uses no conformal set (§10.4).
> - **Metrics.**
>   - `nbm.evaluate` reports detection, lead time, alarm episodes per healthy turbine-year and assessability, in the service's gate order (SYNTHETIC only).
>   - CARE score implementation: PLANNED. Its definitions are fixed in `PREREGISTRATION.md` §4 and §10.2-10.3; the G0 run is BLOCKED on download approval.
> - **Triage: implemented.**
>   - Persistence: the score must stay above the threshold at each of the last 18 operating points (`sustain`; idle rows add no evidence; PD-15); mapping from the deviating temperature to the component (`top_deviations`); anomaly-only states (PD-11).
>   - Within a priority class, wind orders carry an anomaly-ranked score labelled "not a probability" (`app/decision.py`, `tests/test_app_remediation.py`). The `risk_greedy` scheduler orders by it.
>   - Out-of-scope or unavailable criticality-A turbines get a desk review instead of a climb (PD-18). A whole-feed delay raises no work order.
>   - The scheduler (`app/scheduler.py`; default horizon 72 h) handles technicians, skills, shifts, parts and maintenance windows. It has **no cranes**, weather or climbing-wind limits, travel or multi-day jobs (`KNOWN_LIMITATIONS.md` P8).
>   - Not computed: a weekly list under a crane budget, a deferral list with stated risk, and an escalation budget per shift. These remain hypotheses (section 1).
> - **Drift and retraining: not in the platform.** Drift monitoring and gated retraining exist only in the competition pipeline; for wind they are PLANNED (FR-H3).
>   - Inference loads only approved model versions, and the registry verifies the bundle checksum (`app/modelreg.py`).
>   - Re-baselining after a logged replacement: PLANNED (`KNOWN_LIMITATIONS.md` M6).
> - **Persistence and audit: implemented.** Append-only HMAC-chained audit with a fail-closed key (PD-07). `admin verify-audit` needs an anchor unless `--allow-no-anchor` is given (PD-22). The chain covers audit events, not state tables. Technician names are not pseudonymised (`KNOWN_LIMITATIONS.md` S5).
> - **Work orders and outcomes: implemented.** Lifecycle, idempotency and outcomes (`app/workorders.py`).
>   - A latched URGENT_REVIEW or INSPECTION_RECOMMENDED clears in one of two ways (PD-16; `app/states.py` `CLEAR_EVENTS`, `clear_risk`; `app/workorders.py`):
>     - a person completes a qualifying work order: raised after the latch began, for a job that addresses the equipment (not `instrument_check` or `desk_review`), with findings `degradation_found`, `failure_found` or `no_fault_found`. A latch with an unknown start fails closed;
>     - a planner, reliability engineer or admin records a reasoned dismissal (`POST /assets/{id}/clear-risk`, event `dismissed`; no work order is involved).
>   - Either way the asset shows AWAITING_ASSESSMENT until its next assessment.
>   - Deferral reactivation, rejection suppression, hand-back and reprioritise (PD-18).
>   - External ID and idempotent upsert are implemented in the Odoo JSON-2 connector (`app/integration.py`, PD-20). It is shadow by default and tested only against a contract test double (`tests/test_app_integration.py`); a real Odoo instance has NOT been run (`KNOWN_LIMITATIONS.md` S1).
>   - The operator console exists (`src/sentinelloop/console/`, PD-21).
>   - A component mapping trained on EDP's Component and Remarks fields: PLANNED.
> - **Provenance and licence: unchanged.** CARE data stay out of git (`.gitignore` `data/external/`). `product/scripts/fetch_care.py` records the MD5 and SHA-256 (not run).
> - **Claims:** wind capabilities are claimed only as SYNTHETIC in `CLAIM_EVIDENCE_MATRIX.md`.

## 10. Runner-up, and conditions that would change the choice

**Runner-up: DECISION-VALUE-FIRST.** Indian STU depots; diesel-bus powertrain aggregates (engine, fuel-injection pump, gearbox) [L10].

What is verified this session:
- CIRT 2021-22, REAL FIELD ADMINISTRATIVE STATISTICS self-reported by STUs [S29]:
  - fleet utilisation of 72.4%;
  - 164,139 breakdowns (rural 39,799 + hill 532 + urban 123,808, computed);
  - 80,900 workshop and maintenance staff;
  - a note that STUs are in "severe financial crunch".
  - The figures of 12,817 buses off-road and 22,983 spare (cited by the proposal and the judge) appear in a table whose extracted layout is garbled, so they are not independently confirmed here.
- CIRT is "the technical organ of ASRTU". It runs training programmes for STUs and research/consultancy studies of road transport [S30].
- SCANIA Component X's challenge cost matrix charges 200-500 for a late prediction against 7-10 for an early one [S13].
- APS prices a false positive at 10 and a false negative at 500 [S14].
- These are challenge costs, not measured economics.
- Uptake lists Buses among its industries and a "Risk Explorer" feature described in general fleet terms ("prioritize confidently"), does not mention India, and its page states that Bosch announced a planned acquisition of Uptake (dated 19 March 2026) [S31] (vendor page). The page does not describe bus-specific prioritisation.

Why it is second:
- Its public data are adjacent (trucks), in a different form from depot records.
- Technical fit needs a km time base, censoring-aware models and record-based inputs.
- Whether depot records are digital, and whether CIRT or depots would share them, is **UNVERIFIED**.
- The proposal's claims about e-bus GCC contracts and the ASRTU fleet handbook were not re-opened (**UNVERIFIED**).

**Other options the proposals rejected** (not re-argued here; facts re-checked where a source was opened)

| Option | Fact checked this session | Why it stays rejected (from the proposals [L8]-[L10]) |
|---|---|---|
| Rail metro air-production units (MetroPT-3) | REAL FIELD, CC BY 4.0; data span February-August 2020, and the failure table lists four air-leak events between 18 April and 15 July 2020 [S36] | Too few failures from one operator for any accuracy statistic; no cross-site test |
| Data-centre hard drives (Backblaze Drive Stats) | Daily S.M.A.R.T. snapshots; derivative works may be sold but "the data itself" may not [S37] | IT hardware, not industrial maintenance; one operator |
| Offshore oil wells (Petrobras 3W) | Data CC BY 4.0, code Apache 2.0; "rare undesirable real events in oil wells" from three source types [S38] | One operator; event types per the proposal are mostly process events (not re-checked); no realistic access for the team |
| Turbofans (current C-MAPSS) | SIMULATED [L1] | No real data; OEM service contracts (per R3, not re-opened) |

**Conditions that would change the choice**

| # | Condition | Effect |
|---|---|---|
| 1 | G1 fails: no party can legally share 3+ years of SCADA plus a failure or work-order log, or none confirms the inspection-ranking decision | Re-score both options with equal severity, then switch to buses |
| 2 | G0 fails under Amendment 1 (`PREREGISTRATION.md` §10.3). Any one of these is a fail: Farm A's CARE score is at or below the internal power-binned z-threshold baseline; Farm A mean Accuracy is below 0.5; the pooled CARE score is not above 0.66 | Re-table the choice; there is no credible real-data story in wind |
| 3 | The team lead decides to act on the corrected table now | Switch to buses without waiting for G1 |
| 4 | Equal-severity re-scoring of buses (data, access, decision value) changes the ordering | Re-table; the change could favour either option |
| 5 | India's 2.0-2.3 MW fleet proves small, mostly gearless, or lacking exportable 10-minute SCADA history | Change the asset class or band, or switch |
| 6 | A CIRT or STU depot offers 2-3 years of digital per-bus aggregate-change and breakdown registers within about 3 months | Bus access rises and buses overtake wind (judge's condition [L6]) |
| 7 | Legal review finds CC BY-SA obligations block the product, and the CC BY sets alone are not enough | The data advantage shrinks; re-table. The review reads §3(b) as less blocking than feared; not legal advice [S10] |
| 8 | A working WebSearch pass shows India-specific SCADA analytics for mid-life turbines is saturated, or that STU depot tools exist | Re-score competition |
| 9 | The campus has a central chilled-water plant with 12+ months of logs, and the team weights a live pilot within one season above real-data evidence | Run chillers as a side case study only. Under access ×2, chillers tie with buses at 21 and wind trails at 19 (computed) |

---

## 11. Risks accepted

| Risk | Evidence | What limits it |
|---|---|---|
| Few in-class labelled events | 11 events in CARE Farm A [S2]; ±23-25 points (computed) | Interval reporting; cross-asset results reported separately; no precise accuracy claims |
| Label quality | Estimated anomaly starts, inconsistent B/C statuses, missing values set to 0 [S2]; Kelmarsh 2023-2024 defect audit [S6] | Evaluation masks; reconstructed or excluded years; negative results published |
| Domain shift to India | Public data are European [S1][S3][S4][S5]; no Indian turbine SCADA is public [S18]; Indian model mix UNVERIFIED | W5 on a G1 party's data before any Indian claim |
| Buyer and data control unknown | Unresolved by any source opened; large O&M providers exist (INOX Green 11 GW, vendor claim) [S26] | G1 first; switch rule |
| Dense competition with hardware, fleets and backtests | [S22]-[S28] (vendor claims) | Differentiation stays a hypothesis until measured |
| SCADA is coarser than vibration CMS | ONYX claims faults "up to 24 months ahead" with CMS hardware [S24] (vendor claim); CARE lead times not yet computed | Report lead time honestly; no comparison claim |
| RUL claims creeping back | RUL has been evaluated only on SIMULATED data [L3] | Message rule (section 1); claim matrix |
| Licence obligations | CC BY-SA share-alike [S9][S10]; EDP primary terms 403 [S8] | Legal review; CC BY sets for anything that must stay closed |
| Power-sector cyber rules | CEA draft regulations (per R2/R5; final status UNVERIFIED) | Offline-first back-tests; no OT connection before W6 |

---

## 12. Open items

**Decisions for the team lead:**
1. Keep the four-week wind gate, or switch to the runner-up now given section 4.
2. Confirm option (b), the 2.0-2.3 MW band.
3. Approve any outreach (G1 conversations, the CIRT inquiry). None has been made.

**UNVERIFIED facts:**
- the rated power, model and drivetrain type of the CARE farms;
- the drivetrain type of the Hill of Towie, Kelmarsh and Penmanshiel turbines;
- the size, state distribution, model mix and gearbox share of India's 2.0-2.3 MW fleet;
- who controls SCADA exports and work orders for Indian mid-life turbines;
- whether any Indian party makes an inspection-ranking decision with SCADA evidence;
- whether UL 4143 assessments use SCADA or condition-monitoring evidence;
- EDP's primary licence terms;
- the findings of the Kelmarsh defect audit;
- the per-event cost of drivetrain failures in India;
- the final status of CEA cyber regulations;
- India-specific competitor density (no WebSearch);
- whether CIRT or STU depots hold digital per-bus records and would share them;
- the bus off-road and spare figures (garbled table).

---

## Sources

All web sources were opened in this session with WebFetch, accessed **2026-10-18**. "PDF" means WebFetch returned the binary and its text was extracted locally. "Scanned" means the pages were rendered and read visually.

- [S1] Zenodo, CARE To Compare v6, "Wind Turbine SCADA Data For Early Fault Detection" (REAL FIELD; CC BY-SA 4.0): https://zenodo.org/records/15846963
- [S2] CARE to Compare paper (Fraunhofer IEE dataset), arXiv 2404.10320v2 (HTML): https://arxiv.org/html/2404.10320v2
- [S3] Zenodo, Hill of Towie wind farm open dataset v2.1.0 (REAL FIELD; CC BY 4.0): https://zenodo.org/records/22662930
- [S4] Zenodo, Kelmarsh wind farm data v4 (REAL FIELD; CC BY 4.0): https://zenodo.org/records/16807551
- [S5] Zenodo, Penmanshiel wind farm data v3 (REAL FIELD; CC BY 4.0): https://zenodo.org/records/16807304
- [S6] Zenodo, code and outputs for a provenance audit of the Kelmarsh open SCADA dataset, published 6 October 2026; scripts run on Kelmarsh v4 and Penmanshiel v3 and include a Penmanshiel replication (CC BY 4.0): https://zenodo.org/api/records/23196733
- [S7] IEA Wind, EDP OpenData Details (PDF): https://iea-wind.org/wp-content/uploads/2024/07/EDP-OpenData-Details.pdf
- [S8] EDP Open Data (returned HTTP 403; no content read): https://www.edp.com/en/innovation/open-data/data
- [S9] Creative Commons, CC BY-SA 4.0 deed: https://creativecommons.org/licenses/by-sa/4.0/
- [S10] Creative Commons, CC BY-SA 4.0 legal code: https://creativecommons.org/licenses/by-sa/4.0/legalcode.en
- [S11] Creative Commons, CC BY 4.0 deed: https://creativecommons.org/licenses/by/4.0/
- [S12] Researchdata.se, SCANIA Component X dataset v3 (REAL FIELD; CC BY 4.0): https://researchdata.se/catalogue/dataset/2024-34/3
- [S13] SCANIA Component X paper, arXiv 2401.15199v1: https://arxiv.org/html/2401.15199v1
- [S14] UCI, APS Failure at Scania Trucks (REAL FIELD; CC BY 4.0): https://archive.ics.uci.edu/dataset/421/aps+failure+at+scania+trucks
- [S15] MNRE, Physical Progress (installed wind capacity 59,201.07 MW as on 30.09.2026; the table heading says 31 August 2026): https://mnre.gov.in/en/physical-progress/
- [S16] MNRE, National Repowering & Life Extension Policy for Wind Power Projects 2023, circular dated 7 December 2023 (scanned; page numbers are the policy's printed numbers): https://cdnbbsr.s3waas.gov.in/s3716e1b8c6cd17b771da77391355749f3/uploads/2023/12/202312131874296229.pdf
- [S17] NIWE, Academic Associate Programme notice (PDF): https://niwe.res.in/static/pdf/NIWE-AAP_Internship_Programme.pdf
- [S18] NIWE, Open Datasets: https://niwe.res.in/Open_data_Set/open_wind_dataset/
- [S19] NIWE, WT-MARUT portal: https://wtmarut.niwe.res.in
- [S20] UL Standards, UL 4143 product page (scope only): https://www.shopulstandards.com/ProductDetail.aspx?productId=UL4143
- [S21] May and McMillan (2013), Strathprints 54903: https://strathprints.strath.ac.uk/54903/
- [S22] Turbit home page (vendor): https://www.turbit.com/
- [S23] Turbit backtest page (vendor): https://www.turbit.com/backtest
- [S24] ONYX Insight home page (vendor): https://www.onyxinsight.com/
- [S25] ONYX Insight locations (vendor): https://onyxinsight.com/company/our-locations/
- [S26] INOX Green home page (vendor): https://www.inoxgreen.com/
- [S27] IBM case study, KP Group (vendor): https://www.ibm.com/case-studies/kp-group
- [S28] Clir home page (vendor): https://www.clir.eco/
- [S29] CIRT, STUs Profile and Performance 2021-22 (PDF; REAL FIELD ADMINISTRATIVE STATISTICS): https://www.asrtu.org/resource/front/uploads/PROFILE_PERFORMANCE-2021-22.pdf
- [S30] ASRTU, About (CIRT's role): https://www.asrtu.org/page/about
- [S31] Uptake home page (vendor): https://uptake.com/
- [S32] MoEFCC, India Cooling Action Plan, March 2019 (PDF): https://ozonecell.nic.in/wp-content/uploads/2019/03/INDIA-COOLING-ACTION-PLAN-e-circulation-version080319.pdf
- [S33] LBNL/DOE, Fault Detection and Diagnostics datasets (origin and licence not stated): https://faultdetection.lbl.gov/
- [S34] Building Data Genome 2, LICENSE file (text reads "Attribution-ShareAlike 4.0 Unported"; exact version to be checked): https://raw.githubusercontent.com/buds-lab/building-data-genome-project-2/master/LICENSE
- [S35] Augury home page (vendor; lists chillers): https://www.augury.com/
- [S36] UCI, MetroPT-3 (REAL FIELD; CC BY 4.0; four failure events listed): https://archive.ics.uci.edu/dataset/791/metropt+3+dataset
- [S37] Backblaze, Drive Stats data page (custom terms: the data itself may not be sold): https://www.backblaze.com/cloud-storage/resources/hard-drive-test-data
- [S38] Petrobras 3W repository (data CC BY 4.0, code Apache 2.0): https://github.com/petrobras/3W
- [S39] Building Data Genome 2 repository README (3,053 meters, 1,636 buildings, 2016-2017, no fault labels mentioned): https://github.com/buds-lab/building-data-genome-project-2

[S36]-[S38] support the proposals' rejected alternatives (MetroPT, Backblaze and 3W), which are not re-argued here. See [L8]-[L10].

**WebSearch:** one attempt, refused because the shared per-turn budget was used up. No results.

**Local files read in this session**
- [L1] `C:\Users\HP\OneDrive\Desktop\tata\README.md`
- [L2] `C:\Users\HP\OneDrive\Desktop\tata\FINAL_HANDOFF.md`
- [L3] `C:\Users\HP\OneDrive\Desktop\tata\product\PRODUCT_STATUS.md`
- [L4] `C:\Users\HP\OneDrive\Desktop\tata\product\TECHNICAL_DEBT.md`
- [L5] `C:\Users\HP\OneDrive\Desktop\tata\product\DECISION_LOG.md`
- [L6] `C:\Users\HP\OneDrive\Desktop\tata\product\research\V_judge_decision.md`
- [L7] `C:\Users\HP\OneDrive\Desktop\tata\product\research\V_adversarial_review_wind_choice.md`
- [L8] `C:\Users\HP\OneDrive\Desktop\tata\product\research\proposals\V_data_first.md` (searched)
- [L9] `C:\Users\HP\OneDrive\Desktop\tata\product\research\V_access_first.md` (as summarised in the task brief; not re-read)
- [L10] `C:\Users\HP\OneDrive\Desktop\tata\product\research\V_decision_value_first.md` (as summarised in the task brief; not re-read)

**Local computations** (Python, 2026-10-18): Wilson 95% intervals; MNRE row, column and share checks; Kelmarsh and Penmanshiel ratings; INOX Green share; EDP distinct failure records; score sums under five weightings and the G1 scenario.

---

## Fact-check log (2026-10-18)

A fact-check pass re-opened 37 of the 39 web sources on 2026-10-18 with WebFetch. It did not re-open [S8] (HTTP 403 earlier) or [S11]. The IEA EDP summary, NIWE notice, CIRT profile and India Cooling Action Plan PDFs were extracted locally with `pdftotext`. The MNRE policy scan was re-rendered with `pdftoppm`, and printed pages 1, 2, 3, 7 and 10 plus the cover circular were read. The local computations were re-run: Wilson half-widths, MNRE row, column and share checks, Kelmarsh and Penmanshiel per-turbine ratings, the INOX Green share, the EDP distinct-record count, and the score sums under every weighting. All matched.

**Confirmed as written (sample):**
- MNRE installed wind capacity 59,201.07 MW, with the 30.09.2026 column date against the 31 August 2026 heading [S15].
- CARE v6 facts: published 9 July 2025; CC BY-SA 4.0; 5.5 GB zip; the MD5; 36 turbines; 89 years; 86/257/957 features; 45/50 datasets on Zenodo; Farm A from the EDP platform; no rating stated [S1].
- From the CARE paper: per-farm 11/11, 6/9 and 27/31; the 0.66 and 0.5 figures; Accuracy weighted ×2; criticality 72; normal status IDs 0 and 2; the Farm A 14-day and 3-day status marking; estimated starts; B/C zeros for missing values [S2].
- Hill of Towie v2.1.0: 21 SWT-2.3-VS-82 turbines, AeroUp dates, downtime ending August 2024, 29.7 GB [S3].
- Kelmarsh 12.3 MW / 6 and Penmanshiel 28.7 MW / 14, from KMZ file names [S4][S5].
- EDP failure-log counts and dates, operation-log counts, signal list, "Restricted (NDA)" item and sign-in requirement [S7].
- SCANIA Component X: 2,272 repaired and 21,278 censored vehicles; cost matrix 7-10 and 200-500 [S12][S13]. APS costs 10 and 500 [S14].
- MNRE policy: eligibility below 2 MW; the state table; UL 4143 certification; §11 data management; valuation-model inputs; 25.406 GW; circular dated 7 December 2023 [S16].
- NIWE: internship terms [S17], open datasets [S18], WT-MARUT scope [S19].
- UL 4143 scope [S20]; May and McMillan (2013) [S21].
- Vendor figures as quoted: Turbit [S22][S23], ONYX [S24][S25], INOX Green [S26], Clir [S28].
- CIRT 72.4%, 164,139, 80,900 and "severe financial crunch" [S29].
- ICAP quotations [S32]; LBNL page [S33]; BDG2 [S34][S39]; Augury chillers [S35]; Backblaze terms [S37]; 3W licences [S38].

**Corrected in this pass:**
1. **KP Group [S27].** The text said wind "is not mentioned". The case study does mention wind, but only in KP Group's company background; the O&M deployment described covers "solar and hybrid power plants". Corrected in section 6, objection 7.
2. **CARE 0.66 scope [S2].** The text marked pooled-or-per-farm as UNVERIFIED. The paper's Figure 3 caption says "over all 95 sub-datasets", and the paper has no per-farm score table. G0 was updated to say a Farm A-only score is not comparable with 0.66, and the item was removed from the UNVERIFIED list.
3. **EDP Wind Farm 1 [S7].** The text said the farm "has 5 turbines". The IEA summary says the data cover "5 selected wind turbines", and the farm's location dataset lists 16 turbines. Corrected in section 6, objection 1.
4. **Uptake [S31].** The text said the page "shows bus fleet prioritisation". The page lists a Buses industry and a "Risk Explorer" feature in general fleet terms, with no bus-specific prioritisation. Corrected in sections 4 and 10 and labelled as a vendor claim.
5. **MetroPT-3 [S36].** The text read as if the four air-leak events spanned February-August 2020. February-August 2020 is the data span. The four events fall between 18 April and 15 July 2020. Corrected in section 10.
6. **May and McMillan [S21].** "can change the cost-benefit" was corrected to the source's wording, "may alter the cost benefit".
7. **CIRT [S30].** "Technical arm" was corrected to the page's wording, "the technical organ of ASRTU".
8. **CARE event examples [S1].** These were reworded to say they come from the record's version notes ("gearbox bearing damage", event 51; "high temperature in transformer cell", events 34, 7 and 19).
9. **BDG2 [S39].** "Meter data only" was narrowed to "hourly meter readings, no fault labels mentioned".
10. **Penmanshiel [S6].** The audit record [S6] also runs on Penmanshiel v3 and includes a Penmanshiel replication. This was added to the Penmanshiel limits; its findings are UNVERIFIED.
11. **Section 11.** "RUL is validated only on SIMULATED data" was changed to "evaluated only", to avoid implying a validation claim.

**Checked for claims of work that does not exist.** No statement in this record claims an interview, customer, pilot, outreach contact or result on wind data. Sections 2 and 7 state that none has happened, and the outreach steps are labelled PLANNED. (Later update: sections 1, 2 and 9 now cite results on SYNTHETIC wind data from the product's own generator: section 1's decision row quotes the fresh held-out 0.44 healthy alarm episodes per turbine-year, with its 95% interval up to about 2.45, an earlier run's 5.74 (sustain 6) and 39 drifting-sensor alarm episodes, and its message row says the thresholds were tuned on synthetic data. They are labelled SYNTHETIC. Section 5's status note on reason 5 describes the shipped threshold rule but quotes no result. There is still no result on real wind data.)

**Still not checked by this pass:** the claims marked "per R2/R5, not re-opened" (CEA cyber rules, DPDP) and the summaries of [L8]-[L10].

**Sources re-opened by the fact-check** (accessed 2026-10-18): [S1]-[S7], [S9], [S10], [S12]-[S39] at the URLs listed in "Sources". In addition, https://zenodo.org/records/16807551, https://zenodo.org/records/16807304 and https://zenodo.org/records/22662930 were re-opened for farm locations: Kelmarsh "in the UK", Penmanshiel "in the UK", and Hill of Towie "a commercial wind farm in Scotland".
