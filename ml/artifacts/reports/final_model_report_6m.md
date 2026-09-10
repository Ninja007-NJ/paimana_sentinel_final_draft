# delay_6m_v1 final model report

## Decision

- Status: **GREEN**
- Selected on validation only: **CatBoost_weighted**
- Validation PR-AUC: **0.6379**
- Calibration: **isotonic**
- Operating threshold: **0.397369**

## Untouched temporal test

| Metric | Value |
|---|---:|
| Overall target prevalence | 0.2014 |
| Test baseline prevalence | 0.2670 |
| PR-AUC | 0.7430 |
| PR-AUC lift | 2.78x |
| ROC-AUC | 0.8822 |
| Precision | 0.6355 |
| Recall | 0.7681 |
| F1 | 0.6955 |
| Balanced accuracy | 0.8038 |
| False-positive rate | 0.1605 |
| Alerts generated | 417 |
| Brier score | 0.1189 |
| ECE | 0.0693 |

The model is a predictive association, not a causal assessment.
