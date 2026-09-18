"""Generate editable Chinese evidence text and figures from actual V2 outputs."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def table(frame, columns, names=None):
    headers = names or columns
    rows = ['| ' + ' | '.join(headers) + ' |', '| ' + ' | '.join(['---'] * len(columns)) + ' |']
    for _, row in frame.iterrows():
        values = [f'{row[c]:.4f}' if isinstance(row[c], (float, np.floating)) else str(row[c]) for c in columns]
        rows.append('| ' + ' | '.join(values) + ' |')
    return '\n'.join(rows)


def build(result, output):
    output.mkdir(parents=True, exist_ok=True)
    metrics = pd.read_csv(result / 'metrics.csv')
    cv = pd.read_csv(result / 'group_cv.csv')
    intervals = pd.DataFrame(json.loads((result / 'cluster_intervals.json').read_text()))
    manifest = json.loads((result / 'manifest.json').read_text())
    test = metrics[metrics.split == 'test'].copy()
    base = test[test.experiment.isin(['train_mean', 'ridge', 'random_forest'])]
    rf = base[base.experiment == 'random_forest'].iloc[0]
    mean = base[base.experiment == 'train_mean'].iloc[0]
    improvement = 100 * (1 - rf.mae_ah / mean.mae_ah)
    seeds = test[test.experiment.isin(['random_forest', 'rf_seed'])]
    stress = test[test.experiment.isin(['random_forest', 'noise_1pct', 'noise_5pct', 'missing_10pct'])]
    ablation = test[test.experiment.isin(['random_forest', 'without_soc_current', 'without_temperature', 'without_cell_gap'])]
    cv_summary = cv.groupby('model').mae_ah.agg(['mean', 'min', 'max']).reset_index()
    labels = {'train_mean': '训练均值', 'ridge': 'Ridge', 'random_forest': '随机森林',
              'without_soc_current': '去 SOC / 电流', 'without_temperature': '去温度',
              'without_cell_gap': '去单体压差', 'noise_1pct': '1% 特征噪声',
              'noise_5pct': '5% 特征噪声', 'missing_10pct': '10% 特征缺失'}
    plt.rcParams.update({'font.sans-serif': ['Microsoft YaHei', 'SimHei', 'DejaVu Sans'],
                         'axes.unicode_minus': False, 'font.size': 13,
                         'axes.spines.top': False, 'axes.spines.right': False,
                         'svg.fonttype': 'path'})
    for name, frame, title in [
        ('01_model_comparison', base, '三模型对比'),
        ('02_feature_ablation', ablation, '特征消融：固定参数重新训练'),
        ('03_input_stress', stress, '特征层模拟压力测试'),
    ]:
        fig, ax = plt.subplots(figsize=(12.8, 7.2), layout='constrained')
        frame = frame.reset_index(drop=True)
        bars = ax.bar([labels[x] for x in frame.experiment], frame.mae_ah,
                      color=['#164e63'] + ['#2e8b9c'] * (len(frame) - 1), width=.58)
        ax.bar_label(bars, fmt='%.3f', padding=6)
        ax.set_ylim(0, frame.mae_ah.max() * 1.22)
        ax.set_ylabel('容量代理 MAE（Ah，越低越好）')
        ax.set_title(title + '\n公开实车充电数据 · 固定测试车 17—20', pad=22, weight='bold')
        ax.yaxis.grid(True, alpha=.18)
        ax.set_axisbelow(True)
        fig.supxlabel('推算容量代理；非实测 SOH 精度。仅 4 辆同车型测试车。', fontsize=11)
        fig.savefig(output / (name + '.png'), dpi=200)
        fig.savefig(output / (name + '.svg'))
        plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(14.4, 7.2), layout='constrained')
    s = seeds.sort_values('seed')
    bars = axes[0].bar(s.seed.astype(str), s.mae_ah, color='#164e63')
    axes[0].bar_label(bars, fmt='%.3f', padding=6)
    axes[0].set_ylim(0, s.mae_ah.max() * 1.22)
    axes[0].set_title('随机森林重复训练：固定测试车')
    axes[0].set_xlabel('随机种子')
    axes[0].set_ylabel('容量代理 MAE（Ah）')
    for model, g in cv.groupby('model'):
        axes[1].plot(g.fold, g.mae_ah, marker='o', label=labels[model])
    axes[1].set_title('训练车辆内 5 折分组验证')
    axes[1].set_xlabel('折号（按整车分组）')
    axes[1].set_ylabel('容量代理 MAE（Ah）')
    axes[1].set_xticks(range(1, 6))
    axes[1].legend()
    fig.suptitle('公开数据稳健性补充分析', weight='bold', fontsize=20)
    fig.supxlabel('左：测试车 17—20；右：仅训练车 1—14。两种划分结果不直接等价。', fontsize=11)
    fig.savefig(output / '04_seeds_group_cv.png', dpi=200)
    fig.savefig(output / '04_seeds_group_cv.svg')
    plt.close(fig)

    report = f"""# 电循智策：挑战杯研究证据补充报告

