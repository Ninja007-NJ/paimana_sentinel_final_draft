# Feature-direction sanity check

Correlations between major numerical values and their SHAP contributions are in `feature_sanity.json`. Flags identify counter-intuitive protective relationships for schedule pressure, revision history, or stagnation; they are review prompts, not imposed monotonic rules.

| feature                       |   value_shap_correlation | review_flag   |
|:------------------------------|-------------------------:|:--------------|
| project_age_months            |              -0.38084    | False         |
| months_to_target              |              -0.337596   | False         |
| current_time_slip_months      |               0.456999   | False         |
| current_cost_overrun_pct      |               0.323602   | False         |
| spend_ratio_pct               |               0.016416   | False         |
| physical_progress_pct         |               0.85594    | False         |
| financial_physical_gap_pct    |               0.0395351  | False         |
| progress_delta_1m             |              -0.243909   | False         |
| progress_delta_3m             |              -0.361773   | False         |
| progress_delta_6m             |               0.667276   | False         |
| spend_delta_1m_cr             |              -0.00539216 | False         |
| spend_delta_3m_cr             |              -0.0927866  | False         |
| spend_delta_6m_cr             |              -0.0228948  | False         |
| progress_velocity_3m          |              -0.29532    | False         |
| schedule_pressure             |               0.470478   | False         |
| stagnation_streak_months      |              -0.559156   | True          |
| target_revision_count_to_date |              -0.0835421  | False         |
| cost_revision_count_to_date   |              -0.488379   | False         |
| data_quality_score            |              -0.111733   | False         |
| missing_core_fields_count     |             nan          | False         |