# Domain-gap report

**The question:** what separates the data SentinelLoop has been tested on from the data and conditions of its intended first use (PD-10)?
- **Tested on:** NASA C-MAPSS (simulated turbofans) and our synthetic wind SCADA.
- **Intended first use:** geared ~2.0–2.3 MW onshore turbines in India, monitored through 10-minute SCADA.

Each gap is rated by its effect on a claim, together with what would close it. Facts carry their source. Anything not checked in this workspace is marked UNVERIFIED.

## 1. Simulated turbofans (C-MAPSS) → wind turbines

| gap | effect | consequence |
|---|---|---|
| C-MAPSS engines run to failure; turbines are repaired before failure, and public wind data carry ~45 fault events, not trajectories (`research/R4_datasets.md`) | no RUL model can be validated for wind | RUL is not offered for wind (PD-11). The C-MAPSS RUL results (rung 1) carry no weight for wind |
| C-MAPSS degradation is one simulated mechanism per subset; field faults are many and mixed | performance on C-MAPSS says nothing about wind fault detection | only the software paths (data gates, states, workflow) carry over, and they are re-tested on wind (`tests/test_app_wind.py`) |
| C-MAPSS has no timestamps (a cycle index; 3 h per cycle is our assumption) | scheduling-simulator time scales are assumptions | `SCHEDULING_EVALUATION.md` §5 |

## 2. Synthetic wind SCADA → real wind SCADA

`synthetic_wind.py` deliberately simplifies. Every simplification below makes the synthetic task easier than reality, so synthetic detection rates (`evidence/wind_synthetic/w1.md` and `w2.md`: 36/36) are **not** an estimate of real performance.

