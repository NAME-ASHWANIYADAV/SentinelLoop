# E6 — Auditability (H6)

H6: 3409 decisions across 4 subset logs re-derived with 0 mismatches; chains valid True; tampering detected in every log True; 205 work orders carry model version and severity: True. SUPPORTED.

```json
{
 "per_log": {
  "decisions_FD001.jsonl": {
   "n": 510,
   "mismatches": 0,
   "chain_valid": true,
   "details": []
  },
  "decisions_FD002.jsonl": {
   "n": 971,
   "mismatches": 0,
   "chain_valid": true,
   "details": []
  },
  "decisions_FD003.jsonl": {
   "n": 897,
   "mismatches": 0,
   "chain_valid": true,
   "details": []
  },
  "decisions_FD004.jsonl": {
   "n": 1031,
   "mismatches": 0,
   "chain_valid": true,
   "details": []
  }
 },
 "tampered": {
  "decisions_FD001.jsonl": {
   "chain_valid_after_tamper": false,
   "rederivation_mismatches_after_tamper": 1
  },
  "decisions_FD002.jsonl": {
   "chain_valid_after_tamper": false,
   "rederivation_mismatches_after_tamper": 1
  },
  "decisions_FD003.jsonl": {
   "chain_valid_after_tamper": false,
   "rederivation_mismatches_after_tamper": 1
  },
  "decisions_FD004.jsonl": {
   "chain_valid_after_tamper": false,
   "rederivation_mismatches_after_tamper": 1
  }
 },
 "n_orders": 205
}
```
