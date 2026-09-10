from __future__ import annotations

import numpy as np
import pandas as pd


class ConfidenceService:
    """Data-reliability score, deliberately separate from model probability."""

    def __init__(self, reference: pd.DataFrame, features: list[str], identity_sources: dict[str, str]):
        self.features = features
        self.identity_sources = identity_sources
        numeric = reference[features].select_dtypes(include=[np.number])
        self.lower = numeric.quantile(.01)
        self.upper = numeric.quantile(.99)
        self.numeric_features = list(numeric.columns)

    def evaluate(self, row: pd.Series, project_id: str | None = None) -> dict:
        missing = int(row[self.features].isna().sum())
        outside = 0
        for feature in self.numeric_features:
            value = row.get(feature)
            if pd.notna(value) and (value < self.lower[feature] or value > self.upper[feature]):
                outside += 1
        identity_source = self.identity_sources.get(project_id or "", "")
        fallback = identity_source in {"FALLBACK_GENERATED", "AMBIGUOUS_COLLISION"}
        quality = float(row.get("data_quality_score", 0) or 0)
        completeness = 1 - missing / max(len(self.features), 1)
        score = .65 * quality + 35 * completeness - min(20, outside * 2) - (15 if fallback else 0)
        score = round(float(np.clip(score, 0, 100)), 2)
        level = "HIGH" if score >= 85 else ("MEDIUM" if score >= 65 else "LOW")
        return {"level": level, "score": score, "missing_feature_count": missing, "out_of_range_feature_count": outside, "fallback_identity": fallback}
