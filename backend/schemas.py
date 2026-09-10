from __future__ import annotations

import math
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ThresholdProfile(str, Enum):
    EARLY_WARNING = "EARLY_WARNING"
    BALANCED = "BALANCED"
    CONSERVATIVE = "CONSERVATIVE"


class ProjectSnapshotInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    canonical_project_id: str | None = None
    threshold_profile: ThresholdProfile = ThresholdProfile.BALANCED
    project_age_months: float | None
    months_to_target: float | None
    current_time_slip_months: float | None
    current_cost_overrun_pct: float | None
    spend_ratio_pct: float | None
    physical_progress_pct: float | None
    financial_physical_gap_pct: float | None
    progress_delta_1m: float | None
    progress_delta_3m: float | None
    progress_delta_6m: float | None
    spend_delta_1m_cr: float | None
    spend_delta_3m_cr: float | None
    spend_delta_6m_cr: float | None
    progress_velocity_3m: float | None
    schedule_pressure: float | None
    stagnation_streak_months: float | None
    target_revision_count_to_date: float | None
    cost_revision_count_to_date: float | None
    data_quality_score: float = Field(ge=0, le=100)
    missing_core_fields_count: float = Field(ge=0)
    sector: str | None
    state: str | None
    ministry_department: str | None
    progress_acceleration_1m: float | None
    months_since_meaningful_progress: float | None
    target_revisions_last_3m: float | None
    months_since_target_revision: float | None
    expenditure_velocity_pct_3m: float | None
    expenditure_progress_velocity_gap_3m: float | None
    required_progress_per_remaining_month: float | None
    peer_relative_progress_pct: float | None

    @field_validator("sector", "state", "ministry_department")
    @classmethod
    def normalize_category(cls, value):
        if value is None: return value
        value = " ".join(value.split())
        return value or None

    @field_validator("*", mode="after")
    @classmethod
    def finite_numbers(cls, value):
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("numeric inputs must be finite or null")
        return value


class Driver(BaseModel):
    feature: str
    label: str
    observed_value: str | float | None


class PredictionConfidence(BaseModel):
    level: str
    score: float
    missing_feature_count: int
    out_of_range_feature_count: int
    fallback_identity: bool


class PredictionResponse(BaseModel):
    delay_probability_3m: float
    delay_probability_6m: float
    delay_6m_model_status: str
    risk_level: str
    threshold_profile: str
    top_risk_drivers: list[Driver]
    top_protective_drivers: list[Driver]
    data_quality_score: float
    prediction_confidence: PredictionConfidence
    model_version: str


class ProjectListItem(BaseModel):
    canonical_project_id: str
    project_name: str
    sector: str | None
    state: str | None
    latest_snapshot_month: str
    latest_risk_score: float | None
    risk_level: str | None = None
    data_reliability_score: float | None = None
    risk_change_1m: float | None = None


class TrajectoryPoint(BaseModel):
    snapshot_month: str
    predicted_delay_probability_3m: float
    risk_level: str
    data_quality_score: float


class ExplanationResponse(BaseModel):
    canonical_project_id: str
    snapshot_month: str
    delay_probability_3m: float
    risk_level: str
    top_risk_drivers: list[Driver]
    top_protective_drivers: list[Driver]
    explanation: str


class ProjectDetailResponse(BaseModel):
    canonical_project_id: str
    project_metadata: dict[str, Any]
    latest_snapshot: dict[str, Any]
    historical_snapshots: list[dict[str, Any]]
    current_delay_probability_3m: float
    current_delay_probability_6m: float
    delay_6m_model_status: str
    risk_level: str
    explanation: ExplanationResponse
    data_quality_score: float


