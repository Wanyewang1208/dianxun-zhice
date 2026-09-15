# 前端联调与证据边界

本轮基于已合并 PR #1 的 dev（592658f），开发分支为 `feature/frontend-assessment-integration`。保留现有 Overview 视觉和本地 `demoBattery.ts`，使用原有五个模块入口展示统一结果，没有重建前端。

## 启动

需要 Python 3.12、Node >=22.18。首次启动后端会在项目 `.venv` 安装锁定依赖。

项目根目录运行：
```powershell
py -3.12 scripts/start_backend.py --allowed-origin http://127.0.0.1:4173
```

另一终端：
```powershell
cd frontend
Copy-Item .env.example .env
npm install
npm run dev -- --host 127.0.0.1 --port 4173 --strictPort
```

打开 http://127.0.0.1:4173 。`.env` 的 `VITE_API_BASE_URL` 是公开前端配置，不能放 API Key。后端 CORS 允许源必须与浏览器协议、主机名、端口完全相同。若使用默认 `npm run dev` 的 localhost:5173，则后端也设置 `--allowed-origin http://localhost:5173`。

## 演示操作

1. 确认 Backend Connected；初始仍是 DEMO DATA，本地展示不会因后端离线崩溃。
2. Use Demo Dataset 使用仓库 `docs/examples/assessment.request.json`，Vite 直接打包此固定输入，不复制或下载随机样例。
3. Validate BMS 调用 `/api/v1/bms/validate`。也可上传 UTF-8 telemetry / metadata CSV，每个不超过 900 KB；只在内存中处理并发送本地后端，不持久化。
4. Start Assessment 只发起一次 `/api/v1/assessment`，所有模块共享该响应。加载阶段是等待动画，不是后端独立进度事件。
5. LIVE ANALYSIS 下锁定 Demo 场景切换。五个模块与报告使用同一个 request_id。Reset to Demo 显式恢复本地模拟。
6. Assessment Report → Export PDF 调用浏览器打印；打印样式展开完整报告、隐藏导航与按钮。

## 各类证据不能混用

- BMS：合成样例 `SYNTHETIC_PACK_001` 或上传 CSV，只检查质量；schema_ready 不代表电池安全通过。
- SOH/RUL/TreeSHAP：公开 NASA B0018 第 66 次循环，后端真实模型推理，但未验证整车迁移。
- 容量：RUL 返回 Ah 输入；初始容量基准与 SOH 不同，派生容量保持率 82.57% 不等于预测 SOH 77.39%。
- 碳与决策：固定模拟电池包场景，后端实际计算，但活动、路径参数、安全声明包含 Demo 假设，不是经认证的产品足迹或退役检测。
- 碳四阶段：manufacturing / use / maintenance_transport / end_of_life。材料包含在制造中，运输与维护合并，不编造六阶段。
- 分数：weighted_score 与 utility_components 为 0–1，界面换算为 0–100；technical_score 原始字段不是同一量纲。推荐为 null 时显示 HOLD。

## 当前接口缺项与对接注意

未提供整车信息、内阻、温度稳定性、单体一致性检测、绝缘检测、异常电压风险分类、RUL 置信区间、日历寿命、真实预测曲线、推荐应用场景。界面显示 N/A 或 UNKNOWN。

响应的碳详情返回来源/年份/状态，未回传地区和 confidence_level；请求中虽然有这些字段，但不伪装成响应结果。决策场景健康输入也未回传，不用 NASA SOH/RUL 替代。

HTTP 200 也可能出现业务 not_available/not_provided、BMS schema_ready=false、推荐 HOLD，均保留含义。响应结构不完整时拒绝替换当前结果，并提供重试和本地 Demo。先前成功结果在重试失败时保留并标记。

API Client 的细分 SOH/RUL/Explain 接口仅供调试；正式模块不分别请求。Context 每 30 秒检查一次健康状态，120 秒评估超时；健康检查是可用性指示，不是模型持续监控。

## 检查

```powershell
cd frontend
node tests/integration.test.mjs
npm run test:models
npm run test:sites
npm run build
```

首次实测固定样例：health 200；validate 12 accepted / 0 rejected；assessment 200，SOH 77.39439392089844%，RUL 36.28555257448237 reference cycles，碳排放 5560.654 kgCO₂e，推荐 repair_then_use。开发者工具或命令行可以核对 request_id，避免拿文档中的历史响应冒充实时结果。

