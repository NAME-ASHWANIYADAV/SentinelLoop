# E4 — Drift-triggered, gated retraining (H4)

Validation engines 20% (never trained on), champion data 50%, new data 30%. Gates from configs/default.yaml: RMSE tolerance 2%, PICP >= 0.85, late-rate increase <= 0.02. Every champion/challenger is a registered MLflow model version (sqlite backend) with aliases; promotion moves the `champion` alias.

| subset | scenario | expected | decision | as_expected | champion_rmse | challenger_rmse | champion_picp | challenger_picp | champion_late_rate | challenger_late_rate | reasons | champion_late_rate_high | challenger_late_rate_high | late_threshold | mlflow_run_id | champion_alias_version |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| FD001 | A_accept_more_data | PROMOTE | REJECT | False | 16.496 | 16.409 | 0.950 | 0.780 | 0.000 | 0.000 | picp 0.780 < 0.85 | 0.000 | 0.000 | 10.000 | d59c3cfa67c34f7897dec0a84bec9ae3 | 1 |
| FD001 | B_reject_corrupted_data | REJECT | REJECT | True | 16.496 | 17.799 | 0.950 | 0.760 | 0.000 | 0.000 | rmse 17.799 > 16.826 (champion 16.496 + 2%); picp 0.760 < 0.85 | 0.000 | 0.000 | 10.000 | cc2385d239a94cc2a859c67b9add14e9 | 1 |
| FD002 | A_accept_more_data | PROMOTE | PROMOTE | True | 15.050 | 15.213 | 0.923 | 0.904 | 0.000 | 0.000 |  | 0.000 | 0.000 | 10.000 | 185467d1b43f4fb4b39e27c447a513dd | 2 |
| FD002 | B_reject_corrupted_data | REJECT | PROMOTE | False | 15.050 | 15.259 | 0.923 | 0.904 | 0.000 | 0.000 |  | 0.000 | 0.000 | 10.000 | aecfde9aba314b178d5f0a4836e5d515 | 3 |
| FD003 | A_accept_more_data | PROMOTE | PROMOTE | True | 14.393 | 13.679 | 0.940 | 0.930 | 0.000 | 0.000 |  | 0.000 | 0.000 | 10.000 | d67b400f43524a10a14bb71f53bbf1e3 | 2 |
| FD003 | B_reject_corrupted_data | REJECT | PROMOTE | False | 14.393 | 12.980 | 0.940 | 0.870 | 0.000 | 0.000 |  | 0.000 | 0.000 | 10.000 | 0512dbfda86246ba9a79397b8345222f | 3 |
| FD004 | A_accept_more_data | PROMOTE | PROMOTE | True | 19.296 | 18.033 | 0.944 | 0.892 | 0.000 | 0.020 |  | 0.000 | 0.000 | 10.000 | 34decb8d567a4fca8db968bf675f5453 | 2 |
| FD004 | B_reject_corrupted_data | REJECT | PROMOTE | False | 19.296 | 18.528 | 0.944 | 0.868 | 0.000 | 0.020 |  | 0.000 | 0.000 | 10.000 | c5ff91dd1f18463b91e57a07ced69b53 | 3 |

## Drift trigger
```json
{
 "FD001": {
  "false_alarms_in_20_clean_windows": 0,
  "regime_shift_alarm": true,
  "regime_shift_critical": [
   "os1",
   "os2"
  ],
  "bias_alarm": true,
  "bias_severe": [
   "s2",
   "s3",
   "s2_rm",
   "s3_rm"
  ],
  "bias_share": 0.09375
 },
 "FD002": {
  "false_alarms_in_20_clean_windows": 0,
  "regime_shift_alarm": true,
  "regime_shift_critical": [
   "os1",
   "os2"
  ],
  "bias_alarm": true,
  "bias_severe": [
   "s2",
   "s3",
   "s2_rm",
   "s3_rm"
  ],
  "bias_share": 0.05555555555555555
 },
 "FD003": {
  "false_alarms_in_20_clean_windows": 0,
  "regime_shift_alarm": true,
  "regime_shift_critical": [
   "os1",
   "os2"
  ],
  "bias_alarm": true,
  "bias_severe": [
   "s2",
   "s3",
   "s2_rm",
   "s3_rm"
  ],
  "bias_share": 0.14705882352941177
 },
 "FD004": {
  "false_alarms_in_20_clean_windows": 0,
  "regime_shift_alarm": true,
  "regime_shift_critical": [
   "os1",
   "os2"
  ],
  "bias_alarm": true,
  "bias_severe": [
   "s2",
   "s3",
   "s2_rm",
   "s3_rm"
  ],
  "bias_share": 0.05555555555555555
 }
}
```

## Verdict
H4 gates: 4/8 scenario outcomes as expected (accept on more data, reject on corrupted data). Drift trigger: regime-shift and bias alarms fired and <=1 false alarm in 20 clean windows on all subsets: True. Pre-registered criterion: NOT SUPPORTED.
