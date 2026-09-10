from __future__ import annotations

import time
import numpy as np
from sklearn.metrics import (
    accuracy_score, average_precision_score, balanced_accuracy_score, brier_score_loss,
    confusion_matrix, f1_score, log_loss, precision_score, recall_score, roc_auc_score,
)


def expected_calibration_error(y, probability, bins=10):
    y, probability = np.asarray(y), np.asarray(probability)
    edges = np.linspace(0, 1, bins + 1)
    total = 0.0
    for low, high in zip(edges[:-1], edges[1:]):
        mask = (probability >= low) & (probability < high if high < 1 else probability <= high)
        if mask.any():
            total += mask.mean() * abs(y[mask].mean() - probability[mask].mean())
    return float(total)


def classification_metrics(y, probability, threshold=0.5):
    y = np.asarray(y).astype(int); probability = np.asarray(probability)
    pred = (probability >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {
        "pr_auc": float(average_precision_score(y, probability)),
        "roc_auc": float(roc_auc_score(y, probability)) if len(np.unique(y)) > 1 else None,
        "precision": float(precision_score(y, pred, zero_division=0)),
        "recall": float(recall_score(y, pred, zero_division=0)),
        "f1": float(f1_score(y, pred, zero_division=0)),
        "balanced_accuracy": float(balanced_accuracy_score(y, pred)),
        "specificity": float(tn / (tn + fp)) if tn + fp else 0.0,
        "accuracy": float(accuracy_score(y, pred)),
        "brier": float(brier_score_loss(y, probability)),
        "log_loss": float(log_loss(y, np.clip(probability, 1e-9, 1 - 1e-9))),
        "ece": expected_calibration_error(y, probability),
        "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
        "alerts_generated": int(pred.sum()), "threshold": float(threshold),
        "false_positive_rate": float(fp / (fp + tn)) if fp + tn else 0.0,
    }


def timed_probabilities(model, X):
    start = time.perf_counter(); probability = model.predict_proba(X)[:, 1]
    elapsed = time.perf_counter() - start
    return probability, 1000 * elapsed / max(len(X), 1)
