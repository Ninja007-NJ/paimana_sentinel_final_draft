LABELS = {"progress_velocity_3m": "Recent physical-progress velocity", "schedule_pressure": "Schedule pressure", "target_revision_count_to_date": "Prior target revisions", "stagnation_streak_months": "Progress stagnation", "physical_progress_pct": "Current physical progress", "financial_physical_gap_pct": "Financial/physical progress imbalance", "months_to_target": "Time remaining to target", "current_time_slip_months": "Current Schedule Slippage", "data_quality_score": "Data Reliability"}


def humanize_driver(record):
    raw = record["feature"].split("__")[-1]; label = LABELS.get(raw, raw.replace("_", " ").title()); value = record.get("value")
    return {"factor": label, "observed_value": None if value is None else str(value)}


def format_explanation(risks, protective):
    return {"top_risk_drivers": [humanize_driver(r) for r in risks], "top_protective_drivers": [humanize_driver(r) for r in protective]}
