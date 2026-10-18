# S1 policy comparison (generated; SIMULATED)

384 runs, 8 seeds, 120 days, runtime 7.4 min.

## base

| policy | total cost | failures | A failures | unplanned downtime h | preventive repairs | early repairs | inspections (no fault) | late jobs | violations | plan change rate | approvals/day |
|---|---|---|---|---|---|---|---|---|---|---|---|
| RUN_TO_FAILURE | 444.3 ± 64.6 | 116.8 ± 2.1 | 13.9 ± 8.0 | 5336 ± 205 | 0.0 ± 0.0 | 0.0 ± 0.0 | 0.0 ± 0.0 (0.0 ± 0.0) | 0.0 ± 0.0 | 0 ± 0 | 0.00 ± 0.00 | 0.00 ± 0.00 |
| FIXED_INTERVAL | 214.9 ± 10.0 | 8.4 ± 1.2 | 1.2 ± 1.2 | 388 ± 61 | 181.4 ± 1.6 | 127.1 ± 3.1 | 0.0 ± 0.0 (0.0 ± 0.0) | 3.8 ± 1.8 | 0 ± 0 | 0.00 ± 0.01 | 1.62 ± 0.01 |
| THRESHOLD_EDD | 150.8 ± 8.2 | 9.0 ± 2.6 | 0.9 ± 0.6 | 615 ± 271 | 118.0 ± 3.5 | 0.0 ± 0.0 | 0.0 ± 0.0 (0.0 ± 0.0) | 7.2 ± 1.9 | 0 ± 0 | 0.31 ± 0.12 | 1.13 ± 0.03 |
| RISK_CRITICALITY_FIRST | 145.0 ± 7.0 | 10.2 ± 2.3 | 0.2 ± 0.5 | 781 ± 298 | 119.1 ± 3.1 | 0.5 ± 0.5 | 49.6 ± 4.4 (4.2 ± 1.2) | 5.8 ± 1.8 | 0 ± 0 | 0.59 ± 0.09 | 1.59 ± 0.05 |
| RISK_GREEDY | 139.7 ± 5.2 | 4.0 ± 2.4 | 0.1 ± 0.4 | 258 ± 149 | 127.0 ± 2.9 | 0.4 ± 0.5 | 40.8 ± 4.0 (3.9 ± 1.4) | 2.6 ± 1.6 | 0 ± 0 | 0.48 ± 0.11 | 1.47 ± 0.04 |
| RISK_GREEDY_STABLE | 141.3 ± 6.1 | 4.8 ± 3.2 | 0.1 ± 0.4 | 367 ± 273 | 125.9 ± 3.5 | 0.5 ± 0.5 | 41.5 ± 4.2 (3.5 ± 1.6) | 3.5 ± 2.2 | 0 ± 0 | 0.30 ± 0.09 | 1.48 ± 0.05 |
| RISK_MILP | 144.3 ± 7.1 | 5.4 ± 3.3 | 0.2 ± 0.5 | 258 ± 194 | 125.5 ± 3.3 | 0.2 ± 0.5 | 46.0 ± 3.8 (4.1 ± 1.0) | 1.8 ± 1.5 | 0 ± 0 | 0.46 ± 0.08 | 1.53 ± 0.04 |
| RISK_MILP_STABLE | 142.3 ± 5.5 | 5.2 ± 2.5 | 0.0 ± 0.0 | 278 ± 150 | 125.4 ± 2.8 | 0.5 ± 0.5 | 47.0 ± 3.9 (4.4 ± 1.1) | 2.2 ± 1.6 | 0 ± 0 | 0.12 ± 0.04 | 1.53 ± 0.04 |

Paired against THRESHOLD_EDD (same seeds): total cost difference mean [min, max], seeds better / worse

