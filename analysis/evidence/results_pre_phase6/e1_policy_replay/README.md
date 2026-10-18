# E1 — Maintenance-policy replay (H1)

Protocol: out-of-fold CQR predictions over complete training trajectories (5 engine folds, inner 30% calibration split); tune/eval engine split 30/70; min lead 5 cycles; target late rate 5% for the pre-registered matched comparison; cost ratios are ASSUMED failure costs in cycles of discarded life ([25, 50, 100, 200, 500]).

Note: policy B (point minus margin) is the same family as policy A (a shifted threshold); it is reported because it was pre-registered. The informative comparison is the A-family vs the C-family (lower bound) frontier below (secondary analysis, added after the fast smoke run showed zero late orders at T=25).

## Pre-registered table
| subset | policy | threshold | margin | n_engines | n_evaluable | late_rate | mean_discarded_life | median_discarded_life | order_rate | early_rate | n_late | churn |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| FD001 | A_point_T | 25.000 | 0.000 | 70 | 70 | 0.000 | 25.171 | 25.000 | 1.000 | 0.000 | 0 | 5.429 |
| FD001 | C_lower_T | 25.000 | 0.000 | 70 | 70 | 0.000 | 42.886 | 37.000 | 1.000 | 0.171 | 0 | 5.314 |
| FD001 | A_point_matched | 10.000 | 0.000 | 70 | 70 | 0.071 | 9.954 | 10.000 | 1.000 | 0.000 | 5 | nan |
| FD001 | B_margin_matched | 25.000 | 0.000 | 70 | 70 | 0.000 | 25.171 | 25.000 | 1.000 | 0.000 | 0 | nan |
| FD001 | C_lower_matched | 6.000 | 0.000 | 70 | 70 | 0.014 | 16.087 | 15.000 | 1.000 | 0.000 | 1 | nan |
| FD001 | D_cost_25 | 8.000 | 0.000 | 70 | 70 | 0.214 | 8.436 | 8.000 | 1.000 | 0.000 | 15 | nan |
| FD001 | D_cost_50 | 12.000 | 0.000 | 70 | 70 | 0.014 | 11.812 | 11.000 | 1.000 | 0.000 | 1 | nan |
| FD001 | D_cost_100 | 12.000 | 0.000 | 70 | 70 | 0.014 | 11.812 | 11.000 | 1.000 | 0.000 | 1 | nan |
| FD001 | D_cost_200 | 12.000 | 0.000 | 70 | 70 | 0.014 | 11.812 | 11.000 | 1.000 | 0.000 | 1 | nan |
| FD001 | D_cost_500 | 12.000 | 0.000 | 70 | 70 | 0.014 | 11.812 | 11.000 | 1.000 | 0.000 | 1 | nan |
| FD002 | A_point_T | 25.000 | 0.000 | 182 | 182 | 0.000 | 26.736 | 25.000 | 1.000 | 0.005 | 0 | 5.110 |
| FD002 | C_lower_T | 25.000 | 0.000 | 182 | 182 | 0.000 | 39.648 | 36.000 | 1.000 | 0.104 | 0 | 5.236 |
| FD002 | A_point_matched | 11.000 | 0.000 | 182 | 182 | 0.033 | 11.205 | 10.000 | 1.000 | 0.000 | 6 | nan |
| FD002 | B_margin_matched | 25.000 | 0.000 | 182 | 182 | 0.000 | 26.736 | 25.000 | 1.000 | 0.005 | 0 | nan |
| FD002 | C_lower_matched | 5.000 | 0.000 | 182 | 182 | 0.055 | 11.651 | 11.000 | 1.000 | 0.000 | 10 | nan |
| FD002 | D_cost_25 | 9.000 | 0.000 | 182 | 182 | 0.154 | 9.844 | 9.000 | 1.000 | 0.000 | 28 | nan |
| FD002 | D_cost_50 | 12.000 | 0.000 | 182 | 182 | 0.022 | 11.966 | 11.000 | 1.000 | 0.000 | 4 | nan |
| FD002 | D_cost_100 | 12.000 | 0.000 | 182 | 182 | 0.022 | 11.966 | 11.000 | 1.000 | 0.000 | 4 | nan |
| FD002 | D_cost_200 | 14.000 | 0.000 | 182 | 182 | 0.005 | 13.928 | 14.000 | 1.000 | 0.000 | 1 | nan |
| FD002 | D_cost_500 | 14.000 | 0.000 | 182 | 182 | 0.005 | 13.928 | 14.000 | 1.000 | 0.000 | 1 | nan |
| FD003 | A_point_T | 25.000 | 0.000 | 70 | 70 | 0.000 | 25.729 | 25.000 | 1.000 | 0.000 | 0 | 4.314 |
| FD003 | C_lower_T | 25.000 | 0.000 | 70 | 70 | 0.000 | 36.986 | 32.500 | 1.000 | 0.071 | 0 | 5.214 |
| FD003 | A_point_matched | 10.000 | 0.000 | 70 | 70 | 0.029 | 10.147 | 9.000 | 1.000 | 0.000 | 2 | nan |
| FD003 | B_margin_matched | 25.000 | 0.000 | 70 | 70 | 0.000 | 25.729 | 25.000 | 1.000 | 0.000 | 0 | nan |
| FD003 | C_lower_matched | 5.000 | 0.000 | 70 | 70 | 0.029 | 11.676 | 11.000 | 1.000 | 0.000 | 2 | nan |
| FD003 | D_cost_25 | 10.000 | 0.000 | 70 | 70 | 0.029 | 10.147 | 9.000 | 1.000 | 0.000 | 2 | nan |
| FD003 | D_cost_50 | 10.000 | 0.000 | 70 | 70 | 0.029 | 10.147 | 9.000 | 1.000 | 0.000 | 2 | nan |
| FD003 | D_cost_100 | 10.000 | 0.000 | 70 | 70 | 0.029 | 10.147 | 9.000 | 1.000 | 0.000 | 2 | nan |
| FD003 | D_cost_200 | 10.000 | 0.000 | 70 | 70 | 0.029 | 10.147 | 9.000 | 1.000 | 0.000 | 2 | nan |
| FD003 | D_cost_500 | 10.000 | 0.000 | 70 | 70 | 0.029 | 10.147 | 9.000 | 1.000 | 0.000 | 2 | nan |
| FD004 | A_point_T | 25.000 | 0.000 | 174 | 174 | 0.006 | 26.006 | 24.000 | 0.994 | 0.017 | 1 | 5.351 |
| FD004 | C_lower_T | 25.000 | 0.000 | 174 | 174 | 0.000 | 38.839 | 34.000 | 1.000 | 0.098 | 0 | 5.690 |
| FD004 | A_point_matched | 12.000 | 0.000 | 174 | 174 | 0.069 | 12.994 | 12.000 | 0.960 | 0.012 | 12 | nan |
| FD004 | B_margin_matched | 25.000 | 0.000 | 174 | 174 | 0.006 | 26.006 | 24.000 | 0.994 | 0.017 | 1 | nan |
| FD004 | C_lower_matched | 8.000 | 0.000 | 174 | 174 | 0.011 | 14.523 | 13.000 | 1.000 | 0.011 | 2 | nan |
| FD004 | D_cost_25 | 12.000 | 0.000 | 174 | 174 | 0.069 | 12.994 | 12.000 | 0.960 | 0.012 | 12 | nan |
| FD004 | D_cost_50 | 13.000 | 0.000 | 174 | 174 | 0.052 | 13.842 | 13.000 | 0.966 | 0.012 | 9 | nan |
| FD004 | D_cost_100 | 13.000 | 0.000 | 174 | 174 | 0.052 | 13.842 | 13.000 | 0.966 | 0.012 | 9 | nan |
| FD004 | D_cost_200 | 18.000 | 0.000 | 174 | 174 | 0.023 | 18.947 | 18.000 | 0.989 | 0.017 | 4 | nan |
| FD004 | D_cost_500 | 18.000 | 0.000 | 174 | 174 | 0.023 | 18.947 | 18.000 | 0.989 | 0.017 | 4 | nan |

