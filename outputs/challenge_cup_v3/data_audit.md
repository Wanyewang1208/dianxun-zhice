# V3 原始数据核验

完整读取 20 辆匿名车辆的 16,100,728 行公开充电 CSV。原始压缩包及 CSV 的 SHA-256 均与 V2 清单一致。数据来源、MIT 许可快照、论文引用和全部哈希保存在 `research/public_battery/data/v3/source_manifest.json`。

本项目是数据集与文件处理流水线。对 Python 源码和依赖清单进行 SQL/数据库依赖只读检索，结果：Dataset and file-based processing pipeline; no SQL/database evidence in inspected scope。此结论仅覆盖所列检索范围，不宣称已建设数据库。

复用原有 `extract_sessions` 从原始 CSV 重新提取，保留 29,697 个充电片段、20 辆车、10 个首 600 秒特征。与 V2 缓存逐车辆/片段匹配，split 一致，标签与全部特征在 atol=1e-9、rtol=1e-10 内一致；最大绝对差 5.68e-14。V2 缓存未改动。划分固定为 vehicle_001–014 训练、015–016 验证、017–020 测试。

## 质量证据

逐字段缺失率、有限数值范围、无穷值与广范围异常数见 `data_summary.csv`；逐车时间与顺序统计见 `data_quality.json`。时间无效行 0，涉及重复时间的行 51994，原顺序倒退 0，相邻零间隔 36923，大于 10 秒间隔 86605。时间间隔异常可能是两次充电之间的正常停顿，不直接表示故障。

广范围仅用于数据质量筛查，不是车辆安全阈值、OEM 标定或已标注故障。筛选原样沿用 V2：无效/重复观测形成屏障；间隔大于10秒分段；片段至少1200秒、SOC增量至少20个百分点；SOC不下降且电流均为负；代理容量在(0,250] Ah。详细筛选计数见 `vehicle_sample_counts.csv`。不把原始 available_capacity 列当作独立实测完整容量。

## 可发布衍生数据

`research/public_battery/data/v3/session_features.csv` 和20份 `shards/vehicle_###.csv` 仅含匿名车辆ID、稳定片段ID、片段序号、固定划分、10特征及代理容量。`sample_manifest.csv` 可逐片段追溯到固定源文件哈希和提取器版本，但不发布原始日期/时刻。ID 在相同输入哈希和提取器下稳定；并非不可逆匿名化保证。原始 CSV/RAR 不入 Git，报告不包含本机路径。

标签是完整充电片段电流积分/SOC变化推算的容量代理值，不是独立测得的 SOH；特征仅使用前600秒。没有 RUL、EIS、失效/热失控标签、放电工况或已确认时区。字段、单位、可用性边界和split见 `schema.json`、`data_availability.json` 与 `split.json`。这些缺项不能以合成结果替代。

复现：`python -m research.public_battery.audit_v3 --raw-dir ../ev-data --csv-dir ../ev-csv`。单元自检：`python -m research.public_battery.audit_v3 --self-test`。
