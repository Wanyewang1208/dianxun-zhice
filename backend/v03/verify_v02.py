"""Independent exported-result checks for V0.2."""
import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from .rul_v02 import prefix_features

def verify(root):
    checks=[]
    def check(ok,name):
        if not bool(ok):raise AssertionError(name)
        checks.append(name)
    pred=pd.read_csv(root/'data/demo/results/rul_v02/predictions.csv')
    scores=pd.read_csv(root/'data/demo/results/rul_v02/metrics_by_cell.csv')
    macro=pd.read_csv(root/'data/demo/results/rul_v02/macro_metrics.csv')
    cells=pd.read_csv(root/'data/processed/cycles.csv')
    for _,s in scores.iterrows():
        g=pred[(pred.test_battery==s.battery_id)&(pred.model==s.model)]
        v=g.dropna(subset=['true_rul_cycles','predicted_rul_cycles'])
        check(len(v)==s.evaluated_prefixes,f'RUL count {s.battery_id}/{s.model}')
        if len(v):
            e=v.predicted_rul_cycles-v.true_rul_cycles
            values=[e.abs().mean(),np.sqrt((e**2).mean()),1-(e**2).sum()/((v.true_rul_cycles-v.true_rul_cycles.mean())**2).sum()]
            check(np.allclose(values,[s.MAE_cycles,s.RMSE_cycles,s.R2]),f'RUL metric recomputation {s.battery_id}/{s.model}')
    for _,m in macro.iterrows():
        mean=scores[(scores.model==m.model)&(~scores.right_censored)][['MAE_cycles','RMSE_cycles','R2']].mean()
        check(np.allclose(mean,m[['MAE_cycles','RMSE_cycles','R2']].astype(float)),f'Macro mean {m.model}')
    censor=pred[pred.test_battery=='B0007']
    check(censor.true_rul_cycles.isna().all() and censor.right_censored.all(),'Censored B0007 has no invented labels')
    for b,g in pred.groupby('test_battery'):
        check(all(b not in ids.split('|') and 'B0007' not in ids.split('|') for ids in g.train_ids),'Separated event-observed training cells '+b)
        counts=g.groupby('model').cycle.apply(list)
        check(all(x==counts.iloc[0] for x in counts),'Same evaluation prefixes across methods '+b)
        obj=joblib.load(root/f'model/rul_v02/leave_out_{b}.joblib')
        h=cells[cells.battery_id==b]
        rows=g[g.model=='random_forest_rul'].iloc[[0,len(g[g.model=='random_forest_rul'])//2,-1]]
        for _,r in rows.iterrows():
            f=prefix_features(h,r.cycle)
            val=obj['model'].predict(pd.DataFrame([f])[obj['features']])[0]
            check(np.isclose(val,r.predicted_rul_cycles),f'Saved RUL model inference {b}/{r.cycle}')
    old=pd.read_csv(root/'data/demo/results/rul/rul_predictions.csv')
    new=pred[pred.model=='v01_trend'].merge(old,left_on=['test_battery','cycle'],right_on=['battery_id','cycle'],suffixes=('_new','_old'),validate='one_to_one')
    check(len(new)==len(pred[pred.model=='v01_trend']) and np.allclose(new.predicted_rul_cycles_new,new.predicted_rul_cycles_old,equal_nan=True),'V0.1 trend reproduced without clipping or rewriting')
    for tag,accepted,rejected in [('good',12,0),('bad',7,6)]:
        summary=json.loads((root/f'data/demo/results/bms_{tag}/summary.json').read_text(encoding='utf-8'))
        check(summary['accepted_rows']==accepted and summary['rejected_rows']==rejected,'Fixture row counts '+tag)
        check(summary['synthetic_fixture_present'] and not summary['model_inference_performed'],'Fixture identity and no vehicle prediction '+tag)
    bad=pd.read_csv(root/'data/demo/results/bms_bad/issues.csv')
    check({'duplicate_timestamp','timestamp_timezone_missing','numeric_missing_or_invalid','extrema_inverted','plausibility_range'}.issubset(set(bad.code)),'All injected error types detected')
    report={'checks_passed':len(checks),'checks':checks,'scope':'V0.2 exported metrics, separation, model inference and synthetic BMS fixture outputs'}
    (root/'data/demo/results/verification_v02.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(f'{len(checks)} V0.2 checks passed')

if __name__=='__main__':verify(Path(__file__).resolve().parents[2])
