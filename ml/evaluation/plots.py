from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.calibration import calibration_curve
from sklearn.metrics import ConfusionMatrixDisplay, PrecisionRecallDisplay, RocCurveDisplay


def _save(path):
    plt.tight_layout(); plt.savefig(path, dpi=160, bbox_inches="tight"); plt.close()


def target_plots(data, target, plot_dir):
    ax = data[target].value_counts().sort_index().plot.bar(color=["#5b8ff9", "#e8684a"])
    ax.set(title="3-month delay target distribution", xlabel="Delay event", ylabel="Rows")
    _save(plot_dir / "target_distribution.png")
    monthly = data.groupby("snapshot_month")[target].agg(["count", "sum"]); monthly["rate"] = monthly["sum"] / monthly["count"]
    monthly["rate"].plot(marker="o", color="#e8684a")
    plt.title("Delay-event rate by snapshot month"); plt.ylabel("Positive rate"); plt.xticks(rotation=45)
    _save(plot_dir / "target_distribution_by_month.png")


def comparison_curves(y, probabilities, plot_dir):
    for kind, display, filename in (("pr", PrecisionRecallDisplay, "pr_curves.png"), ("roc", RocCurveDisplay, "roc_curves.png")):
        _, ax = plt.subplots(figsize=(7, 5))
        for name, probability in probabilities.items():
            display.from_predictions(y, probability, name=name, ax=ax)
        ax.set_title("Precision–Recall curves" if kind == "pr" else "ROC curves")
        _save(plot_dir / filename)


def confusion_plot(y, probability, threshold, path):
    ConfusionMatrixDisplay.from_predictions(y, np.asarray(probability) >= threshold, cmap="Blues", colorbar=False)
    plt.title(f"Temporal test confusion matrix (threshold={threshold:.3f})"); _save(path)


def threshold_plot(table, path):
    plt.plot(table.threshold, table.precision, label="Precision"); plt.plot(table.threshold, table.recall, label="Recall"); plt.plot(table.threshold, table.f1, label="F1")
    plt.xlabel("Threshold"); plt.ylabel("Score"); plt.title("Validation threshold analysis"); plt.legend(); _save(path)


def calibration_plot(y, series, path):
    for name, probability in series.items():
        observed, predicted = calibration_curve(y, probability, n_bins=10, strategy="quantile")
        plt.plot(predicted, observed, marker="o", label=name)
    plt.plot([0, 1], [0, 1], "--", color="gray", label="Ideal")
    plt.xlabel("Predicted probability"); plt.ylabel("Observed frequency"); plt.title("Calibration on temporal test"); plt.legend(); _save(path)


def bar_metrics(records, label, value, title, path):
    frame = pd.DataFrame(records)
    if frame.empty: return
    sns.barplot(data=frame, x=label, y=value, color="#5b8ff9"); plt.title(title); plt.xticks(rotation=45, ha="right"); _save(path)


def feature_importance_plot(importance, path, top_n=15):
    frame = pd.DataFrame(importance).sort_values("importance").tail(top_n)
    plt.barh(frame.feature, frame.importance, color="#5b8ff9"); plt.title("Top global model drivers"); plt.xlabel("Mean absolute SHAP value"); _save(path)