- RUN_TO_FAILURE: +293.5 [+195.5, +407.5], better on 0/8, worse on 8/8
- FIXED_INTERVAL: +64.1 [+46.0, +78.5], better on 0/8, worse on 8/8
- THRESHOLD_EDD: +0.0 [+0.0, +0.0], better on 0/8, worse on 0/8
- RISK_CRITICALITY_FIRST: -5.8 [-20.7, +10.5], better on 6/8, worse on 1/8
- RISK_GREEDY: -11.1 [-22.7, +1.6], better on 7/8, worse on 1/8
- RISK_GREEDY_STABLE: -9.5 [-20.2, +1.6], better on 7/8, worse on 1/8
- RISK_MILP: -6.5 [-16.0, +10.9], better on 6/8, worse on 2/8
- RISK_MILP_STABLE: -8.5 [-22.1, +7.5], better on 6/8, worse on 2/8

## tight_labour

| policy | total cost | failures | A failures | unplanned downtime h | preventive repairs | early repairs | inspections (no fault) | late jobs | violations | plan change rate | approvals/day |
|---|---|---|---|---|---|---|---|---|---|---|---|
| RUN_TO_FAILURE | 419.0 ± 65.1 | 109.0 ± 2.3 | 13.6 ± 8.6 | 10435 ± 1229 | 0.0 ± 0.0 | 0.0 ± 0.0 | 0.0 ± 0.0 (0.0 ± 0.0) | 0.0 ± 0.0 | 0 ± 0 | 0.00 ± 0.00 | 0.00 ± 0.00 |
| FIXED_INTERVAL | 319.8 ± 37.0 | 68.4 ± 3.9 | 9.0 ± 4.7 | 14339 ± 947 | 52.9 ± 4.8 | 30.5 ± 4.0 | 0.0 ± 0.0 (0.0 ± 0.0) | 4.4 ± 1.8 | 0 ± 0 | 0.03 ± 0.01 | 1.61 ± 0.03 |
| THRESHOLD_EDD | 197.7 ± 15.9 | 35.5 ± 4.2 | 3.8 ± 1.9 | 15827 ± 1815 | 66.0 ± 5.1 | 0.0 ± 0.0 | 0.0 ± 0.0 (0.0 ± 0.0) | 19.0 ± 3.1 | 0 ± 0 | 0.48 ± 0.04 | 1.14 ± 0.04 |
| RISK_CRITICALITY_FIRST | 164.3 ± 16.8 | 32.1 ± 4.8 | 0.2 ± 0.5 | 11295 ± 2843 | 77.8 ± 5.4 | 0.2 ± 0.5 | 52.8 ± 5.9 (4.6 ± 1.6) | 9.4 ± 2.7 | 0 ± 0 | 0.53 ± 0.05 | 1.63 ± 0.08 |
| RISK_GREEDY | 158.2 ± 15.0 | 29.0 ± 4.4 | 0.1 ± 0.4 | 10945 ± 3095 | 81.8 ± 7.3 | 0.2 ± 0.5 | 53.0 ± 5.3 (4.6 ± 1.6) | 9.6 ± 4.7 | 0 ± 0 | 0.52 ± 0.02 | 1.62 ± 0.06 |
| RISK_GREEDY_STABLE | 162.8 ± 19.9 | 29.9 ± 4.4 | 0.5 ± 1.1 | 11497 ± 2969 | 80.0 ± 6.0 | 0.2 ± 0.5 | 52.5 ± 5.1 (4.6 ± 1.6) | 10.6 ± 3.6 | 0 ± 0 | 0.49 ± 0.05 | 1.61 ± 0.07 |
| RISK_MILP | 182.2 ± 13.7 | 37.9 ± 3.5 | 0.5 ± 0.5 | 7085 ± 1395 | 79.0 ± 3.7 | 0.1 ± 0.4 | 56.2 ± 4.7 (4.9 ± 1.4) | 1.0 ± 1.3 | 0 ± 0 | 0.70 ± 0.06 | 1.77 ± 0.04 |
| RISK_MILP_STABLE | 175.2 ± 13.7 | 38.1 ± 4.4 | 0.1 ± 0.4 | 7799 ± 1323 | 77.6 ± 4.3 | 0.4 ± 0.5 | 55.6 ± 4.6 (4.9 ± 1.4) | 2.2 ± 1.3 | 0 ± 0 | 0.45 ± 0.04 | 1.76 ± 0.04 |

Paired against THRESHOLD_EDD (same seeds): total cost difference mean [min, max], seeds better / worse

