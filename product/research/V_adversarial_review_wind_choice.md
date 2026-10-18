# Adversarial review of the initial vertical choice (wind)

Written 2026-10-18 for the SentinelLoop product team. Role: adversarial reviewer of the judge's choice in `V_judge_decision.md`:
- **Vertical:** Indian onshore wind-farm owner-operators of ageing turbines eligible for repowering or life extension under MNRE's 2023 policy, starting in Tamil Nadu, with NIWE (Chennai) as the institutional door.
- **Asset class:** geared onshore turbines of about 1.5-2.3 MW, monitored only through 10-minute SCADA and alarm/event logs.

My brief was to attack the choice on five points:
1. Would a real maintenance team use the product?
2. Are the public data real and usable? (I opened the licences myself.)
3. Is the pilot path realistic?
4. Is the decision value real?
5. What is the strongest reason to choose differently?

The rule is to reject by default if a claimed fact does not hold.

**Tool status.**
- WebSearch was unavailable: the one call I made returned "this turn's web search budget is used up" (a 200-call limit shared across agents). I ran no searches and did not work around the limit.
- WebFetch worked. I used it only on primary or known URLs.
- I downloaded four PDFs with `curl` into isolated scratch folders and read them locally: the MNRE policy, the NIWE AAP notice, the IEA Wind EDP summary and the CIRT STU profile.
- The MNRE policy is a scanned image. I rendered every page to PNG with `pdftoppm` and read the table values from the page images myself.

**Labels.**
- **Verified (reviewer):** I opened the source in this session and it says what is written.
- **UNVERIFIED:** not confirmed in this session.
- **Vendor claim:** taken from a vendor's own page.
- **Judgement:** my reasoning, not a sourced fact.
- **Computed:** arithmetic I ran locally on figures from a cited source.

**Data types** follow R4: real field, real laboratory, simulated, synthetic.

---

## 1. Verdict: REJECT the choice as specified

The asset class survives: geared onshore turbines of about 2 MW, monitored through 10-minute SCADA, with CARE / EDP / Kelmarsh / Penmanshiel / Hill of Towie as an evidence base. The **vertical framing** around it does not hold up:
- ageing, repowering-eligible owners;
- Tamil Nadu first;
- NIWE as the door;
- "1.5-2 MW matches the public data".

One stated fact is wrong as written. Three inferences built on verified numbers do not follow from those numbers. And under the judge's own weighting, one-point corrections that the evidence supports erase wind's lead.

The four failures:
1. **The band-match claim is wrong as stated.** The choice says "the public data are 2.05-2.3 MW machines".
   - That is true only for the **unlabelled** sets. Kelmarsh and Penmanshiel come to 2.05 MW per turbine (computed from 12.3 MW / 6 and 28.7 MW / 14) [S6][S7]. Hill of Towie is the SWT-2.3-VS-82 [S5].
   - The **labelled** set, CARE, does not state the rated power or type of any farm. The paper says anonymisation removed "the turbine type and the location" for Farms B and C [S1][S2]. The IEA summary of the EDP source data for Farm A gives no rating either [S4].
   - The 2.05-2.3 MW machines also sit **above** MNRE's "below 2 MW" eligibility criterion and outside the table's "1.5-2 MW" column [S8]. The two ranges set side by side in the rationale do not overlap.
2. **The Tamil Nadu start rests on a number that is mostly outside the chosen band.**
   - Of Tamil Nadu's 7,386.5 MW below 2 MW, only 1,473.5 MW (19.9%, computed) is 1.5-2 MW. 4,100 MW (55.5%, computed) is below 1 MW [S8].
   - Nationally, the 1.5-2 MW band is led by Gujarat (1,805.35 MW), then Andhra Pradesh (1,701.2 MW). Tamil Nadu is third [S8].
