# S2 part C: shipped RUL trigger settings on the S2 evaluation engines (generated; SIMULATED)

RISK_GREEDY at the shipped values {'decision_horizon_h': 60.0, 'p_inspect': 0.1, 'p_urgent': 0.3} vs RISK_GREEDY tuned on FD001 (S2 part B, tuned in base, downtime unpriced). FD003 engines, seeds 0-7, 120 days, 30 assets. Total cost, mean over seeds; paired difference shipped - tuned [min, max].

| scenario | shipped | tuned in base | shipped - tuned | shipped worse on | THRESHOLD_EDD at 60 h (untuned) | THRESHOLD_EDD tuned in base |
|---|---|---|---|---|---|---|
| base | 128.3 | 127.0 | +1.3 [-2.2, +7.2] | 5/8 | 149.7 | 126.0 |
| tight_labour | 157.3 | 156.6 | +0.7 [-17.6, +18.6] | 4/8 | 213.1 | 165.9 |
| parts_tight | 132.8 | 132.0 | +0.8 [-4.9, +9.7] | 4/8 | 163.6 | 129.8 |
| parts_shortage | 173.3 | 173.1 | +0.2 [-37.8, +17.5] | 5/8 | 191.2 | 168.8 |
| degraded_predictions | 175.5 | 155.2 | +20.3 [+0.5, +46.9] | 8/8 | 295.1 | 135.9 |
| approval_delay | 146.9 | 138.5 | +8.4 [-0.6, +28.2] | 7/8 | 295.1 | 139.4 |
| adverse | 198.2 | 196.4 | +1.9 [-31.2, +26.1] | 5/8 | 240.2 | 193.4 |
