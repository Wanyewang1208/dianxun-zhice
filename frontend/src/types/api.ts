export interface Envelope<T> {
  success: boolean;
  code: string;
  message: string;
  data: T;
  error: { code: string; message: string } | null;
  request_id: string;
  schema_version: string;
  warnings: string[];
}
export interface HealthResponse {
  status: string;
  mode: string;
  models_ready: boolean;
  real_vehicle_validated: boolean;
}
export interface BMSRequest {
  telemetry_csv: string;
  metadata_csv: string;
  max_gap_s?: number;
}
export interface BMSValidationResponse {
  status: "checked";
  summary: {
    input_rows: number;
    accepted_rows: number;
    rejected_rows: number;
    error_count: number;
    warning_count: number;
    schema_ready: boolean;
    unvalidated_telemetry_columns?: string[];
    unvalidated_metadata_columns?: string[];
    synthetic_fixture_present: boolean;
    interpretation: string;
    scope: string;
    source_provenance: string;
  };
  issues: {
    csv_row: number;
    severity: string;
    code: string;
    field: string;
    detail: string;
  }[];
  accepted: Record<string, unknown>[];
  rejected: Record<string, unknown>[];
  normalized_metadata: Record<string, unknown>[];
}
export interface ModelCase {
  battery_id: string;
  cycle: number;
}
export interface AssessmentRequest {
  model_case: ModelCase;
  scenario: {
    scenario_id: string;
    data_kind: string;
    assessed_at: string;
    inspection_at: string;
    health: { soh_pct: number; rul_cycles: number; rul_unit: string };
    safety: Record<string, boolean>;
  };
  weights?: Record<string, number>;
  bms?: BMSRequest;
  carbon?: {
    activities: Record<string, unknown>[];
    factors: Record<string, unknown>[];
    allow_demo: boolean;
  };
}
export interface Unavailable {
  status: "not_available" | "not_provided";
  reason: string;
}
export interface SOHResult {
  status: "available";
  battery_id: string;
  cycle: number;
  predicted_soh_pct: number;
  measured_soh_pct: number;
  model: string;
  unit: string;
  evidence_kind: string;
  validation_status: string;
  scope: string;
}
export interface RULResult {
  status: "available" | "not_available";
  battery_id: string;
  cycle: number;
  predicted_rul_cycles: number | null;
  unit: string;
  method?: string;
  reason?: string;
  features?: { current_capacity_ah: number; initial_capacity_ah: number };
  operating_condition_caution: string;
  validation_status: string;
}
export interface ExplainabilityResult {
  status: "available";
  method: string;
  base_value_soh_pct: number;
  additivity_error_pp: number;
  contributions: {
    feature: string;
    feature_value: number;
    shap_soh_pp: number;
    direction: string;
  }[];
  interpretation: string;
  scope: string;
}
export interface CarbonDetail {
  activity_id: string;
  stage: string;
  quantity: number;
  activity_unit: string;
  factor_id: string;
  factor_value: number;
  factor_status: string;
  emissions_kgCO2e: number;
  factor_source: string;
  factor_year: string;
  description?: string;
  derivation?: string;
  data_status: string;
}
export interface CarbonResult {
  status: "calculated";
  summary: {
    total_kgCO2e: number;
    by_stage_kgCO2e: Record<string, number>;
    included_stages: string[];
    missing_stages: string[];
    scope_complete: boolean;
    contains_illustrative_factors: boolean;
    contains_illustrative_activities: boolean;
    interpretation: string;
    allocation: string;
  };
  details: CarbonDetail[];
  factor_provenance: string;
}
export interface SafetyResult {
  scope: string;
  gates: { route_id: string; eligible: boolean; reason_codes: string[] }[];
}
export interface DecisionCandidate {
  route_id: string;
  route_name: string;
  carbon_kgco2e: number;
  npv_cny: number;
  recovered_kg: number;
  technical_score: number;
  eligible: boolean;
  reason_codes: string[];
  weighted_score: number | null;
  utility_components: Record<string, number>;
  pareto_optimal: boolean;
}
export interface RecommendationResult {
  status: string;
  route_id: string | null;
  parameter_status: string;
  weights: Record<string, number>;
}
export interface AssessmentResponse {
  manual?: import("./manual").ManualResponse;
  battery_id: string;
  battery_id_scope: string;
  scenario_id: string;
  data_quality: BMSValidationResponse | Unavailable;
  soh: SOHResult | Unavailable;
  rul: RULResult;
  explainability: ExplainabilityResult | Unavailable;
  carbon: CarbonResult | Unavailable;
  safety: SafetyResult;
  candidate_paths: DecisionCandidate[];
  recommendation: RecommendationResult;
  decision_reason: string[];
  automatic_model_to_pack_transfer: boolean;
  display_notice: string;
  limitations: string[];
}
