export type SafetyFlag = boolean | null;
export interface Scenario {
  scenario_id: string;
  data_kind: 'illustrative' | 'vehicle_unvalidated' | string;
  assessed_at?: string;
  inspection_at?: string;
  health?: {soh_pct?: number | null; rul_cycles?: number | null; rul_unit?: 'reference_discharge_cycles'};
  safety?: Partial<Record<'critical_event'|'electrical_pass'|'thermal_pass'|'mechanical_pass'|'post_repair_pass'|'second_life_approved'|'recycler_approved'|'transport_approved', SafetyFlag>>;
}
export interface RouteResult {
  route_id: 'continue_use'|'repair_then_use'|'second_life'|'recycle';
  route_name: string;
  eligible: boolean;
  reason_codes: string[];
  weighted_score: number | null;
  pareto_optimal: boolean;
  carbon_kgco2e: number;
  npv_cny: number;
  recovered_kg: number;
  technical_score: number;
  illustrative_service_limit_kwh: number | null;
}
export interface DecisionResult {
  schema_version: '0.3';
  scenario_id: string;
  status: 'simulation_recommendation'|'hold_for_evidence_or_professional_review';
  recommended_route: RouteResult['route_id'] | null;
  feasible_routes: string[];
  pareto_routes: string[];
  routes: RouteResult[];
  policy_status: 'illustrative_not_validated';
}
export interface ReportRequest {
  model_case: {battery_id: string; cycle: number};
  scenario: Scenario;
  weights?: {carbon: number; economic: number; resource: number; technical: number};
}