## Secondary: late-rate / discarded-life frontier (tuned on tuning engines, evaluated on eval engines)
| subset | target_late_rate | A_threshold | A_late_eval | A_discarded_eval | C_threshold | C_late_eval | C_discarded_eval | C_better_or_equal | C_dominated |
|---|---|---|---|---|---|---|---|---|---|
| FD001 | 0.000 | 12.000 | 0.014 | 11.812 | 8.000 | 0.000 | 19.043 | False | False |
| FD001 | 0.025 | 12.000 | 0.014 | 11.812 | 8.000 | 0.000 | 19.043 | False | False |
| FD001 | 0.050 | 10.000 | 0.071 | 9.954 | 6.000 | 0.014 | 16.087 | False | False |
| FD001 | 0.100 | 8.000 | 0.214 | 8.436 | 5.000 | 0.014 | 15.333 | False | False |
| FD002 | 0.000 | 14.000 | 0.005 | 13.928 | 6.000 | 0.022 | 12.685 | False | False |
| FD002 | 0.025 | 12.000 | 0.022 | 11.966 | 5.000 | 0.055 | 11.651 | False | False |
| FD002 | 0.050 | 11.000 | 0.033 | 11.205 | 5.000 | 0.055 | 11.651 | False | True |
| FD002 | 0.100 | 9.000 | 0.154 | 9.844 | 4.000 | 0.115 | 10.391 | False | False |
| FD003 | 0.000 | 10.000 | 0.029 | 10.147 | 8.000 | 0.000 | 15.429 | False | False |
| FD003 | 0.025 | 10.000 | 0.029 | 10.147 | 8.000 | 0.000 | 15.429 | False | False |
| FD003 | 0.050 | 10.000 | 0.029 | 10.147 | 5.000 | 0.029 | 11.676 | False | False |
| FD003 | 0.100 | 10.000 | 0.029 | 10.147 | 4.000 | 0.043 | 10.672 | False | True |
| FD004 | 0.000 | 18.000 | 0.023 | 18.947 | 10.000 | 0.000 | 17.149 | True | False |
| FD004 | 0.025 | 15.000 | 0.029 | 15.473 | 10.000 | 0.000 | 17.149 | False | False |
| FD004 | 0.050 | 12.000 | 0.069 | 12.994 | 8.000 | 0.011 | 14.523 | False | False |
| FD004 | 0.100 | 11.000 | 0.115 | 12.279 | 6.000 | 0.029 | 12.095 | True | False |

