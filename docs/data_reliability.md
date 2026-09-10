# Data reliability

Prediction probability and data reliability are intentionally separate. Reliability combines the dataset quality score, missing model inputs, fallback/generated identity and values outside reference ranges. It is returned as a 0–100 score and HIGH, MEDIUM or LOW label. A high probability with low reliability should trigger source review, not stronger certainty.
