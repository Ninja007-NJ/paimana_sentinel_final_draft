# Calibration report

Calibration was fit on September–October validation probabilities and selected using November validation Brier score/ECE.

| method   |   pr_auc |   roc_auc |   precision |   recall |       f1 |   balanced_accuracy |   specificity |   accuracy |     brier |   log_loss |       ece |   tn |   fp |   fn |   tp |   alerts_generated |   threshold |   false_positive_rate |
|:---------|---------:|----------:|------------:|---------:|---------:|--------------------:|--------------:|-----------:|----------:|-----------:|----------:|-----:|-----:|-----:|-----:|-------------------:|------------:|----------------------:|
| none     | 0.529473 |  0.895282 |    0.571429 | 0.419048 | 0.483516 |            0.684139 |      0.949231 |   0.875497 | 0.0837564 |   0.273409 | 0.0276766 |  617 |   33 |   61 |   44 |                 77 |         0.5 |             0.0507692 |
| sigmoid  | 0.529473 |  0.895282 |    0.554217 | 0.438095 | 0.489362 |            0.690586 |      0.943077 |   0.872848 | 0.0879573 |   0.293551 | 0.0642646 |  613 |   37 |   59 |   46 |                 83 |         0.5 |             0.0569231 |
| isotonic | 0.520069 |  0.893773 |    0.545455 | 0.628571 | 0.584071 |            0.771978 |      0.915385 |   0.875497 | 0.0864408 |   0.29999  | 0.0397722 |  595 |   55 |   39 |   66 |                121 |         0.5 |             0.0846154 |

Selected method: **none**. Test Brier raw: **0.1946**; calibrated: **0.1946**.
