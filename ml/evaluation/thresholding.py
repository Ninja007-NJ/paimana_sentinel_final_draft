from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix, f1_score, precision_score, recall_score


def threshold_table(y, probability, thresholds=None):
    thresholds = np.asarray(thresholds if thresholds is not None else np.linspace(0.02, 0.90, 177))
    records = []
    for threshold in thresholds:
        pred = (np.asarray(probability) >= threshold).astype(int)
        tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
        records.append({
            "threshold": float(threshold),
            "precision": precision_score(y, pred, zero_division=0),
            "recall": recall_score(y, pred, zero_division=0),
            "f1": f1_score(y, pred, zero_division=0),
            "false_positive_rate": fp / (fp + tn) if fp + tn else 0,
            "alerts_generated": int(pred.sum()),
        })
    return pd.DataFrame(records)


def select_thresholds(table):
    balanced = table.loc[table.f1.idxmax()]
    early_pool = table[table.recall >= 0.80]
    early = early_pool.loc[early_pool.precision.idxmax()] if len(early_pool) else table.loc[table.recall.idxmax()]
    conservative_pool = table[table.precision >= 0.50]
    conservative = conservative_pool.loc[conservative_pool.recall.idxmax()] if len(conservative_pool) else table.loc[table.precision.idxmax()]
    critical_pool = table[table.precision >= 0.70]
    critical = critical_pool.loc[critical_pool.recall.idxmax()] if len(critical_pool) else table.iloc[(table.threshold - max(0.75, conservative.threshold)).abs().argsort()[:1]].iloc[0]
    values = {
        "EARLY_WARNING": float(early.threshold), "BALANCED": float(balanced.threshold),
        "CONSERVATIVE": float(conservative.threshold), "CRITICAL": float(critical.threshold),
    }
    ordered = sorted([values["EARLY_WARNING"], values["BALANCED"], values["CONSERVATIVE"], values["CRITICAL"]])
    values.update(dict(zip(("EARLY_WARNING", "BALANCED", "CONSERVATIVE", "CRITICAL"), ordered)))
    return values


def risk_level(probability, thresholds):
    if probability >= thresholds["CRITICAL"]: return "CRITICAL"
    if probability >= thresholds["CONSERVATIVE"]: return "HIGH"
    if probability >= thresholds["BALANCED"]: return "MEDIUM"
    return "LOW"
