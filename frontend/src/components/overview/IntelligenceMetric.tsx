import type { LucideIcon } from "lucide-react";
import CountUp from "../CountUp";
export default function IntelligenceMetric({
  label,
  value,
  unit,
  description,
  Icon,
  decimals = 0,
  tone = "mint",
  index,
}: {
  label: string;
  value: number | string;
  unit?: string;
  description: string;
  Icon: LucideIcon;
  decimals?: number;
  tone?: string;
  index: number;
}) {
  return (
    <article className={`intelligence-metric surface reveal metric-${index}`}>
      <div className="metric-top">
        <span>{label}</span>
        <Icon className={tone} size={27} strokeWidth={1.5} />
      </div>
      <div className={`metric-value ${typeof value === "string" ? tone : ""}`}>
        {typeof value === "number" ? (
          <CountUp value={value} decimals={decimals} />
        ) : (
          value
        )}
        <small>{unit}</small>
      </div>
      <p>{description}</p>
    </article>
  );
}
