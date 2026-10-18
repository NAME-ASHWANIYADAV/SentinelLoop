# E1 — Maintenance-policy replay (H1)

Protocol: out-of-fold CQR predictions over complete training trajectories (5 engine folds, inner 30% calibration split); tune/eval engine split 30/70; min lead 5 cycles; target late rate 5% for the pre-registered matched comparison; cost ratios are ASSUMED failure costs in cycles of discarded life ([25, 50, 100, 200, 500]).

Note: policy B (point minus margin) is the same family as policy A (a shifted threshold); it is reported because it was pre-registered. The informative comparison is the A-family vs the C-family (lower bound) frontier below (secondary analysis, added after the fast smoke run showed zero late orders at T=25).

## Pre-registered table
| subset | policy | threshold | margin | n_engines | n_evaluable | late_rate | mean_discarded_life | median_discarded_life | order_rate | early_rate | n_late | churn |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| FD001 | A_point_T | 25.000 | 0.000 | 70 | 70 | 0.000 | 25.243 | 25.000 | 1.000 | 0.000 | 0 | 5.029 |
| FD001 | C_lower_T | 25.000 | 0.000 | 70 | 70 | 0.000 | 40.257 | 34.500 | 1.000 | 0.157 | 0 | 5.529 |
| FD001 | A_point_matched | 10.000 | 0.000 | 70 | 70 | 0.057 | 9.985 | 10.000 | 1.000 | 0.000 | 4 | nan |
| FD001 | B_margin_matched | 25.000 | 0.000 | 70 | 70 | 0.000 | 25.243 | 25.000 | 1.000 | 0.000 | 0 | nan |
| FD001 | C_lower_matched | 6.000 | 0.000 | 70 | 70 | 0.014 | 14.174 | 13.000 | 1.000 | 0.000 | 1 | nan |
| FD001 | D_cost_25 | 8.000 | 0.000 | 70 | 70 | 0.214 | 8.109 | 8.000 | 1.000 | 0.000 | 15 | nan |
| FD001 | D_cost_50 | 10.000 | 0.000 | 70 | 70 | 0.057 | 9.985 | 10.000 | 1.000 | 0.000 | 4 | nan |
| FD001 | D_cost_100 | 10.000 | 0.000 | 70 | 70 | 0.057 | 9.985 | 10.000 | 1.000 | 0.000 | 4 | nan |
| FD001 | D_cost_200 | 10.000 | 0.000 | 70 | 70 | 0.057 | 9.985 | 10.000 | 1.000 | 0.000 | 4 | nan |
| FD001 | D_cost_500 | 10.000 | 0.000 | 70 | 70 | 0.057 | 9.985 | 10.000 | 1.000 | 0.000 | 4 | nan |
| FD002 | A_point_T | 25.000 | 0.000 | 182 | 182 | 0.000 | 26.544 | 25.000 | 1.000 | 0.005 | 0 | 5.033 |
| FD002 | C_lower_T | 25.000 | 0.000 | 182 | 182 | 0.000 | 39.198 | 36.000 | 1.000 | 0.093 | 0 | 5.066 |
| FD002 | A_point_matched | 11.000 | 0.000 | 182 | 182 | 0.027 | 10.774 | 10.000 | 1.000 | 0.000 | 5 | nan |
| FD002 | B_margin_matched | 25.000 | 0.000 | 182 | 182 | 0.000 | 26.544 | 25.000 | 1.000 | 0.005 | 0 | nan |
| FD002 | C_lower_matched | 5.000 | 0.000 | 182 | 182 | 0.071 | 11.183 | 11.000 | 1.000 | 0.000 | 13 | nan |
| FD002 | D_cost_25 | 10.000 | 0.000 | 182 | 182 | 0.088 | 10.205 | 9.000 | 1.000 | 0.000 | 16 | nan |
| FD002 | D_cost_50 | 12.000 | 0.000 | 182 | 182 | 0.016 | 11.927 | 11.000 | 1.000 | 0.000 | 3 | nan |
| FD002 | D_cost_100 | 12.000 | 0.000 | 182 | 182 | 0.016 | 11.927 | 11.000 | 1.000 | 0.000 | 3 | nan |
| FD002 | D_cost_200 | 12.000 | 0.000 | 182 | 182 | 0.016 | 11.927 | 11.000 | 1.000 | 0.000 | 3 | nan |
| FD002 | D_cost_500 | 16.000 | 0.000 | 182 | 182 | 0.000 | 16.099 | 16.000 | 1.000 | 0.000 | 0 | nan |
| FD003 | A_point_T | 25.000 | 0.000 | 70 | 70 | 0.000 | 25.743 | 25.000 | 1.000 | 0.000 | 0 | 4.486 |
| FD003 | C_lower_T | 25.000 | 0.000 | 70 | 70 | 0.000 | 36.700 | 33.000 | 1.000 | 0.071 | 0 | 5.329 |
| FD003 | A_point_matched | 11.000 | 0.000 | 70 | 70 | 0.014 | 10.739 | 10.000 | 1.000 | 0.000 | 1 | nan |
| FD003 | B_margin_matched | 25.000 | 0.000 | 70 | 70 | 0.000 | 25.743 | 25.000 | 1.000 | 0.000 | 0 | nan |
| FD003 | C_lower_matched | 4.000 | 0.000 | 70 | 70 | 0.057 | 10.167 | 9.000 | 1.000 | 0.000 | 4 | nan |
| FD003 | D_cost_25 | 11.000 | 0.000 | 70 | 70 | 0.014 | 10.739 | 10.000 | 1.000 | 0.000 | 1 | nan |
| FD003 | D_cost_50 | 11.000 | 0.000 | 70 | 70 | 0.014 | 10.739 | 10.000 | 1.000 | 0.000 | 1 | nan |
| FD003 | D_cost_100 | 11.000 | 0.000 | 70 | 70 | 0.014 | 10.739 | 10.000 | 1.000 | 0.000 | 1 | nan |
| FD003 | D_cost_200 | 11.000 | 0.000 | 70 | 70 | 0.014 | 10.739 | 10.000 | 1.000 | 0.000 | 1 | nan |
| FD003 | D_cost_500 | 11.000 | 0.000 | 70 | 70 | 0.014 | 10.739 | 10.000 | 1.000 | 0.000 | 1 | nan |
| FD004 | A_point_T | 25.000 | 0.000 | 174 | 174 | 0.006 | 25.653 | 24.000 | 0.994 | 0.017 | 1 | 5.523 |
| FD004 | C_lower_T | 25.000 | 0.000 | 174 | 174 | 0.000 | 38.874 | 34.000 | 1.000 | 0.103 | 0 | 5.747 |
| FD004 | A_point_matched | 13.000 | 0.000 | 174 | 174 | 0.046 | 13.970 | 13.000 | 0.971 | 0.012 | 8 | nan |
| FD004 | B_margin_matched | 25.000 | 0.000 | 174 | 174 | 0.006 | 25.653 | 24.000 | 0.994 | 0.017 | 1 | nan |
| FD004 | C_lower_matched | 8.000 | 0.000 | 174 | 174 | 0.006 | 14.312 | 13.000 | 1.000 | 0.011 | 1 | nan |
| FD004 | D_cost_25 | 13.000 | 0.000 | 174 | 174 | 0.046 | 13.970 | 13.000 | 0.971 | 0.012 | 8 | nan |
| FD004 | D_cost_50 | 13.000 | 0.000 | 174 | 174 | 0.046 | 13.970 | 13.000 | 0.971 | 0.012 | 8 | nan |
| FD004 | D_cost_100 | 13.000 | 0.000 | 174 | 174 | 0.046 | 13.970 | 13.000 | 0.971 | 0.012 | 8 | nan |
| FD004 | D_cost_200 | 17.000 | 0.000 | 174 | 174 | 0.017 | 17.626 | 16.000 | 0.989 | 0.012 | 3 | nan |
| FD004 | D_cost_500 | 17.000 | 0.000 | 174 | 174 | 0.017 | 17.626 | 16.000 | 0.989 | 0.012 | 3 | nan |

