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

`synthetic_wind.py` deliberately simplifies. Every simplification below makes the synthetic task easier than reality, so synthetic detection rates (`evidence/wind_synthetic/w1.md`: 36/36) are **not** an estimate of real performance.

| synthetic simplification | real-world counterpart | likely effect on real performance |
|---|---|---|
| first-order thermal lag driven only by power and ambient | cooling-system control (fans and thermostats switching), seasonal cooling changes, oil-viscosity effects, sun load on the nacelle | larger and structured residuals → higher thresholds → later detection or more false alarms |
| a fault adds heat that grows smoothly to failure | real faults are intermittent, step-like, or show in vibration long before temperature; many never heat the measured point | lower detection rate; some fault types undetectable from SCADA temperatures |
| small per-turbine offsets, constant over time | sensor replacements, component swaps and retrofits shift baselines | needs re-commissioning after logged maintenance (rule exists; the trigger from work-order history is PLANNED) |
| no curtailment, derating, icing or grid events | curtailment is reported as frequent in some Indian states (UNVERIFIED in this workspace) | idle and derated periods → more out-of-scope assessments; derating changes the load–temperature relation |
| idealised 10-minute grid, rare gaps | real exports have gaps, duplicated stamps, clock changes and unit inconsistencies | the ingestion contract handles these explicitly; rejection rates on real exports are unknown |
| one healthy-training period per turbine is cleanly healthy | real "healthy" periods contain undetected developing faults | thresholds set too high; developing faults absorbed into the baseline (commissioning risk, PD-12) |
| slow sensor drift and slow component heating look alike | the same on real turbines without redundant sensors | drift raises alarms (`w1.md`: 193–293 alarm-hours per drifting sensor); an inspection is the only discriminator |

## 3. European public turbines → Indian fleet

| gap | status | effect |
|---|---|---|
| **Climate.** Public data are from Portugal (CARE Farm A), German offshore (B), the UK (Kelmarsh, Penmanshiel, Hill of Towie). Indian sites see higher ambient temperatures, monsoon seasons and dust (UNVERIFIED in this workspace) | open | the ambient-temperature envelope check will declare Indian conditions out of scope for a model trained only on cooler sites. **This is intended:** a model must be commissioned and trained on the customer's own turbines |
| **Turbine models.** Public data: Senvion MM82/MM92, Siemens SWT-2.3, unnamed CARE turbines. Which models dominate the Indian 2.0–2.3 MW fleet, and whether they are geared, is UNVERIFIED (choice record §1) | open | signal sets and thermal behaviour differ by model; needs a per-model mapping and per-turbine training |
| **Signal availability and naming.** CARE farms have 86, 257 and 957 features (arXiv:2404.10320). Indian exports may carry fewer drivetrain temperatures | open | a turbine without a measured gearbox-bearing temperature cannot have that target; scope is declared per signal set |
| **Labels.** Public failure labels come from operator logbooks (EDP) or curated events (CARE). A customer's labels depend on its work-order quality (`research/R1_maintenance_workflows.md`: no sourced data on Indian work-order quality) | open | rung-4 back-tests may be limited by label quality, not model quality |
| **Who controls data and maintenance.** OEM full-service contracts may leave the owner without SCADA access or maintenance control (UNVERIFIED; G1 tests it) | open | may block rung 4 regardless of model quality |

## 4. What closes each gap

| gap | closed by | rung |
|---|---|---|
| real fault detectability and false-alarm rate | G0 on CARE (pre-registered); Kelmarsh/Penmanshiel false-alarm and drift check | 3 |
| Indian climate, turbine models, signal sets | a customer's historical export, trained and evaluated per turbine | 4 |
| label quality, maintenance practice, who acts | G1 conversations, then a back-test with the customer's work-order log | 4 |
| live data problems, alarm burden, operator trust | shadow pilot | 5 |
| value | operational use against a pre-agreed baseline | 6 |
