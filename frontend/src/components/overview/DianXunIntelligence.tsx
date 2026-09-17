import { t } from "../../i18n";
import { Sparkles, ChevronDown, ArrowUpRight } from "lucide-react";
import { useState } from "react";
import type { BatteryScenario } from "../../types/battery";
export default function DianXunIntelligence({
  data,
  onDecision,
}: {
  data: BatteryScenario;
  onDecision: () => void;
}) {
  const [open, setOpen] = useState(true);
  return (
    <section className="intelligence surface">
      <button
        className="insight-heading"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        aria-controls="insight-content"
      >
        <span>
          <Sparkles size={19} />
          <strong>{t("DianXun Intelligence")}</strong>
          <small>{t("3 Insights Detected")}</small>
        </span>
        <ChevronDown size={19} className={open ? "rotated" : ""} />
      </button>
      {t(open && (
        <div id="insight-content" className="reveal">
          <div className="insight-list" key={data.id}>
            {t(data.insights.map((insight, i) => (
              <article key={insight}>
                <span className="insight-number">{t("0")}{t(i + 1)}</span>
                <div>
                  <p>{t(insight)}</p>
                  <small>{t(data.insightNotes[i])}</small>
                </div>
              </article>
            )))}
          </div>
          <div
            className={`recommendation ${data.id === "retired" ? "retired" : ""}`}
          >
            <div>
              <span className="micro-label">{t("SUGGESTED NEXT STEP / 场景建议")}</span>
              <h3>
                {t(data.decision)}
                {t(data.decisionLabel) !== t(data.decision) && <span>{t(data.decisionLabel)}</span>}
              </h3>
              <p>{t(data.recommendation)}</p>
            </div>
            <button
              className="icon-button"
              aria-label={t("查看决策说明")}
              onClick={onDecision}
            >
              <ArrowUpRight size={23} />
            </button>
          </div>
          <p className="demo-note">{t("基于示例数据与可解释规则生成；不代表真实检测或安全认证结果。")}</p>
        </div>
      ))}
    </section>
  );
}