## Secondary: late-rate / discarded-life frontier (tuned on tuning engines, evaluated on eval engines)
| subset | target_late_rate | A_threshold | A_late_eval | A_discarded_eval | C_threshold | C_late_eval | C_discarded_eval | C_better_or_equal | C_dominated |
|---|---|---|---|---|---|---|---|---|---|
| FD001 | 0.000 | 10.000 | 0.057 | 9.985 | 7.000 | 0.014 | 15.710 | False | False |
| FD001 | 0.025 | 10.000 | 0.057 | 9.985 | 7.000 | 0.014 | 15.710 | False | False |
| FD001 | 0.050 | 10.000 | 0.057 | 9.985 | 6.000 | 0.014 | 14.174 | False | False |
| FD001 | 0.100 | 8.000 | 0.214 | 8.109 | 6.000 | 0.014 | 14.174 | False | False |
| FD002 | 0.000 | 16.000 | 0.000 | 16.099 | 6.000 | 0.033 | 12.153 | False | False |
| FD002 | 0.025 | 12.000 | 0.016 | 11.927 | 5.000 | 0.071 | 11.183 | False | False |
| FD002 | 0.050 | 11.000 | 0.027 | 10.774 | 5.000 | 0.071 | 11.183 | False | True |
| FD002 | 0.100 | 10.000 | 0.088 | 10.205 | 4.000 | 0.121 | 10.287 | False | True |
| FD003 | 0.000 | 11.000 | 0.014 | 10.739 | 6.000 | 0.000 | 12.371 | False | False |
| FD003 | 0.025 | 11.000 | 0.014 | 10.739 | 6.000 | 0.000 | 12.371 | False | False |
| FD003 | 0.050 | 11.000 | 0.014 | 10.739 | 4.000 | 0.057 | 10.167 | False | False |
| FD003 | 0.100 | 10.000 | 0.029 | 9.956 | 4.000 | 0.057 | 10.167 | False | True |
| FD004 | 0.000 | 17.000 | 0.017 | 17.626 | 10.000 | 0.000 | 17.149 | True | False |
| FD004 | 0.025 | 15.000 | 0.023 | 15.712 | 9.000 | 0.000 | 15.690 | True | False |
| FD004 | 0.050 | 13.000 | 0.046 | 13.970 | 8.000 | 0.006 | 14.312 | False | False |
| FD004 | 0.100 | 12.000 | 0.057 | 12.835 | 6.000 | 0.023 | 11.935 | True | False |

