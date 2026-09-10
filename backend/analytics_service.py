from __future__ import annotations

import pandas as pd

from backend.alert_service import AlertService
from backend.project_service import ProjectService, clean_value


MINIMUM_GROUP_SIZE = 10


class AnalyticsService:
    def __init__(self, projects: ProjectService, alerts: AlertService):
        self.projects = projects
        self.alerts = alerts
        self.latest = projects.latest.reset_index(drop=True).copy()
        self.rapid_alert_project_ids = {
            item["canonical_project_id"] for item in alerts._alerts
            if item["alert_type"] == "RAPIDLY_RISING_RISK"
        }

    def _metrics(self, frame: pd.DataFrame) -> dict:
        risk = frame["predicted_delay_probability_3m"]
        original = pd.to_numeric(frame.get("original_cost_cr"), errors="coerce")
        current = pd.to_numeric(frame.get("current_forecast_cost_cr"), errors="coerce")
        expenditure = pd.to_numeric(frame.get("cumulative_expenditure_cr"), errors="coerce")
        high_count = int(frame.risk_level.isin(["HIGH", "CRITICAL"]).sum())
        return {
            "project_count": int(frame.canonical_project_id.nunique()),
            "average_delay_risk": round(float(risk.mean()), 6),
            "median_delay_risk": round(float(risk.median()), 6),
            "high_risk_count": high_count,
            "high_risk_percentage": round(high_count / len(frame) * 100, 2) if len(frame) else 0.0,
            "critical_risk_count": int((frame.risk_level == "CRITICAL").sum()),
            "rapidly_rising_risk_count": int(frame.canonical_project_id.isin(self.rapid_alert_project_ids).sum()),
            "average_data_reliability": round(float(frame.data_quality_score.mean()), 2),
            "aggregate_original_cost_cr": clean_value(original.sum(min_count=1)),
            "aggregate_current_cost_cr": clean_value(current.sum(min_count=1)),
            "aggregate_expenditure_cr": clean_value(expenditure.sum(min_count=1)),
        }

    def groups(self, column: str) -> list[dict]:
        output = []
        for name, frame in self.latest.groupby(column, dropna=True, sort=True):
            if len(frame) < MINIMUM_GROUP_SIZE or str(name).strip() in ("", "nan"):
                continue
            row = {column: str(name), **self._metrics(frame)}
            row["risk_change_1m"] = round(float(frame.risk_change_1m.mean()), 6) if frame.risk_change_1m.notna().any() else None
            output.append(row)
        return sorted(output, key=lambda item: (-item["average_delay_risk"], str(item[column])))

    def portfolio(self) -> dict:
        distribution = self.latest.risk_level.value_counts().reindex(["LOW", "MEDIUM", "HIGH", "CRITICAL"], fill_value=0)
        monthly = []
        for month, frame in self.projects.frame.groupby("snapshot_month", sort=True):
            monthly.append({
                "snapshot_month": str(month),
                "project_count": int(frame.canonical_project_id.nunique()),
                "average_delay_risk": round(float(frame.predicted_delay_probability_3m.mean()), 6),
                "high_or_critical_count": int(frame.risk_level.isin(["HIGH", "CRITICAL"]).sum()),
            })
        return {
            "summary": {**self._metrics(self.latest), "active_alert_count": self.alerts.count()},
            "latest_snapshot_month": str(self.latest.snapshot_month.max()),
            "risk_distribution": [{"risk_level": key, "count": int(value)} for key, value in distribution.items()],
            "risk_trend": monthly,
            "minimum_group_size": MINIMUM_GROUP_SIZE,
        }
