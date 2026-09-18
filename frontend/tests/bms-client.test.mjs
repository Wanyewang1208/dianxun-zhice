import test from 'node:test';
import assert from 'node:assert/strict';
import { validateBms, qualityLabel } from '../src/lib/bmsClient.ts';

const summary = {schema_ready:true, warning_count:0, unvalidated_telemetry_columns:[], unvalidated_metadata_columns:[]};
const data = {summary, issues:[]};
test('posts to quality endpoint and returns validation result', async () => {
  const result = await validateBms('a,b\n1,2', 'c\n3', async (url, options) => {
    assert.equal(url, '/api/v1/bms/validate');
    assert.deepEqual(JSON.parse(options.body), {telemetry_csv:'a,b\n1,2',metadata_csv:'c\n3'});
    return new Response(JSON.stringify({success:true,data}));
  });
  assert.deepEqual(result,data);
});
test('quality rejection under HTTP 200 is not displayed as passed', () => {
  assert.equal(qualityLabel({...summary,schema_ready:false}), '核心字段未通过');
});
test('extra columns and warnings cannot appear as a clean pass', () => {
  assert.equal(qualityLabel({...summary,unvalidated_telemetry_columns:['fault_code']}), '存在未校验字段');
  assert.equal(qualityLabel({...summary,warning_count:1}), '核心字段可读取，需复核警告');
});
test('HTML fallback is a connection error, never demo success', async () => {
  await assert.rejects(validateBms('a','b',async()=>new Response('<html>demo</html>')),/服务|接口/);
});
test('row limit has actionable feedback', async () => {
  await assert.rejects(validateBms('a','b',async()=>new Response(JSON.stringify({success:false,error:{message:'CSV exceeds 10000 rows'}}),{status:400})),/10,000/);
});
test('JSON byte size is checked before network including escaping', async () => {
  let called=false;
  await assert.rejects(validateBms('"'.repeat(1100000),'b',async()=>{called=true;return new Response();}),/2 MiB/);
  assert.equal(called,false);
});
test('network failure is actionable', async () => {
  await assert.rejects(validateBms('a','b',async()=>{throw new TypeError('Failed to fetch')}),/服务/);
});
test('malformed success response is rejected', async () => {
  await assert.rejects(validateBms('a','b',async()=>new Response(JSON.stringify({success:true,data:{}}))),/接口/);
});
