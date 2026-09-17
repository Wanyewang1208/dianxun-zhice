import type { AssessmentResponse } from "../types/api";
import type { ManualResponse } from "../types/manual";
// Normalize transport variants once. The original manual evidence remains intact.
export function normalizeAssessment(
  raw: AssessmentResponse | ManualResponse,
): AssessmentResponse {
  if (!("input_mode" in raw) || raw.input_mode !== "manual")
    return raw as AssessmentResponse;
  const m = raw as ManualResponse;
  if (
    !m.input_snapshot ||
    !m.effective_condition ||
    !m.field_sources ||
    !m.prototype_assumptions ||
    !m.soh ||
    !m.rul ||
    !m.residual_value ||
    !Array.isArray(m.residual_value.missing_components) ||
    !m.residual_value.component_scores ||
    !Array.isArray(m.data_quality?.notes) ||
    !Array.isArray(m.candidate_paths) ||
    !Array.isArray(m.safety?.reason_codes)
  )
    throw new ApiError("incomplete", "手动评估返回不完整。");
  for (const n of [
    m.soh.calculated_soh,
    m.rul.predicted_rul_cycles,
    m.residual_value.index,
  ])
    if (n !== null && !Number.isFinite(n))
      throw new ApiError("incomplete", "手动评估数值无效。");
  const unavailable = {
    status: "not_available" as const,
    reason: "手动模式不使用 NASA 模型；详见手动计算结果。",
  };
  return {
    manual: m,
    battery_id: m.battery_id ?? "N/A",
    battery_id_scope: m.battery_id_scope,
    scenario_id: m.data_kind,
    data_quality:
      m.data_quality.bms.status === "checked"
        ? m.data_quality.bms
        : {
            status: "not_provided",
            reason: "No BMS supplied; manual schema validated",
          },
    soh: unavailable,
    rul: {
      status: "not_available",
      battery_id: m.battery_id ?? "N/A",
      cycle: Number(m.input_snapshot.cycle_count ?? 0),
      predicted_rul_cycles: null,
      unit: m.rul.unit,
      reason: m.rul.reason,
      operating_condition_caution: m.rul.reason,
      validation_status: "manual",
    },
    explainability: m.explainability,
    carbon: m.carbon,
    safety: {
      scope: m.safety.status,
      gates: m.candidate_paths.map((p) => ({
        route_id: p.route_id,
        eligible: p.eligible,
        reason_codes: p.reason_codes,
      })),
    },
    candidate_paths: m.candidate_paths.map((p) => ({
      ...p,
      route_name: p.route_name ?? routeNames[p.route_id],
      utility_components: p.utility_components ?? {},
    })) as AssessmentResponse["candidate_paths"],
    recommendation: { ...m.recommendation, weights: {} },
    decision_reason: m.decision_reason,
    automatic_model_to_pack_transfer: m.automatic_model_to_pack_transfer,
    display_notice: m.display_notice,
    limitations: m.limitations,
  };
}
import { ApiError } from "./api";
export const format = (n: unknown, d = 2) =>
  typeof n === "number" && Number.isFinite(n) ? n.toFixed(d) : "N/A";
