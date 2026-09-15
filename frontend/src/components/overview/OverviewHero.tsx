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
      <p className="eyebrow">
        电循智策 <span>/</span> DIANXUN ZHICE
      </p>
      <h1>
        One Battery.
        <br />
        One Lifecycle.
        <br />
        One Decision.
      </h1>
      <p className="hero-description">
        让每一块动力电池的健康、寿命、碳足迹
        <br className="desktop-break" />
        与最终去向都有据可依。
      </p>
      <ScenarioSwitch
        value={scenario}
        onChange={onChange}
        disabled={busy || dataSource === "live"}
      />
      <button className="primary-button" onClick={onAssess} disabled={busy}>
        {busy ? <LoaderCircle className="spin" size={19} /> : null}
        <span>
          {busy ? "正在等待后端评估…" : "开始电池评估"}
          <small>{busy ? "Analyzing battery data" : "Start Assessment"}</small>
        </span>
        {!busy && <ArrowRight size={22} />}
      </button>
      <p className="hero-footnote">
        <span className="status-dot" />
        可解释模型 · 可追溯数据 · 全生命周期决策
      </p>
    </section>
  );
}
