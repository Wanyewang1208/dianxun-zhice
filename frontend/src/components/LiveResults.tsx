import { ManualResults, ManualPassport } from "./ManualAssessment";
import { useAssessment } from "../context/AssessmentContext";
import { format, routeNames } from "../lib/assessmentAdapter";
import type { ModuleId } from "../types/battery";
function Values({ items }: { items: [string, unknown][] }) {
  return (
    <dl className="live-values">
      {items.map(([name, value]) => (
        <div key={name}>
          <dt>{name}</dt>
          <dd>{value == null ? "N/A" : String(value)}</dd>
        </div>
      ))}
    </dl>
  );
}
export function LivePassport() {
  const { assessmentResult, view } = useAssessment();
  if (!assessmentResult || !view) return null;
  if (view.manual) return <ManualPassport />;
  const r = assessmentResult.data;
  return (
    <section className="passport surface" aria-label="电池数字护照">
      <div className="passport-heading">
        <h2>Battery Digital Passport</h2>
        <span className="mint">LIVE</span>
      </div>
      <div className="passport-id">
        <span className="micro-label">NASA EXPERIMENTAL CELL</span>
        <strong>{r.battery_id}</strong>
      </div>
      <div className="passport-body">
        <div className="passport-readings">
          <div>
            <span>State of Health</span>
            <strong className="mint">
              {format(view.soh, 1)}
              <small>%</small>
            </strong>
          </div>
          <div>
            <span>Remaining Useful Life</span>
            <strong className="cyan">
              {format(view.rul, 1)}
              <small> reference cycles</small>
            </strong>
          </div>
          <div>
            <span>Scenario Carbon · {r.scenario_id}</span>
            <strong>
              {format(view.carbon)}
              <small> tCO₂e</small>
            </strong>
          </div>
        </div>
        <figure>
          <img
            src="/assets/battery-pack.png"
            width="1024"
            height="1024"
            alt="概念渲染，非被测电池实物"
          />
          <figcaption>CONCEPT VISUAL · 非实物</figcaption>
        </figure>
      </div>
      <Values
        items={[
          ["Vehicle / Mileage", "N/A"],
          ["Pack capacity / Chemistry", "N/A"],
          ["NASA cycle", r.rul.cycle],
          ["Vehicle safety", "UNKNOWN"],
        ]}
      />
      <p className="demo-note">
        公开实验电芯 · 未验证整车迁移。碳足迹属于另一模拟场景。
      </p>
    </section>
  );
}
export function LivePreviews({
  onModule,
}: {
  onModule: (m: ModuleId) => void;
}) {
  const { view, assessmentResult } = useAssessment();
  if (!view || !assessmentResult) return null;
  return (
    <section id="technology" className="technology">
      <div className="section-heading">
        <h2>
          Technology Preview <span>让结论可复核</span>
        </h2>
      </div>
      <div className="technology-grid">
        {(
          [
            [
              "health",
              "Battery Health",
              `${format(view.soh, 1)} %`,
              "SOH = Qcurrent / Qinitial × 100% · 模型预测与容量比值分别展示",
            ],
            [
              "life",
              "Remaining Life",
              `${format(view.rul, 1)} cycles`,
              view.lifeLabel + " · 真实预测曲线未提供",
            ],
            [
              "carbon",
              "Carbon Intelligence",
              `${format(view.carbon)} tCO₂e`,
              "C = Σ(Activity Data × Emission Factor) · 模拟情景核算",
            ],
          ] as const
        ).map(([id, title, value, note]) => (
          <article className="technology-card surface" key={id}>
            <h3>{title}</h3>
            <div className="preview-result">
              <strong className="mint">{value}</strong>
            </div>
            <p>{note}</p>
            <button onClick={() => onModule(id)}>查看结果 →</button>
          </article>
        ))}
      </div>
    </section>
  );
}
export function LiveDecisionSummary({
  onDecision,
}: {
  onDecision: () => void;
}) {
  const { assessmentResult, view } = useAssessment();
  if (!view || !assessmentResult) return null;
  return (
    <section className="surface live-summary">
      <p className="eyebrow">DIANXUN INTELLIGENCE / SIMULATION</p>
      <h2>{view.decision}</h2>
      <p>Backend recommendation · {format(view.score, 1)} / 100</p>
      <p>{assessmentResult.data.recommendation.parameter_status}</p>
      <details>
        <summary>Why this decision?</summary>
        {assessmentResult.data.decision_reason.map((reason, i) => (
          <p key={i}>{reason}</p>
        ))}
      </details>
      <button onClick={onDecision}>查看安全门槛与四条候选路径 →</button>
    </section>
  );
}
export default function LiveResults({
  module,
}: {
  module: ModuleId | "assessment";
}) {
  const a = useAssessment();
  if (!a.assessmentResult || !a.view) return null;
  if (a.view.manual) return <ManualResults module={module} />;
  const r = a.assessmentResult.data,
    v = a.view;
  const report = module === "report" || module === "assessment";
  const show = (m: ModuleId) => report || module === m;
  return (
    <div className={report ? "live-results assessment-report" : "live-results"}>
      <p className="source-notice">
        Data Source: Live Backend · 公开电芯模型 / 模拟情景 · request{" "}
        {a.assessmentResult.request_id}
      </p>
      <p>{r.display_notice}</p>
      {report && (
        <section>
          <h3>Vehicle & Battery Information</h3>
          <Values
            items={[
              ["Vehicle", "N/A"],
              ["NASA cell", r.battery_id],
              ["Identity scope", r.battery_id_scope],
              ["Decision scenario", r.scenario_id],
              ["Vehicle transfer", String(r.automatic_model_to_pack_transfer)],
              ["Request schema", a.assessmentResult.schema_version],
            ]}
          />
        </section>
      )}
      {report && (
        <section>
          <h3>Data Quality · BMS</h3>
          {r.data_quality.status === "checked" ? (
            <>
              <Values
                items={[
                  ["Accepted rows", r.data_quality.summary.accepted_rows],
                  ["Rejected rows", r.data_quality.summary.rejected_rows],
                  ["Errors", r.data_quality.summary.error_count],
                  ["Warnings", r.data_quality.summary.warning_count],
                  ["Schema ready", r.data_quality.summary.schema_ready],
                  [
                    "Synthetic fixture",
                    r.data_quality.summary.synthetic_fixture_present,
                  ],
                ]}
              />
              <p>{r.data_quality.summary.interpretation}</p>
              <p>{r.data_quality.summary.source_provenance}</p>
              {r.data_quality.issues.map((issue, i) => (
                <p key={i}>
                  Row {issue.csv_row}: {issue.field} · {issue.detail}
                </p>
              ))}
            </>
          ) : (
            <p>{r.data_quality.reason}</p>
          )}
        </section>
      )}
      {show("health") && (
        <section>
          <h3>Battery Health</h3>
          <Values
            items={[
              ["Predicted SOH", `${format(v.soh)} %`],
              [
                "Measured SOH",
                r.soh.status === "available"
                  ? `${format(r.soh.measured_soh_pct)} %`
                  : "N/A",
              ],
              ["Model", r.soh.status === "available" ? r.soh.model : "N/A"],
              ["Internal resistance", "N/A"],
              ["Temperature stability", "N/A"],
              ["Cell consistency", "N/A"],
            ]}
          />
          <p className="dialog-model">SOH = Qcurrent / Qinitial × 100%</p>
          <Values
            items={[
              [
                "Current measured capacity (RUL input)",
                `${format(r.rul.features?.current_capacity_ah, 4)} Ah`,
              ],
              [
                "Initial capacity (RUL input)",
                `${format(r.rul.features?.initial_capacity_ah, 4)} Ah`,
              ],
              [
                "Derived retention (RUL reference)",
                r.rul.features && r.rul.features.initial_capacity_ah > 0
                  ? `${format((r.rul.features.current_capacity_ah / r.rul.features.initial_capacity_ah) * 100)} %`
                  : "N/A",
              ],
            ]}
          />
          <p>
            容量比值由 RUL 输入派生，参考初始容量与 SOH
            模型基准不同，不能替代上方 SOH 预测。
          </p>
          {r.soh.status === "available" && <p>{r.soh.scope}</p>}
        </section>
      )}
      {show("life") && (
        <section>
          <h3>Remaining Useful Life</h3>
          <Values
            items={[
              ["Remaining reference cycles", format(v.rul)],
              ["Current cycle", r.rul.cycle],
              ["Method", r.rul.method],
              ["Confidence interval", "N/A"],
              ["Predicted EOL cycle", "N/A"],
              ["Estimated years", "N/A"],
            ]}
          />
          <p>{r.rul.reason || r.rul.operating_condition_caution}</p>
          <p>{r.rul.validation_status}</p>
          <div className="unavailable-chart">
            Historical / Prediction Curve · Not Available
            <br />
            后端未返回曲线；未将本地示例曲线作为真实预测。
          </div>
        </section>
      )}
      {(show("health") || module === "life") && (
        <section>
          <h3>Why this prediction?</h3>
          {r.explainability.status === "available" ? (
            <>
              <p>
                {r.explainability.method} · Top Contributing Factors · SOH
                percentage points
              </p>
              <Values
                items={[
                  [
                    "Baseline SOH",
                    format(r.explainability.base_value_soh_pct, 4),
                  ],
                  [
                    "Additivity error (pp)",
                    format(r.explainability.additivity_error_pp, 8),
                  ],
                ]}
              />
              <div className="shap-list">
                {v.contributions.map((c) => (
                  <div key={c.feature}>
                    <span>
                      {c.feature}
                      <small>Feature value: {format(c.feature_value, 6)}</small>
                    </span>
                    <div className="shap-track">
                      <i
                        style={{
                          width: `${(Math.abs(c.shap_soh_pp) / (Math.max(...v.contributions.map((x) => Math.abs(x.shap_soh_pp))) || 1)) * 100}%`,
                          background:
                            c.shap_soh_pp >= 0
                              ? "var(--mint, #9cedc5)"
                              : "#e9ae78",
                        }}
                      />
                    </div>
                    <b>
                      {c.shap_soh_pp > 0 ? "+" : ""}
                      {format(c.shap_soh_pp, 4)} pp
                    </b>
                    <small>{c.direction}</small>
                  </div>
                ))}
              </div>
              <p>{r.explainability.interpretation}</p>
            </>
          ) : (
            <p>
              Explainability currently unavailable · {r.explainability.reason}
            </p>
          )}
        </section>
      )}
      {show("carbon") && (
        <section>
          <h3>Carbon Passport</h3>
          <p className="dialog-model">C = Σ(Activity Data × Emission Factor)</p>
          {r.carbon.status === "calculated" ? (
            <>
              <Values
                items={[
                  ["Total lifecycle carbon", `${format(v.carbon, 3)} tCO₂e`],
                  ["Scope complete", r.carbon.summary.scope_complete],
                  [
                    "Missing stages",
                    r.carbon.summary.missing_stages.join(", ") || "None",
                  ],
                  [
                    "Illustrative factors",
                    r.carbon.summary.contains_illustrative_factors,
                  ],
                  [
                    "Illustrative activities",
                    r.carbon.summary.contains_illustrative_activities,
                  ],
                ]}
              />
              <Values
                items={v.stages.map(([name, n]) => [
                  name,
                  `${format(n)} kgCO₂e`,
                ])}
              />
              <p>
                后端按四阶段核算；原材料计入制造，运输与维护合并，不额外拆分或重复计数。
              </p>
              <p>{r.carbon.summary.interpretation}</p>
              <p>{r.carbon.summary.allocation}</p>
              <h4>Data Provenance</h4>
              <p>
                {r.carbon.factor_provenance} · 来源由调用方声明，未经独立核验。
              </p>
              {r.carbon.details.map((d) => (
                <article className="factor-row" key={d.activity_id}>
                  <strong>{d.description || d.activity_id}</strong>
                  <p>
                    {format(d.quantity)} {d.activity_unit} ×{" "}
                    {format(d.factor_value, 4)} = {format(d.emissions_kgCO2e)}{" "}
                    kgCO₂e
                  </p>
                  <p>{d.derivation}</p>
                  <p>
                    {d.factor_id} · {d.factor_status} · year {d.factor_year} ·
                    Region / Confidence: N/A
                  </p>
                  <p>
                    Source:{" "}
                    {/^https?:\/\//.test(d.factor_source) ? (
                      <a
                        href={d.factor_source}
                        target="_blank"
                        rel="noreferrer"
                      >
                        {d.factor_source}
                      </a>
                    ) : (
                      "Not Available"
                    )}
                  </p>
                </article>
              ))}
            </>
          ) : (
            <p>Not Available · {r.carbon.reason}</p>
          )}
        </section>
      )}
      {show("decision") && (
        <section>
          <h3>Green Decision · Safety Gate</h3>
          <p>{r.safety.scope} · 下方是模拟路径门槛，不代表检测认证。</p>
          <Values
            items={[
              "Thermal Risk",
              "Cell Consistency",
              "Insulation",
              "Abnormal Voltage",
            ].map((k) => [k, "UNKNOWN · 未提供检测结果"])}
          />
          <div className="table-scroll">
            <table>
              <caption>Backend route eligibility</caption>
              <thead>
                <tr>
                  <th>Route</th>
                  <th>Gate</th>
                  <th>Reason codes</th>
                </tr>
              </thead>
              <tbody>
                {r.safety.gates.map((g) => (
                  <tr key={g.route_id}>
                    <td>{routeNames[g.route_id] || g.route_id}</td>
                    <td>{g.eligible ? "PASS" : "FAIL / HOLD"}</td>
                    <td>{g.reason_codes.join(", ") || "None"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <h4>Candidate Paths</h4>
          <p>加权分与分项效用由 0–1 转为 0–100；不可用分数保持 N/A。</p>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Route</th>
                  <th>Score / 100</th>
                  <th>Carbon kgCO₂e</th>
                  <th>NPV CNY</th>
                  <th>Recovered kg</th>
                  <th>Eligible</th>
                </tr>
              </thead>
              <tbody>
                {r.candidate_paths.map((p) => (
                  <tr key={p.route_id}>
                    <td>{routeNames[p.route_id] || p.route_name}</td>
                    <td>
                      {p.weighted_score === null
                        ? "N/A"
                        : format(p.weighted_score * 100, 1)}
                    </td>
                    <td>{format(p.carbon_kgco2e)}</td>
                    <td>{format(p.npv_cny)}</td>
                    <td>{format(p.recovered_kg)}</td>
                    <td>{p.eligible ? "Yes" : "No"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <h4>Final Recommendation · {v.decision}</h4>
          <Values
            items={[
              ["Score / 100", format(v.score, 1)],
              ["Status", r.recommendation.status],
              ["Parameters", r.recommendation.parameter_status],
              ["Application", "N/A"],
            ]}
          />
          <h4>Why this decision?</h4>
          <p>
            NASA SOH: {format(v.soh)}% / RUL: {format(v.rul)} reference
            cycles，仅为公开电芯结果，未自动移植到决策电池包。
          </p>
          <p>
            决策场景的输入 SOH/RUL 未在 assessment
            响应中回传；请以固定请求文件中的情景声明为准。
          </p>
          <Values
            items={
              v.selected
                ? Object.entries(v.selected.utility_components || {}).map(
                    ([k, n]) => [`${k} utility / 100`, format(n * 100, 1)],
                  )
                : [["Utility scores", "N/A · HOLD"]]
            }
          />
          <Values
            items={Object.entries(r.recommendation.weights).map(([k, n]) => [
              `${k} weight`,
              n,
            ])}
          />
          {r.decision_reason.map((reason, i) => (
            <p key={i}>{reason}</p>
          ))}
        </section>
      )}
      {(report || module === 'decision') && <section><h3>Residual Value · Prototype Technical Estimation</h3><p>Not Available · 原 NASA 模式未返回剩余价值。仅在手动模式具备明确证据或显式 Demo 假设时显示，不将路径 NPV 当作电池估值。</p></section>}
      <section>
        <h3>Model / Demo Boundary</h3>
        {r.limitations.map((s, i) => (
          <p key={i}>{s}</p>
        ))}
        {a.assessmentResult.warnings.map((s, i) => (
          <p key={i}>Warning: {s}</p>
        ))}
      </section>
      {report && (
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
