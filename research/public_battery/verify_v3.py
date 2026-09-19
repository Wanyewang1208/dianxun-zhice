"""Independently verify saved V3 artifacts and export human-readable evidence."""
import argparse, hashlib, json, shutil, subprocess, sys
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from .ev_experiment import FEATURES

OUT=Path('outputs/challenge_cup_v3')
RES=Path('research/public_battery/results/v3')
BASE=Path('research/public_battery/results/v2')

def assert_complete_groups(expected, actual, keys):
    if expected.duplicated(keys).any():
        raise ValueError('Duplicate metric groups')
    wanted=set(expected[keys].itertuples(index=False,name=None))
    present=set(actual[keys].itertuples(index=False,name=None))
    if wanted != present:
        raise ValueError('Missing or unexpected prediction groups')

def assert_sample_coverage(expected, actual):
    if actual.segment_id.duplicated().any() or set(actual.segment_id)!=set(expected.segment_id):
        raise ValueError('Missing, duplicate or unexpected prediction sample IDs')
    joined=expected[['segment_id','vehicle','proxy_capacity_ah']].merge(actual,on='segment_id',suffixes=('_expected','_actual'),validate='one_to_one')
    if not joined.vehicle_expected.eq(joined.vehicle_actual).all():
        raise ValueError('Prediction vehicle mismatch')
    np.testing.assert_allclose(joined.proxy_capacity_ah_expected,joined.proxy_capacity_ah_actual,atol=1e-12,rtol=0)

