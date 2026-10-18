# E1 seed sensitivity (post hoc; finding ML-6)

| subset | seed | n_eval_engines | oof_s | A_point_T_late | A_point_T_discarded | C_lower_T_late | C_lower_T_discarded | C_lower_tuned_threshold | C_lower_tuned_late | C_lower_tuned_discarded | A_point_tuned_threshold | A_point_tuned_late | A_point_tuned_discarded | gap_discarded_C_minus_A_at_T |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| FD001 | 42 | 70 | 28.500 | 0.000 | 25.243 | 0.000 | 40.257 | 6.000 | 0.014 | 14.174 | 10.000 | 0.057 | 9.985 | 15.014 |
| FD001 | 43 | 70 | 28.200 | 0.000 | 24.571 | 0.000 | 40.886 | 2.000 | 0.200 | 12.643 | 10.000 | 0.014 | 10.130 | 16.314 |
| FD001 | 44 | 70 | 29.900 | 0.000 | 25.143 | 0.000 | 41.729 | 0.000 | 0.543 | 17.344 | 11.000 | 0.043 | 11.791 | 16.586 |

## Summary
FD001: over 3 seeds the lower-bound policy discards 15.0-16.6 more cycles than the point policy at T=25 (late rates A 0.000-0.000, C 0.000-0.000); tuned C thresholds 0-6
