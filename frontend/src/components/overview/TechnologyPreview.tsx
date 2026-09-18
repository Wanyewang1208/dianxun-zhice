import { t } from "../../i18n";
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
        <span className="micro-label">{t("MODEL ")}{t(number)}</span>
        <h3>{t(name)}</h3>
      </div>
      <button
        onClick={onClick}
        className="icon-button"
        aria-label={t(`打开 ${name} 模块说明`)}
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
        <span>{t("SOH =")}</span>
        <span className="fraction">
          <span>{t("Q")}<sub>{t("current")}</sub>
          </span>
          <span>{t("Q")}<sub>{t("initial")}</sub>
          </span>
        </span>
        <span>{t("× 100%")}</span>
      </div>
      <dl className="model-values">
        <div>
          <dt>{t("Current capacity")}</dt>
          <dd>
            {t(data.currentCapacity.toFixed(2))} <span>{t("kWh")}</span>
          </dd>
        </div>
        <div>
          <dt>{t("Initial capacity")}</dt>
          <dd>
            {t(data.initialCapacity.toFixed(2))} <span>{t("kWh")}</span>
          </dd>
        </div>
      </dl>
      <div className="preview-result">
        <span>{t("Calculated SOH")}</span>
        <strong className="mint">
          {t(soh.toFixed(1))}
          <small>{t("%")}</small>
        </strong>
      </div>
      <p className="demo-note">{t("由当前可用容量与额定容量实时计算")}</p>
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
        <span>{t("Current Cycle")}<strong>{t(data.cycles.toLocaleString("en-US"))}</strong>
        </span>
        <span>{t("Predicted EOL")}<strong>{t(data.eolCycles.toLocaleString("en-US"))}</strong>
        </span>
        <span>{t("RUL")}<strong className="cyan">
            {t(rul)}
            <small>{t(" cycles")}</small>
          </strong>
        </span>
      </div>
      <Suspense
        fallback={
          <div className="mini-chart" role="status">{t("正在载入预测曲线…")}</div>
        }
      >
        <DegradationChart data={data} />
      </Suspense>
      <div className="chart-legend">
        <span>
          <i />{t("历史")}</span>
        <span>
          <i className="dashed" />{t("预测")}</span>
        <span>
          {t(data.threshold)}{t("% ")}{t(data.id === "used" ? "车用" : "梯次")}{t("参考线")}</span>
      </div>
      <p className="demo-note">{t("局部线性基线 · 示例假设，非实测拟合")}</p>
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
      <div className="carbon-formula">{t("C = Σ ")}<span>{t("(Activity Data × Emission Factor)")}</span>
      </div>
      <div className="carbon-total">
        <strong>
          {t(total.toFixed(2))}
          <small>{t(" tCO₂e")}</small>
        </strong>
        <span>{t("Total Lifecycle Carbon")}</span>
      </div>
      <div
        className="carbon-segments"
        role="img"
        aria-label={t("生命周期碳排放阶段占比")}
      >
        {t(data.carbon.map((s) => (
          <span
            key={s.name}
            style={{
              width: `${(calculateEmission(s.activity, s.factor) / 1000 / total) * 100}%`,
              background: s.color,
            }}
            title={t(`${s.name} ${(calculateEmission(s.activity, s.factor) / 1000).toFixed(2)} tCO₂e`)}
          />
        )))}
      </div>
      <div className="carbon-legend">
        {t(data.carbon.map((s) => (
          <span key={s.name}>
            <i style={{ background: s.color }} />
            {t(s.name)}
            <b>{t((calculateEmission(s.activity, s.factor) / 1000).toFixed(2))}</b>
          </span>
        )))}
      </div>
      <p className="demo-note">{t("示例因子 · kgCO₂e 计算后统一换算为吨")}</p>
    </article>
  );
}
export default function TechnologyPreview(props: Props) {
  return (
    <section id="technology" className="technology">
      <div className="section-heading">
        <div>
          <p className="eyebrow">{t("BUILT ON EXPLAINABLE MODELS")}</p>
          <h2>{t("Technology Preview ")}<span>{t("让结论可复核")}</span>
          </h2>
        </div>
        <span className="section-number">{t("02 / THE SCIENCE")}</span>
      </div>
      <div className="technology-grid">
        <BatteryHealthPreview {...props} />
        <RULPreview {...props} />
        <CarbonPreview {...props} />
      </div>
    </section>
  );
}
