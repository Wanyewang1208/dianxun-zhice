# model · SOH / RUL 模型

## 职责
后续集中管理容量健康评估、剩余寿命预测、训练、推理及性能验证。目前前端演示函数仍保留在 `frontend/src/lib/batteryMath.ts`，本次接入 V0.3 公开电芯模型；前端演示函数保持原样。

## 推荐文件
数据预处理代码、训练/推理脚本、可解释基线、评估测试、环境依赖清单和模型卡。模型卡说明输入输出、单位、阈值、适用范围、训练数据版本与评估方法。

## 不应该放
未经脱敏的原始 BMS、虚拟环境、缓存、未说明来源的模型权重、伪造的准确率。大数据与权重需另行约定存储或 Git LFS，不直接提交大型二进制。

## 对接约定
数据由 `data/` 提供版本与字段说明；推理入口由 `backend/` 调用；接口写入 `docs/`。输出 SOH、RUL、预测参考线、适用场景、置信区间及模型版本。严格区分车用寿命与梯次寿命，避免把不同 EOL 口径混用。


---

## V0.3 模块接入

手动表单扩展：manual_metrics.py 提供容量比SOH和显式Demo寿命算术；residual_value.py 提供透明的原型指数/估价，权重在valuation_config.py。没有增加整车训练模型；缺少寿命/安全/一致性证据时输出null和缺项说明。详见docs/MANUAL_ASSESSMENT.md。

# model：模型与推理

无 Web API。`inference.py` 复用 `explain_soh.py`、`rul_v02.py`，backend service 调用这些函数。已有训练/实验辅助函数为复现保留，启动 API 不重新训练。

- `xgboost.joblib`：V0.1 SOH pipeline，训练 B0005/B0006/B0007，B0018 固定留出。其他三个 case 属训练电芯，不能将其样例预测视为外部验证。
- `rul_v02/leave_out_B*.joblib`：V0.2 每个留出电芯对应的随机森林。不是通用整车部署模型。输入通过 prefix_features 从截至当前循环的至少 30 次实测容量得到。
- `explain_soh.py`：XGBoost 原生 exact TreeSHAP；不是虚构解释、不是因果识别。原 SHAP 全局 CSV 和图在 data/demo/results/shap、figures（图仅完整包）。
- 完整包还保留 linear_regression/random_forest/cycle_only_linear/train_mean 基线权重；轻量包只保留推理所需 XGBoost 和四个 RUL 权重。

SOH 特征：cycle（循环数）；voltage_60s_v/120s_v/300s_v/600s_v、voltage_mean_v（V）；voltage_slope_v_per_s（V/s）；current_mean_a/current_std_a（A）；temperature_mean_c/temperature_rise_c/ambient_temperature_c（摄氏度，rise 为温差）。来自实验最初 600 秒，不从任意车辆 BMS 自动推导。

RUL 特征：cycle（循环数）、current_capacity_ah/initial_capacity_ah/drop_from_initial_ah/local_std_ah/local_mean_ah（Ah）、local_slope_ah_per_cycle（Ah/循环）。EOL=1.4Ah 仅是该公开 2Ah 电芯数据约定，不是整车退役阈值。当前接口从打包公开数据读取容量历史，不接受任意车辆容量替代。

输出 SOH 单位 %，SHAP 单位百分点，RUL 单位 reference_discharge_cycles。无校准置信区间。模型依赖与原成果一致，见 backend/requirements.txt；仅加载本包可信 joblib，接口不接受上传模型。
