import { t } from "../i18n";
import { useAssessment } from "../context/AssessmentContext";
import { format, routeNames } from "../lib/assessmentAdapter";
import type { ModuleId } from "../types/battery";
export const manualFields = [
  ["battery_brand", "电池品牌", "text"],
  ["battery_type", "电池类型", "LFP,NMC,Other"],
  ["vehicle_brand", "车辆品牌", "text"],
  ["vehicle_model", "车辆型号", "text"],
  ["rated_capacity_kwh", "额定容量 (kWh)", "number"],
  ["current_available_capacity_kwh", "当前可用容量 (kWh)", "number"],
  ["cycle_count", "循环次数", "number"],
  ["mileage_km", "里程 (km)", "number"],
  ["new_battery_reference_price", "新电池参考价格 (CNY)", "number"],
  ["measured_soh", "专业检测 SOH 声明 (%)", "number"],
  ["primary_charging_method", "主要充电方式", "home_ac,public_ac,dc_fast"],
  ["fast_charge_ratio", "快充比例 (%)", "number"],
  ["average_daily_mileage_km", "日均里程 (km)", "number"],
  ["annual_mileage_km", "年里程 (km)", "number"],
  ["average_environment_temperature_c", "平均环境温度 (°C)", "number"],
  ["usual_charge_upper_soc", "充电上限 SOC (%)", "number"],
  ["usual_discharge_lower_soc", "放电下限 SOC (%)", "number"],
  ["region", "使用地区", "text"],
  ["fault_code_present", "是否有故障码", "boolean"],
  ["thermal_event_history", "是否有热事件历史", "boolean"],
  ["current_temperature_c", "当前温度 (°C)", "number"],
  ["historical_max_temperature_c", "历史最高温度 (°C)", "number"],
  ["max_cell_voltage_v", "最高单体电压 (V)", "number"],
  ["min_cell_voltage_v", "最低单体电压 (V)", "number"],
  ["cell_voltage_delta_mv", "单体压差 (mV)", "number"],
  ["internal_resistance_mohm", "内阻 (mΩ)", "number"],
] as const;
export function ManualForm() {
  const a = useAssessment();
  const r = a.manualRequest;
  if (!r) return null;
  return (
    <details className="manual-form" open>
      <summary>{t("Manual Input ·")}{t(" ")}
        {t(r.data_kind === "demo"
          ? "明确 Demo 假设"
          : "用户声明，不自动填充未知值")}
      </summary>
      <p>{t("品牌、类型、里程和使用工况用于记录与报告，未作为已验证整车预测模型输入。额定容量必填；其他空项发送 null。")}</p>
      {t(r.prototype_assumptions && (
        <p className="source-notice">{t("Demo assumptions: reference cycle life")}{t(" ")}
          {t(r.prototype_assumptions.reference_cycle_life)}{t("; safety factor")}{t(" ")}
          {t(r.prototype_assumptions.safety_factor)}{t("; consistency factor")}{t(" ")}
          {t(r.prototype_assumptions.consistency_factor)}{t("。仅用于原型算术估值。")}</p>
      ))}
      <div className="manual-grid">
        {t(manualFields.map(([key, label, type]) => (
          <label key={key}>
            {t(label)}
            {t(type === "text" || type === "number" ? (
              <input
                aria-label={t(label)}
                type={type}
                step={key === "cycle_count" ? "1" : "any"}
                value={String(r.manual_input[key] ?? "")}
                disabled={a.assessmentStatus === "loading" || a.validating}
                onChange={(e) =>
                  a.setManualField(
                    key,
                    e.target.value === ""
                      ? null
                      : type === "number"
                        ? Number(e.target.value)
                        : e.target.value,
                  )
                }
              />
            ) : (
              <select
                aria-label={t(label)}
                value={String(r.manual_input[key] ?? "")}
                disabled={a.assessmentStatus === "loading" || a.validating}
                onChange={(e) =>
                  a.setManualField(
                    key,
                    e.target.value === ""
                      ? null
                      : type === "boolean"
                        ? e.target.value === "true"
                        : e.target.value,
                  )
                }
              >
                <option value="">{t("未知 / 未填写")}</option>
                {t((type === "boolean" ? ["true", "false"] : type.split(",")).map(
                  (v) => (
                    <option key={v} value={v}>
                      {t(v === "true" ? "是" : v === "false" ? "否" : v)}
                    </option>
                  ),
                ))}
              </select>
            ))}
          </label>
        )))}
      </div>
    </details>
  );
}
function Values({ items, raw = false }: { items: [string, unknown][]; raw?: boolean }) {
  return (
    <dl className="live-values">
      {t(items.map(([k, v]) => (
        <div key={k}>
          <dt>{t(k)}</dt>
          <dd>{v == null ? t("N/A") : typeof v === "boolean" ? t(String(v)) : raw ? String(v) : t(String(v))}</dd>
        </div>
      )))}
    </dl>
  );
}
export function ManualPassport() {
  const { view } = useAssessment();
  const m = view?.manual;
  if (!m) return null;
  return (
    <section className="passport surface">
      <h2>{t("Battery Digital Passport")}</h2>
      <p className="source-notice">{t("LIVE · Manual ")}{t(m.data_kind)}</p>
      <h3>{m.battery_id ?? t("Battery ID · N/A")}</h3>
      <Values
        raw
        items={[
          ["Capacity SOH", `${format(view.soh, 1)} %`],
          ["Battery brand", m.input_snapshot.battery_brand],
          ["Battery type", m.input_snapshot.battery_type],
          ["Rated capacity kWh", m.input_snapshot.rated_capacity_kwh],
          [
            "Current capacity kWh",
            m.input_snapshot.current_available_capacity_kwh,
          ],
          ["Cycle count", m.input_snapshot.cycle_count],
          ["Mileage km", m.input_snapshot.mileage_km],
          ["Residual Value index", format(m.residual_value.index)],
        ]}
      />
      <p>{t("Prototype Technical Estimation · 手填容量计算，不代表 NASA 推理或真实整车认证。")}</p>
    </section>
  );
}
export function ManualResults({ module }: { module: ModuleId | "assessment" }) {
  const a = useAssessment();
  const m = a.view?.manual;
  if (!m || !a.assessmentResult) return null;
  const all = module === "report" || module === "assessment";
  const show = (id: ModuleId) => all || module === id;
  const v = m.residual_value;
  return (
    <div className={all ? "live-results assessment-report" : "live-results"}>
      <p className="source-notice">{t("Data Source: Live Backend · Manual / ")}{t(m.data_kind)}{t(" · request")}{t(" ")}
        {a.assessmentResult.request_id}
      </p>
      <p>{t(m.display_notice)}</p>
      {t(all && (
        <section>
          <h3>{t("Vehicle & Battery / Usage")}</h3>
          <Values
            raw
            items={manualFields.map(([k, label]) => [
              label,
              m.input_snapshot[k],
            ])}
          />
          <h3>{t("Data Validation")}</h3>
          <p>
            {t(m.data_quality.manual)}{t(" · BMS used:")}{t(" ")}
            {t(String(m.data_quality.bms_used_for_condition))}
          </p>
          {t(m.data_quality.bms.status === "checked" ? (
            <Values
              items={[
                ["Accepted", m.data_quality.bms.summary.accepted_rows],
                ["Rejected", m.data_quality.bms.summary.rejected_rows],
                ["Schema ready", m.data_quality.bms.summary.schema_ready],
              ]}
            />
          ) : (
            <p>{t("BMS not provided · 手动输入无需 CSV")}</p>
          ))}
          {t(m.data_quality.notes.map((n, i) => (
            <p key={i}>{t(n)}</p>
          )))}
          <h4>{t("Effective Condition / Field Sources")}</h4>
          <Values
            items={Object.entries(m.effective_condition).map(([k, n]) => [
              k,
              `${n ?? "N/A"} · ${m.field_sources[k] ?? "missing"}`,
            ])}
          />
        </section>
      ))}
      {t(show("health") && (
        <section>
          <h3>{t("Battery Health · Capacity Ratio")}</h3>
          <Values
            items={[
              ["Calculated SOH (%)", format(m.soh.calculated_soh)],
              ["Measured SOH declaration (%)", format(m.soh.measured_soh)],
              ["Difference (pp)", format(m.soh.difference_pp)],
              ["Rated capacity kWh", m.input_snapshot.rated_capacity_kwh],
              [
                "Current capacity kWh",
                m.input_snapshot.current_available_capacity_kwh,
              ],
            ]}
          />
          <p>{t("SOH = Qcurrent / Qinitial × 100%")}</p>
          <p>{t(m.soh.measurement_notice)}</p>
          <p>{t(m.soh.reason)}</p>
        </section>
      ))}
      {t(show("life") && (
        <section>
          <h3>{t("Remaining Life")}</h3>
          <Values
            items={[
              ["Status", m.rul.status],
              ["Cycles", format(m.rul.predicted_rul_cycles)],
              ["Unit", m.rul.unit],
              ["Method", m.rul.method],
            ]}
          />
          <p>{t(m.rul.reason)}</p>
          <p>{t("Confidence / Calendar life / Prediction curve: N/A")}</p>
        </section>
      ))}
      {t((show("health") || module === "life") && (
        <section>
          <h3>{t("Explainability")}</h3>
          <p>
            {t(m.explainability.status)}{t(" · ")}{t(m.explainability.reason)}
          </p>
          <p>{t("How is this calculated? ")}{t(m.soh.method)}</p>
        </section>
      ))}
      {t(show("carbon") && (
        <section>
          <h3>{t("Carbon Passport")}</h3>
          <p>{t("C = Σ(Activity Data × Emission Factor)")}</p>
          {t(m.carbon.status === "calculated" ? (
            <>
              <Values
                items={[
                  ["Total kgCO₂e", format(m.carbon.summary.total_kgCO2e)],
                  ...Object.entries(m.carbon.summary.by_stage_kgCO2e),
                ]}
              />
              <p>{t(m.carbon.summary.interpretation)}</p>
              <p>{t(m.carbon.summary.allocation)}</p>
              <p>{t(m.carbon.factor_provenance)}</p>
              {t(m.carbon.details.map((d) => (
                <p key={d.activity_id}>
                  {t(d.activity_id)}{t(": ")}{t(d.quantity)} {t(d.activity_unit)}{t(" ×")}{t(" ")}
                  {t(d.factor_value)}{t(" = ")}{t(format(d.emissions_kgCO2e))}{t(" kgCO₂e ·")}{t(" ")}
                  {t(d.factor_status)}{t(" · ")}{t(d.factor_year)}{t(" ·")}{t(" ")}
                  {t(d.factor_source || "Source unavailable")}
                </p>
              )))}
            </>
          ) : (
            <p>{t("Not Available · ")}{t(m.carbon.reason)}</p>
          ))}
        </section>
      ))}
      {t(show("decision") && (
        <section>
          <h3>{t("Safety / Green Decision")}</h3>
          <p>
            {t(m.safety.status)}{t(" · Certified: ")}{t(String(m.safety.certified))}
          </p>
          {t(m.safety.reason_codes.map((s) => (
            <p key={s}>{t(s)}</p>
          )))}
          <Values
            items={m.candidate_paths.map((p) => [
              routeNames[p.route_id] ?? p.route_id,
              `${p.eligible ? "Prototype eligible" : "HOLD"} · score ${p.weighted_score === null ? "N/A" : format(p.weighted_score * 100)} · ${p.reason_codes.join(", ")}`,
            ])}
          />
          <h4>{t(a.view?.decision)}</h4>
          {t(m.decision_reason.map((s, i) => (
            <p key={i}>{t(s)}</p>
          )))}
          <p>{t(m.recommendation.parameter_status)}</p>
        </section>
      ))}
      {t((show("decision") || all) && (
        <section>
          <h3>{t("Residual Value · Prototype Technical Estimation")}</h3>
          <Values
            items={[
              ["Status", v.status],
              ["Index / 100", format(v.index)],
              [
                "Value range CNY",
                v.estimated_value_range_cny
                  ? `${format(v.estimated_value_range_cny.lower)} – ${format(v.estimated_value_range_cny.upper)}`
                  : "N/A",
              ],
              ["Missing components", v.missing_components.join(", ") || "None"],
            ]}
          />
          <p>{t(v.index_formula)}</p>
          <p>{t(v.price_formula)}</p>
          <Values
            items={Object.entries(v.component_scores).map(([k, n]) => [
              `${k} / 100`,
              format(n),
            ])}
          />
          <p>{t("未知分项数学边界：")}{t(format(v.index_bounds?.lower))}{t(" –")}{t(" ")}
            {t(format(v.index_bounds?.upper))}{t("；不是完整价值指数或价格置信区间。")}</p>
          <p>{t(v.parameter_status)}</p>
          <p>{t(v.band_basis)}</p>
          <p>{t(v.disclaimer)}</p>
          <h4>{t("Explicit Demo Assumptions")}</h4>
          <Values items={Object.entries(m.prototype_assumptions)} />
          <p>{t("Second-life potential: ")}{t(m.second_life_potential.level ?? "N/A")}{t(" ·")}{t(" ")}
            {t(m.second_life_potential.reason)}
          </p>
        </section>
      ))}
      <section>
        <h3>{t("Model / Demo Boundary")}</h3>
        <p>{t("BMS 上传主要用于数据质量检查。NASA SOH/RUL/SHAP 仅用于公开实验电芯模式；手动模式不套用这些模型。Carbon 需明确场景活动与因子，Green Decision 为原型决策逻辑，尚未完成真实整车大规模验证。")}</p>
        {t(m.limitations.map((s, i) => (
          <p key={i}>{t(s)}</p>
        )))}
      </section>
      {t(all && (
        <button
          className="primary-button compact print-button"
          onClick={() => window.print()}
        >{t("Export PDF / 打印报告")}</button>
      ))}
    </div>
  );
}
