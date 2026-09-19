# V3 公开实车充电衍生数据

20辆车、29,697个充电片段、10个首600秒特征。标签是充电积分/SOC变化计算的容量代理值，不是独立实测SOH。数据处理仅使用真实公开充电观测，不合成缺失工况或失效标签。

## 文件

- `session_features.csv`：完整匿名特征/标签表；`shards/`：20个按车辆分片CSV，可直接合并；不需要Parquet依赖。
- `sample_manifest.csv`：稳定segment_id、匿名vehicle、session_index、固定split。
- `vehicle_split.csv`：逐车划分与样本数；train=001–014、validation=015–016、test=017–020。不得随机按行重新划分。
- `feature_dictionary.csv`、`schema.json`：字段/单位/计算和可用性；metadata和标签不作为输入特征。
- `data_summary.csv`：原始20CSV逐字段完整审计；`source_manifest.json`：来源、原始文件/分片哈希。
- `DATA_AVAILABILITY.md`：真实数据可支持与不能支持的结论；`LICENSE_OR_SOURCE.md`、`LICENSE.txt`：来源引用与许可快照。
- `SHA256SUMS.txt`：本目录其余所有文件的SHA-256（不包含该清单自身）。

公开衍生表移除了原始日期/时刻，只保留每车保留片段的稳定序号。ID稳定性依赖相同源文件哈希、提取器和顺序；不声称不可逆匿名化。原始CSV/RAR不在本目录或Git交付包内。

从仓库根目录重新核验并提取：`python -m research.public_battery.audit_v3 --raw-dir <archives-directory> --csv-dir <csv-directory>`。会读取仓库外原始文件并生成新的V3产物，不修改V2。`--self-test`执行质量/匿名化自检；`--verify-derived`在已完成原始提取的环境中核对私有提取/公开总表/分片/V2顺序。公开表可直接用于V3训练复现，无需原始时间。

前600秒采样均值不是时间加权均值。电压插值仅使用已在前600秒内观测到的点，600秒处无采样时使用最后一个前缀值，不访问未来点。完整片段目标值仅用于监督标签；不得作为在线已知实测容量。
