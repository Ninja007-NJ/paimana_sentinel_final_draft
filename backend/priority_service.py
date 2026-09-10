from __future__ import annotations

from collections import Counter, defaultdict

import numpy as np
import pandas as pd

from backend.alert_service import AlertService
from backend.model_service import ModelService
from backend.peer_service import PeerService
from backend.project_service import ProjectService, clean_value


TRAJECTORY_POINTS = {
    "INSUFFICIENT_HISTORY": 2.0,
    "IMPROVING": 0.0,
    "STABLE": 3.0,
    "RISING": 10.0,
    "RAPIDLY_RISING": 17.0,
    "ACCELERATING": 20.0,
}
ALERT_POINTS = {
    "CRITICAL_RISK": 10.0,
    "NEW_HIGH_RISK": 10.0,
    "RAPIDLY_RISING_RISK": 7.0,
    "LOW_CONFIDENCE_HIGH_RISK": 6.0,
    "REPEATED_TARGET_REVISION": 4.0,
    "STAGNATING_PROJECT": 3.0,
}


def _positive_quantile(values: pd.Series, quantile: float, fallback: float) -> float:
    positive = pd.to_numeric(values, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    positive = positive[positive > 0]
    return float(positive.quantile(quantile)) if len(positive) else fallback


def trajectory_metrics(probabilities: list[float], thresholds: dict[str, float]) -> dict:
    values = np.asarray(probabilities, dtype=float)
    count = len(values)
    change_1m = float(values[-1] - values[-2]) if count >= 2 else None
    change_3m = float(values[-1] - values[-4]) if count >= 4 else None
    velocity = float(np.diff(values[-4:]).mean()) if count >= 2 else None
    acceleration = float((values[-1] - values[-2]) - (values[-2] - values[-3])) if count >= 3 else None
    if count < 3:
        status = "INSUFFICIENT_HISTORY"
    else:
        meaningful = thresholds["meaningful_change"]
        if change_1m <= -meaningful or (abs(change_1m) < meaningful and change_3m is not None and change_3m <= -meaningful):
            status = "IMPROVING"
        elif change_1m >= meaningful and acceleration >= thresholds["acceleration"]:
            status = "ACCELERATING"
        elif change_1m >= thresholds["rapid_change_1m"] or (change_3m is not None and change_3m >= thresholds["rapid_change_3m"]):
            status = "RAPIDLY_RISING"
        elif change_1m >= meaningful or (change_3m is not None and change_3m >= meaningful):
            status = "RISING"
        else:
            status = "STABLE"
    return {
        "history_observations": count,
        "risk_change_1m": change_1m,
        "risk_change_3m": change_3m,
        "risk_velocity": velocity,
        "risk_acceleration": acceleration,
        "trajectory_status": status,
    }


class PriorityService:
    """Deterministic intervention ranking built only from existing trusted outputs."""

    FORMULA = {
        "schedule_risk": "35 points: 25 × 3-month probability + 10 × 6-month probability",
        "trajectory": "20 points: distribution-aware trajectory state",
        "deterministic_alerts": "15 points: capped severity/type weights",
        "peer_position": "10 points: peer risk and progress percentiles",
        "project_exposure": "10 points: current-cost empirical percentile",
        "schedule_pressure": "10 points: schedule-pressure empirical percentile",
    }

    def __init__(self, projects: ProjectService, model: ModelService, alerts: AlertService, peers: PeerService):
        self.projects = projects
        self.model = model
        self.alerts = alerts
        self.peers = peers
        self.thresholds = self._derive_trajectory_thresholds()
        self._records = self._build_records()
        scores = pd.Series([item["intervention_priority_score"] for item in self._records])
        self.priority_thresholds = {
            "CRITICAL": float(scores.quantile(.90)),
            "HIGH": float(scores.quantile(.75)),
            "MEDIUM": float(scores.quantile(.40)),
        }
        for item in self._records:
            item["intervention_priority_level"] = self._priority_level(item["intervention_priority_score"])
            item["recommended_review_action"] = self._recommended_action(item)
        self._records.sort(key=lambda item: (-item["intervention_priority_score"], item["canonical_project_id"]))
        for rank, item in enumerate(self._records, 1):
            item["rank"] = rank
        self._by_project = {item["canonical_project_id"]: item for item in self._records}

    def _latest_trajectory_frame(self) -> pd.DataFrame:
        records = []
        for project_id, frame in self.projects.frame.groupby("canonical_project_id", sort=True):
            probabilities = frame.sort_values("snapshot_month").predicted_delay_probability_3m.tolist()
            values = trajectory_metrics(probabilities, {
                "meaningful_change": .02, "rapid_change_1m": .30,
                "rapid_change_3m": .56, "acceleration": .31,
            })
            records.append({"canonical_project_id": project_id, **values})
        return pd.DataFrame(records)

    def _derive_trajectory_thresholds(self) -> dict[str, float]:
        provisional = self._latest_trajectory_frame()
        return {
            "meaningful_change": _positive_quantile(provisional.risk_change_1m, .25, .02),
            "rapid_change_1m": _positive_quantile(provisional.risk_change_1m, .75, .30),
            "rapid_change_3m": _positive_quantile(provisional.risk_change_3m, .75, .56),
            "acceleration": _positive_quantile(provisional.risk_acceleration, .75, .31),
        }

    @staticmethod
    def _percentile_map(series: pd.Series) -> dict[str, float]:
        numeric = pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan)
        ranks = numeric.rank(method="average", pct=True)
        return {str(index): float(value) for index, value in ranks.items() if pd.notna(value)}

    def _build_records(self) -> list[dict]:
        latest = self.projects.latest.copy()
        delay_6m = self.model.probabilities_6m(latest)
        six_month = dict(zip(latest.canonical_project_id.astype(str), delay_6m))
        cost_percentile = self._percentile_map(latest.set_index("canonical_project_id").current_forecast_cost_cr)
        pressure_percentile = self._percentile_map(latest.set_index("canonical_project_id").schedule_pressure)
        peer_frame = self.peers.latest.copy()
        peer_groups = peer_frame.groupby("sector", dropna=True)
        peer_frame["portfolio_peer_risk_percentile"] = peer_groups.predicted_delay_probability_3m.rank(method="average", pct=True) * 100
        peer_frame["portfolio_peer_progress_percentile"] = peer_groups.physical_progress_pct.rank(method="average", pct=True) * 100
        peer_frame["portfolio_peer_count"] = peer_groups.canonical_project_id.transform("count") - 1
        peer_metrics = peer_frame.set_index("canonical_project_id")[[
            "portfolio_peer_risk_percentile", "portfolio_peer_progress_percentile", "portfolio_peer_count"
        ]].to_dict("index")
        alerts_by_project = defaultdict(list)
        for alert in self.alerts._alerts:
            alerts_by_project[alert["canonical_project_id"]].append(alert)

        output = []
        for project_id, frame in self.projects.frame.groupby("canonical_project_id", sort=True):
            frame = frame.sort_values("snapshot_month")
            latest_row = frame.iloc[-1]
            probabilities = frame.predicted_delay_probability_3m.astype(float).tolist()
            trend = trajectory_metrics(probabilities, self.thresholds)
            risk_3m = float(probabilities[-1])
            risk_6m = float(six_month[project_id])
            project_alerts = alerts_by_project[project_id]
            peer_values = peer_metrics.get(project_id, {})
            peer_count_value = peer_values.get("portfolio_peer_count", 0)
            peer_count = 0 if pd.isna(peer_count_value) else int(peer_count_value)
            peer = {
                "available": peer_count >= self.peers.minimum_peer_size,
                "peer_count": peer_count,
                "risk_percentile": clean_value(peer_values.get("portfolio_peer_risk_percentile")),
                "progress_percentile": clean_value(peer_values.get("portfolio_peer_progress_percentile")),
            }
            peer_component = 0.0
            if peer["available"]:
                peer_component += .07 * float(peer.get("risk_percentile") or 0)
                peer_component += .03 * (100 - float(peer.get("progress_percentile") or 100))
            alert_component = min(15.0, sum(ALERT_POINTS.get(item["alert_type"], 0) for item in project_alerts))
            components = {
                "schedule_risk": 25 * risk_3m + 10 * risk_6m,
                "trajectory": TRAJECTORY_POINTS[trend["trajectory_status"]],
                "deterministic_alerts": alert_component,
                "peer_position": min(10.0, peer_component),
                "project_exposure": 10 * cost_percentile.get(project_id, 0.0),
                "schedule_pressure": 10 * pressure_percentile.get(project_id, 0.0),
            }
            score = round(float(np.clip(sum(components.values()), 0, 100)), 2)
            reasons = self._reasons(risk_3m, risk_6m, trend, project_alerts, peer,
                                    cost_percentile.get(project_id), pressure_percentile.get(project_id),
                                    float(latest_row.data_quality_score))
            metadata = self.projects.metadata(project_id, latest_row)
            output.append(clean_value({
                "rank": 0,
                "canonical_project_id": project_id,
                "project_name": metadata.get("project_name") or project_id,
                "sector": metadata.get("sector"),
                "ministry_department": metadata.get("ministry_department"),
                "state": metadata.get("state"),
                "delay_probability_3m": risk_3m,
                "delay_probability_6m": risk_6m,
                "risk_level": str(latest_row.risk_level),
                "data_reliability_score": float(latest_row.data_quality_score),
                "intervention_priority_score": score,
                "intervention_priority_level": "",
                "recommended_review_action": "",
                **trend,
                "top_priority_reasons": reasons[:4],
                "key_reason": reasons[0],
                "score_components": {key: round(value, 2) for key, value in components.items()},
            }))
        return output

    @staticmethod
    def _reasons(risk_3m, risk_6m, trend, alerts, peer, cost_pct, pressure_pct, reliability) -> list[str]:
        weighted = []
        if risk_3m >= .75: weighted.append((25, "High 3-month delay risk"))
        elif risk_3m >= .50: weighted.append((18, "Elevated 3-month delay risk"))
        if risk_6m >= .75: weighted.append((10, "High 6-month delay risk"))
        status = trend["trajectory_status"]
        if status == "ACCELERATING": weighted.append((20, "Risk is accelerating"))
        elif status == "RAPIDLY_RISING": weighted.append((17, "Risk is rapidly rising"))
        elif status == "RISING": weighted.append((10, "Risk is rising"))
        if any(item["severity"] == "CRITICAL" for item in alerts): weighted.append((15, "Critical deterministic warning is active"))
        elif alerts: weighted.append((8, "Deterministic warning is active"))
        if peer.get("available") and float(peer.get("risk_percentile") or 0) >= 75:
            weighted.append((9, f"Project is in the {float(peer['risk_percentile']):.0f}th risk percentile among peers"))
        if peer.get("available") and float(peer.get("progress_percentile") or 100) <= 25:
            weighted.append((7, "Progress is in the bottom peer-group quartile"))
        if cost_pct is not None and cost_pct >= .90: weighted.append((6, "Project exposure is in the top cost decile"))
        if pressure_pct is not None and pressure_pct >= .90: weighted.append((6, "Schedule pressure is in the top portfolio decile"))
        if reliability < 65: weighted.append((14, "High uncertainty requires urgent data verification"))
        if not weighted: weighted.append((1, "Current risk and monitoring signals support routine review"))
        return [reason for _, reason in sorted(weighted, key=lambda item: (-item[0], item[1]))]

    def _priority_level(self, score: float) -> str:
        if score >= self.priority_thresholds["CRITICAL"]: return "CRITICAL"
        if score >= self.priority_thresholds["HIGH"]: return "HIGH"
        if score >= self.priority_thresholds["MEDIUM"]: return "MEDIUM"
        return "LOW"

    def _recommended_action(self, item: dict) -> str:
        high_operational_risk = item["risk_level"] in {"HIGH", "CRITICAL"}
        if high_operational_risk and item["data_reliability_score"] < 65:
            return "VERIFY_DATA_URGENTLY"
        if high_operational_risk:
            return "IMMEDIATE_REVIEW"
        if item["trajectory_status"] in {"ACCELERATING", "RAPIDLY_RISING"} or item["intervention_priority_level"] in {"CRITICAL", "HIGH"}:
            return "EARLY_INTERVENTION"
        return "ROUTINE_MONITORING"

    def get(self, project_id: str) -> dict:
        if project_id not in self._by_project:
            raise KeyError(project_id)
        return self._by_project[project_id]

    def all(self, limit: int = 500, **filters) -> list[dict]:
        records = self._records
        key_map = {
            "priority_level": "intervention_priority_level",
            "trajectory_status": "trajectory_status",
            "sector": "sector",
            "ministry": "ministry_department",
            "state": "state",
            "recommended_action": "recommended_review_action",
        }
        for supplied, field in key_map.items():
            value = filters.get(supplied)
            if value:
                expected = str(value).strip().casefold()
                records = [item for item in records if str(item.get(field) or "").casefold() == expected]
        return records[:max(0, min(limit, len(records)))]

    def enrich_alerts(self, records: list[dict]) -> list[dict]:
        return [{**item,
                 "intervention_priority_score": self.get(item["canonical_project_id"])["intervention_priority_score"],
                 "intervention_priority_level": self.get(item["canonical_project_id"])["intervention_priority_level"]}
                for item in records]

    def audit(self) -> dict:
        return {
            "eligible_projects": len(self._records),
            "insufficient_history_projects": sum(item["trajectory_status"] == "INSUFFICIENT_HISTORY" for item in self._records),
            "trajectory_distribution": dict(Counter(item["trajectory_status"] for item in self._records)),
            "priority_distribution": dict(Counter(item["intervention_priority_level"] for item in self._records)),
            "recommended_action_distribution": dict(Counter(item["recommended_review_action"] for item in self._records)),
            "trajectory_thresholds_probability_points": self.thresholds,
            "priority_score_thresholds": self.priority_thresholds,
            "formula": self.FORMULA,
        }
