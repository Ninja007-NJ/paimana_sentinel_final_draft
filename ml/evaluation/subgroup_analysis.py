from __future__ import annotations

import pandas as pd
from ml.evaluation.metrics import classification_metrics


def subgroup_metrics(frame, probabilities, target, group_column, threshold, minimum_rows=50, minimum_positives=5):
    work = frame.copy(); work["probability"] = probabilities
    output = []
    for name, group in work.groupby(group_column, dropna=False):
        positives = int(group[target].sum())
        if len(group) < minimum_rows or positives < minimum_positives or positives == len(group): continue
        output.append({"group_column": group_column, "group": str(name), "rows": len(group), "positives": positives, **classification_metrics(group[target], group.probability, threshold)})
    return output
