# 现有XGBoost的SHAP解释

在保存的XGBoost模型上调用原生精确TreeSHAP，`pred_contribs=True`、`approx_contribs=False`，沿用训练好的树结构和路径覆盖信息。没有重新训练模型，也没有用测试集拟合解释背景。模型文件哈希随结果记录。

解释B0018的132次放电预测，所有贡献以SOH百分点表示。最后一项为模型基准值，其余12项贡献的和加基准值应等于预测值。本次浮点加和误差在0.0001个百分点以内。全局图为测试样本的平均绝对贡献；局部图预先选择第30、66、100循环，不挑选最好看的个案。

输出results/shap/shap_values.csv的shap__cycle是循环序号的贡献，cycle列是样本主键。正贡献表示相对于模型基准值拉高预测，负贡献表示拉低预测，不能理解为物理容量增减的因果分解。

在这批固定实验工况中，环境温度贡献为0；这不证明温度不影响老化。多个电压特征高度相关，贡献会受特征定义和模型分配方式影响。应写“模型主要依据电压变化特征和循环序号”，不能写“已经量化高温导致多少电池衰减”。

原始放电容量、完整放电时长未进入SOH特征。因此不能把容量变化列为本模型的SHAP特征，也不能从这些归因证明机理。模型预测仍是公开电芯验证，不是实车精度保证。

依据：[XGBoost 3.4.1官方API](https://xgboost.readthedocs.io/en/stable/python/python_api.html)说明pred_contribs输出SHAP及偏置，合计等于raw margin；本模型是平方误差回归，raw margin与SOH输出一致。[SHAP官方因果解释警示](https://shap.readthedocs.io/en/latest/example_notebooks/overviews/Be%20careful%20when%20interpreting%20predictive%20models%20in%20search%20of%20causal%20insights.html)明确区分预测解释与因果推断。
