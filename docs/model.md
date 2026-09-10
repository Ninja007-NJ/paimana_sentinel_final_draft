# Frozen Model V1.1

The primary model is CatBoost V1.1 (`delay_3m_v1_1`). It estimates whether the reported expected/revised completion target will move later within three calendar months, using only current and prior observations. Evaluation uses a temporal split rather than a random future-mixing split. Frozen validation PR-AUC is 0.7877. Temporal-test metrics are PR-AUC 0.6061, ROC-AUC 0.8214, precision 0.6436, recall 0.4269, F1 0.5133, Brier 0.1848 and ECE 0.1531.

Status is YELLOW: useful signal with calibration and unseen-project limitations. Unseen-project PR-AUC is 0.5315 with recall 0.1471, materially weaker than recurring-project monitoring. The product does not retrain, replace, or tune this artifact. Six-month and cost models are not part of the production interface.
