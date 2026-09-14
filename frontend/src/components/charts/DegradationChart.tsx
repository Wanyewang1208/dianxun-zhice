import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  ReferenceLine,
  Tooltip,
} from "recharts";
import { getDegradationCurve } from "../../lib/batteryMath";
import type { BatteryScenario } from "../../types/battery";
export default function DegradationChart({ data }: { data: BatteryScenario }) {
  return (
    <div
      className="mini-chart"
      role="img"
      aria-label={`示例 SOH 曲线：当前 ${data.cycles} 次循环，预测 ${data.eolCycles} 次达到 ${data.threshold}% 参考线`}
    >
      <ResponsiveContainer width="100%" height="100%" minWidth={0}>
        <LineChart
          data={getDegradationCurve(data)}
          margin={{ top: 8, left: -28, right: 5, bottom: 0 }}
        >
          <XAxis
            dataKey="cycle"
            type="number"
            domain={[0, data.eolCycles]}
            ticks={[0, data.cycles, data.eolCycles]}
            axisLine={false}
            tickLine={false}
            tick={{ fill: "#8b9692", fontSize: 10 }}
          />
          <YAxis
            domain={[data.threshold - 4, 102]}
            ticks={[data.threshold, 100]}
            axisLine={false}
            tickLine={false}
            tick={{ fill: "#8b9692", fontSize: 10 }}
          />
          <ReferenceLine
            y={data.threshold}
            stroke="#62736b"
            strokeDasharray="3 4"
          />
          <Tooltip
            contentStyle={{
              background: "#18201e",
              border: "1px solid #34473c",
              borderRadius: 12,
              color: "#f4f7f6",
              fontSize: 12,
            }}
            labelFormatter={(v) => `Cycle ${v}`}
            formatter={(v, name) => [
              `${Number(v).toFixed(1)}%`,
              name === "historical" ? "Historical SOH" : "Predicted SOH",
            ]}
          />
          <Line
            name="historical"
            dataKey="historical"
            type="monotone"
            stroke="#8bd9b2"
            strokeWidth={2}
            dot={false}
            animationDuration={400}
          />
          <Line
            name="predicted"
            dataKey="predicted"
            type="linear"
            stroke="#6fe7e1"
            strokeDasharray="4 4"
            strokeWidth={2}
            dot={false}
            animationDuration={400}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
