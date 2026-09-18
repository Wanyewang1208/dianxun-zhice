import test from 'node:test';
import assert from 'node:assert/strict';
import { qualityLabel } from '../src/lib/bmsClient.ts';
const summary={schema_ready:true,warning_count:0,unvalidated_telemetry_columns:[],unvalidated_metadata_columns:[]};
test('core failure under HTTP 200 is not passed',()=>assert.equal(qualityLabel({...summary,schema_ready:false}),'核心字段未通过'));
test('unchecked fields cannot appear as clean pass',()=>assert.equal(qualityLabel({...summary,unvalidated_telemetry_columns:['fault_code']}),'存在未校验字段'));
test('warnings require review',()=>assert.equal(qualityLabel({...summary,warning_count:1}),'核心字段可读取，需复核警告'));
test('old backend without explicit scope cannot appear as clean pass',()=>assert.equal(qualityLabel({schema_ready:true,warning_count:0}),'校验范围未知，请更新后端'));
test('normal core fields pass',()=>assert.equal(qualityLabel(summary),'核心字段校验通过'));
