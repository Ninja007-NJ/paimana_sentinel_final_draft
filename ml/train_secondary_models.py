"""Leakage-safe temporal evaluation for PAIMANA secondary risk models.

Model selection, calibration, and threshold choice use validation data only.
The chronological test partition is evaluated once after those choices are fixed.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier, Pool
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBClassifier

from ml.config import MODEL_DIR, RANDOM_SEED, REPORT_DIR
from ml.evaluation.metrics import classification_metrics
from ml.evaluation.thresholding import threshold_table
from ml.features.feature_registry import ALLOWED_FEATURES, CATEGORICAL_FEATURES, NUMERICAL_FEATURES
from ml.features.temporal_v1_1 import V1_1_FEATURES, add_v1_1_features
from ml.models.calibration import ProbabilityCalibrator

ROOT = Path(__file__).resolve().parents[1]
FEATURES = ALLOWED_FEATURES + V1_1_FEATURES
NUMERICAL = NUMERICAL_FEATURES + V1_1_FEATURES
CATEGORICAL = CATEGORICAL_FEATURES


@dataclass(frozen=True)
class Task:
    key: str
    dataset: str
    target: str
    train_end: str
    selection_months: tuple[str, ...]
    calibration_months: tuple[str, ...]
    test_months: tuple[str, ...]
    model_version: str
    bundle_name: str
    report_name: str


TASKS = {
    "delay_6m": Task("delay_6m", "training_delay_6m.csv", "delay_event_next_6m", "2025-06", ("2025-07",), ("2025-08",), ("2025-09", "2025-10"), "delay_6m_v1", "delay_6m_model_bundle_v1.joblib", "final_model_report_6m.md"),
    "cost_3m": Task("cost_3m", "training_cost_3m.csv", "cost_escalation_next_3m", "2025-08", ("2025-09", "2025-10"), ("2025-11",), ("2025-12", "2026-01"), "cost_escalation_3m_v1", "cost_3m_model_bundle_v1.joblib", "final_cost_model_report_3m.md"),
    "cost_6m": Task("cost_6m", "training_cost_6m.csv", "cost_escalation_next_6m", "2025-06", ("2025-07",), ("2025-08",), ("2025-09", "2025-10"), "cost_escalation_6m_v1", "cost_6m_model_bundle_v1.joblib", "final_cost_model_report_6m.md"),
}


def preprocessor(scale: bool) -> ColumnTransformer:
    numeric_steps = [("impute", SimpleImputer(strategy="median"))]
    if scale:
        numeric_steps.append(("scale", StandardScaler()))
    return ColumnTransformer([
        ("numeric", Pipeline(numeric_steps), NUMERICAL),
        ("categorical", Pipeline([("impute", SimpleImputer(strategy="most_frequent")), ("onehot", OneHotEncoder(handle_unknown="ignore", min_frequency=3))]), CATEGORICAL),
    ])


def prepare_cat(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame[FEATURES].copy()
    for column in CATEGORICAL:
        output[column] = output[column].fillna("__MISSING__").astype(str)
    return output


def candidates(train: pd.DataFrame, target: str) -> list[dict]:
    positives = max(int(train[target].sum()), 1)
    ratio = float((len(train) - positives) / positives)
    records = [{"name": "DummyClassifier", "kind": "dummy", "config": {}, "model": DummyClassifier(strategy="prior", random_state=RANDOM_SEED)}]
    for weight in (None, "balanced"):
        model = Pipeline([("preprocess", preprocessor(True)), ("model", LogisticRegression(C=1.0, class_weight=weight, max_iter=3000, random_state=RANDOM_SEED))])
        records.append({"name": f"Logistic_{weight or 'unweighted'}", "kind": "logistic", "config": {"class_weight": weight}, "model": model})
    for weighted in (False, True):
        config = {"iterations": 450, "depth": 5, "learning_rate": .04, "l2_leaf_reg": 7}
        if weighted:
            config["class_weights"] = [1.0, ratio]
        model = CatBoostClassifier(loss_function="Logloss", eval_metric="PRAUC", random_seed=RANDOM_SEED, verbose=False, allow_writing_files=False, thread_count=-1, **config)
        records.append({"name": f"CatBoost_{'weighted' if weighted else 'unweighted'}", "kind": "catboost", "config": config, "model": model})
    for weighted in (False, True):
        config = {"n_estimators": 450, "max_depth": 3, "learning_rate": .04, "min_child_weight": 4, "subsample": .85, "colsample_bytree": .85}
        if weighted:
            config["scale_pos_weight"] = ratio
        model = Pipeline([("preprocess", preprocessor(False)), ("model", XGBClassifier(objective="binary:logistic", eval_metric="logloss", random_state=RANDOM_SEED, n_jobs=-1, **config))])
        records.append({"name": f"XGBoost_{'weighted' if weighted else 'unweighted'}", "kind": "xgboost", "config": config, "model": model})
    return records


def fit(record: dict, frame: pd.DataFrame, target: str) -> dict:
    if record["kind"] == "dummy":
        record["model"].fit(np.zeros((len(frame), 1)), frame[target])
    elif record["kind"] == "catboost":
        record["model"].fit(prepare_cat(frame), frame[target], cat_features=CATEGORICAL, verbose=False)
    else:
        record["model"].fit(frame[FEATURES], frame[target])
    return record


def probabilities(record: dict, frame: pd.DataFrame) -> np.ndarray:
    if record["kind"] == "dummy":
        return record["model"].predict_proba(np.zeros((len(frame), 1)))[:, 1]
    if record["kind"] == "catboost":
        return record["model"].predict_proba(prepare_cat(frame))[:, 1]
    return record["model"].predict_proba(frame[FEATURES])[:, 1]


def clone_selected(record: dict, train: pd.DataFrame, target: str) -> dict:
    fresh = next(item for item in candidates(train, target) if item["name"] == record["name"])
    return fit(fresh, train, target)


def calibrate(raw: np.ndarray, y: pd.Series) -> tuple[str, ProbabilityCalibrator, np.ndarray]:
    y_array = np.asarray(y).astype(int)
    positives = int(y_array.sum())
    splits = min(5, positives, len(y_array) - positives)
    methods = ["none", "sigmoid"] + (["isotonic"] if splits >= 3 else [])
    comparisons = []
    oof_values: dict[str, np.ndarray] = {}
    for method in methods:
        if method == "none" or splits < 2:
            oof = np.clip(raw, 0, 1)
        else:
            oof = np.zeros(len(y_array))
            folds = StratifiedKFold(n_splits=splits, shuffle=True, random_state=RANDOM_SEED)
            for fit_index, score_index in folds.split(raw, y_array):
                fold = ProbabilityCalibrator(method).fit(raw[fit_index], y_array[fit_index])
                oof[score_index] = fold.transform(raw[score_index])
        metric = classification_metrics(y_array, oof, .5)
        comparisons.append((method, metric["brier"], metric["ece"]))
        oof_values[method] = oof
    method = min(comparisons, key=lambda row: (row[1], row[2]))[0]
    final = ProbabilityCalibrator(method)
    if method != "none":
        final.fit(raw, y_array)
    return method, final, oof_values[method]


def select_operating_threshold(y: pd.Series, probability: np.ndarray) -> float:
    quantiles = np.quantile(probability, np.linspace(0, 1, 101))
    table = threshold_table(y, probability, np.unique(np.r_[np.linspace(.001, .95, 250), quantiles]))
    best_f1 = table.f1.max()
    pool = table[table.f1 == best_f1]
    return float(pool.sort_values(["precision", "recall", "threshold"], ascending=[False, False, False]).iloc[0].threshold)


def feature_importance(record: dict, frame: pd.DataFrame, target: str) -> list[dict]:
    if record["kind"] == "dummy":
        return []
    if record["kind"] == "catboost":
        values = record["model"].get_feature_importance(Pool(prepare_cat(frame), label=frame[target], cat_features=CATEGORICAL))
        return [{"feature": feature, "importance": float(value)} for feature, value in sorted(zip(FEATURES, values), key=lambda item: item[1], reverse=True)[:12]]
    pipeline = record["model"]
    names = pipeline.named_steps["preprocess"].get_feature_names_out()
    estimator = pipeline.named_steps["model"]
    values = np.abs(estimator.coef_[0]) if record["kind"] == "logistic" else estimator.feature_importances_
    aggregate = {feature: 0.0 for feature in FEATURES}
    for transformed, value in zip(names, values):
        cleaned = transformed.split("__", 1)[-1]
        feature = next((candidate for candidate in FEATURES if cleaned == candidate or cleaned.startswith(candidate + "_")), cleaned)
        aggregate[feature] = aggregate.get(feature, 0.0) + float(value)
    return [{"feature": feature, "importance": value} for feature, value in sorted(aggregate.items(), key=lambda item: item[1], reverse=True)[:12]]


def status_for(task: Task, metrics: dict, prevalence: float) -> str:
    lift = metrics["pr_auc"] / prevalence if prevalence else 0
    if task.key == "delay_6m":
        if metrics["pr_auc"] >= .40 and lift >= 1.8 and metrics["roc_auc"] >= .72:
            return "GREEN"
        if metrics["pr_auc"] >= .28 and lift >= 1.35 and metrics["roc_auc"] >= .65:
            return "YELLOW"
        return "RED"
    if lift >= 5 and metrics["precision"] >= .15 and metrics["recall"] >= .25 and metrics["roc_auc"] >= .72:
        return "GREEN"
    if lift >= 2 and metrics["precision"] >= .05 and metrics["recall"] >= .15 and metrics["roc_auc"] >= .65:
        return "YELLOW"
    return "RED"


def split(task: Task, data: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    train = data[data.snapshot_month.between("2025-01", task.train_end)].copy()
    selection = data[data.snapshot_month.isin(task.selection_months)].copy()
    calibration = data[data.snapshot_month.isin(task.calibration_months)].copy()
    test = data[data.snapshot_month.isin(task.test_months)].copy()
    if not (train.snapshot_month.max() < selection.snapshot_month.min() <= selection.snapshot_month.max() < calibration.snapshot_month.min() < test.snapshot_month.min()):
        raise ValueError(f"Invalid chronological split for {task.key}")
    return train, selection, calibration, test


def train_task(task: Task) -> dict:
    data = add_v1_1_features(pd.read_csv(ROOT / "paimana_dataset_v3" / task.dataset))
    train, selection, calibration, test = split(task, data)
    comparisons = []
    for record in candidates(train, task.target):
        fit(record, train, task.target)
        metric = classification_metrics(selection[task.target], probabilities(record, selection), .5)
        record["validation_metrics"] = metric
        comparisons.append(record)
    selected = max(comparisons, key=lambda row: (row["validation_metrics"]["pr_auc"], -row["validation_metrics"]["brier"]))
    fit_frame = pd.concat([train, selection], ignore_index=True)
    final = clone_selected(selected, fit_frame, task.target)
    raw_calibration = probabilities(final, calibration)
    calibration_method, calibrator, validation_probability = calibrate(raw_calibration, calibration[task.target])
    threshold = select_operating_threshold(calibration[task.target], validation_probability)

    # The model, calibration, and operating threshold are frozen before this line.
    test_probability = calibrator.transform(probabilities(final, test))
    test_metrics = classification_metrics(test[task.target], test_probability, threshold)
    prevalence = float(data[task.target].mean())
    test_prevalence = float(test[task.target].mean())
    status = status_for(task, test_metrics, test_prevalence)
    importance = feature_importance(final, fit_frame, task.target)
    result = {
        "task": task.key,
        "target": task.target,
        "rows": int(len(data)),
        "projects": int(data.canonical_project_id.nunique()),
        "positives": int(data[task.target].sum()),
        "prevalence": prevalence,
        "test_prevalence": test_prevalence,
        "split": {"train": sorted(train.snapshot_month.unique().tolist()), "selection": list(task.selection_months), "calibration": list(task.calibration_months), "test": list(task.test_months)},
        "selected_model": selected["name"],
        "validation_pr_auc": selected["validation_metrics"]["pr_auc"],
        "calibration_method": calibration_method,
        "operating_threshold": threshold,
        "test_metrics": test_metrics,
        "pr_auc_lift": test_metrics["pr_auc"] / test_prevalence if test_prevalence else None,
        "feature_importance": importance,
        "status": status,
        "candidate_validation_metrics": [{"model": row["name"], **row["validation_metrics"]} for row in comparisons],
    }
    bundle = {
        "model_version": task.model_version,
        "model_name": selected["name"],
        "model_type": selected["kind"],
        "target": task.target,
        "features": FEATURES,
        "categorical_features": CATEGORICAL,
        "model": final["model"],
        "calibrator": calibrator,
        "threshold": threshold,
        "status": status,
        "metadata": {key: value for key, value in result.items() if key not in {"candidate_validation_metrics", "feature_importance"}},
        "global_importance": importance,
    }
    joblib.dump(bundle, MODEL_DIR / task.bundle_name)
    (REPORT_DIR / f"{task.key}_result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    pd.DataFrame(result["candidate_validation_metrics"]).to_csv(REPORT_DIR / f"{task.key}_model_comparison.csv", index=False)
    m = test_metrics
    caveat = "Cost escalation modelling remains experimental due to event sparsity." if task.key.startswith("cost") and status != "GREEN" else "The model is a predictive association, not a causal assessment."
    report = f"""# {task.model_version} final model report

