# carbon · 碳核算与碳因子

## 职责
本模块管理生命周期边界、活动数据乘排放因子的计算、区域因子检索和结果溯源。目前演示计算仍保留在 `frontend/src/lib/carbonMath.ts`。

## 推荐文件
核算函数、边界与分配规则、因子模式定义、单位转换、核算测试、因子来源说明。可共享的数据文件统一放 `data/`，避免两处维护同一份数据。

## 不应该放
无出处的真实因子、授权不明的数据、密钥、缓存；不得将示例数值标为官方核验数据。

## 对接约定
与 `backend/` 约定活动数据及响应格式；与 `data/` 约定因子数据版本；在 `docs/` 记录核算边界、排除项和单位。每个因子至少包含名称、类别、地区、年份、数值、单位、来源和数据等级。向前端返回各阶段与合计结果，并说明实际排放、未来情景估计和避免排放的区别。


---

## V0.3 模块接入

# carbon：独立生命周期核算

`calculator.calculate(activities, factors, allow_demo=False)` 直接复用 V0.3 碳核算核心：

**C = Σ(Activity Data × Emission Factor)**

backend 只传入 pandas 表并序列化输出。核心验证包括必需字段、唯一 ID、单位匹配、非负有限数、示例参数显式许可；不自动单位换算，不计回收替代信用。

为保持原结果，继续使用四组 stage：manufacturing（原材料+制造）、use（使用）、maintenance_transport（运输+维护）、end_of_life（退役）。六阶段拆分尚未完成，不能把总制造因子与其中原材料重复计入。

`factors/carbon_factors.csv` 和 `factor_metadata.json` 保留因子来源 URL、年份、geography、单位、系统边界及定性 confidence_level。标为 official 的状态继承原包，本次未重新核验网址或适用性；没有来源的 Demo 因子明确为 demo_unvalidated。置信等级不是统计置信区间。正式计算需由团队核对年份、地区、工艺、产品边界。

示例活动见 factors/example_activities.csv。制造、运输、退役等多项是人为 Demo 参数；算术正确不等于经第三方核证产品碳足迹。生命周期示例总量不等于 NASA 电芯或上传车辆的实测碳排放，也不应与退役决策中的前瞻路径总量重复相加。
