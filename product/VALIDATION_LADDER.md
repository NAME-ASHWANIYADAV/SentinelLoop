# Validation ladder

How SentinelLoop evidence is graded, and where each capability stands on 2026-10-18. Rungs build on each other: evidence on one rung says nothing about the rungs above it.

**No capability has reached rung 4, 5 or 6.** Any document, slide or conversation that implies otherwise is wrong and must be corrected.

| Rung | Name | Data | What it can show | What it cannot show |
|---|---|---|---|---|
| 1 | Simulated benchmark | NASA C-MAPSS (simulated turbofans) | the method works end to end; calibration and decision logic behave as designed on a known simulator | anything about real equipment, real sensors or real failure modes |
| 2 | Synthetic behaviour | our own generators (`synthetic_wind.py`), injected faults | the software reacts correctly to known situations: faults flagged, bad data refused, out-of-scope conditions declared | detection performance on real data; the generator encodes our own assumptions |
| 3 | Public real field | CARE to Compare, Kelmarsh, Penmanshiel, Hill of Towie (real turbines, public) | whether the model detects real recorded faults and how often it false-alarms on real healthy turbines, under a pre-registered protocol | performance at a customer's site, on their turbines, with their data quality and their maintenance practice |
| 4 | Customer historical back-test | a customer's own SCADA and work-order history, offline | whether the alarms would have preceded that customer's recorded failures, and at what false-alarm cost | how people respond to the alarms; live data problems; business value |
| 5 | Shadow pilot | live customer data, read-only; recommendations recorded, never executed | live data quality, latency, alarm burden, operator agreement with recommendations | outcomes of acting on the recommendations |
| 6 | Operational use | live, with recommendations acted on under the customer's procedures and controls | measured outcomes (failures avoided, downtime, cost) against a pre-agreed baseline | — (the top rung; still site-specific) |

## Status by capability

| Capability | Highest rung reached | Evidence | Next rung needs |
|---|---|---|---|
| RUL with 90% interval (turbofan) | 1 | `docs/NUMBERS.md`, `artifacts/<subset>/metrics.json` | real run-to-failure data in the same asset class (none public for turbofans with a usable licence) |
| Wind drivetrain anomaly detection | 2 | `tests/test_app_wind.py`; `product/evidence/wind_synthetic/w1.md` (36/36 synthetic faults detected, median lead 8–12 days; 17 alarm-hours on 820 healthy turbine-days) | rung 3: G0 on CARE to Compare (pre-registered `product/evidence/g0/PREREGISTRATION.md`); **blocked on download approval** |
| Data-quality gating (missing, stale, stuck, conflicting, implausible) | 2 | `tests/test_app_ingest.py`, `tests/test_app_health.py`, `tests/test_app_wind.py`; competition E3 stress tests (INJECTED on C-MAPSS) | rung 3: run the same gates over real SCADA exports with their real gaps |
| Scope declaration (out of envelope, idle, unknown regime, no baseline) | 2 | same tests | rung 3 |
| Decision engine and work-order workflow | 2 (behaviour) | `tests/test_app_decision.py`, `tests/test_app_workorders.py` | rung 5: operators using it in shadow mode |
| Scheduling under constraints | 1 (value), 2 (feasibility) | `product/SCHEDULING_EVALUATION.md` (simulator on C-MAPSS predictions) | rung 4: replay a customer's backlog, crews and parts history |
| CMMS integration | 0 (not yet built) | — | Phase 6: sandbox (Odoo Community), then a customer CMMS in read-only shadow mode |
| Business value (downtime, cost) | 0 | none | rung 6 only; nothing below rung 6 can establish it |

## Rules

1. Every result names its rung and its data class: SIMULATED, SYNTHETIC, PUBLIC REAL FIELD, CUSTOMER REAL FIELD.
2. A rung-3 result is reported per farm and per asset class. A cross-asset result (for example offshore farms when the target is onshore) is labelled cross-asset.
3. Rung 3 and above need a pre-registration committed before the data are seen, with a pass/fail rule.
4. Rung 4 and above need a written data-sharing agreement and the customer's sign-off on the protocol.
5. Rung 5 and above need the customer's safety and change-management approval. Shadow mode is read-only: nothing is written to the customer's CMMS except, if explicitly enabled, draft requests flagged as SentinelLoop shadow output.
6. Rung 6 needs a pre-agreed baseline and a measurement plan (`PILOT_ACCEPTANCE_CRITERIA.md`), and an explicit authorisation for each kind of action the system may trigger. The system never triggers a physical maintenance action by itself (principle 8).