## Decision

- Status: **{status}**
- Selected on validation only: **{selected['name']}**
- Validation PR-AUC: **{selected['validation_metrics']['pr_auc']:.4f}**
- Calibration: **{calibration_method}**
- Operating threshold: **{threshold:.6f}**

## Untouched temporal test

| Metric | Value |
|---|---:|
| Overall target prevalence | {prevalence:.4f} |
| Test baseline prevalence | {test_prevalence:.4f} |
| PR-AUC | {m['pr_auc']:.4f} |
| PR-AUC lift | {result['pr_auc_lift']:.2f}x |
| ROC-AUC | {m['roc_auc']:.4f} |
| Precision | {m['precision']:.4f} |
| Recall | {m['recall']:.4f} |
| F1 | {m['f1']:.4f} |
| Balanced accuracy | {m['balanced_accuracy']:.4f} |
| False-positive rate | {m['false_positive_rate']:.4f} |
| Alerts generated | {m['alerts_generated']} |
| Brier score | {m['brier']:.4f} |
| ECE | {m['ece']:.4f} |

{caveat}
"""
    (REPORT_DIR / task.report_name).write_text(report, encoding="utf-8")
    print(json.dumps({"task": task.key, "selected_model": selected["name"], "validation_pr_auc": result["validation_pr_auc"], "test_metrics": test_metrics, "status": status}, indent=2))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("tasks", nargs="+", choices=TASKS)
    args = parser.parse_args()
    np.random.seed(RANDOM_SEED)
    for key in args.tasks:
        train_task(TASKS[key])


if __name__ == "__main__":
    main()
