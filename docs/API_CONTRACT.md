# 电循智策 API Contract v1.0

Base URL：`http://127.0.0.1:8013`。仅本地 Demo。JSON 使用 UTF-8，数值必须有限，不允许 NaN/Infinity。请求体上限 2 MiB；CSV 每表上限 10000 行。未知顶层字段拒绝。无鉴权、无文件持久化。

## 接口表与兼容映射

| Method | URL | 用途 | V0.3 对应 |
|---|---|---|---|
| GET | /api/v1/health | 启动时已真实加载 SOH/RUL 并做样例推理的就绪状态 | /health 保留原格式 |
| GET | /api/v1/status | health 别名 | 新增 |
| POST | /api/v1/bms/validate | CSV 上传与质量检查 | 原 bms_validate.validate |
| POST | /api/v1/soh | NASA 电芯 SOH 推理 | 原 XGBoost 模型 |
| POST | /api/v1/rul | 历史容量特征→已有 RUL 模型推理 | 原 V0.2 模型，非重新训练 |
| POST | /api/v1/explain | 真实单样本 TreeSHAP | /v0.3/explain 保留 |
| POST | /api/v1/carbon | 生命周期活动量×因子 | 原 carbon.calculate |
| POST | /api/v1/decision | 安全门槛→Pareto→加权推荐 | /v0.3/decision 保留 |
| POST | /api/v1/assessment | 正式前端统一调用入口 | /v0.3/report 保留，新增聚合格式 |

旧 `/v0.3/*` 成功响应保持原结构，不加 v1 外壳。旧 report 的 RUL 仍读取 V0.2 保存结果；新 RUL/assessment 读取同一折模型进行推理。旧接口失败仍为 `{"error":{"code":"...","message":"..."}}`，在新服务中的错误码统一为下面的大写码。原始服务器还可通过 `python -m backend.v03.api_server` 启动，用于完整复现原错误码行为。

## 统一 v1 JSON 响应

```json
{"success":true,"code":"OK","message":"ok","data":{},"error":null,"request_id":"服务端生成的32位追踪ID","schema_version":"1.0","warnings":["原型边界说明"]}
```

失败时 `success=false`、`data=null`、`error={"code":"INVALID_REQUEST","message":"具体原因"}`，顶层 code/message 同步。`warnings` 始终提示证据边界，不是电池故障列表。request_id 仅关联响应，服务不建立历史任务数据库。

| HTTP | code | 含义与处理 |
|---|---|---|
| 200 | OK | 请求成功；仍须检查模块 status、schema_ready、推荐是否为空 |
| 400 | INVALID_REQUEST | JSON/CSV/字段/单位/枚举/权重错误，修正输入 |
| 404 | NOT_FOUND | URL 不存在 |
| 413 | PAYLOAD_TOO_LARGE | 超过 2 MiB，请缩小样例 |
| 415 | UNSUPPORTED_MEDIA_TYPE | 普通接口只接受 application/json |
| 503 | MODEL_UNAVAILABLE | 启动就绪检查失败，检查依赖和模型 |
| 503 | RESOURCE_UNAVAILABLE | 运行所需模型或数据文件缺失 |
| 500 | PROCESSING_FAILED | 内部失败，检查服务日志 |

**数据质量不合格、安全方案不满足约束、容量历史不足不是 HTTP 故障**：分别检查 `summary.schema_ready=false`、`recommendation.route_id=null`、`rul.status=not_available`。不得把这些渲染成“检测通过”。

## 1. health/status

无请求体。data 为 `{"status":"ok","mode":"local_research_demo","models_ready":true,"real_vehicle_validated":false}`。就绪检查发生在启动时，不是持续后台模型监控。配置缺失的其他模块可能仍在调用时返回 503。

## 2. BMS 上传与质量检查

JSON 请求：
```json
{"telemetry_csv":"battery_id,timestamp,pack_voltage,...\n...","metadata_csv":"battery_id,battery_chemistry,...\n...","max_gap_s":30}
```
telemetry_csv、metadata_csv 为必填 CSV 文本。max_gap_s 可选，默认 30 秒，正有限数。可直接读取用户选择的文件后发送文本。

也支持 `multipart/form-data`：文件字段 `telemetry`、`metadata` 必填，文本 `max_gap_s` 可选。**使用 FormData 时不要手工设置 Content-Type**。仅接收 UTF-8 CSV，不接收 Excel 文件；文件名不用于服务器路径，不保存上传文件。

