export type QualitySummary = {
  input_rows: number; accepted_rows: number; rejected_rows: number;
  error_count: number; warning_count: number; schema_ready: boolean;
  synthetic_fixture_present: boolean;
  unvalidated_telemetry_columns: string[]; unvalidated_metadata_columns: string[];
};
export type QualityResult = {
  summary: QualitySummary;
  issues: {csv_row:number; severity:string; code:string; field:string; detail:string}[];
};

const issueMessages:Record<string,string> = {
  unvalidated_column:'该字段仅保留，尚未校验或用于健康、安全分析',
  missing_telemetry_column:'时序表缺少必需字段，请核对列名或转换供应商字段',
  missing_metadata_column:'元数据表缺少必需字段',
  invalid_metadata:'电池包元数据不合格，请核对单位、容量及电流方向',
  metadata_rejected:'该电池包元数据不合格，相关时序行已拒绝',
  unknown_battery_id:'电池 ID 未在元数据中找到',
  timestamp_timezone_missing:'时间戳缺少时区，请注明 Z 或 +08:00 等偏移',
  timestamp_invalid:'时间戳无法解析',
  numeric_missing_or_invalid:'缺少有效数值，请检查空值、文本或无效编码',
  plausibility_range:'数值超出导入合理范围；该范围不是安全阈值',
  extrema_inverted:'最大值小于最小值',
  invalid_charge_status:'充放电状态不在约定枚举中',
  unknown_charge_state:'状态未知，无法进行片段分类',
  current_status_mismatch:'电流方向与充放电状态不一致，请复核',
  duplicate_timestamp:'同一电池的时间戳重复，冲突行均已隔离',
  out_of_order_input:'原始记录未按时间排序，接收结果已排序',
  time_gap:'时间间隔超过允许值，不应跨缺口积分',
  mileage_missing_or_invalid:'里程缺失或无效，相关分析不可用',
  mileage_column_absent:'未提供里程，建议补充',
};
export const issueMessage=(code:string,detail:string)=>issueMessages[code]||detail;

export function qualityLabel(s: QualitySummary): string {
  if (!s.schema_ready) return '核心字段未通过';
  if (s.unvalidated_telemetry_columns.length || s.unvalidated_metadata_columns.length) return '存在未校验字段';
  if (s.warning_count) return '核心字段可读取，需复核警告';
  return '核心字段校验通过';
}

export async function validateBms(telemetry:string, metadata:string, request:typeof fetch=fetch, signal?:AbortSignal):Promise<QualityResult> {
  const body=JSON.stringify({telemetry_csv:telemetry,metadata_csv:metadata});
  if (new TextEncoder().encode(body).length>2*1024*1024) throw new Error('请求超过 2 MiB，请按车辆和时间段拆分文件；每张 CSV 最多 10,000 行。');
  let response:Response;
  try { response=await request('/api/v1/bms/validate',{method:'POST',headers:{'Content-Type':'application/json'},body,signal}); }
  catch { throw new Error(signal?.aborted ? '请求已取消或超时，请缩小数据片段后重试。' : '无法连接 BMS 校验服务，请确认后端服务已启动并连接到此网页。'); }
  let envelope;
  try { envelope=await response.json(); }
  catch { throw new Error('BMS 接口未返回有效结果，请确认校验服务已连接；静态演示站点不能单独处理上传。'); }
  if (!response.ok || !envelope.success) {
    const message=envelope.error?.message || '';
    if (response.status===413) throw new Error('请求超过 2 MiB，请拆分数据后重试。');
    if (message.includes('10000 rows')) throw new Error('CSV 超过 10,000 行，请按车辆和时间段拆分后重试。');
    if (message.includes('Duplicate CSV columns')) throw new Error('CSV 存在重复列名，请修改后重试：'+message);
    if (response.status>=500 || response.status===404) throw new Error('BMS 校验服务不可用，请检查后端服务连接。');
    throw new Error('文件未能处理：'+(message || '请检查 CSV 格式和 UTF-8 编码。'));
  }
  const result=envelope.data;
  if (!result || typeof result.summary?.schema_ready!=='boolean' || !Array.isArray(result.issues)
      || !Array.isArray(result.summary.unvalidated_telemetry_columns) || !Array.isArray(result.summary.unvalidated_metadata_columns)) {
    throw new Error('BMS 接口版本不匹配或返回不完整，请连接更新后的后端服务。');
  }
  return result;
}
