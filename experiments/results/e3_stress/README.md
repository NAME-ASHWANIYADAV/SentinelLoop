# E3 — Sensor stress and input quality (H3)

Half of the official test engines are corrupted over their last 20 cycles; the other half stay clean. All signals are change-relative to the clean run of the same engines. Detection = window quality flag OR newly raised sustained anomaly OR newly raised escalation (data_quality / conflicting_evidence / drift). Silent-wrong-order = HIGH/CRITICAL issued without escalation that differs from the clean decision; 'naive' agent ignores quality/drift inputs, 'full' agent uses them.

| subset | fault | n_corrupted | n_clean | detection_rate | false_alarm_rate | detect_by_quality | detect_by_new_anomaly | severity_changed_rate_naive | silent_wrong_order_naive | silent_wrong_order_full | escalation_share_full_corrupted | escalation_share_full_clean | escalation_share_base_clean | silent_wrong_order_full_no_fleet_rule | fleet_drift_alarm_mixed_tail | fleet_drift_alarm_clean_early | fleet_drift_reasons | rmse_shift_point_corrupted | reduction_silent_wrong | H3_detect_ok | H3_fa_ok | H3_swo_ok |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| FD001 | missing20 | 50 | 50 | 1.000 | 0.000 | 1.000 | 0.000 | 0.080 | 0.040 | 0.000 | 1.000 | 0.360 | 0.160 | 0.000 | True | False | severe_single_feature | 6.498 | 1.000 | True | True | True |
| FD001 | noise3s | 50 | 50 | 0.980 | 0.000 | 0.320 | 0.820 | 0.780 | 0.100 | 0.000 | 0.760 | 0.360 | 0.160 | 0.060 | True | False | severe_single_feature | 19.577 | 1.000 | True | True | True |
| FD001 | bias2s | 50 | 50 | 0.120 | 0.000 | 0.000 | 0.120 | 0.080 | 0.040 | 0.000 | 0.400 | 0.360 | 0.160 | 0.040 | True | False | severe_single_feature | 4.229 | 1.000 | False | True | True |
| FD001 | regime_shift | 50 | 50 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.360 | 0.160 | 0.000 | True | False | operating_setting,severe_single_feature | 0.000 | nan | True | True | True |
| FD001 | bias3s | 50 | 50 | 0.200 | 0.000 | 0.000 | 0.200 | 0.140 | 0.060 | 0.000 | 0.440 | 0.360 | 0.160 | 0.060 | True | False | severe_single_feature | 4.584 | 1.000 | False | True | True |
| FD002 | missing20 | 129 | 130 | 1.000 | 0.000 | 1.000 | 0.829 | 0.783 | 0.031 | 0.000 | 1.000 | 0.246 | 0.177 | 0.000 | True | False | severe_single_feature | 38.669 | 1.000 | True | True | True |
| FD002 | noise3s | 129 | 130 | 1.000 | 0.000 | 1.000 | 0.829 | 0.822 | 0.047 | 0.000 | 1.000 | 0.246 | 0.177 | 0.000 | True | False | severe_single_feature | 47.315 | 1.000 | True | True | True |
| FD002 | bias2s | 129 | 130 | 0.884 | 0.000 | 0.519 | 0.814 | 0.612 | 0.031 | 0.000 | 0.752 | 0.246 | 0.177 | 0.031 | True | False | severe_single_feature | 6.663 | 1.000 | False | True | True |
| FD002 | regime_shift | 129 | 130 | 1.000 | 0.000 | 1.000 | 0.829 | 0.829 | 0.000 | 0.000 | 1.000 | 0.246 | 0.177 | 0.000 | True | False | operating_setting,severe_single_feature | 77.866 | nan | True | True | True |
| FD002 | bias3s | 129 | 130 | 0.899 | 0.000 | 0.612 | 0.829 | 0.628 | 0.031 | 0.000 | 0.822 | 0.246 | 0.177 | 0.016 | True | False | severe_single_feature | 6.765 | 1.000 | False | True | True |
| FD003 | missing20 | 50 | 50 | 1.000 | 0.000 | 1.000 | 0.000 | 0.040 | 0.000 | 0.000 | 1.000 | 0.280 | 0.160 | 0.000 | True | True | feature_share | 6.103 | nan | True | True | True |
| FD003 | noise3s | 50 | 50 | 1.000 | 0.000 | 0.460 | 0.900 | 0.840 | 0.200 | 0.000 | 0.660 | 0.280 | 0.160 | 0.120 | True | True | severe_single_feature | 18.404 | 1.000 | True | True | True |
| FD003 | bias2s | 50 | 50 | 0.040 | 0.000 | 0.020 | 0.040 | 0.140 | 0.100 | 0.000 | 0.320 | 0.280 | 0.160 | 0.100 | True | True | feature_share | 3.019 | 1.000 | False | True | True |
| FD003 | regime_shift | 50 | 50 | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 | 0.280 | 0.160 | 0.000 | True | True | operating_setting | 0.000 | nan | True | True | True |
| FD003 | bias3s | 50 | 50 | 0.060 | 0.000 | 0.020 | 0.060 | 0.140 | 0.100 | 0.000 | 0.320 | 0.280 | 0.160 | 0.100 | True | True | feature_share | 3.463 | 1.000 | False | True | True |
| FD004 | missing20 | 124 | 124 | 1.000 | 0.000 | 1.000 | 0.879 | 0.806 | 0.032 | 0.000 | 1.000 | 0.250 | 0.065 | 0.000 | True | False | severe_single_feature | 32.021 | 1.000 | True | True | True |
| FD004 | noise3s | 124 | 124 | 1.000 | 0.000 | 1.000 | 0.879 | 0.806 | 0.008 | 0.000 | 1.000 | 0.250 | 0.065 | 0.000 | True | False | severe_single_feature | 48.760 | 1.000 | True | True | True |
| FD004 | bias2s | 124 | 124 | 0.960 | 0.000 | 0.427 | 0.879 | 0.629 | 0.040 | 0.000 | 0.661 | 0.250 | 0.065 | 0.032 | True | False | feature_share | 8.561 | 1.000 | True | True | True |
| FD004 | regime_shift | 124 | 124 | 1.000 | 0.000 | 1.000 | 0.879 | 0.855 | 0.081 | 0.000 | 1.000 | 0.250 | 0.065 | 0.000 | True | False | operating_setting,severe_single_feature | 64.858 | 1.000 | True | True | True |
| FD004 | bias3s | 124 | 124 | 0.960 | 0.000 | 0.556 | 0.879 | 0.637 | 0.048 | 0.000 | 0.750 | 0.250 | 0.065 | 0.040 | True | False | feature_share | 8.581 | 1.000 | True | True | True |

