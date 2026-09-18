# V2：挑战杯研究证据补充

本分支仅作研究与原型实验。**预测对象是充电积分/SOC 推算容量代理，不是独立实测 SOH。**

入口：[研究报告](report_v2/挑战杯研究证据报告.md) / [申报书填写建议](report_v2/申报书填写建议.md) / [固定实验方案](V2_PROTOCOL.md)。

## 复现

在仓库根目录使用 Python 3.12；创建专用环境，避免改变系统 Python：

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate；Linux/macOS: source .venv/bin/activate
python -m pip install -r research/public_battery/requirements-v2.lock
python -m unittest tests.test_research_v2 tests.test_public_ev -v
python -m research.public_battery.validation_v2 --models-dir ../v2-models
python -m research.public_battery.report_v2
```

训练输入使用已提交的 session_features.csv，无须重新下载原始文件；原始提取复现方式见 README.md。本轮在不同于原结果的锁定依赖环境重训，新的环境与源码摘要单独保存。模型是研究工件，不由业务后端自动加载；仅加载自己训练或可信交付的 joblib 文件。

## 产物

- results/v2/：11 种实验配置的验证/测试指标、逐记录预测、逐车误差、5 折车辆划分、车辆重采样区间、来源摘要。
- report_v2/：四张可用于展示的 PNG/SVG、可编辑 Markdown 报告和申报文字。
- --models-dir 指定的仓库外目录：均值、Ridge、随机森林主模型；SHA-256 记录在 manifest.json。

这是回顾性补充实验。固定参数后完整报告，不能当作事先预注册的独立盲测。不替换 Demo 在线模型，不创建合并到 dev 的 PR。

## 本轮验收

12 项研究测试通过（6 项新增、6 项原有）；全部 22 行指标由 97,306 条预测记录独立重算一致；3 个模型重载预测一致；5 折车辆隔离检查通过；20 份原压缩包摘要与原记录一致。四张 PNG 已逐图检查，SVG 同源导出。独立代码与报告复核未发现必须修复项。

完整证据见 results/v2/verification.json。只运行与本次研究变更相关的测试，没有宣称重新执行整个业务系统测试或网页部署。

原环境与新锁定环境比较见 results/v2/baseline_reproduction.csv：均值和 Ridge 在浮点容差内一致，随机森林测试 MAE 从 3.5786735 变为 3.5795806 Ah（差 0.0009071 Ah），不是逐位完全复现；应引用本轮报告的 3.5796 Ah，并附本轮环境。原结果未覆盖。
