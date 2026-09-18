# 外部数据补录与实验（2026-09-18）

此前三处链接未落实为数据文件。本次补录将“来源已登记”“已下载”“已处理”“已实验”分开记录；网页/API没有改为自动使用新模型。

## 已取得的数据

### Oxford Battery Degradation Dataset 1

作者：David Howey、Christoph Birkl，2017；DOI `10.5287/bodleian:KO2kdmYGg`。原始说明要求同时引用 Christoph R. Birkl 的 Oxford 2017 博士论文 *Diagnosis and Prognosis of Degradation in Lithium-Ion Batteries*。

- 官方完整 MAT 266,164,290 字节，原文件与 Readme 保存在 `data/raw/oxford/`；SHA256、官方地址见 `data/source_notes/oxford/provenance.json`。
- 8 颗 740mAh Kokam 软包电芯，40°C 实验室老化；519 个诊断观测点，每个包含 C1ch/C1dc/OCVch/OCVdc。不是 519 颗电池，也不是全部驱动循环的时序。
- 本次提取 C1dc 全量 1,610,378 行，压缩时序分电芯保存在 `data/raw/oxford/processed_timeseries/`；其他阶段完整保留在原 MAT，尚未展开成表。
- `data/processed/oxford/` 保存循环表、实体汇总、质量报告及清洗记录。
- 原始 Readme 把 t 描述为秒，但文件实际 t 为约 735954 的 MATLAB 日期序数、相邻间隔约 1/86400 天。本版明确使用 `(t-t0)*86400`，保留源时间，未伪称 UTC。无需用时长预测容量，也不从未来样本插值。
- C1dc 的 q 为有符号累计 mAh，容量 `(q_first-q_last)/1000` Ah；SOH=容量/0.740×100%。未填充不存在的电流测量值。
- 采用前600秒电压和温度特征；后续整段容量仅作标签，ID、全程时长、q 与容量不作为预测特征。

实验：Cell1–Cell6 训练（366 行），Cell7–Cell8 留出测试（153 行），固定超参数、不随机拆循环。平均 MAE 为 train-mean 5.3588、cycle-only 1.8311、Ridge 1.0172、Random Forest 0.7169 个百分点。每电芯指标、逐行预测与模型配置保存在 `data/demo/results/oxford/`；实验权重在 `model/experiments/oxford/`。

上述结果是 Oxford 内部留出电芯验证，不是 NASA→Oxford 泛化、不是真实整车精度。只有2颗测试电芯，不能以153行当成153个独立样本。模型尚未替换在线 NASA 模型。

RUL 复用 `model.core.estimate_rul` 做前缀容量趋势诊断，显式设置5个表征观测点、0.592Ah（额定80%）示例阈值。阈值首次跨越只知道落在两个诊断点之间，保留区间，不能把首次观测低于阈值的循环当成精确失效时刻。该实验依赖容量历史，不输出剩余天数，也不代表完成通用RUL训练。

数据库及衍生整理适用 ODbL-1.0，单项内容遵从 DbCL-1.0；保留 `data/source_notes/oxford/Readme.txt` 的完整权利说明。本项目不将原始数据改标为 MIT。

### Iontech 筛选后的公开道路车辆充电数据

Iontech 是索引，本次选择第40项，并追溯到原作者 `BatICM/battery-charging-data-of-on-road-electric-vehicles`，固定提交 `36fef4bd99f626561e2d138a40ccff3d1f3ddfc2`。20个RAR及来源说明已下载，文件校验见 `data/source_notes/road_ev/provenance.json`。

引用：Deng Z, Xu L, Liu H, Hu X, Duan Z, Xu Y. *Prognostics of battery capacity based on charging data and data-driven methods for on-road vehicles*. Applied Energy 339 (2023), 120954。

处理脚本 `scripts/prepare_road_ev.py` 保留原 CSV；将各车匿名标识为 ROAD_EV_01…20，检查时间、有限数值、SOC范围及极值顺序，隔离所有重复时间戳，按超过10秒的间隔分段。原始时间未声明时区，保留源本地时间。源字段 `available_energy (kw)` 的单位有歧义，不擅自改成 kWh 或当作健康标签。

容量提取实验保留原作者电流积分除以SOC变化的公式，增加明确筛选：至少100行、SOC跨度至少20个百分点、充电电流非正、无大于10秒间隔、无明显SOC逆转/跳变。输出是容量代理量，不是独立容量测试真值。没有确认额定容量基准，不生成整车SOH百分比，不把使用同一电流/SOC算出的代理量当作独立监督标签证明模型精度。

本数据为他人公开实车充电记录，不是团队自行采集的20辆车，也不是对团队检测产品的20辆车验证。原始仓库 LICENSE 和 README 已保存，保留论文引用；未执行下载的上游代码。

## 未取得的数据与候选

- IVST：仍为0辆已取得。官方宣称全量300辆、约72GB压缩包，样例约100MB；样例也需要申请。用户确认尚未取得授权下载链接。登记申请入口与专门条款，不伪造身份提交、不绕过申请、不把受限数据上传公共仓库。
- Iontech：完整索引保存为 `data/source_notes/iontech_catalogue.json`；原README快照本地保留并记录SHA256。其余条目不算作已经下载。下一批可考虑第7项动态驱动实验、第26项寿命基准、第32项较大电芯群体、第44/49项退役或二次寿命；应先核验原站许可、版本及容量标签。第14项NASA与已有数据去重。

## 复现与保存

使用现有 backend/requirements.txt 中的 numpy/pandas/scipy/scikit-learn/joblib；Windows 自带 tar 用于核验并解包 RAR。

```sh
python scripts/register_external_sources.py
python scripts/prepare_oxford.py
python scripts/benchmark_oxford.py
python scripts/download_road_data.py
python scripts/prepare_road_ev.py
python -m unittest discover -s tests -v
```

Oxford 官方下载在本环境的普通HTTP客户端返回403，浏览器下载正常。重新处理前从 provenance 指定的官方链接取得原MAT；不要把错误HTML保存成MAT。Iontech 原README快照应先保存到 `data/raw/source_intake/iontech.txt` 再重新生成索引。

原始大文件与完整规范化时序仅保存在本地 `data/raw/`（已被Git忽略）。GitHub只保存来源索引、处理脚本、轻量循环/会话汇总、实验结果和实验模型；这与原 NASA 的大原始文件不直接提交策略一致。

## 实际处理汇总

20辆公开车辆共16,100,728行原始数据；51,994条重复时间戳记录全部隔离，保留16,048,734行。划分87,977个充电片段，31,204个通过容量代理量筛选；其余33,113个过短、23,634个SOC跨度不足、16个SOC跳变或逆转、10个电流符号不符合条件。筛选通过不等于容量真值可信或车辆安全合格。

原有NASA 4颗、新增Oxford 8颗，共12颗公开实验室电芯；另有20辆公开道路车辆记录。团队自采真实车辆验证数量没有因此增加。

## 本次验证

- 109项现有及新增测试通过（含10项外部数据处理测试）。
- `python scripts/verify_external_data.py` 核验26个原始文件大小/SHA256、实体数量、会话行数守恒以及4个保存模型的预测复现。需要先取得本地原始文件；CI单元测试不依赖大数据下载。
- 道路数据容量代理量范围11.39–146.75Ah，中位数122.18Ah。低值仍可能受SOC误差、记录片段或工况影响，未以无来源阈值剔除，不视为测量真值。
- frontend/、backend/、carbon/及现有生产推理代码没有改动；本次只补录研究数据和实验。
