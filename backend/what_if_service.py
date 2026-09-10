from __future__ import annotations

import numpy as np
import pandas as pd

from backend.model_service import ModelService
from backend.project_service import ProjectService


DISCLAIMER = "This scenario reflects model behavior under modified inputs and does not imply guaranteed causal impact."

FEATURE_LABELS = {
    "progress_velocity_3m": "Expected physical progress velocity",
    "expenditure_velocity_pct_3m": "Expenditure velocity",
    "stagnation_streak_months": "Stagnation duration assumption",
    "required_progress_per_remaining_month": "Required Monthly Progress",
    "schedule_pressure": "Schedule Pressure",
}


class WhatIfService:
    def __init__(self, projects: ProjectService, model: ModelService):
        self.projects = projects
        self.model = model
        self.allowed = [name for name in FEATURE_LABELS if name in model.features]
        reference = projects.frame[self.allowed].apply(pd.to_numeric, errors="coerce")
        self.bounds = {}
        for feature in self.allowed:
            values = reference[feature].replace([np.inf, -np.inf], np.nan).dropna()
            low = float(values.quantile(0.01)) if len(values) else 0.0
            high = float(values.quantile(0.99)) if len(values) else 1.0
            if feature == "stagnation_streak_months":
                low, high = max(0.0, low), max(1.0, high)
            if low == high:
                high = low + 1.0
            self.bounds[feature] = (round(low, 4), round(high, 4))

    def configuration(self, project_id: str) -> dict:
        row = self.projects.latest_row(project_id)
        controls = []
        for feature in self.allowed:
            low, high = self.bounds[feature]
            current = row.get(feature)
            controls.append({
                "feature": feature,
                "label": FEATURE_LABELS[feature],
                "minimum": low,
                "maximum": high,
                "current": None if pd.isna(current) else float(current),
                "step": 1.0 if feature == "stagnation_streak_months" else round(max((high - low) / 100, 0.01), 3),
            })
        return {"canonical_project_id": project_id, "controls": controls, "disclaimer": DISCLAIMER}

    def simulate(self, project_id: str, changes: dict) -> dict:
        original = self.projects.latest_row(project_id)
        scenario = original.copy(deep=True)
        changed = []
        for feature, value in changes.items():
            if value is None:
                continue
            if feature not in self.allowed:
                raise ValueError(f"Feature is not scenario-adjustable: {feature}")
            low, high = self.bounds[feature]
            value = float(value)
            if value < low or value > high:
                raise ValueError(f"{feature} must be between {low} and {high}")
            previous = original.get(feature)
            scenario[feature] = value
            changed.append({
                "feature": feature,
                "label": FEATURE_LABELS[feature],
                "original_value": None if pd.isna(previous) else float(previous),
                "scenario_value": value,
            })
        if not changed:
            raise ValueError("Provide at least one scenario-adjustable value")
        current_risk = float(original["predicted_delay_probability_3m"])
        scenario_risk = float(self.model.predict_one(scenario, project_id=project_id, explain=False)["delay_probability_3m"])
        delta = round((scenario_risk - current_risk) * 100, 2)
        direction = "higher" if delta > 0 else "lower" if delta < 0 else "unchanged"
        return {
            "canonical_project_id": project_id,
            "current_risk": current_risk,
            "scenario_risk": scenario_risk,
            "current_probability": current_risk,
            "scenario_probability": scenario_risk,
            "probability_delta": round(scenario_risk - current_risk, 6),
            "current_risk_level": self.model.risk_level(current_risk),
            "scenario_risk_level": self.model.risk_level(scenario_risk),
            "difference_percentage_points": delta,
            "changed_features": changed,
            "original_values": {item["feature"]: item["original_value"] for item in changed},
            "scenario_values": {item["feature"]: item["scenario_value"] for item in changed},
            "validation_warnings": [],
            "scenario_explanation": f"Under these modified model inputs, estimated three-month delay risk is {abs(delta):.2f} percentage points {direction}.",
            "disclaimer": DISCLAIMER,
        }

    def recommendations(self, project_id: str) -> dict:
        row = self.projects.latest_row(project_id)
        candidates = []
        favorable_quantile = {
            "progress_velocity_3m": 0.75,
            "expenditure_velocity_pct_3m": 0.75,
            "stagnation_streak_months": 0.10,
            "required_progress_per_remaining_month": 0.25,
            "schedule_pressure": 0.25,
        }
        for feature in self.allowed:
            low, high = self.bounds[feature]
            target = low + (high - low) * favorable_quantile[feature]
            if feature == "stagnation_streak_months":
                target = round(target)
            current = row.get(feature)
            if pd.isna(current) or abs(float(current) - target) < 1e-9:
                continue
            if feature in {"progress_velocity_3m", "expenditure_velocity_pct_3m"} and target <= float(current):
                continue
            if feature in {"stagnation_streak_months", "required_progress_per_remaining_month", "schedule_pressure"} and target >= float(current):
                continue
            try:
                result = self.simulate(project_id, {feature: target})
            except ValueError:
                continue
            reduction = result["current_risk"] - result["scenario_risk"]
            if reduction <= 0:
                continue
            distance = abs(target - float(current)) / max(high - low, 1e-9)
            feasibility = max(0.0, 1.0 - distance)
            candidates.append((reduction * (0.5 + 0.5 * feasibility), feature, target, result, feasibility))
        candidates.sort(key=lambda item: (-item[0], item[1]))
        recommendations = []
        for rank, (_, feature, target, result, feasibility) in enumerate(candidates[:3], 1):
            current = float(row[feature])
            recommendations.append({
                "rank": rank,
                "feature": feature,
                "label": FEATURE_LABELS[feature],
                "current_value": current,
                "scenario_value": float(target),
                "current_risk": result["current_risk"],
                "scenario_risk": result["scenario_risk"],
                "difference_percentage_points": result["difference_percentage_points"],
                "feasibility_score": round(feasibility * 100, 1),
                "wording": (
                    f"Under this model scenario, changing {FEATURE_LABELS[feature].lower()} from "
                    f"{current:.2f} to {target:.2f} changes estimated delay risk from "
                    f"{result['current_risk'] * 100:.1f}% to {result['scenario_risk'] * 100:.1f}%."
                ),
            })
        return {"canonical_project_id": project_id, "recommendations": recommendations, "disclaimer": DISCLAIMER}
