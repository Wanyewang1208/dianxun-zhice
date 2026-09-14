"""Exploratory RUL comparison; training cells never overlap the evaluation cell."""
import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from .core import eol_cycle,estimate_rul,assert_disjoint,EOL_CAPACITY_AH

FEATURES=['cycle','current_capacity_ah','initial_capacity_ah','drop_from_initial_ah',
          'local_slope_ah_per_cycle','local_std_ah','local_mean_ah']
MODELS=['v01_trend','training_rate','blended_rate','random_forest_rul']

def prefix_features(history,current_cycle,window=30):
    h=history[history.cycle<=current_cycle].sort_values('cycle')
    if len(h)<window: raise ValueError('Need at least 30 prior/current measurements')
    if h.cycle.duplicated().any() or not np.isfinite(h[['cycle','capacity_ah']]).all().all():
        raise ValueError('Invalid or duplicate history observations')
    w=h.tail(window)
    return {'cycle':int(h.cycle.iloc[-1]),'current_capacity_ah':float(h.capacity_ah.iloc[-1]),
            'initial_capacity_ah':float(h.capacity_ah.iloc[0]),
            'drop_from_initial_ah':float(h.capacity_ah.iloc[0]-h.capacity_ah.iloc[-1]),
            'local_slope_ah_per_cycle':float(np.polyfit(w.cycle,w.capacity_ah,1)[0]),
            'local_std_ah':float(w.capacity_ah.std(ddof=0)),
            'local_mean_ah':float(w.capacity_ah.mean())}

def fit_priors(training):
    rates=[]; ids=[]
    for b,g in training.groupby('battery_id'):
        end=eol_cycle(g.cycle,g.capacity_ah)
        if end is None: continue
        h=g[g.cycle<=end].sort_values('cycle')
        rate=-float(np.polyfit(h.cycle,h.capacity_ah,1)[0])
        if rate>0: rates.append(rate);ids.append(b)
    if not rates: raise ValueError('No training cell with observed EOL and declining capacity')
    return {'rate_ah_per_cycle':float(np.median(rates)),'training_ids':ids,
            'per_cell_rate':dict(zip(ids,rates)),'source':'Observed training cells only, whole pre-EOL capacity regression'}

def predict_prior(features,prior,method):
    rate=prior['rate_ah_per_cycle']
    if method=='blended_rate':
        # Prespecified regularization. Floor comes from training cells, not test lifetimes.
        rate=max(.25*rate,.5*rate+.5*max(0.,-features['local_slope_ah_per_cycle']))
    elif method!='training_rate': raise ValueError('Unknown prior method')
    return max(0.,features['current_capacity_ah']-EOL_CAPACITY_AH)/rate

def labelled_rows(frame):
    rows=[]
    for b,g in frame.groupby('battery_id'):
        end=eol_cycle(g.cycle,g.capacity_ah)
        if end is None: continue
        for c in g.loc[(g.cycle>=30)&(g.cycle<end),'cycle']:
            rows.append({'battery_id':b,'true_rul_cycles':end-int(c),**prefix_features(g,int(c))})
    return pd.DataFrame(rows)

def run_fold(frame,train_ids,test_id,save_dir=None):
    assert_disjoint(train_ids,[test_id])
    training=frame[frame.battery_id.isin(train_ids)]
    test=frame[frame.battery_id==test_id].sort_values('cycle')
    if test.empty: raise ValueError('No test cell')
    prior=fit_priors(training)
    train=labelled_rows(training)
    if train.empty: raise ValueError('No eligible labelled training prefixes')
    model=RandomForestRegressor(n_estimators=300,max_depth=4,min_samples_leaf=8,random_state=42,n_jobs=2)
    # Each training cell has equal total sample weight, irrespective of observed lifespan.
    weights=1/train.groupby('battery_id').battery_id.transform('size')
    weights=weights/weights.mean()
    model.fit(train[FEATURES],train.true_rul_cycles,sample_weight=weights)
    if save_dir is not None:
        save_dir.mkdir(parents=True,exist_ok=True)
        joblib.dump({'model':model,'features':FEATURES,'prior':prior,'train_ids':train_ids,'test_id':test_id},
                    save_dir/f'leave_out_{test_id}.joblib')
    end=eol_cycle(test.cycle,test.capacity_ah); rows=[]
    for c in test.cycle:
        if c<30 or (end is not None and c>=end): continue
        f=prefix_features(test,int(c))
        old=estimate_rul(test.loc[test.cycle<=c,'cycle'],test.loc[test.cycle<=c,'capacity_ah'])
        values={'v01_trend':old['predicted_rul_cycles'],
                'training_rate':predict_prior(f,prior,'training_rate'),
                'blended_rate':predict_prior(f,prior,'blended_rate'),
                'random_forest_rul':float(model.predict(pd.DataFrame([f])[FEATURES])[0])}
        for name,value in values.items():
            rows.append({'test_battery':test_id,'train_ids':'|'.join(train_ids),'cycle':int(c),
                         'model':name,'true_rul_cycles':None if end is None else end-int(c),
                         'predicted_rul_cycles':value,'right_censored':end is None,
                         'prior_rate_ah_per_cycle':prior['rate_ah_per_cycle']})
    return pd.DataFrame(rows),prior