- RUN_TO_FAILURE: +221.3 [+156.5, +331.0], better on 0/8, worse on 8/8
- FIXED_INTERVAL: +122.1 [+97.0, +178.5], better on 0/8, worse on 8/8
- THRESHOLD_EDD: +0.0 [+0.0, +0.0], better on 0/8, worse on 0/8
- RISK_CRITICALITY_FIRST: -33.4 [-53.5, -13.0], better on 8/8, worse on 0/8
- RISK_GREEDY: -39.5 [-55.9, -26.0], better on 8/8, worse on 0/8
- RISK_GREEDY_STABLE: -34.9 [-59.1, -15.0], better on 8/8, worse on 0/8
- RISK_MILP: -15.4 [-33.8, +11.0], better on 7/8, worse on 1/8
- RISK_MILP_STABLE: -22.5 [-48.0, -1.0], better on 8/8, worse on 0/8

## parts_shortage

| policy | total cost | failures | A failures | unplanned downtime h | preventive repairs | early repairs | inspections (no fault) | late jobs | violations | plan change rate | approvals/day |
|---|---|---|---|---|---|---|---|---|---|---|---|
| RUN_TO_FAILURE | 210.6 ± 31.7 | 55.1 ± 1.2 | 6.6 ± 3.7 | 35276 ± 941 | 0.0 ± 0.0 | 0.0 ± 0.0 | 0.0 ± 0.0 (0.0 ± 0.0) | 0.0 ± 0.0 | 0 ± 0 | 0.00 ± 0.00 | 0.00 ± 0.00 |
| FIXED_INTERVAL | 202.4 ± 34.0 | 51.9 ± 1.9 | 6.2 ± 4.0 | 34218 ± 893 | 5.5 ± 1.2 | 4.1 ± 1.5 | 0.0 ± 0.0 (0.0 ± 0.0) | 0.5 ± 0.5 | 0 ± 0 | 0.01 ± 0.01 | 0.92 ± 0.02 |
| THRESHOLD_EDD | 169.7 ± 18.6 | 41.0 ± 3.3 | 4.6 ± 2.4 | 26844 ± 3529 | 13.9 ± 3.2 | 0.0 ± 0.0 | 0.0 ± 0.0 (0.0 ± 0.0) | 6.2 ± 1.4 | 0 ± 0 | 0.24 ± 0.04 | 0.80 ± 0.03 |
| RISK_CRITICALITY_FIRST | 197.8 ± 41.9 | 41.1 ± 3.5 | 7.1 ± 5.7 | 14892 ± 3578 | 14.6 ± 3.6 | 0.0 ± 0.0 | 25.4 ± 4.1 (1.8 ± 1.3) | 2.8 ± 0.9 | 0 ± 0 | 0.25 ± 0.05 | 1.02 ± 0.05 |
| RISK_GREEDY | 165.1 ± 24.1 | 40.5 ± 2.4 | 4.1 ± 2.5 | 26180 ± 3995 | 15.5 ± 2.4 | 0.1 ± 0.4 | 25.2 ± 4.0 (2.0 ± 1.2) | 3.6 ± 1.7 | 0 ± 0 | 0.26 ± 0.06 | 1.02 ± 0.04 |
| RISK_GREEDY_STABLE | 162.8 ± 24.8 | 40.0 ± 2.5 | 4.0 ± 2.6 | 25890 ± 3923 | 16.0 ± 2.5 | 0.1 ± 0.4 | 25.2 ± 4.0 (2.0 ± 1.2) | 3.1 ± 1.5 | 0 ± 0 | 0.21 ± 0.05 | 1.01 ± 0.03 |
| RISK_MILP | 203.8 ± 46.8 | 41.5 ± 2.4 | 7.9 ± 6.3 | 10279 ± 2030 | 14.5 ± 2.4 | 0.1 ± 0.4 | 25.8 ± 3.4 (2.0 ± 1.2) | 0.4 ± 0.5 | 0 ± 0 | 0.63 ± 0.09 | 1.03 ± 0.03 |
| RISK_MILP_STABLE | 202.6 ± 47.8 | 41.6 ± 2.7 | 7.6 ± 6.4 | 11612 ± 3276 | 14.4 ± 2.7 | 0.1 ± 0.4 | 25.8 ± 3.4 (2.0 ± 1.2) | 0.6 ± 0.5 | 0 ± 0 | 0.52 ± 0.12 | 1.03 ± 0.03 |

