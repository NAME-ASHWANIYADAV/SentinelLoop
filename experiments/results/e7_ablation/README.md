# E7 — Ablations

| subset | variant | n_features | test_rmse_capped | test_rmse_raw | test_picp | test_mpiw | holdout_late_rate_point | holdout_discarded_point | holdout_late_rate_lower | holdout_discarded_lower |
|---|---|---|---|---|---|---|---|---|---|---|
| FD001 | full | 62 | 15.054 | 16.131 | 0.900 | 65.626 | 0.000 | 22.650 | 0.000 | 32.400 |
| FD001 | raw_sensors_only_no_rolling | 17 | 17.745 | 18.861 | 0.890 | 53.889 | 0.000 | 25.950 | 0.000 | 41.050 |
| FD001 | with_ema_0.3 | 58 | 13.676 | 14.723 | 0.930 | 67.497 | 0.000 | 25.300 | 0.000 | 35.650 |
| FD001 | asymmetric_cqr | 62 | 15.054 | 16.131 | 0.920 | 68.020 | 0.000 | 22.650 | 0.000 | 35.400 |
| FD004 | full | 70 | 16.551 | 28.016 | 0.827 | 54.360 | 0.000 | 30.320 | 0.000 | 39.860 |
| FD004 | no_regime_normalisation | 86 | 17.699 | 28.768 | 0.891 | 70.493 | 0.000 | 34.340 | 0.000 | 55.620 |
| FD004 | raw_sensors_only_no_rolling | 19 | 18.243 | 29.044 | 0.879 | 64.591 | 0.000 | 32.920 | 0.000 | 51.060 |
| FD004 | with_ema_0.3 | 86 | 23.199 | 33.787 | 0.839 | 77.596 | 0.040 | 31.292 | 0.000 | 58.300 |
| FD004 | asymmetric_cqr | 70 | 16.551 | 28.016 | 0.887 | 56.790 | 0.000 | 30.320 | 0.000 | 43.780 |

Ablation table: each row removes or adds one component; compare with 'full'. The point-vs-lower-bound columns are the policy ablation.
