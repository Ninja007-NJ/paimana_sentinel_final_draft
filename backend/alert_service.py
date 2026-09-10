from __future__ import annotations

import math

import pandas as pd

from backend.project_service import ProjectService, clean_value


RAPID_RISE_THRESHOLD = 0.20
LOW_RELIABILITY_THRESHOLD = 65.0
STAGNATION_MONTHS = 3
RECENT_REVISION_COUNT = 2

SEVERITY = {
    "CRITICAL_RISK": ("CRITICAL", 50),
    "NEW_HIGH_RISK": ("CRITICAL", 45),
    "RAPIDLY_RISING_RISK": ("WARNING", 35),
    "LOW_CONFIDENCE_HIGH_RISK": ("WARNING", 32),
    "REPEATED_TARGET_REVISION": ("WARNING", 26),
    "STAGNATING_PROJECT": ("INFO", 18),
}

EXPLANATIONS = {
    "CRITICAL_RISK": "The frozen backend risk band is currently CRITICAL.",
    "RAPIDLY_RISING_RISK": "The three-month risk estimate rose by at least 20 percentage points across the latest three observed snapshots.",
    "NEW_HIGH_RISK": "The project moved from LOW/MEDIUM into a HIGH/CRITICAL backend risk band.",
    "LOW_CONFIDENCE_HIGH_RISK": "Risk is HIGH/CRITICAL while the latest source reliability score is below 65.",
    "STAGNATING_PROJECT": "Reported physical progress has shown a stagnation streak of at least three months.",
    "REPEATED_TARGET_REVISION": "At least two target revisions are recorded in the recent three-month history.",
}


class AlertService:
    def __init__(self, projects: ProjectService):
        self.projects = projects
        self._alerts = self._build_all()

    def _types_for(self, row: pd.Series, previous: pd.Series | None, recent_risk_change: float | None) -> list[str]:
        alert_types = []
        risk_level = row.get("risk_level")
        if risk_level == "CRITICAL": alert_types.append("CRITICAL_RISK")
        if recent_risk_change is not None and recent_risk_change >= RAPID_RISE_THRESHOLD: alert_types.append("RAPIDLY_RISING_RISK")
        if risk_level in {"HIGH", "CRITICAL"} and previous is not None and previous.get("risk_level") in {"LOW", "MEDIUM"}: alert_types.append("NEW_HIGH_RISK")
        if risk_level in {"HIGH", "CRITICAL"} and float(row.get("data_quality_score", 0)) < LOW_RELIABILITY_THRESHOLD: alert_types.append("LOW_CONFIDENCE_HIGH_RISK")
        if float(row.get("stagnation_streak_months", 0) or 0) >= STAGNATION_MONTHS: alert_types.append("STAGNATING_PROJECT")
        if float(row.get("target_revisions_last_3m", 0) or 0) >= RECENT_REVISION_COUNT: alert_types.append("REPEATED_TARGET_REVISION")
        return alert_types

    def _record(self, row: pd.Series, alert_type: str, recent_risk_change: float | None) -> dict:
        severity, base = SEVERITY[alert_type]
        risk = float(row.predicted_delay_probability_3m)
        change = clean_value(recent_risk_change)
        quality = float(row.data_quality_score)
        cost = row.get("current_forecast_cost_cr")
        cost_bonus = min(10.0, math.log10(max(float(cost), 1.0))) if pd.notna(cost) else 0.0
        score = base + risk * 30 + max(float(change or 0), 0) * 30 + cost_bonus + quality / 100 * 3
        return {
            "alert_id": f"{row.canonical_project_id}:{alert_type}:{row.snapshot_month}",
            "project_id": row.canonical_project_id,
            "canonical_project_id": row.canonical_project_id,
            "project_name": str(clean_value(row.get("project_name")) or row.canonical_project_id),
            "sector": clean_value(row.get("sector")),
            "ministry_department": clean_value(row.get("ministry_department")),
            "alert_type": alert_type,
            "severity": severity,
            "priority_score": round(score, 3),
            "current_risk": risk,
            "risk_change": change,
            "recent_risk_change": change,
            "data_reliability": quality,
            "data_reliability_score": quality,
            "snapshot_month": row.snapshot_month,
            "latest_snapshot_month": row.snapshot_month,
            "explanation": EXPLANATIONS[alert_type],
            "supporting_evidence": {
                "risk_level": str(row.get("risk_level")),
                "current_risk": round(risk, 6),
                "recent_three_observation_risk_change": None if change is None else round(float(change), 6),
                "data_reliability_score": round(quality, 2),
                "stagnation_streak_months": clean_value(row.get("stagnation_streak_months")),
                "target_revisions_last_3m": clean_value(row.get("target_revisions_last_3m")),
            },
        }

    def _build_all(self) -> list[dict]:
        records = []
        for project_id, rows in self.projects.frame.groupby("canonical_project_id", sort=True):
            rows = rows.sort_values("snapshot_month")
            row = rows.iloc[-1]
            previous = rows.iloc[-2] if len(rows) > 1 else None
            recent = rows.tail(3)
            recent_risk_change = None
            if len(recent) >= 2:
                recent_risk_change = float(recent.iloc[-1].predicted_delay_probability_3m - recent.iloc[0].predicted_delay_probability_3m)
            for alert_type in self._types_for(row, previous, recent_risk_change):
                records.append(self._record(row, alert_type, recent_risk_change))
        return sorted(records, key=lambda item: (-item["priority_score"], item["canonical_project_id"], item["alert_type"]))

    def all(self, limit: int = 500, severity: str | None = None, alert_type: str | None = None,
            sector: str | None = None, ministry: str | None = None) -> list[dict]:
        records = self._alerts
        filters = {"severity": severity, "alert_type": alert_type, "sector": sector, "ministry_department": ministry}
        for key, value in filters.items():
            if value:
                expected = value.strip().casefold()
                records = [item for item in records if str(item.get(key) or "").casefold() == expected]
        return records[: max(0, min(limit, 2000))]

    def count(self) -> int:
        return len(self._alerts)

    def for_project(self, project_id: str) -> list[dict]:
        self.projects.latest_row(project_id)
        return [item for item in self._alerts if item["canonical_project_id"] == project_id]
