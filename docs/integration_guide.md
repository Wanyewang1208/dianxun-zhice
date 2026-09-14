# 现有 frontend 联调说明

本包不创建、不修改 frontend。组员只需对接一次 assessment 请求，无需自行拼接算法结果。

1. 按根目录 MERGE_GUIDE 合并模块，用 Python 3.12 执行 `python scripts/start_backend.py`。
2. 浏览器打开 `http://127.0.0.1:8013/api/v1/health`，确认 success 与 models_ready。
3. Base URL 为 `http://127.0.0.1:8013/api/v1`。前端端口默认允许 `http://localhost:5173`；如为 3000，启动时指定 `--allowed-origin http://localhost:3000`。localhost 与 127.0.0.1 是不同 Origin，必须匹配实际地址。
4. 将 docs/examples/assessment.request.json 的完整 JSON 用作首次请求。随后运行 `python scripts/smoke_test.py` 验证后端全链路。
5. 前端分别展示 BMS 质量、NASA 电芯模型、示例电池包决策；任何真实车辆输入不自动映射到 NASA case。

```javascript
// requestBody 来自 docs/examples/assessment.request.json 或按 API_CONTRACT 构造。
const API_BASE = 'http://127.0.0.1:8013/api/v1';
async function assess(requestBody) {
  const res = await fetch(`${API_BASE}/assessment`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(requestBody)
  });
  const envelope = await res.json();
  if (!res.ok || !envelope.success) {
    throw new Error(`${envelope.code}: ${envelope.message}`);
  }
  return envelope; // 保留 warnings，结果在 envelope.data
}
// const {data, warnings} = await assess(requestBody);
// data.recommendation.route_id === null 时显示“需补证据/专业复核”，不要默认选第一条。
```

把选中文件放入 assessment（避免先上传再拼接结果）：
```javascript
requestBody.bms = {
  telemetry_csv: await telemetryFile.text(),
  metadata_csv: await metadataFile.text(),
  max_gap_s: 30
};
const result = await assess(requestBody);
```

独立上传接口仅供调试：
```javascript
const form = new FormData();
form.append('telemetry', telemetryFile);
form.append('metadata', metadataFile);
const response = await fetch(`${API_BASE}/bms/validate`, {method:'POST', body:form});
const quality = await response.json();
```

`backend/.env.example` 可复制为 `backend/.env`，修改 DIANXUN_PORT/DIANXUN_ALLOWED_ORIGIN；命令行参数优先，其次现有环境变量，其次 .env。未配置秘密。服务绑定 127.0.0.1；前后端在同一台电脑运行，无需公网地址。跨电脑联调/反向代理尚未配置。

## 排查与展示规则

- fetch 网络失败：先确认服务进程与 health；检查 Origin 是否与允许地址完全相同。CORS 是浏览器访问设置，不是鉴权机制。
- 400：查看 error.message，检查字段、CSV 结构、单位、权重。不能把容量缺失改写为 0。
- 503：确认 model/ 和 data/ 一起合并，Python 3.12 依赖版本正确。
- quality.schema_ready=false：展示 issues，保留原始输入供用户纠正；该值不是电池安全评级。
- RUL not_available：显示 reason，不显示虚构寿命。
- weighted_score=null：方案被淘汰；显示 reason_codes。分数不是安全概率。
- 所有 Demo 权重/因子提示、未实车验证说明、SHAP 非因果说明应保留。不要添加未校准的 confidence 或商业检测准确率。

没有对现有 frontend 执行真实联调，因为本次未提供其代码；本次验证覆盖真实本地 HTTP 与文件上传。
