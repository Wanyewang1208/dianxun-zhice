import type { BatteryScenario } from "../types/battery";
export function calculateSOH(current: number, initial: number): number {
  if (
    !Number.isFinite(current) ||
    !Number.isFinite(initial) ||
    initial <= 0 ||
    current < 0
  )
    throw new Error("Invalid capacity");
  return (current / initial) * 100;
}
export function calculateBaselineRUL(
  a: number,
  b: number,
  threshold: number,
  currentCycle: number,
): number {
  if (
    ![a, b, threshold, currentCycle].every(Number.isFinite) ||
    b >= 0 ||
    currentCycle < 0
  )
    throw new Error("Invalid linear baseline");
  return Math.max(0, (threshold - a) / b - currentCycle);
}
export function getBatteryModel(s: BatteryScenario) {
  const soh = calculateSOH(s.currentCapacity, s.initialCapacity);
  // Demo parameters connect the current observation to the scenario's assumed EOL.
  // This is a local future baseline, not a fitted model for the complete history.
  const b = (s.threshold - soh) / (s.eolCycles - s.cycles),
    a = soh - b * s.cycles;
  return {
    soh,
    a,
    b,
    rul: Math.round(calculateBaselineRUL(a, b, s.threshold, s.cycles)),
  };
}
export function getDegradationCurve(s: BatteryScenario) {
  const { soh, a, b } = getBatteryModel(s);
  const history = Array.from({ length: 7 }, (_, i) => ({
    cycle: Math.round((s.cycles * i) / 6),
    historical: Number((100 - (100 - soh) * Math.pow(i / 6, 0.68)).toFixed(2)),
    predicted: i === 6 ? soh : null,
  }));
  return [
    ...history,
    ...Array.from({ length: 5 }, (_, i) => {
      const cycle = Math.round(
        s.cycles + ((s.eolCycles - s.cycles) * (i + 1)) / 5,
      );
      return {
        cycle,
        historical: null,
        predicted: Number((a + b * cycle).toFixed(2)),
      };
    }),
  ];
}