Paired against THRESHOLD_EDD (same seeds): total cost difference mean [min, max], seeds better / worse

- RUN_TO_FAILURE: +40.9 [+17.5, +82.5], better on 0/8, worse on 8/8
- FIXED_INTERVAL: +32.7 [+2.5, +78.5], better on 0/8, worse on 8/8
- THRESHOLD_EDD: +0.0 [+0.0, +0.0], better on 0/8, worse on 0/8
- RISK_CRITICALITY_FIRST: +28.2 [-10.4, +100.7], better on 1/8, worse on 7/8
- RISK_GREEDY: -4.6 [-35.4, +22.0], better on 3/8, worse on 5/8
- RISK_GREEDY_STABLE: -6.9 [-35.4, +22.0], better on 4/8, worse on 4/8
- RISK_MILP: +34.1 [+4.7, +109.8], better on 0/8, worse on 8/8
- RISK_MILP_STABLE: +33.0 [-10.3, +109.8], better on 1/8, worse on 7/8

## degraded_predictions

| policy | total cost | failures | A failures | unplanned downtime h | preventive repairs | early repairs | inspections (no fault) | late jobs | violations | plan change rate | approvals/day |
|---|---|---|---|---|---|---|---|---|---|---|---|
| RUN_TO_FAILURE | 444.3 ± 64.6 | 116.8 ± 2.1 | 13.9 ± 8.0 | 5336 ± 205 | 0.0 ± 0.0 | 0.0 ± 0.0 | 0.0 ± 0.0 (0.0 ± 0.0) | 0.0 ± 0.0 | 0 ± 0 | 0.00 ± 0.00 | 0.00 ± 0.00 |
| FIXED_INTERVAL | 214.9 ± 10.0 | 8.4 ± 1.2 | 1.2 ± 1.2 | 388 ± 61 | 181.4 ± 1.6 | 127.1 ± 3.1 | 0.0 ± 0.0 (0.0 ± 0.0) | 3.8 ± 1.8 | 0 ± 0 | 0.00 ± 0.01 | 1.62 ± 0.01 |
| THRESHOLD_EDD | 307.1 ± 48.3 | 64.8 ± 6.3 | 8.5 ± 5.2 | 4742 ± 1181 | 53.4 ± 6.2 | 0.0 ± 0.0 | 0.0 ± 0.0 (0.0 ± 0.0) | 46.9 ± 4.2 | 0 ± 0 | 0.55 ± 0.09 | 1.42 ± 0.04 |
| RISK_CRITICALITY_FIRST | 179.7 ± 15.0 | 28.2 ± 3.1 | 1.4 ± 1.2 | 2070 ± 358 | 94.5 ± 3.4 | 0.0 ± 0.0 | 61.5 ± 4.0 (1.9 ± 0.8) | 15.0 ± 3.1 | 0 ± 0 | 0.67 ± 0.03 | 1.78 ± 0.04 |
| RISK_GREEDY | 175.2 ± 11.4 | 21.5 ± 5.2 | 1.5 ± 1.2 | 1401 ± 508 | 102.8 ± 6.0 | 0.0 ± 0.0 | 49.9 ± 4.5 (1.6 ± 0.9) | 16.8 ± 3.6 | 0 ± 0 | 0.56 ± 0.12 | 1.64 ± 0.05 |
| RISK_GREEDY_STABLE | 173.4 ± 10.1 | 20.8 ± 3.2 | 1.4 ± 1.2 | 1228 ± 343 | 103.6 ± 4.2 | 0.0 ± 0.0 | 50.9 ± 3.8 (1.6 ± 0.9) | 16.4 ± 2.9 | 0 ± 0 | 0.36 ± 0.10 | 1.64 ± 0.04 |
| RISK_MILP | 189.2 ± 18.7 | 27.9 ± 5.9 | 2.0 ± 1.9 | 1829 ± 681 | 95.4 ± 7.7 | 0.0 ± 0.0 | 53.8 ± 5.8 (1.4 ± 0.7) | 19.1 ± 3.5 | 0 ± 0 | 0.55 ± 0.09 | 1.71 ± 0.03 |
| RISK_MILP_STABLE | 185.6 ± 11.2 | 26.9 ± 4.4 | 1.6 ± 1.4 | 1593 ± 454 | 96.9 ± 6.0 | 0.0 ± 0.0 | 55.1 ± 6.1 (1.4 ± 1.1) | 17.6 ± 3.1 | 0 ± 0 | 0.15 ± 0.05 | 1.72 ± 0.04 |

