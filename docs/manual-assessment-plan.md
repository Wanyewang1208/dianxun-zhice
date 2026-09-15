# 手动录入评估：后端阶段范围

沿用 feature/v03-backend-integration，已同步 dev。禁止修改 frontend。

1. 在 /api/v1/assessment 增加显式 input_mode=manual 分支，旧 NASA model_case/scenario 请求保持兼容。
2. 接受分步表单的扁平 manual_input，校验单位、范围、空值与矛盾字段，保留用户声明和数据来源。
3. 在 model/manual_metrics.py 计算容量比 SOH，保留 measured_soh；不把车辆信息送入 NASA 模型，不伪造 SHAP/RUL。
4. 可选 BMS 沿用 V0.3 校验；只有质量通过且电池 ID 唯一匹配时使用最新接受记录的已校验字段；保留被覆盖手填值。
5. model/residual_value.py 按 35/30/20/15 权重计算原型指数；缺失分项返回可计算边界而非假值。只有显式 Demo 假设齐全且安全无阻断时输出价格区间。
6. carbon 继续接收明确活动/因子清单，不从地区或里程猜生命周期总碳。四路径决策复用原模块，只在显式 Demo 证据下运行；真实输入不能自动放行。
7. 增加无 BMS、空值、容量比、非法字段、压差、来源优先级、安全阻断、估值公式、缺失数据和旧接口兼容测试；补 schema、字段映射、请求响应与 smoke。
8. 在当前分支提交、推送并新建 PR 到 dev；不直接合并，不改 main。

交付边界：表单字段已由后端接收，不代表每个字段都进入已验证预测模型。缺失寿命、安全或一致性证据时，真实用户不能获得完整估值指数/人民币区间；响应列明 missing_components。Demo 假设需在请求中显式提供，禁止服务端静默默认。
