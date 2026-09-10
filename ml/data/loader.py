from __future__ import annotations

import pandas as pd

from ml.config import DATASET, IDENTITY_AUDIT, RAW_DATASET, TARGET


def load_delay_data(path=DATASET, enrich=True) -> pd.DataFrame:
    data = pd.read_csv(path)
    data["snapshot_month"] = data["snapshot_month"].astype(str)
    data[TARGET] = pd.to_numeric(data[TARGET], errors="raise").astype(int)
    if not enrich:
        return data
    raw_columns = [
        "canonical_project_id", "snapshot_month", "reporting_regime",
        "original_cost_cr", "current_forecast_cost_cr", "current_target_source",
        "current_cost_source", "quality_flags",
    ]
    raw = pd.read_csv(RAW_DATASET, usecols=raw_columns)
    data = data.merge(raw, on=["canonical_project_id", "snapshot_month"], how="left", validate="one_to_one")
    identity = pd.read_csv(IDENTITY_AUDIT, usecols=["canonical_project_id", "identity_source", "collision_flag"])
    data = data.merge(identity, on="canonical_project_id", how="left", validate="many_to_one")
    return data


def load_prediction_input(path) -> pd.DataFrame:
    return pd.read_csv(path)
