from __future__ import annotations

import pandas as pd

from ml.config import TARGET
from ml.features.feature_registry import ALLOWED_FEATURES


def validate_training_data(data: pd.DataFrame) -> None:
    required = {"canonical_project_id", "snapshot_month", TARGET, *ALLOWED_FEATURES}
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"Missing training columns: {sorted(missing)}")
    if data.duplicated(["canonical_project_id", "snapshot_month"]).any():
        raise ValueError("Duplicate project-month observations found")
    if not set(data[TARGET].dropna().unique()).issubset({0, 1}):
        raise ValueError("Target must be binary")


def validate_prediction_data(data: pd.DataFrame) -> None:
    missing = set(ALLOWED_FEATURES) - set(data.columns)
    if missing:
        raise ValueError(f"Missing prediction features: {sorted(missing)}")
    forbidden = [column for column in data.columns if column.startswith("delay_event_next_") or column.startswith("future_coverage_")]
    if forbidden:
        raise ValueError(f"Prediction input contains forbidden outcome columns: {forbidden}")
