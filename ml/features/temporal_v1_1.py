"""Leakage-safe Model V1.1 features derived from frozen observations through t."""
from __future__ import annotations

from collections import defaultdict

import numpy as np
import pandas as pd

from ml.config import RAW_DATASET

V1_1_FEATURES = [
    "progress_acceleration_1m",
    "months_since_meaningful_progress",
    "target_revisions_last_3m",
    "months_since_target_revision",
    "expenditure_velocity_pct_3m",
    "expenditure_progress_velocity_gap_3m",
    "required_progress_per_remaining_month",
    "peer_relative_progress_pct",
]


def _month_number(value: str) -> int:
    year, month = map(int, value.split("-"))
    return year * 12 + month


def build_temporal_features(raw_path=RAW_DATASET) -> pd.DataFrame:
    columns = [
        "canonical_project_id", "snapshot_month", "sector", "current_target_doc",
        "current_forecast_cost_cr", "cumulative_expenditure_cr", "physical_progress_pct",
    ]
    raw = pd.read_csv(raw_path, usecols=columns)
    raw["month_number"] = raw.snapshot_month.map(_month_number)
    records = []
    for project_id, sequence in raw.groupby("canonical_project_id", sort=False):
        sequence = sequence.sort_values("month_number")
        by_month = {int(row.month_number): row for row in sequence.itertuples(index=False)}
        last_progress_month = None
        last_revision_month = None
        revision_months = []
        for row in sequence.itertuples(index=False):
            month = int(row.month_number)
            prior1, prior2, prior3 = by_month.get(month - 1), by_month.get(month - 2), by_month.get(month - 3)
            progress = row.physical_progress_pct
            acceleration = np.nan
            if prior1 is not None and prior2 is not None and pd.notna(progress) and pd.notna(prior1.physical_progress_pct) and pd.notna(prior2.physical_progress_pct):
                acceleration = (progress - prior1.physical_progress_pct) - (prior1.physical_progress_pct - prior2.physical_progress_pct)
            if prior1 is not None and pd.notna(progress) and pd.notna(prior1.physical_progress_pct) and progress - prior1.physical_progress_pct >= 0.5:
                last_progress_month = month
            months_since_progress = np.nan if last_progress_month is None else month - last_progress_month

            if prior1 is not None and pd.notna(row.current_target_doc) and pd.notna(prior1.current_target_doc) and str(row.current_target_doc) != str(prior1.current_target_doc):
                last_revision_month = month
                revision_months.append(month)
            recent_revisions = sum(month - 2 <= revision <= month for revision in revision_months)
            months_since_revision = np.nan if last_revision_month is None else month - last_revision_month

            expenditure_velocity_pct = np.nan
            if prior3 is not None and pd.notna(row.cumulative_expenditure_cr) and pd.notna(prior3.cumulative_expenditure_cr) and pd.notna(row.current_forecast_cost_cr) and row.current_forecast_cost_cr > 0:
                expenditure_velocity_pct = 100 * (row.cumulative_expenditure_cr - prior3.cumulative_expenditure_cr) / row.current_forecast_cost_cr / 3
            progress_velocity = np.nan
            if prior3 is not None and pd.notna(progress) and pd.notna(prior3.physical_progress_pct):
                progress_velocity = (progress - prior3.physical_progress_pct) / 3
            velocity_gap = expenditure_velocity_pct - progress_velocity if pd.notna(expenditure_velocity_pct) and pd.notna(progress_velocity) else np.nan

            records.append({
                "canonical_project_id": project_id, "snapshot_month": row.snapshot_month,
                "progress_acceleration_1m": acceleration,
                "months_since_meaningful_progress": months_since_progress,
                "target_revisions_last_3m": recent_revisions,
                "months_since_target_revision": months_since_revision,
                "expenditure_velocity_pct_3m": expenditure_velocity_pct,
                "expenditure_progress_velocity_gap_3m": velocity_gap,
            })
    features = pd.DataFrame(records)
    peer = raw.groupby(["snapshot_month", "sector"], dropna=False).physical_progress_pct.transform("median")
    peer_frame = raw[["canonical_project_id", "snapshot_month"]].copy()
    peer_frame["peer_relative_progress_pct"] = raw.physical_progress_pct - peer
    features = features.merge(peer_frame, on=["canonical_project_id", "snapshot_month"], how="left", validate="one_to_one")
    return features


def add_v1_1_features(data: pd.DataFrame) -> pd.DataFrame:
    result = data.merge(build_temporal_features(), on=["canonical_project_id", "snapshot_month"], how="left", validate="one_to_one")
    remaining = pd.to_numeric(result["months_to_target"], errors="coerce")
    progress = pd.to_numeric(result["physical_progress_pct"], errors="coerce")
    result["required_progress_per_remaining_month"] = np.where(remaining > 0, (100 - progress) / remaining, np.nan)
    return result