3. **The "policy-backed decision" does not consume what the product outputs.**
   - The policy's repowering valuation (Annex) is driven by tariff, the 3-year average delivered generation and O&M cost [S8]. Component condition plays no part.
   - The policy also requires life extension to be "assessed and certified by the certification agency" under UL 4143 [S8].
   - The product's output is a SCADA early warning. It is neither a repowering input nor a UL 4143 certificate.
4. **The "verified institutional door" is a door into NIWE's own projects, not to turbine owners or their SCADA.**
   - The AAP is unpaid and on-site with daily attendance. Interns work at the division head's discretion. Publication needs the Director General's approval and a NIWE co-author, and interns sign a data-protection declaration [S9].
   - Policy §11 has NIWE collect "performance related data", with SNAs/CNA and **SLDCs** providing "all necessary data" [S8]. SLDCs are State Load Despatch Centres, i.e. the grid side. Whether NIWE holds any turbine-level 10-minute SCADA is UNVERIFIED.

**Rescoring with the judge's own weights** (data and technical fit doubled):

| | Wind |
|---|---|
| Judge's scores | 27 |
| Data 4→3 (in-class labelled evidence is about 11 events, not 44-45) | 25: ties buses at 25 |
| Also decision value 4→3 (repowering candidates are end-of-life; the policy's decision ignores condition) | 24: buses win at 25 |
| Also access 2→1 | 23 |

All computed (section 5).

A resubmission that keeps wind must meet the conditions in section 7. Otherwise the runner-up (STU depots, diesel-bus aggregates) should be re-tabled for the decision.

---

## 2. Claim-by-claim check

| # | Claim in the choice | Reviewer's check | Result |
|---|---|---|---|
| 1 | CARE to Compare v6: Fraunhofer IEE; 36 turbines, 3 farms, 95 datasets; 45 fault-leading, 50 normal; CC BY-SA 4.0; one 5.5 GB zip, MD5 2547b58c...; published 2025-07-09 | Zenodo page opened: all confirmed. The page also shows "Modified" 12 Oct 2026. It states no rated power or turbine model [S1]. | **Holds** |
| 2 | Paper v2 gives 44/51 (A=11, B=6, C=27) | Confirmed. Normal datasets per farm: A=11, B=9, C=31 [S2] | **Holds**. Discrepancy with the Zenodo v6 page is real. |
| 3 | Data are real field | Paper: anonymised data from operating wind farms (A onshore Portugal; B and C offshore Germany) [S2] | **Holds**: REAL FIELD |
| 4 | "The public data are 2.05-2.3 MW machines" (the band rationale) | True for Kelmarsh, Penmanshiel and HoT (unlabelled) [S5][S6][S7]. Not stated for CARE (any farm) [S1][S2] or the EDP source [S4]. | **Fails as stated**. Labelled-data rating is UNVERIFIED. |
| 5 | 1.5-2 MW is the largest sub-2 MW band: 9,065.35 of 25,396.65 MW, about 35.7% | Scanned table pp.1-2 read: 9,065.35 / 25,396.65 = 35.7% (computed). Larger than 0.5-1 MW (8,276) [S8]. | **Holds** |
| 6 | Tamil Nadu 7,386.5 MW below 2 MW; policy text 25.406 GW | Both confirmed [S8]. But TN's 1.5-2 MW is only 1,473.5 MW (19.9%); 55.5% is sub-1 MW (computed). TN ranks 3rd in the target band. | **Number holds; the inference fails** |
| 7 | India wind capacity 59,201.07 MW as on 30.09.2026 | Confirmed. The section heading on the same page says 31 Aug 2026 [S10]. | **Holds** (date inconsistent on the source page) |
| 8 | No Indian turbine SCADA is public (NIWE open data) | 10 wind-monitoring-station sets plus a 150 m atlas; no turbine SCADA; "© All Rights Reserved" [S11] | **Holds** |
| 9 | EDP Wind Farm 1 logbook: 23 records; 256,231 log records; CC-BY-SA; sign-in | IEA summary (secondary) confirms all four. 5 turbines; no rated power stated. The location file is "Restricted (NDA)" [S4]. EDP primary page returned **HTTP 403** to me [S12]. | **Holds (secondary only)**. EDP's own terms are UNVERIFIED. |
| 10 | Hill of Towie: 21 SWT-2.3-VS-82, 2016-2026 alarm logs, 10-minute downtime, AeroUp dates, CC BY 4.0 | Confirmed. Downtime is "calculated from a combination of the SCADA data and RES operator logs", which the judge had left UNVERIFIED and is now verified. The downtime file **ends August 2024**. No failure or replacement records are described [S5]. | **Holds**, with the downtime ending Aug 2024 |
| 11 | Kelmarsh v4 / Penmanshiel v3: CC BY 4.0, 2016-2024 | Confirmed. "Events data" included; no failure labels; Penmanshiel has no WT03 [S6][S7] | **Holds** |
| 12 | The CC BY-SA 4.0 deed allows commercial adaptation with share-alike | Legal code opened. Share-alike applies "if You Share Adapted Material You produce" (§3(b)). Uses needing no permission are not regulated (§2(a)(2), §8(a)). §4 covers Sui Generis Database Rights [S3]. | **Holds**. See 3.2: the licence risk is narrower than the switch condition assumes (not legal advice). |
| 13 | CARE benchmark: autoencoder 0.66; 0.5 accuracy threshold | Confirmed. If Acc < 0.5 the score equals Acc. Random = 0.5. Isolation forest does not beat 0.5 [S2]. | **Holds** |
| 14 | Wilson half-widths about ±13-14 (44 events) and ±23-25 (11 events) | Recomputed: n=44, 0.130-0.142; n=11, 0.234-0.254; n=12, 0.236-0.246 | **Holds** |
| 15 | May and McMillan 2013: false alarms can reduce the advantage of CM | Strathprints: false-alarm costs "may alter the cost benefit of condition monitoring systems" [S13] | **Holds** |
| 16 | Policy requires LTE assessment "as per the UL 4143" and caps life at 40 years | Confirmed, p.3. The assessment and certification are done "by the certification agency" [S8]. UL 4143 covers LTE "rules and procedures", using a risk approach relating severity to confidence in the failure mode, onshore only [S14]. | **Holds**; the inference about decision value fails (3.4) |
| 17 | Policy §11 tasks NIWE with collecting "performance related data for all the sites" | Confirmed. SNAs/CNA **with SLDCs** provide the data [S8]. | **Holds**; the inference that NIWE is a SCADA door is UNVERIFIED and doubtful |
| 18 | NIWE AAP: Chennai, unpaid, 2 weeks-6 months, UG/PG with 60%, lists "Machine Learning /AI and data analysis" | Confirmed [S9]. Also on the notice: on-site work, NIWE projects, DG approval for publication, NIWE co-author, data-protection declaration, at most 25 interns at a time. | **Holds**; "door" is overstated |
| 19 | Competitors: ONYX 32,000+, Turbit 3,500+ with backtests, INOX Green 11 GW wind O&M and "Predictive Maintenance" | All confirmed as vendor claims [S15][S17][S19]. New: ONYX lists a **Bengaluru, India** office [S16]. Turbit's paid backtest needs 3+ years of SCADA [S18]. | **Holds**; competition is denser in India than the choice states |
| 20 | Runner-up: CIRT 2021-22 shows 72.4% utilisation, 164,139 breakdowns, 80,900 workshop staff | Spot-checked in the PDF text: 72.4% (text), 164,139 (sum of 39,799 + 532 + 123,808), 80,900; "financial crunch" present. The off-road and spare figures (12,817; 22,983) appear in a garbled table, but are consistent with held minus on-road to within about 100 buses (computed) [S20]. | **Holds** (partly checked) |

---

## 3. The attacks

### 3.1 Would a real maintenance team in this vertical use it?

1. **The user is not identified, and the likely holder of data and work orders is not the target.**
   - The vertical names "owner-operators", but the policy's own eligibility list targets turbines that are below 2 MW, past their design life or over 15 years old [S8].
   - In India's wind sector, at least one O&M provider claims "11 GW of Wind O&M assets" [S19] (vendor claim). That is about 18.6% of 59.2 GW (computed; [S10]).
   - Whether the owners of 1.5-2 MW machines, rather than OEM or O&M contractors, control SCADA exports and raise work orders is still **UNVERIFIED**. The judge marked it UNVERIFIED too, and nothing I could open resolves it.
   - The triage agent drafts work orders. If the O&M contractor runs maintenance under contract, the owner has no maintenance team to hand them to (judgement).
2. **Repowering candidates are end-of-life assets.** An early warning is worth most on an asset with many years ahead of it. A turbine being considered for scrapping and replacement has the shortest horizon in the fleet.
   - The policy's own valuation of an old asset (Annex, "PPA value") is the NPV of tariff × average generation minus O&M cost over the remaining PPA years [S8]. Condition does not enter.
   - A major drivetrain failure on such a turbine is as likely to trigger a repowering decision as a repair (judgement). That is a "repair vs repower" decision the product does not currently model.
3. **What remains is the most commoditised layer.** In wind, the product drops its headline capability (RUL with a 90% conformal interval), as the choice concedes.
   - What remains is a normal-behaviour model on 10-minute SCADA. Turbit, for example, sells per-turbine neural networks on SCADA. It names gearbox damage, generator failures and main-bearing exchanges as backtest targets, and accepts exports from Vestas, Siemens Gamesa, Nordex, Enercon and GE [S17][S18] (vendor claims).

### 3.2 Is the claimed public data real and usable?

**What holds.** Every dataset named is REAL FIELD, and every licence I opened allows commercial use:
- CARE: CC BY-SA 4.0 [S1].
- Hill of Towie, Kelmarsh and Penmanshiel: CC BY 4.0 [S5][S6][S7].

**What does not hold, or is overstated:**
1. **In-class labelled evidence is about 11 events, not 44-45.**
   - CARE Farm A, the only onshore labelled farm, has 11 anomaly events and 11 normal datasets on 5 turbines [S2]. Its rated power is not stated anywhere I opened [S1][S2][S4].
   - The other 33 events (paper v2 count) are on anonymised **offshore** turbines with 257 and 957 features [S1][S2]. That is a different asset class, which the judge concedes for the cross-site rung.
   - The EDP logbook covers the same 5 turbines [S4], so it is not independent evidence.
   - At n=11, a measured detection rate of 55-73% carries a 95% Wilson half-width of 23-25 points (computed). About 38 events would be needed to get within ±15 points, and about 89 within ±10 points (computed at p=0.6).
2. **The CC BY sets carry no failure labels.**
   - Hill of Towie gives alarm logs and a downtime series derived from SCADA plus operator logs, which ends August 2024 [S5].
   - Kelmarsh and Penmanshiel give "events data" [S6][S7].
   - Downtime is not a fault label. In-class cross-site claims can cover false-alarm rate and alarm/downtime agreement only, as the judge says.
3. **The EDP licence chain is unverified at the primary source.**
   - CARE Farm A is "based on data from the EDP open data platform" [S1].
   - EDP's own page returned HTTP 403 [S12]. The CC-BY-SA label comes only from the IEA summary [S4].
   - The CARE paper text states no dataset licence of its own; the CC BY-SA in its footer is the paper's licence [S2].
4. **Correction in the choice's favour: CC BY-SA is less blocking than the switch condition fears.**
   - Share-alike binds only when you "Share Adapted Material You produce" (§3(b)). Uses that need no permission under copyright or database rights are not regulated (§2(a)(2), §8(a)) [S3].
   - Internal training and selling alerts is a different act from redistributing a derived dataset (judgement, not legal advice).
   - The live obligation is narrower: any re-published relabelled CARE or EDP subset or benchmark file must carry CC BY-SA. EU sui generis database rights (§4) may apply because the sources are Portuguese and German [S3] (judgement).

### 3.3 Is the pilot path realistic?

1. **NIWE AAP terms** [S9]:
   - interns "work with scientists/engineers on NIWE's projects" and are engaged at NIWE's discretion;
   - they must work from NIWE's office with daily attendance, unpaid, with their own logistics;
   - publication of results needs explicit approval from the Director General, with a NIWE guide as second co-author;
   - interns sign a declaration under NIWE's Data Protection Policy, with legal action threatened for disclosure of "resource data".

   That makes the AAP a way into NIWE's projects. It is not a route to owners. It also restricts publication and data in ways that conflict with using the output as a startup's calling card (judgement).
2. **NIWE's policy role does not obviously involve turbine SCADA.**
   - §11 has NIWE keep a database of "ownership, technology, turbine details, connected SS, land ownership". It also has NIWE collect "performance related data", with SNAs/CNA and SLDCs as the providers [S8].
   - SLDC data are grid-side (judgement). Whether NIWE holds 10-minute turbine SCADA is **UNVERIFIED**.
   - NIWE's newest portal, WT-MARUT, is a supply-chain **traceability** portal. It records component genealogy, dispatch and commissioning, not operational or failure data [S21].
3. **The week-1 gate is too weak to produce evidence.**
   - The judge's gate asks for at least 12 months of 10-minute history plus a fault log.
   - A competitor's paid backtest asks for "Minimum 3 years of SCADA history per turbine, 5+ years ideal" [S18] (vendor claim).
   - A small owner's 12-month export from a few turbines will probably contain few or no labelled drivetrain failures (judgement; Indian failure rates UNVERIFIED). Rung W5 could then measure false alarms but not detection.
4. **Geography.** If the asset band is 1.5-2 MW, Gujarat and Andhra Pradesh hold more of it than Tamil Nadu [S8]. Tamil Nadu's case rests on NIWE being in Chennai and on its sub-1 MW fleet, which is outside the chosen band.

### 3.4 Is the decision value real?

- **Repowering:** the policy's mechanics turn on energy yield (≥1.5× the old project's actual generation), transmission, DISCOM consent, a PPA moratorium of up to 2 years and NPV-based asset valuation [S8]. None of this uses component condition.
- **Life extension:** "assessed and certified by the certification agency" under UL 4143 [S8]. UL 4143's public scope describes a risk-based LTE procedure for onshore turbines [S14].
  - Whether an LTE assessment uses SCADA history or condition monitoring evidence is **UNVERIFIED**; the full standard was not read.
  - At best, the product could supply evidence to the certifier. It does not make the decision.
