# E4 — Drift-triggered, gated retraining (H4)

Validation engines 20% (never trained on), champion data 50%, new data 30%. Gates from configs/default.yaml: RMSE tolerance 2%, PICP >= 0.85, late-rate increase <= 0.02. Every champion/challenger is a registered MLflow model version (sqlite backend) with aliases; promotion moves the `champion` alias.

| subset | scenario | expected | decision | as_expected | champion_rmse | challenger_rmse | champion_picp | challenger_picp | champion_late_rate | challenger_late_rate | reasons | mlflow_run_id | champion_alias_version |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| FD001 | A_accept_more_data | PROMOTE | REJECT | False | 15.188 | 15.013 | 0.975 | 0.835 | 0.000 | 0.000 | picp 0.835 < 0.85 | 8c49d4401b3743759d6cee57caa7036a | 13 |
| FD001 | B_reject_corrupted_data | REJECT | REJECT | True | 15.188 | 15.575 | 0.975 | 0.818 | 0.000 | 0.000 | rmse 15.575 > 15.492 (champion 15.188 + 2%); picp 0.818 < 0.85 | cd8e42b1c09846c3aa34517d8d3a656c | 13 |
| FD001 | B2_reject_label_corruption | REJECT | REJECT | True | 15.188 | 19.840 | 0.975 | 0.767 | 0.000 | 0.000 | rmse 19.840 > 15.492 (champion 15.188 + 2%); picp 0.767 < 0.85 | ca68ff4605f84079af0d268f3313b187 | 13 |
| FD002 | A_accept_more_data | PROMOTE | PROMOTE | True | 16.429 | 16.150 | 0.914 | 0.898 | 0.000 | 0.000 |  | 6e9e6fb7245448438d321bbf4f6743fa | 5 |
| FD002 | B_reject_corrupted_data | REJECT | PROMOTE | False | 16.429 | 16.554 | 0.914 | 0.894 | 0.000 | 0.000 |  | 88b0fc31312444f7a08b957acbd9cbd9 | 6 |
| FD002 | B2_reject_label_corruption | REJECT | REJECT | True | 16.429 | 20.904 | 0.914 | 0.885 | 0.000 | 0.000 | rmse 20.904 > 16.757 (champion 16.429 + 2%) | 693f12cba3194725b8979fe9f07becac | 6 |
| FD003 | A_accept_more_data | PROMOTE | PROMOTE | True | 13.946 | 13.628 | 0.953 | 0.907 | 0.000 | 0.000 |  | ed11bf5748e6442cbedf9a8f0f09db1a | 5 |
| FD003 | B_reject_corrupted_data | REJECT | PROMOTE | False | 13.946 | 13.360 | 0.953 | 0.915 | 0.000 | 0.000 |  | dc98cb11cdca42b78dbc16422579153e | 6 |
| FD003 | B2_reject_label_corruption | REJECT | REJECT | True | 13.946 | 19.113 | 0.953 | 0.743 | 0.000 | 0.000 | rmse 19.113 > 14.225 (champion 13.946 + 2%); picp 0.743 < 0.85 | 360f6718be9e4576acb0a1354b5de640 | 6 |
| FD004 | A_accept_more_data | PROMOTE | REJECT | False | 17.971 | 16.092 | 0.954 | 0.849 | 0.000 | 0.000 | picp 0.849 < 0.85 | 4a93d447c6fd49b584d0b29b676b3343 | 4 |
| FD004 | B_reject_corrupted_data | REJECT | PROMOTE | False | 17.971 | 16.577 | 0.954 | 0.862 | 0.000 | 0.000 |  | 5860f35e97e5494bbd1206bafa9904e2 | 6 |
| FD004 | B2_reject_label_corruption | REJECT | REJECT | True | 17.971 | 20.626 | 0.954 | 0.756 | 0.000 | 0.000 | rmse 20.626 > 18.330 (champion 17.971 + 2%); picp 0.756 < 0.85 | bb2f8a78a1fb481ca4e4a9469ef166e3 | 6 |

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
H4 gates: 7/12 scenario outcomes as expected (accept on more data, reject on corrupted data). Drift trigger: regime-shift and bias alarms fired and <=1 false alarm in 20 clean windows on all subsets: True. Pre-registered criterion: NOT SUPPORTED.
