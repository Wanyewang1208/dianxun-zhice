"""Independent acceptance checks against exported rows and source checksums."""
import hashlib
import json
from datetime import datetime,timezone
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from .core import FEATURES,TRAIN_IDS,TEST_IDS,early_features

def verify(root):
    checks=[]
    def check(condition,label):
        if not bool(condition): raise AssertionError(label)
        checks.append(label)
    provenance=json.loads((root/'data/raw/provenance.json').read_text(encoding='utf-8'))
    for f in provenance['files']:
        check(hashlib.sha256((root/'data/raw'/f['file']).read_bytes()).hexdigest()==f['sha256'],
              'Original source checksum: '+f['file'])
    cycles=pd.read_csv(root/'data/processed/cycles.csv')
    check(not cycles.duplicated(['battery_id','cycle']).any(),'Unique battery/cycle rows')
    check(np.allclose(cycles.soh_pct,cycles.capacity_ah/2*100),'SOH labels match measured Capacity / rated 2 Ah')
    splits=pd.read_csv(root/'data/demo/results/soh/split_assignment.csv')
    train=set(splits.loc[splits.split=='train','battery_id'])
    test=set(splits.loc[splits.split=='test','battery_id'])
    check(not train&test and train==set(TRAIN_IDS) and test==set(TEST_IDS),'No cell overlap in fixed holdout')
    check(not set(FEATURES)&{'capacity_ah','soh_pct','battery_id','discharge_duration_s','sample_count'},'No label-derived predictor columns')
    for prefix in ['holdout','lobo']:
        pred=pd.read_csv(root/f'data/demo/results/soh/{prefix}_predictions.csv')
        metrics_path='holdout_metrics.csv' if prefix=='holdout' else 'lobo_metrics_by_cell.csv'
        scores=pd.read_csv(root/'data/demo/results/soh'/metrics_path)
        for _,s in scores.iterrows():
            p=pred[(pred.split==s['split'])&(pred.model==s.model)]
            err=p.predicted_soh_pct-p.true_soh_pct
            expected=[np.abs(err).mean(),np.sqrt(np.mean(err**2)),
                      1-np.sum(err**2)/np.sum((p.true_soh_pct-p.true_soh_pct.mean())**2)]
            check(len(p)==s.n and np.allclose(expected,[s.MAE_pp,s.RMSE_pp,s.R2],rtol=1e-8,atol=1e-8),
                  f'Exported metric recomputed: {s["split"]}/{s.model}')
        joined=pred.merge(cycles[['battery_id','cycle','soh_pct']],on=['battery_id','cycle'],validate='many_to_one')
        check(len(joined)==len(pred) and np.allclose(joined.true_soh_pct,joined.soh_pct),'Prediction labels match cleaned source: '+prefix)
    held=cycles[cycles.battery_id.isin(TEST_IDS)]
    hp=pd.read_csv(root/'data/demo/results/soh/holdout_predictions.csv')
    for name in hp.model.unique():
        obj=joblib.load(root/'model'/f'{name}.joblib')
        actual=obj['model'].predict(held[obj['features']])
        saved=hp[hp.model==name].sort_values(['battery_id','cycle'])
        check(np.allclose(actual,saved.predicted_soh_pct),'Saved model reproduces predictions: '+name)
    signals=pd.read_csv(root/'data/processed/discharge_timeseries.csv.gz')
    check(not signals.duplicated(['battery_id','cycle','time_s']).any(),'Unique time-series keys')
    # Recreate early features for first/middle/last cycle of every cell from saved long table.
    for b,g in cycles.groupby('battery_id'):
        for _,row in g.iloc[[0,len(g)//2,-1]].iterrows():
            s=signals[(signals.battery_id==b)&(signals.cycle==row.cycle)]
            early=early_features({'Time':s.time_s,'Voltage_measured':s.voltage_v,
                                  'Current_measured':s.current_a,'Temperature_measured':s.temperature_c})
            check(all(np.isclose(v,row[k],atol=1e-10) for k,v in early.items()),f'Long-table feature reconstruction: {b}/{row.cycle}')
    labels=pd.read_csv(root/'data/demo/results/rul/rul_labels.csv')
    for b,g in cycles.groupby('battery_id'):
        crossed=g[g.capacity_ah<=1.4]
        eol=None if crossed.empty else int(crossed.cycle.min())
        lab=labels[labels.battery_id==b]
        if eol is None:
            check(lab.rul_cycles.isna().all() and lab.right_censored.all(),'Right censor without fabricated RUL: '+b)
        else:
            check(np.allclose(lab.rul_cycles,np.maximum(eol-lab.cycle,0)),'RUL first-passage label: '+b)
    rp=pd.read_csv(root/'data/demo/results/rul/rul_predictions.csv')
    rm=pd.read_csv(root/'data/demo/results/rul/rul_metrics.csv')
    for _,m in rm.iterrows():
        g=rp[(rp.battery_id==m.battery_id)&(rp.observed_history_rows>=30)].dropna(subset=['true_rul_cycles','predicted_rul_cycles'])
        check(len(g)==m.evaluated_prefixes,'RUL evaluated sample count: '+m.battery_id)
        if len(g):
            err=g.predicted_rul_cycles-g.true_rul_cycles
            check(np.allclose([np.abs(err).mean(),np.sqrt(np.mean(err**2))],[m.MAE_cycles,m.RMSE_cycles]),
                  'RUL metrics recalculated: '+m.battery_id)
    detail=pd.read_csv(root/'data/demo/results/carbon/carbon_detail.csv')
    summary=json.loads((root/'data/demo/results/carbon/carbon_summary.json').read_text(encoding='utf-8'))
    check(np.allclose(detail.quantity*detail.factor_value,detail.emissions_kgCO2e),'Carbon row arithmetic and units')
    check(np.isclose(detail.emissions_kgCO2e.sum(),summary['total_kgCO2e']),'Carbon total reconciliation')
    check(summary['contains_illustrative_factors'],'Demonstration factors visible in output')
    dictionary=pd.read_csv(root/'data/sample/bms/电循智策_BMS数据需求清单.csv')
    required={'timestamp','pack_voltage','pack_current','SOC','cell_voltage_max','cell_voltage_min','temperature_max',
              'temperature_min','mileage','charge_status','cell_voltages','temperature_probes','SOH_BMS',
              'insulation_resistance','fault_codes','battery_chemistry','rated_capacity_ah'}
    check(required.issubset(set(dictionary.field)),'All user-required BMS fields present')
    check(set(dictionary.priority)=={'必须','强烈建议','可选'},'BMS priority tiers present')
    check(not dictionary.field.duplicated().any() and not dictionary.isna().any().any(),'BMS dictionary complete without duplicate field keys')
    for name in ['degradation_curves','soh_true_vs_predicted','soh_parity','lobo_mae','rul_baseline','carbon_example']:
        for ext in ['png','svg']:
            check((root/'data/demo/results/figures'/f'{name}.{ext}').stat().st_size>1000,'Figure saved: '+name+'.'+ext)
    report={'verified_at_utc':datetime.now(timezone.utc).isoformat(),'checks_passed':len(checks),'checks':checks,
            'scope':'Data integrity, non-overlap, metric reconstruction, saved-model inference, carbon arithmetic, BMS field coverage, figure existence. Visual inspection separate.'}
    (root/'data/demo/results/verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(f'{len(checks)} acceptance checks passed',flush=True)

if __name__=='__main__': verify(Path(__file__).resolve().parents[2])