- **Routine maintenance on these assets** is a real decision. But its per-event cost in India and who pays for it under O&M contracts are **UNVERIFIED** [judge's list].
- **Net (judgement):** the policy proves a decision exists. It does not prove that decision needs SentinelLoop. Decision value should be 3, not 4, until an owner or O&M provider confirms that SCADA early warning changes a spend decision on these turbines.

### 3.5 Competition, re-checked (vendor claims)

| Vendor | What its pages show |
|---|---|
| ONYX Insight | "32,000+ turbines monitored", "catching faults up to 24 months ahead", 15 CMS hardware types [S15]. Lists a **Bengaluru, India** office [S16]. |
| Turbit | "3500+" turbines, "40+ Customers Worldwide" [S17]. A paid one-off backtest on exports from major OEMs, reviewed with the customer [S18]. This is the same offer as SentinelLoop's proposed rung W5. |
| IBM Maximo Renewables | Automatically creates and prioritises work orders [S22]. Its KP Group case study names a customer "headquartered in Gujarat, India" with 1.4 GW across 70+ sites. The O&M described covers solar and hybrid plants, with anomaly alerts [S23]. |
| INOX Green | 11 GW of wind O&M; lists "Predictive Maintenance" [S19] |
| Clir | Reconciles "OEM calculations" and generates "dispute-ready reports" [S24] |

Indian buyers do buy renewable asset-performance software from global vendors, and at least one SCADA-analytics incumbent has an Indian office. The competition score of 2 is fair, not generous.

---

## 4. What still holds (so the team does not over-correct)

- Wind is still the only one of the three options with **real field, commercially licensed, in-form** public data (10-minute SCADA) [S1][S5][S6][S7]. The 3-6 month evidence ladder (CARE Farm A score vs 0.66; conformal false-alarm control on normal datasets; drift and retrain gates across the HoT AeroUp dates) can run with no customer. It is worth running whatever vertical is chosen, because it is the only real-data evidence the team can produce now.
- All MNRE numbers quoted by the judge are correct as numbers [S8][S10].
- False alarms are a documented cost driver [S13], and CARE ships normal datasets for measuring them [S1].
- Licence risk on CARE is narrower than the switch condition assumes (3.2), though this is not legal advice.

---

## 5. Rescoring sensitivity (computed)

Scores are 1-5 per criterion: data, access, decision value, technical fit, competition, regulation. "Weighted" doubles data and technical fit, the judge's own choice.

| Scenario | Wind (D,A,DV,TF,C,R) | Equal sum | Weighted | Buses weighted | Winner (weighted) |
|---|---|---|---|---|---|
| Judge's scores | 4,2,4,4,2,3 | 19 | 27 | 25 | Wind |
| Data 4→3 (in-class labels about 11 events; rating unknown) | 3,2,4,4,2,3 | 18 | 25 | 25 | **Tie** |
| + decision value 4→3 (policy decision ignores condition; end-of-life assets) | 3,2,3,4,2,3 | 17 | 24 | 25 | **Buses** |
| + access 2→1 (NIWE AAP is not an owner door; owner data control unverified) | 3,1,3,4,2,3 | 16 | 23 | 25 | **Buses** |

Chillers stay at 20 weighted. The bus scores are left as the judge set them. I did not re-attack them here beyond the spot-check in row 20 of section 2. They carry their own UNVERIFIED access (depot records may be on paper) and an adjacent-only public dataset (SCANIA trucks).

---

## 6. Strongest reason to choose differently

Wind's lead rests on one criterion: in-class real labelled data. On inspection, that criterion amounts to about 11 onshore events on 5 turbines of unstated rating, plus unlabelled UK farms. Its access and decision-value story rests on a policy and an institute that do not touch turbine-level condition data.
- Correct either the data or the decision-value score by one point and wind no longer wins under the judge's own weights (section 5).
- With the evidence advantage that thin, the option with the lower competitive density and a verified recurring, capacity-constrained decision (bus depots: 164,139 breakdowns and 72.4% utilisation in CIRT 2021-22 [S20]) deserves to be re-tabled.
- The other credible alternative keeps the asset class but changes the vertical. Instead of ageing sub-2 MW owners, target whoever **runs recurring maintenance on about 2-2.3 MW geared fleets and controls their SCADA**. That could be an IPP asset-management team or an independent O&M provider. This matches the public data's turbine size and removes the end-of-life problem.
  - The Indian fleet composition, gearbox share and data rights for this alternative are all **UNVERIFIED**, and it faces the same incumbents (3.5).

---

## 7. Required changes before wind can be accepted

1. **Restate the data claim honestly.** In-class labelled evidence is CARE Farm A: 11 events (recount from the v6 files), 5 turbines, rating not stated. The offshore 33-34 events are a cross-asset rung. Re-score data at 3 unless the Farm A turbines are confirmed to be geared and about 2 MW.
2. **Fix the band logic.** Either target "below 2 MW" (policy-eligible, and Indian model mix UNVERIFIED) and admit that no public labelled data match it, or target 2-2.3 MW geared fleets (matches the public data) and drop the repowering-eligibility hook. Do not juxtapose the two.
3. **Choose geography from the band data**, or justify Tamil Nadu explicitly by NIWE's location alone. Gujarat (1,805.35 MW) and Andhra Pradesh (1,701.2 MW) lead the 1.5-2 MW band [S8].
4. **Replace "policy-backed decision"** with a decision someone has confirmed they make with SCADA evidence: inspection prioritisation under a crane or technician budget, OEM availability disputes, or evidence for a UL 4143 assessor (UNVERIFIED). Re-score decision value at 3 until confirmed.
5. **Reclassify NIWE** from "institutional door" to "optional internship with publication and data restrictions". Before any work on NIWE data, get written clarification from NIWE that results can be published and reused by the team.
6. **Make the access test the first gate, not a later switch condition.** Within 2-4 weeks, hold 3-5 conversations with owners, IPPs or O&M providers. Pass only if at least one party can legally share at least 3 years of 10-minute SCADA plus a failure or work-order log for turbines of a stated model. Three years matches what a competitor asks for its own backtest [S18]. If the gate fails, switch to the runner-up rather than continuing on public data alone.
7. **Pre-register the falsification test**: CARE Farm A score against the 0.66 autoencoder and the 0.5 accuracy floor, reported with Wilson intervals. Run it regardless of the vertical decision.
8. **Licence note:** keep CARE- and EDP-derived published artefacts under CC BY-SA. Record that §3(b) share-alike is triggered by Sharing Adapted Material. Get the EDP primary terms, which returned 403 to me, before relying on Farm A commercially.

---

## 8. Items that remain UNVERIFIED

- Rated power, model and drivetrain type of the CARE Farm A (EDP) turbines, and of CARE Farms B and C.
- India's installed 1.5-2 MW model mix and gearless share. Wikipedia describes Vensys as a "German gearless wind turbine manufacturer" with a licensee named "ReGen" [S25], but it gives no country or Indian capacity. NIWE's §11 database and the ALMM/RLMM lists are the places to resolve this; the ALMM page did not load [S26].
- Whether Indian owners, rather than OEM or O&M contractors, control SCADA exports and work orders.
- Whether NIWE holds turbine-level SCADA, and whether AAP output may be reused commercially.
- Whether UL 4143 LTE assessments consume SCADA or condition-monitoring evidence.
- Per-event cost of drivetrain failures on Indian sub-2 MW turbines.
- EDP Open Data primary licence terms (HTTP 403).
- Suzlon's O&M fleet size and installed base by model. Suzlon pages returned 404 or 500 or gave no figures [S27]. Wikipedia gives only "10,000 megawatts installed ... in India" in January 2017 [S28].
- Repowering uptake since December 2023 (no search available).
- Final status of CEA power-sector cyber regulations (not re-checked).

---

## Sources

All accessed 2026-10-18. Opened in this session with WebFetch, or with `curl` for PDFs.

- [S1] Zenodo, CARE To Compare v6 (real field; CC BY-SA 4.0): https://zenodo.org/records/15846963
- [S2] arXiv 2404.10320v2, CARE to Compare paper (HTML): https://arxiv.org/html/2404.10320v2
- [S3] CC BY-SA 4.0 legal code: https://creativecommons.org/licenses/by-sa/4.0/legalcode.en
- [S4] IEA Wind, EDP OpenData Details (PDF; curl + pdftotext): https://iea-wind.org/wp-content/uploads/2024/07/EDP-OpenData-Details.pdf
- [S5] Zenodo, Hill of Towie v2.1.0 (real field; CC BY 4.0): https://zenodo.org/records/22662930
- [S6] Zenodo, Kelmarsh v4 (real field; CC BY 4.0): https://zenodo.org/records/16807551
- [S7] Zenodo, Penmanshiel v3 (real field; CC BY 4.0): https://zenodo.org/records/16807304
- [S8] MNRE, National Repowering & Life Extension Policy for Wind Power Projects 2023 (scanned PDF; curl, pages rendered with pdftoppm and read): https://cdnbbsr.s3waas.gov.in/s3716e1b8c6cd17b771da77391355749f3/uploads/2023/12/202312131874296229.pdf
- [S9] NIWE Academic Associate Programme notice (PDF; curl + pdftotext): https://niwe.res.in/static/pdf/NIWE-AAP_Internship_Programme.pdf
- [S10] MNRE Physical Progress: https://mnre.gov.in/en/physical-progress/
- [S11] NIWE Open Datasets: https://niwe.res.in/Open_data_Set/open_wind_dataset/
- [S12] EDP Open Data (HTTP 403, no content): https://www.edp.com/en/innovation/open-data/data
- [S13] Strathprints 54903, May and McMillan (2013): https://strathprints.strath.ac.uk/54903/
- [S14] UL Standards, UL 4143 product page (scope only): https://www.shopulstandards.com/ProductDetail.aspx?productId=UL4143
- [S15] ONYX Insight home page (vendor): https://www.onyxinsight.com/
- [S16] ONYX Insight locations (vendor): https://onyxinsight.com/company/our-locations/
- [S17] Turbit home page (vendor): https://www.turbit.com/
- [S18] Turbit backtest page (vendor): https://www.turbit.com/backtest
- [S19] INOX Green home page (vendor): https://www.inoxgreen.com/
- [S20] CIRT, STUs Profile and Performance 2021-22 (PDF; curl + pdftotext; real field administrative statistics): https://www.asrtu.org/resource/front/uploads/PROFILE_PERFORMANCE-2021-22.pdf
- [S21] NIWE WT-MARUT portal: https://wtmarut.niwe.res.in
- [S22] IBM Maximo Renewables (vendor): https://www.ibm.com/products/maximo/renewables
- [S23] IBM case study, KP Group (vendor): https://www.ibm.com/case-studies/kp-group
- [S24] Clir home page (vendor): https://www.clir.eco/
- [S25] Wikipedia, Vensys (secondary): https://en.wikipedia.org/wiki/Vensys
- [S26] IWTMA home, ALMM list and data repository pages: https://www.indianwindpower.com/ ; https://www.indianwindpower.com/almm-list/ ; https://www.indianwindpower.com/data_repositry/index.php ; https://www.indianwindpower.com/publication/almm-wind/ (socket hang-up, no content)
- [S27] Suzlon pages (no usable figures): https://www.suzlon.com/ ; https://www.suzlon.com/in-en/ (404) ; https://www.suzlon.com/our-businesses/products/ (500) ; https://www.suzlon.com/investors/financial-reports/ (500)
- [S28] Wikipedia, Suzlon Energy (secondary): https://en.wikipedia.org/wiki/Suzlon_Energy

Also opened, used only for context or with no usable result:
- https://en.wikipedia.org/wiki/Wind_power_in_India: secondary; no OEM shares.
- https://mnre.gov.in/en/wind-overview/: no repowering or OEM data.
- https://niwe.res.in/ and https://niwe.res.in/department/department_s&r/: ALMM supported by NIWE; no list linked.
- https://en.wikipedia.org/wiki/Regen_Powertech and https://en.wikipedia.org/wiki/Wind_World_India: both 404.
- https://standardscatalog.ul.com/ProductDetail.aspx?productId=UL4143: DNS failure.
- https://www.indianwindpowerassociation.com/: DNS failure.

**WebSearch:** one attempt, refused because the shared per-turn budget was exhausted.

**Local files read:**
- `C:\Users\HP\OneDrive\Desktop\tata\product\research\V_judge_decision.md`
- `C:\Users\HP\OneDrive\Desktop\tata\product\research\proposals\V_data_first.md`
- `C:\Users\HP\OneDrive\Desktop\tata\product\research\R*.md` (searched for wind-related entries)

**Local computations** (Python, 2026-10-18): Wilson intervals; MNRE table shares; rescoring.
