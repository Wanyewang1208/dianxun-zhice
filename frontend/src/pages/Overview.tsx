import { Activity, Clock3, Leaf, ShieldCheck, ShieldAlert } from "lucide-react";
import type { BatteryScenario, ScenarioId, ModuleId } from "../types/battery";
import { getBatteryModel } from "../lib/batteryMath";
import { calculateLifecycleCarbon } from "../lib/carbonMath";
import OverviewHero from "../components/overview/OverviewHero";
import BatteryPassport from "../components/overview/BatteryPassport";
import IntelligenceMetric from "../components/overview/IntelligenceMetric";
import LifecycleFlow from "../components/overview/LifecycleFlow";
import DianXunIntelligence from "../components/overview/DianXunIntelligence";
import TechnologyPreview from "../components/overview/TechnologyPreview";
import InnovationStory from "../components/overview/InnovationStory";
interface Props {
  data: BatteryScenario;
  onScenario: (id: ScenarioId) => void;
  onAssess: () => void;
  onModule: (id: ModuleId) => void;
  busy: boolean;
}
export default function Overview({
  data,
  onScenario,
  onAssess,
  onModule,
  busy,
}: Props) {
  const { soh, rul } = getBatteryModel(data);
  return (
    <>
      <div className="hero-grid">
        <OverviewHero
          scenario={data.id}
          onChange={onScenario}
          onAssess={onAssess}
          busy={busy}
        />
        <BatteryPassport data={data} />
      </div>
      <section className="metrics-grid" aria-label="四项核心评估指标">
        <IntelligenceMetric
          index={0}
          label="State of Health"
          value={soh}
          decimals={1}
          unit="%"
          description="SOH · 电池健康状态"
          Icon={Activity}
        />
        <IntelligenceMetric
          index={1}
          label="Remaining Useful Life"
          value={rul}
          unit="cycles"
          description="RUL · 预计剩余循环寿命"
          Icon={Clock3}
          tone="cyan"
        />
        <IntelligenceMetric
          index={2}
          label="Lifecycle Carbon"
          value={calculateLifecycleCarbon(data.carbon)}
          decimals={2}
          unit="tCO₂e"
          description="全生命周期碳足迹 · 示例"
          Icon={Leaf}
        />
        <IntelligenceMetric
          index={3}
          label="Risk Assessment"
          value={data.risk}
          description={`${data.riskLabel} · 场景风险等级`}
          Icon={data.id === "used" ? ShieldCheck : ShieldAlert}
          tone={data.id === "used" ? "mint" : "amber"}
        />
      </section>
      <LifecycleFlow />
      <DianXunIntelligence
        data={data}
        onDecision={() => onModule("decision")}
      />
      <TechnologyPreview data={data} onModule={onModule} />
      <InnovationStory />
      <BmsQualityPanel />
      <footer className="page-footer">
        <span>
          电循智策 <span className="muted">/ DianXun ZhiCe</span>
        </span>
        <span>新能源汽车动力电池全生命周期智能评估与绿色决策平台</span>
        <span>DEMO v1.0</span>
      </footer>
    </>
  );
}
import BmsQualityPanel from "../components/BmsQualityPanel";
