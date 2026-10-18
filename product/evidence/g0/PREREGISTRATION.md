# G0 pre-registration: wind normal-behaviour model on CARE to Compare

**Written 2026-10-18, before the dataset was downloaded.** No CARE file has been opened on this machine. The git commit that first contains this file is its date stamp. Any change made after results are seen must be listed in section 9 as a deviation, with its reason. It must not silently replace the protocol below.

**Amendment 1 (2026-10-18, still before any download)** is in section 10. Where it conflicts with sections 2–5, section 10 governs. **Amendment 2** (same day, still before any download) is in section 11 and governs over section 10 where they conflict.

Gate: G0 in `product/INITIAL_MARKET_AND_ASSET_CHOICE.md` section 7.

Sources for the metric definitions:
- Gück et al., "CARE to Compare: A real-world dataset for anomaly detection in wind turbine data", arXiv:2404.10320v2 (read 2026-10-18).
- The journal version is *Data* 9(12):138; MDPI returned 403 to an automated fetch.

## 1. Data

- **Dataset:** CARE to Compare v6, Zenodo record 15846963. File `CARE_To_Compare.zip`, 5,503,439,673 bytes, MD5 `2547b58c21ac8c242d13232860cf500c` (Zenodo API, 2026-10-18).
- **Licence:** CC BY-SA 4.0. No CARE-derived data file is committed to this repository. Only aggregate metrics and code are committed, with attribution.
- **Data class:** REAL FIELD (PUBLIC). The paper gives these counts; they are recounted after download and any difference is reported:

| | Farm A | Farm B | Farm C |
|---|---|---|---|
| Turbines | 5 | 9 | 22 |
| Anomaly datasets | 11 | 6 | 27 |
| Normal datasets | 11 | 9 | 31 |
| Features | 86 | 257 | 957 |

- **Downloads are treated as untrusted:**
  - Extract into a new, empty directory (`data/external/care_v6/`, git-ignored).
  - Parse only with `python -I`, from scripts kept outside that directory.
  - Execute nothing that is shipped in the archive.

## 2. Model (fixed now)

The product's wind normal-behaviour model (`src/sentinelloop/app/nbm.py`, ridge regression with the same EWMA load features, window, sustain and threshold rule), adapted to CARE's anonymised features by a mapping file:

1. **Inputs.** Active power, wind speed, and ambient temperature, chosen from each farm's feature descriptions. Nacelle temperature and rotor/generator speed are used if described. When a sensor has 10-minute average, min, max and standard deviation, only the average is used.
2. **Targets.** Every average temperature sensor whose description names a drivetrain or electrical component: gearbox, bearing, generator, shaft, transformer, converter, oil, hydraulic.
   - Excluded: ambient, nacelle, tower, cabinet, outside, spinner and hub air temperatures. Those are inputs or environment, not component health.
   - **The mapping is written from the descriptions file alone, before any event data or label is read**, and committed before scoring.
