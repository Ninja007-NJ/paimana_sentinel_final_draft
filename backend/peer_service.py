from __future__ import annotations

import numpy as np
import pandas as pd

from backend.project_service import ProjectService, clean_value


MINIMUM_PEER_SIZE = 5


def cost_bucket(value) -> str:
    if pd.isna(value): return "UNKNOWN"
    value = float(value)
    if value < 100: return "UNDER_100_CR"
    if value < 500: return "100_500_CR"
    if value < 1000: return "500_1000_CR"
    if value < 5000: return "1000_5000_CR"
    return "OVER_5000_CR"


def age_bucket(value) -> str:
    if pd.isna(value): return "UNKNOWN"
    value = float(value)
    if value < 36: return "UNDER_3_YEARS"
    if value < 60: return "3_5_YEARS"
    if value < 120: return "5_10_YEARS"
    return "OVER_10_YEARS"


def progress_stage(value) -> str:
    if pd.isna(value): return "UNKNOWN"
    value = float(value)
    if value < 25: return "0_25_PCT"
    if value < 50: return "25_50_PCT"
    if value < 75: return "50_75_PCT"
    if value < 100: return "75_100_PCT"
    return "COMPLETE_OR_ABOVE"


def percentile(values: pd.Series, value) -> float | None:
    clean = values.dropna().astype(float)
    if pd.isna(value) or clean.empty: return None
    return round(float((clean <= float(value)).mean() * 100), 2)


class PeerService:
    def __init__(self, projects: ProjectService, minimum_peer_size: int = MINIMUM_PEER_SIZE):
        self.projects = projects
        self.minimum_peer_size = minimum_peer_size
        self.latest = projects.latest.copy()
        self.latest["cost_bucket"] = self.latest["current_forecast_cost_cr"].map(cost_bucket)
        self.latest["age_bucket"] = self.latest["project_age_months"].map(age_bucket)
        self.latest["progress_stage"] = self.latest["physical_progress_pct"].map(progress_stage)

    def _select(self, row: pd.Series) -> tuple[pd.DataFrame, dict]:
        dimensions = ["sector", "cost_bucket", "age_bucket", "progress_stage"]
        candidates = self.latest[self.latest.canonical_project_id != row.canonical_project_id]
        applied = []
        for dimension in dimensions:
            value = row.get(dimension)
            if pd.isna(value) or value in (None, "", "UNKNOWN"): continue
            trial = candidates[candidates[dimension] == value]
            if len(trial) >= self.minimum_peer_size:
                candidates = trial
                applied.append(dimension)
        ministry = row.get("ministry_department")
        if pd.notna(ministry):
            ministry_trial = candidates[candidates.ministry_department == ministry]
            if len(ministry_trial) >= self.minimum_peer_size:
                candidates = ministry_trial
                applied.append("ministry_department")
        definition = {dimension: clean_value(row.get(dimension)) for dimension in applied}
        return candidates.sort_index(), definition

    def compare(self, project_id: str) -> dict:
        row = self.latest.loc[project_id]
        peers, definition = self._select(row)
        available = len(peers) >= self.minimum_peer_size
        if not available:
            peers = peers.iloc[0:0]

        progress = clean_value(row.get("physical_progress_pct"))
        spend_ratio = clean_value(row.get("spend_ratio_pct"))
        risk = clean_value(row.get("predicted_delay_probability_3m"))
        progress_median = clean_value(peers.physical_progress_pct.median()) if available else None
        spend_median = clean_value(peers.spend_ratio_pct.median()) if available else None
        risk_median = clean_value(peers.predicted_delay_probability_3m.median()) if available else None
        difference = None if progress is None or progress_median is None else round(float(progress - progress_median), 2)
        return {
            "canonical_project_id": project_id,
            "available": available,
            "peer_definition": definition,
            "peer_group_definition": definition,
            "peer_count": int(len(peers)),
            "minimum_peer_size": self.minimum_peer_size,
            "project_physical_progress_pct": progress,
            "peer_median_physical_progress_pct": progress_median,
            "peer_relative_progress_difference_pct": difference,
            "project_expenditure_ratio_pct": spend_ratio,
            "peer_median_expenditure_ratio_pct": spend_median,
            "project_delay_risk": risk,
            "peer_median_delay_risk": risk_median,
            "risk_percentile": percentile(peers.predicted_delay_probability_3m, risk) if available else None,
            "progress_percentile": percentile(peers.physical_progress_pct, progress) if available else None,
        }
