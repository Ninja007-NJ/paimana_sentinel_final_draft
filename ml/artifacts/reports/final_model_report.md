# PAIMANA Sentinel — Model V1 final report

## Decision

**MODEL_STATUS=YELLOW**

The validation-selected model is **CatBoost_1**, calibrated with **none**. Selection emphasized future-period PR-AUC, operational recall/precision, calibration, stability, and explainability—not accuracy alone.

The model has substantial signal above the temporal-test prevalence baseline, but it does not materially exceed the transparent logistic benchmark: final PR-AUC is **0.5527** versus logistic **0.5608**, and test ECE is **0.1580**. It therefore requires another feature/calibration iteration before a GREEN production recommendation.

## Temporal test metrics

|   pr_auc |   roc_auc |   precision |   recall |       f1 |   balanced_accuracy |   specificity |   accuracy |    brier |   log_loss |   ece |   tn |   fp |   fn |   tp |   alerts_generated |   threshold |   false_positive_rate |
|---------:|----------:|------------:|---------:|---------:|--------------------:|--------------:|-----------:|---------:|-----------:|------:|-----:|-----:|-----:|-----:|-------------------:|------------:|----------------------:|
| 0.552698 |  0.791872 |    0.555332 | 0.453202 | 0.499096 |            0.655126 |       0.85705 |   0.742923 | 0.194637 |   0.628602 | 0.158 | 1325 |  221 |  333 |  276 |                497 |        0.23 |               0.14295 |

## Baseline comparison

| model                    |   pr_auc |   roc_auc |   precision |   recall |       f1 |   balanced_accuracy |    brier |
|:-------------------------|---------:|----------:|------------:|---------:|---------:|--------------------:|---------:|
| Dummy_prior              | 0.282599 |  0.5      |    0.282599 | 1        | 0.440666 |            0.5      | 0.217064 |
| Logistic_unweighted_C0.1 | 0.560827 |  0.799162 |    0.515777 | 0.697865 | 0.593161 |            0.71989  | 0.170451 |
| CatBoost_1               | 0.552698 |  0.791872 |    0.553145 | 0.418719 | 0.476636 |            0.642736 | 0.194637 |
| XGBoost_3                | 0.564923 |  0.780946 |    0.574324 | 0.418719 | 0.48433  |            0.648234 | 0.18128  |
| CatBoost_1_calibrated    | 0.552698 |  0.791872 |    0.555332 | 0.453202 | 0.499096 |            0.655126 | 0.194637 |

## Quality experiment

| dataset       |   pr_auc |   roc_auc |   precision |   recall |       f1 |   balanced_accuracy |   specificity |   accuracy |    brier |   log_loss |      ece |   tn |   fp |   fn |   tp |   alerts_generated |   threshold |   false_positive_rate |
|:--------------|---------:|----------:|------------:|---------:|---------:|--------------------:|--------------:|-----------:|---------:|-----------:|---------:|-----:|-----:|-----:|-----:|-------------------:|------------:|----------------------:|
| full          | 0.552698 |  0.791872 |    0.555332 | 0.453202 | 0.499096 |            0.655126 |      0.85705  |   0.742923 | 0.194637 |   0.628602 | 0.158    | 1325 |  221 |  333 |  276 |                497 |        0.23 |              0.14295  |
| quality >= 80 | 0.587374 |  0.802465 |    0.518341 | 0.557461 | 0.53719  |            0.676288 |      0.795115 |   0.727759 | 0.173907 |   0.514534 | 0.114058 | 1172 |  302 |  258 |  325 |                627 |        0.23 |              0.204885 |

## Limitations

The outcome is a reported target-date deterioration signal, not proof of execution failure or causality. Reporting regimes changed during Dataset v1.0. Temporal test contains recurring and unseen projects; unseen-project results are separately reported. No cost model, neural network, frontend, peer engine, or causal what-if engine was trained.
