from __future__ import annotations

import numpy as np
import pandas as pd
import shap
from catboost import Pool

from ml.features.feature_registry import ALLOWED_FEATURES, CATEGORICAL_FEATURES
from ml.features.preprocessing import prepare_catboost


def catboost_shap(model, frame, max_rows=1000):
    sample = prepare_catboost(frame[ALLOWED_FEATURES].sample(min(max_rows, len(frame)), random_state=26103))
    pool = Pool(sample, cat_features=CATEGORICAL_FEATURES)
    raw = model.get_feature_importance(pool, type="ShapValues")
    explanation = shap.Explanation(values=raw[:, :-1], base_values=raw[:, -1], data=sample.to_numpy(), feature_names=ALLOWED_FEATURES)
    importance = [{"feature": feature, "importance": float(value)} for feature, value in zip(ALLOWED_FEATURES, np.abs(raw[:, :-1]).mean(axis=0))]
    return None, sample, explanation, sorted(importance, key=lambda x: x["importance"], reverse=True)


def xgboost_shap(pipeline, frame, max_rows=1000):
    sample = frame[ALLOWED_FEATURES].sample(min(max_rows, len(frame)), random_state=26103)
    transformed = pipeline.named_steps["preprocess"].transform(sample); names = pipeline.named_steps["preprocess"].get_feature_names_out()
    if hasattr(transformed, "toarray"): transformed = transformed.toarray()
    explainer = shap.TreeExplainer(pipeline.named_steps["model"]); explanation = explainer(transformed)
    importance = [{"feature": name, "importance": float(value)} for name, value in zip(names, np.abs(explanation.values).mean(axis=0))]
    return explainer, pd.DataFrame(transformed, columns=names), explanation, sorted(importance, key=lambda x: x["importance"], reverse=True)


def local_driver_records(feature_names, shap_values, row_values, top_n=5):
    records = [{"feature": str(n), "contribution": float(c), "value": v} for n, c, v in zip(feature_names, shap_values, row_values)]
    risks = sorted((r for r in records if r["contribution"] > 0), key=lambda r: r["contribution"], reverse=True)[:top_n]
    protective = sorted((r for r in records if r["contribution"] < 0), key=lambda r: r["contribution"])[:top_n]
    return risks, protective
