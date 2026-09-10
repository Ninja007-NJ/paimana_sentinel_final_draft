from __future__ import annotations

import joblib
import numpy as np
import pandas as pd
from catboost import Pool

from backend.config import DEFAULT_THRESHOLD_PROFILE, DELAY_6M_MODEL_BUNDLE, MODEL_BUNDLE
from backend.confidence_service import ConfidenceService
from backend.explanation_service import ExplanationService
from ml.evaluation.thresholding import risk_level as frozen_risk_level


class ModelService:
    def __init__(self, bundle_path=MODEL_BUNDLE):
        if not bundle_path.exists():
            raise FileNotFoundError(f"Frozen V1.1 model bundle not found: {bundle_path}")
        bundle = joblib.load(bundle_path)
        if bundle.get("model_version") != "delay_3m_v1_1" or bundle.get("model_type") != "catboost":
            raise RuntimeError("Unexpected model artifact; Phase 2 requires frozen V1.1 CatBoost")
        self.bundle = bundle
        self.model = bundle["model"]
        self.calibrator = bundle["calibrator"]
        self.thresholds = bundle["thresholds"]
        self.features = bundle["features"]
        self.model_version = bundle["model_version"]
        self.categorical = [feature for feature in ("sector", "state", "ministry_department") if feature in self.features]
        self.explanations = ExplanationService()
        self.confidence: ConfidenceService | None = None
        self.delay_6m_bundle = joblib.load(DELAY_6M_MODEL_BUNDLE)
        if self.delay_6m_bundle.get("model_version") != "delay_6m_v1" or self.delay_6m_bundle.get("status") not in {"GREEN", "YELLOW"}:
            raise RuntimeError("The 6-month delay model is missing or not accepted for product use")
        self.delay_6m_status = self.delay_6m_bundle["status"]

    def configure_confidence(self, reference: pd.DataFrame, identity_sources: dict[str, str]):
        self.confidence = ConfidenceService(reference, self.features, identity_sources)

    def prepare(self, frame: pd.DataFrame) -> pd.DataFrame:
        missing = set(self.features) - set(frame.columns)
        if missing:
            raise ValueError(f"Missing model features: {sorted(missing)}")
        output = frame[self.features].copy()
        for column in self.categorical:
            output[column] = output[column].fillna("__MISSING__").astype(str)
        return output

    def probabilities(self, frame: pd.DataFrame) -> np.ndarray:
        prepared = self.prepare(frame)
        raw = self.model.predict_proba(prepared)[:, 1]
        return np.clip(self.calibrator.transform(raw), 0, 1)

    def probabilities_6m(self, frame: pd.DataFrame) -> np.ndarray:
        bundle = self.delay_6m_bundle
        features = bundle["features"]
        missing = set(features) - set(frame.columns)
        if missing:
            raise ValueError(f"Missing 6-month model features: {sorted(missing)}")
        prepared = frame[features].copy()
        for column in bundle["categorical_features"]:
            prepared[column] = prepared[column].fillna("__MISSING__").astype(str)
        raw = bundle["model"].predict_proba(prepared)[:, 1]
        return np.clip(bundle["calibrator"].transform(raw), 0, 1)

    def risk_level(self, probability: float) -> str:
        return frozen_risk_level(probability, self.thresholds)

    def shap_values(self, frame: pd.DataFrame) -> np.ndarray:
        prepared = self.prepare(frame)
        pool = Pool(prepared, cat_features=self.categorical)
        return self.model.get_feature_importance(pool, type="ShapValues")[:, :-1]

    def predict_one(self, row: pd.Series, project_id: str | None = None, threshold_profile=DEFAULT_THRESHOLD_PROFILE, explain=True) -> dict:
        frame = pd.DataFrame([row])
        probability = float(self.probabilities(frame)[0])
        if explain:
            values = self.shap_values(frame)[0]
            risk_drivers, protective_drivers, sentence = self.explanations.format(self.features, values, row)
        else:
            risk_drivers, protective_drivers, sentence = [], [], ""
        confidence = self.confidence.evaluate(row, project_id) if self.confidence else {"level": "LOW", "score": 0, "missing_feature_count": 0, "out_of_range_feature_count": 0, "fallback_identity": False}
        return {
            "delay_probability_3m": probability,
            "delay_probability_6m": float(self.probabilities_6m(frame)[0]),
            "delay_6m_model_status": self.delay_6m_status,
            "risk_level": self.risk_level(probability),
            "threshold_profile": str(getattr(threshold_profile, "value", threshold_profile)),
            "top_risk_drivers": risk_drivers,
            "top_protective_drivers": protective_drivers,
            "data_quality_score": float(row.get("data_quality_score", 0)),
            "prediction_confidence": confidence,
            "model_version": self.model_version,
            "explanation_sentence": sentence,
        }
