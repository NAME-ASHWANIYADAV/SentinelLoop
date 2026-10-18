# S1d robust tuning (generated; SIMULATED)

Grids: threshold_h 60-300 h; interval 80-130 cycles; risk decision horizon {60,100,150} h x (p_inspect, p_urgent) {(0.01,0.05),(0.03,0.15),(0.05,0.2),(0.1,0.3)}. Tuned on seeds 100-107 by mean total cost; evaluated on seeds 0-7.

Settings at a grid edge (the optimum may lie outside the grid): parts_shortage/THRESHOLD_EDD -> {'threshold_h': 300.0}; adverse/THRESHOLD_EDD -> {'threshold_h': 300.0}; base/FIXED_INTERVAL -> {'interval_age_cycles': 130}; degraded_predictions/FIXED_INTERVAL -> {'interval_age_cycles': 130}; approval_delay/FIXED_INTERVAL -> {'interval_age_cycles': 130}; adverse/FIXED_INTERVAL -> {'interval_age_cycles': 80}; tight_labour/FIXED_INTERVAL -> {'interval_age_cycles': 80}

## tuned_in_base

| scenario | THRESHOLD_EDD | FIXED_INTERVAL | RISK_GREEDY | RISK_GREEDY_STABLE | best |
|---|---|---|---|---|---|
| base | 138.2 ± 4.9 | 210.9 ± 7.8 | 138.3 ± 3.6 | 138.8 ± 4.1 | THRESHOLD_EDD |
| tight_labour | 165.8 ± 14.5 | 312.1 ± 45.4 | 153.5 ± 12.1 | 154.3 ± 12.9 | RISK_GREEDY |
| parts_shortage | 158.0 ± 21.8 | 201.4 ± 34.2 | 162.6 ± 21.6 | 163.5 ± 23.1 | THRESHOLD_EDD |
| degraded_predictions | 140.3 ± 6.2 | 210.9 ± 7.8 | 166.6 ± 11.1 | 168.9 ± 12.6 | THRESHOLD_EDD |
| approval_delay | 148.0 ± 11.8 | 212.7 ± 9.9 | 148.9 ± 9.8 | 155.8 ± 5.5 | THRESHOLD_EDD |
| adverse | 175.4 ± 20.1 | 240.9 ± 30.7 | 172.2 ± 20.3 | 171.7 ± 20.3 | RISK_GREEDY_STABLE |

Paired RISK_GREEDY minus THRESHOLD_EDD (eval seeds): mean [min, max], risk better / worse

- base: +0.0 [-5.9, +4.7], 3/8 better, 5/8 worse
- tight_labour: -12.3 [-25.3, -2.5], 8/8 better, 0/8 worse
- parts_shortage: +4.5 [-3.6, +26.2], 3/8 better, 5/8 worse
- degraded_predictions: +26.3 [+16.1, +43.0], 0/8 better, 8/8 worse
- approval_delay: +1.0 [-17.5, +18.2], 4/8 better, 4/8 worse
- adverse: -3.2 [-13.4, +7.5], 5/8 better, 3/8 worse

## tuned_in_scenario

| scenario | THRESHOLD_EDD | FIXED_INTERVAL | RISK_GREEDY | RISK_GREEDY_STABLE | best |
|---|---|---|---|---|---|
| base | 138.2 ± 4.9 | 210.9 ± 7.8 | 138.3 ± 3.6 | 138.8 ± 4.1 | THRESHOLD_EDD |
| tight_labour | 151.0 ± 7.7 | 264.6 ± 26.6 | 145.4 ± 5.5 | 146.1 ± 6.7 | RISK_GREEDY |
| parts_shortage | 131.8 ± 17.7 | 197.3 ± 33.4 | 146.5 ± 17.4 | 147.4 ± 15.4 | THRESHOLD_EDD |
| degraded_predictions | 138.2 ± 4.9 | 210.9 ± 7.8 | 150.0 ± 2.6 | 149.7 ± 2.6 | THRESHOLD_EDD |
| approval_delay | 141.0 ± 4.3 | 212.7 ± 9.9 | 141.5 ± 2.7 | 141.2 ± 3.0 | THRESHOLD_EDD |
| adverse | 129.1 ± 16.1 | 234.4 ± 34.5 | 139.7 ± 12.5 | 139.7 ± 15.3 | THRESHOLD_EDD |

