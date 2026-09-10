from __future__ import annotations

from ml.evaluation.metrics import classification_metrics


def metrics_by_month(frame, probabilities, target, threshold, minimum_rows=25):
    work = frame[["snapshot_month", target]].copy(); work["probability"] = probabilities
    output = []
    for month, group in work.groupby("snapshot_month"):
        if len(group) < minimum_rows or group[target].nunique() < 2: continue
        metrics = classification_metrics(group[target], group.probability, threshold)
        output.append({"month": month, "rows": len(group), "positives": int(group[target].sum()), **metrics})
    return output
