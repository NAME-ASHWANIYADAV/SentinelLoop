# Data strategy

Status 2026-10-18. The vertical is provisional and gated (PD-10): Indian onshore wind, geared ~2.0–2.3 MW turbines, 10-minute SCADA.

## 1. Position

- SentinelLoop has **no customer data**. Its models have run only on:
  - simulated engines (NASA C-MAPSS);
  - our own synthetic wind SCADA.
- The chosen vertical has public real field data in the same form a customer would export: 10-minute SCADA with alarm, status and some failure logs. That is the main reason it was kept (choice record §5).
- The product's data contract does not ingest status, alarm or curtailment data (`KNOWN_LIMITATIONS.md` M3). In G0, CARE's status IDs only select which rows are used and scored; they are never model inputs (rule 5).
- No Indian turbine SCADA is public. Every public real dataset available is European. The gap between European test data and Indian turbines is a stated risk (`DOMAIN_GAP_REPORT.md`).

## 2. Datasets and their role

| dataset | class | licence | role | status |
|---|---|---|---|---|
| NASA C-MAPSS FD001–FD004 | SIMULATED | no licence stated (R4: needs written confirmation for commercial use) | method development; scheduling simulator inputs; no product claim | in use |
| `synthetic_wind.py` | SYNTHETIC | ours | behaviour tests and regression tests for every wind code path; ladder rung 2; W3 chose the alarm-persistence default on pooled tuning fleets and checked it once on fresh fleets (PD-15, §5) | in use (`tests/test_app_wind.py`, `product/evidence/wind_synthetic/w1.md`, `w2.md`, `w3.md`) |
| CARE to Compare v6 (Zenodo 15846963) | PUBLIC REAL FIELD | CC BY-SA 4.0 | G0 falsification test; rung 3. 95 datasets, 44 with a labelled fault-leading anomaly | pre-registered, with Amendments 1 and 2 written before any download (PD-25; `PREREGISTRATION.md` §11); **download (5.50 GB) awaiting approval** |
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
4. **Splits.** In time, per turbine: training comes first and never overlaps the period it is evaluated on. Never random time windows.
   - For G0, each CARE dataset is trained on its own turbine's training part and scored on its prediction part (`PREREGISTRATION.md` §10.4, which supersedes the earlier "by turbine and by farm" wording).
   - In-class and cross-asset results are reported separately: Farm A onshore; Farms B and C cross-asset.
   - Thresholds come from healthy data only.