Paired RISK_GREEDY minus THRESHOLD_EDD (eval seeds): mean [min, max], risk better / worse

- base: +0.0 [-5.9, +4.7], 3/8 better, 5/8 worse
- tight_labour: -5.6 [-11.9, +5.7], 6/8 better, 2/8 worse
- parts_shortage: +14.7 [+2.7, +29.7], 0/8 better, 8/8 worse
- degraded_predictions: +11.8 [+5.0, +15.8], 0/8 better, 8/8 worse
- approval_delay: +0.5 [-5.9, +3.9], 2/8 better, 6/8 worse
- adverse: +10.6 [+0.0, +21.1], 0/8 better, 7/8 worse

## Tuned settings

- adverse / FIXED_INTERVAL: {'interval_age_cycles': 80}
- adverse / RISK_GREEDY: {'decision_horizon_h': 150.0, 'p_inspect': 0.05, 'p_urgent': 0.2}
- adverse / RISK_GREEDY_STABLE: {'decision_horizon_h': 150.0, 'p_inspect': 0.05, 'p_urgent': 0.2}
- adverse / THRESHOLD_EDD: {'threshold_h': 300.0}
- approval_delay / FIXED_INTERVAL: {'interval_age_cycles': 130}
- approval_delay / RISK_GREEDY: {'decision_horizon_h': 100.0, 'p_inspect': 0.1, 'p_urgent': 0.3}
- approval_delay / RISK_GREEDY_STABLE: {'decision_horizon_h': 100.0, 'p_inspect': 0.1, 'p_urgent': 0.3}
- approval_delay / THRESHOLD_EDD: {'threshold_h': 130.0}
- base / FIXED_INTERVAL: {'interval_age_cycles': 130}
- base / RISK_GREEDY: {'decision_horizon_h': 60.0, 'p_inspect': 0.05, 'p_urgent': 0.2}
- base / RISK_GREEDY_STABLE: {'decision_horizon_h': 60.0, 'p_inspect': 0.05, 'p_urgent': 0.2}
- base / THRESHOLD_EDD: {'threshold_h': 100.0}
- degraded_predictions / FIXED_INTERVAL: {'interval_age_cycles': 130}
- degraded_predictions / RISK_GREEDY: {'decision_horizon_h': 100.0, 'p_inspect': 0.1, 'p_urgent': 0.3}
- degraded_predictions / RISK_GREEDY_STABLE: {'decision_horizon_h': 100.0, 'p_inspect': 0.1, 'p_urgent': 0.3}
- degraded_predictions / THRESHOLD_EDD: {'threshold_h': 130.0}
- parts_shortage / FIXED_INTERVAL: {'interval_age_cycles': 100}
- parts_shortage / RISK_GREEDY: {'decision_horizon_h': 150.0, 'p_inspect': 0.01, 'p_urgent': 0.05}
- parts_shortage / RISK_GREEDY_STABLE: {'decision_horizon_h': 150.0, 'p_inspect': 0.01, 'p_urgent': 0.05}
- parts_shortage / THRESHOLD_EDD: {'threshold_h': 300.0}
- tight_labour / FIXED_INTERVAL: {'interval_age_cycles': 80}
- tight_labour / RISK_GREEDY: {'decision_horizon_h': 100.0, 'p_inspect': 0.05, 'p_urgent': 0.2}
- tight_labour / RISK_GREEDY_STABLE: {'decision_horizon_h': 100.0, 'p_inspect': 0.05, 'p_urgent': 0.2}
- tight_labour / THRESHOLD_EDD: {'threshold_h': 200.0}