export const routeNames: Record<string, string> = {
  continue_use: "Continue Use",
  repair_then_use: "Repair & Reuse",
  second_life: "Second-Life Utilization",
  recycle: "Recycling",
};
export function assessmentAdapter(r: AssessmentResponse) {
  if (
    !r ||
    typeof r.battery_id !== "string" ||
    !r.soh ||
    !r.rul ||
    !r.carbon ||
    !r.data_quality ||
    !r.explainability ||
    !Array.isArray(r.safety?.gates) ||
    !Array.isArray(r.candidate_paths) ||
    !r.recommendation ||
    !Array.isArray(r.decision_reason) ||
    !Array.isArray(r.limitations)
  )
    throw new ApiError("incomplete", "后端返回缺少评估模块，未替换当前结果。");
  if (
    (r.soh.status === "available" &&
      !Number.isFinite(r.soh.predicted_soh_pct)) ||
    (r.rul.status === "available" &&
      !Number.isFinite(r.rul.predicted_rul_cycles)) ||
    (r.carbon.status === "calculated" &&
      (!Number.isFinite(r.carbon.summary?.total_kgCO2e) ||
        !r.carbon.summary.by_stage_kgCO2e ||
        !Array.isArray(r.carbon.details))) ||
    (r.explainability.status === "available" &&
      (!Array.isArray(r.explainability.contributions) ||
        r.explainability.contributions.some(
          (c) => !Number.isFinite(c.shap_soh_pp),
        )))
  )
    throw new ApiError("incomplete", "后端返回的数值或列表不完整。");
  const strings = (x: unknown): x is string[] =>
    Array.isArray(x) && x.every((s) => typeof s === "string");
  const bad = () => {
    throw new ApiError(
      "incomplete",
      "后端返回的评估结构不完整，未替换当前结果。",
    );
  };
  if (
    !strings(r.limitations) ||
    !strings(r.decision_reason) ||
    typeof r.display_notice !== "string" ||
    typeof r.scenario_id !== "string" ||
    !r.recommendation.weights ||
    typeof r.recommendation.weights !== "object"
  )
    bad();
  if (
    !["available", "not_available", "not_provided"].includes(r.soh.status) ||
    !["available", "not_available"].includes(r.rul.status) ||
    !["calculated", "not_available", "not_provided"].includes(
      r.carbon.status,
    ) ||
    !["checked", "not_available", "not_provided"].includes(
      r.data_quality.status,
    ) ||
    !["available", "not_available", "not_provided"].includes(
      r.explainability.status,
    )
  )
    bad();
  if (
    r.data_quality.status === "checked" &&
    (!r.data_quality.summary ||
      typeof r.data_quality.summary.schema_ready !== "boolean" ||
      !Array.isArray(r.data_quality.issues))
  )
    bad();
  if (
    r.carbon.status === "calculated" &&
    (!strings(r.carbon.summary.missing_stages) ||
      Object.values(r.carbon.summary.by_stage_kgCO2e).some(
        (n) => !Number.isFinite(n),
      ) ||
      r.carbon.details.some(
        (d) =>
          !d ||
          typeof d.activity_id !== "string" ||
          typeof d.factor_source !== "string" ||
          !Number.isFinite(d.emissions_kgCO2e),
      ))
  )
    bad();
  if (
    r.safety.gates.some(
      (g) =>
        !g ||
        typeof g.route_id !== "string" ||
        typeof g.eligible !== "boolean" ||
        !strings(g.reason_codes),
    )
  )
    bad();
  if (
    r.candidate_paths.some(
      (p) =>
        !p ||
        typeof p.route_id !== "string" ||
        typeof p.eligible !== "boolean" ||
        !strings(p.reason_codes) ||
        !p.utility_components ||
        Object.values(p.utility_components).some((n) => !Number.isFinite(n)) ||
        (p.weighted_score !== null &&
          (!Number.isFinite(p.weighted_score) ||
            p.weighted_score < 0 ||
            p.weighted_score > 1)),
    )
  )
    bad();
  const selected = r.candidate_paths.find(
    (p) => p.route_id === r.recommendation.route_id,
  );
  if (r.recommendation.route_id !== null && !selected)
    throw new ApiError("incomplete", "推荐路径与候选路径不一致。");
  return {
    manual: r.manual ?? null,
    soh: r.manual
      ? r.manual.soh.calculated_soh
      : r.soh.status === "available"
        ? r.soh.predicted_soh_pct
        : null,
    rul: r.manual
      ? r.manual.rul.predicted_rul_cycles
      : r.rul.status === "available"
        ? r.rul.predicted_rul_cycles
        : null,
    healthLabel: r.manual ? "Capacity SOH · 手填容量比" : "SOH · NASA 模型预测",
    lifeLabel: r.manual
      ? r.manual.rul.status === "prototype_assumption"
        ? "Demo 假设等效循环"
        : "手动模式寿命证据不足"
      : "RUL · 参考放电循环",
    carbon:
      r.carbon.status === "calculated"
        ? r.carbon.summary.total_kgCO2e / 1000
        : null,
    selected,
    decision: r.recommendation.route_id
      ? routeNames[r.recommendation.route_id] || selected?.route_name || "N/A"
      : "HOLD",
    score:
      selected?.weighted_score == null ? null : selected.weighted_score * 100,
    contributions:
      r.explainability.status === "available"
        ? [...r.explainability.contributions].sort(
            (a, b) => Math.abs(b.shap_soh_pp) - Math.abs(a.shap_soh_pp),
          )
        : [],
    stages:
      r.carbon.status === "calculated"
        ? Object.entries(r.carbon.summary.by_stage_kgCO2e)
        : [],
  };
}
