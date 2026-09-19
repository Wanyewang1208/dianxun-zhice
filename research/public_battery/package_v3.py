"""Build reproducible V3 documentation, manifests and the LFS evidence archive."""
import hashlib,json,zipfile,subprocess,re,shutil
from pathlib import Path
import pandas as pd

ROOT=Path.cwd();OUT=ROOT/'outputs/challenge_cup_v3'

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def table(frame):
    return '| '+' | '.join(frame.columns)+' |\n|'+'|'.join(['---']*len(frame.columns))+'|\n'+ '\n'.join('| '+' | '.join(f'{v:.4f}' if isinstance(v,float) else str(v) for v in row)+' |' for row in frame.itertuples(index=False,name=None))

def docs():
    s=json.loads((OUT/'02_metrics/metrics_summary.json').read_text(encoding='utf8'))
    results=pd.read_csv('research/public_battery/results/v3/metrics.csv')
    old=pd.read_csv('research/public_battery/results/v2/metrics.csv')
    compare=pd.read_csv(OUT/'v2_v3_comparison.csv')
    assert compare.within_tolerance.all()
    models=pd.DataFrame(s['model_comparison'])[['experiment','mae_ah','rmse_ah','r2']]
    command='''```sh
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
'''
    text=f'''# {s['project']}

Challenge Cup Evidence V3

本次任务是容量代理预测与稳健性验证。基准提交为 `2f49614`，研究分支为 `experiment/challenge-cup-evidence-v3`。容量代理来自充电电流积分和 SOC 变化，不是独立实测 SOH；只有四辆固定测试车，结果不能视为跨车型能力或真实退役处置效果。

## 本轮真实运行结果

全量读取并核验原始数据，重提取 {s['vehicles']} 辆车、{s['sessions']:,} 个片段。训练/验证/测试车辆为 1—14 / 15—16 / 17—20，对应片段 {s['split_sessions']['train']:,} / {s['split_sessions']['validation']:,} / {s['split_sessions']['test']:,}。

{table(models)}

随机森林 MAE 相对训练均值基线降低 {s['rf_relative_mae_improvement_pct']:.2f}%。12 项原研究测试通过；全部后端及研究测试 {s['all_tests_passed']} 项通过。V2/V3 的 {len(compare)} 个比较值均在规定容差内。

随机森林三种种子测试 MAE 均值 {s['seed_summary_sample_sd']['mae_ah']['mean']:.4f} Ah、样本标准差 {s['seed_summary_sample_sd']['mae_ah']['std']:.4f} Ah。训练车内五折随机森林 MAE 均值 {s['group_cv_summary_sample_sd']['random_forest']['mae_ah']['mean']:.4f} Ah、样本标准差 {s['group_cv_summary_sample_sd']['random_forest']['mae_ah']['std']:.4f} Ah。样本标准差不是置信区间。

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

{command}

若需从原始文件重新审计：先按数据获取说明下载固定来源版本并用支持RAR的tar解压到仓库外，执行 `python -m research.public_battery.audit_v3 --raw-dir ../ev-data --csv-dir ../ev-csv`。原始文件只读；提取函数沿用冻结V2，新结果不覆盖V2。

图表从CSV生成；Word图题在图下、表题在表上。PNG为300dpi，SVG为矢量；图9实际为误差分布展示。所有本页数字由V3结果自动生成。

## 同步方式

只推送指定V3分支及新建的带说明标签；不改main/dev/V2，不创建PR或合并，不强制推送。模型和最终ZIP通过Git LFS上传。运行环境没有GitHub CLI，因此不创建Release；证据ZIP在分支的outputs目录以LFS提供。发布后同步报告保存在交付目录，记录远端核验时的真实提交与对象状态。

## 引用

Deng Z, Xu L, Liu H, Hu X, Duan Z, Xu Y. Prognostics of battery capacity based on charging data and data-driven methods for on-road vehicles. Applied Energy. 2023;339:120954. https://doi.org/10.1016/j.apenergy.2023.120954
'''
    (OUT/'README.md').write_text(text,encoding='utf8')
    (OUT/'reproducibility.md').write_text('# V3 复现命令\n\n'+command,encoding='utf8')
    (OUT/'metrics_summary.md').write_text('# 容量代理实验结果\n\n'+table(results[results.split=='test'][['experiment','seed','mae_ah','rmse_ah','r2']]),encoding='utf8')
    changes=old.merge(results,on=['experiment','split','seed'],suffixes=('_old','_new'))
    changes=changes[changes.split=='test'][['experiment','mae_ah_old','mae_ah_new']]
    (OUT/'申报材料数字更新清单.md').write_text('# 申报材料数字更新清单\n\n'+table(changes)+'\n\n全部差异在容差内；四位小数展示值不需要实质更新。V3新增审计、追溯、图表与验证说明。两份最终复核版Word由新结果重新生成，旧V2文件不修改。历史网页展示和NASA电芯结果属于其他证据域，不用本次Ah指标覆盖。',encoding='utf8')
    frontend=json.loads((OUT/'08_tests_and_verification/frontend_validation.json').read_text(encoding='utf8'))
    assert frontend['passed'] and all(c['exit_code']==0 for c in frontend['commands'])
    dump={'research_tests':s['research_tests_passed'],'v3_evidence_regression_tests':4,'backend_and_research_tests':s['all_tests_passed'],
        'frontend':{'passed':frontend['passed'],'evidence':'08_tests_and_verification/frontend_validation.json'},
        'legacy_backend_model_version_warnings':'Existing 1.9.1 serialized business estimators loaded in 1.7.2 research test environment; tests passed, production models untouched.'}
    (OUT/'08_tests_and_verification/test_summary.json').write_text(json.dumps(dump,ensure_ascii=False,indent=2),encoding='utf8')