2026-09-15 验证记录：9 项接口/Adapter 检查、现有模型检查、4 项 Sites 运行时测试、最终生产构建均通过。浏览器完整流程成功，五个模块共享同一个 request_id；异常合成 CSV 显示 0 accepted / 1 rejected；停止后端后出现离线提示，恢复后 Retry 成功。390px 页面及模块未出现横向溢出。全新浏览器会话无控制台 error/warn。打印按钮已触发，未生成或检查独立 PDF 文件。

本轮通过 `feature/frontend-assessment-integration` 分支交付，PR 目标为 `dev`，不直接修改或推送 main。`.venv`、`node_modules`、`dist`、`.env` 由 `.gitignore` 排除。

## PR #2 兼容性验证（2026-09-15）

- 同步 dev `8de5c08a7f7365818fd8fcb0a31632fcde5a9f12`，安全 merge 提交 `9905f4b7ce3d69f4ffd060d89bca597783e15298`；无冲突，main 保持 `eb190cf`。
- PR #2 仅提供后端手动模式。本轮保留现有页面，增加同一评估入口内的 Manual Input / Manual Demo 表单与结果适配；新旧响应在 assessmentAdapter 中统一处理，原始手动证据单独保留，不改写成 NASA 预测。
- 手填字段包含品牌、类型、额定/当前容量、循环、里程、充电方式、快充比例、日均/年里程、环境温度、SOC 范围及条件记录。品牌/工况等记录不会被声称为已验证预测特征。
- 新响应包括 input_snapshot、effective_condition、field_sources、prototype_assumptions、soh.calculated_soh/measured_soh/difference_pp、residual_value、current_use_value、second_life_potential。手动质量结构为 data_quality.manual/bms；安全状态不再使用原 NASA 分支 gates 结构。
- Manual Input 的空值保持 null，默认不带 BMS 或假设。点击 Start Assessment 校验手填 schema；只有选择 CSV 才能单独 Validate BMS。切回团队 NASA 样例恢复原请求。
- 浏览器实填品牌“联调测试电池”、LFP、60/49.44 kWh、1126循环、68420 km、home_ac、20%快充，报告完整回显，容量 SOH 82.4%。RUL/SHAP/碳缺证据时为 N/A；决策 HOLD；价值指数/价格缺证据时为 null。
- Manual Demo 直接采用 docs/examples/manual_demo.request.json：显式2500循环寿命、0.9安全因子、0.91一致性因子。返回1374 assumed_equivalent_cycles、指数76.978、价格范围16319.6377344–20770.4480256 CNY。以上均为 Prototype Technical Estimation，不是整车模型结果或市场鉴价。
- HTTP 实测：health 200；BMS 12 accepted；原 assessment SOH 77.39439392089844%；手填字段回显、原型估值、热事件阻断均符合契约；CORS匹配127.0.0.1:4173。热事件时 index_bounds 也可为 null，Adapter/报告已兼容。
- 后端99项测试、手动HTTP smoke、原9项前端接口检查加2组手动/阻断兼容检查、原模型检查、4项Sites测试及生产构建通过。浏览器手动/原型估值/NASA报告均可打开，离线错误和Retry恢复有效。
- 完整流程指各阶段有可追溯结果或明确的不可用状态，不代表每个分支都有寿命、SHAP、碳与价格数值。所有原型及未完成真实整车大规模验证说明保留。独立PDF文件仍未生成或核验。

最终提交前已再次实际操作 Demo Dataset、Manual Input 与 Manual Demo：车辆品牌/型号、电池品牌/类型、容量、里程、循环、地区、快充、温度和新电池价格均可回显。计算 SOH 82.40% 与专业检测声明 80.00% 分开显示，差值 2.40 个百分点；普通手填不因填写价格就补造估值。桌面及 390px 窄屏页面/报告无横向溢出，打印入口调用无报错。最终生产构建、接口兼容与既有模型/Sites回归检查通过。

本适配通过 feature/frontend-assessment-integration 提交交付，目标 PR 为 dev，不直接合入 main。打印入口检查不等于独立 PDF 文件的排版核验；尚未生成或核验独立 PDF。
