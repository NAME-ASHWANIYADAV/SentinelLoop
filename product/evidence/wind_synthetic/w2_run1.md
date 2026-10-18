# W2 inspection margin and sustain revisited (generated; SYNTHETIC; behaviour calibration only)

Tuning fleets: seeds 40-45 (never used by W1). Held-out check: the W1 fleets (seeds 20-25). Rule fixed before running: <= 1.0 healthy alarm episode per turbine-year, then most detections, then longest median lead.

## Tuning fleets

| margin | sustain (10-min points) | detected | median lead (days) | healthy alarm episodes / turbine-years = per turbine-year | drifting-sensor episodes | pre-onset alarms | assessable share |
|---|---|---|---|---|---|---|---|
| 1.25 | 6 | 36/36 | 9.4 | 3 / 2.27 = 1.32 | 41 | 2 | 0.54 |
| 1.25 | 12 | 36/36 | 8.9 | 2 / 2.27 = 0.88 | 42 | 0 | 0.54 |
| 1.25 | 18 | 36/36 | 8.8 | 2 / 2.27 = 0.88 | 41 | 0 | 0.54 |
| 1.25 | 36 | 36/36 | 8.3 | 2 / 2.27 = 0.88 | 38 | 0 | 0.55 |
| 1.5 | 6 | 36/36 | 8.7 | 2 / 2.27 = 0.88 | 38 | 0 | 0.54 |
| 1.5 | 12 | 36/36 | 8.7 | 2 / 2.27 = 0.88 | 39 | 0 | 0.54 |
| 1.5 | 18 | 36/36 | 8.6 | 2 / 2.27 = 0.88 | 37 | 0 | 0.54 |
| 1.5 | 36 | 36/36 | 7.9 | 2 / 2.27 = 0.88 | 36 | 0 | 0.55 |
| 2.0 | 6 | 36/36 | 7.6 | 2 / 2.27 = 0.88 | 37 | 0 | 0.54 |
| 2.0 | 12 | 36/36 | 7.6 | 2 / 2.27 = 0.88 | 38 | 0 | 0.54 |
| 2.0 | 18 | 36/36 | 7.5 | 2 / 2.27 = 0.88 | 37 | 0 | 0.54 |
| 2.0 | 36 | 36/36 | 6.9 | 2 / 2.27 = 0.88 | 35 | 0 | 0.55 |
| 2.5 | 6 | 36/36 | 7.2 | 2 / 2.27 = 0.88 | 36 | 0 | 0.54 |
| 2.5 | 12 | 36/36 | 7.0 | 2 / 2.27 = 0.88 | 37 | 0 | 0.54 |
| 2.5 | 18 | 36/36 | 6.9 | 2 / 2.27 = 0.88 | 36 | 0 | 0.54 |
| 2.5 | 36 | 36/36 | 6.1 | 2 / 2.27 = 0.88 | 35 | 0 | 0.55 |

Chosen: margin 1.25, sustain 12

## Held-out W1 fleets (seeds 20-25): chosen setting vs the previous setting (1.25, 6)

| margin | sustain (10-min points) | detected | median lead (days) | healthy alarm episodes / turbine-years = per turbine-year | drifting-sensor episodes | pre-onset alarms | assessable share |
|---|---|---|---|---|---|---|---|
| 1.25 | 6 | 36/36 | 9.6 | 13 / 2.27 = 5.74 | 38 | 7 | 0.59 |
| 1.25 | 12 | 36/36 | 8.9 | 6 / 2.27 = 2.65 | 37 | 3 | 0.59 |

Caveats: the generator and the model share assumptions (KNOWN_LIMITATIONS E3); a slow drift of a single temperature sensor still cannot be told apart from heating; these numbers say nothing about real turbines.