实验分支：experiment/design-data-v2。日期：2026-09-18。

## 一、结论与进展

已有公开实车数据上的模型训练、基线对比和量化结果，本轮补齐重复训练、特征消融、分组验证、输入压力测试和车辆级不确定性分析。它们是**容量代理预测的探索性研究证据**，不能替代独立实测容量、真实 SOH/RUL 或退役安全验证，也不等于已经满足某届挑战杯的全部申报条件。

| 截图中的缺口 | 本轮可核查状态 | 仍需完成 |
| --- | --- | --- |
| 模型训练尚未形成结果 | 三模型重训完成；保存主模型及重载预测一致性检查 | 独立实测容量标签校准 |
| 对比实验尚未完成 | 均值、Ridge、随机森林；三组特征消融 | 外部数据集与论文方法同条件复现 |
| 稳健性验证尚未完成 | 三随机种子、训练车 5 折分组验证、三种输入压力测试 | 跨车型、真实传感器误差、前瞻性验证 |
| 暂无可信量化结果 | 保存逐记录预测、总体/逐车指标、探索性车辆重采样区间 | 更大独立测试车队及可靠置信区间 |

## 二、数据与方法

数据来自公开的 20 辆商用车充电记录。继承的特征缓存包含 29,697 个有效会话；训练 20,851、验证 2,864、测试 5,982。整车固定划分为 1—14 / 15—16 / 17—20。输入为每段前 600 秒的 SOC、电流、电压、温度、单体压差摘要；标签为全段电流积分除以 SOC 增量得到的 Ah 容量代理。

本轮基于已有缓存重新训练，没有重新提取原始全部记录。缓存 SHA-256：
`{manifest['input_sha256']}`。

本轮是**已知原测试结果后的补充分析**；先固定 V2_PROTOCOL.md，再运行，不以测试结果调参，不宣称预注册盲测。模型参数沿用原方案：Ridge alpha=10；随机森林 200 棵树、叶节点最少 5 样本。标准化仅拟合训练数据。分组交叉验证只使用训练车。

## 三、固定测试集对比

{table(base, ['experiment', 'mae_ah', 'rmse_ah', 'r2', 'vehicle_macro_mae_ah'], ['模型', 'MAE / Ah', 'RMSE / Ah', 'R²', '车辆等权 MAE / Ah'])}

随机森林相对训练均值基线的**会话加权 MAE 降低 {improvement:.2f}%**。R² 不是准确率；该改善针对容量代理，一部分预测能力可能来自输入与标签共享电流/SOC 信息。

![三模型比较](01_model_comparison.png)

## 四、稳健性与消融

### 随机种子重复

{table(seeds, ['seed', 'mae_ah', 'rmse_ah', 'r2'], ['随机种子', 'MAE / Ah', 'RMSE / Ah', 'R²'])}

