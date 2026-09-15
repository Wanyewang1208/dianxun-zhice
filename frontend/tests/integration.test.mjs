import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createRequire } from "node:module";
const { build } = createRequire(import.meta.resolve("vite"))("esbuild");
const bundle = await build({
  stdin: {
    contents:
      "export * from './src/lib/api.ts'; export * from './src/lib/assessmentAdapter.ts'",
    resolveDir: process.cwd(),
  },
  bundle: true,
  write: false,
  format: "esm",
  platform: "node",
  define: { "import.meta.env": "{}" },
});
const api = await import(
  "data:text/javascript;base64," +
    Buffer.from(bundle.outputFiles[0].text).toString("base64")
);
const fixture = JSON.parse(
  await readFile("../docs/examples/assessment.response.json", "utf8"),
);
const fresh = () => structuredClone(fixture.data);
let checks = 0;
const check = (name, fn) => {
  fn();
  checks++;
  console.log("PASS", name);
};
check("contract fixture maps units and exact recommendation", () => {
  const v = api.assessmentAdapter(fresh());
  assert.equal(v.soh, 77.39439392089844);
  assert.equal(v.carbon, 5.560654);
  assert.equal(v.decision, "Repair & Reuse");
  assert.equal(v.score, v.selected.weighted_score * 100);
  assert.equal(v.contributions[0].feature, "voltage_600s_v");
});
check("unavailable RUL/carbon/SHAP and HOLD never use Demo fallback", () => {
  const r = fresh();
  r.rul = { ...r.rul, status: "not_available", predicted_rul_cycles: null };
  r.carbon = { status: "not_provided", reason: "none" };
  r.explainability = { status: "not_available", reason: "none" };
  r.recommendation.route_id = null;
  const v = api.assessmentAdapter(r);
  assert.equal(v.rul, null);
  assert.equal(v.carbon, null);
  assert.equal(v.score, null);
  assert.equal(v.decision, "HOLD");
  assert.deepEqual(v.contributions, []);
});
check("zero remains zero", () => {
  const r = fresh();
  r.rul.predicted_rul_cycles = 0;
  r.candidate_paths.find(
    (p) => p.route_id === r.recommendation.route_id,
  ).weighted_score = 0;
  const v = api.assessmentAdapter(r);
  assert.equal(v.rul, 0);
  assert.equal(v.score, 0);
  assert.equal(api.format(0), "0.00");
});
check("malformed nested collections reject atomically", () => {
  for (const mutate of [
    (r) => delete r.carbon.summary.missing_stages,
    (r) => delete r.data_quality.summary,
    (r) => (r.explainability.contributions = null),
    (r) => (r.recommendation.route_id = "unknown"),
    (r) => (r.candidate_paths[0].weighted_score = NaN),
  ]) {
    let r = fresh();
    mutate(r);
    assert.throws(
      () => api.assessmentAdapter(r),
      (e) => e.kind === "incomplete",
    );
  }
});
const realFetch = globalThis.fetch;
try {
  for (const [name, status, payload, kind] of [
    ["invalid BMS", 400, { success: false }, "invalid"],
    ["server failure", 500, { success: false }, "failed"],
    ["incomplete envelope", 200, { success: true, data: {} }, "incomplete"],
  ]) {
    globalThis.fetch = async () =>
      new Response(JSON.stringify(payload), { status });
    await assert.rejects(api.runAssessment({}), (e) => e.kind === kind);
    checks++;
    console.log("PASS", name);
  }
  globalThis.fetch = async () => {
    throw new TypeError("fetch failed");
  };
  await assert.rejects(api.healthCheck(), (e) => e.kind === "offline");
  checks++;
  globalThis.fetch = (_, options) =>
    new Promise((_, reject) =>
      options.signal.addEventListener("abort", () =>
        reject(new Error("aborted")),
      ),
    );
  await assert.rejects(
    api.request("assessment", {}, 10),
    (e) => e.kind === "timeout",
  );
  checks++;
} finally {
  globalThis.fetch = realFetch;
}
console.log(`${checks} integration checks passed`);
