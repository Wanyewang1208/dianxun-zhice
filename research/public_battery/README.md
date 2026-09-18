# 公开实车数据验证记录（2026-09-18）

实验分支新增：[V2 训练复现、稳健性与挑战杯申报证据](V2_README.md)。下文保留原实验记录；新结果与环境单独保存。

本目录保存真实公开数据的获取、质量检查和独立车辆容量代理训练记录。**容量代理来自电流积分与 SOC 变化，不是实测容量标签；本次不构成真实 SOH、RUL、故障预警或退役决策有效性验证。** 研究模型未替换 Demo 的在线模型。

## 三个来源的实际状态

| 来源 | 本次实际进展 | 限制 |
|---|---|---|
| [IVST 长安官方页面](http://ivstskl.changan.com.cn/?p=2697) | 核实数据介绍和申请入口 | [样例申请](https://ivstskl.changan.com.cn/?p=2799)需要申请人姓名、联系方式、单位和用途；未提交申请，未获得原始文件，未训练 |
| [Iontech](https://github.com/shiyunliu-battery/Iontech) | 从其目录找到并下载全部 20 辆实车充电数据，完成审计、字段适配和代理容量训练 | Iontech 是索引，不是这批数据的原创发布方；标签是推算值 |
| [Oxford ORA](https://ora.ox.ac.uk/objects/uuid:03ba4b01-cfed-46d3-9b1a-7d4a7bdf6fac) | 官方页面及文件链接已核实，访问记录见 `oxford_access.json` | 文件请求返回 403；正常浏览器点击没有取得文件，并出现 reCAPTCHA 保护标识；未完成验证或绕过保护。没有 MAT，未训练 |

Oxford 为 8 个实验室电芯、740 mAh，与实车电池包数据分开。页面列 ODC-ODbL 1.0。IVST 页面列 CC BY-NC-SA 4.0，科研用途和具体交付条件仍须按申请确认。

## 实车来源与引用

- Iontech 索引版本：`f997d29b25fc457313c1dcb17b74029c6ebea13c`。
- 实际下载仓库：[shiyunliu-battery/battery-charging-data-of-on-road-electric-vehicles](https://github.com/shiyunliu-battery/battery-charging-data-of-on-road-electric-vehicles)，版本 `904a336bc4a8de05acdec2598708fd787bbdb8e3`；`#1.rar` 至 `#20.rar` 全部取得。
- 原作者维护的[仓库](https://github.com/BatICM/battery-charging-data-of-on-road-electric-vehicles)补充说明：BAIC EU500、CATL NCM、145 Ah、90 串、32 个温度传感器。查阅快照保存为 `EV_PRIMARY_README.md`。
- 论文：Deng Z, Xu L, Liu H, Hu X, Duan Z, Xu Y. *Prognostics of battery capacity based on charging data and data-driven methods for on-road vehicles*. Applied Energy. 2023;339:120954. https://doi.org/10.1016/j.apenergy.2023.120954
- 下载仓库附 MIT 许可，原文保留于 `EV_SOURCE_LICENSE.txt`。原始压缩包/CSV 保存在 Git 仓库外；此目录提交派生特征、预测和记录，保留来源声明。
- 每辆车压缩包与解压文件的 SHA-256、大小见 `results/ev/raw_manifest.json`。

## 方法与事先固定的划分

1. 原始时间按 `YYYYMMDDHHMMSS` 解析；原始时区未知。研究只用同一会话相对时间。重复时间、无效核心数值、SOC 越界及最大值小于最小值被剔除；在原始顺序先设置无效行屏障，然后排序，避免跨无效观测积分。
2. 时间间隔大于 10 秒或不递增时切段。仅保留时长至少 1200 秒、SOC 增量至少 20 个百分点、SOC 单调且电流全为负的充电片段。
3. 容量代理 `-∫I dt / 3600 / (ΔSOC/100)`，保留 `(0,250] Ah`。250 Ah 是本研究宽松异常筛选界限，不是厂商安全阈值。各过滤步骤计数见 `audit.csv`。不将原始 `available_capacity` 当健康标签。
4. 输入只取前 600 秒：起始 SOC、电压及 60/300/600 秒电压、平均电流/温度、温升、单体压差均值和最大值。插值限制在已观测前缀；不足整 600 秒的最后采样点以端点值延伸。不使用全程 SOC 增量、容量、全程时长、可用能量、车辆 ID 作为模型输入。
5. 固定按整车隔离：1—14 训练，15—16 验证，17—20 测试；不按同车行随机拆分。固定训练均值基线、标准化 Ridge(alpha=10)、随机森林(200 棵树、min_samples_leaf=5、seed=42)。标准化仅拟合训练集；不按测试结果调参，完整报告三者。

即便输入只用前缀，电流/SOC 仍与代理标签的生成共享物理和数学信息；指标仅反映与该推算方法的一致程度。连续会话相关，同车型同数据源且只有 4 辆测试车，不能推广为其他车型/体系的准确率。没有故障确认、实测容量或退役结局，未训练对应模块。

## Demo 实际数据检查

`demo_compatibility.json` 保存调用当前后端 `backend.v03.bms_validate.validate` 的结果。使用 EV1 前 100 行映射核心字段及官方额定参数：

- 原始无时区时间：100 行全部拒绝，原因 `timestamp_timezone_missing`，并提示缺少里程。
- **仅用于验证适配器的假设 UTC+08:00**：100 行通过核心字段检查，仍有缺少里程警告。此处没有证实来源时区，不代表可直接上线导入。
- 文件是充电专用数据，因此适配为 charging；电流负值代表充电。不提供完整单体/温度数组，不做这些字段的验证。本次只测试该真实样例的后端核心检查，不等同全数据网页上传或线上部署验证。

## 复现

在项目根目录、安装 Python 3.12 与 `results/ev/environment.json` 对应版本的 NumPy/Pandas/SciPy/scikit-learn 后运行；系统需要可解 RAR 的 `tar`（Windows bsdtar 可用）：

```sh
git clone https://github.com/shiyunliu-battery/battery-charging-data-of-on-road-electric-vehicles ../ev-data
git -C ../ev-data checkout 904a336bc4a8de05acdec2598708fd787bbdb8e3
python -m research.public_battery.ev_experiment --raw-repo ../ev-data --extracted ../ev-csv --output research/public_battery/results/ev
python -m unittest discover -s tests
```

脚本安全校验每个压缩包只有预期 `#n.csv`。特征、划分及代理标签见 `session_features.csv`；逐条预测见 `predictions.csv`；总体与逐车误差见 `metrics.json`、`per_vehicle_metrics.csv`。Ridge 参数、训练均值和森林重要性保存于 `learned_parameters.json`；森林完整对象不入 Git，可按固定脚本重训。

## 集成和验证

先前 Demo 修复 PR [#4](https://github.com/Wanyewang1208/dianxun-zhice/pull/4) 已合入 dev，合并提交 `a25a3ec1eb6980bf49ae0a0546df83ccac774c58`。保留双语切换、手动评估与现有模型边界。

本轮复核发现并修复“无效时间戳排序后不能阻断原始片段”的研究脚本问题，补充回归测试。Demo 前端构建、9 项 BMS/站点测试、双语测试、模型算术测试、13 项接口映射测试及 2 种手动评估变体均通过。最终后端及研究测试计数、训练结果见 `RESULTS.md`。
