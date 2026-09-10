# Leakage audit — PAIMANA dataset V3

No future observation is used in an engineered feature. Future rows are read only by the four label builders after the feature row at month `t` has been completed.

| Feature family | Data available at month t | Why leakage-safe |
|---|---|---|
| Identity and metadata | Current and repaired stable categorical observations | Repair uses only stable descriptive fields, never outcomes or time-varying numbers. |
| Project age / months to target | Approval/start and target reported at t | No later report is consulted. |
| Current slip / cost overrun / spend ratio | Original and current values reported at t | These are contemporaneous state variables. |
| Progress and spend deltas | Exact observations at t-1, t-3, or t-6 | `nearest_prior` requires the intended prior calendar month and never substitutes a future row. |
| Velocity / schedule pressure / stagnation | Current and prior observations only | Computed before future labels are evaluated. |
| Revision counts to date | Chronological observations through t | Counters are updated while walking forward and contain no later revisions. |
| Data-quality and provenance flags | Source rows through t | Transition flags compare t only with t-1. |
| Delay and cost labels | Strictly t+1..t+h | These columns are outcomes, not features; gaps or semantic ambiguity produce NaN. |

The model-specific CSVs retain only rows whose corresponding outcome is genuinely known. They must not feed label columns, validity flags, future-coverage fields, or future-derived audit fields into model features.

Do **not** use a random row-level train/test split. Use a temporal split for future evaluation, with optional group-aware checks by `canonical_project_id` to measure project memorization. No ML model was trained by this builder.
