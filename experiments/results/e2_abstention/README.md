# E2 — Abstention / escalation (H2)

Same OOF replay and eval engines as E1. 'Error' = first serious (HIGH/CRITICAL) order is late (< 5 cycles of true life) or never, or too early (> 60 cycles discarded). 'Acted-upon' engines are those whose first serious decision was NOT escalated to a human.

| subset | n_eval | error_rate_all_decisions | error_rate_acted_upon | error_rate_among_escalated | relative_reduction | escalation_share | H2_supported_subset |
|---|---|---|---|---|---|---|---|
| FD001 | 70 | 0.157 | 0.150 | 0.200 | 0.045 | 0.143 | False |
| FD002 | 182 | 0.093 | 0.104 | 0.036 | -0.112 | 0.154 | False |
| FD003 | 70 | 0.071 | 0.078 | 0.000 | -0.094 | 0.086 | False |
| FD004 | 174 | 0.103 | 0.106 | 0.077 | -0.021 | 0.075 | False |

## Verdict
H2: error rate among acted-upon engines is >=20% lower than among all engines with escalation share <=25% on 0/4 subsets. Pre-registered criterion (>=3/4): NOT SUPPORTED.

```json
{
 "FD001": {
  "n_eval": 70,
  "error_rate_all_decisions": 0.15714285714285714,
  "error_rate_acted_upon": 0.15,
  "error_rate_among_escalated": 0.2,
  "relative_reduction": 0.04545454545454547,
  "escalation_share": 0.14285714285714285,
  "reasons": {
   "insufficient_evidence": 10
  },
  "H2_supported_subset": false
 },
 "FD002": {
  "n_eval": 182,
  "error_rate_all_decisions": 0.09340659340659341,
  "error_rate_acted_upon": 0.1038961038961039,
  "error_rate_among_escalated": 0.03571428571428571,
  "relative_reduction": -0.11229946524064177,
  "escalation_share": 0.15384615384615385,
  "reasons": {
   "insufficient_evidence": 28
  },
  "H2_supported_subset": false
 },
 "FD003": {
  "n_eval": 70,
  "error_rate_all_decisions": 0.07142857142857142,
  "error_rate_acted_upon": 0.078125,
  "error_rate_among_escalated": 0.0,
  "relative_reduction": -0.09375000000000006,
  "escalation_share": 0.08571428571428572,
  "reasons": {
   "insufficient_evidence": 6
  },
  "H2_supported_subset": false
 },
 "FD004": {
  "n_eval": 174,
  "error_rate_all_decisions": 0.10344827586206896,
  "error_rate_acted_upon": 0.10559006211180125,
  "error_rate_among_escalated": 0.07692307692307693,
  "relative_reduction": -0.02070393374741207,
  "escalation_share": 0.07471264367816093,
  "reasons": {
   "insufficient_evidence": 13
  },
  "H2_supported_subset": false
 }
}
```
