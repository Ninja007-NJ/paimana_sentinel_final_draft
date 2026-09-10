# PAIMANA Sentinel — Model V1

Production-oriented early-warning classifier for the probability that a project's reported completion target moves later within three calendar months.

The frozen input is `paimana_dataset_v3/training_delay_3m.csv`. Dataset builders and cached PDFs are never modified by this package.

## Commands

```bash
python -m ml.train_delay_3m
python -m ml.evaluate_delay_3m
python -m ml.predict_delay_3m --input project_rows.csv
python -m pytest ml/tests
```

Primary evaluation is chronological: January–August 2025 train, September–November validation, and December 2025–January 2026 test. Model V1 excludes project identifiers, reporting regime, future coverage, validity fields, targets, and future-derived values from predictors.

Probabilities describe predictive association with a future reported target revision. They do not prove causality or execution failure.
