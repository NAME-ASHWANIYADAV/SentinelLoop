# Local demo check (2026-10-18, SYNTHETIC data, this laptop)

Purpose: the evidence behind the "local demo: GO" decision in `FINAL_PRODUCT_HANDOFF.md`. This is a manual check on demo data and says nothing about real turbines or real users.

## Steps

1. The previous demo folder was moved aside: `artifacts_demo/console` → `artifacts_demo/console_prev_*` (git-ignored).
2. A fresh demo site was built:
   ```bash
   set -a; . artifacts_demo/demo_key.env; set +a; PYTHONPATH=src .venv/Scripts/python.exe product/scripts/demo_site.py artifacts_demo/console
   ```
   Result: 6 synthetic turbines. WT03 URGENT_REVIEW (injected HSS-bearing fault), WT05 DATA_QUALITY_FAILURE (stuck oil-temperature sensor), the others NORMAL_MONITORING. Demo data time: 2026-01-24T23:50Z.
3. The API was started: `product/scripts/run_demo_api.py` (127.0.0.1:8080). The console was started: `streamlit run src/sentinelloop/console/app.py --server.port 8502`. Both ran through `.claude/launch.json`.
4. Checks in the in-app browser, signed in with the demo planner's test key (`demo_credentials.json`, git-ignored):

| check | observed |
|---|---|
| `GET /api/v1/ready` | `schema_version` 7, `schema_current` true, 1 approved model, audit key configured. `decision_config`: "placeholder defaults (downtime cost 0, illustrative due dates): set them with serve --decision-config" |
| Fleet page | Urgent review 1, Data problem 1, Normal monitoring 4. Caption: "'Cannot assess' is never a statement that the asset is healthy" |
| Work queue | P1 "Inspect WT03 (URGENT_REVIEW)": the reason states "a policy threshold, not a failure-time prediction" and no failure probability. P2 instrument check on WT05 gives the reason "stuck_signal:gearbox_oil_temp constant for the last 73 points (longest run in training 4)". Waiting time and due date are shown |
| Approve WO-000001 | "WO-000001 approved", and the order left the pending list |
| Asset page, WT03 | "trained on SYNTHETIC data … Not field-validated". No remaining-life or failure-probability estimate. Deviations are shown in multiples of the inspection threshold (HSS bearing 19.0 ×, oil sump 8.44 ×) |

## Problem seen

At a 652 px-wide viewport, Streamlit's sidebar overlays the page. A click aimed at "Approve" landed on the sidebar's "Sign out", and the session was lost; no order was changed. At 1,400 px the same action worked. This is covered by KNOWN_LIMITATIONS P7 (no mobile layout).

## Not covered here

These are covered by the automated suite instead (`tests/test_console.py`, `tests/test_app_*.py`):
- scheduling, start and complete with an outcome;
- technician and engineer roles;
- CMMS dispatch.

Full suite on 2026-10-18: 335 passed, 1 skipped (the Odoo sandbox test, pending approval).

## Re-check on the final code (2026-10-18, after the re-review fixes and W3; commit f531b72)

The demo site was rebuilt from scratch the same way. The previous folder was moved aside as `artifacts_demo/console_prev_*`. The new site has the same six synthetic turbines: WT03 URGENT_REVIEW, WT05 DATA_QUALITY_FAILURE, the others NORMAL_MONITORING.

| check | observed |
|---|---|
| `GET /api/v1/ready` | `schema_version` 9 (migrations 0008–0009 applied), `schema_current` true, 1 approved model, audit key configured, `decision_config` placeholder defaults |
| Fleet page | Urgent review 1, Data problem 1, Normal monitoring 4 |
| Work queue | Same P1 inspection (WT03) and P2 instrument check (WT05). Times now carry the site's zone ("due 25 Jan 2026 23:50 UTC"; the deferral date is entered "at 06:00 UTC time") |
| Approve WO-000001 | "WO-000001 approved" |
| Asset page, WT03 | Synthetic-data model line, no failure probability. The deviation table is a plain-text data grid (1 `stDataFrame`, 0 markdown tables) and the page shows no exception |

At this commit the full suite gives 602 passed, 1 skipped (Odoo sandbox, pending approval).