Paired against THRESHOLD_EDD (same seeds): total cost difference mean [min, max], seeds better / worse

- RUN_TO_FAILURE: +137.2 [+87.0, +186.5], better on 0/8, worse on 8/8
- FIXED_INTERVAL: -92.2 [-171.0, -40.5], better on 8/8, worse on 0/8
- THRESHOLD_EDD: +0.0 [+0.0, +0.0], better on 0/8, worse on 0/8
- RISK_CRITICALITY_FIRST: -127.4 [-202.0, -89.2], better on 8/8, worse on 0/8
- RISK_GREEDY: -131.9 [-220.1, -73.8], better on 8/8, worse on 0/8
- RISK_GREEDY_STABLE: -133.7 [-222.5, -67.5], better on 8/8, worse on 0/8
- RISK_MILP: -117.9 [-178.3, -82.5], better on 8/8, worse on 0/8
- RISK_MILP_STABLE: -121.6 [-198.8, -82.3], better on 8/8, worse on 0/8

## approval_delay

| policy | total cost | failures | A failures | unplanned downtime h | preventive repairs | early repairs | inspections (no fault) | late jobs | violations | plan change rate | approvals/day |
|---|---|---|---|---|---|---|---|---|---|---|---|
| RUN_TO_FAILURE | 444.3 ± 64.6 | 116.8 ± 2.1 | 13.9 ± 8.0 | 5336 ± 205 | 0.0 ± 0.0 | 0.0 ± 0.0 | 0.0 ± 0.0 (0.0 ± 0.0) | 0.0 ± 0.0 | 0 ± 0 | 0.00 ± 0.00 | 0.00 ± 0.00 |
| FIXED_INTERVAL | 227.9 ± 16.6 | 18.8 ± 1.8 | 1.6 ± 1.7 | 999 ± 113 | 159.8 ± 2.5 | 100.1 ± 3.0 | 0.0 ± 0.0 (0.0 ± 0.0) | 8.1 ± 1.4 | 0 ± 0 | 0.03 ± 0.01 | 1.62 ± 0.01 |
| THRESHOLD_EDD | 279.6 ± 40.3 | 53.6 ± 4.1 | 7.5 ± 4.2 | 3471 ± 483 | 66.4 ± 2.8 | 0.0 ± 0.0 | 0.0 ± 0.0 (0.0 ± 0.0) | 33.1 ± 2.2 | 0 ± 0 | 0.19 ± 0.05 | 1.45 ± 0.05 |
| RISK_CRITICALITY_FIRST | 159.0 ± 12.2 | 17.9 ± 4.6 | 0.8 ± 0.7 | 1086 ± 373 | 108.2 ± 5.7 | 0.5 ± 0.5 | 10.2 ± 1.7 (1.0 ± 0.8) | 12.4 ± 2.7 | 0 ± 0 | 0.29 ± 0.06 | 1.30 ± 0.03 |
| RISK_GREEDY | 156.9 ± 9.2 | 14.2 ± 3.2 | 0.9 ± 1.1 | 893 ± 354 | 112.0 ± 3.6 | 0.5 ± 0.5 | 8.1 ± 1.2 (0.6 ± 0.5) | 10.5 ± 2.0 | 0 ± 0 | 0.36 ± 0.06 | 1.25 ± 0.03 |
| RISK_GREEDY_STABLE | 161.3 ± 10.2 | 15.6 ± 4.8 | 1.0 ± 1.1 | 1016 ± 478 | 110.5 ± 5.8 | 0.4 ± 0.5 | 7.9 ± 1.6 (0.5 ± 0.5) | 12.1 ± 2.9 | 0 ± 0 | 0.16 ± 0.04 | 1.26 ± 0.03 |
| RISK_MILP | 168.1 ± 7.2 | 19.4 ± 3.6 | 1.1 ± 1.1 | 910 ± 197 | 107.2 ± 4.7 | 0.5 ± 0.5 | 9.5 ± 0.9 (0.5 ± 0.5) | 9.8 ± 2.6 | 0 ± 0 | 0.42 ± 0.05 | 1.31 ± 0.03 |
| RISK_MILP_STABLE | 168.4 ± 10.5 | 18.5 ± 4.6 | 1.1 ± 1.0 | 1011 ± 328 | 108.0 ± 5.1 | 0.5 ± 0.5 | 8.6 ± 1.9 (0.8 ± 0.5) | 10.4 ± 2.3 | 0 ± 0 | 0.10 ± 0.03 | 1.29 ± 0.05 |

