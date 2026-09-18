import { t } from "../i18n";
import { useAssessment } from "../context/AssessmentContext";
import LiveResults from "./LiveResults";
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
  const { assessmentResult } = useAssessment();
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
      className={`module-dialog ${assessmentResult ? "live-dialog" : ""}`}
      onCancel={onClose}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="dialog-top">
        <span className="eyebrow">{t("DIANXUN INTELLIGENCE")}</span>
        <button className="icon-button" onClick={onClose} aria-label={t("关闭")}>
          <X size={20} />
        </button>
      </div>
      <h2 id="dialog-title">{t(name)}</h2>
      <p className="dialog-subtitle">
        {t(assessment ? "示例数据评估" : modules[module][1])}
      </p>
      {t(assessmentResult ? (
        <LiveResults module={module} />
      ) : assessment && progress < 5 ? (
        <div className="analysis-progress" role="status">
          <p>{t("Analyzing battery data...")}</p>
          {t(analysisSteps.map((s, i) => (
            <div key={s} className={i <= progress ? "processing" : ""}>
              {t(i < progress ? (
                <Check size={16} />
              ) : i === progress ? (
                <LoaderCircle size={16} className="spin" />
              ) : (
                <span className="step-count">{t(i + 1)}</span>
              ))}
              {t(s)}
            </div>
          )))}
        </div>
      ) : (
        <>
          <div className="dialog-summary">
            <span>
              {t(data.name)}{t(" · ")}{data.batteryId}
            </span>
            <strong>{t(assessment ? "示例评估完成" : data.decisionLabel)}</strong>
            <p>{t(data.recommendation)}</p>
          </div>
          <dl className="dialog-values">
            <div>
              <dt>{t("Calculated SOH")}</dt>
              <dd>{t(soh.toFixed(1))}{t("%")}</dd>
            </div>
            <div>
              <dt>{t("Estimated RUL")}</dt>
              <dd>{t(rul)}{t(" cycles")}</dd>
            </div>
            <div>
              <dt>{t("Lifecycle Carbon")}</dt>
              <dd>{t(calculateLifecycleCarbon(data.carbon).toFixed(2))}{t(" tCO₂e")}</dd>
            </div>
            <div>
              <dt>{t("Risk")}</dt>
              <dd>{t(data.risk)}</dd>
            </div>
          </dl>
          {t(module === "life" && (
            <p className="dialog-model">{t("SOH(n) = ")}{t(getBatteryModel(data).a.toFixed(3))}{t(" −")}{t(" ")}
              {t(Math.abs(getBatteryModel(data).b).toFixed(6))}{t("n")}<br />{t("EOL = ")}{t(data.threshold)}{t("% · 当前 ")}{t(data.cycles)}{t(" cycles")}<br />{t("局部线性预测参数为演示假设；退役场景使用梯次寿命参考线。")}</p>
          ))}
          {t(module === "carbon" && (
            <p className="dialog-model">{t("来源：Demo Dataset · 地区：青海（电网因子示例）· 年份：2026 · 数据等级：模拟，未核验。原材料计入制造阶段，避免重复核算；退役阶段为情景估计。")}</p>
          ))}
          <p className="scope-note">{t("当前为本地 Demo 摘要。点击首页 Start Assessment 后，本模块将展示后端结果。")}</p>
          <button
            className="primary-button compact"
            onClick={() => {
              onClose();
              document.getElementById("technology")?.scrollIntoView({
                behavior: matchMedia("(prefers-reduced-motion: reduce)").matches
                  ? "instant"
                  : "smooth",
              });
            }}
          >{t("查看首页技术预览")}<ArrowRight size={18} />
          </button>
        </>
      ))}
      {t(!assessmentResult && (
        <p className="demo-note">{t("DEMO DATA · 当前为本地情景模拟，开始评估后可查看后端结果。")}</p>
      ))}

    </dialog>
  );
}