class PeerComparisonResponse(BaseModel):
    canonical_project_id: str
    available: bool
    peer_definition: dict[str, Any]
    peer_group_definition: dict[str, Any]
    peer_count: int
    minimum_peer_size: int
    project_physical_progress_pct: float | None
    peer_median_physical_progress_pct: float | None
    peer_relative_progress_difference_pct: float | None
    project_expenditure_ratio_pct: float | None
    peer_median_expenditure_ratio_pct: float | None
    project_delay_risk: float | None
    peer_median_delay_risk: float | None
    risk_percentile: float | None
    progress_percentile: float | None


class AlertRecord(BaseModel):
    alert_id: str
    project_id: str
    canonical_project_id: str
    project_name: str
    sector: str | None = None
    ministry_department: str | None = None
    alert_type: str
    severity: str
    priority_score: float
    current_risk: float
    risk_change: float | None
    recent_risk_change: float | None
    data_reliability: float
    data_reliability_score: float
    snapshot_month: str
    latest_snapshot_month: str
    explanation: str
    supporting_evidence: dict[str, Any]
    intervention_priority_score: float | None = None
    intervention_priority_level: str | None = None


class PriorityRecord(BaseModel):
    rank: int
    canonical_project_id: str
    project_name: str
    sector: str | None
    ministry_department: str | None
    state: str | None
    delay_probability_3m: float
    delay_probability_6m: float
    risk_level: str
    data_reliability_score: float
    intervention_priority_score: float = Field(ge=0, le=100)
    intervention_priority_level: str
    recommended_review_action: str
    history_observations: int
    trajectory_status: str
    risk_change_1m: float | None
    risk_change_3m: float | None
    risk_velocity: float | None
    risk_acceleration: float | None
    top_priority_reasons: list[str]
    key_reason: str
    score_components: dict[str, float]


class WhatIfRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    changes: dict[str, float] | None = None
    progress_velocity_3m: float | None = None
    expenditure_velocity_pct_3m: float | None = None
    stagnation_streak_months: float | None = None
    required_progress_per_remaining_month: float | None = None
    schedule_pressure: float | None = None

    @field_validator("*", mode="after")
    @classmethod
    def finite_scenario_values(cls, value):
        if isinstance(value, (int, float)) and not math.isfinite(value):
            raise ValueError("scenario values must be finite")
        return value

    def scenario_changes(self) -> dict[str, float]:
        flat = self.model_dump(exclude_none=True, exclude={"changes"})
        if self.changes is not None:
            if flat:
                raise ValueError("Use either the changes object or flat scenario fields, not both")
            return self.changes
        return flat


class WhatIfResponse(BaseModel):
    canonical_project_id: str
    current_risk: float
    scenario_risk: float
    current_probability: float
    scenario_probability: float
    probability_delta: float
    current_risk_level: str
    scenario_risk_level: str
    difference_percentage_points: float
    changed_features: list[dict[str, Any]]
    original_values: dict[str, float | None]
    scenario_values: dict[str, float]
    validation_warnings: list[str]
    scenario_explanation: str
    disclaimer: str


class ScenarioRecommendation(BaseModel):
    rank: int
    feature: str
    label: str
    current_value: float | None
    scenario_value: float
    current_risk: float
    scenario_risk: float
    difference_percentage_points: float
    feasibility_score: float
    wording: str


class ScenarioRecommendationsResponse(BaseModel):
    canonical_project_id: str
    recommendations: list[ScenarioRecommendation]
    disclaimer: str


class AssistantQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=1, max_length=1500)
    project_id: str | None = Field(default=None, min_length=1, max_length=200)

    @field_validator("question")
    @classmethod
    def non_blank_question(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("question must not be blank")
        return value

    @field_validator("project_id")
    @classmethod
    def clean_project_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("project_id must not be blank")
        return value


class AssistantResponse(BaseModel):
    answer: str
    scope: str
    project_id: str | None
    provider: str
    model: str
    grounded: bool
    sources_used: list[str]


class IntelligenceQuestion(BaseModel):
    """Compatibility schema for the legacy project-scoped endpoint."""
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=1, max_length=1500)

    @field_validator("question")
    @classmethod
    def non_blank_question(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("question must not be blank")
        return value
