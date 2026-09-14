import type { BatteryScenario } from "../types/battery";
const carbon: BatteryScenario["carbon"] = [
  {
    name: "制造",
    english: "Manufacturing",
    activity: 60,
    factor: 97.3333333333,
    color: "#8fbea5",
  },
  {
    name: "运输",
    english: "Transportation",
    activity: 1000,
    factor: 0.31,
    color: "#769caf",
  },
  {
    name: "使用",
    english: "Vehicle Use",
    activity: 5047.619047619,
    factor: 0.42,
    color: "#6fe7e1",
  },
  {
    name: "维护",
    english: "Maintenance",
    activity: 1,
    factor: 190,
    color: "#c3cba7",
  },
  {
    name: "退役",
    english: "Retirement",
    activity: 1,
    factor: 260,
    color: "#718079",
  },
];
export const usedVehicleScenario: BatteryScenario = {
  id: "used",
  name: "二手车交易评估",
  english: "Used EV Assessment",
  batteryId: "DXZC-A02-2026",
  vehicle: "2022 EV Demo",
  batteryType: "LFP",
  initialCapacity: 60,
  currentCapacity: 49.44,
  mileage: 68420,
  cycles: 1126,
  eolCycles: 2046,
  threshold: 80,
  confidence: [780, 1060],
  years: 3.1,
  risk: "LOW",
  riskLabel: "低风险",
  decision: "Continue Vehicle Use",
  decisionLabel: "继续车用",
  recommendation:
    "当前电池健康状态支持继续车用。建议保持定期检测，跟踪容量衰减与温度表现。",
  insights: [
    "Battery degradation remains stable.",
    "No significant abnormal thermal behavior detected.",
    "Current battery condition supports continued vehicle use.",
  ],
  insightNotes: [
    "示例容量曲线呈稳定退化趋势。",
    "示例温度记录未出现明显热异常。",
    "综合健康与寿命示例数据，建议继续车用。",
  ],
  completeness: 94,
  source: "Demo Dataset · 情景模拟",
  carbon,
};
export const retiredBatteryScenario: BatteryScenario = {
  ...usedVehicleScenario,
  id: "retired",
  name: "退役电池流转评估",
  english: "Retired Battery Assessment",
  batteryId: "DXZC-B07-2026",
  vehicle: "Retired EV Battery Demo",
  currentCapacity: 41.22,
  mileage: 168200,
  cycles: 2310,
  eolCycles: 2620,
  threshold: 60,
  confidence: [240, 380],
  years: 1.0,
  risk: "MEDIUM",
  riskLabel: "中等风险",
  decision: "Second-Life Utilization",
  decisionLabel: "梯次利用",
  recommendation:
    "容量已低于本演示的车用退役参考线。建议在通过安全筛选与适配验证后，评估低倍率固定式储能用途。",
  insights: [
    "Capacity is below the vehicle-use reference threshold.",
    "Moderate risk requires a dedicated safety assessment.",
    "Second-life storage is the proposed next application.",
  ],
  insightNotes: [
    "SOH 低于 80% 的车用参考线。",
    "中等风险；需完成专项安全筛选。",
    "建议评估固定式储能，尚未完成安全准入验证。",
  ],
  completeness: 88,
  carbon: carbon.map((stage) =>
    stage.name === "使用" ? { ...stage, activity: 7428.571428571 } : stage,
  ),
};
export const scenarios = {
  used: usedVehicleScenario,
  retired: retiredBatteryScenario,
};
export const lifecycleSteps = [
  { label: "Vehicle", zh: "整车信息", icon: "car" },
  { label: "Battery Data", zh: "电池数据", icon: "battery" },
  { label: "Health", zh: "健康评估", icon: "health" },
  { label: "Remaining Life", zh: "寿命预测", icon: "life" },
  { label: "Carbon", zh: "碳足迹", icon: "carbon" },
  { label: "Green Decision", zh: "绿色决策", icon: "decision" },
];
export const analysisSteps = [
  "Reading BMS Data",
  "Calculating SOH",
  "Estimating RUL",
  "Calculating Carbon Footprint",
  "Generating Recommendation",
];
