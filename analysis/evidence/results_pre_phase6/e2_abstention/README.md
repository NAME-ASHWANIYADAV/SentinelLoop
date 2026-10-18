# E2 — Abstention / escalation (H2)

Same OOF replay and eval engines as E1. 'Error' = first serious (HIGH/CRITICAL) order is late (< 5 cycles of true life) or never, or too early (> 60 cycles discarded). 'Acted-upon' engines are those whose first serious decision was NOT escalated to a human.

| subset | n_eval | error_rate_all_decisions | error_rate_acted_upon | error_rate_among_escalated | relative_reduction | escalation_share | H2_supported_subset |
|---|---|---|---|---|---|---|---|
| FD001 | 70 | 0.171 | 0.175 | 0.143 | -0.019 | 0.100 | False |
| FD002 | 182 | 0.104 | 0.116 | 0.057 | -0.108 | 0.192 | False |
| FD003 | 70 | 0.071 | 0.071 | 0.071 | 0.000 | 0.200 | False |
| FD004 | 174 | 0.098 | 0.099 | 0.083 | -0.011 | 0.069 | False |

## Verdict
H2: error rate among acted-upon engines is >=20% lower than among all engines with escalation share <=25% on 0/4 subsets. Pre-registered criterion (>=3/4): NOT SUPPORTED.

```json
{
 "FD001": {
  "n_eval": 70,
  "error_rate_all_decisions": 0.17142857142857143,
  "error_rate_acted_upon": 0.1746031746031746,
  "error_rate_among_escalated": 0.14285714285714285,
  "relative_reduction": -0.01851851851851845,
  "escalation_share": 0.1,
  "reasons": {
   "insufficient_evidence": 7
  },
  "H2_supported_subset": false
 },
 "FD002": {
  "n_eval": 182,
  "error_rate_all_decisions": 0.1043956043956044,
  "error_rate_acted_upon": 0.11564625850340136,
  "error_rate_among_escalated": 0.05714285714285714,
  "relative_reduction": -0.10776942355889724,
  "escalation_share": 0.19230769230769232,
  "reasons": {
   "insufficient_evidence": 35
  },
  "H2_supported_subset": false
 },
 "FD003": {
  "n_eval": 70,
  "error_rate_all_decisions": 0.07142857142857142,
  "error_rate_acted_upon": 0.07142857142857142,
  "error_rate_among_escalated": 0.07142857142857142,
  "relative_reduction": 0.0,
  "escalation_share": 0.2,
  "reasons": {
   "insufficient_evidence": 14
  },
  "H2_supported_subset": false
 },
 "FD004": {
  "n_eval": 174,
  "error_rate_all_decisions": 0.09770114942528736,
  "error_rate_acted_upon": 0.09876543209876543,
  "error_rate_among_escalated": 0.08333333333333333,
  "relative_reduction": -0.01089324618736372,
  "escalation_share": 0.06896551724137931,
  "reasons": {
   "insufficient_evidence": 12
  },
  "H2_supported_subset": false
 }
}
```
