from __future__ import annotations

from collections import Counter

from backend.alert_service import AlertService
from backend.analytics_service import AnalyticsService
from backend.model_service import ModelService
from backend.peer_service import PeerService
from backend.project_service import ProjectService, clean_value
from backend.priority_service import PriorityService
from backend.trajectory_service import TrajectoryService
from backend.what_if_service import WhatIfService


class AssistantContextBuilder:
    """Builds small, JSON-safe contexts from existing source-of-truth services."""

    def __init__(self, projects: ProjectService, model: ModelService, trajectories: TrajectoryService,
                 peers: PeerService, alerts: AlertService, what_if: WhatIfService, analytics: AnalyticsService,
                 priorities: PriorityService):
        self.projects = projects
        self.model = model
        self.trajectories = trajectories
        self.peers = peers
        self.alerts = alerts
        self.what_if = what_if
        self.analytics = analytics
        self.priorities = priorities

    @staticmethod
    def reliability_level(score: float) -> str:
        return "HIGH" if score >= 85 else ("MEDIUM" if score >= 65 else "LOW")

    def project(self, project_id: str) -> tuple[dict, list[str]]:
        latest = self.projects.latest_row(project_id)
        prediction = self.model.predict_one(latest, project_id=project_id, explain=True)
        metadata = self.projects.metadata(project_id, latest)
        trajectory = self.trajectories.trajectory(project_id)[-6:]
        peers = self.peers.compare(project_id)
        alerts = self.alerts.for_project(project_id)[:5]
        scenarios = self.what_if.recommendations(project_id)["recommendations"][:3]
        reliability = float(latest["data_quality_score"])
        priority = self.priorities.get(project_id)
        context = {
            "scope": "project",
            "project": {
                "canonical_project_id": project_id,
                "project_name": metadata.get("project_name"),
                "sector": metadata.get("sector"),
                "state": metadata.get("state"),
                "ministry_department": metadata.get("ministry_department"),
                "agency": metadata.get("agency"),
                "latest_snapshot_month": str(latest["snapshot_month"]),
                "physical_progress_pct": clean_value(latest.get("physical_progress_pct")),
                "current_target_doc": clean_value(latest.get("current_target_doc")),
            },
            "schedule_risk": {
                "delay_risk_3m": prediction["delay_probability_3m"],
                "delay_risk_6m": prediction["delay_probability_6m"],
                "risk_level": prediction["risk_level"],
                "six_month_model_status": prediction["delay_6m_model_status"],
            },
            "data_reliability": {"score": reliability, "level": self.reliability_level(reliability)},
            "trajectory": trajectory,
            "risk_drivers": prediction["top_risk_drivers"],
            "protective_drivers": prediction["top_protective_drivers"],
            "peer_comparison": peers,
            "alerts": alerts,
            "recommended_scenarios": scenarios,
            "intervention_priority": {
                key: priority[key] for key in (
                    "intervention_priority_score", "intervention_priority_level",
                    "recommended_review_action", "trajectory_status", "risk_change_1m",
                    "risk_change_3m", "risk_velocity", "risk_acceleration", "top_priority_reasons",
                )
            },
            "limitations": {
                "drivers_are_associations_not_causes": True,
                "scenarios_are_not_causal_guarantees": True,
                "cost_escalation_prediction_operational": False,
            },
        }
        sources = ["project", "prediction_3m", "prediction_6m", "data_reliability", "trajectory", "shap", "peers", "alerts", "scenarios", "intervention_priority"]
        return clean_value(context), sources

    def portfolio(self) -> tuple[dict, list[str]]:
        summary = self.analytics.portfolio()
        sectors = self.analytics.groups("sector")[:8]
        ministries = self.analytics.groups("ministry_department")[:8]
        states = self.analytics.groups("state")[:5]
        alerts = self.alerts.all(limit=10)
        priorities = self.priorities.all(limit=10)
        all_alerts = self.alerts.all(limit=2000)
        pattern_counts = Counter(item["alert_type"] for item in all_alerts)
        high_priority = Counter(
            item["alert_type"] for item in all_alerts if item["severity"] in {"HIGH", "CRITICAL"}
        )
        context = {
            "scope": "portfolio",
            "portfolio": summary,
            "top_sector_aggregates": sectors,
            "top_ministry_aggregates": ministries,
            "top_state_aggregates": states,
            "top_prioritized_warnings": alerts,
            "top_intervention_priorities": priorities,
            "warning_patterns": [
                {"alert_type": alert_type, "count": count, "high_priority_count": high_priority[alert_type]}
                for alert_type, count in pattern_counts.most_common(8)
            ],
            "limitations": {
                "rankings_are_from_compact_aggregates": True,
                "cost_escalation_prediction_operational": False,
            },
        }
        return clean_value(context), ["portfolio", "sectors", "ministries", "states", "alerts", "intervention_priority"]
