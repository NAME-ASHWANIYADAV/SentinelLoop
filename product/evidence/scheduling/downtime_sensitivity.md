# Downtime-price sensitivity (generated; SIMULATED; decisions unchanged, outcomes re-priced)

Cheapest policy by mean re-priced cost (total cost + d x unplanned downtime hours). Cost units as in S1 (failure A = 10).

| scenario | d=0.0 | d=0.0005 | d=0.001 | d=0.002 | d=0.005 | d=0.01 | d=0.02 |
|---|---|---|---|---|---|---|---|
| adverse | RISK_GREEDY | RISK_GREEDY | RISK_GREEDY | RISK_GREEDY | RISK_MILP_STABLE | RISK_MILP_STABLE | RISK_MILP_STABLE |
| approval_delay | RISK_GREEDY | RISK_GREEDY | RISK_GREEDY | RISK_GREEDY | RISK_GREEDY | RISK_GREEDY | RISK_GREEDY |
| base | RISK_GREEDY | RISK_GREEDY | RISK_GREEDY | RISK_GREEDY | RISK_GREEDY | RISK_GREEDY | RISK_GREEDY |
| degraded_predictions | RISK_GREEDY_STABLE | RISK_GREEDY_STABLE | RISK_GREEDY_STABLE | RISK_GREEDY_STABLE | RISK_GREEDY_STABLE | RISK_GREEDY_STABLE | RISK_GREEDY_STABLE |
| parts_shortage | RISK_GREEDY_STABLE | RISK_GREEDY_STABLE | RISK_GREEDY_STABLE | RISK_GREEDY_STABLE | RISK_MILP | RISK_MILP | RISK_MILP |
| tight_labour | RISK_GREEDY | RISK_GREEDY | RISK_GREEDY | RISK_GREEDY | RISK_GREEDY | RISK_MILP | RISK_MILP |

Break-even d at which RISK_MILP_STABLE's paired mean cost falls below RISK_GREEDY's:

- adverse: d > 0.0026 per hour (MILP_STABLE costs +46.8 more but saves 17698 downtime hours on average)
- approval_delay: never (MILP_STABLE does not reduce downtime)
- base: never (MILP_STABLE does not reduce downtime)
- degraded_predictions: never (MILP_STABLE does not reduce downtime)
- parts_shortage: d > 0.0026 per hour (MILP_STABLE costs +37.5 more but saves 14569 downtime hours on average)
- tight_labour: d > 0.0054 per hour (MILP_STABLE costs +17.0 more but saves 3146 downtime hours on average)
