import { ManualForm } from "./ManualAssessment";
import { useEffect, useState } from "react";
import { useAssessment } from "../context/AssessmentContext";
const steps = [
  "Reading BMS Data",
  "Validating Data Quality",
  "Calculating SOH",
  "Estimating RUL",
  "Running Explainability",
  "Calculating Carbon Footprint",
  "Evaluating Safety",
  "Generating Green Decision",
];
export default function AssessmentControls() {
  const a = useAssessment();
  const [step, setStep] = useState(0);
  const [files, setFiles] = useState({
    telemetry_csv: "团队固定遥测 CSV",
    metadata_csv: "团队固定元数据 CSV",
  });
  const loading = a.assessmentStatus === "loading";
  useEffect(() => {
    setStep(0);
    if (!loading) return;
    const t = setInterval(
      () => setStep((s) => Math.min(s + 1, steps.length - 1)),
      1800,
    );
    return () => clearInterval(t);
  }, [loading]);
  async function upload(key: "telemetry_csv" | "metadata_csv", file?: File) {
    if (!file) return;
    try {
      if (file.size > 900000)
        throw new Error("CSV 超过 900 KB，请使用较小的样例文件。");
      const text = new TextDecoder("utf-8", { fatal: true }).decode(
        await file.arrayBuffer(),
      );
      a.setBMS(key, text);
      setFiles((f) => ({ ...f, [key]: file.name }));
    } catch (e) {
      a.setError(e instanceof Error ? e.message : "请使用 UTF-8 CSV。");
    }
  }
  return (
    <section
      className="assessment-controls surface"
      aria-label="评估数据与连接"
    >
      <div className="integration-actions">
        <button
          disabled={loading || a.validating}
          onClick={() => a.useManual(false)}
        >
          Manual Input · 手动录入
        </button>
        <button
          disabled={loading || a.validating}
          onClick={() => a.useManual(true)}
        >
          Manual Demo · 原型估值样例
        </button>
        <strong>
          {a.dataSource === "live" ? "LIVE ANALYSIS" : "DEMO DATA"}
        </strong>
        <span>
          {a.backendStatus === "online"
            ? "Backend Connected"
            : a.backendStatus === "checking"
              ? "Checking backend…"
              : "Backend unavailable"}
        </span>
        <button onClick={() => void a.checkBackend()}>检查连接</button>
        <button
          disabled={loading || a.validating}
          onClick={() => {
            a.useTeamDataset();
            setFiles({
              telemetry_csv: "团队固定遥测 CSV",
              metadata_csv: "团队固定元数据 CSV",
            });
          }}
        >
          Use Demo Dataset · 团队样例
        </button>
        <button
          disabled={loading || a.validating}
          onClick={() => {
            a.loadDemoAssessment();
            setFiles({
              telemetry_csv: "团队固定遥测 CSV",
              metadata_csv: "团队固定元数据 CSV",
            });
          }}
        >
          Reset to Demo · 本地展示
        </button>
      </div>
      <p>
        {a.manualRequest
          ? "手动模式：容量比 SOH；寿命、SHAP、碳和价值缺少证据时保持 N/A。显式 Manual Demo 才使用假设。"
          : "模型：NASA B0018 / cycle 66；BMS 仅数据检查；碳与决策使用固定模拟电池包。上传文件不会转换为整车 SOH/RUL。"}
      </p>
      <div className="integration-actions">
        {(["telemetry_csv", "metadata_csv"] as const).map((key) => (
          <label key={key}>
            {key === "telemetry_csv" ? "Telemetry CSV" : "Metadata CSV"}
            <input
              type="file"
              accept=".csv,text/csv"
              disabled={loading || a.validating}
              onChange={(e) => {
                void upload(key, e.target.files?.[0]);
                e.target.value = "";
              }}
            />
            <small>{a.request.bms?.[key] ? files[key] : "未选择 CSV"}</small>
          </label>
        ))}
        <button
          disabled={loading || a.validating || !a.request.bms}
          onClick={() => void a.validate()}
        >
          {a.validating ? "检查中…" : "Validate BMS"}
        </button>
      </div>
      <ManualForm />
      {a.validation && (
        <p role="status">
          Data Quality:{" "}
          {a.validation.summary.schema_ready
            ? "格式检查通过（非安全认证）"
            : "Invalid BMS Data"}{" "}
          · {a.validation.summary.accepted_rows} accepted /{" "}
          {a.validation.summary.rejected_rows} rejected /{" "}
          {a.validation.summary.warning_count} warnings
        </p>
      )}
      {a.validation?.issues.length ? (
        <details>
          <summary>检查问题</summary>
          {a.validation.issues.map((i, n) => (
            <p key={n}>
              Row {i.csv_row} · {i.severity} · {i.field} · {i.detail}
            </p>
          ))}
        </details>
      ) : null}
      {loading && (
        <div role="status" className="integration-progress">
          <strong>{steps[step]}…</strong>
          <progress max={steps.length} value={step + 1} />
          <small>
            流程进度动画 · 正在等待一次 assessment 请求，非逐项完成状态
          </small>
        </div>
      )}
      {a.error && (
        <div role="alert">
          <strong>Assessment unavailable</strong>
          <p>{a.error}</p>
          <div className="integration-actions">
            <button
              disabled={loading || a.validating}
              onClick={() => void a.runAssessment()}
            >
              Retry
            </button>
            <button
              onClick={() => {
                a.loadDemoAssessment();
                setFiles({
                  telemetry_csv: "团队固定遥测 CSV",
                  metadata_csv: "团队固定元数据 CSV",
                });
              }}
            >
              Use Local Demo
            </button>
          </div>
          {a.assessmentResult && <p>当前仍显示上一次成功结果，尚未更新。</p>}
        </div>
      )}
    </section>
  );
}