三次测试 MAE 范围 {seeds.mae_ah.min():.4f}—{seeds.mae_ah.max():.4f} Ah，只说明固定划分下对这些种子的敏感性，不能替代独立重复采样。

### 特征消融

{table(ablation, ['experiment', 'mae_ah', 'rmse_ah', 'r2'], ['实验', 'MAE / Ah', 'RMSE / Ah', 'R²'])}

分别删除 SOC/电流、温度、单体压差组后重新训练。去掉单体压差后，测试 MAE 为 {ablation.loc[ablation.experiment == 'without_cell_gap', 'mae_ah'].iloc[0]:.4f} Ah，低于完整特征模型；因此不能宣称所有特征均有增益。该现象保留为后续独立数据验证的问题，不据此改选本轮主模型。消融结果描述当前模型与样本中的依赖，不能作因果解释；电压等剩余信号也可能间接编码 SOC 或充电阶段。

![消融](02_feature_ablation.png)

### 输入压力

{table(stress, ['experiment', 'mae_ah', 'rmse_ah', 'r2'], ['实验', 'MAE / Ah', 'RMSE / Ah', 'R²'])}

噪声是独立高斯特征扰动，标准差取各特征训练标准差的 1% / 5%；缺失为随机遮蔽 10% 特征元素、使用训练中位数填补。固定模型与标签，只改变评估输入，seed=2026。这不是原始采样点丢包实验，也没有依据真实仪器规格校准噪声；部分扰动组合可能偏离物理一致性。

![压力测试](03_input_stress.png)

### 训练车内分组验证

{table(cv_summary, ['model', 'mean', 'min', 'max'], ['模型', '5 折 MAE 均值 / Ah', '最低折 / Ah', '最高折 / Ah'])}

这里均值对折等权，不是全会话加权均值。每折训练/留出车辆清单见 folds.json；参数固定，不利用这些折挑参数，也不把交叉验证得分与原测试集得分当成同一批样本的结果。

![种子与分组验证](04_seeds_group_cv.png)

## 五、车辆级不确定性

{table(intervals, ['model', 'vehicle_macro_mae_ah', 'exploratory_95pct_low', 'exploratory_95pct_high', 'paired_macro_improvement_ah'], ['模型', '车辆等权 MAE / Ah', '探索性区间下限', '上限', '相对均值基线的配对改善 / Ah'])}

每次整车重采样 4 辆、有放回，2000 次，seed=2026，取百分位 2.5% 和 97.5%。先计算逐车误差再等权平均，避免把同车连续会话当独立车辆。配对改善使用同一批车辆，详见 cluster_intervals.json。只有 4 辆测试车，区间支持度有限，不作统计显著性或跨车型性能承诺；不是单个预测的预测区间。

## 六、申报书可粘贴文字

### 作品撰写的目的和基本思路

本作品围绕新能源汽车电池运行数据的质量治理与状态评估开展研究，探索从充电片段识别、特征提取到容量代理预测及结果解释的可复现分析流程。研究采用公开实车充电数据，按车辆实体划分训练、验证和测试集，以训练均值、线性回归及随机森林进行比较，并通过特征消融、分组验证和输入压力测试考察方法的适用边界。原型系统用于展示数据检查与辅助分析流程；真实健康状态、剩余寿命及循环利用路径的有效性仍需独立实测标签和应用场景验证。

### 作品的科学性、先进性及独特之处

本作品注重车辆实体隔离、训练过程可复现和结论可追溯，避免同车数据随机拆分造成的评估偏差。当前已在 20 辆公开车辆的 29,697 个充电片段上完成三类基线比较，并补充特征消融、不同随机种子重复实验、训练车辆内分组交叉验证及特征层压力测试。固定测试集上随机森林的容量代理预测 MAE 为 {rf.mae_ah:.4f} Ah、RMSE 为 {rf.rmse_ah:.4f} Ah、R² 为 {rf.r2:.4f}；相对训练均值基线的 MAE 降低 {improvement:.2f}%。上述结果说明方法在本数据源上具有代理量预测能力，不代表真实 SOH 测量精度；尚未证明相对已有文献方法的领先性。

