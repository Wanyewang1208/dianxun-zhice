# 手动评估阶段验证记录

验证日期：2026-09-15。目标分支：feature/v03-backend-integration → dev。

- Python 3.12：`python -m unittest discover -s tests -q`，99项通过，包含既有71项及新增28项。
- `python -m backend.v03.verify_v03`，39项既有数值复核通过。
- 实际本地HTTP服务：`scripts/smoke_test.py` 与 `scripts/smoke_manual.py` 全部通过；覆盖既有BMS/SOH/RUL/真实SHAP/碳/决策，以及手填容量、Demo估值、缺失证据和大整数400响应。
- 三份请求示例通过 assessment JSON Schema 校验。响应示例由实际HTTP服务产生。
- 独立审查发现的异常温度/压差绕过、大整数500问题已修正，并增加回归测试。额外检查压差自报值和极值不一致时不能绕过复核。
- 手填假设循环寿命不再转标为公开电芯寿命单位；原决策服务包络不据此自动放行。
- frontend/、main、历史数据与已训练模型文件未修改。未运行前端构建，也未声称已完成网页联调。

运行环境沿用V0.3依赖；没有新增运行时第三方依赖。JSON Schema校验使用工作区外临时jsonschema工具，不作为API启动依赖。

仍待完成：组员页面接入、真实车辆容量/寿命验证、经验证的价值与安全系数、市场价格校准、真实梯次资质评估。Demo范围不能替代检测报告。
