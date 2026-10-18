# E5 — Decision metrics vs RMSE (H5)

| subset | model | rmse_eval_random_truncation | late_rate | mean_discarded_life | early_rate |
|---|---|---|---|---|---|
| FD001 | naive_mean | 41.855 | 1.000 | nan | nan |
| FD001 | random_forest | 15.222 | 0.000 | 25.171 | 0.000 |
| FD001 | hgbr_all_fold_engines | 14.143 | 0.000 | 25.586 | 0.000 |
| FD001 | hgbr_70pct_point | 15.070 | 0.000 | 25.171 | 0.000 |
| FD001 | hgbr_cqr_lower_bound | 15.070 | 0.000 | 42.886 | 0.171 |
| FD002 | naive_mean | 42.006 | 1.000 | nan | nan |
| FD002 | random_forest | 16.791 | 0.000 | 24.286 | 0.000 |
| FD002 | hgbr_all_fold_engines | 15.982 | 0.000 | 26.066 | 0.005 |
| FD002 | hgbr_70pct_point | 16.245 | 0.000 | 26.736 | 0.005 |
| FD002 | hgbr_cqr_lower_bound | 16.245 | 0.000 | 39.648 | 0.104 |
| FD003 | naive_mean | 41.815 | 1.000 | nan | nan |
| FD003 | random_forest | 13.695 | 0.000 | 24.614 | 0.000 |
| FD003 | hgbr_all_fold_engines | 12.845 | 0.000 | 25.871 | 0.000 |
| FD003 | hgbr_70pct_point | 13.563 | 0.000 | 25.729 | 0.000 |
| FD003 | hgbr_cqr_lower_bound | 13.563 | 0.000 | 36.986 | 0.071 |
| FD004 | naive_mean | 42.085 | 1.000 | nan | nan |
| FD004 | random_forest | 16.680 | 0.006 | 24.832 | 0.017 |
| FD004 | hgbr_all_fold_engines | 16.010 | 0.006 | 26.295 | 0.017 |
| FD004 | hgbr_70pct_point | 16.051 | 0.006 | 26.006 | 0.017 |
| FD004 | hgbr_cqr_lower_bound | 16.051 | 0.000 | 38.839 | 0.098 |

## Verdict
H5: an RMSE-vs-decision-metric inversion exists on 4/4 subsets. Pre-registered criterion (at least one): SUPPORTED.

```json
{
 "FD001": {
  "spearman_rmse_vs_late": 0.7254762501100117,
  "inversions": [
   "hgbr_all_fold_engines (rmse 14.14) vs hgbr_70pct_point (rmse 15.07): late 0.000 vs 0.000, discarded 25.6 vs 25.2",
   "hgbr_all_fold_engines (rmse 14.14) vs random_forest (rmse 15.22): late 0.000 vs 0.000, discarded 25.6 vs 25.2",
   "hgbr_cqr_lower_bound (rmse 15.07) vs random_forest (rmse 15.22): late 0.000 vs 0.000, discarded 42.9 vs 25.2"
  ]
 },
 "FD002": {
  "spearman_rmse_vs_late": 0.7254762501100117,
  "inversions": [
   "hgbr_all_fold_engines (rmse 15.98) vs random_forest (rmse 16.79): late 0.000 vs 0.000, discarded 26.1 vs 24.3",
   "hgbr_70pct_point (rmse 16.24) vs random_forest (rmse 16.79): late 0.000 vs 0.000, discarded 26.7 vs 24.3",
   "hgbr_cqr_lower_bound (rmse 16.24) vs random_forest (rmse 16.79): late 0.000 vs 0.000, discarded 39.6 vs 24.3"
  ]
 },
 "FD003": {
  "spearman_rmse_vs_late": 0.7254762501100117,
  "inversions": [
   "hgbr_all_fold_engines (rmse 12.84) vs hgbr_70pct_point (rmse 13.56): late 0.000 vs 0.000, discarded 25.9 vs 25.7",
   "hgbr_all_fold_engines (rmse 12.84) vs random_forest (rmse 13.70): late 0.000 vs 0.000, discarded 25.9 vs 24.6",
   "hgbr_70pct_point (rmse 13.56) vs random_forest (rmse 13.70): late 0.000 vs 0.000, discarded 25.7 vs 24.6",
   "hgbr_cqr_lower_bound (rmse 13.56) vs random_forest (rmse 13.70): late 0.000 vs 0.000, discarded 37.0 vs 24.6"
  ]
 },
 "FD004": {
  "spearman_rmse_vs_late": 0.5735393346764044,
  "inversions": [
   "hgbr_all_fold_engines (rmse 16.01) vs hgbr_70pct_point (rmse 16.05): late 0.006 vs 0.006, discarded 26.3 vs 26.0",
   "hgbr_all_fold_engines (rmse 16.01) vs hgbr_cqr_lower_bound (rmse 16.05): late 0.006 vs 0.000, discarded 26.3 vs 38.8",
   "hgbr_all_fold_engines (rmse 16.01) vs random_forest (rmse 16.68): late 0.006 vs 0.006, discarded 26.3 vs 24.8",
   "hgbr_70pct_point (rmse 16.05) vs hgbr_cqr_lower_bound (rmse 16.05): late 0.006 vs 0.000, discarded 26.0 vs 38.8",
   "hgbr_70pct_point (rmse 16.05) vs random_forest (rmse 16.68): late 0.006 vs 0.006, discarded 26.0 vs 24.8",
   "hgbr_cqr_lower_bound (rmse 16.05) vs random_forest (rmse 16.68): late 0.000 vs 0.006, discarded 38.8 vs 24.8"
  ]
 }
}
```
