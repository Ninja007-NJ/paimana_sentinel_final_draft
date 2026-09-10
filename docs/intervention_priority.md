# Intervention Intelligence

The Intervention Priority Engine is a deterministic decision-support layer over PAIMANA Sentinel's existing trusted analytics. It does not train a model, estimate a new probability, or change the frozen 3-month and accepted 6-month predictions.

## Risk velocity and acceleration

All calculations use the ordered 3-month delay probabilities and remain in probability points internally:

- `risk_change_1m = p(t) - p(t-1)`
- `risk_change_3m = p(t) - p(t-3)` when four reporting observations exist
- `risk_velocity` is the mean consecutive change over up to the latest three reporting intervals
- `risk_acceleration = [p(t) - p(t-1)] - [p(t-1) - p(t-2)]`

Acceleration classification requires at least three observations. Projects with fewer observations return `INSUFFICIENT_HISTORY`; unavailable numeric values are `null`. The frontend multiplies probability-point changes by 100 only for percentage-point display.

The thresholds were derived from the frozen portfolio's positive-change distributions rather than guessed constants:

- Meaningful one-period change: positive-change 25th percentile = `0.02049447`
- Rapid one-period change: positive-change 75th percentile = `0.29932496`
- Rapid three-period change: positive-change 75th percentile = `0.56081081`
- Material acceleration: positive-acceleration 75th percentile = `0.31013893`

Classification is exclusive and follows this order: `IMPROVING`, `ACCELERATING`, `RAPIDLY_RISING`, `RISING`, then `STABLE`. Only observations available through each project's latest reporting period are used; no future records or target outcomes enter the calculation.

## Intervention Priority Score

The score is bounded from 0 to 100 and is explicitly not a probability. It uses six explainable components:

- Schedule risk — 35 points: `25 × 3-month probability + 10 × 6-month probability`
- Trajectory — 20 points based on the exclusive trajectory state
- Active deterministic alerts — 15 points, with transparent alert-type weights and a hard cap
- Sector-peer position — 10 points from risk percentile and inverse progress percentile when the peer cohort is sufficient
- Project exposure — 10 points from the current valid cost's empirical portfolio percentile
- Schedule pressure — 10 points from the existing schedule-pressure metric's empirical portfolio percentile

Priority levels use the portfolio score distribution: `CRITICAL` at or above the 90th percentile (`69.051`), `HIGH` at or above the 75th (`46.4575`), `MEDIUM` at or above the 40th (`20.09`), otherwise `LOW`. This avoids concentrating most projects in one high-priority band. Ties are ordered by canonical project ID.

Data Reliability does not inflate or suppress the score. It changes the recommended action: high operational risk with reliability below 65 becomes `VERIFY_DATA_URGENTLY`; high operational risk with adequate reliability becomes `IMMEDIATE_REVIEW`; moderate projects with rapid or accelerating deterioration become `EARLY_INTERVENTION`; remaining projects receive `ROUTINE_MONITORING`.

## Frozen portfolio audit

The deterministic audit contains 2,804 unique eligible projects. Of these, 195 have insufficient history. Trajectory counts are 707 improving, 1,105 stable, 477 rising, 207 rapidly rising, 113 accelerating, and 195 insufficient history. Priority counts are 281 critical, 420 high, 982 medium, and 1,121 low. Recommended actions are 766 immediate review, 23 early intervention, 0 verify data urgently, and 2,015 routine monitoring. The zero verification count reflects the current portfolio's reliability distribution; the rule remains implemented and tested for low-reliability, high-risk inputs.