def summarize(predictions):
    rows=[]
    for (b,m),g in predictions.groupby(['test_battery','model']):
        v=g.dropna(subset=['true_rul_cycles','predicted_rul_cycles'])
        errors=v.predicted_rul_cycles-v.true_rul_cycles
        denom=((v.true_rul_cycles-v.true_rul_cycles.mean())**2).sum()
        rows.append({'battery_id':b,'model':m,'eligible_prefixes':len(g),'evaluated_prefixes':len(v),
                     'prediction_coverage':float(g.predicted_rul_cycles.notna().mean()),
                     'MAE_cycles':float(errors.abs().mean()) if len(v) else None,
                     'RMSE_cycles':float(np.sqrt((errors**2).mean())) if len(v) else None,
                     'R2':float(1-(errors**2).sum()/denom) if denom>0 else None,
                     'right_censored':bool(g.right_censored.iloc[0])})
    return pd.DataFrame(rows)

def run(root):
    data=pd.read_csv(root/'data/processed/cycles.csv')
    out=root/'data/demo/results/rul_v02';out.mkdir(parents=True,exist_ok=True)
    observed=[b for b,g in data.groupby('battery_id') if eol_cycle(g.cycle,g.capacity_ah) is not None]
    parts=[];priors={}
    for test in sorted(data.battery_id.unique()):
        ids=[b for b in observed if b!=test]
        p,prior=run_fold(data,ids,test,root/'model/rul_v02')
        parts.append(p);priors[test]=prior
    pred=pd.concat(parts,ignore_index=True); scores=summarize(pred)
    pred.to_csv(out/'predictions.csv',index=False,encoding='utf-8-sig')
    scores.to_csv(out/'metrics_by_cell.csv',index=False,encoding='utf-8-sig')
    macro=scores[~scores.right_censored].groupby('model')[['MAE_cycles','RMSE_cycles','R2']].mean().reset_index()
    macro.to_csv(out/'macro_metrics.csv',index=False,encoding='utf-8-sig')
    labelled_rows(data).to_csv(out/'causal_training_features.csv',index=False,encoding='utf-8-sig')
    (out/'protocol.json').write_text(json.dumps({'version':'0.2','status':'exploratory_same_dataset_reuse',
        'reason':'All four cells were already examined in V0.1; not a new independent external test',
        'EOL_capacity_ah':1.4,'EOL_source':'data/raw/README.txt','window':30,
        'observed_EOl_cells':observed,'features':FEATURES,'priors':priors,
        'parameters':'Fixed before first V0.2 scores; RF 300 trees, depth4, leaf8, seed42; blend 50/50',
        'censoring':'B0007 kept for forecasts only; excluded from supervised training and MAE/RMSE/R2',
        'common_evaluation':'Cycles>=30 and strictly before first observed EOL; identical prefixes across models',
        'input_assumption':'Measured capacity at current and previous cycles; not BMS-only or end-to-end SOH/RUL',
        'uncertainty':'No calibrated intervals; only three event-observed cells; repeated prefixes correlated',
        'model_artifacts':'One training-only model per held-out cell; not a production deployment model'},indent=2),encoding='utf-8')
    print(macro.to_string(index=False),flush=True)

if __name__=='__main__':run(Path(__file__).resolve().parents[1])
