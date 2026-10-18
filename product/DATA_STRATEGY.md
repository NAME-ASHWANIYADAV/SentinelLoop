# Data strategy

Status 2026-10-18. The vertical is provisional and gated (PD-10): Indian onshore wind, geared ~2.0–2.3 MW turbines, 10-minute SCADA.

## 1. Position

- SentinelLoop has **no customer data**. Its models have run only on:
  - simulated engines (NASA C-MAPSS);
  - our own synthetic wind SCADA.
- The chosen vertical has public real field data in the same form a customer would export: 10-minute SCADA with alarm, status and some failure logs. That is the main reason it was kept (choice record §5).
- No Indian turbine SCADA is public. Every public real dataset available is European. The gap between European test data and Indian turbines is a stated risk (`DOMAIN_GAP_REPORT.md`).

## 2. Datasets and their role

| dataset | class | licence | role | status |
|---|---|---|---|---|
| NASA C-MAPSS FD001–FD004 | SIMULATED | no licence stated (R4: needs written confirmation for commercial use) | method development; scheduling simulator inputs; no product claim | in use |
| `synthetic_wind.py` | SYNTHETIC | ours | behaviour tests and regression tests for every wind code path; ladder rung 2 | in use (`tests/test_app_wind.py`, `product/evidence/wind_synthetic/w1.md`) |
| CARE to Compare v6 (Zenodo 15846963) | PUBLIC REAL FIELD | CC BY-SA 4.0 | G0 falsification test; rung 3. 95 datasets, 44 with a labelled fault-leading anomaly | pre-registered; **download (5.50 GB) awaiting approval** |
| Kelmarsh v4 (Zenodo 16807551), 6 Senvion MM92 | PUBLIC REAL FIELD | CC BY 4.0 | false-alarm rate and drift on real healthy turbines across seasons; no curated failure list | not downloaded (yearly zips 98–716 MB) |
| Penmanshiel v3 (Zenodo 16807304), 14 Senvion MM82 | PUBLIC REAL FIELD | CC BY 4.0 | as Kelmarsh; a second farm for cross-site checks | not downloaded (~7.5 GB) |
| Hill of Towie v2.1.0 (Zenodo 22662930), 21 Siemens SWT-2.3 | PUBLIC REAL FIELD | CC BY 4.0 | alarm logs and operator-derived downtime; turbine class closest to the 2.3 MW target | not downloaded (29.7 GB, too large for this machine's free disk) |
| SCANIA Component X | PUBLIC REAL FIELD (trucks) | CC BY 4.0 | runner-up vertical (bus depots): RUL-with-censoring benchmark | not downloaded (PLANNED if the runner-up is chosen) |

## 3. Rules

1. **Provenance.** Every training or evaluation run records the dataset version, file checksums, the code commit and the data class in the model manifest or result file.
2. **Licence.**
   - Raw third-party data never enter git (`data/external/` is ignored).
   - CC BY sources are attributed.
   - Files derived from CC BY-SA data keep the CC BY-SA licence. Aggregate metrics are not derived datasets (a licence review is PLANNED, choice record §7).
3. **Untrusted input.**
   - A downloaded archive goes into its own new directory and is parsed only with `python -I`.
   - Nothing shipped in an archive is executed.
   - Checksums are verified before use.
4. **Splits.** By turbine and by farm, never random time windows. A training period never overlaps the period it is evaluated on. Thresholds come from healthy data only.
5. **Labels as evaluation masks.** CARE status IDs (normal = 0 and 2) choose which rows are scored. They are never model inputs.
6. **Pre-registration.** Rung 3 and above need a committed protocol before the data are opened (`VALIDATION_LADDER.md`). G0's protocol is `product/evidence/g0/PREREGISTRATION.md`, committed in b40fccd.
7. **Customer data (rung 4 and above, none yet).**
   - A written data-sharing agreement covering purpose, retention, deletion and who may see what.
   - Data stay on infrastructure the customer approves.
   - Technician names are pseudonymised in analysis copies (India's DPDP Act duty noted in R5; not re-verified).
   - Customer data are never used to train a model shared with another customer without written consent.

## 4. What a first customer would need to export (hypothesis for G1)

- At least 3 years of 10-minute SCADA for the turbines in scope. Signals: wind speed, active power, rotor and generator speed, pitch, ambient and nacelle temperature, and gearbox and generator temperatures as available.
- Alarm and event logs, and turbine status codes.
- The failure or work-order log: date, turbine, component, action, downtime.
- Turbine model, rating, drivetrain type, commissioning date, and component replacements or retrofits (re-baselining points).
- Whether the owner, the OEM or an O&M contractor controls the export, and under what contract.

## 5. Synthetic data policy

Synthetic data are for **behaviour testing only**: does the software react correctly to a known situation.
- They are never used to estimate detection rates, lead times or false-alarm rates for real turbines.
- They are never used to tune thresholds that will be applied to real data.
- `synthetic_wind.py` declares its physics in its module docstring, and every output carries `data_class: SYNTHETIC`.
