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
        <p className="eyebrow">BEYOND BATTERY DETECTION</p>
        <h2>
          从一次检测，
          <br />
          到一整个生命周期的决策。
        </h2>
        <p>动力电池全生命周期智能决策系统</p>
      </div>
      <div className="innovation-steps">
        {steps.map(([en, zh], i) => (
          <div key={en}>
            <span className="micro-label">0{i + 1}</span>
            <strong>{en}</strong>
            <span>{zh}</span>
            {i < 3 && <ArrowRight size={18} />}
          </div>
        ))}
      </div>
    </section>
  );
}
