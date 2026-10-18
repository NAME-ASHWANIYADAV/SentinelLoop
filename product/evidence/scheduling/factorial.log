# S1e trigger x scheduler factorial (generated; SIMULATED)

Parameters (S1d base-tuned): {'threshold_h': 100.0, 'decision_horizon_h': 60.0, 'p_inspect': 0.05, 'p_urgent': 0.2}. Seeds 0-7, 120 days.

| scenario | THRESHOLD_EDD | THRESHOLD_CRITICALITY_FIRST | THRESHOLD_MILP | THRESHOLD_GREEDY | RISK_EDD | RISK_GREEDY | RISK_MILP |
|---|---|---|---|---|---|---|---|
| base | 138.2 | 139.2 | 137.7 | 138.2 | 141.0 | 138.3 | 142.0 |
| tight_labour | 165.8 | 170.5 | 163.8 | 339.5 | 187.9 | 153.5 | 180.9 |
| parts_shortage | 158.0 | 220.9 | 200.7 | 208.4 | 164.6 | 162.6 | 206.7 |
| degraded_predictions | 140.3 | 137.1 | 145.6 | 141.8 | 190.0 | 166.6 | 183.7 |
| approval_delay | 148.0 | 149.5 | 153.8 | 148.9 | 163.5 | 148.9 | 162.8 |
| adverse | 175.4 | 258.8 | 224.2 | 255.6 | 188.6 | 172.2 | 213.3 |

Paired effects (mean [min, max] over seeds; n better of 8; negative = cheaper):

- trigger effect (RISK_EDD - THRESHOLD_EDD): base +2.8 [+0.1, +7.5] 0/8; tight_labour +22.2 [-0.4, +51.6] 1/8; parts_shortage +6.6 [-6.8, +18.1] 1/8; degraded_predictions +49.7 [+35.5, +98.3] 0/8; approval_delay +15.5 [+6.1, +25.1] 0/8; adverse +13.2 [-10.9, +32.6] 2/8
- risk scheduler given risk trigger (RISK_GREEDY - RISK_EDD): base -2.7 [-9.1, +2.3] 6/8; tight_labour -34.4 [-54.1, -11.8] 8/8; parts_shortage -2.1 [-17.2, +25.3] 6/8; degraded_predictions -23.4 [-55.3, -5.5] 8/8; approval_delay -14.5 [-25.4, -2.8] 8/8; adverse -16.4 [-34.5, +6.1] 7/8
- MILP scheduler given risk trigger (RISK_MILP - RISK_EDD): base +1.0 [-6.2, +17.3] 4/8; tight_labour -7.1 [-37.4, +11.4] 5/8; parts_shortage +42.0 [+11.0, +81.5] 0/8; degraded_predictions -6.3 [-25.7, +6.2] 5/8; approval_delay -0.6 [-11.3, +8.3] 5/8; adverse +24.7 [-4.5, +42.1] 1/8
- criticality-first scheduler given threshold (THRESHOLD_CRITICALITY_FIRST - THRESHOLD_EDD): base +1.0 [-2.0, +7.5] 1/8; tight_labour +4.8 [-16.0, +26.5] 3/8; parts_shortage +62.9 [+20.0, +117.0] 0/8; degraded_predictions -3.2 [-17.0, +4.0] 5/8; approval_delay +1.5 [-6.5, +18.0] 3/8; adverse +83.3 [+37.5, +145.0] 0/8
- MILP scheduler given threshold (THRESHOLD_MILP - THRESHOLD_EDD): base -0.6 [-5.0, +0.5] 1/8; tight_labour -1.9 [-16.5, +26.0] 6/8; parts_shortage +42.7 [+5.0, +73.5] 0/8; degraded_predictions +5.3 [-1.0, +10.0] 1/8; approval_delay +5.8 [-4.0, +13.5] 1/8; adverse +48.8 [+22.5, +113.0] 0/8
- risk-ranked queue given threshold (THRESHOLD_GREEDY - THRESHOLD_EDD): base -0.1 [-1.0, +0.5] 1/8; tight_labour +173.8 [+123.5, +228.5] 0/8; parts_shortage +50.4 [+27.5, +64.0] 0/8; degraded_predictions +1.4 [-5.5, +7.0] 2/8; approval_delay +0.9 [-12.0, +17.5] 3/8; adverse +80.2 [+54.0, +129.5] 0/8
- THRESHOLD_GREEDY - RISK_GREEDY: base -0.1 [-4.2, +4.9] 5/8; tight_labour +186.0 [+133.8, +231.0] 0/8; parts_shortage +45.9 [+29.8, +60.4] 0/8; degraded_predictions -24.8 [-40.0, -12.6] 8/8; approval_delay -0.1 [-17.7, +15.2] 3/8; adverse +83.4 [+59.8, +125.9] 0/8
