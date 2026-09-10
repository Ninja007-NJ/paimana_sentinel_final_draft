from __future__ import annotations

import pandas as pd

LABELS = {
    "months_to_target": "Time remaining to the current target",
    "required_progress_per_remaining_month": "Required Monthly Progress",
    "current_time_slip_months": "Current Schedule Slippage",
    "schedule_pressure": "Schedule pressure",
    "physical_progress_pct": "Current physical progress",
    "peer_relative_progress_pct": "Progress vs Similar Projects",
    "progress_acceleration_1m": "Recent progress acceleration",
    "months_since_meaningful_progress": "Time since meaningful progress",
    "target_revisions_last_3m": "Recent target revisions",
    "months_since_target_revision": "Time since target revision",
    "expenditure_progress_velocity_gap_3m": "Expenditure/progress velocity gap",
    "state": "Project state",
    "sector": "Project sector",
    "ministry_department": "Ministry / Department",
}


def driver(feature: str, value) -> dict:
    if pd.isna(value): value = None
    elif not isinstance(value, str): value = round(float(value), 4)
    return {"feature": feature, "label": LABELS.get(feature, feature.replace("_", " ").title()), "observed_value": value}


class ExplanationService:
    def format(self, feature_names, shap_values, row: pd.Series, top_n=5):
        records = [(feature, float(impact)) for feature, impact in zip(feature_names, shap_values)]
        risks = sorted((item for item in records if item[1] > 0), key=lambda item: item[1], reverse=True)[:top_n]
        protective = sorted((item for item in records if item[1] < 0), key=lambda item: item[1])[:top_n]
        risk_drivers = [driver(feature, row.get(feature)) for feature, _ in risks]
        protective_drivers = [driver(feature, row.get(feature)) for feature, _ in protective]
        risk_text = ", ".join(item["label"].lower() for item in risk_drivers[:2]) or "no dominant risk factor"
        protective_text = ", ".join(item["label"].lower() for item in protective_drivers[:2]) or "no dominant protective factor"
        sentence = f"Risk is primarily increased by {risk_text}, while {protective_text} reduces the estimate. These are predictive associations, not causal effects."
        return risk_drivers, protective_drivers, sentence
