# 手动录入评估：前端对接补充

本阶段只实现后端，**没有修改 frontend、页面或依赖**。接口仍为 `POST /api/v1/assessment`，原 `model_case + scenario` NASA 演示请求继续兼容。手动表单必须显式传 `input_mode="manual"`，不要把用户车辆编号改写成 B0018。

## 最小请求：无需 BMS

```json
{
  "input_mode": "manual",
  "data_kind": "user_declared",
  "manual_input": {
    "rated_capacity_kwh": 60,
    "current_available_capacity_kwh": 49.44,
    "measured_soh": 80,
    "cycle_count": 1126,
    "fault_code_present": null,
    "thermal_event_history": null
  }
}
```

`manual_input` 使用扁平字段，对应五步表单的 state。`data_kind` 必填：真实用户填写为 `user_declared`；点击演示数据按钮时为 `demo`。`battery_id` 可选，不填写返回 null 或唯一匹配的 BMS ID；不自动生成车辆身份。rated_capacity_kwh 必填且 >0，其余字段可省略或传 null；不使用 placeholder 默认值。

统一响应外壳保持 success/code/message/data/error/request_id/schema_version/warnings。缺失可选证据返回 200 与模块 not_available/insufficient_evidence，不把字段缺失当服务器故障。无效类型、数值、单位对应字段或未知字段返回 400 / INVALID_REQUEST，message 含字段名；前端可显示“请核对该值”。

## 已接收字段与单位

| 表单步骤 | 字段 | 单位/类型 | 当前用途 |
|---|---|---|---|
| Vehicle & Battery | vehicle_brand, vehicle_model, battery_brand, region | 字符串，最多200字符或null | 回显/报告，未进入预测模型 |
| Vehicle & Battery | registration_year | 整数年份，不晚于当前UTC年份 | 回显/报告 |
| Vehicle & Battery | battery_type | LFP/NMC/Other/null | 回显，未选择化学体系模型 |
| Vehicle & Battery | rated_capacity_kwh, current_available_capacity_kwh | kWh | 计算容量比SOH；额定>0，当前≥0且≤额定105% |
| Vehicle & Battery | mileage_km, cycle_count | km / 非负整数循环 | 里程仅保留；循环数仅在明确Demo寿命假设中使用 |
| Vehicle & Battery | new_battery_reference_price | 非负元人民币 | 完整Demo证据下估值；不查市场数据库 |
| Advanced | measured_soh | %，0–120 | 专业检测值单独保留，仍是调用方声明 |
| Condition | max_cell_voltage_v, min_cell_voltage_v | V，0–10，max≥min | 压差算术与展示，非安全阈值判定 |
| Condition | cell_voltage_delta_mv | mV，0–10000 | 空值时用(max-min)×1000；有矛盾时保留并提示 |
| Condition | current_temperature_c, historical_max_temperature_c | °C，-60–150 | 回显，未做经验证的温度风险分类 |
| Condition | internal_resistance_mohm | 非负mΩ | 保留；缺少电池结构和基准，不自动量化一致性 |
| Condition | fault_code_present, thermal_event_history | true/false/null | true 阻断普通车用估价；false 不是专业安全放行 |
| Usage | fast_charge_ratio | %，0–100 | 唯一共享字段；Step2/3不要维护两个冲突副本 |
| Usage | average_daily_mileage_km, annual_mileage_km | 非负km/日、km/年 | 保留，不自动相互推导 |
| Usage | primary_charging_method | home_ac/public_ac/dc_fast/null | 统一字段名；前端“主要充电方式”映射到此 |
| Usage | usual_charge_upper_soc, usual_discharge_lower_soc | %，0–100，upper≥lower | 校验与保留 |
| Usage | average_environment_temperature_c | °C，-60–150 | 保留，不自动套用寿命折损系数 |
| Advanced | pack_voltage, pack_current | V(0–2000), A(-10000–10000) | 保留/可由已校验CSV覆盖显示 |
| Advanced | charge_throughput_kwh, discharge_throughput_kwh | 非负kWh | 保留；不将能量直接当容量或寿命 |

所有数字必须有限，拒绝 NaN/Infinity、数字字符串及代替数字的布尔值。所有手填字段保存在响应 `input_snapshot`，空值保持 null；不会存入数据库。

## SOH、压差、RUL 与解释

- `soh.calculated_soh = 当前可用能量 / 初始额定能量 × 100`。60与49.44得到82.4%。必须采用相同可用能量边界、温度和测量条件；算术值不等于认证检测值。
- `soh.measured_soh` 原样保留；`difference_pp=calculated-measured`。不覆盖任一结果，也不自动用专业声明替代计算值进入估价。
- `soh.predicted_soh_pct=null` 明确该分支没有调用训练SOH模型。前端手动模式使用 calculated_soh，旧NASA模式仍用 predicted_soh_pct。
- `effective_condition.cell_voltage_delta_mv` 给出选定来源的压差；原值仍在 input_snapshot。前端 live preview 可用同一纯算术公式，最终以API结果为准。
- 真实用户的 `rul.status=not_available`：没有从车辆品牌、里程与循环数得到可信整车寿命的模型。不要显示成0循环或自动使用NASA样例。
- `explainability.status=not_available`：容量比是算术，不伪造SHAP。formula可展示为“How is this calculated?”。原NASA分支真实TreeSHAP不受影响。

## 可选 BMS 优先级

顶层 `bms` 使用原 JSON CSV格式（telemetry_csv、metadata_csv、可选max_gap_s），不需要新增上传接口。无BMS不阻止手动评估。