5. **Labels as evaluation masks.** CARE status IDs (normal = 0 and 2) choose which rows are used for training and which are scored (`PREREGISTRATION.md` §2.3, §4). They are never model inputs.
6. **Pre-registration.** Rung 3 and above need a committed protocol before the data are opened (`VALIDATION_LADDER.md`). G0's protocol is `product/evidence/g0/PREREGISTRATION.md`, committed in b40fccd. Its Amendment 1 (§10, committed in afadc02, still before any download) fixes the adapter, gates, timing and decision rule, with Farm A as the primary decision. Amendment 2 (§11, committed in f531b72, also before any download) governs where it conflicts with §10: it changes the stuck-signal and gate-order definitions and the product alarm count (sustain 18 operating points). No pass/fail criterion changed (§11.2).
7. **Customer data (rung 4 and above, none yet).**
   - A written data-sharing agreement covering purpose, retention, deletion and who may see what.
   - Data stay on infrastructure the customer approves.
   - Technician names are pseudonymised in analysis copies (India's DPDP Act duty noted in R5; not re-verified).
   - Customer data are never used to train a model shared with another customer without written consent.

## 4. What a first customer would need to export (hypothesis for G1)

- At least 3 years of 10-minute SCADA for the turbines in scope, with the wind type's signals (`src/sentinelloop/app/adapters/wind.py`):
  - wind speed, active power, rotor and generator speed, ambient and nacelle temperature, gearbox oil, gearbox high-speed-shaft bearing and generator bearing temperature;
  - pitch angle is optional (`OPTIONAL_SIGNALS`; the model does not read it);
  - every other signal is required today. A turbine that lacks one is a DATA_QUALITY_FAILURE (`missing_signal`) until it arrives. Per-model or per-turbine signal subsets are not built, and no requirement or limitation entry covers them yet.
- Alarm and event logs, turbine status codes, and curtailment or derating records. They are needed to reconcile alarms and explain out-of-scope periods. They are **not in the data contract** and cannot be ingested (`KNOWN_LIMITATIONS.md` M3), so they are used offline until operating-state signals exist (PLANNED).
- The failure or work-order log: date, turbine, component, action, downtime.
- Turbine model, rating, drivetrain type, commissioning date, and component replacements or retrofits (re-baselining points).
- Whether the owner, the OEM or an O&M contractor controls the export, and under what contract.

**How an export reaches the platform today** (`DATA_CONTRACTS.md` §1):
- **Names and units.** Each export is renamed to the platform's signal names and converted to its units before ingestion. There is no per-site tag mapping (FR-B3, PLANNED; `KNOWN_LIMITATIONS.md` P12) and no unit conversion.
- **Batch size.** At most 200,000 readings per batch (`ingest.MAX_RECORDS_PER_BATCH`). A wide CSV counts rows × signal columns; one turbine-day of 10 signals is 1,440 readings. A larger file is refused and must be split. Request bodies are also capped at 10 MB, which a JSON batch reaches at about 90,000 readings (`DATA_CONTRACTS.md` §1).
- **Periodic exports.** The site's policy file sets `assess_at: latest_reading` for the wind type (the shipped default in `configs/platform.yaml` is `now`), and each export is replayed with `POST /api/v1/assets/{id}/assess-range`, oldest instant first. An assessment at or before the last applied instant is stored as a replay and never moves the live state (PD-17).
- **Late feeds.** With `assess_at: now`, when every required signal is late together, the assessment reports `data_delivery_delay`, and no work order is raised at the turbine while the delay lasts (PD-17). The first good assessment after it can still raise an instrument-check order, because the data-quality failure needs 2 good assessments to clear (known gap, `DATA_CONTRACTS.md` §1). With `latest_reading`, a stopped export shows instead as ASSESSMENT_OVERDUE (26 h for wind) and in the staleness report (`DATA_CONTRACTS.md` §1).

## 5. Synthetic data policy

Synthetic data are for **behaviour testing only**: does the software react correctly to a known situation.
- They are never used to estimate detection rates, lead times or false-alarm rates for real turbines.
- Threshold values are fitted on the healthy data the model is trained on, which for a customer means its own turbines. Inspect = 1.25 × the largest healthy rolling score on the held-out healthy slice (with a floor of 0.5); urgent = 3 × inspect (`nbm.fit`).
- **One exception, recorded in PD-15.** With no real data available, the persistence default (sustain 18 operating points = 3 h of operation) and the inspect margin (1.25) were chosen on pooled synthetic tuning fleets 40–45 and 20–25 (W3, `product/evidence/wind_synthetic/w3.md`), by a rule committed before the run (25d4d59), and checked once on fresh synthetic fleets 60–65.
  - They are starting defaults, not settings tuned for real turbines.
  - On the fresh synthetic fleets they give 0.44 healthy alarm episodes per turbine-year (1 in 2.27 turbine-years). That point estimate is below W3's 1.0 limit, but these fleets cannot resolve the limit: even zero episodes would allow 1.32 at 95% (`w3.md`). W3's rule applied the limit on the tuning set (0.22, 1 in 4.53 turbine-years); the fresh fleets are a single check. The 95% interval runs up to about 2.45, so even on synthetic data neither the 1.0 limit nor the proposed pilot ceiling of 2 is excluded, and drifting sensors added 39 alarm episodes (`KNOWN_LIMITATIONS.md` E7, M1).
  - The rate is sensitive to persistence. Earlier runs chose sustain 12 (W2 run 1, driven by gating defects since fixed, `w2_run1.md`) and then sustain 6, which gave 5.74 on its held-out fleets (W2 run 2, `w2.md`).
  - G0 reports the product alarm count at sustain 18 on real normal datasets (`PREREGISTRATION.md` §11, Amendment 2), and a partner's rung-4 back-test can change both (`PILOT_PROTOCOL.md` §6).
- The urgent multiple (3 × inspect) is also a policy choice set on synthetic data, not a calibrated value (`KNOWN_LIMITATIONS.md` M4).
- `synthetic_wind.py` declares its physics in its module docstring, and every output carries `data_class: SYNTHETIC`.
