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
          <strong>DianXun Intelligence</strong>
          <small>3 Insights Detected</small>
        </span>
        <ChevronDown size={19} className={open ? "rotated" : ""} />
      </button>
      {open && (
        <div id="insight-content" className="reveal">
          <div className="insight-list" key={data.id}>
            {data.insights.map((insight, i) => (
              <article key={insight}>
                <span className="insight-number">0{i + 1}</span>
                <div>
                  <p>{insight}</p>
                  <small>{data.insightNotes[i]}</small>
                </div>
              </article>
            ))}
          </div>
          <div
            className={`recommendation ${data.id === "retired" ? "retired" : ""}`}
          >
            <div>
              <span className="micro-label">
                SUGGESTED NEXT STEP / 场景建议
              </span>
              <h3>
                {data.decision}
                <span>{data.decisionLabel}</span>
              </h3>
              <p>{data.recommendation}</p>
            </div>
            <button
              className="icon-button"
              aria-label="查看决策说明"
              onClick={onDecision}
            >
              <ArrowUpRight size={23} />
            </button>
          </div>
          <p className="demo-note">
            基于示例数据与可解释规则生成；不代表真实检测或安全认证结果。
          </p>
        </div>
      )}
    </section>
  );
}
