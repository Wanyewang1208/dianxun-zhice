"""Build the human-readable index and checksummed V4 evidence archive."""
import hashlib
import importlib.metadata
import json
import shutil
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path('outputs/challenge_cup_v4')


def digest(p):
    h = hashlib.sha256()
    with p.open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def deliverable(p):
    rel = p.relative_to(ROOT)
    return p.is_file() and not any(x.startswith('qa_') for x in rel.parts) and p.suffix != '.log' and p.name != '升级前材料审计.md'


def main():
    verification = json.loads((ROOT/'06_verification/independent_verification.json').read_text(encoding='utf-8'))
    assert verification['passed'] and verification['models_reloaded'] == 15
    for name, sha in verification['verified_inputs_sha256'].items():
        assert digest(ROOT/name) == sha, name
    methods = {'train_mean':'训练均值', 'train_median':'训练中位数', 'ridge':'Ridge', 'random_forest':'随机森林', 'hist_gradient_boosting':'直方图梯度提升树'}
    m = pd.read_csv(ROOT/'02_metrics/all_metrics.csv')
    m = m[(m.group=='primary') & (m.split=='test') & (m.window_s==600)]
    fair = pd.read_csv(ROOT/'02_metrics/matched_formula_comparison.csv')
    fair = fair[(fair.split=='test') & (fair.threshold==1)]
    summary = ['# 电循智策 V4 研究升级证据包', '',
        '本轮完成短时充电信息与容量代理预测的回顾性补充研究。新增同窗口公式参照、训练中位数和梯度提升树对照，并分析观测长度、特征依赖、工况、车辆数量与筛选覆盖率。这里是研究进展和答辩材料，没有据此宣称团队已撰写或发表论文。', '',
        '## 先读什么', '',
        '- 组员先读 `07_materials/电循智策_V4组员理解与答辩手册.pdf`，按“一辆车—短时记录—容量参考值”理解项目。',
        '- 答辩使用 `07_materials/电循智策_挑战杯研究升级版_V4.pptx`，配套PDF与逐页讲解。正文和表格可编辑；数据图附SVG和CSV。',
        '- 完整解释见 `07_materials/电循智策_V4研究进展与实验结果.pdf`，同时提供Word。',
        '- 单张图见 `05_figures/png`；矢量图见 `05_figures/svg`；数字见 `05_figures/source_csv`。', '',
        '## 最重要的新发现', '',
        '在各窗口SOC增量至少1个百分点的相同片段上，方法优劣随窗口变化：', '',
        '| 观察时长 | 比较片段数 | 条件覆盖率 | 随机森林MAE Ah | 同窗口公式MAE Ah |',
        '|---|---:|---:|---:|---:|']
    for w in [120,300,600]:
        rf = fair[(fair.window_s==w)&(fair.experiment=='random_forest')].iloc[0]
        formula = fair[(fair.window_s==w)&(fair.experiment=='prefix_formula')].iloc[0]
        summary.append(f'| {w//60}分钟 | {int(rf.n):,} | {rf.coverage:.2%} | {rf.mae_ah:.4f} | {formula.mae_ah:.4f} |')
    summary += ['', '2分钟和5分钟时随机森林误差较低，10分钟时直接公式误差较低。公式使用同一时间范围内的电流积分与终点SOC；与模型是相同观测时长、不同特征表达。没有宣称机器学习全面优于公式，也没有把事后观察到的交叉用于部署自动切换规则。', '',
        '## 10分钟五方法完整队列对照', '',
        '以下均为4辆历史固定测试车、5,982个片段，误差对应容量代理，不是真实SOH。公式对照详见上表。', '',
        '| 方法 | MAE Ah | RMSE Ah | R² |', '|---|---:|---:|---:|']
    for _, r in m.iterrows():
        summary.append(f'| {methods[r.experiment]} | {r.mae_ah:.4f} | {r.rmse_ah:.4f} | {r.r2:.4f} |')
    summary += ['', '新增梯度提升树没有超过随机森林；质量筛选只带来很小的误差变化，均已保留并说明。', '',
        '## 数据和检验范围', '',
        '- 重读20个原始CSV，共16,100,728行。每个窗口都是原来的29,697个有效片段；89,091行是三种窗口展开，不能当成新增独立样本。',
        '- 车辆1—14训练，15—16验证，17—20历史固定测试。窗口标签/编号/划分不变；10分钟输入与V3一致。',
        '- 15个主模型完整重训；五折仅在训练车辆内；三种子消融与车辆数量实验、模拟噪声/缺失均完成。',
        f'- 独立复算{verification["independently_recomputed_metric_rows"]:,}行误差指标，15模型完整验证/测试重载30次一致。135项Python自动化测试通过，其中14项为本轮新增。',
        '- 自动化测试发现旧生产模型跨scikit-learn版本警告；未据此验证旧模型或网页兼容性。本轮新模型在记录的1.7.2环境训练和重载。',
        '- V3三种主方法9项MAE/RMSE/R²在1e-4容差内复现。V2/V3、main/dev以及原文件保留，本轮不合并、不创建PR。', '',
        '## 必须保留的限制', '',
        '这是已看过历史测试结果后的补充分析，不是新盲测。20辆车来自同一公开来源和车型；完整片段筛选依赖后续记录，所以覆盖率只适用于这批离线合格片段。标签与输入共享电流/SOC信号，缺少配对的独立容量检测，不能解释为真实SOH、跨车型通用或实际退役安全决策。特征扰动不等同真实传感器故障试验。网页、NASA电芯研究、碳和路径模块保留为前期基础与应用原型。', '',
        '## 来源与复现', '',
        '- 原作者数据及公式：[BatICM道路车辆充电数据](https://github.com/BatICM/battery-charging-data-of-on-road-electric-vehicles)。',
        '- 固定下载版本：[shiyunliu-battery数据仓库](https://github.com/shiyunliu-battery/battery-charging-data-of-on-road-electric-vehicles/tree/904a336bc4a8de05acdec2598708fd787bbdb8e3)。许可MIT，保留来源版本、许可和SHA256。',
        '- 数据对应论文：[Deng等，Applied Energy 339，120954](https://doi.org/10.1016/j.apenergy.2023.120954)。引用原作者工作不代表本团队已发表论文。',
        '- 可执行步骤见 `reproducibility.md`；代码摘录与依赖见 `08_reproducibility`；完整仓库分支 `experiment/challenge-cup-evidence-v4`。',
        '- 包内未附1.2GB原始CSV、V3全部旧产物、遗留生产模型或私有材料，只保存本轮结果及来源核验；原始数据可按来源下载。',
        '- `SHA256SUMS.json`记录包内交付文件校验值（不包含自身）。']
    (ROOT/'README.md').write_text('\n'.join(summary)+'\n',encoding='utf-8')
    (ROOT/'reproducibility.md').write_text('''# V4复现说明

请在另一个检出目录和独立环境中复现，避免覆盖已审阅证据。Python 3.12.14；数值环境依赖见08_reproducibility/requirements-v4.lock。随机森林200树、叶节点最少5样本；其余参数与固定实验设计见V4_PROTOCOL.md。V4训练代码和协议SHA保存在run_manifest.json。

在仓库根目录按顺序运行：

```text
python -m research.public_battery.download_ev_source --destination ../public-ev-fixed-source
```

将经过校验的20个RAR解压到独立的../public-ev-csv目录，文件应为#1.csv至#20.csv。脚本不会更改原始CSV；重新读取时核对V3原始校验值。

```text
python -m research.public_battery.windows_v4 --csv-dir ../public-ev-csv
python -m research.public_battery.upgrade_v4
python -m research.public_battery.quality_refresh_v4
python -m research.public_battery.verify_upgrade_v4
python -m unittest discover -s tests -p "test_*.py"
python -m research.public_battery.report_upgrade_v4
python -m research.public_battery.defense_v4
```

阈值刷新步骤只处理SOC增量浮点边界，候选阈值和模型不变。1e-9比较容差避免名义上的2或10个百分点被二进制表示误排除。刷新前CSV仍存于06_verification；报告和图表读取刷新后的结果。不能省略此步骤。

仅从图对应CSV重绘：

```text
python -m research.public_battery.report_upgrade_v4 --regenerate-from-csv --figures-only
```

数字和预测应在所列容差内一致；压缩文件的字节哈希可能随工具、压缩头时间等变化，不能把压缩字节不等自动当成数值不等。

PPT生成器需要Codex演示文稿运行库和Windows PowerPoint导出，普通Python环境不具备这个额外条件。Word用python-docx生成，交付PDF由Microsoft Word导出，所有页面均检查。已提供可直接使用的PPTX、DOCX和PDF。运行库不存在时可直接用CSV/SVG在常规办公软件重排，不影响独立复算。

08_reproducibility/repo_files是相关研究源码快照，保留仓库相对目录；完整执行优先使用GitHub V4分支的全仓库。它不是一个自带Python解释器或全部原始数据的安装包。源数据许可见同目录EV_SOURCE_LICENSE.txt。

没有重训或覆盖网页生产模型；旧模型跨版本兼容警告已单列，网页联调不在本轮研究优先验收范围。
''',encoding='utf-8')
    repro = ROOT/'08_reproducibility'; repro.mkdir(exist_ok=True)
    packages = sorted(f'{d.metadata["Name"]}=={d.version}' for d in importlib.metadata.distributions() if d.metadata.get('Name'))
    (repro/'requirements-v4.lock').write_text('\n'.join(packages)+'\n',encoding='utf-8')
    sources = list(Path('research/public_battery').glob('*v4.py')) + [Path('research/public_battery')/name for name in ['V4_PROTOCOL.md','ev_experiment.py','validation_v3.py','download_ev_source.py','EV_SOURCE_LICENSE.txt']]
    sources += [Path('tests/test_windows_v4.py'),Path('tests/test_research_v4.py')]
    for source in sources:
        target = repro/'repo_files'/source
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,target)
    shutil.copyfile('research/public_battery/data/v3/source_manifest.json',repro/'source_manifest.json')
    shutil.copyfile('research/public_battery/EV_SOURCE_LICENSE.txt',repro/'EV_SOURCE_LICENSE.txt')
    items = sorted(p for p in ROOT.rglob('*') if deliverable(p) and p.name!='SHA256SUMS.json')
    checks = {p.relative_to(ROOT).as_posix():{'sha256':digest(p),'bytes':p.stat().st_size} for p in items}
    (ROOT/'SHA256SUMS.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
    archive = Path('outputs/电循智策_挑战杯研究升级证据包_V4.zip')
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(ROOT.rglob('*')):
            if deliverable(p): z.write(p,Path('challenge_cup_v4')/p.relative_to(ROOT))
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for name, entry in checks.items():
            assert hashlib.sha256(z.read('challenge_cup_v4/'+name)).hexdigest()==entry['sha256'],name
    print(json.dumps({'archive':str(archive),'files':len(checks),'bytes':archive.stat().st_size,'sha256':digest(archive)},ensure_ascii=False))


if __name__=='__main__': main()
