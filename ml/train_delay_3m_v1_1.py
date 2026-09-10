"""One focused, leakage-safe improvement pass for PAIMANA Sentinel Model V1.1."""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier, Pool
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBClassifier

from ml.config import ARTIFACTS, MODEL_DIR, RANDOM_SEED, REPORT_DIR, TARGET
from ml.data.loader import load_delay_data
from ml.data.splitting import temporal_split, unseen_project_test
from ml.evaluation.metrics import classification_metrics
from ml.evaluation.thresholding import select_thresholds, threshold_table
from ml.features.feature_registry import ALLOWED_FEATURES, CATEGORICAL_FEATURES, NUMERICAL_FEATURES
from ml.features.temporal_v1_1 import V1_1_FEATURES, add_v1_1_features
from ml.models.calibration import ProbabilityCalibrator

FEATURES = ALLOWED_FEATURES + V1_1_FEATURES
NUMERICAL = NUMERICAL_FEATURES + V1_1_FEATURES
CATEGORICAL = CATEGORICAL_FEATURES
V1 = {"pr_auc": .5526976957562444, "brier": .1946374025979912, "ece": .1580004486072721, "unseen_recall": .17647058823529413}


def preprocessor(scale=False):
    numeric_steps = [("impute", SimpleImputer(strategy="median"))]
    if scale: numeric_steps.append(("scale", StandardScaler()))
    return ColumnTransformer([
        ("numeric", Pipeline(numeric_steps), NUMERICAL),
        ("categorical", Pipeline([("impute", SimpleImputer(strategy="most_frequent")), ("onehot", OneHotEncoder(handle_unknown="ignore", min_frequency=3))]), CATEGORICAL),
    ])


def prepare_cat(frame):
    output = frame[FEATURES].copy()
    for column in CATEGORICAL: output[column] = output[column].fillna("__MISSING__").astype(str)
    return output


def make_record(name, kind, config):
    if kind == "logistic":
        model = Pipeline([("preprocess", preprocessor(True)), ("model", LogisticRegression(max_iter=3000, random_state=RANDOM_SEED, **config))])
    elif kind == "catboost":
        model = CatBoostClassifier(loss_function="Logloss", eval_metric="PRAUC", random_seed=RANDOM_SEED, verbose=False, allow_writing_files=False, thread_count=-1, **config)
    else:
        model = Pipeline([("preprocess", preprocessor(False)), ("model", XGBClassifier(objective="binary:logistic", eval_metric="logloss", random_state=RANDOM_SEED, n_jobs=-1, **config))])
    return {"name": name, "kind": kind, "config": config, "model": model}


def fit(record, train, evaluation=None):
    if record["kind"] == "catboost":
        kwargs = {"cat_features": CATEGORICAL, "verbose": False}
        if evaluation is not None:
            kwargs.update({"eval_set": (prepare_cat(evaluation), evaluation[TARGET]), "early_stopping_rounds": 60})
        record["model"].fit(prepare_cat(train), train[TARGET], **kwargs)
    else:
        record["model"].fit(train[FEATURES], train[TARGET])
    return record


def probability(record, frame):
    if record["kind"] == "catboost": return record["model"].predict_proba(prepare_cat(frame))[:, 1]
    return record["model"].predict_proba(frame[FEATURES])[:, 1]


def candidates(train):
    ratio = float((len(train) - train[TARGET].sum()) / train[TARGET].sum())
    output = []
    for weight in (None, "balanced"):
        for c in (.1, 1.0): output.append(make_record(f"Logistic_{weight or 'unweighted'}_C{c}", "logistic", {"C": c, "class_weight": weight}))
    for index, config in enumerate([
        {"iterations": 550, "depth": 5, "learning_rate": .04, "l2_leaf_reg": 7},
        {"iterations": 650, "depth": 6, "learning_rate": .035, "l2_leaf_reg": 9},
        {"iterations": 550, "depth": 5, "learning_rate": .04, "l2_leaf_reg": 7, "class_weights": [1, ratio]},
    ], 1): output.append(make_record(f"CatBoost_{index}", "catboost", config))
    for index, config in enumerate([
        {"n_estimators": 500, "max_depth": 3, "learning_rate": .04, "min_child_weight": 5, "subsample": .85, "colsample_bytree": .85},
        {"n_estimators": 600, "max_depth": 4, "learning_rate": .035, "min_child_weight": 5, "subsample": .85, "colsample_bytree": .85},
        {"n_estimators": 500, "max_depth": 3, "learning_rate": .04, "min_child_weight": 5, "subsample": .85, "colsample_bytree": .85, "scale_pos_weight": ratio},
    ], 1): output.append(make_record(f"XGBoost_{index}", "xgboost", config))
    return output


