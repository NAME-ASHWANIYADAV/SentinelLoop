# Known limitations

Status 2026-10-18, after the Phase 9 adversarial review (`ADVERSARIAL_REVIEW.md`) and its remediation. Each row gives the limitation, its effect and what would remove it.

Severity:
- **H** blocks a pilot or a claim;
- **M** must be addressed before operational use;
- **L** is minor.

Review finding IDs (for example `om_manager-4`) refer to `ADVERSARIAL_REVIEW.md`.

## 1. Evidence

| # | limitation | effect | removed by | sev |
|---|---|---|---|---|
| E1 | No customer, no interview and no field data. Every model result is SIMULATED (C-MAPSS) or SYNTHETIC (our wind generator) | No claim is possible about real detection, false alarms, value or user acceptance | G1 conversations; rung-4 back-test; rung-5 pilot (`VALIDATION_LADDER.md`) | H |
| E2 | The wind model has not been run on any real turbine data. G0 is pre-registered and amended before download (`product/evidence/g0/PREREGISTRATION.md` §10), but it is blocked on download approval | Detection performance on real faults is unknown | G0 (the user's download approval is pending) | H |
| E3 | Synthetic wind evaluation is circular: the generator and the model share our assumptions. 36/36 detected is a behaviour check, not performance | Synthetic numbers must never be quoted as performance | Real data (E2) | H |
| E4 | Scheduling results are SIMULATED, on C-MAPSS predictions, with assumed costs and crews and perfect inspection. The rankings change with tuning, with the price of downtime and with the scenario (S2, `SCHEDULING_EVALUATION.md`). The two scarcity scenarios are fleet collapse and are not ranked | No scheduling benefit can be claimed | Replay of a customer's backlog and crew history (rung 4) | M |
| E5 | RUL intervals under-cover in late life: 0.81–0.87 in the decision-relevant band (C1) | The intervals are not a conditional guarantee near failure | Recalibration by predicted band (PLANNED); real data | M |
| E6 | The RUL model's P(failure before the job ends) is **not calibrated** (C2, SIMULATED): shown about 0.55 when about 0.92 was observed, and the 5% due-date rule is violated 9–18% of the time in late life. It is labelled "model-implied, not calibrated" wherever the platform shows it: assessment and decision reasons, the console and the CMMS description (`tests/test_app_handoff_fixes.py`) | Due dates derived from it are later than their stated risk | Recalibration in the bundle, with a held-out calibration set (PD-19) | M |
| E7 | The wind alarm setting was chosen on synthetic data only (W3, PD-15). On fresh synthetic fleets it gives 0.44 healthy alarm episodes per turbine-year (1 in 2.27 turbine-years; 95% interval up to about 2.45, which does not exclude the proposed pilot ceiling of 2). With the same fixed gating, shorter persistence gave 5.74 (sustain 6) and 2.65 (sustain 12) on the W2 held-out fleets 20–25, so the rate is sensitive to persistence. Counted the way the pilot's alarm-burden criterion counts (`PILOT_ACCEPTANCE_CRITERIA.md` B3, drifting-sensor turbines included), the fresh fleets give about 13 episodes per turbine-year (1 + 39 in about 3.0 turbine-years), far above the proposed ceiling of 2 (`PILOT_PROTOCOL.md` §7) | The real false-inspection rate is unknown, and could exceed what a site accepts | G0 reports the real rate on normal datasets; per-site threshold review at commissioning | M |
| E8 | Synthetic exposure (turbine-years) is derived from the number of evaluations, which assumes gap-free 10-minute data (`wind-eval-migrations-07`) | Rates per turbine-year are approximate where data have gaps | Exposure from timestamps (G0 computes it from the data) | L |

## 2. Model and decision logic

| # | limitation | effect | removed by | sev |
|---|---|---|---|---|
| M1 | Slow drift of a single temperature sensor cannot be told apart from component heating (no redundant sensors) | False inspections: 39 drifting-sensor alarm episodes on the fresh W3 fleets at the shipped setting | Cross-turbine comparison and physical-redundancy checks (PLANNED); inspection remains the discriminator | M |
| M2 | Commissioning on a period that already contains a developing fault hides that fault | Missed detection on that turbine | Human judgement, plus a check of the baseline offsets against the fleet (PLANNED) | M |
| M3 | Turbine status codes, alarm codes, curtailment and derating setpoints are not in the data contract (`om_manager-3`). Icing and grid events are not modelled. Idle periods are out of scope | More out-of-scope time; load–temperature relations change under derating; the pilot cannot use OEM status data | Operating-state signals per site (PLANNED) | M |
| M4 | Thresholds are policy choices tuned on synthetic data: margin 1.25 × max healthy score, sustain 18 operating points (W3, PD-15), urgent = 3 × inspect. They are not calibrated probabilities | The urgent threshold has no validated meaning | Calibration on labelled field events | M |
| M5 | Decision parameters (due dates, downtime cost, suppression periods) can be set per site (PD-24), but the shipped values are placeholders. `/ready` says so | Due dates and rankings are not site-appropriate until set | Site configuration agreed with the customer | M |
| M6 | No re-commissioning prompt after a logged component replacement. No bulk re-commissioning after a model change (`om_manager-2`) | Stale baselines after maintenance; a model change leaves turbines out of scope until each is re-commissioned | Link outcomes to commissioning; bulk commissioning route (PLANNED) | M |
| M7 | For RUL models the platform ships the probabilistic trigger at untuned S1 settings, not a per-site tuned threshold (`data_scientist-3`) | The trigger is not tuned to any site | A per-site tuned point-threshold trigger (PLANNED) | M |
| M8 | Deviations are not shown in °C against the expected value. Instrument checks have no specific finding codes (`technician-8`, `technician-10`) | Technicians see standardised scores, not physical quantities | Console and outcome-model additions | L |
| M9 | A planner can defer a P1 order to any date; it comes back for approval on that date, but its length is not capped (`decision-lifecycle-10`) | An urgent order can be parked for a long time by one person | A cap, or a second approver, for deferring P1 work (PLANNED) | M |
| M10 | When a replayed export raises a latch, the order's explanation cites the latest applied assessment (for example a feed delay), not the replay that raised it. The replay is recorded in the asset's audit history (`asset_state.escalated_by_replay`) and notes | The approver must open the asset history to see the evidence | Cite the escalating assessment in the recommendation (PLANNED) | L |
| M11 | The rotor/generator relation check looks at the last scoring window, not at the whole span the model scores; only the stuck-sensor check covers the whole scored span (re-review residual) | A brief conflicting-readings episode at the start of the span can still be scored | Apply the conflict check to the whole scored span | L |

## 3. Platform and operations

| # | limitation | effect | removed by | sev |
|---|---|---|---|---|
| P1 | One process and one SQLite file; the rate limit is in-process | Single-site scale only; no high availability | A PostgreSQL port and process supervision if needed (PD-06) | L |
| P2 | List endpoints are unpaginated. `/assets` does several lookups per asset (latency in `product/evidence/load/l1.md`) | Slow fleet views at hundreds of assets | Pagination and a joined query | L |
| P3 | No retention or archiving of readings | Disk grows by about 0.17 MB per turbine-day | A retention policy | L |
| P4 | No API route creates asset types or sites; that needs the library or an admin | Onboarding needs an engineer | Admin routes (PLANNED) | L |
| P5 | Assessments, deferral reactivation and dispatch run from external schedulers (cron); none is built in | Operations must set up the jobs; ASSESSMENT_OVERDUE shows when they stop | A built-in scheduler, or documented service units | L |
| P6 | Audit-key rotation has no in-place procedure | A key change starts a new database generation | Re-anchoring support (PLANNED) | L |
| P7 | The console has no offline mode and no mobile layout, is English only, and has no feedback form. It needs a live connection and an API key (`technician-11`) | Limited use at the turbine | Pilot feedback (`OPERATOR_FEEDBACK_PLAN.md`) | M |
| P8 | The scheduler has no cranes, weather or climbing-wind limits, travel between turbines, multi-day jobs or multi-site crews (`om_manager-4`) | Schedules for major wind jobs are not feasible plans; the adapter's major-component jobs cannot be scheduled realistically | Scheduler extensions, driven by a customer's real constraints | H for wind operations; M for a shadow pilot |
| P9 | No workflow for OEM-serviced turbines: no responsible party, OEM ticket reference or service-report import (`om_manager-10`) | Sites under OEM contracts cannot route work | An OEM workflow (PLANNED) | M |
| P10 | No "my jobs" view. Technician resources are not linked to users, so any technician can start or complete any scheduled order (`technician-12`, `security-5`) | Weak accountability on the floor | Link resources to users and add assignment checks | M |
| P11 | The console cannot raise a follow-up job or edit shifts (`technician-7`). Roles are not scoped per site, and there is no O&M-head reporting (`om_manager-15`) | Planners use the API or the CMMS for these | Console additions; per-site role scoping | M |
| P12 | No per-site tag mapping (FR-B3). Each turbine must deliver the adapter's required signals under the adapter's names (`pitch_angle` is optional) (`om_manager-11`) | Onboarding needs a data-mapping step outside the product | Per-site mapping configuration (PLANNED) | M |
| P13 | `assess-range` costs one rate-limit token per 10 steps: with the shipped limiter at most about 1,200 steps per call. One range runs per user and two per server; others get 429 with Retry-After | Back-fills of long exports must be split, and the assessment job must honour 429 | Configure the limiter per site; a queued back-fill job (PLANNED) | L |
| P14 | Building the MILP ignores its time limit; the API refuses MILP requests above 5,000 order-slots instead (`api-security-console-7`) | Large what-if MILP runs need a shorter horizon or longer slots | Time-limited model building | L |

## 4. Integration and security

| # | limitation | effect | removed by | sev |
|---|---|---|---|---|
| S1 | The CMMS connector is tested only against a contract test double. The real Odoo sandbox run is pending image-download approval | Compatibility with real Odoo is unproven | Run `sandbox/odoo/setup.sh` and `tests/test_app_odoo_sandbox.py` | H |
| S2 | No customer CMMS integration exists | No claim of compatibility with SAP PM, Maximo, etc. | A per-customer adapter and test | M |
| S3 | No external penetration test, no SSO, and no signed model manifests. Registration hashes the bundle against its own manifest only (`security-13`) | Security claims are limited to the reviewed code and tests | An external test; OIDC; signatures | M |
| S4 | Dependency advisories: mlflow 3.0.1 (development only; excluded from platform installs), pyarrow 20.0.0, pytest 8.4.2 | Known vulnerabilities in the development environment | Upgrades (download approval pending) | M |
| S5 | Technician data are not pseudonymised. Deletion tooling does not exist, and the audit chain records actor names that cannot be redacted (`safety-9`). DPDP duties have not been checked against the Act | Data-protection exposure at a customer | Pseudonymisation, opaque audit actors and a legal review | M |
| S6 | The integration (machine) role can assess and dispatch, and is broader than one job needs. Its completions never clear latches (`security-5`) | A stolen integration key can create noise and replays, though not clear a latch | Split the integration role | M |
| S7 | The audit chain covers audit events, not state tables: a direct database edit of state is not detected (PD-22). `/ready` and the OpenAPI schema are unauthenticated (accepted) | Tamper evidence depends on database access control | Restrict database access; state hashing if required | L |
| S8 | CSV uploads are capped at 200,000 readings and parsed off the event loop, but not streamed (`security-8`) | Large exports must be split | A streaming parser | L |
| S9 | Signed CMMS webhooks carry no version or delivery id, so a receiver cannot reject an in-window replay or reordering (`cmms-integration-9`) | A receiver must deduplicate by work-order id and state itself | Add a delivery id and version to the signed body | L |
| S10 | After a lost create answer, the CMMS is searched by marker before any re-create, and once more an hour later. A duplicate found by those searches is dead-lettered for a person, and the other request stays live until a person acts. A create that commits after the one-hour re-check is **not detected** | Rare duplicate maintenance requests need manual closure, and a very late one is not flagged | A CMMS-side idempotency key where the CMMS supports one | L |
| S11 | Integration configs stored before the re-review fixes are re-checked at dispatch: a timeout above 120 s is clamped, and an invalid database name dead-letters every item. There is no config-update route (re-register under a new id) | An upgraded site with an invalid stored value must re-register its target | An audited config-update route (PLANNED) | L |

## 5. Commercial

| # | limitation | effect | removed by | sev |
|---|---|---|---|---|
| C1 | There is no pricing hypothesis, ROI method, unit-economics model or customer reference, and no commercial pilot terms (`buyer-5`) | No business case can be presented as evidence; business value sits on rung 0 | G1 conversations; a pilot with agreed terms; an ROI method agreed with the partner before data | H for sales; does not block engineering work |
| C2 | No validated reason to buy over incumbents. Indian OEM and SCADA-analytics alternatives have not been verified (`buyer-10`) | Differentiation is a hypothesis | Sourced competitive research and customer conversations | M |
| C3 | Savings, avoided failures and availability gains are explicitly out of scope. A read-only shadow pilot (rung 5) cannot show them, because nothing the system says changes what the partner does | No savings claim may be made | A rung-6 trial in which recommendations are acted on, with a baseline and measurement plan agreed before it starts (`VALIDATION_LADDER.md`) | H for sales |

## 6. Scope boundary (not a defect)

SentinelLoop is advisory. It is not part of any safety function and claims no SIL. It takes no protection-layer credit and must not be counted as a barrier in a hazard analysis. It never writes to a control system, and no recommendation becomes work without a named person's approval (`RELIABILITY_AND_SAFETY.md` §1).
