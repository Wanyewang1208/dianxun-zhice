import { useEffect, useRef } from "react";
import { X, ArrowRight, Check, LoaderCircle } from "lucide-react";
import type { BatteryScenario, ModuleId } from "../types/battery";
import { getBatteryModel } from "../lib/batteryMath";
import { calculateLifecycleCarbon } from "../lib/carbonMath";
import { analysisSteps } from "../data/demoBattery";
const modules = {
  health: ["Battery Health", "电池健康分析"],
  life: ["Remaining Life", "剩余寿命预测"],
  carbon: ["Carbon Passport", "碳足迹溯源"],
  decision: ["Green Decision", "绿色决策"],
  report: ["Assessment Report", "智能评估报告"],
};
export default function ModuleDialog({
  module,
  data,
  onClose,
  progress,
}: {
  module: ModuleId | "assessment" | null;
  data: BatteryScenario;
  onClose: () => void;
  progress: number;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const { soh, rul } = getBatteryModel(data);
  useEffect(() => {
    const el = dialog.current;
    if (module) {
      el?.showModal();
    } else el?.close();
  }, [module]);
  if (!module) return null;
  const assessment = module === "assessment";
  const name = assessment ? "Battery Assessment" : modules[module][0];
  return (
    <dialog
      ref={dialog}
      aria-labelledby="dialog-title"
      className="module-dialog"
      onCancel={onClose}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="dialog-top">
        <span className="eyebrow">DIANXUN INTELLIGENCE</span>
        <button className="icon-button" onClick={onClose} aria-label="关闭">
          <X size={20} />
        </button>
      </div>
      <h2 id="dialog-title">{name}</h2>
      <p className="dialog-subtitle">
        {assessment ? "示例数据评估" : modules[module][1]}
      </p>
      {assessment && progress < 5 ? (
        <div className="analysis-progress" role="status">
          <p>Analyzing battery data...</p>
          {analysisSteps.map((s, i) => (
            <div key={s} className={i <= progress ? "processing" : ""}>
              {i < progress ? (
                <Check size={16} />
              ) : i === progress ? (
                <LoaderCircle size={16} className="spin" />
              ) : (
                <span className="step-count">{i + 1}</span>
              )}
              {s}
            </div>
          ))}
        </div>
      ) : (
        <>
          <div className="dialog-summary">
            <span>
              {data.name} · {data.batteryId}
            </span>
            <strong>{assessment ? "示例评估完成" : data.decisionLabel}</strong>
            <p>{data.recommendation}</p>
          </div>
          <dl className="dialog-values">
            <div>
              <dt>Calculated SOH</dt>
              <dd>{soh.toFixed(1)}%</dd>
            </div>
            <div>
              <dt>Estimated RUL</dt>
              <dd>{rul} cycles</dd>
            </div>
            <div>
              <dt>Lifecycle Carbon</dt>
              <dd>{calculateLifecycleCarbon(data.carbon).toFixed(2)} tCO₂e</dd>
            </div>
            <div>
              <dt>Risk</dt>
              <dd>{data.risk}</dd>
            </div>
          </dl>
          {module === "life" && (
            <p className="dialog-model">
              SOH(n) = {getBatteryModel(data).a.toFixed(3)} −{" "}
              {Math.abs(getBatteryModel(data).b).toFixed(6)}n<br />
              EOL = {data.threshold}% · 当前 {data.cycles} cycles
              <br />
              局部线性预测参数为演示假设；退役场景使用梯次寿命参考线。
            </p>
          )}
          {module === "carbon" && (
            <p className="dialog-model">
              来源：Demo Dataset · 地区：青海（电网因子示例）· 年份：2026 ·
              数据等级：模拟，未核验。原材料计入制造阶段，避免重复核算；退役阶段为情景估计。
            </p>
          )}
          <p className="scope-note">
            本轮开放 Overview 与技术预览。
            {assessment ? "完整分析页面" : `${name} 正式子页面`}尚未开发。
          </p>
          <button
            className="primary-button compact"
            onClick={() => {
              onClose();
              document
                .getElementById("technology")
                ?.scrollIntoView({
                  behavior: matchMedia("(prefers-reduced-motion: reduce)")
                    .matches
                    ? "instant"
                    : "smooth",
                });
            }}
          >
            查看首页技术预览
            <ArrowRight size={18} />
          </button>
        </>
      )}
      <p className="demo-note">情景模拟 · 不接入真实 BMS 或外部 AI 服务</p>
    </dialog>
  );
}
