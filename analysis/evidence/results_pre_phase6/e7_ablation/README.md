# E7 — Ablations

| subset | variant | n_features | test_rmse_capped | test_rmse_raw | test_picp | test_mpiw | holdout_late_rate_point | holdout_discarded_point | holdout_late_rate_lower | holdout_discarded_lower |
|---|---|---|---|---|---|---|---|---|---|---|
| FD001 | full | 62 | 15.020 | 16.095 | 0.880 | 64.621 | 0.000 | 23.900 | 0.000 | 33.650 |
| FD001 | raw_sensors_only_no_rolling | 17 | 17.745 | 18.861 | 0.890 | 53.889 | 0.000 | 25.950 | 0.000 | 41.050 |
| FD001 | with_ema_0.3 | 58 | 13.676 | 14.723 | 0.930 | 67.548 | 0.000 | 25.300 | 0.000 | 35.200 |
| FD001 | asymmetric_cqr | 62 | 15.020 | 16.095 | 0.880 | 66.717 | 0.000 | 23.900 | 0.000 | 33.650 |
| FD004 | full | 70 | 16.613 | 28.068 | 0.839 | 58.956 | 0.000 | 29.980 | 0.000 | 39.120 |
| FD004 | no_regime_normalisation | 86 | 17.934 | 29.022 | 0.887 | 70.869 | 0.000 | 34.860 | 0.000 | 54.560 |
| FD004 | raw_sensors_only_no_rolling | 19 | 18.243 | 29.044 | 0.879 | 64.591 | 0.000 | 32.920 | 0.000 | 51.060 |
| FD004 | with_ema_0.3 | 86 | 23.199 | 33.787 | 0.847 | 77.770 | 0.040 | 31.292 | 0.000 | 57.420 |
| FD004 | asymmetric_cqr | 70 | 16.613 | 28.068 | 0.863 | 60.195 | 0.000 | 29.980 | 0.000 | 42.340 |

Ablation table: each row removes or adds one component; compare with 'full'. The point-vs-lower-bound columns are the policy ablation.
