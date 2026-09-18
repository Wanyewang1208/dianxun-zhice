import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import { createRequire } from 'node:module';
const { build } = createRequire(import.meta.resolve('vite'))('esbuild');
assert.ok(existsSync('src/i18n/index.ts'), 'The bilingual display module must exist');
const bundle = await build({entryPoints:['src/i18n/index.ts'],bundle:true,write:false,format:'esm',platform:'node'});
const {translate, readLanguage, saveLanguage} = await import('data:text/javascript;base64,'+Buffer.from(bundle.outputFiles[0].text).toString('base64'));
assert.equal(translate('Battery Health','zh'),'电池健康');
assert.equal(translate('存在未校验字段','en'),'Some fields have not been validated');
assert.equal(translate('下载完整质量报告','en'),'Download full quality report');
assert.match(translate('telemetry: preserved but NOT validated or used for health/safety inference','zh'),/未校验/);
assert.equal(translate('额定容量 (kWh)','en'),'Rated capacity (kWh)');
assert.equal(translate('输入数据未通过检查，请核对手动字段、容量单位或 CSV 与元数据。','en'),'Input validation failed. Check the manual fields, capacity units, CSV and metadata.');
assert.equal(translate(82.4,'en'),82.4);
assert.equal(translate(null,'zh'),null);
assert.equal(translate('B0018','zh'),'B0018');
assert.equal(translate('49.44 kWh','en'),'49.44 kWh');
assert.equal(translate('Unknown backend evidence','zh'),'Unknown backend evidence');
for (const value of ['SOH','RUL','SHAP','LFP','kgCO₂e','tCO₂e','kWh','CNY','SOH = Qcurrent / Qinitial × 100%','C = Σ(Activity Data × Emission Factor)']) {
  assert.equal(translate(value,'zh'),value);
  assert.equal(translate(value,'en'),value);
}
for (const marker of ['DEMO DATA','DEMO DATA / Local Demo','DEMO DATASET / 2026','DEMO v1.0','Manual Demo · 原型估值样例']) {
  assert.match(translate(marker,'zh'),/Demo/i);
  assert.match(translate(marker,'en'),/Demo/i);
}
assert.equal(translate('36.3 cycles','zh'),'36.3 次循环');
assert.equal(translate('Cycle 66','zh'),'循环 66');
assert.equal(translate('true','en'),'Yes');
assert.equal(translate('false','zh'),'否');
assert.equal(translate('lowers_prediction','zh'),'降低预测值');
assert.equal(translate('Gap exceeds 30.0 seconds; do not integrate across gap','zh'),'间隔超过 30.0 秒；不可跨越该间隔积分');
assert.equal(translate('Health: voltage_unit must be V; no inferred conversion; invalid rated capacity','zh'),'Health: voltage_unit 必须为 V；不进行推测换算; 额定容量无效');
assert.equal(translate('Unexpected: vendor-specific detail','zh'),'Unexpected: vendor-specific detail');
const storage = new Map();
const local={getItem:k=>storage.get(k)??null,setItem:(k,v)=>storage.set(k,v)};
assert.equal(readLanguage(local),'zh');
saveLanguage('en',local);assert.equal(readLanguage(local),'en');
local.setItem('dianxun.language','invalid');assert.equal(readLanguage(local),'zh');
const blocked={getItem(){throw Error('blocked')},setItem(){throw Error('blocked')}};
assert.equal(readLanguage(blocked),'zh');assert.doesNotThrow(()=>saveLanguage('en',blocked));
console.log('PASS: bilingual labels/errors, units and unknown evidence unchanged, preference persistence and blocked storage');