## Verdict
H3 pre-registered faults fully passing (detect>=0.90, false-alarm<=0.05, silent-wrong-order reduced>=50%): 3/4. Per fault: bias2s: detect FAIL, false-alarm ok, silent-wrong-order ok; bias3s: detect FAIL, false-alarm ok, silent-wrong-order ok; missing20: detect ok, false-alarm ok, silent-wrong-order ok; noise3s: detect ok, false-alarm ok, silent-wrong-order ok; regime_shift: detect ok, false-alarm ok, silent-wrong-order ok. bias3s is a secondary row (added after the fast diagnostic). Fleet-level drift alarms are reported separately.

Escalation reasons on corrupted engines (full agent):
```json
{
 "FD001": {
  "missing20": {
   "escalation_reasons_full": {
    "data_quality": 50,
    "drift_active": 14,
    "insufficient_evidence": 10
   }
  },
  "noise3s": {
   "escalation_reasons_full": {
    "insufficient_evidence": 25,
    "drift_active": 21,
    "data_quality": 16
   }
  },
  "bias2s": {
   "escalation_reasons_full": {
    "drift_active": 16,
    "insufficient_evidence": 8
   }
  },
  "regime_shift": {
   "escalation_reasons_full": {
    "data_quality": 50,
    "drift_active": 15,
    "insufficient_evidence": 8
   }
  },
  "bias3s": {
   "escalation_reasons_full": {
    "drift_active": 17,
    "insufficient_evidence": 10
   }
  }
 },
 "FD002": {
  "missing20": {
   "escalation_reasons_full": {
    "data_quality": 129,
    "drift_active": 58,
    "insufficient_evidence": 55
   }
  },
  "noise3s": {
   "escalation_reasons_full": {
    "data_quality": 129,
    "drift_active": 70,
    "insufficient_evidence": 65
   }
  },
  "bias2s": {
   "escalation_reasons_full": {
    "data_quality": 67,
    "drift_active": 39,
    "insufficient_evidence": 29,
    "conflicting_evidence": 12
   }
  },
  "regime_shift": {
   "escalation_reasons_full": {
    "data_quality": 129,
    "insufficient_evidence": 120,
    "drift_active": 118
   }
  },
  "bias3s": {
   "escalation_reasons_full": {
    "data_quality": 79,
    "drift_active": 39,
    "insufficient_evidence": 28,
    "conflicting_evidence": 13
   }
  }
 },
 "FD003": {
  "missing20": {
   "escalation_reasons_full": {
    "data_quality": 50,
    "drift_active": 8,
    "insufficient_evidence": 2
   }
  },
  "noise3s": {
   "escalation_reasons_full": {
    "data_quality": 23,
    "drift_active": 19,
    "insufficient_evidence": 5,
    "conflicting_evidence": 1
   }
  },
  "bias2s": {
   "escalation_reasons_full": {
    "drift_active": 14,
    "insufficient_evidence": 3,
    "conflicting_evidence": 1,
    "data_quality": 1
   }
  },
  "regime_shift": {
   "escalation_reasons_full": {
    "data_quality": 50,
    "drift_active": 9,
    "insufficient_evidence": 2
   }
  },
  "bias3s": {
   "escalation_reasons_full": {
    "drift_active": 14,
    "insufficient_evidence": 3,
    "conflicting_evidence": 1,
    "data_quality": 1
   }
  }
 },
 "FD004": {
  "missing20": {
   "escalation_reasons_full": {
    "data_quality": 124,
    "insufficient_evidence": 79,
    "drift_active": 56
   }
  },
  "noise3s": {
   "escalation_reasons_full": {
    "data_quality": 124,
    "insufficient_evidence": 92,
    "drift_active": 62
   }
  },
  "bias2s": {
   "escalation_reasons_full": {
    "data_quality": 53,
    "drift_active": 42,
    "insufficient_evidence": 17,
    "conflicting_evidence": 9
   }
  },
  "regime_shift": {
   "escalation_reasons_full": {
    "data_quality": 124,
    "drift_active": 106,
    "insufficient_evidence": 101
   }
  },
  "bias3s": {
   "escalation_reasons_full": {
    "data_quality": 69,
    "drift_active": 42,
    "insufficient_evidence": 17,
    "conflicting_evidence": 9
   }
  }
 }
}
```