Paired against THRESHOLD_EDD (same seeds): total cost difference mean [min, max], seeds better / worse

- RUN_TO_FAILURE: +164.7 [+112.5, +269.5], better on 0/8, worse on 8/8
- FIXED_INTERVAL: -51.7 [-110.5, -11.5], better on 8/8, worse on 0/8
- THRESHOLD_EDD: +0.0 [+0.0, +0.0], better on 0/8, worse on 0/8
- RISK_CRITICALITY_FIRST: -120.6 [-201.0, -67.7], better on 8/8, worse on 0/8
- RISK_GREEDY: -122.7 [-194.8, -74.7], better on 8/8, worse on 0/8
- RISK_GREEDY_STABLE: -118.3 [-195.4, -69.1], better on 8/8, worse on 0/8
- RISK_MILP: -111.5 [-194.1, -64.7], better on 8/8, worse on 0/8
- RISK_MILP_STABLE: -111.3 [-185.3, -60.2], better on 8/8, worse on 0/8

## adverse

| policy | total cost | failures | A failures | unplanned downtime h | preventive repairs | early repairs | inspections (no fault) | late jobs | violations | plan change rate | approvals/day |
|---|---|---|---|---|---|---|---|---|---|---|---|
| RUN_TO_FAILURE | 260.7 ± 38.9 | 67.4 ± 0.7 | 8.4 ± 5.0 | 35212 ± 636 | 0.0 ± 0.0 | 0.0 ± 0.0 | 0.0 ± 0.0 (0.0 ± 0.0) | 0.0 ± 0.0 | 0 ± 0 | 0.00 ± 0.00 | 0.00 ± 0.00 |
| FIXED_INTERVAL | 243.9 ± 28.9 | 60.6 ± 3.0 | 7.5 ± 3.8 | 34416 ± 974 | 9.5 ± 1.8 | 5.4 ± 1.5 | 0.0 ± 0.0 (0.0 ± 0.0) | 0.5 ± 0.5 | 0 ± 0 | 0.01 ± 0.01 | 1.12 ± 0.03 |
| THRESHOLD_EDD | 213.6 ± 36.8 | 51.8 ± 3.5 | 6.6 ± 4.0 | 34518 ± 1719 | 12.5 ± 2.9 | 0.0 ± 0.0 | 0.0 ± 0.0 (0.0 ± 0.0) | 15.4 ± 2.7 | 0 ± 0 | 0.39 ± 0.04 | 0.92 ± 0.04 |
| RISK_CRITICALITY_FIRST | 222.4 ± 39.5 | 44.9 ± 3.2 | 7.4 ± 5.2 | 15104 ± 4575 | 21.4 ± 3.0 | 0.0 ± 0.0 | 38.2 ± 5.3 (1.4 ± 1.1) | 7.5 ± 2.3 | 0 ± 0 | 0.36 ± 0.04 | 1.25 ± 0.06 |
| RISK_GREEDY | 180.2 ± 20.6 | 42.0 ± 4.9 | 4.1 ± 2.4 | 29814 ± 2783 | 23.4 ± 4.8 | 0.0 ± 0.0 | 37.5 ± 4.7 (1.4 ± 1.1) | 9.8 ± 1.4 | 0 ± 0 | 0.38 ± 0.06 | 1.22 ± 0.07 |
| RISK_GREEDY_STABLE | 182.3 ± 24.2 | 43.0 ± 5.8 | 4.4 ± 2.7 | 30303 ± 2705 | 22.5 ± 5.3 | 0.0 ± 0.0 | 37.6 ± 4.8 (1.4 ± 1.1) | 10.2 ± 2.3 | 0 ± 0 | 0.33 ± 0.07 | 1.23 ± 0.07 |
| RISK_MILP | 227.3 ± 41.8 | 46.4 ± 3.9 | 7.5 ± 5.6 | 12664 ± 2965 | 19.6 ± 3.7 | 0.0 ± 0.0 | 37.6 ± 4.8 (1.4 ± 1.1) | 10.0 ± 4.4 | 0 ± 0 | 0.71 ± 0.05 | 1.26 ± 0.06 |
| RISK_MILP_STABLE | 227.0 ± 43.8 | 46.6 ± 4.3 | 7.2 ± 5.8 | 12116 ± 2790 | 19.8 ± 4.1 | 0.0 ± 0.0 | 37.9 ± 4.9 (1.4 ± 1.1) | 9.5 ± 3.9 | 0 ± 0 | 0.62 ± 0.08 | 1.26 ± 0.06 |

