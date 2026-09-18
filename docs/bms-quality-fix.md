# BMS 质量修复与双语前端整合

复测日期：2026-09-18。整合基线：dev / 7af12fb（含持久化中英文切换、手动评估与后端联调）。

## 最终行为

- 使用既有 AssessmentControls 上传入口，不另建重复面板；原有手动输入、团队样例、评估结果与中英文切换全部保留。
- BMS 额外字段逐列返回 unvalidated_column 警告，列出未校验范围。schema_ready 仅表示核心必需字段检查；页面分别显示核心字段失败、未校验字段、需复核警告和核心字段通过。旧后端缺少范围信息时不会显示无条件通过。
- 拒绝重复 CSV 表头（含开头空白行），里程数值规范化。新增后端 summary 字段：unvalidated_telemetry_columns、unvalidated_metadata_columns、all_supplied_fields_validated、schema_ready_scope。
- 质量报告可下载 JSON；新增结果标题、报告按钮和请求错误支持中文/English。
- 保留既有每文件 900 KB 上传限制及 UTF-8 校验，API 上限每表 10,000 行、请求 2 MiB。前端按 JSON 编码后字节数检查请求体，大小、行数和重复列名错误分别提示。共享请求超时仍为 120 秒。
- 数据质量检查不等于实车 SOH/RUL 验证或电池安全认证；单体数组、探针数组与故障事件专用分析尚未接入。

## 运行与连接

按仓库 README 启动 Python 后端（8013）与 Vite。VITE_API_BASE_URL 默认空，使用同源 /api/v1，开发时由 Vite 代理到 http://127.0.0.1:8013。生产必须配置同源后端路由，或显式设置 VITE_API_BASE_URL 并配置后端 CORS；纯静态站点本身不能运行 Python。

## 复测

- 后端 unittest：105 项全部通过。
- 前端 TypeScript/Vite 构建通过。
- BMS 标题与范围 5 项、站点 4 项全部通过。
- 接口适配 13 项检查及两个手动模式案例通过。
- 双语翻译、语言偏好保存、原有模型算术检查通过。
- 浏览器：团队合成样例 12/12 接收；中文/English 切换后结果数值不变，刷新保留 English；手动 Demo 返回容量 SOH 82.4%、假设等效循环 1374，保持原型标记；带单体数组和故障字段的样例明确显示 2 条警告。
- 独立代码审查：与 7af12fb 比较未发现新的 P1/P2 问题。

命令：python -m unittest discover -s tests -v；frontend 下 npm run build、npm run test:models、npm run test:sites、npm run test:bms、npm run test:integration、npm run test:i18n。

本轮没有取得或验证真实车辆数据；GitHub 代码同步不等同网站部署。
