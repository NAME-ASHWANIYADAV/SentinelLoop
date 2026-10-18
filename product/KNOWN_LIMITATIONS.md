# Known limitations

Status 2026-10-18. Each limitation states its effect and what would remove it. The adversarial review (`ADVERSARIAL_REVIEW.md`) adds confirmed findings to this list. Severity: **H** blocks a pilot or a claim, **M** must be addressed before operational use, **L** minor.

## 1. Evidence

| # | limitation | effect | removed by | sev |
|---|---|---|---|---|
| E1 | No customer, no interview, no field data. Every model result is SIMULATED (C-MAPSS) or SYNTHETIC (our wind generator) | no claim about real detection, false alarms, value or user acceptance is possible | G1 conversations; rung 4 back-test; rung 5 pilot (`VALIDATION_LADDER.md`) | H |
| E2 | The wind model has not been run on any real turbine data. G0 is pre-registered but blocked on the CARE download | detection performance on real faults unknown | G0 (download approval pending) | H |
| E3 | Synthetic wind evaluation is circular: the generator and the model share our assumptions (36/36 detection is a behaviour check) | synthetic numbers must never be quoted as performance | real data (E2) | H |
| E4 | Scheduling value is SIMULATED on C-MAPSS predictions, with assumed costs, crews and perfect inspection; results reverse with tuning and downtime price | no scheduling benefit can be claimed | replay of a customer's backlog and crew history (rung 4) | M |
| E5 | RUL intervals under-cover in late life (0.81–0.87 in the decision-relevant band) | intervals are not a conditional guarantee near failure | Mondrian recalibration (PLANNED); real data | M |

## 2. Model and decision logic

| # | limitation | effect | removed by | sev |
|---|---|---|---|---|
| M1 | Slow sensor drift is indistinguishable from component heating (no redundant temperature sensors) | false inspections (193–293 alarm-hours per drifting sensor in W1) | cross-turbine comparison and physical-redundancy checks (PLANNED); inspection remains the discriminator | M |
| M2 | Commissioning on a period that already contains a developing fault hides it | missed detection on that turbine | human judgement plus a check of the baseline offsets against the fleet (PLANNED) | M |
| M3 | Curtailment, derating, icing and grid events are not modelled separately; idle periods are out of scope | more out-of-scope time; changed load–temperature relations under derating | per-site operating-state signals (PLANNED) | M |
| M4 | Thresholds are policy choices (1.25 × max healthy score; urgent = 3 × inspect), not calibrated probabilities | the urgent threshold has no validated meaning | calibration on labelled field events | M |
| M5 | Decision engine default due dates (24 h / 168 h / 720 h) and costs are placeholders | due dates are not site-appropriate | site configuration with the customer | M |
| M6 | No re-commissioning prompt after a logged component replacement | stale baselines after maintenance | link outcomes to commissioning (PLANNED) | M |

## 3. Platform and operations

| # | limitation | effect | removed by | sev |
|---|---|---|---|---|
| P1 | One process, one SQLite file; the rate limit is in-process | single-site scale only; no high availability | PostgreSQL port and process supervision if needed (PD-06) | L |
| P2 | List endpoints are unpaginated; `/assets` does one state lookup per asset (p50 288 ms for 50 assets in L1) | slow fleet views at hundreds of assets | pagination and a joined query | L |
| P3 | No readings retention or archiving | disk grows by about 0.17 MB per turbine-day | retention policy | L |
| P4 | No API route to create asset types or sites (library or admin only) | onboarding needs an engineer | admin routes (PLANNED) | L |
| P5 | Assessments and dispatch run by external schedulers (cron); none is built in | operations must set up jobs | built-in scheduler or documented service units | L |
| P6 | Audit-key rotation has no in-place procedure | a key change starts a new database generation | re-anchoring support (PLANNED) | L |
| P7 | The console has no offline mode, no mobile layout, English only, and no in-console feedback form | limited use on site | pilot feedback (`OPERATOR_FEEDBACK_PLAN.md`) | M |

## 4. Integration and security

| # | limitation | effect | removed by | sev |
|---|---|---|---|---|
| S1 | The CMMS connector is tested only against a contract test double; the real Odoo sandbox run is pending (image download approval) | real-Odoo compatibility unproven | run `tests/test_app_odoo_sandbox.py` | H |
| S2 | No customer CMMS integration exists | no claim of compatibility with SAP PM, Maximo, etc. | per-customer adapter and test | M |
| S3 | No external penetration test; no SSO; no signed model manifests | security claims limited to the reviewed code and tests | external test; OIDC; signatures | M |
| S4 | Dependency advisories: mlflow 3.0.1 (development only; excluded from platform installs), pyarrow 20.0.0, pytest 8.4.2 | known vulnerabilities in the development environment | upgrades (download approval pending) | M |
| S5 | Technician data are not pseudonymised in the platform; DPDP duties not verified against the Act | data-protection exposure at a customer | pseudonymisation and legal review | M |