Even on this easier task, the shipped setting leaves two unfavourable results. The setting is inspect margin 1.25 and sustain 12 points (2 h), chosen in W2 on separate tuning fleets (PD-15). Both results are SYNTHETIC (`evidence/wind_synthetic/w2.md`):
- **False alarms.** On the held-out W1 fleets, healthy turbines give **2.65 alarm episodes per turbine-year** (6 in 2.27 turbine-years). That is above W2's own target of 1.0 and above the proposed pilot ceiling of 2 (`KNOWN_LIMITATIONS.md` E7). On the tuning fleets the same setting gave 0.88.
- **Assessability.** A valid assessment was possible at only **54–59% of hourly instants** (W2's assessable share, mean over each set of six fleets). Almost all of the rest was out of scope: data-quality failures were rare, since each fleet has one stuck sensor for one day (`product/experiments/w2_threshold_revisit.py`). There is no curtailment in the synthetic data at all.
  - This is not a measure of wind-driven idle time. In each fleet six of ten turbines get an injected component failure, and the generator stops them for the rest of the record (`synthetic_wind.py`). Those stops are about 15–22% of all instants; without them the per-fleet share is about 0.52–0.80 (a re-count on W2's fleets, not part of `w2.md`).
  - The model makes no statement unless the turbine produced power above 5% of rated in at least half of its 8-hour scoring window (`nbm.applicability`). An idle instant inside a mostly operating window is still assessed, on the last operating score.

| synthetic simplification | real-world counterpart | likely effect on real performance |
|---|---|---|
| first-order thermal lag driven only by power and ambient | cooling-system control (fans and thermostats switching), seasonal cooling changes, oil-viscosity effects, sun load on the nacelle | larger and structured residuals → higher thresholds → later detection or more false alarms |
| a fault adds heat that grows smoothly to failure | real faults are intermittent, step-like, or show in vibration long before temperature; many never heat the measured point | lower detection rate; some fault types undetectable from SCADA temperatures |
| small per-turbine offsets, constant over time | sensor replacements, component swaps and retrofits shift baselines | needs re-commissioning after logged maintenance (rule exists; the trigger from work-order history is PLANNED) |
| no curtailment, derating, icing or grid events | curtailment is reported as frequent in some Indian states (UNVERIFIED in this workspace) | idle periods → more out-of-scope time. W2's 41–46% without a valid assessment on synthetic data is not a baseline for this, since about a fifth of its instants are turbines stopped after an injected failure (above). Turbine status codes, alarm codes and curtailment or derating setpoints are **not in the data contract** (`KNOWN_LIMITATIONS.md` M3). The platform therefore cannot tell a grid backdown, a manual or OEM stop and a fault trip apart: all of them show as `insufficient_operation`. A derated turbine still producing above 5% of rated is scored like any other operation, with no flag that it is derated, although derating changes the load–temperature relation. Icing and grid events are not modelled |
| idealised 10-minute grid, rare gaps | real exports have gaps, duplicated stamps, clock changes and unit inconsistencies | the ingestion contract handles these explicitly; rejection rates on real exports are unknown |
| one healthy-training period per turbine is cleanly healthy | real "healthy" periods contain undetected developing faults | thresholds set too high; developing faults absorbed into the baseline (commissioning risk, PD-12) |
| slow sensor drift and slow component heating look alike | the same on real turbines without redundant sensors | drift raises alarms, and so inspection orders rather than instrument checks: 37 alarm episodes from 6 drifting sensors on the held-out fleets at sustain 12 (`w2.md`), and 193–293 alarm-hours per drifting sensor at the earlier sustain 6 (`w1.md`). An inspection is the only discriminator (`KNOWN_LIMITATIONS.md` M1) |

## 3. European public turbines → Indian fleet

| gap | status | effect |
|---|---|---|
| **Climate.** Public data are from Portugal (CARE Farm A), German offshore (B), the UK (Kelmarsh, Penmanshiel, Hill of Towie). Indian sites see higher ambient temperatures, monsoon seasons and dust (UNVERIFIED in this workspace) | open | the ambient-temperature envelope check will declare Indian conditions out of scope for a model trained only on cooler sites. **This is intended:** a model must be commissioned and trained on the customer's own turbines, over a period that covers the ambient range of the season it will assess (`PILOT_PROTOCOL.md` §3) |
| **Turbine models.** Public data: Senvion MM82/MM92, Siemens SWT-2.3, unnamed CARE turbines. Which models dominate the Indian 2.0–2.3 MW fleet, and whether they are geared, is UNVERIFIED (choice record §1) | open | signal sets and thermal behaviour differ by model; needs a per-model mapping and per-turbine training |
| **Signal availability and naming.** CARE farms have 86, 257 and 957 features (arXiv:2404.10320). Indian exports may carry fewer drivetrain temperatures | open | a turbine without a measured gearbox-bearing temperature cannot have that target. **Scope is not yet declared per signal set.**<br>• Every turbine must deliver all nine required wind signals, including all three target temperatures, under the platform's names and units (`DATA_CONTRACTS.md` §1). Only `pitch_angle` is optional.<br>• A signal that is never delivered is a lasting DATA_QUALITY_FAILURE (`missing_signal`), which raises instrument-check orders.<br>• Per-site tag mapping is PLANNED (FR-B3, `KNOWN_LIMITATIONS.md` P12). Per-model or per-turbine signal subsets are not built, and no requirement or limitation entry covers them yet. G0's adapter omits absent optional inputs (`PREREGISTRATION.md` §10.1); the product does not yet |
| **Labels.** Public failure labels come from operator logbooks (EDP) or curated events (CARE). A customer's labels depend on its work-order quality (`research/R1_maintenance_workflows.md`: no sourced data on Indian work-order quality) | open | rung-4 back-tests may be limited by label quality, not model quality |
| **Who controls data and maintenance.** OEM full-service contracts may leave the owner without SCADA access or maintenance control (UNVERIFIED; G1 tests it) | open | may block rung 4 regardless of model quality |
| **Season.** Indian wind is described as strongly seasonal, with long low-wind periods outside the monsoon months. This is a role-played reviewer's outside knowledge (`ADVERSARIAL_REVIEW.md` om_manager-8), UNVERIFIED in this workspace | open | idle hours are out of scope, so the calendar share of assessable time falls in low-wind months. The pilot criteria therefore measure assessability over operating hours, and the pilot plan declares its season and expected share before day 1 (`PILOT_ACCEPTANCE_CRITERIA.md` B1/S1, `PILOT_PROTOCOL.md` §3) |

## 4. What closes each gap

| gap | closed by | rung |
|---|---|---|
| real fault detectability and false-alarm rate | G0 on CARE: pre-registered; under Amendment 1, Farm A is the primary decision against an internal baseline, and G0 also reports product alarm episodes per turbine-year at sustain 12. Then a Kelmarsh/Penmanshiel false-alarm and drift check | 3 |
| assessability on real data | G0 reports it per farm (`PREREGISTRATION.md` §10.2); then the back-test on the partner's history reports it per month, over operating hours | 3, 4 |
| curtailment, derating and stops | operating-state signals per site (PLANNED, `KNOWN_LIMITATIONS.md` M3); until then, the partner's status and curtailment logs compared offline | 4, 5 |
| Indian climate, turbine models, signal sets | a customer's historical export, trained and evaluated per turbine | 4 |
| label quality, maintenance practice, who acts | G1 conversations, then a back-test with the customer's work-order log | 4 |
| live data problems, alarm burden, operator trust | shadow pilot | 5 |
| value | operational use against a pre-agreed baseline | 6 |
