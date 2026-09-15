import type {
  AssessmentRequest,
  BMSValidationResponse,
  CarbonResult,
  Unavailable,
  DecisionCandidate,
} from "./api";
export type ManualInput = Record<string, string | number | boolean | null> & {
  rated_capacity_kwh: number | null;
};
export interface ManualRequest {
  input_mode: "manual";
  data_kind: "user_declared" | "demo";
  manual_input: ManualInput;
  bms?: AssessmentRequest["bms"];
  carbon?: AssessmentRequest["carbon"];
  prototype_assumptions?: {
    reference_cycle_life: number;
    safety_factor: number;
    consistency_factor: number;
  };
}
export interface ResidualValue {
  status: string;
  index: number | null;
  index_bounds: { lower: number; upper: number; kind: string } | null;
  missing_components: string[];
  component_scores: Record<string, number | null>;
  weights: Record<string, number>;
  estimated_value_range_cny: {
    lower: number;
    upper: number;
    midpoint: number;
    kind: string;
  } | null;
  index_formula: string;
  price_formula: string;
  parameter_status: string;
  value_basis: string;
  band_basis: string;
  disclaimer: string;
}
export interface ManualResponse {
  input_mode: "manual";
  data_kind: "user_declared" | "demo";
  battery_id: string | null;
  battery_id_scope: string;
  input_snapshot: ManualInput;
  effective_condition: Record<string, string | number | boolean | null>;
  field_sources: Record<string, string>;
  prototype_assumptions: Record<string, number>;
  data_quality: {
    manual: string;
    bms: BMSValidationResponse | { status: "not_provided" };
    bms_used_for_condition: boolean;
    notes: string[];
  };
  soh: {
    status: string;
    calculated_soh: number | null;
    measured_soh: number | null;
    difference_pp: number | null;
    method: string;
    measurement_notice: string;
    reason: string | null;
  };
  rul: {
    status: string;
    predicted_rul_cycles: number | null;
    unit: string;
    method: string | null;
    reason: string;
  };
  explainability: Unavailable;
  carbon: CarbonResult | Unavailable;
  safety: { status: string; reason_codes: string[]; certified: boolean };
  residual_value: ResidualValue;
  second_life_potential: {
    status: string;
    level: string | null;
    reason: string;
  };
  candidate_paths: (Partial<DecisionCandidate> &
    Pick<
      DecisionCandidate,
      "route_id" | "eligible" | "weighted_score" | "reason_codes"
    >)[];
  recommendation: {
    status: string;
    route_id: string | null;
    parameter_status: string;
  };
  decision_reason: string[];
  display_notice: string;
  limitations: string[];
  automatic_model_to_pack_transfer: boolean;
}
