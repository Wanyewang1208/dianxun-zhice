import { t } from "../../i18n";
import {
  CarFront,
  BatteryMedium,
  HeartPulse,
  ChartNoAxesCombined,
  Leaf,
  Route,
  ArrowRight,
} from "lucide-react";
import { lifecycleSteps } from "../../data/demoBattery";
const icons = [
  CarFront,
  BatteryMedium,
  HeartPulse,
  ChartNoAxesCombined,
  Leaf,
  Route,
];
export default function LifecycleFlow() {
  return (
    <section className="lifecycle surface">
      <div className="section-heading">
        <div>
          <h2>{t("Lifecycle Intelligence Flow")}</h2>
          <p>{t("从整车信息到绿色决策，每一步都有依据。")}</p>
        </div>
        <span className="eyebrow">{t("ONE CONTINUOUS DECISION CHAIN")}</span>
      </div>
      <ol className="flow-steps">
        {t(lifecycleSteps.map((step, i) => {
          const Icon = icons[i];
          return (
            <li key={step.label}>
              <div className="flow-node">
                <Icon size={24} strokeWidth={1.4} />
              </div>
              <strong>{t(step.label)}</strong>
              {t(step.zh) !== t(step.label) && <span>{t(step.zh)}</span>}
              {t(i < 5 && (
                <ArrowRight className="flow-arrow" size={19} strokeWidth={1} />
              ))}
            </li>
          );
        }))}
      </ol>
    </section>
  );
}
