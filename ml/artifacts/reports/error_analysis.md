# Error analysis

At the balanced threshold there are **221** false positives and **333** false negatives. The table summarizes the 100 highest-confidence errors of each type; row-level evidence is exported separately. Predictions are associations, not causal findings.

| error_type     |   reviewed_rows |   mean_months_to_target |   mean_current_time_slip_months |   mean_schedule_pressure |   mean_physical_progress_pct |   mean_progress_velocity_3m |   mean_target_revision_count_to_date |   mean_data_quality_score | common_sector     |
|:---------------|----------------:|------------------------:|--------------------------------:|-------------------------:|-----------------------------:|----------------------------:|-------------------------------------:|--------------------------:|:------------------|
| false_positive |             100 |                    0.59 |                           20.37 |                  18.0995 |                        65.54 |                     1.17037 |                                 1.12 |                     93.12 | Telecommunication |
| false_negative |             100 |                  -11.24 |                           15.92 |                  15.7499 |                        63.11 |                     1.58621 |                                 1.05 |                     90.32 | Railways          |
