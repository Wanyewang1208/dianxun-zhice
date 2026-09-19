# 电循智策——基于BMS多维运行数据的动力电池健康评估与循环利用决策研究

Challenge Cup Evidence V3

本次任务是容量代理预测与稳健性验证。基准提交为 `2f49614`，研究分支为 `experiment/challenge-cup-evidence-v3`。容量代理来自充电电流积分和 SOC 变化，不是独立实测 SOH；只有四辆固定测试车，结果不能视为跨车型能力或真实退役处置效果。

## 本轮真实运行结果

全量读取并核验原始数据，重提取 20 辆车、29,697 个片段。训练/验证/测试车辆为 1—14 / 15—16 / 17—20，对应片段 20,851 / 2,864 / 5,982。

| experiment | mae_ah | rmse_ah | r2 |
|---|---|---|---|
| train_mean | 5.1381 | 6.4347 | -0.0285 |
| ridge | 4.4449 | 5.7097 | 0.1902 |
| random_forest | 3.5796 | 4.8489 | 0.4160 |

随机森林 MAE 相对训练均值基线降低 30.33%。12 项原研究测试通过；全部后端及研究测试 121 项通过。V2/V3 的 223 个比较值均在规定容差内。

随机森林三种种子测试 MAE 均值 3.5813 Ah、样本标准差 0.0015 Ah。训练车内五折随机森林 MAE 均值 3.4938 Ah、样本标准差 0.6903 Ah。样本标准差不是置信区间。

## 数据许可与公开范围

公开数据来自 Iontech 收录的真实车辆充电数据仓库，固定版本 `904a336bc4a8de05acdec2598708fd787bbdb8e3`，来源仓库附 MIT 许可。本包保留许可原文、引用、原始文件哈希和匿名派生数据。原始约16百万行数据不重复入Git，以控制历史体积并减少时间元数据传播；通过来源仓库获取。公开特征表去除原始日期时间，以 `vehicle_001` 等匿名编号和稳定片段编号索引，未发现VIN、车牌、GPS或人员字段。不宣称不可逆匿名化。

代码沿用仓库现有授权范围；数据来源许可不自动改变项目代码许可。详见 `research/public_battery/data/v3/DATA_AVAILABILITY.md` 与 `LICENSE_OR_SOURCE.md`。

## 目录

- `research/public_battery/data/v3/`：匿名特征/代理标签、20车分片、片段清单、字段字典、划分、校验值。
- `research/public_battery/results/v3/`：固定划分与分组验证预测、全实验指标、配置来源。
- `01_data_audit/`：原始数据质量核验与重提取对比。
- `02_metrics/`、`03_predictions/`：分类指标、固定测试及CV预测。
- `04_models/`：均值基线、Ridge、随机森林、标准化器，经Git LFS保存；仅加载可信文件。
- `05_figures_png/`、`06_figures_svg/`、`07_figure_source_data/`：十张图及底表。
- `08_tests_and_verification/`：独立复算、自动测试、图表与Word验证证据。
- `09_reports/`、`10_docx/`：中文解读与两份可编辑Word材料。
- `config/`：特征与模型参数。

## 复现

先克隆本仓库并切换 `experiment/challenge-cup-evidence-v3`，以下命令在仓库根目录执行。证据ZIP包含本轮产物和研究脚本，不代替完整项目源码；运行全套测试需要仓库中的历史后端代码和V2比较文件。训练环境 Python 3.12.14；核心库版本与 V2 一致，锁定文件含图表和Word依赖。模型seed=42，重复seed=17/42/2026，扰动和簇重采样seed=2026。原有业务模型来自另一版本scikit-learn，全套测试会有旧模型版本提示；本轮新研究模型在同一锁定环境重载核验，不替换业务模型。

```sh
python -m venv .venv-v3
# Activate the environment, then:
python -m pip install -r research/public_battery/requirements-v3.lock
git lfs pull
python -m research.public_battery.audit_v3 --self-test
python -m research.public_battery.validation_v3 --source research/public_battery/data/v3/session_features.csv --output research/public_battery/results/v3 --models-dir outputs/challenge_cup_v3/04_models
python -m research.public_battery.verify_v3 --source research/public_battery/data/v3/session_features.csv
python -m research.public_battery.report_v3 --source research/public_battery/data/v3/session_features.csv --output outputs/challenge_cup_v3 --verification outputs/challenge_cup_v3/08_tests_and_verification/verification.json --figures-only
python research/public_battery/report_v3/check_figure_data.py --result research/public_battery/results/v3 --source research/public_battery/data/v3/session_features.csv --output outputs/challenge_cup_v3 --verification outputs/challenge_cup_v3/08_tests_and_verification/verification.json --record
python -m research.public_battery.report_v3 --source research/public_battery/data/v3/session_features.csv --output outputs/challenge_cup_v3 --verification outputs/challenge_cup_v3/08_tests_and_verification/verification.json
# Render and inspect every DOCX page; record documents_pending=false only after inspection.
python -m research.public_battery.package_v3
```


若需从原始文件重新审计：先按数据获取说明下载固定来源版本并用支持RAR的tar解压到仓库外，执行 `python -m research.public_battery.audit_v3 --raw-dir ../ev-data --csv-dir ../ev-csv`。原始文件只读；提取函数沿用冻结V2，新结果不覆盖V2。

图表从CSV生成；Word图题在图下、表题在表上。PNG为300dpi，SVG为矢量；图9实际为误差分布展示。所有本页数字由V3结果自动生成。

## 同步方式

只推送指定V3分支及新建的带说明标签；不改main/dev/V2，不创建PR或合并，不强制推送。模型和最终ZIP通过Git LFS上传。运行环境没有GitHub CLI，因此不创建Release；证据ZIP在分支的outputs目录以LFS提供。发布后同步报告保存在交付目录，记录远端核验时的真实提交与对象状态。

## 引用

Deng Z, Xu L, Liu H, Hu X, Duan Z, Xu Y. Prognostics of battery capacity based on charging data and data-driven methods for on-road vehicles. Applied Energy. 2023;339:120954. https://doi.org/10.1016/j.apenergy.2023.120954
