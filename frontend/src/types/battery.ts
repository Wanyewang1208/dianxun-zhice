export type ScenarioId = "used" | "retired";
export type ModuleId = "health" | "life" | "carbon" | "decision" | "report";
export interface CarbonStage {
  name: string;
  english: string;
  activity: number;
  factor: number;
  color: string;
}
export interface BatteryScenario {
  id: ScenarioId;
  name: string;
  english: string;
  batteryId: string;
  vehicle: string;
  batteryType: string;
  initialCapacity: number;
  currentCapacity: number;
  mileage: number;
  cycles: number;
  eolCycles: number;
  threshold: number;
  confidence: [number, number];
  years: number;
  risk: "LOW" | "MEDIUM";
  riskLabel: string;
  decision: string;
  decisionLabel: string;
  recommendation: string;
  insights: [string, string, string];
  insightNotes: [string, string, string];
  completeness: number;
  source: string;
  carbon: CarbonStage[];
}