### 作品的实际应用价值和现实意义

本作品形成了可追溯的数据质量检查、模型比较和误差分析流程，可作为后续电池评估研究与原型开发的基础，并帮助识别数据不足时不宜输出确定性结论的场景。预期应用包括检测数据预处理、健康评估研究辅助及循环利用方案展示。现阶段尚未完成企业部署或真实退役效果验证，不能宣称已降低检测成本、事故率或碳排放；相关价值需在独立实测容量校准和场景试验中量化。

### 学术论文文摘草稿

针对实车充电数据中标签获取困难及同车样本相关性问题，本研究构建按车辆隔离的容量代理预测实验流程，使用 20 辆公开车辆的充电记录提取 29,697 个有效片段，以片段前 600 秒的多维摘要预测由全段电流积分和 SOC 变化推算的容量代理。比较训练均值、Ridge 与随机森林，并实施特征消融、随机种子重复、分组验证和输入压力测试。固定测试车辆上，随机森林 MAE 为 {rf.mae_ah:.4f} Ah，RMSE 为 {rf.rmse_ah:.4f} Ah。结果表明该流程具有本数据源内的代理预测能力，但输入与代理标签共享电学信号、独立测试车辆较少，尚需实测容量与跨车型数据进一步验证。

## 七、尚不能写成已完成的事项

- 真实 SOH/RUL 精度、故障诊断敏感度、退役决策安全性、碳减排实效。
- 外部实验室容量校准、跨车型泛化、企业合作与部署成效、论文发表或专利授权。
- 本报告不替代正式参赛通知、资格审核和完整论文。引用会话中的旧校赛条件未在本轮取得原始文件核验。

## 八、复现与证据目录

依赖与命令见上一级 V2_README.md。metrics.csv 为全部实验结果；predictions.csv.gz 为逐会话预测；per_vehicle.csv 为逐车误差；group_cv.csv 与 folds.json 为分组证据；manifest.json 为环境、输入与源码摘要。训练模型另行保存在交付包 models/，不加载来历不明的 joblib。

## 九、来源与参考

1. Deng Z, Xu L, Liu H, Hu X, Duan Z, Xu Y. Prognostics of battery capacity based on charging data and data-driven methods for on-road vehicles. Applied Energy, 2023, 339:120954. https://doi.org/10.1016/j.apenergy.2023.120954
2. [数据作者仓库](https://github.com/BatICM/battery-charging-data-of-on-road-electric-vehicles)。本项目原下载版本与摘要见上一级 README.md 及 results/ev/raw_manifest.json。
3. [scikit-learn 分组交叉验证文档](https://scikit-learn.org/stable/modules/cross_validation.html)。本轮使用 GroupKFold，实际依赖版本以 requirements-v2.lock 为准。

以上为本研究引用来源，不等同完成系统文献检索或查新。
"""
    (output / '挑战杯研究证据报告.md').write_text(report, encoding='utf-8')
    application = report.split('## 六、申报书可粘贴文字\n\n')[1].split('## 七、')[0]
    (output / '申报书填写建议.md').write_text('# 电循智策：申报书填写建议\n\n'
        '仅用于对应栏目的内容更新；不是对原申报表文件的直接修改。\n\n' + application, encoding='utf-8')
    for artifact in [*output.glob('*.svg'), *output.glob('*.md')]:
        cleaned = '\n'.join(line.rstrip() for line in artifact.read_text(encoding='utf-8').splitlines()).rstrip() + '\n'
        artifact.write_text(cleaned, encoding='utf-8')
    print('Report and four PNG/SVG figures generated:', output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--results', type=Path, default=Path('research/public_battery/results/v2'))
    parser.add_argument('--output', type=Path, default=Path('research/public_battery/report_v2'))
    args = parser.parse_args()
    build(args.results, args.output)
