export function qualityLabel(s: {schema_ready:boolean; warning_count:number; unvalidated_telemetry_columns?:string[]; unvalidated_metadata_columns?:string[]}): string {
  if (!s.schema_ready) return '核心字段未通过';
  if (!s.unvalidated_telemetry_columns || !s.unvalidated_metadata_columns) return '校验范围未知，请更新后端';
  if (s.unvalidated_telemetry_columns.length || s.unvalidated_metadata_columns.length) return '存在未校验字段';
  if (s.warning_count) return '核心字段可读取，需复核警告';
  return '核心字段校验通过';
}
