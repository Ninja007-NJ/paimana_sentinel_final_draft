export type RiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export interface ProjectListItem {
  canonical_project_id: string;
  project_name: string;
  sector: string | null;
  state: string | null;
  latest_snapshot_month: string;
  latest_risk_score: number | null;
  risk_level?: RiskLevel | null;
  data_reliability_score?: number | null;
  risk_change_1m?: number | null;
}

export interface Driver {
  feature: string;
  label: string;
  observed_value: string | number | null;
}

export interface Explanation {
  canonical_project_id: string;
  snapshot_month: string;
  delay_probability_3m: number;
  risk_level: RiskLevel;
  top_risk_drivers: Driver[];
  top_protective_drivers: Driver[];
  explanation: string;
}

export interface Snapshot {
  snapshot_month: string;
  current_target_doc: string | null;
  current_forecast_cost_cr: number | null;
  cumulative_expenditure_cr: number | null;
  physical_progress_pct: number | null;
  data_quality_score: number | null;
  quality_flags: string | null;
  original_cost_cr?: number | null;
  revised_cost_cr?: number | null;
  anticipated_cost_cr?: number | null;
  original_doc?: string | null;
  revised_doc?: string | null;
  anticipated_doc?: string | null;
  current_target_source?: string | null;
}

export interface ProjectDetail {
  canonical_project_id: string;
  project_metadata: {
    project_name?: string | null;
    sector?: string | null;
    state?: string | null;
    ministry_department?: string | null;
    agency?: string | null;
    reporting_regime?: string | null;
    identity_source?: string | null;
    identity_confidence?: string | number | null;
  };
  latest_snapshot: Snapshot;
  historical_snapshots: Snapshot[];
  current_delay_probability_3m: number;
  current_delay_probability_6m: number;
  delay_6m_model_status: "GREEN" | "YELLOW";
  risk_level: RiskLevel;
  explanation: Explanation;
  data_quality_score: number;
}

export interface TrajectoryPoint {
  snapshot_month: string;
  predicted_delay_probability_3m: number;
  risk_level: RiskLevel;
  data_quality_score: number;
}

export interface PortfolioRiskRow extends ProjectListItem {
  risk_level: RiskLevel;
  latest_quality_score: number;
  risk_change: number | null;
}

export interface PeerComparison {
  canonical_project_id: string; available: boolean; peer_group_definition: Record<string, string | null>;
  peer_definition?: Record<string, string | null>;
  peer_count: number; minimum_peer_size: number; project_physical_progress_pct: number | null;
  peer_median_physical_progress_pct: number | null; peer_relative_progress_difference_pct: number | null;
  project_expenditure_ratio_pct: number | null; peer_median_expenditure_ratio_pct: number | null;
  project_delay_risk: number | null; peer_median_delay_risk: number | null;
  risk_percentile: number | null; progress_percentile: number | null;
}

export interface AlertRecord {
  alert_id: string; canonical_project_id: string; project_name: string; alert_type: string;
  severity: "INFO" | "WARNING" | "CRITICAL"; priority_score: number; current_risk: number;
  recent_risk_change: number | null; data_reliability_score: number; latest_snapshot_month: string; explanation: string;
  sector?: string | null; ministry_department?: string | null; supporting_evidence?: Record<string, string | number | null>;
  intervention_priority_score?: number | null; intervention_priority_level?: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL" | null;
}

export interface PriorityRecord {
  rank: number; canonical_project_id: string; project_name: string; sector: string | null;
  ministry_department: string | null; state: string | null; delay_probability_3m: number;
  delay_probability_6m: number; risk_level: RiskLevel; data_reliability_score: number;
  intervention_priority_score: number; intervention_priority_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  recommended_review_action: "IMMEDIATE_REVIEW" | "EARLY_INTERVENTION" | "VERIFY_DATA_URGENTLY" | "ROUTINE_MONITORING";
  history_observations: number; trajectory_status: "INSUFFICIENT_HISTORY" | "IMPROVING" | "STABLE" | "RISING" | "RAPIDLY_RISING" | "ACCELERATING";
  risk_change_1m: number | null; risk_change_3m: number | null; risk_velocity: number | null;
  risk_acceleration: number | null; top_priority_reasons: string[]; key_reason: string;
  score_components: Record<string, number>;
}

export interface WhatIfControl { feature: string; label: string; minimum: number; maximum: number; current: number | null; step: number }
export interface WhatIfConfig { canonical_project_id: string; controls: WhatIfControl[]; disclaimer: string }
export interface WhatIfResult {
  canonical_project_id: string; current_risk: number; scenario_risk: number; difference_percentage_points: number;
  current_probability: number; scenario_probability: number; probability_delta: number; current_risk_level: RiskLevel; scenario_risk_level: RiskLevel;
  changed_features: { feature: string; label: string; original_value: number | null; scenario_value: number }[];
  original_values: Record<string, number | null>; scenario_values: Record<string, number>; validation_warnings: string[];
  scenario_explanation: string; disclaimer: string;
}
export interface ScenarioRecommendation {
  rank: number; feature: string; label: string; current_value: number | null; scenario_value: number;
  current_risk: number; scenario_risk: number; difference_percentage_points: number; feasibility_score: number; wording: string;
}
export interface ScenarioRecommendations { canonical_project_id: string; recommendations: ScenarioRecommendation[]; disclaimer: string }

export interface PortfolioAnalytics {
  summary: { project_count: number; average_delay_risk: number; median_delay_risk: number; high_risk_count: number; high_risk_percentage: number; critical_risk_count: number; rapidly_rising_risk_count: number; average_data_reliability: number; aggregate_original_cost_cr: number | null; aggregate_current_cost_cr: number | null; aggregate_expenditure_cr: number | null; active_alert_count: number };
  latest_snapshot_month: string; risk_distribution: { risk_level: RiskLevel; count: number }[];
  risk_trend: { snapshot_month: string; project_count: number; average_delay_risk: number; high_or_critical_count: number }[]; minimum_group_size: number;
}

export interface GroupAnalytics {
  project_count: number; average_delay_risk: number; median_delay_risk: number; high_risk_count: number; high_risk_percentage: number; critical_risk_count: number;
  rapidly_rising_risk_count: number; average_data_reliability: number; aggregate_original_cost_cr: number | null;
  aggregate_current_cost_cr: number | null; aggregate_expenditure_cr: number | null; risk_change_1m: number | null;
  sector?: string; ministry_department?: string; state?: string;
}

export interface AssistantResponse {
  answer: string;
  scope: "project" | "portfolio";
  project_id: string | null;
  provider: "openrouter" | "deterministic-fallback";
  model: string;
  grounded: boolean;
  sources_used: string[];
}
