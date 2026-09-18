import { t } from "../../i18n";
import { useAssessment } from "../../context/AssessmentContext";
import { ArrowRight, LoaderCircle } from "lucide-react";
import ScenarioSwitch from "./ScenarioSwitch";
import type { ScenarioId } from "../../types/battery";
export default function OverviewHero({
  scenario,
  onChange,
  onAssess,
  busy,
}: {
  scenario: ScenarioId;
  onChange: (id: ScenarioId) => void;
  onAssess: () => void;
  busy: boolean;
}) {
  const { dataSource } = useAssessment();
  return (
    <section className="overview-hero">
      <p className="eyebrow">{t("电循智策")}</p>
      <h1>{t("One Battery.")}<br />{t("One Lifecycle.")}<br />{t("One Decision.")}</h1>
      <p className="hero-description">{t("让每一块动力电池的健康、寿命、碳足迹")}<br className="desktop-break" />{t("与最终去向都有据可依。")}</p>
      <ScenarioSwitch
        value={scenario}
        onChange={onChange}
        disabled={busy || dataSource === "live"}
      />
      <button className="primary-button" onClick={onAssess} disabled={busy}>
        {t(busy ? <LoaderCircle className="spin" size={19} /> : null)}
        <span>
          {t(busy ? "正在等待后端评估…" : "开始电池评估")}
        </span>
        {t(!busy && <ArrowRight size={22} />)}
      </button>
      <p className="hero-footnote">
        <span className="status-dot" />{t("可解释模型 · 可追溯数据 · 全生命周期决策")}</p>
    </section>
  );
}
