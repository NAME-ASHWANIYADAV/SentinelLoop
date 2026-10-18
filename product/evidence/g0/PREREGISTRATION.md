# G0 pre-registration: wind normal-behaviour model on CARE to Compare

**Written 2026-10-18, before the dataset was downloaded.** No CARE file has been opened on this machine. The git commit that first contains this file is its date stamp. Any change made after results are seen must be listed in section 9 as a deviation, with its reason. It must not silently replace the protocol below.

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