| 遥测必填列 | 类型/单位/约定 |
|---|---|
| battery_id | 字符串，必须匹配元数据 |
| timestamp | ISO8601，必须含 Z 或 +08:00 等时区 |
| pack_voltage | V |
| pack_current | A；符号由元数据声明，输出规范为放电为正 |
| SOC | %，0–100 |
| cell_voltage_max/min | V，最大值不得低于最小值 |
| temperature_max/min | degC，最大值不得低于最小值 |
| charge_status | charging / discharging / idle / unknown |
| mileage（可选） | km |

元数据必填列：`battery_id`、`battery_chemistry`、`rated_capacity_ah`（>0 Ah）、`current_sign_convention`（discharge_positive/charge_positive）、`voltage_unit=V`、`current_unit=A`、`temperature_unit=degC`、`soc_unit=%`、`data_origin`（来源声明，合成样例使用 synthetic_fixture）。

data 返回 `status=checked`、`summary`、`accepted`、`rejected`、`issues`、`normalized_metadata`。summary 包括 input_rows/accepted_rows/rejected_rows/error_count/warning_count/schema_ready/model_inference_performed=false。issues 每项：`csv_row`（含表头的1起始行号；0为表级问题）、`severity`、`code`、`field`、`detail`。accepted 包括规范化 UTC 时间、放电正电流、原始 pack_current_raw、source_csv_row。该检查不等于安全检测或 SOH 推理。

完整样例见 [bms.request.json](examples/bms.request.json)。

## 3. SOH、RUL、Explain

三者使用相同必填请求：
```json
{"battery_id":"B0018","cycle":66}
```
仅允许 B0005/B0006/B0007/B0018；cycle 为正整数且必须存在于打包数据中。这是公开电芯 case 选择，不是用户上传车辆编号。未知电芯/循环返回 400。

- SOH：`status`、`battery_id`、`cycle`、`predicted_soh_pct`、`measured_soh_pct`（%）、`model`、`unit`、`evidence_kind`、`validation_status`、`scope`。模型使用最初 600s 的放电特征。未返回虚构 confidence/车辆准确率。
- RUL：`predicted_rul_cycles`（参考放电循环数）、`status`、`unit`、`method`、`train_ids`、`features`、`capacity_history_rows`、`input_requirement`、`validation_status`、`operating_condition_caution`。特征单位见 [模型说明](../model/README.md)。不足 30 次容量测量、已到公开数据 EOL 阈值时返回 not_available、null 和 reason，不能补零。不是天数、公里数或实际车辆承诺寿命。
- Explain：`status=available`、`base_value_soh_pct`、`predicted_soh_pct`、`measured_soh_pct`、`additivity_error_pp`、`contributions[]`。每项有 `feature`、`feature_value`、`shap_soh_pp`（SOH 百分点）、`direction`（raises_prediction/lowers_prediction/zero）。保留 V0.3 字段名，前端可显示为 feature/contribution，但勿丢单位。基值+贡献和≈预测值，误差容差 1e-4 百分点。训练/留出身份见 split_role；SHAP 不等于真实衰减原因。

## 4. carbon

```json
{"activities":[{"activity_id":"a","stage":"use","quantity":10,"activity_unit":"kWh","factor_id":"f","data_status":"illustrative"}],"factors":[{"factor_id":"f","value":0.5,"activity_unit":"kWh","output_unit":"kgCO2e","status":"illustrative","geography":"未指定","year":"未指定","source_url":"","confidence_level":"demo_unvalidated"}],"allow_demo":true}
```

activities/factors 必填、非空对象数组；allow_demo 可选布尔，默认 false。quantity/value 为非负有限数；活动单位必须与因子一致，不自动换算。activity_id/factor_id 不可重复。因子状态接受 official/verified/illustrative（均为调用方声明）；示例活动或因子要求显式 allow_demo=true。

四个兼容 stage：manufacturing / use / maintenance_transport / end_of_life。原材料归 manufacturing，运输与维护归 maintenance_transport。当前未拆分六阶段；不可给已包含原材料的制造因子再重复计入原材料。完整范围和缺失阶段通过 summary 显示。

data：`status=calculated`、`summary`、`details[]`、`factor_provenance`。summary 包括 total_kgCO2e、by_stage_kgCO2e、included_stages、missing_stages、scope_complete、contains_illustrative_factors/activities、interpretation、allocation。details 是活动记录加 factor_value/factor_status/emissions_kgCO2e/factor_source/factor_year。因子来源、地区、年份、边界、定性 confidence level 见 `carbon/factors/factor_metadata.json`；置信等级不是概率。

