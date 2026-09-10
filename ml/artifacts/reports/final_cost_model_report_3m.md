# cost_escalation_3m_v1 final model report

## Decision

- Status: **RED**
- Selected on validation only: **CatBoost_weighted**
- Validation PR-AUC: **0.4523**
- Calibration: **isotonic**
- Operating threshold: **0.393558**

## Untouched temporal test

| Metric | Value |
|---|---:|
| Overall target prevalence | 0.0163 |
| Test baseline prevalence | 0.0085 |
| PR-AUC | 0.0209 |
| PR-AUC lift | 2.46x |
| ROC-AUC | 0.6071 |
| Precision | 0.0345 |
| Recall | 0.0455 |
| F1 | 0.0392 |
| Balanced accuracy | 0.5173 |
| False-positive rate | 0.0109 |
| Alerts generated | 29 |
| Brier score | 0.0106 |
| ECE | 0.0118 |

Cost escalation modelling remains experimental due to event sparsity.