## Verdict
H1 primary (pre-registered): (i) late rate C<A at equal threshold on 1/4 subsets (informative, i.e. any late orders at T=25, on 1/4); (ii) discarded life C<=B at matched late rate on 4/4 subsets; criterion (>=3/4 on both): NOT SUPPORTED. Secondary frontier (A-family vs C-family at matched late-rate targets [0.0, 0.025, 0.05, 0.1]): C better-or-equal on both metrics in 2/16 target points, C dominated in 2/16.

```json
{
 "FD001": {
  "H1_i_late_rate_C_lt_A_equal_threshold": false,
  "H1_i_informative": false,
  "late_A_T": 0.0,
  "late_C_T": 0.0,
  "discarded_A_T": 25.17142857142857,
  "discarded_C_T": 42.885714285714286,
  "H1_ii_discarded_C_le_B_matched": true,
  "discarded_B_matched": 25.17142857142857,
  "discarded_C_matched": 16.08695652173913,
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
    "mean_discarded_life": 26.7
   },
   "C_lower_T": {
    "n_engines": 100,
    "n_pending": 70,
    "n_evaluable": 30,
    "late_rate": 0.0,
    "order_rate": 0.3,
    "mean_discarded_life": 39.0
   }
  }
 },
 "FD002": {
  "H1_i_late_rate_C_lt_A_equal_threshold": false,
  "H1_i_informative": false,
  "late_A_T": 0.0,
  "late_C_T": 0.0,
  "discarded_A_T": 26.736263736263737,
  "discarded_C_T": 39.64835164835165,
  "H1_ii_discarded_C_le_B_matched": true,
  "discarded_B_matched": 26.736263736263737,
  "discarded_C_matched": 11.651162790697674,
  "late_B_matched_eval": 0.0,
  "late_C_matched_eval": 0.054945054945054944,
  "tuned": {
   "tC": 5.0,
   "mB": 0.0,
   "tA": 11.0
  },
  "n_tune": 78,
  "n_eval": 182,
  "frontier_C_better_or_equal_count": 0,
  "frontier_C_dominated_count": 1,
  "note": "B (point minus margin) is the same policy family as A; reported because it was pre-registered.",
  "test_engine_view": {
   "A_point_T": {
    "n_engines": 259,
    "n_pending": 201,
    "n_evaluable": 58,
    "late_rate": 0.0,
    "order_rate": 0.22393822393822393,
    "mean_discarded_life": 26.03448275862069
   },
   "C_lower_T": {
    "n_engines": 259,
    "n_pending": 187,
    "n_evaluable": 72,
    "late_rate": 0.0,
    "order_rate": 0.277992277992278,
    "mean_discarded_life": 41.02777777777778
   }
  }
 },
 "FD003": {
  "H1_i_late_rate_C_lt_A_equal_threshold": false,
  "H1_i_informative": false,
  "late_A_T": 0.0,
  "late_C_T": 0.0,
  "discarded_A_T": 25.728571428571428,
  "discarded_C_T": 36.98571428571429,
  "H1_ii_discarded_C_le_B_matched": true,
  "discarded_B_matched": 25.728571428571428,
  "discarded_C_matched": 11.676470588235293,
  "late_B_matched_eval": 0.0,
  "late_C_matched_eval": 0.02857142857142857,
  "tuned": {
   "tC": 5.0,
   "mB": 0.0,
   "tA": 10.0
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
    "n_pending": 78,
    "n_evaluable": 22,
    "late_rate": 0.0,
    "order_rate": 0.22,
    "mean_discarded_life": 34.04545454545455
   }
  }
 },
 "FD004": {
  "H1_i_late_rate_C_lt_A_equal_threshold": true,
  "H1_i_informative": true,
  "late_A_T": 0.005747126436781609,
  "late_C_T": 0.0,
  "discarded_A_T": 26.00578034682081,
  "discarded_C_T": 38.839080459770116,
  "H1_ii_discarded_C_le_B_matched": true,
  "discarded_B_matched": 26.00578034682081,
  "discarded_C_matched": 14.523255813953488,
  "late_B_matched_eval": 0.005747126436781609,
  "late_C_matched_eval": 0.011494252873563218,
  "tuned": {
   "tC": 8.0,
   "mB": 0.0,
   "tA": 12.0
  },
  "n_tune": 75,
  "n_eval": 174,
  "frontier_C_better_or_equal_count": 2,
  "frontier_C_dominated_count": 0,
  "note": "B (point minus margin) is the same policy family as A; reported because it was pre-registered.",
  "test_engine_view": {
   "A_point_T": {
    "n_engines": 248,
    "n_pending": 201,
    "n_evaluable": 47,
    "late_rate": 0.0,
    "order_rate": 0.18951612903225806,
    "mean_discarded_life": 32.02127659574468
   },
   "C_lower_T": {
    "n_engines": 248,
    "n_pending": 183,
    "n_evaluable": 65,
    "late_rate": 0.0,
    "order_rate": 0.2620967741935484,
    "mean_discarded_life": 40.58461538461538
   }
  }
 }
}
```
