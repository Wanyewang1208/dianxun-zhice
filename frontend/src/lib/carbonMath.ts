import type { CarbonStage } from "../types/battery";
export function calculateEmission(activity: number, factor: number) {
  if (
    !Number.isFinite(activity) ||
    !Number.isFinite(factor) ||
    activity < 0 ||
    factor < 0
  )
    throw new Error("Invalid emission data");
  return activity * factor;
}
export function calculateLifecycleCarbon(stages: CarbonStage[]) {
  return (
    stages.reduce(
      (total, s) => total + calculateEmission(s.activity, s.factor),
      0,
    ) / 1000
  );
}
