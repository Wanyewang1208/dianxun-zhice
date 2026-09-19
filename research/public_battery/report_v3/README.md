# V3 正式图表与可编辑报告

正式项目名称：电循智策——基于BMS多维运行数据的动力电池健康评估与循环利用决策研究。

生成器为 `research/public_battery/report_v3.py`。输入为本轮 V3 的 `metrics.csv`、`predictions.csv.gz`、`group_cv.csv`、`per_vehicle.csv`，以及已校验的 `session_features.csv` 与质量控制 `verification.json`。不会修改 V2 产物；模型指标不在代码内硬编码。

从仓库根目录执行：

```sh
python -m research.public_battery.report_v3 --result research/public_battery/results/v3 --source research/public_battery/data/v3/session_features.csv --output <交付根目录> --verification <交付根目录>/08_tests_and_verification/verification.json
```

加入 `--figures-only` 可先生成图表与逐图解释；正式 DOCX 要求十项质量记录均为通过。每图生成 PNG（1920×1080，300 dpi）、SVG、源数据 CSV。统计量与样本标准差从原始结果计算；散点及误差分布保留全部对应测试预测，不抽样挑选。

`verification.json` 使用 `checks` 数组，每项包含 `id`、`passed`、`detail`。所需项目为 `split`、`fields`、`recompute`、`reload`、`predictions`、`figures`、`seeds`、`group_cv`、`noise`、`missing`。缺少记录不会被推定为通过。

DOCX 完成后必须导出 PDF，逐页渲染并检查排版。渲染产物仅用于质量复核，不替代 DOCX。Word 图题位于图下，表题位于表上。源数据是推算容量代理，不能解释为实测 SOH 准确率或安全认证。
