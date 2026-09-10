# Temporal split

The split was fixed before training and preserves chronology.

| partition   | start   | end     |   rows |   unique_projects |   positives |   negatives |   positive_rate_pct |
|:------------|:--------|:--------|-------:|------------------:|------------:|------------:|--------------------:|
| train       | 2025-01 | 2025-08 |   6065 |              1786 |         988 |        5077 |             16.2902 |
| validation  | 2025-09 | 2025-11 |   2148 |               774 |         336 |        1812 |             15.6425 |
| test        | 2025-12 | 2026-01 |   2155 |              1313 |         609 |        1546 |             28.2599 |

## Project overlap

| comparison       |   overlap_projects |   left_projects |   right_projects |
|:-----------------|-------------------:|----------------:|-----------------:|
| train_validation |                685 |            1786 |              774 |
| train_test       |                949 |            1786 |             1313 |
| validation_test  |                727 |             774 |             1313 |

Secondary robustness uses only temporal-test rows from projects absent from both train and validation.
