# E5 — Decision metrics vs RMSE (H5)

| subset | model | rmse_eval_random_truncation | late_rate | mean_discarded_life | early_rate |
|---|---|---|---|---|---|
| FD001 | naive_mean | 41.855 | 1.000 | nan | nan |
| FD001 | random_forest | 15.252 | 0.000 | 25.200 | 0.000 |
| FD001 | hgbr_all_fold_engines | 14.177 | 0.000 | 26.243 | 0.000 |
| FD001 | hgbr_70pct_point | 15.041 | 0.000 | 25.243 | 0.000 |
| FD001 | hgbr_cqr_lower_bound | 15.041 | 0.000 | 40.257 | 0.157 |
| FD002 | naive_mean | 42.006 | 1.000 | nan | nan |
| FD002 | random_forest | 16.795 | 0.000 | 24.319 | 0.000 |
| FD002 | hgbr_all_fold_engines | 15.973 | 0.000 | 26.297 | 0.005 |
| FD002 | hgbr_70pct_point | 16.210 | 0.000 | 26.544 | 0.005 |
| FD002 | hgbr_cqr_lower_bound | 16.210 | 0.000 | 39.198 | 0.093 |
| FD003 | naive_mean | 41.815 | 1.000 | nan | nan |
| FD003 | random_forest | 13.668 | 0.000 | 24.800 | 0.000 |
| FD003 | hgbr_all_fold_engines | 12.610 | 0.000 | 25.829 | 0.000 |
| FD003 | hgbr_70pct_point | 13.726 | 0.000 | 25.743 | 0.000 |
| FD003 | hgbr_cqr_lower_bound | 13.726 | 0.000 | 36.700 | 0.071 |
| FD004 | naive_mean | 42.085 | 1.000 | nan | nan |
| FD004 | random_forest | 16.681 | 0.006 | 24.832 | 0.017 |
| FD004 | hgbr_all_fold_engines | 16.051 | 0.006 | 25.994 | 0.017 |
| FD004 | hgbr_70pct_point | 16.086 | 0.006 | 25.653 | 0.017 |
| FD004 | hgbr_cqr_lower_bound | 16.086 | 0.000 | 38.874 | 0.103 |

## Verdict
H5: an RMSE-vs-decision-metric inversion exists on 4/4 subsets. Pre-registered criterion (at least one): SUPPORTED.

```json
{
 "FD001": {
  "spearman_rmse_vs_late": 0.7254762501100117,
  "inversions": [
   "hgbr_all_fold_engines (rmse 14.18) vs hgbr_70pct_point (rmse 15.04): late 0.000 vs 0.000, discarded 26.2 vs 25.2",
   "hgbr_all_fold_engines (rmse 14.18) vs random_forest (rmse 15.25): late 0.000 vs 0.000, discarded 26.2 vs 25.2",
   "hgbr_70pct_point (rmse 15.04) vs random_forest (rmse 15.25): late 0.000 vs 0.000, discarded 25.2 vs 25.2",
   "hgbr_cqr_lower_bound (rmse 15.04) vs random_forest (rmse 15.25): late 0.000 vs 0.000, discarded 40.3 vs 25.2"
  ]
 },
 "FD002": {
  "spearman_rmse_vs_late": 0.7254762501100117,
  "inversions": [
   "hgbr_all_fold_engines (rmse 15.97) vs random_forest (rmse 16.79): late 0.000 vs 0.000, discarded 26.3 vs 24.3",
   "hgbr_70pct_point (rmse 16.21) vs random_forest (rmse 16.79): late 0.000 vs 0.000, discarded 26.5 vs 24.3",
   "hgbr_cqr_lower_bound (rmse 16.21) vs random_forest (rmse 16.79): late 0.000 vs 0.000, discarded 39.2 vs 24.3"
  ]
 },
 "FD003": {
  "spearman_rmse_vs_late": 0.7254762501100117,
  "inversions": [
   "hgbr_all_fold_engines (rmse 12.61) vs random_forest (rmse 13.67): late 0.000 vs 0.000, discarded 25.8 vs 24.8",
   "hgbr_all_fold_engines (rmse 12.61) vs hgbr_70pct_point (rmse 13.73): late 0.000 vs 0.000, discarded 25.8 vs 25.7"
  ]
 },
 "FD004": {
  "spearman_rmse_vs_late": 0.5735393346764044,
  "inversions": [
   "hgbr_all_fold_engines (rmse 16.05) vs hgbr_70pct_point (rmse 16.09): late 0.006 vs 0.006, discarded 26.0 vs 25.7",
   "hgbr_all_fold_engines (rmse 16.05) vs hgbr_cqr_lower_bound (rmse 16.09): late 0.006 vs 0.000, discarded 26.0 vs 38.9",
   "hgbr_all_fold_engines (rmse 16.05) vs random_forest (rmse 16.68): late 0.006 vs 0.006, discarded 26.0 vs 24.8",
   "hgbr_70pct_point (rmse 16.09) vs hgbr_cqr_lower_bound (rmse 16.09): late 0.006 vs 0.000, discarded 25.7 vs 38.9",
   "hgbr_70pct_point (rmse 16.09) vs random_forest (rmse 16.68): late 0.006 vs 0.006, discarded 25.7 vs 24.8",
   "hgbr_cqr_lower_bound (rmse 16.09) vs random_forest (rmse 16.68): late 0.000 vs 0.006, discarded 38.9 vs 24.8"
  ]
 }
}
```
