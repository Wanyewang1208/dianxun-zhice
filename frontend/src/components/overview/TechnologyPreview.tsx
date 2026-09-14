import { ArrowUpRight } from "lucide-react";
import type { BatteryScenario, ModuleId } from "../../types/battery";
import { getBatteryModel } from "../../lib/batteryMath";
import {
  calculateEmission,
  calculateLifecycleCarbon,
} from "../../lib/carbonMath";
import { lazy, Suspense } from "react";
const DegradationChart = lazy(() => import("../charts/DegradationChart"));
type Props = { data: BatteryScenario; onModule: (id: ModuleId) => void };
function PreviewHeading({
  number,
  name,
  onClick,
}: {
  number: string;
  name: string;
  onClick: () => void;
}) {
  return (
    <div className="preview-heading">
      <div>
        <span className="micro-label">MODEL {number}</span>
        <h3>{name}</h3>
      </div>
      <button
        onClick={onClick}
        className="icon-button"
        aria-label={`打开 ${name} 模块说明`}
      >
        <ArrowUpRight size={19} />
      </button>
    </div>
  );
}
export function BatteryHealthPreview({ data, onModule }: Props) {
  const { soh } = getBatteryModel(data);
  return (
    <article className="technology-card surface">
      <PreviewHeading
        number="01"
        name="Battery Health"
        onClick={() => onModule("health")}
      />
      <div className="formula">
        <span>SOH =</span>
        <span className="fraction">
          <span>
            Q<sub>current</sub>
          </span>
          <span>
            Q<sub>initial</sub>
          </span>
        </span>
        <span>× 100%</span>
      </div>
      <dl className="model-values">
        <div>
          <dt>Current capacity</dt>
          <dd>
            {data.currentCapacity.toFixed(2)} <span>kWh</span>
          </dd>
        </div>
        <div>
          <dt>Initial capacity</dt>
          <dd>
            {data.initialCapacity.toFixed(2)} <span>kWh</span>
          </dd>
        </div>
      </dl>
      <div className="preview-result">
        <span>Calculated SOH</span>
        <strong className="mint">
          {soh.toFixed(1)}
          <small>%</small>
        </strong>
      </div>
      <p className="demo-note">由当前可用容量与额定容量实时计算</p>
    </article>
  );
}
export function RULPreview({ data, onModule }: Props) {
  const { rul } = getBatteryModel(data);
  return (
    <article className="technology-card surface">
      <PreviewHeading
        number="02"
        name="Remaining Life"
        onClick={() => onModule("life")}
      />
      <div className="rul-values">
        <span>
          Current Cycle<strong>{data.cycles.toLocaleString("en-US")}</strong>
        </span>
        <span>
          Predicted EOL<strong>{data.eolCycles.toLocaleString("en-US")}</strong>
        </span>
        <span>
          RUL
          <strong className="cyan">
            {rul}
            <small> cycles</small>
          </strong>
        </span>
      </div>
      <Suspense
        fallback={
          <div className="mini-chart" role="status">
            正在载入预测曲线…
          </div>
        }
      >
        <DegradationChart data={data} />
      </Suspense>
      <div className="chart-legend">
        <span>
          <i />
          历史
        </span>
        <span>
          <i className="dashed" />
          预测
        </span>
        <span>
          {data.threshold}% {data.id === "used" ? "车用" : "梯次"}参考线
        </span>
      </div>
      <p className="demo-note">局部线性基线 · 示例假设，非实测拟合</p>
    </article>
  );
}
export function CarbonPreview({ data, onModule }: Props) {
  const total = calculateLifecycleCarbon(data.carbon);
  return (
    <article className="technology-card surface">
      <PreviewHeading
        number="03"
        name="Carbon Intelligence"
        onClick={() => onModule("carbon")}
      />
      <div className="carbon-formula">
        C = Σ <span>(Activity Data × Emission Factor)</span>
      </div>
      <div className="carbon-total">
        <strong>
          {total.toFixed(2)}
          <small> tCO₂e</small>
        </strong>
        <span>Total Lifecycle Carbon</span>
      </div>
      <div
        className="carbon-segments"
        role="img"
        aria-label="生命周期碳排放阶段占比"
      >
        {data.carbon.map((s) => (
          <span
            key={s.name}
            style={{
              width: `${(calculateEmission(s.activity, s.factor) / 1000 / total) * 100}%`,
              background: s.color,
            }}
            title={`${s.name} ${(calculateEmission(s.activity, s.factor) / 1000).toFixed(2)} tCO₂e`}
          />
        ))}
      </div>
      <div className="carbon-legend">
        {data.carbon.map((s) => (
          <span key={s.name}>
            <i style={{ background: s.color }} />
            {s.name}
            <b>{(calculateEmission(s.activity, s.factor) / 1000).toFixed(2)}</b>
          </span>
        ))}
      </div>
      <p className="demo-note">示例因子 · kgCO₂e 计算后统一换算为吨</p>
    </article>
  );
}
export default function TechnologyPreview(props: Props) {
  return (
    <section id="technology" className="technology">
      <div className="section-heading">
        <div>
          <p className="eyebrow">BUILT ON EXPLAINABLE MODELS</p>
          <h2>
            Technology Preview <span>让结论可复核</span>
          </h2>
        </div>
        <span className="section-number">02 / THE SCIENCE</span>
      </div>
      <div className="technology-grid">
        <BatteryHealthPreview {...props} />
        <RULPreview {...props} />
        <CarbonPreview {...props} />
      </div>
    </section>
  );
}
