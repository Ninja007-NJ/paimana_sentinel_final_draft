from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap
from catboost import Pool

from ml.config import MODEL_DIR, MODEL_VERSION, PREDICTION_DIR
from ml.data.loader import load_prediction_input
from ml.data.validation import validate_prediction_data
from ml.evaluation.thresholding import risk_level
from ml.explainability.explanation_formatter import format_explanation
from ml.explainability.shap_explainer import local_driver_records
from ml.features.feature_registry import ALLOWED_FEATURES, CATEGORICAL_FEATURES
from ml.features.preprocessing import prepare_catboost

DEFAULT_BUNDLE = MODEL_DIR / "delay_3m_model_bundle_v1.joblib"


def _confidence(row):
    quality = float(row.get("data_quality_score", 0) or 0)
    missing = float(row.get("missing_core_fields_count", 0) or 0)
    if quality >= 90 and missing == 0: return "HIGH"
    if quality >= 80 and missing <= 1: return "MEDIUM"
    return "LOW"


def _raw_and_drivers(bundle, frame):
    X = frame[ALLOWED_FEATURES]
    if bundle.model_type == "catboost":
        prepared = prepare_catboost(X)
        raw_probability = bundle.model.predict_proba(prepared)[:, 1]
        pool = Pool(prepared, cat_features=CATEGORICAL_FEATURES)
        values = bundle.model.get_feature_importance(pool, type="ShapValues")[:, :-1]
        names, observed = ALLOWED_FEATURES, prepared.to_numpy()
    elif bundle.model_type == "xgboost":
        raw_probability = bundle.model.predict_proba(X)[:, 1]
        transformed = bundle.model.named_steps["preprocess"].transform(X)
        if hasattr(transformed, "toarray"): transformed = transformed.toarray()
        names = bundle.model.named_steps["preprocess"].get_feature_names_out()
        values = shap.TreeExplainer(bundle.model.named_steps["model"])(transformed).values
        observed = transformed
    else:
        raw_probability = bundle.model.predict_proba(X)[:, 1]
        transformed = bundle.model.named_steps["preprocess"].transform(X)
        if hasattr(transformed, "toarray"): transformed = transformed.toarray()
        names = bundle.model.named_steps["preprocess"].get_feature_names_out()
        values = transformed * bundle.model.named_steps["model"].coef_[0]
        observed = transformed
    return raw_probability, names, values, observed


def predict_delay_risk(project_row, bundle_path=DEFAULT_BUNDLE, threshold_profile="BALANCED"):
    bundle = joblib.load(bundle_path)
    frame = project_row.copy() if isinstance(project_row, pd.DataFrame) else pd.DataFrame([project_row])
    validate_prediction_data(frame)
    raw, names, shap_values, observed = _raw_and_drivers(bundle, frame)
    calibrated = bundle.calibrator.transform(raw)
    results = []
    for index, probability in enumerate(calibrated):
        risks, protective = local_driver_records(names, shap_values[index], observed[index])
        explanation = format_explanation(risks, protective)
        results.append({
            "delay_probability_3m": round(float(probability), 6),
            "baseline_risk": round(float(bundle.metadata.get("training_prevalence", 0)), 6),
            "risk_level": risk_level(float(probability), bundle.thresholds),
            "threshold_profile": threshold_profile,
            **explanation,
            "data_quality_score": None if pd.isna(frame.iloc[index].get("data_quality_score")) else float(frame.iloc[index].get("data_quality_score")),
            "model_confidence": _confidence(frame.iloc[index]),
            "model_version": bundle.model_version,
            "prediction_metadata": {"dataset_version": bundle.dataset_version, "selected_threshold": bundle.thresholds[threshold_profile]},
        })
    return results[0] if len(results) == 1 else results


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--input", required=True); parser.add_argument("--output"); parser.add_argument("--profile", default="BALANCED", choices=["EARLY_WARNING", "BALANCED", "CONSERVATIVE"])
    args = parser.parse_args(); frame = load_prediction_input(args.input); results = predict_delay_risk(frame, threshold_profile=args.profile)
    output = Path(args.output) if args.output else PREDICTION_DIR / "delay_3m_predictions.json"
    output.write_text(json.dumps(results, indent=2), encoding="utf-8"); print(json.dumps(results, indent=2)); print(f"Saved: {output}")


if __name__ == "__main__": main()
