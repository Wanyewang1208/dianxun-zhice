import { useEffect, useRef, useState } from 'react';
import { issueMessage, qualityLabel, validateBms } from '../lib/bmsClient';
import type { QualityResult } from '../lib/bmsClient';

export default function BmsQualityPanel() {
  const [telemetry,setTelemetry]=useState<File|null>(null);
  const [metadata,setMetadata]=useState<File|null>(null);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const [result,setResult]=useState<QualityResult|null>(null);
  const [source,setSource]=useState('');
  const active=useRef<AbortController|null>(null);
  useEffect(()=>()=>active.current?.abort(),[]);
  const reset=()=>{setResult(null);setError('');setSource('');};
  async function run(sample=false) {
    if (active.current) return;
    reset();setBusy(true);
    const controller=new AbortController();active.current=controller;
    const timer=setTimeout(()=>controller.abort(),60000);
    try {
      let t:string,m:string;
      if (sample) {
        const files=await Promise.all(['good_telemetry.csv','metadata.csv'].map(async name=>{
          const response=await fetch('/bms-samples/'+name,{signal:controller.signal});
          if (!response.ok) throw new Error('合成样例文件加载失败。');
          return response.text();
        }));
        [t,m]=files;
        setSource('内置合成样例（非真实车辆）');
      } else {
        if (!telemetry || !metadata) throw new Error('请选择时序 CSV 和元数据 CSV 两个文件。');
        if (telemetry.size+metadata.size>2*1024*1024) throw new Error('文件合计超过 2 MiB，请先拆分成小片段。');
        const decode=async(file:File)=>new TextDecoder('utf-8',{fatal:true}).decode(await file.arrayBuffer());
        try { [t,m]=await Promise.all([decode(telemetry),decode(metadata)]); }
        catch { throw new Error('文件不是有效 UTF-8 文本，请将 CSV 保存为 UTF-8 编码后重试。'); }
        setSource(`${telemetry.name} + ${metadata.name}（来源由上传者声明）`);
      }
      const checked=await validateBms(t,m,fetch,controller.signal);
      if (!controller.signal.aborted) setResult(checked);
    } catch(e) {setError(e instanceof Error?e.message:'文件处理失败，请检查格式。');}
    finally {clearTimeout(timer);active.current=null;setBusy(false);}
  }
  const s=result?.summary;
  return <section className="bms-panel" aria-labelledby="bms-heading" id="bms-quality">
    <div className="bms-heading"><div><span className="eyebrow">BMS DATA QUALITY</span><h2 id="bms-heading">BMS 数据接入检查</h2></div><span className="dataset-badge">数据质量 · 不预测健康与寿命</span></div>
    <p>上传标准格式的时序与电池包元数据，检查缺失、重复、越界及时间中断。此处结果独立于上方示例护照，不会替换示例 SOH、RUL 或退役建议。</p>
    <div className="bms-files">
      <label>时序 CSV<input type="file" accept=".csv,text/csv" disabled={busy} onChange={e=>{setTelemetry(e.target.files?.[0]||null);reset();}} /></label>
      <label>元数据 CSV<input type="file" accept=".csv,text/csv" disabled={busy} onChange={e=>{setMetadata(e.target.files?.[0]||null);reset();}} /></label>
    </div>
    <p className="bms-help">UTF-8 编码；每张表最多 10,000 行，请求上限 2 MiB。原始供应商字段须先转换，时间戳须注明时区；单位、电流方向和车辆身份不能猜测。</p>
    <div className="bms-actions">
      <button className="primary-button compact" disabled={busy||!telemetry||!metadata} onClick={()=>run()}>{busy?'正在检查…':'检查所选文件'}</button>
      <button className="bms-secondary" disabled={busy} onClick={()=>run(true)}>测试内置合成样例</button>
      <a href="/bms-samples/good_telemetry.csv" download>时序样例</a><a href="/bms-samples/metadata.csv" download>元数据样例</a>
    </div>
    {error&&<p className="bms-error" role="alert">{error}</p>}
    {result&&s&&<div className="bms-result" aria-live="polite">
      <h3>{qualityLabel(s)}</h3><p>{source}</p>
      <p>{s.synthetic_fixture_present?'包含合成测试数据。':'数据真实性未独立核验。'} 校验通过不等于电池安全、SOH/RUL 准确或可退役处置。</p>
      <dl className="bms-counts">{[['输入行',s.input_rows],['接收行',s.accepted_rows],['拒绝行',s.rejected_rows],['错误',s.error_count],['警告',s.warning_count]].map(([label,value])=><div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>
      {(s.unvalidated_telemetry_columns.length>0||s.unvalidated_metadata_columns.length>0)&&<p className="bms-warning">以下字段仅保留，未参与校验或健康、安全分析：{[...s.unvalidated_telemetry_columns,...s.unvalidated_metadata_columns].join('、')}。单体数组、探针数组及故障事件的专用分析尚未接入。</p>}
      {result.issues.length>0&&<><div className="bms-table"><table><thead><tr><th>CSV 行号</th><th>级别</th><th>字段</th><th>问题</th></tr></thead><tbody>{result.issues.slice(0,100).map((issue,i)=><tr key={i}><td>{issue.csv_row||'整表'}</td><td>{issue.severity==='error'?'错误':'警告'}</td><td>{issue.field||'—'}</td><td>{issueMessage(issue.code,issue.detail)}<details><summary>详细信息</summary>{issue.code}：{issue.detail}</details></td></tr>)}</tbody></table></div><p>显示前 {Math.min(100,result.issues.length)} 条，共 {result.issues.length} 条。</p></>}
      <button className="bms-secondary" onClick={()=>{
        const url=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)],{type:'application/json'}));
        const a=document.createElement('a');a.href=url;a.download='bms-quality-report.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
      }}>下载完整质量报告</button>
    </div>}
  </section>;
}
