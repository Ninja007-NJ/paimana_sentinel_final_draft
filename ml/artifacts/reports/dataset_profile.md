# Dataset profile — PAIMANA Sentinel Model V1

- Rows: **10,368**
- Unique projects: **2,154**
- Snapshot range: **2025-01 through 2026-01**
- Positive prevalence: **18.64%**
- Fallback/generated identity rows: **39**

## Target by month

| snapshot_month   |   rows |   positives |   negatives |   positive_rate_pct |
|:-----------------|-------:|------------:|------------:|--------------------:|
| 2025-01          |   1460 |         315 |        1145 |             21.5753 |
| 2025-02          |   1351 |         272 |        1079 |             20.1332 |
| 2025-03          |   1340 |         252 |        1088 |             18.806  |
| 2025-04          |    268 |          16 |         252 |              5.9701 |
| 2025-05          |    278 |          15 |         263 |              5.3957 |
| 2025-06          |    256 |           6 |         250 |              2.3438 |
| 2025-07          |    458 |          46 |         412 |             10.0437 |
| 2025-08          |    654 |          66 |         588 |             10.0917 |
| 2025-09          |    657 |         108 |         549 |             16.4384 |
| 2025-10          |    736 |         123 |         613 |             16.712  |
| 2025-11          |    755 |         105 |         650 |             13.9073 |
| 2025-12          |    865 |         192 |         673 |             22.1965 |
| 2026-01          |   1290 |         417 |         873 |             32.3256 |

## Feature missingness

| feature                       |   missing_pct |
|:------------------------------|--------------:|
| project_age_months            |        4.3017 |
| months_to_target              |        0      |
| current_time_slip_months      |        0      |
| current_cost_overrun_pct      |        0      |
| spend_ratio_pct               |        0      |
| physical_progress_pct         |        4.7068 |
| financial_physical_gap_pct    |        4.7068 |
| progress_delta_1m             |       24.2091 |
| progress_delta_3m             |       57.0988 |
| progress_delta_6m             |       71.412  |
| spend_delta_1m_cr             |       20.6019 |
| spend_delta_3m_cr             |       55.4688 |
| spend_delta_6m_cr             |       68.8657 |
| progress_velocity_3m          |       57.0988 |
| schedule_pressure             |        4.7068 |
| stagnation_streak_months      |        0      |
| target_revision_count_to_date |        0      |
| cost_revision_count_to_date   |        0      |
| data_quality_score            |        0      |
| missing_core_fields_count     |        0      |
| sector                        |       10.87   |
| state                         |       12.2685 |
| ministry_department           |       12.3553 |

## Categorical cardinality

| feature             |   unique |   missing_pct |
|:--------------------|---------:|--------------:|
| sector              |       33 |       10.87   |
| state               |      114 |       12.2685 |
| ministry_department |       17 |       12.3553 |

## Data quality

| threshold   |   rows |
|:------------|-------:|
| below_90    |   3234 |
| below_80    |    543 |
| below_70    |    118 |
| below_60    |     24 |

## Numerical distributions

Full percentiles and moments are stored in `dataset_profile.json`; no rows were removed during profiling.