def package():
    docs()
    verification=json.loads((OUT/'08_tests_and_verification/verification.json').read_text(encoding='utf8'))
    assert len(verification['checks'])>=10 and all(c['passed'] for c in verification['checks'])
    assert not verification.get('figures_pending',True)
    assert not verification.get('documents_pending',True)
    files=[p for p in OUT.rglob('*') if p.is_file() and p.name not in ['MANIFEST.csv','SHA256SUMS.txt']]
    files += [p for p in (ROOT/'research/public_battery/data/v3').rglob('*') if p.is_file()]
    files += [p for p in (ROOT/'research/public_battery/results/v3').rglob('*') if p.is_file()]
    files += [ROOT/'research/public_battery'/name for name in ['audit_v3.py','validation_v3.py','verify_v3.py','report_v3.py','package_v3.py','publication_check_v3.py','download_ev_source.py','V3_PROTOCOL.md','requirements-v3.lock','ev_experiment.py']]
    files += [p for p in (ROOT/'research/public_battery/report_v3').glob('*.py')]
    files += [p for p in (ROOT/'research/public_battery/report_v3').glob('*.ps1')]
    rows=[{'path':str(p.relative_to(ROOT)).replace('\\','/'),'bytes':p.stat().st_size,'sha256':digest(p)} for p in sorted(set(files))]
    pd.DataFrame(rows).to_csv(OUT/'MANIFEST.csv',index=False)
    (OUT/'SHA256SUMS.txt').write_text('\n'.join(r['sha256']+'  '+r['path'] for r in rows)+'\n',encoding='utf8')
    archive=ROOT/'outputs/电循智策_挑战杯最终复核证据包_V3.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for r in rows:z.write(ROOT/r['path'],r['path'])
        for name in ['MANIFEST.csv','SHA256SUMS.txt']:z.write(OUT/name,'outputs/challenge_cup_v3/'+name)
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    # Separate checksum to avoid self-referential archive hashes.
    (ROOT/'outputs/证据包_V3_SHA256.txt').write_text(digest(archive)+'  '+archive.name+'\n',encoding='utf8')
    print(json.dumps({'files':len(rows),'uncompressed_bytes':sum(r['bytes'] for r in rows),'zip_bytes':archive.stat().st_size,'zip_sha256':digest(archive)},indent=2))

if __name__=='__main__':package()
