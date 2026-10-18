# S1b MILP assignment check (generated; SIMULATED; seeds 0-3, 120 days)

Sums over seeds. `plans` = rolling-horizon planning calls; `milp_dropped_in_assignment` = jobs the aggregated MILP placed that no specific technician crew could take; `unscheduled_job_days` = job x planning-call pairs left unscheduled for any reason.

| policy | scenario | plans | non-optimal | dropped in assignment | unscheduled job-days |
|---|---|---|---|---|---|
| RISK_MILP | adverse | 480 | 0 | 0 | 7328 |
| RISK_MILP | approval_delay | 480 | 0 | 2 | 5 |
| RISK_MILP | base | 480 | 0 | 0 | 2 |
| RISK_MILP | degraded_predictions | 480 | 0 | 1 | 39 |
| RISK_MILP | parts_shortage | 480 | 0 | 0 | 9076 |
| RISK_MILP | tight_labour | 480 | 0 | 0 | 775 |
| RISK_MILP_STABLE | adverse | 480 | 0 | 0 | 7329 |
| RISK_MILP_STABLE | approval_delay | 480 | 0 | 0 | 34 |
| RISK_MILP_STABLE | base | 480 | 0 | 0 | 12 |
| RISK_MILP_STABLE | degraded_predictions | 480 | 0 | 0 | 35 |
| RISK_MILP_STABLE | parts_shortage | 480 | 0 | 0 | 9077 |
| RISK_MILP_STABLE | tight_labour | 480 | 0 | 0 | 929 |
