import assert from "node:assert/strict";
import {
  calculateSOH,
  calculateBaselineRUL,
  getBatteryModel,
  getDegradationCurve,
} from "../src/lib/batteryMath.ts";
import {
  calculateEmission,
  calculateLifecycleCarbon,
} from "../src/lib/carbonMath.ts";
import {
  usedVehicleScenario as a,
  retiredBatteryScenario as b,
} from "../src/data/demoBattery.ts";
assert.ok(Math.abs(calculateSOH(49.44, 60) - 82.4) < 1e-8);
assert.ok(Math.abs(calculateSOH(41.22, 60) - 68.7) < 1e-8);
assert.throws(() => calculateSOH(1, 0));
assert.throws(() => calculateSOH(-1, 60));
assert.throws(() => calculateBaselineRUL(100, 0, 80, 1000));
assert.equal(getBatteryModel(a).rul, 920);
assert.equal(getBatteryModel(b).rul, 310);
for (const s of [a, b]) {
  const model = getBatteryModel(s);
  assert.ok(Math.abs(model.a + model.b * s.eolCycles - s.threshold) < 1e-8);
  const curve = getDegradationCurve(s);
  assert.equal(curve.at(-1).predicted, s.threshold);
  assert.equal(curve[6].historical, Number(model.soh.toFixed(2)));
}
assert.equal(calculateEmission(8420, 0.42), 3536.4);
assert.equal(calculateLifecycleCarbon(a.carbon).toFixed(2), "8.72");
assert.equal(calculateLifecycleCarbon(b.carbon).toFixed(2), "9.72");
assert.throws(() => calculateEmission(-1, 0.42));
assert.notEqual(a.decision, b.decision);
assert.equal(a.insights.length, 3);
assert.equal(b.insights.length, 3);
console.log(
  "PASS: SOH capacity ratios, invalid inputs, both RUL baselines, chart endpoints, carbon arithmetic and scenario isolation.",
);