def cross_fitted_calibration(raw, y):
    raw, y = np.asarray(raw), np.asarray(y)
    folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_SEED)
    comparisons, oof_by_method = [], {}
    for method in ("none", "sigmoid", "isotonic"):
        oof = np.zeros(len(y))
        if method == "none": oof[:] = raw
        else:
            for fit_idx, score_idx in folds.split(raw, y):
                calibrator = ProbabilityCalibrator(method).fit(raw[fit_idx], y[fit_idx])
                oof[score_idx] = calibrator.transform(raw[score_idx])
        metrics = classification_metrics(y, oof, .5)
        comparisons.append({"method": method, **metrics}); oof_by_method[method] = oof
    chosen = min(comparisons, key=lambda row: (row["brier"], row["ece"]))["method"]
    final = ProbabilityCalibrator(chosen)
    if chosen != "none": final.fit(raw, y)
    table = threshold_table(y, oof_by_method[chosen]); thresholds = select_thresholds(table)
    return chosen, final, comparisons, thresholds


def refit_selected(selected, fit_frame):
    config = dict(selected["config"])
    if selected["kind"] == "catboost":
        best = selected["model"].get_best_iteration()
        if best and best > 0: config["iterations"] = best + 1
    final = make_record(selected["name"], selected["kind"], config)
    return fit(final, fit_frame)


def top_features(record, fit_frame):
    if record["kind"] == "catboost":
        pool = Pool(prepare_cat(fit_frame), label=fit_frame[TARGET], cat_features=CATEGORICAL)
        values = record["model"].get_feature_importance(pool)
        return [name for name, _ in sorted(zip(FEATURES, values), key=lambda item: item[1], reverse=True)[:10]]
    pipeline = record["model"]; names = pipeline.named_steps["preprocess"].get_feature_names_out()
    if record["kind"] == "logistic": values = np.abs(pipeline.named_steps["model"].coef_[0])
    else: values = pipeline.named_steps["model"].feature_importances_
    aggregates = {feature: 0.0 for feature in FEATURES}
    for transformed, value in zip(names, values):
        cleaned = transformed.split("__", 1)[-1]
        match = next((feature for feature in FEATURES if cleaned == feature or cleaned.startswith(feature + "_")), cleaned)
        aggregates[match] = aggregates.get(match, 0.0) + float(value)
    return [name for name, _ in sorted(aggregates.items(), key=lambda item: item[1], reverse=True)[:10]]


