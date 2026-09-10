# Model comparison

Model selection was made on validation data. Test metrics are reported for comparison but were not used to select hyperparameters. PR-AUC is primary because delay events are the minority class.

| model                    |   pr_auc |   roc_auc |   precision |   recall |       f1 |   balanced_accuracy |    brier | calibration   |   inference_ms_per_row | interpretability   |
|:-------------------------|---------:|----------:|------------:|---------:|---------:|--------------------:|---------:|:--------------|-----------------------:|:-------------------|
| Dummy_prior              | 0.282599 |  0.5      |    0.282599 | 1        | 0.440666 |            0.5      | 0.217064 | raw           |             0.00063878 | high               |
| Logistic_unweighted_C0.1 | 0.560827 |  0.799162 |    0.515777 | 0.697865 | 0.593161 |            0.71989  | 0.170451 | raw           |             0.00393939 | high               |
| CatBoost_1               | 0.552698 |  0.791872 |    0.553145 | 0.418719 | 0.476636 |            0.642736 | 0.194637 | raw           |             0.00346574 | SHAP-supported     |
| XGBoost_3                | 0.564923 |  0.780946 |    0.574324 | 0.418719 | 0.48433  |            0.648234 | 0.18128  | raw           |             0.00813319 | SHAP-supported     |
| CatBoost_1_calibrated    | 0.552698 |  0.791872 |    0.555332 | 0.453202 | 0.499096 |            0.655126 | 0.194637 | none          |             0.00346574 | SHAP-supported     |