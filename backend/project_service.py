from __future__ import annotations

import math
from datetime import date, datetime
from typing import Any

import numpy as np
import pandas as pd

from backend.config import IDENTITY_AUDIT, RAW_SNAPSHOTS, TRAINING_DATA, TRAINING_MASTER
from backend.model_service import ModelService
from ml.features.temporal_v1_1 import add_v1_1_features


def clean_value(value):
    if value is None:
        return None
    if isinstance(value, dict):
        return {str(key): clean_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean_value(item) for item in value]
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()
    if not isinstance(value, str):
        try:
            if pd.isna(value):
                return None
        except (TypeError, ValueError):
            pass
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, np.integer): return int(value)
    if isinstance(value, (np.floating, float)):
        number = float(value)
        return number if math.isfinite(number) else None
    return value


class ProjectService:
    def __init__(self, model_service: ModelService):
        self.model_service = model_service
        master = pd.read_csv(TRAINING_MASTER)
        features = add_v1_1_features(master)
        raw_columns = [
            "canonical_project_id", "snapshot_month", "project_name", "agency",
            "reporting_regime", "current_target_doc", "current_forecast_cost_cr",
            "cumulative_expenditure_cr", "quality_flags", "identity_confidence",
            "original_cost_cr", "revised_cost_cr", "anticipated_cost_cr",
            "original_doc", "revised_doc", "anticipated_doc", "current_target_source",
        ]
        raw = pd.read_csv(RAW_SNAPSHOTS, usecols=raw_columns)
        self.frame = features.merge(raw, on=["canonical_project_id", "snapshot_month"], how="left", validate="one_to_one")
        self.frame.sort_values(["canonical_project_id", "snapshot_month"], inplace=True)
        self.frame["predicted_delay_probability_3m"] = self.model_service.probabilities(self.frame)
        self.frame["risk_level"] = self.frame["predicted_delay_probability_3m"].map(self.model_service.risk_level)
        self.frame["risk_change_1m"] = self.frame.groupby("canonical_project_id")["predicted_delay_probability_3m"].diff()

        identity = pd.read_csv(IDENTITY_AUDIT)
        self.identity_records = identity.set_index("canonical_project_id").to_dict("index")
        self.identity_sources = identity.set_index("canonical_project_id")["identity_source"].to_dict()
        training_keys = pd.read_csv(TRAINING_DATA, usecols=["canonical_project_id", "snapshot_month"])
        training_keys = training_keys[training_keys.snapshot_month <= "2025-10"]
        reference = self.frame.merge(training_keys, on=["canonical_project_id", "snapshot_month"], how="inner", validate="one_to_one")
        self.model_service.configure_confidence(reference, self.identity_sources)

        latest = self.frame.groupby("canonical_project_id", sort=False).tail(1).copy()
        latest["latest_risk_score"] = latest["predicted_delay_probability_3m"]
        self.latest = latest.set_index("canonical_project_id", drop=False)
        self._list_cache = [
            {
                "canonical_project_id": row.canonical_project_id,
                "project_name": str(clean_value(row.project_name) or ""),
                "sector": clean_value(row.sector), "state": clean_value(row.state),
                "latest_snapshot_month": row.snapshot_month,
                "latest_risk_score": float(row.latest_risk_score),
                "risk_level": row.risk_level,
                "data_reliability_score": float(row.data_quality_score),
                "risk_change_1m": clean_value(row.risk_change_1m),
            }
            for row in latest.itertuples(index=False)
        ]

    def list_projects(self) -> list[dict]:
        return self._list_cache

    def rows_for_project(self, project_id: str) -> pd.DataFrame:
        rows = self.frame[self.frame.canonical_project_id == project_id].copy()
        if rows.empty:
            raise KeyError(project_id)
        return rows.sort_values("snapshot_month")

    def latest_row(self, project_id: str) -> pd.Series:
        if project_id not in self.latest.index:
            raise KeyError(project_id)
        return self.latest.loc[project_id]

    def metadata(self, project_id: str, row: pd.Series) -> dict:
        identity = self.identity_records.get(project_id, {})
        return {
            "project_name": clean_value(row.get("project_name")), "sector": clean_value(row.get("sector")),
            "state": clean_value(row.get("state")), "ministry_department": clean_value(row.get("ministry_department")),
            "agency": clean_value(row.get("agency")), "reporting_regime": clean_value(row.get("reporting_regime")),
            "identity_source": clean_value(identity.get("identity_source")), "identity_confidence": clean_value(identity.get("identity_confidence")),
        }

    def snapshot_record(self, row: pd.Series) -> dict:
        fields = [
            "snapshot_month", "current_target_doc", "current_forecast_cost_cr",
            "cumulative_expenditure_cr", "physical_progress_pct", "data_quality_score", "quality_flags",
            "original_cost_cr", "revised_cost_cr", "anticipated_cost_cr",
            "original_doc", "revised_doc", "anticipated_doc", "current_target_source",
        ]
        return {field: clean_value(row.get(field)) for field in fields}
