from __future__ import annotations

NUMERICAL_FEATURES = [
    "project_age_months", "months_to_target", "current_time_slip_months",
    "current_cost_overrun_pct", "spend_ratio_pct", "physical_progress_pct",
    "financial_physical_gap_pct", "progress_delta_1m", "progress_delta_3m",
    "progress_delta_6m", "spend_delta_1m_cr", "spend_delta_3m_cr",
    "spend_delta_6m_cr", "progress_velocity_3m", "schedule_pressure",
    "stagnation_streak_months", "target_revision_count_to_date",
    "cost_revision_count_to_date", "data_quality_score", "missing_core_fields_count",
]
CATEGORICAL_FEATURES = ["sector", "state", "ministry_department"]
ALLOWED_FEATURES = NUMERICAL_FEATURES + CATEGORICAL_FEATURES

DESCRIPTIONS = {
    "project_age_months": "Elapsed months from approval/start through snapshot t.",
    "months_to_target": "Months from snapshot t to the current reported target.",
    "current_time_slip_months": "Current target minus original target at t.",
    "current_cost_overrun_pct": "Current forecast cost over original cost at t.",
    "spend_ratio_pct": "Cumulative expenditure divided by current forecast cost at t.",
    "physical_progress_pct": "Reported physical progress at t.",
    "financial_physical_gap_pct": "Spend ratio minus physical progress at t.",
    "progress_delta_1m": "Physical-progress change from exactly t-1.",
    "progress_delta_3m": "Physical-progress change from exactly t-3.",
    "progress_delta_6m": "Physical-progress change from exactly t-6.",
    "spend_delta_1m_cr": "Expenditure change from exactly t-1.",
    "spend_delta_3m_cr": "Expenditure change from exactly t-3.",
    "spend_delta_6m_cr": "Expenditure change from exactly t-6.",
    "progress_velocity_3m": "Average monthly progress over the prior three months.",
    "schedule_pressure": "Remaining progress divided by remaining target months.",
    "stagnation_streak_months": "Consecutive low-change observations through t.",
    "target_revision_count_to_date": "Target revisions observed through t only.",
    "cost_revision_count_to_date": "Cost revisions observed through t only.",
    "data_quality_score": "Contemporaneous source-quality score.",
    "missing_core_fields_count": "Missing core values at t.",
    "sector": "Normalized project sector.", "state": "Normalized state/territory.",
    "ministry_department": "Normalized responsible ministry/department.",
}
CONTROLLABILITY = {
    **{name: "OBSERVATIONAL_NOT_DIRECTLY_ACTIONABLE" for name in ALLOWED_FEATURES},
    "sector": "IMMUTABLE", "state": "IMMUTABLE", "project_age_months": "IMMUTABLE",
    "progress_velocity_3m": "POTENTIALLY_SCENARIO_ADJUSTABLE",
    "stagnation_streak_months": "POTENTIALLY_SCENARIO_ADJUSTABLE",
    "schedule_pressure": "POTENTIALLY_SCENARIO_ADJUSTABLE",
}
EXCLUDED_PATTERNS = {
    "canonical_project_id": "Direct identifier; grouping/evaluation only.",
    "snapshot_month": "Temporal split/evaluation only.",
    "reporting_regime": "Regime diagnostic only; explicitly excluded from Model V1.",
    "delay_event_next_*": "Target/future outcome leakage.",
    "cost_escalation_next_*": "Future outcome leakage.",
    "future_coverage_*": "Future availability leakage.",
    "valid_*_target_*": "Label validity/future coverage leakage.",
    "raw_*": "Raw source/provenance text is excluded.",
}


def registry_records():
    records = []
    for name in ALLOWED_FEATURES:
        records.append({
            "feature_name": name,
            "type": "numerical" if name in NUMERICAL_FEATURES else "categorical",
            "description": DESCRIPTIONS[name], "allowed": True,
            "leakage_reason": "", "controllability": CONTROLLABILITY[name],
        })
    for name, reason in EXCLUDED_PATTERNS.items():
        records.append({"feature_name": name, "type": "excluded", "description": "", "allowed": False, "leakage_reason": reason, "controllability": "NOT_APPLICABLE"})
    return records


def exclusion_reason(column):
    if column in {"canonical_project_id", "snapshot_month"}:
        return EXCLUDED_PATTERNS[column]
    if column == "reporting_regime":
        return EXCLUDED_PATTERNS[column]
    if column.startswith("delay_event_next_") or column.startswith("cost_escalation_next_"):
        return "Target or future outcome leakage."
    if column.startswith("future_coverage_"):
        return "Future availability leakage."
    if column.startswith("valid_") and "_target_" in column:
        return "Label validity and future coverage leakage."
    if column in {"current_target_source", "current_cost_source", "quality_flags", "identity_source", "collision_flag"}:
        return "Provenance/evaluation diagnostic; excluded from Model V1 predictors."
    if column in {"original_cost_cr", "current_forecast_cost_cr"}:
        return "Joined only to define evaluation cost buckets; not registered as a Model V1 predictor."
    return "Not registered for Model V1; excluded by default."


def registry_for_columns(columns):
    records = registry_records()[:len(ALLOWED_FEATURES)]
    for column in columns:
        if column in ALLOWED_FEATURES:
            continue
        records.append({
            "feature_name": column, "type": "excluded", "description": "",
            "allowed": False, "leakage_reason": exclusion_reason(column),
            "controllability": "NOT_APPLICABLE",
        })
    return records
