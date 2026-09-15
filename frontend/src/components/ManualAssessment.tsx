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
      <summary>
        Manual Input ·{" "}
        {r.data_kind === "demo"
          ? "明确 Demo 假设"
          : "用户声明，不自动填充未知值"}
      </summary>
      <p>
        品牌、类型、里程和使用工况用于记录与报告，未作为已验证整车预测模型输入。额定容量必填；其他空项发送
        null。
      </p>
      {r.prototype_assumptions && (
        <p className="source-notice">
          Demo assumptions: reference cycle life{" "}
          {r.prototype_assumptions.reference_cycle_life}; safety factor{" "}
          {r.prototype_assumptions.safety_factor}; consistency factor{" "}
          {r.prototype_assumptions.consistency_factor}。仅用于原型算术估值。
        </p>
      )}
      <div className="manual-grid">
        {manualFields.map(([key, label, type]) => (
          <label key={key}>
            {label}
            {type === "text" || type === "number" ? (
              <input
                aria-label={label}
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
                aria-label={label}
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
                <option value="">未知 / 未填写</option>
                {(type === "boolean" ? ["true", "false"] : type.split(",")).map(
                  (v) => (
                    <option key={v} value={v}>
                      {v === "true" ? "是" : v === "false" ? "否" : v}
                    </option>
                  ),
                )}
              </select>
            )}
          </label>
        ))}
      </div>
    </details>
  );
}
function Values({ items }: { items: [string, unknown][] }) {
  return (
    <dl className="live-values">
      {items.map(([k, v]) => (
        <div key={k}>
          <dt>{k}</dt>
          <dd>{v == null ? "N/A" : String(v)}</dd>
        </div>
      ))}
    </dl>
  );
}
export function ManualPassport() {
  const { view } = useAssessment();
  const m = view?.manual;
  if (!m) return null;
  return (
    <section className="passport surface">
      <h2>Battery Digital Passport</h2>
      <p className="source-notice">LIVE · Manual {m.data_kind}</p>
      <h3>{m.battery_id ?? "Battery ID · N/A"}</h3>
      <Values
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
      <p>
        Prototype Technical Estimation · 手填容量计算，不代表 NASA
        推理或真实整车认证。
      </p>
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
      <p className="source-notice">
        Data Source: Live Backend · Manual / {m.data_kind} · request{" "}
        {a.assessmentResult.request_id}
      </p>
      <p>{m.display_notice}</p>
      {all && (
        <section>
          <h3>Vehicle & Battery / Usage</h3>
          <Values
            items={manualFields.map(([k, label]) => [
              label,
              m.input_snapshot[k],
            ])}
          />
          <h3>Data Validation</h3>
          <p>
            {m.data_quality.manual} · BMS used:{" "}
            {String(m.data_quality.bms_used_for_condition)}
          </p>
          {m.data_quality.bms.status === "checked" ? (
            <Values
              items={[
                ["Accepted", m.data_quality.bms.summary.accepted_rows],
                ["Rejected", m.data_quality.bms.summary.rejected_rows],
                ["Schema ready", m.data_quality.bms.summary.schema_ready],
              ]}
            />
          ) : (
            <p>BMS not provided · 手动输入无需 CSV</p>
          )}
          {m.data_quality.notes.map((n, i) => (
            <p key={i}>{n}</p>
          ))}
          <h4>Effective Condition / Field Sources</h4>
          <Values
            items={Object.entries(m.effective_condition).map(([k, n]) => [
              k,
              `${n ?? "N/A"} · ${m.field_sources[k] ?? "missing"}`,
            ])}
          />
        </section>
      )}
      {show("health") && (
        <section>
          <h3>Battery Health · Capacity Ratio</h3>
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
          <p>SOH = Qcurrent / Qinitial × 100%</p>
          <p>{m.soh.measurement_notice}</p>
          <p>{m.soh.reason}</p>
        </section>
      )}
      {show("life") && (
        <section>
          <h3>Remaining Life</h3>
          <Values
            items={[
              ["Status", m.rul.status],
              ["Cycles", format(m.rul.predicted_rul_cycles)],
              ["Unit", m.rul.unit],
              ["Method", m.rul.method],
            ]}
          />
          <p>{m.rul.reason}</p>
          <p>Confidence / Calendar life / Prediction curve: N/A</p>
        </section>
      )}
      {(show("health") || module === "life") && (
        <section>
          <h3>Explainability</h3>
          <p>
            {m.explainability.status} · {m.explainability.reason}
          </p>
          <p>How is this calculated? {m.soh.method}</p>
        </section>
      )}
      {show("carbon") && (
        <section>
          <h3>Carbon Passport</h3>
          <p>C = Σ(Activity Data × Emission Factor)</p>
          {m.carbon.status === "calculated" ? (
            <>
              <Values
                items={[
                  ["Total kgCO₂e", format(m.carbon.summary.total_kgCO2e)],
                  ...Object.entries(m.carbon.summary.by_stage_kgCO2e),
                ]}
              />
              <p>{m.carbon.summary.interpretation}</p>
              <p>{m.carbon.summary.allocation}</p>
              <p>{m.carbon.factor_provenance}</p>
              {m.carbon.details.map((d) => (
                <p key={d.activity_id}>
                  {d.activity_id}: {d.quantity} {d.activity_unit} ×{" "}
                  {d.factor_value} = {format(d.emissions_kgCO2e)} kgCO₂e ·{" "}
                  {d.factor_status} · {d.factor_year} ·{" "}
                  {d.factor_source || "Source unavailable"}
                </p>
              ))}
            </>
          ) : (
            <p>Not Available · {m.carbon.reason}</p>
          )}
        </section>
      )}
      {show("decision") && (
        <section>
          <h3>Safety / Green Decision</h3>
          <p>
            {m.safety.status} · Certified: {String(m.safety.certified)}
          </p>
          {m.safety.reason_codes.map((s) => (
            <p key={s}>{s}</p>
          ))}
          <Values
            items={m.candidate_paths.map((p) => [
              routeNames[p.route_id] ?? p.route_id,
              `${p.eligible ? "Prototype eligible" : "HOLD"} · score ${p.weighted_score === null ? "N/A" : format(p.weighted_score * 100)} · ${p.reason_codes.join(", ")}`,
            ])}
          />
          <h4>{a.view?.decision}</h4>
          {m.decision_reason.map((s, i) => (
            <p key={i}>{s}</p>
          ))}
          <p>{m.recommendation.parameter_status}</p>
        </section>
      )}
      {(show("decision") || all) && (
        <section>
          <h3>Residual Value · Prototype Technical Estimation</h3>
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
          <p>{v.index_formula}</p>
          <p>{v.price_formula}</p>
          <Values
            items={Object.entries(v.component_scores).map(([k, n]) => [
              `${k} / 100`,
              format(n),
            ])}
          />
          <p>
            未知分项数学边界：{format(v.index_bounds?.lower)} –{" "}
            {format(v.index_bounds?.upper)}；不是完整价值指数或价格置信区间。
          </p>
          <p>{v.parameter_status}</p>
          <p>{v.band_basis}</p>
          <p>{v.disclaimer}</p>
          <h4>Explicit Demo Assumptions</h4>
          <Values items={Object.entries(m.prototype_assumptions)} />
          <p>
            Second-life potential: {m.second_life_potential.level ?? "N/A"} ·{" "}
            {m.second_life_potential.reason}
          </p>
        </section>
      )}
      <section>
        <h3>Model / Demo Boundary</h3>
        <p>
          BMS 上传主要用于数据质量检查。NASA SOH/RUL/SHAP
          仅用于公开实验电芯模式；手动模式不套用这些模型。Carbon
          需明确场景活动与因子，Green Decision
          为原型决策逻辑，尚未完成真实整车大规模验证。
        </p>
        {m.limitations.map((s, i) => (
          <p key={i}>{s}</p>
        ))}
      </section>
      {all && (
        <button
          className="primary-button compact print-button"
          onClick={() => window.print()}
        >
          Export PDF / 打印报告
        </button>
      )}
    </div>
  );
}