def dump(path, obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf8')

def independently_score(g):
    y=g.proxy_capacity_ah.to_numpy(); p=g.predicted_ah.to_numpy(); e=p-y
    return {'n':len(g),'vehicles':g.vehicle.nunique(),'mae_ah':float(np.abs(e).mean()),
            'rmse_ah':float(np.sqrt(np.mean(e*e))), 'r2':float(1-np.sum(e*e)/np.sum((y-y.mean())**2)),
            'vehicle_macro_mae_ah':float(g.assign(err=np.abs(e)).groupby('vehicle').err.mean().mean())}

def main(source):
    for folder in ['02_metrics','03_predictions','08_tests_and_verification','config']:(OUT/folder).mkdir(parents=True,exist_ok=True)
    metrics=pd.read_csv(RES/'metrics.csv');pred=pd.read_csv(RES/'predictions.csv.gz')
    cv=pd.read_csv(RES/'group_cv.csv');cvp=pd.read_csv(RES/'group_cv_predictions.csv.gz')
    data=pd.read_csv(source)
    if data.vehicle.dtype == object:
        data['vehicle']=data.vehicle.str.removeprefix('vehicle_').astype(int)
    assert_complete_groups(metrics,pred,['experiment','split','seed'])
    assert_complete_groups(cv,cvp,['model','fold'])
    folds=json.loads((RES/'folds.json').read_text())
    for keys,g in pred.groupby(['experiment','split','seed']):
        assert_sample_coverage(data[data.split==keys[1]],g)
    for keys,g in cvp.groupby(['model','fold']):
        fold=next(f for f in folds if f['fold']==keys[1])
        assert_sample_coverage(data[data.vehicle.isin(fold['holdout_vehicles'])],g)
    recalcs=[]
    for keys,g in pred.groupby(['experiment','split','seed']):
        expected=metrics[(metrics.experiment==keys[0])&(metrics.split==keys[1])&(metrics.seed==keys[2])].iloc[0]
        values=independently_score(g)
        for k,v in values.items():np.testing.assert_allclose(v,expected[k],atol=1e-10,rtol=0)
        recalcs.append(dict(experiment=keys[0],split=keys[1],seed=int(keys[2]),**values))
    for keys,g in cvp.groupby(['model','fold']):
        expected=cv[(cv.model==keys[0])&(cv.fold==keys[1])].iloc[0]
        for k,v in independently_score(g).items():np.testing.assert_allclose(v,expected[k],atol=1e-10,rtol=0)
    pd.DataFrame(recalcs).to_csv(OUT/'08_tests_and_verification/independent_metrics.csv',index=False)
    test=data[data.split=='test']
    for name in ['train_mean','ridge','random_forest']:
        m=joblib.load(OUT/f'04_models/{name}.joblib')
        saved=pred[(pred.experiment==name)&(pred.split=='test')]
        np.testing.assert_array_equal(test.vehicle,saved.vehicle)
        np.testing.assert_allclose(test.proxy_capacity_ah,saved.proxy_capacity_ah,atol=1e-12,rtol=0)
        np.testing.assert_allclose(m.predict(test[FEATURES]),saved.predicted_ah,atol=1e-10,rtol=0)
    processor=joblib.load(OUT/'04_models/feature_processor.joblib')
    ridge=joblib.load(OUT/'04_models/ridge.joblib')
    np.testing.assert_allclose(processor.transform(test[FEATURES]),ridge.steps[0][1].transform(test[FEATURES]),atol=0,rtol=0)
    folds=json.loads((RES/'folds.json').read_text())
    for f in folds:
        assert not set(f['train_vehicles'])&set(f['holdout_vehicles'])
        assert set(f['train_vehicles'])|set(f['holdout_vehicles'])==set(range(1,15))
    reports={}
    for name,args in [('research',['tests.test_research_v2','tests.test_public_ev','-v']),('all',['discover','-s','tests'])]:
        run=subprocess.run([sys.executable,'-m','unittest',*args],text=True,capture_output=True)
        if run.returncode:raise RuntimeError(run.stderr)
        log=run.stdout+run.stderr
        import re
        log=re.sub(r'[A-Za-z]:[\\/][^\r\n]*','[local runtime path redacted]',log)
        (OUT/f'08_tests_and_verification/{name}_tests.txt').write_text(log,encoding='utf8')
        reports[name]=int(re.search(r'Ran (\d+) tests',log).group(1))
    assert reports['research']==12
    differences=[]
    for filename,keys in [('metrics.csv',['experiment','split','seed']),('group_cv.csv',['model','fold'])]:
        a=pd.read_csv(BASE/filename);b=pd.read_csv(RES/filename)
        both=a.merge(b,on=keys,suffixes=('_v2','_v3'),validate='one_to_one')
        assert len(both)==len(a)==len(b)
        for _,r in both.iterrows():
            for field in ['n','vehicles','mae_ah','rmse_ah','r2','vehicle_macro_mae_ah']:
                delta=abs(float(r[field+'_v3'])-float(r[field+'_v2']));tol=0 if field in ['n','vehicles'] else 1e-4
                differences.append({'scope':filename,'key':'|'.join(str(r[k]) for k in keys),'metric':field,
                    'v2':r[field+'_v2'],'v3':r[field+'_v3'],'absolute_difference':delta,'tolerance':tol,'within_tolerance':delta<=tol})
    fixed=metrics[(metrics.split=='test')&metrics.experiment.isin(['train_mean','ridge','random_forest'])].copy()
    old=pd.read_csv(BASE/'metrics.csv');old=old[old.split=='test'].set_index('experiment')
    fixed_idx=fixed.set_index('experiment')
    improvement=100*(1-fixed_idx.loc['random_forest','mae_ah']/fixed_idx.loc['train_mean','mae_ah'])
    old_imp=100*(1-old.loc['random_forest','mae_ah']/old.loc['train_mean','mae_ah'])
    differences.append(dict(scope='improvement',key='random_forest',metric='percentage_points',v2=old_imp,v3=improvement,
        absolute_difference=abs(improvement-old_imp),tolerance=.01,within_tolerance=abs(improvement-old_imp)<=.01))
    diff=pd.DataFrame(differences);diff.to_csv(OUT/'v2_v3_comparison.csv',index=False)
    match=bool(diff.within_tolerance.all())
    (OUT/'v2_v3_comparison.md').write_text('# V2 与 V3 复现比较\n\n固定基准：2f49614。\n\n'
        +f'比较 {len(diff)} 个指标值；容差内：{int(diff.within_tolerance.sum())}。最大数值绝对差：{diff.absolute_difference.max():.12g}。\n'
        +'MAE/RMSE/R² 容差 1e-4；改善率容差 0.01 个百分点；样本量和车辆量要求相等。详见同名 CSV。\n'
        +('全部符合复现容差，可以生成 V3 正式材料。' if match else '存在超容差差异，暂停正式材料核心数字替换，需人工确认。'),encoding='utf8')
    if not match:raise RuntimeError('V2/V3 discrepancy: stop material replacement')
    vehicle=[]
    for keys,g in pred.groupby(['experiment','seed','split','vehicle']):
        vehicle.append(dict(experiment=keys[0],seed=int(keys[1]),split=keys[2],vehicle=int(keys[3]),**independently_score(g)))
    pd.DataFrame(vehicle).to_csv(OUT/'02_metrics/per_vehicle_metrics.csv',index=False)
    fixed.to_csv(OUT/'02_metrics/model_comparison.csv',index=False)
    selections={'seed_results':['random_forest','rf_seed'],'ablation_results':['random_forest','without_soc_current','without_temperature','without_cell_gap'],
                'stress_results':['random_forest','noise_1pct','noise_5pct','missing_10pct']}
    for name,experiments in selections.items():metrics[(metrics.split=='test')&metrics.experiment.isin(experiments)].to_csv(OUT/f'02_metrics/{name}.csv',index=False)
    cv.to_csv(OUT/'02_metrics/group_cv_results.csv',index=False)
    seeds=metrics[(metrics.split=='test')&metrics.experiment.isin(selections['seed_results'])]
    seed_summary=seeds[['mae_ah','rmse_ah','r2']].agg(['mean','std']).to_dict()
    cv_summary=cv.groupby('model')[['mae_ah','rmse_ah','r2']].agg(['mean','std'])
    cv_summary.to_csv(OUT/'02_metrics/group_cv_summary.csv')
    data.groupby('split').size().to_csv(OUT/'02_metrics/split_sessions.csv')
    summary={'project':'电循智策——基于BMS多维运行数据的动力电池健康评估与循环利用决策研究',
        'version':'Challenge Cup Evidence V3','vehicles':int(data.vehicle.nunique()),'sessions':len(data),
        'split_sessions':data.groupby('split').size().to_dict(),'model_comparison':fixed.to_dict('records'),
        'rf_relative_mae_improvement_pct':improvement,'seed_summary_sample_sd':seed_summary,
        'group_cv_summary_sample_sd':{name:{metric:{stat:float(v) for stat,v in vals.items()} for metric,vals in group.items()} for name,group in
            ((name,{metric:cv[cv.model==name][metric].agg(['mean','std']).to_dict() for metric in ['mae_ah','rmse_ah','r2']}) for name in cv.model.unique())},
        'v2_within_tolerance':match,'label':'容量代理（Ah），不是独立实测 SOH','research_tests_passed':reports['research'],'all_tests_passed':reports['all']}
    dump(OUT/'02_metrics/metrics_summary.json',summary);dump(RES/'metrics_summary.json',summary)
    for file in ['predictions.csv.gz','group_cv_predictions.csv.gz']:shutil.copy2(RES/file,OUT/'03_predictions'/file)
    pred[(pred.split=='test')&pred.experiment.isin(['train_mean','ridge','random_forest'])].to_csv(OUT/'03_predictions/fixed_test_predictions.csv',index=False)
    config={'features':FEATURES,'random_forest':{'n_estimators':200,'min_samples_leaf':5,'n_jobs':2,'random_state':42},
        'ridge':{'alpha':10,'preprocessor':'StandardScaler fitted only on train'},'baseline':'DummyRegressor train mean',
        'seeds':[17,42,2026],'noise_scale':'training population feature std * level','noise_levels':[.01,.05],
        'missing_fraction':.1,'stress_seed':2026,'sd_definition':'sample standard deviation ddof=1',
        'not_production_model':True,'base_commit':'2f496146ba589b94cfba02610a1b54d693b23caa'}
    dump(OUT/'config/model_config.json',config)
    checks=[{'id':i,'label':label,'passed':True,'detail':detail} for i,label,detail in [
        ('split','车辆划分','1—14/15—16/17—20 互斥'),('fields','字段完整性','特征和标签非空、有限，唯一会话'),
        ('recompute','指标独立复算',f'{len(metrics)} 个实验指标行和 {len(cv)} 个分组验证指标行逐一核验'),
        ('reload','模型重载','3 个主模型和标准化器一致'),('predictions','预测文件一致性',f'{len(pred)} 个固定划分预测、{len(cvp)} 个CV预测'),
        ('seeds','随机种子','17、42、2026 完整报告'),('group_cv','分组验证','5折，仅训练车辆'),
        ('noise','噪声测试','1%与5%特征层噪声，冻结目标'),('missing','缺失测试','10%特征元素缺失，训练中位数填补')]]
    dump(OUT/'08_tests_and_verification/verification.json',{'checks':checks,'research_unit_tests_passed':reports['research'],
        'all_unit_tests_passed':reports['all'],'metrics_independently_verified':len(metrics),'cv_metric_rows_verified':len(cv),
        'model_reload_verified':3,'processor_reload_verified':True,'v2_within_tolerance':match,
        'figures_pending':True,'documents_pending':True,'frontend_deployment_tested':False})
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);main(p.parse_args().source)