3. **Training.** Each dataset is trained on its own training part only (the dataset's training/prediction column).
   - Only rows whose status ID is 0 or 2 are used. The paper calls these normal; 1, 3, 4 and 5 are not.
   - The last 25% of the training part (time order) is the threshold-validation slice. The ridge is fitted on the first 75%.
   - This per-dataset, per-turbine training plays the role of the product's commissioning baseline, so no extra offset is applied.
4. **Point prediction.** p = 1 at a timestamp when the rolling score of any target exceeds its inspect threshold. The threshold is 1.25 × the maximum healthy rolling score on the validation slice (product rule, `nbm.INSPECT_MARGIN`). Scores need half a window of operating points; before that, p = 0.
5. **No information from the prediction part is used** for fitting, threshold choice, feature choice or hyper-parameters.
   - Settings fixed now: window 36, sustain 6, EWMA taus (3, 9, 18), ridge 1e-3, margin 1.25.
   - The `sustain` rule is **not** applied to p. CARE's criticality counter plays that role.

## 3. Event decision (criticality counter, CARE Algorithm 1)

The paper's text and its algorithm disagree about which status value increments the counter. Resolved now as follows:
- The counter increments when p = 1 and the row's status is **normal (0 or 2)**.
- It decrements (floor 0) when p = 0 and the status is normal.
- It holds when the status is abnormal.
- An event is detected when the counter **reaches 72** (≥ 72) at any time in the prediction part.

## 4. Metrics (CARE paper definitions)

- **Coverage:** F_β with β = 0.5 over the prediction part of anomaly datasets. The ground truth is 1 inside the event window and 0 outside it. Only normal-status rows are scored. The mean is taken over anomaly datasets.
- **Accuracy:** tn / (fp + tn) over the normal-status rows of the prediction part of normal datasets. The mean is taken over normal datasets.
- **Reliability:** event-wise F_β (β = 0.5) over all datasets. A detected event on an anomaly dataset is a TP; on a normal dataset, an FP. An undetected anomaly dataset is an FN.
- **Earliness:** weighted score over anomaly datasets' event windows. The weight is 1 in the first half of the event and falls linearly to 0 at its end. The score is Σ w·p / Σ w per dataset, then averaged.
- **CARE score:** (Coverage + Earliness + Reliability + 2·Accuracy) / 5.
  - If no anomaly is detected anywhere, the score is 0.
  - If mean Accuracy < 0.5, the score equals mean Accuracy.
- **Also reported:**
  - event detection rate per farm with a Wilson 95% interval;
  - lead time (event start minus the first timestamp the counter reaches 72), median and range;
  - alarms on normal datasets, per turbine-year of prediction data;
  - achieved against nominal false-alarm behaviour.

## 5. Decision rule (fixed now)

- **Primary:** the pooled CARE score over all 95 datasets, compared with the published autoencoder result of 0.66.
- **G0 passes** only if the pooled CARE score is > 0.66 **and** mean Accuracy is ≥ 0.5.
- **G0 fails** otherwise. A fail means the wind choice is re-tabled, as the choice record states.
- **Farm A** (in class, onshore) is reported separately. There is no published per-farm bar, so the Farm A score informs the decision but does not decide it.
- **Farms B and C** are reported separately as cross-asset results.
- With 11 in-class events, a detection rate carries an uncertainty of about ±25 points. No precision claim is made.

## 6. Forbidden after results are seen

- Re-tuning any setting in section 2 on the prediction parts to turn a fail into a pass.
- Dropping datasets, except where a parse failure leaves a dataset with no usable target or input. Such datasets are listed, counted and scored as "no detection, Accuracy computed if normal".
- Changing the decision rule.

## 7. Allowed and reported

- Bug fixes in parsing or metric code. Each fix is listed with its effect on the score, and the pre-fix score is kept.
- Exploratory analyses after the primary result. They are labelled post hoc and kept apart from the gate result.

## 8. Outputs

- `product/evidence/g0/feature_mapping_{A,B,C}.json`: committed before scoring.
- `product/evidence/g0/results.json` and `results.md`: per dataset, per farm and pooled metrics; the run's code commit and input MD5.
- A runtime log.

## 9. Deviations

(none yet)

## 10. Amendment 1 (2026-10-18, before any CARE file was downloaded)

**Why.** The adversarial review (`product/ADVERSARIAL_REVIEW.md`: data_scientist-7, data_scientist-11, buyer-8, buyer-9) found that sections 2–5 left choices open that would have to be made while running G0, several of which move the score in a predictable direction. It also found that the pooled decision rule would be decided mostly by offshore, cross-asset data. No CARE data had been downloaded when this amendment was written (`data/external/` did not exist). The git commit that adds this section is its date stamp. The repository has no remote, so that stamp is local; the team is asked to publish the SHA-256 of this file externally (for example as a pushed tag or a public registry entry) before the download (`FINAL_PRODUCT_HANDOFF.md`).

Where this section conflicts with sections 2–5, this section governs.

### 10.1 Adapter (replaces the open parts of §2)

1. **Inputs.**
   - Required: active power, wind speed, ambient temperature, chosen from each farm's feature descriptions.
   - Optional: nacelle temperature and rotor (or generator) speed. If a farm describes none, those feature columns are omitted and the regression is fitted on the remaining ones. Nothing is imputed for an absent column.
2. **Rated power** (sets the "operating" mask, power > 5% of rated): the 99.5th percentile of active power over the normal-status rows of that dataset's training part.
3. **Rotor-speed scaling**: divided by its 99.5th percentile over the same rows. This replaces the synthetic generator's 16.8 rpm.
4. **Zeros as missing values.** Farms B and C use 0 for missing values (paper). For temperature columns, an exact 0.0 is treated as missing. For power and wind speed, 0 is a valid value.
5. **Gates applied in the assessment service's order.**
   - Platform data checks first (`configs/platform.yaml` defaults): any required signal (inputs and targets) missing in more than 10% of the scoring window is a data-quality failure.
   - Then the model's gates (`nbm.gate`, defaults):
     - data quality: a stuck signal, meaning a trailing constant run longer than max(5, the longest run in training); and, only where a farm describes both rotor and generator speed, the rotor/generator relation learned from the training part;
     - scope: operating share ≥ 50% of the scoring window; ambient, nacelle and wind speed outside the training range (plus 5% of that range) on no more than 20% of points.
   - Remaining missing cells are forward- and back-filled inside the window, as in the product, and the share of filled cells is reported.
   - A timestamp whose window fails a gate gets p = 0, the product's "no anomaly statement". It is still scored by the CARE metrics. The baseline in §10.3 uses the same gates.
6. **Targets and multiplicity.** All targets are selected by the description rule in §2.2.
   - Each target gets its own threshold from the validation slice.
   - The number of targets per farm is reported.
   - No further multiplicity correction is applied. False alarms are penalised by the Accuracy term, and the internal baseline in §10.3 faces the same number of targets.
7. **Thresholds and persistence.**
   - The inspect margin stays 1.25 × the maximum healthy rolling score on the validation slice. The synthetic-only revisit W2 (`product/evidence/wind_synthetic/w2.md`, rule fixed before it ran) chose margin 1.25 and sustain 12. Sustain 12 is now the product default (`nbm.SUSTAIN`, PD-15).
   - As in §2.5, sustain is **not** applied to p. CARE's criticality counter (§3) is the persistence rule, and stacking both would double-count persistence.
   - The W2 choice enters G0 only through the "also reported" product alarm count on normal datasets. That count uses the product rule: an alarm episode is a run of consecutive sustained exceedances (sustain 12) per turbine-year of normal-dataset prediction data (`nbm._episodes`).
   - §2.5's "sustain 6" is replaced by "sustain 12, product alarm count only".

### 10.2 Timing definitions (replace the open parts of §3 and §4)

- **Event detected:** the criticality counter reaches 72 at any time in the prediction part of an anomaly dataset.
  - Detections are reported split into "before the event window" and "inside the event window".
- **Lead time:** event start minus the first instant the counter reaches 72. A positive value means before the event start; a negative value means after it.
- The phrase "achieved against nominal false-alarm behaviour" in §4 is withdrawn: the threshold rule has no nominal rate.
- **Assessability** is also reported: the share of normal-status prediction rows whose window passes both gates, per farm.

### 10.3 Decision rule (replaces §5)

**Primary, in class: Farm A** (onshore, 22 datasets). Farm A's CARE score is compared with that of an **internal baseline computed by the same metric code**, the "power-binned z-threshold":
- For each target, the training part's normal-status operating rows are binned by deciles of active power; a mean and standard deviation are kept per bin.
- p = 1 at a timestamp when any target's |z| > 3. No sustain is applied; the criticality counter applies, as for the model.
- Same gates, same criticality rule.

**G0 passes only if all three hold:**
1. Farm A CARE score is above the baseline's Farm A CARE score.
2. Farm A mean Accuracy is ≥ 0.5.
3. The pooled CARE score over all 95 datasets is > 0.66 (the published autoencoder result, computed by different code, kept as a secondary bar).

A pooled pass with a Farm A result at or below the baseline is a **fail** for the vertical decision.

**Reporting:**
- Farm A's event detection rate is reported with its Wilson 95% interval.
- With 11 events no precision claim is made.
- Any external or sales use of G0 must quote the Farm A result with its interval, and must label the pooled result "mostly cross-asset (offshore)".

### 10.4 Splits (reconciliation with the market record)

`INITIAL_MARKET_AND_ASSET_CHOICE.md` §7 asked for splits by turbine and farm.
- CARE's design trains and predicts each dataset on its own turbine's history: a training year, then a prediction part. That is equivalent to commissioning each turbine on its own past, which is how the product is deployed (PD-12).
- There is no random time split.
- No conformal calibration set is used: thresholds come from the healthy validation slice (§2.3). The market record's wording is superseded here.

### 10.5 Unchanged

Data, licence and handling (§1); the forbidden and allowed changes (§6, §7); outputs (§8). Deviations after data are seen still go in §9.

## 11. Amendment 2 (2026-10-18, still before any CARE file was downloaded)

**Why.** The re-review of the Phase 9 fixes (`product/ADVERSARIAL_REVIEW.md`, "Re-review of the fixes") found three defects in the product's wind gating and alarm rule. Each one changes how §10 is applied:
- **wind-eval-migrations-01.** A stuck temperature sensor that recovered produced an urgent alarm. The model scored the stuck readings that the data check had just rejected.
- **wind-eval-migrations-05.** The sustain rule counted rows, not operating points.
- **wind-eval-migrations-06.** The evaluation harness skipped the platform's own data checks.

All three were fixed in the product, test-first. W2 was then re-run under its unchanged pre-stated rule (run 2, `product/evidence/wind_synthetic/w2.md`; run 1 is kept as `w2_run1.md`). Run 2's tuning fleets could not resolve its limit. W3 (`product/experiments/w3_pooled_threshold.py`, protocol committed before it ran in 25d4d59; results in `product/evidence/wind_synthetic/w3.md`) then chose the setting on a pooled tuning set and checked it on fresh fleets.

No CARE data had been downloaded when this amendment was written (`data/external/` did not exist). Where this section conflicts with §10, this section governs.

### 11.1 Changes to §10.1

1. **Stuck signals (§10.1.5).** A stuck signal is a constant run longer than max(5, the longest run in training). It counts wherever it falls in the rows the model scores, not only at the end of the window, because a recovered sensor's readings stay in the rolling means for hours.
2. **Gate order (§10.1.5).** The model's data checks run before any scope decision, including when there is no baseline, as in the product (`nbm.gate`; PD-13, PD-28). The platform's generic data checks are applied at the wind policy's limits (`configs/platform.yaml`, `nbm.evaluate(policy=...)`).
3. **Product alarm count (§10.1.7).**
   - The product rule now counts **sustain 18 operating points** (3 h of operation, margin 1.25), the setting W3 chose (`nbm.SUSTAIN`). This replaces sustain 12.
   - Sustain is still **not** applied to p; CARE's criticality counter remains the persistence rule.
   - Rates are reported per calendar turbine-year and per assessable turbine-year.

### 11.2 What the synthetic runs say about this setting (SYNTHETIC)

- **W2 run 2** (tuning fleets 40–45 only): it chose sustain 6. That setting gave 5.74 healthy alarm episodes per turbine-year on the held-out fleets 20–25. Its 2.27 healthy turbine-years could not resolve the 1.0 limit.
- **W3**, tuning on fleets 40–45 and 20–25 pooled (4.53 healthy turbine-years):
  - margin 1.25, sustain 18 gives 0.22 episodes per turbine-year with 72/72 faults detected;
  - on the fresh fleets 60–65 it gives **0.44 per turbine-year** (1 episode in 2.27 turbine-years; 95% interval up to about 2.45), 36/36 detected, median lead 8.9 days.

These synthetic figures do not predict the real rate; G0's normal datasets give the first real-data estimate. **No G0 pass/fail criterion changes** (§10.3 stands).

### 11.3 Unchanged

Everything else in §10 and §§1–8.
