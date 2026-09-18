import { t } from "../../i18n";
import { ArrowRight } from "lucide-react";
const steps = [
  ["Detection", "现在怎么样？"],
  ["Prediction", "还能用多久？"],
  ["Evaluation", "环境代价是多少？"],
  ["Decision", "下一步应该去哪？"],
];
export default function InnovationStory() {
  return (
    <section className="innovation">
      <div className="innovation-title">
        <p className="eyebrow">{t("BEYOND BATTERY DETECTION")}</p>
        <h2>{t("从一次检测，")}<br />{t("到一整个生命周期的决策。")}</h2>
        <p>{t("动力电池全生命周期智能决策系统")}</p>
      </div>
      <div className="innovation-steps">
        {t(steps.map(([en, zh], i) => (
          <div key={en}>
            <span className="micro-label">{t("0")}{t(i + 1)}</span>
            <strong>{t(en)}</strong>
            <span>{t(zh)}</span>
            {t(i < 3 && <ArrowRight size={18} />)}
          </div>
        )))}
      </div>
    </section>
  );
}
