# E3 — Sensor stress and input quality (H3)

Half of the official test engines are corrupted over their last 20 cycles; the other half stay clean. All signals are change-relative to the clean run of the same engines. Detection = window quality flag OR newly raised sustained anomaly OR newly raised escalation (data_quality / conflicting_evidence / drift). Silent-wrong-order = HIGH/CRITICAL issued without escalation that differs from the clean decision; 'naive' agent ignores quality/drift inputs, 'full' agent uses them.

| subset | fault | n_corrupted | n_clean | detection_rate | false_alarm_rate | detect_by_quality | detect_by_new_anomaly | severity_changed_rate_naive | silent_wrong_order_naive | silent_wrong_order_full | escalation_share_full_corrupted | fleet_drift_alarm_mixed_tail | fleet_drift_alarm_clean_early | fleet_drift_reasons | rmse_shift_point_corrupted | reduction_silent_wrong | H3_detect_ok | H3_fa_ok | H3_swo_ok |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| FD001 | missing20 | 50 | 50 | 1.000 | 0.000 | 1.000 | 0.000 | 0.120 | 0.040 | 0.000 | 1.000 | True | False | severe_single_feature | 6.467 | 1.000 | True | True | True |
| FD001 | noise3s | 50 | 50 | 0.980 | 0.000 | 0.320 | 0.820 | 0.720 | 0.080 | 0.000 | 0.760 | True | False | severe_single_feature | 18.675 | 1.000 | True | True | True |
| FD001 | bias2s | 50 | 50 | 0.120 | 0.000 | 0.000 | 0.120 | 0.080 | 0.040 | 0.000 | 0.380 | True | False | severe_single_feature | 4.083 | 1.000 | False | True | True |
| FD001 | regime_shift | 50 | 50 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | True | False | operating_setting,severe_single_feature | 0.000 | nan | True | True | True |
| FD001 | bias3s | 50 | 50 | 0.200 | 0.000 | 0.000 | 0.200 | 0.140 | 0.040 | 0.000 | 0.360 | True | False | severe_single_feature | 4.524 | 1.000 | False | True | True |
| FD002 | missing20 | 129 | 130 | 1.000 | 0.000 | 1.000 | 0.829 | 0.783 | 0.062 | 0.000 | 1.000 | True | False | severe_single_feature | 39.995 | 1.000 | True | True | True |
| FD002 | noise3s | 129 | 130 | 1.000 | 0.000 | 1.000 | 0.829 | 0.814 | 0.039 | 0.000 | 1.000 | True | False | severe_single_feature | 48.306 | 1.000 | True | True | True |
| FD002 | bias2s | 129 | 130 | 0.884 | 0.000 | 0.519 | 0.814 | 0.605 | 0.023 | 0.000 | 0.829 | True | False | severe_single_feature | 6.338 | 1.000 | False | True | True |
| FD002 | regime_shift | 129 | 130 | 1.000 | 0.000 | 1.000 | 0.829 | 0.814 | 0.194 | 0.000 | 1.000 | True | False | operating_setting,severe_single_feature | 77.514 | 1.000 | True | True | True |
| FD002 | bias3s | 129 | 130 | 0.899 | 0.000 | 0.612 | 0.829 | 0.620 | 0.023 | 0.000 | 0.891 | True | False | severe_single_feature | 6.454 | 1.000 | False | True | True |
| FD003 | missing20 | 50 | 50 | 1.000 | 0.000 | 1.000 | 0.000 | 0.040 | 0.000 | 0.000 | 1.000 | True | True | severe_single_feature | 5.579 | nan | True | True | True |
| FD003 | noise3s | 50 | 50 | 1.000 | 0.000 | 0.460 | 0.900 | 0.860 | 0.160 | 0.000 | 0.660 | True | True | severe_single_feature | 18.086 | 1.000 | True | True | True |
| FD003 | bias2s | 50 | 50 | 0.040 | 0.000 | 0.020 | 0.040 | 0.120 | 0.040 | 0.000 | 0.240 | True | True | severe_single_feature | 3.276 | 1.000 | False | True | True |
| FD003 | regime_shift | 50 | 50 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | True | True | operating_setting,severe_single_feature | 0.000 | nan | True | True | True |
| FD003 | bias3s | 50 | 50 | 0.060 | 0.000 | 0.020 | 0.060 | 0.140 | 0.060 | 0.000 | 0.260 | True | True | severe_single_feature | 3.584 | 1.000 | False | True | True |
| FD004 | missing20 | 124 | 124 | 1.000 | 0.000 | 1.000 | 0.879 | 0.823 | 0.048 | 0.000 | 1.000 | True | False | severe_single_feature | 32.787 | 1.000 | True | True | True |
| FD004 | noise3s | 124 | 124 | 1.000 | 0.000 | 1.000 | 0.879 | 0.823 | 0.016 | 0.000 | 1.000 | True | False | severe_single_feature | 48.740 | 1.000 | True | True | True |
| FD004 | bias2s | 124 | 124 | 0.960 | 0.000 | 0.427 | 0.879 | 0.637 | 0.065 | 0.000 | 0.653 | True | False | feature_share | 8.331 | 1.000 | True | True | True |
| FD004 | regime_shift | 124 | 124 | 1.000 | 0.000 | 1.000 | 0.879 | 0.855 | 0.113 | 0.000 | 1.000 | True | False | operating_setting,severe_single_feature | 64.051 | 1.000 | True | True | True |
| FD004 | bias3s | 124 | 124 | 0.960 | 0.000 | 0.556 | 0.879 | 0.645 | 0.073 | 0.000 | 0.742 | True | False | feature_share | 8.367 | 1.000 | True | True | True |

