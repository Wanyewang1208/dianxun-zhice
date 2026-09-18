"""Fixed, cell-held-out SOH baselines and causal capacity-history RUL diagnostic experiment."""
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import joblib
import numpy as np
import pandas as pd
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error
from model.core import assert_disjoint, estimate_rul
from scripts.prepare_oxford import FEATURES, threshold_interval

def main():
    frame=pd.read_csv(ROOT/'data/processed/oxford/cycles.csv');frame=frame[frame.feature_eligible]
    train_ids=[f'Cell{i}' for i in range(1,7)];test_ids=['Cell7','Cell8'];assert_disjoint(train_ids,test_ids)
    train=frame[frame.battery_id.isin(train_ids)];test=frame[frame.battery_id.isin(test_ids)]
    out=ROOT/'data/demo/results/oxford';out.mkdir(parents=True,exist_ok=True)
    weights=ROOT/'model/experiments/oxford';weights.mkdir(parents=True,exist_ok=True)
    models={'train_mean':(DummyRegressor(),['cycle']),'cycle_only_linear':(LinearRegression(),['cycle']),'ridge':(make_pipeline(StandardScaler(),Ridge(alpha=1.)),FEATURES),'random_forest':(RandomForestRegressor(n_estimators=200,min_samples_leaf=3,max_features=1.,random_state=42,n_jobs=2),FEATURES)}
    metrics=[];predictions=[]
    for name,(model,features) in models.items():
        model.fit(train[features],train.soh_pct);p=model.predict(test[features]);part=test[['battery_id','cycle','soh_pct']].copy();part['predicted_soh_pct']=p;part['model']=name;predictions.append(part)
        for cell,g in part.groupby('battery_id'):
            metrics.append({'model':name,'battery_id':cell,'n':len(g),'mae_pp':mean_absolute_error(g.soh_pct,g.predicted_soh_pct),'rmse_pp':float(np.sqrt(mean_squared_error(g.soh_pct,g.predicted_soh_pct)))})
        joblib.dump({'model':model,'features':features,'train_ids':train_ids,'test_ids':test_ids,'dataset':'oxford_degradation_1','not_for_vehicle_api':True},weights/(name+'.joblib'))
    pd.concat(predictions).to_csv(out/'holdout_predictions.csv',index=False)
    metric=pd.DataFrame(metrics);metric.to_csv(out/'metrics_by_cell.csv',index=False)
    macro=metric.groupby('model')[['mae_pp','rmse_pp']].mean();macro.to_csv(out/'macro_metrics.csv')
    rul=[]
    for cell,g in frame.groupby('battery_id'):
        g=g.sort_values('cycle');low,high,censored=threshold_interval(g.cycle,g.capacity_ah)
        for i in range(len(g)):
            prefix=g.iloc[:i+1];now=int(prefix.cycle.iloc[-1]);pred=estimate_rul(prefix.cycle,prefix.capacity_ah,window=5,threshold=.592)
            prediction=pred['predicted_rul_cycles'];error=None;in_interval=None
            if not censored and low is not None and now<low and prediction is not None:
                lower=low-now;upper=high-now;in_interval=lower<prediction<=upper;error=max(lower-prediction,prediction-upper,0.)
            rul.append({'battery_id':cell,'cycle':now,**pred,'right_censored':censored,'observed_crossing_lower_exclusive':low,'observed_crossing_upper_inclusive':high,'absolute_distance_to_interval_cycles':error,'prediction_in_interval':in_interval})
    pd.DataFrame(rul).to_csv(out/'rul_prefix_diagnostics.csv',index=False)
    report={'dataset':'Oxford Battery Degradation Dataset 1','train_ids':train_ids,'test_ids':test_ids,'train_records':len(train),'test_records':len(test),'features':FEATURES,'seed':42,'tuning':'none; fixed baselines; no test-set selection loop','macro_soh_metrics':macro.reset_index().to_dict('records'),'rul':'Reuse model.core.estimate_rul with five observed diagnostic records, threshold .592Ah; evaluate distance to observed crossing interval, not exact life ground truth','scope':'Within-Oxford held-out-cell baseline; neither NASA-to-Oxford transfer nor real-vehicle validation; full-discharge capacity is label only','api_changed':False}
    (out/'experiment.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report,indent=2))

if __name__=='__main__':main()
