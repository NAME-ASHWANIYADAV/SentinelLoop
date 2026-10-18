# E4 — Drift-triggered, gated retraining (H4)

Validation engines 20% (never trained on), champion data 50%, new data 30%. Gates from configs/default.yaml: RMSE tolerance 2%, PICP >= 0.85, late-rate increase <= 0.02. Every champion/challenger is a registered MLflow model version (sqlite backend) with aliases; promotion moves the `champion` alias.

| subset | scenario | expected | decision | as_expected | champion_rmse | challenger_rmse | champion_picp | challenger_picp | champion_late_rate | challenger_late_rate | reasons | mlflow_run_id | champion_alias_version |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| FD001 | A_accept_more_data | PROMOTE | REJECT | False | 16.748 | 16.701 | 0.970 | 0.800 | 0.000 | 0.000 | picp 0.800 < 0.85 | dcada8f1ebf845a8a484e7452451b13d | 10 |
| FD001 | B_reject_corrupted_data | REJECT | REJECT | True | 16.748 | 17.398 | 0.970 | 0.800 | 0.000 | 0.000 | rmse 17.398 > 17.083 (champion 16.748 + 2%); picp 0.800 < 0.85 | 3bef2eed0dff41aba0b7419081bdeca4 | 10 |
| FD002 | A_accept_more_data | PROMOTE | PROMOTE | True | 15.365 | 15.112 | 0.919 | 0.908 | 0.000 | 0.000 |  | f93be65077084c3a92eb575e1ac21024 | 2 |
| FD002 | B_reject_corrupted_data | REJECT | PROMOTE | False | 15.365 | 15.076 | 0.919 | 0.900 | 0.000 | 0.000 |  | cd08e1231e1241c7a1f870444068e519 | 3 |
| FD003 | A_accept_more_data | PROMOTE | PROMOTE | True | 14.130 | 13.796 | 0.950 | 0.910 | 0.000 | 0.000 |  | eb8d382cb523425ea28c00841318a594 | 2 |
| FD003 | B_reject_corrupted_data | REJECT | PROMOTE | False | 14.130 | 12.988 | 0.950 | 0.910 | 0.000 | 0.000 |  | 2a2503c1511349fbb6f2176e0246a1ac | 3 |
| FD004 | A_accept_more_data | PROMOTE | PROMOTE | True | 19.118 | 18.098 | 0.940 | 0.872 | 0.000 | 0.000 |  | b2399fa972c640849fbd875d6f7a49ac | 2 |
| FD004 | B_reject_corrupted_data | REJECT | PROMOTE | False | 19.118 | 18.327 | 0.940 | 0.860 | 0.000 | 0.000 |  | 5388fe28bc7144d6988c0c557dfe40e2 | 3 |

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