def main():
    np.random.seed(RANDOM_SEED)
    data = add_v1_1_features(load_delay_data())
    train, validation, test = temporal_split(data)
    selection = validation[validation.snapshot_month.isin(["2025-09", "2025-10"])].copy()
    calibration = validation[validation.snapshot_month.eq("2025-11")].copy()

    records = []
    for record in candidates(train):
        fit(record, train, selection if record["kind"] == "catboost" else None)
        p = probability(record, selection)
        record["selection_metrics"] = classification_metrics(selection[TARGET], p, .5)
        records.append(record)
    selected = max(records, key=lambda row: (row["selection_metrics"]["pr_auc"], -row["selection_metrics"]["brier"]))

    fit_frame = pd.concat([train, selection], ignore_index=True)
    final = refit_selected(selected, fit_frame)
    calibration_raw = probability(final, calibration)
    calibration_method, calibrator, calibration_comparison, thresholds = cross_fitted_calibration(calibration_raw, calibration[TARGET])

    # Frozen test is accessed only after model/config/calibration/thresholds are fixed.
    test_raw = probability(final, test); test_probability = calibrator.transform(test_raw)
    metrics = classification_metrics(test[TARGET], test_probability, thresholds["BALANCED"])
    unseen = unseen_project_test(train, validation, test)
    unseen_probability = calibrator.transform(probability(final, unseen))
    unseen_metrics = classification_metrics(unseen[TARGET], unseen_probability, thresholds["BALANCED"])

    high_train = fit_frame[fit_frame.data_quality_score >= 80]
    high_calibration = calibration[calibration.data_quality_score >= 80]
    high_test = test[test.data_quality_score >= 80]
    high_model = refit_selected(selected, high_train)
    high_raw = probability(high_model, high_calibration)
    high_calibrator = ProbabilityCalibrator(calibration_method)
    if calibration_method != "none": high_calibrator.fit(high_raw, high_calibration[TARGET])
    high_probability = high_calibrator.transform(probability(high_model, high_test))
    high_pr_auc = float(average_precision_score(high_test[TARGET], high_probability))

    monthly = []
    for month, indices in test.groupby("snapshot_month").groups.items():
        idx = test.index.get_indexer(indices); group = test.loc[indices]
        monthly.append({"month": month, **classification_metrics(group[TARGET], test_probability[idx], thresholds["BALANCED"])})
    top10 = top_features(final, fit_frame)

    improvements = sum([
        metrics["pr_auc"] >= V1["pr_auc"] + .01,
        metrics["brier"] <= V1["brier"] - .01,
        metrics["ece"] <= V1["ece"] - .03,
        unseen_metrics["recall"] >= V1["unseen_recall"] + .05,
    ])
    if improvements >= 3 and metrics["pr_auc"] >= .5608:
        status = "GREEN"
    elif metrics["pr_auc"] >= .53 and metrics["roc_auc"] >= .75 and metrics["brier"] <= .21:
        status = "YELLOW"
    else:
        status = "RED"

    artifact = {
        "model_version": "delay_3m_v1_1", "model_name": selected["name"], "model_type": selected["kind"],
        "features": FEATURES, "model": final["model"], "calibrator": calibrator, "thresholds": thresholds,
    }
    joblib.dump(artifact, MODEL_DIR / "delay_3m_v1_1_bundle.joblib")
    result = {
        "selected_model": selected["name"], "selection_validation_months": ["2025-09", "2025-10"],
        "calibration_month": "2025-11", "calibration_method": calibration_method,
        "validation_pr_auc": selected["selection_metrics"]["pr_auc"], "test_metrics": metrics,
        "unseen_project_metrics": unseen_metrics, "high_quality_subset_pr_auc": high_pr_auc,
        "top_10_features": top10, "temporal_stability": monthly, "calibration_comparison": calibration_comparison,
        "status": status,
    }
    (REPORT_DIR / "v1_1_result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(f"V1.1 BEST MODEL: {selected['name']}")
    print(f"Validation PR-AUC: {selected['selection_metrics']['pr_auc']:.4f}")
    print(f"Test PR-AUC: {metrics['pr_auc']:.4f}")
    print(f"Test ROC-AUC: {metrics['roc_auc']:.4f}")
    print(f"Precision: {metrics['precision']:.4f}")
    print(f"Recall: {metrics['recall']:.4f}")
    print(f"F1: {metrics['f1']:.4f}")
    print(f"Brier: {metrics['brier']:.4f}")
    print(f"ECE: {metrics['ece']:.4f}")
    print(f"Unseen-project PR-AUC: {unseen_metrics['pr_auc']:.4f}")
    print(f"Unseen-project Recall: {unseen_metrics['recall']:.4f}")
    print(f"High-quality subset PR-AUC: {high_pr_auc:.4f}")
    print("Top 10 features: " + ", ".join(top10))
    print(f"MODEL_V1_1_STATUS={status}")


if __name__ == "__main__": main()