只有原V0.3检查的 schema_ready=true 且 battery_id 匹配（未指定时接受唯一ID），才采用该电池最新接受记录：

| CSV字段 | manual有效字段 |
|---|---|
| cell_voltage_max/min | max/min_cell_voltage_v |
| temperature_max | current_temperature_c（最近快照最高探针温度，明确此含义） |
| pack_voltage/current | pack_voltage/current |

优先使用BMS电压时重新计算压差。不会用最近快照温度冒充历史最高温度，不从元数据Ah推算kWh，不使用未校验的CSV内阻/累计吞吐字段。字段来源见 field_sources；CSV有质量错误、ID歧义或不匹配时保留手填值并在 notes 提示。

`data_quality.bms.detected_columns` 是原遥测列；accepted_row_fraction 是接受行比例，**不是字段完整率或模型可信度**。文件名由前端state保留，不上传服务器。数据质量合格不等于安全合格。

## 剩余价值：完整演示与真实缺项

权重在 `model/valuation_config.py`：Health35%、Life30%、Safety20%、Consistency15%，标记 Prototype Weighting。价格公式在 `model/residual_value.py`：

`Index = 0.35H + 0.30L + 0.20S + 0.15C`

`V = P_new × H/100 × L/100 × S/100 × C/100`

Health使用容量比SOH并限制在0–100；不会篡改soh中的原始结果。

只有 `data_kind=demo` 可以发送顶层 `prototype_assumptions`：

```json
{"reference_cycle_life":2500,"safety_factor":0.9,"consistency_factor":0.91}
```

这些是**明确传入的假设，不是后台默认或行业验证参数**。Demo RUL=max(0,reference_cycle_life-cycle_count)，Life=100×Demo RUL/reference_cycle_life；Safety/Consistency=对应假设×100。当前未根据压差、温差、内阻训练或标定一致性系数。UI必须将假设与Demo标签一起展示；真实模式禁止传这些假设。

证据完整时，没有新电池价格也能返回0–100指数；填写价格后返回 estimated_value_range_cny。只有已匹配、通过核心质量检查的BMS使用±8%，否则±12%；上限不超过输入新电池价。这是原型敏感性范围，不是统计置信区间或市场鉴价。

缺少Life/Safety/Consistency等分项时：index=null，estimated_value_range_cny=null；missing_components列明缺项，index_bounds给出未知分项取0–100的**数学边界**，不能作为单一“剩余价值分数”展示。比如只有82.4%容量SOH时，边界为28.84–93.84，并不表示价值已评定。这样处理优先满足“不填假数据”，因此第一阶段不强行给每个真实用户一个完整分数。

报告出现热事件、故障码或Demo Safety=0时，普通车用估价被阻断。若提交decision_scenario且继续使用门槛未通过，同样不输出普通车用估价。

## 去向与碳结果

真实用户默认 hold_for_evidence_or_professional_review，不自动放行任何路径，也不把热事件直接转成“可安全运输回收”。current_use_value 与 second_life_potential 分开；梯次潜力未知时 level=null，不编造High/Medium/Low。

Demo 可显式传 `decision_scenario`（原scenario格式，data_kind必须illustrative）和可选weights。复用现有安全门槛与四路径多目标评价，使用手动计算SOH及显式Demo RUL；scenario中的同名health被这些本轮计算值替代。所有检查标志须由请求显式提供；手填热事件/故障或未知安全状态优先阻断，不能被scenario反向覆盖。梯次路径符合示例门槛时仅返回prototype_scenario/candidate，不声称真实梯次资质。

可选顶层carbon沿用活动量×因子清单。只填region、mileage不会猜制造排放、电耗、因子年份或生命周期总量。缺清单返回not_provided。

## 前端要做的对接（本PR不实施）

1. Step Form 收集上述字段，空输入转换null，不填默认假值；Step2/3快充共用一个字段。
2. 点击评估只调用一次assessment；加载动画仅代表展示流程，不能称7个AI模型。
3. 显示input_snapshot、effective_condition和field_sources；按模块status分别显示数值、缺失证据或Demo假设。
4. 使用Demo数据按钮可以加载 [manual_demo.request.json](examples/manual_demo.request.json)；其2500循环、0.9/0.91系数属于额外明确假设，不是用户给定品牌型号的真实参数。
5. [manual.request.json](examples/manual.request.json) 为真实用户模式的82.4%容量演示输入，无虚构寿命、价值或碳数值。
6. 将 JSON 响应字段映射到摘要和报告。前端页面/布局/构建测试由前端组员完成；本PR没有运行npm、没有新增页面或数据库。

请求schema：`docs/schemas/manual.request.schema.json`。统一assessment schema增加oneOf兼容两种模式。既有单模块 /soh、/rul、/explain 仍仅支持NASA case，手动录入统一使用 /assessment。

## 原型安全复核与单位边界

有效条件（优先通过核心检查的匹配BMS）温度低于0或高于60°C、历史最高温度高于60°C或压差大于200mV，进入专业复核并阻断示例估价。这些是保守的Demo复核触发值，不是电池化学体系对应的认证安全限值；未触发不等于安全。

手填Demo寿命单位始终为 assumed_equivalent_cycles，不能改标为原模型 reference_discharge_cycles。因此可选旧决策场景的继续使用/梯次服务包络检查不会自动放行，需后续验证容量及工况对应关系。原NASA模式不受影响。

后端启动后运行 `python scripts/smoke_manual.py --base-url http://127.0.0.1:8013` 检查真实HTTP响应。