## 5. decision

请求：`{"scenario":{...},"weights":{"carbon":1,"economic":1,"resource":1,"technical":1}}`。scenario 必填；weights 可选，默认 data/demo/decision/config.json 的 Demo 权重。提供权重时四项都需要，非负有限数且总和>0，服务端归一化。

| scenario 字段 | 约定 |
|---|---|
| scenario_id | 必填非空字符串 |
| data_kind | 只有 illustrative 可获得示例推荐；vehicle_unvalidated 等实际数据状态会被安全门拦截 |
| assessed_at / inspection_at | 带时区 ISO8601；缺失、过期或顺序异常均阻断方案 |
| health.soh_pct | %，0–120 或 null |
| health.rul_cycles | 非负循环数或 null |
| health.rul_unit | reference_discharge_cycles；缺失会限制依赖寿命的方案 |
| safety.* | true/false/null；禁止字符串 "false"；缺失按未知处理 |

safety 标志：critical_event、electrical_pass、thermal_pass、mechanical_pass、post_repair_pass、second_life_approved、recycler_approved、transport_approved。它们是输入证据声明，不由软件自动检测。critical_event=true 或未知时整体 hold；其他缺失/失败证据淘汰相应方案。

data 保留 V0.3 的 status/recommended_route/feasible_routes/pareto_routes/weights/routes/functional_unit/policy_status/reason/limitations，并新增 `parameter_status="Demo / Prototype Parameters"`。routes 有四项：continue_use（继续使用）、repair_then_use（检修再利用）、second_life（梯次利用）、recycle（再生回收）。每项包括 eligible、reason_codes、weighted_score（0–1，不可行则 null）、pareto_optimal、utility_components、carbon_kgco2e（kgCO2e）、npv_cny（元）、recovered_kg（kg）、technical_score（示例分数）、service_kwh/replacement_service_kwh、cashflows/resources/carbon_detail。不可行方案仍保留用于解释淘汰原因，但不参与推荐。

比较顺序：安全约束→可行方案→多指标 Pareto 集→归一化偏好权重→推荐。不是行业认证权重或正式处置意见。

## 6. assessment：前端核心接口

必填 model_case 与 scenario，结构分别同上。可选 weights、bms（同 JSON BMS 请求）、carbon（同 carbon 请求）。省略 bms/carbon 时相应 status=not_provided，**不自动填造结果**。

```json
{"model_case":{"battery_id":"B0018","cycle":66},"scenario":{"scenario_id":"DEMO","data_kind":"illustrative"}}
```
该最小请求可演示模型，但安全证据不全会 hold。正式演示请使用 [完整请求](examples/assessment.request.json)，含合成 BMS、演示碳清单、完整示例安全证据。其 [完整响应](examples/assessment.response.json) 为本次真实 HTTP 运行保存，不是手写数值。

data 一次返回以下字段：

| 字段 | 内容 |
|---|---|
| battery_id / battery_id_scope | NASA case 编号 / NASA_public_cell_case |
| scenario_id | 独立示例电池包方案编号 |
| data_quality | BMS 质量结果或 not_provided |
| soh / rul | 上述模块输出 |
| explainability | 真 TreeSHAP 输出，含 status/method |
| carbon | 活动清单的生命周期碳结果或 not_provided |
| safety | scope 与四条路径 gates（route_id/eligible/reason_codes） |
| candidate_paths | 四条完整候选方案数据、分数及淘汰原因 |
| recommendation | status、route_id（可能 null）、parameter_status、weights |
| decision_reason | 推荐或 hold 的解释列表 |
| automatic_model_to_pack_transfer | 固定 false |
| display_notice / limitations | 必须在 Demo 中呈现的证据边界 |

流程为质量检查→公开 case SOH→实测容量 RUL→SHAP→活动清单碳计算→示例方案决策→聚合。**上传 BMS、公开电芯、示例电池包三个对象并非同一真实电池**。BMS 不合格时仍可展示独立 NASA 示例，但不得把 NASA 输出贴在上传车辆上。碳生命周期清单与方案的前瞻比较边界不同，也不得重复相加。

通用结构错误/碳单位错误返回整次 400；数据缺失的业务状态保留在 200 的模块输出。没有异步任务、报告下载 URL 或上传文件 ID。
