# E4 — Drift-triggered, gated retraining (H4)

Validation engines 20% (never trained on), champion data 50%, new data 30%. Gates from configs/default.yaml: RMSE tolerance 2%, PICP >= 0.85, late-rate increase <= 0.02. Every champion/challenger is a registered MLflow model version (sqlite backend) with aliases; promotion moves the `champion` alias.

| subset | scenario | expected | decision | as_expected | champion_rmse | challenger_rmse | champion_picp | challenger_picp | champion_late_rate | challenger_late_rate | reasons | champion_late_rate_high | challenger_late_rate_high | late_threshold | mlflow_run_id | champion_alias_version |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| FD001 | A_accept_more_data | PROMOTE | REJECT | False | 15.157 | 14.965 | 0.975 | 0.830 | 0.000 | 0.000 | picp 0.830 < 0.85 | 0.000 | 0.000 | 10.000 | 63ed1fc35c744833a357d0d77fabb6ab | 4 |
| FD001 | B_reject_corrupted_data | REJECT | REJECT | True | 15.157 | 15.688 | 0.975 | 0.802 | 0.000 | 0.000 | rmse 15.688 > 15.460 (champion 15.157 + 2%); picp 0.802 < 0.85 | 0.000 | 0.000 | 10.000 | ac67bd5a227e43df9f79175637a83033 | 4 |
| FD001 | B2_reject_label_corruption | REJECT | REJECT | True | 15.157 | 19.898 | 0.975 | 0.775 | 0.000 | 0.000 | rmse 19.898 > 15.460 (champion 15.157 + 2%); picp 0.775 < 0.85 | 0.000 | 0.000 | 10.000 | ff88c66325c54e659d713e2f5d827392 | 4 |
| FD002 | A_accept_more_data | PROMOTE | PROMOTE | True | 16.348 | 16.146 | 0.938 | 0.906 | 0.000 | 0.000 |  | 0.000 | 0.000 | 10.000 | a68ac9e82dca48628da371b126f9a74a | 5 |
| FD002 | B_reject_corrupted_data | REJECT | REJECT | True | 16.348 | 16.797 | 0.938 | 0.899 | 0.000 | 0.000 | rmse 16.797 > 16.675 (champion 16.348 + 2%) | 0.000 | 0.000 | 10.000 | 2c553763b85f42e3a1620332588908a0 | 4 |
| FD002 | B2_reject_label_corruption | REJECT | REJECT | True | 16.348 | 20.819 | 0.938 | 0.895 | 0.000 | 0.000 | rmse 20.819 > 16.675 (champion 16.348 + 2%) | 0.000 | 0.000 | 10.000 | b1d1eca30bbf47a2ab19861419067b69 | 4 |
| FD003 | A_accept_more_data | PROMOTE | PROMOTE | True | 14.165 | 13.649 | 0.905 | 0.912 | 0.000 | 0.000 |  | 0.000 | 0.000 | 10.000 | cdef8fee543340dcb862d3dd6d6617e6 | 5 |
| FD003 | B_reject_corrupted_data | REJECT | PROMOTE | False | 14.165 | 13.176 | 0.905 | 0.885 | 0.000 | 0.000 |  | 0.000 | 0.000 | 10.000 | dd0e21e2c584438da55f72ad048d9df3 | 6 |
| FD003 | B2_reject_label_corruption | REJECT | REJECT | True | 14.165 | 19.328 | 0.905 | 0.738 | 0.000 | 0.100 | rmse 19.328 > 14.448 (champion 14.165 + 2%); picp 0.738 < 0.85; late_rate 0.100 > 0.020 (champion 0.000 + 0.02) | 0.000 | 0.000 | 10.000 | 20243f49b2554588b05ae7668e99227c | 4 |
| FD004 | A_accept_more_data | PROMOTE | PROMOTE | True | 17.783 | 16.183 | 0.953 | 0.853 | 0.000 | 0.020 |  | 0.000 | 0.000 | 10.000 | 2dddc3f90ba94c8baeb7b76270a6317e | 5 |
| FD004 | B_reject_corrupted_data | REJECT | PROMOTE | False | 17.783 | 16.715 | 0.953 | 0.857 | 0.000 | 0.020 |  | 0.000 | 0.000 | 10.000 | 9dad355d4d644050be3067a3b27bf345 | 6 |
| FD004 | B2_reject_label_corruption | REJECT | REJECT | True | 17.783 | 20.653 | 0.953 | 0.775 | 0.000 | 0.160 | rmse 20.653 > 18.138 (champion 17.783 + 2%); picp 0.775 < 0.85; late_rate 0.160 > 0.020 (champion 0.000 + 0.02) | 0.000 | 0.000 | 10.000 | a881e73ccf43462ab3450e6fd953d09b | 4 |

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
H4 gates: 9/12 scenario outcomes as expected (accept on more data, reject on corrupted data). Drift trigger: regime-shift and bias alarms fired and <=1 false alarm in 20 clean windows on all subsets: True. Pre-registered criterion: NOT SUPPORTED.