## Verdict
H1 primary (pre-registered): (i) late rate C<A at equal threshold on 1/4 subsets (informative, i.e. any late orders at T=25, on 1/4); (ii) discarded life C<=B at matched late rate on 4/4 subsets; criterion (>=3/4 on both): NOT SUPPORTED. Secondary frontier (A-family vs C-family at matched late-rate targets [0.0, 0.025, 0.05, 0.1]): C better-or-equal on both metrics in 3/16 target points, C dominated in 3/16.

```json
{
 "FD001": {
  "H1_i_late_rate_C_lt_A_equal_threshold": false,
  "H1_i_informative": false,
  "late_A_T": 0.0,
  "late_C_T": 0.0,
  "discarded_A_T": 25.242857142857144,
  "discarded_C_T": 40.25714285714286,
  "H1_ii_discarded_C_le_B_matched": true,
  "discarded_B_matched": 25.242857142857144,
  "discarded_C_matched": 14.173913043478262,
  "late_B_matched_eval": 0.0,
  "late_C_matched_eval": 0.014285714285714285,
  "tuned": {
   "tC": 6.0,
   "mB": 0.0,
   "tA": 10.0
  },
  "n_tune": 30,
  "n_eval": 70,
  "frontier_C_better_or_equal_count": 0,
  "frontier_C_dominated_count": 0,
  "note": "B (point minus margin) is the same policy family as A; reported because it was pre-registered.",
  "test_engine_view": {
   "A_point_T": {
    "n_engines": 100,
    "n_pending": 80,
    "n_evaluable": 20,
    "late_rate": 0.0,
    "order_rate": 0.2,
    "mean_discarded_life": 26.9
   },
   "C_lower_T": {
    "n_engines": 100,
    "n_pending": 73,
    "n_evaluable": 27,
    "late_rate": 0.0,
    "order_rate": 0.27,
    "mean_discarded_life": 39.2962962962963
   }
  }
 },
 "FD002": {
  "H1_i_late_rate_C_lt_A_equal_threshold": false,
  "H1_i_informative": false,
  "late_A_T": 0.0,
  "late_C_T": 0.0,
  "discarded_A_T": 26.543956043956044,
  "discarded_C_T": 39.1978021978022,
  "H1_ii_discarded_C_le_B_matched": true,
  "discarded_B_matched": 26.543956043956044,
  "discarded_C_matched": 11.183431952662723,
  "late_B_matched_eval": 0.0,
  "late_C_matched_eval": 0.07142857142857142,
  "tuned": {
   "tC": 5.0,
   "mB": 0.0,
   "tA": 11.0
  },
  "n_tune": 78,
  "n_eval": 182,
  "frontier_C_better_or_equal_count": 0,
  "frontier_C_dominated_count": 2,
  "note": "B (point minus margin) is the same policy family as A; reported because it was pre-registered.",
  "test_engine_view": {
   "A_point_T": {
    "n_engines": 259,
    "n_pending": 202,
    "n_evaluable": 57,
    "late_rate": 0.0,
    "order_rate": 0.22007722007722008,
    "mean_discarded_life": 25.789473684210527
   },
   "C_lower_T": {
    "n_engines": 259,
    "n_pending": 187,
    "n_evaluable": 72,
    "late_rate": 0.0,
    "order_rate": 0.277992277992278,
    "mean_discarded_life": 40.736111111111114
   }
  }
 },
 "FD003": {
  "H1_i_late_rate_C_lt_A_equal_threshold": false,
  "H1_i_informative": false,
  "late_A_T": 0.0,
  "late_C_T": 0.0,
  "discarded_A_T": 25.742857142857144,
  "discarded_C_T": 36.7,
  "H1_ii_discarded_C_le_B_matched": true,
  "discarded_B_matched": 25.742857142857144,
  "discarded_C_matched": 10.166666666666666,
  "late_B_matched_eval": 0.0,
  "late_C_matched_eval": 0.05714285714285714,
  "tuned": {
   "tC": 4.0,
   "mB": 0.0,
   "tA": 11.0
  },
  "n_tune": 30,
  "n_eval": 70,
  "frontier_C_better_or_equal_count": 0,
  "frontier_C_dominated_count": 1,
  "note": "B (point minus margin) is the same policy family as A; reported because it was pre-registered.",
  "test_engine_view": {
   "A_point_T": {
    "n_engines": 100,
    "n_pending": 84,
    "n_evaluable": 16,
    "late_rate": 0.0,
    "order_rate": 0.16,
    "mean_discarded_life": 24.5
   },
   "C_lower_T": {
    "n_engines": 100,
    "n_pending": 77,
    "n_evaluable": 23,
    "late_rate": 0.0,
    "order_rate": 0.23,
    "mean_discarded_life": 36.65217391304348
   }
  }
 },
 "FD004": {
  "H1_i_late_rate_C_lt_A_equal_threshold": true,
  "H1_i_informative": true,
  "late_A_T": 0.005747126436781609,
  "late_C_T": 0.0,
  "discarded_A_T": 25.653179190751445,
  "discarded_C_T": 38.87356321839081,
  "H1_ii_discarded_C_le_B_matched": true,
  "discarded_B_matched": 25.653179190751445,
  "discarded_C_matched": 14.3121387283237,
  "late_B_matched_eval": 0.005747126436781609,
  "late_C_matched_eval": 0.005747126436781609,
  "tuned": {
   "tC": 8.0,
   "mB": 0.0,
   "tA": 13.0
  },
  "n_tune": 75,
  "n_eval": 174,
  "frontier_C_better_or_equal_count": 3,
  "frontier_C_dominated_count": 0,
  "note": "B (point minus margin) is the same policy family as A; reported because it was pre-registered.",
  "test_engine_view": {
   "A_point_T": {
    "n_engines": 248,
    "n_pending": 203,
    "n_evaluable": 45,
    "late_rate": 0.0,
    "order_rate": 0.1814516129032258,
    "mean_discarded_life": 32.84444444444444
   },
   "C_lower_T": {
    "n_engines": 248,
    "n_pending": 184,
    "n_evaluable": 64,
    "late_rate": 0.0,
    "order_rate": 0.25806451612903225,
    "mean_discarded_life": 40.75
   }
  }
 }
}
```