## Verdict
H3 pre-registered faults fully passing (detect>=0.90, false-alarm<=0.05, silent-wrong-order reduced>=50%): 3/4. Per fault: bias2s: detect FAIL, false-alarm ok, silent-wrong-order ok; bias3s: detect FAIL, false-alarm ok, silent-wrong-order ok; missing20: detect ok, false-alarm ok, silent-wrong-order ok; noise3s: detect ok, false-alarm ok, silent-wrong-order ok; regime_shift: detect ok, false-alarm ok, silent-wrong-order ok. bias3s is a secondary row (added after the fast diagnostic). Fleet-level drift alarms are reported separately.

Escalation reasons on corrupted engines (full agent):
```json
{
 "FD001": {
  "missing20": {
   "escalation_reasons_full": {
    "data_quality": 50,
    "drift_active": 15,
    "insufficient_evidence": 10
   }
  },
  "noise3s": {
   "escalation_reasons_full": {
    "insufficient_evidence": 24,
    "drift_active": 20,
    "data_quality": 16
   }
  },
  "bias2s": {
   "escalation_reasons_full": {
    "drift_active": 16,
    "insufficient_evidence": 7
   }
  },
  "regime_shift": {
   "escalation_reasons_full": {
    "data_quality": 50,
    "drift_active": 17,
    "insufficient_evidence": 7
   }
  },
  "bias3s": {
   "escalation_reasons_full": {
    "drift_active": 15,
    "insufficient_evidence": 7
   }
  }
 },
 "FD002": {
  "missing20": {
   "escalation_reasons_full": {
    "data_quality": 129,
    "insufficient_evidence": 84,
    "drift_active": 61
   }
  },
  "noise3s": {
   "escalation_reasons_full": {
    "data_quality": 129,
    "insufficient_evidence": 108,
    "drift_active": 73
   }
  },
  "bias2s": {
   "escalation_reasons_full": {
    "data_quality": 67,
    "drift_active": 39,
    "insufficient_evidence": 18,
    "conflicting_evidence": 12
   }
  },
  "regime_shift": {
   "escalation_reasons_full": {
    "data_quality": 129,
    "drift_active": 122,
    "insufficient_evidence": 91
   }
  },
  "bias3s": {
   "escalation_reasons_full": {
    "data_quality": 79,
    "drift_active": 39,
    "insufficient_evidence": 18,
    "conflicting_evidence": 13
   }
  }
 },
 "FD003": {
  "missing20": {
   "escalation_reasons_full": {
    "data_quality": 50,
    "drift_active": 8,
    "insufficient_evidence": 3
   }
  },
  "noise3s": {
   "escalation_reasons_full": {
    "data_quality": 23,
    "drift_active": 19,
    "insufficient_evidence": 10,
    "conflicting_evidence": 1
   }
  },
  "bias2s": {
   "escalation_reasons_full": {
    "drift_active": 10,
    "insufficient_evidence": 4,
    "conflicting_evidence": 1,
    "data_quality": 1
   }
  },
  "regime_shift": {
   "escalation_reasons_full": {
    "data_quality": 50,
    "drift_active": 8,
    "insufficient_evidence": 3
   }
  },
  "bias3s": {
   "escalation_reasons_full": {
    "drift_active": 11,
    "insufficient_evidence": 4,
    "conflicting_evidence": 1,
    "data_quality": 1
   }
  }
 },
 "FD004": {
  "missing20": {
   "escalation_reasons_full": {
    "data_quality": 124,
    "insufficient_evidence": 82,
    "drift_active": 62
   }
  },
  "noise3s": {
   "escalation_reasons_full": {
    "data_quality": 124,
    "insufficient_evidence": 92,
    "drift_active": 61
   }
  },
  "bias2s": {
   "escalation_reasons_full": {
    "data_quality": 53,
    "drift_active": 41,
    "insufficient_evidence": 15,
    "conflicting_evidence": 9
   }
  },
  "regime_shift": {
   "escalation_reasons_full": {
    "data_quality": 124,
    "drift_active": 111,
    "insufficient_evidence": 101
   }
  },
  "bias3s": {
   "escalation_reasons_full": {
    "data_quality": 69,
    "drift_active": 41,
    "insufficient_evidence": 15,
    "conflicting_evidence": 9
   }
  }
 }
}
```