Paired against THRESHOLD_EDD (same seeds): total cost difference mean [min, max], seeds better / worse

- RUN_TO_FAILURE: +47.1 [+26.5, +68.0], better on 0/8, worse on 8/8
- FIXED_INTERVAL: +30.2 [+5.5, +57.5], better on 0/8, worse on 8/8
- THRESHOLD_EDD: +0.0 [+0.0, +0.0], better on 0/8, worse on 0/8
- RISK_CRITICALITY_FIRST: +8.8 [-31.2, +44.2], better on 2/8, worse on 6/8
- RISK_GREEDY: -33.4 [-62.7, +22.0], better on 7/8, worse on 1/8
- RISK_GREEDY_STABLE: -31.3 [-62.7, +18.6], better on 7/8, worse on 1/8
- RISK_MILP: +13.7 [-23.3, +34.6], better on 2/8, worse on 6/8
- RISK_MILP_STABLE: +13.4 [-19.2, +39.0], better on 2/8, worse on 6/8

## Cost sensitivity (best policy per scenario across 45 cost settings)

```
{
 "adverse": {
  "FIXED_INTERVAL": 0,
  "RISK_CRITICALITY_FIRST": 0,
  "RISK_GREEDY": 35,
  "RISK_GREEDY_STABLE": 1,
  "RUN_TO_FAILURE": 3,
  "THRESHOLD_EDD": 6
 },
 "approval_delay": {
  "FIXED_INTERVAL": 0,
  "RISK_CRITICALITY_FIRST": 8,
  "RISK_GREEDY": 28,
  "RISK_GREEDY_STABLE": 0,
  "RUN_TO_FAILURE": 9,
  "THRESHOLD_EDD": 0
 },
 "base": {
  "FIXED_INTERVAL": 0,
  "RISK_CRITICALITY_FIRST": 3,
  "RISK_GREEDY": 26,
  "RISK_GREEDY_STABLE": 0,
  "RUN_TO_FAILURE": 9,
  "THRESHOLD_EDD": 7
 },
 "degraded_predictions": {
  "FIXED_INTERVAL": 10,
  "RISK_CRITICALITY_FIRST": 6,
  "RISK_GREEDY": 1,
  "RISK_GREEDY_STABLE": 19,
  "RUN_TO_FAILURE": 9,
  "THRESHOLD_EDD": 0
 },
 "parts_shortage": {
  "FIXED_INTERVAL": 0,
  "RISK_CRITICALITY_FIRST": 0,
  "RISK_GREEDY": 0,
  "RISK_GREEDY_STABLE": 31,
  "RUN_TO_FAILURE": 9,
  "THRESHOLD_EDD": 5
 },
 "tight_labour": {
  "FIXED_INTERVAL": 0,
  "RISK_CRITICALITY_FIRST": 0,
  "RISK_GREEDY": 34,
  "RISK_GREEDY_STABLE": 0,
  "RUN_TO_FAILURE": 3,
  "THRESHOLD_EDD": 8
 }
}
```