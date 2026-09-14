"""Fixed-cell holdout + leave-one-cell-out SOH baselines. No test-driven tuning."""
import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error,mean_squared_error,r2_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor
from .core import FEATURES,TRAIN_IDS,TEST_IDS,CELL_IDS,assert_disjoint

def metrics(y,p):
    return {'MAE_pp':float(mean_absolute_error(y,p)),
            'RMSE_pp':float(np.sqrt(mean_squared_error(y,p))),
            'R2':float(r2_score(y,p)) if len(y)>1 else None}

def models():
    # Fixed before evaluation. Do not change these after looking at held-out scores.
    return {
        'train_mean':(FEATURES,make_pipeline(SimpleImputer(strategy='median'),DummyRegressor(strategy='mean'))),
        'cycle_only_linear':(['cycle'],make_pipeline(LinearRegression())),
        'linear_regression':(FEATURES,make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),LinearRegression())),
        'random_forest':(FEATURES,make_pipeline(SimpleImputer(strategy='median'),RandomForestRegressor(
            n_estimators=300,max_depth=6,min_samples_leaf=5,random_state=42,n_jobs=2))),
        'xgboost':(FEATURES,make_pipeline(SimpleImputer(strategy='median'),XGBRegressor(
            n_estimators=250,max_depth=3,learning_rate=.03,subsample=.9,colsample_bytree=.9,
            reg_lambda=5,objective='reg:squarederror',random_state=42,n_jobs=2,tree_method='hist')))}

def evaluate_split(frame,train_ids,test_ids,split_name,save_dir=None):
    assert_disjoint(train_ids,test_ids)
    tr=frame[frame.battery_id.isin(train_ids)].copy()
    te=frame[frame.battery_id.isin(test_ids)].copy()
    assert_disjoint(tr.battery_id.unique().tolist(),te.battery_id.unique().tolist())
    if tr.empty or te.empty: raise ValueError('Empty train/test split')
    pred_rows=[]; scores=[]; train_scores=[]
    for name,(features,model) in models().items():
        model.fit(tr[features],tr.soh_pct)
        pred=model.predict(te[features])
        table=te[['battery_id','cycle','soh_pct']].copy().rename(columns={'soh_pct':'true_soh_pct'})
        table['predicted_soh_pct']=pred; table['model']=name; table['split']=split_name
        pred_rows.append(table)
        scores.append({'split':split_name,'test_battery':','.join(test_ids),'model':name,'n':len(te),
                       **metrics(te.soh_pct,pred)})
        train_scores.append({'split':split_name,'model':name,'n':len(tr),**metrics(tr.soh_pct,model.predict(tr[features]))})
        if save_dir is not None:
            joblib.dump({'model':model,'features':features,'target':'capacity_ah / 2 * 100',
                         'train_ids':train_ids,'test_ids':test_ids,'early_window_s':600},save_dir/f'{name}.joblib')
    return pd.DataFrame(scores),pd.concat(pred_rows,ignore_index=True),pd.DataFrame(train_scores)

def train(root):
    out=root/'data/demo/results/soh'; out.mkdir(parents=True,exist_ok=True)
    model_dir=root/'model'; model_dir.mkdir(exist_ok=True)
    frame=pd.read_csv(root/'data/processed/cycles.csv')
    frame=frame[frame.feature_eligible.astype(str).str.lower().eq('true')].copy()
    scores,pred,training=evaluate_split(frame,TRAIN_IDS,TEST_IDS,'fixed_holdout',model_dir)
    scores.to_csv(out/'holdout_metrics.csv',index=False,encoding='utf-8-sig')
    pred.to_csv(out/'holdout_predictions.csv',index=False,encoding='utf-8-sig')
    training.to_csv(out/'training_metrics_diagnostic_only.csv',index=False,encoding='utf-8-sig')
    fold_scores=[]; fold_pred=[]
    for test_id in CELL_IDS:
        s,p,_=evaluate_split(frame,[b for b in CELL_IDS if b!=test_id],[test_id],'LOBO_'+test_id)
        fold_scores.append(s); fold_pred.append(p)
    lobo=pd.concat(fold_scores,ignore_index=True)
    lobo.to_csv(out/'lobo_metrics_by_cell.csv',index=False,encoding='utf-8-sig')
    pd.concat(fold_pred,ignore_index=True).to_csv(out/'lobo_predictions.csv',index=False,encoding='utf-8-sig')
    macro=lobo.groupby('model')[['MAE_pp','RMSE_pp','R2']].agg(['mean','std'])
    macro.columns=['_'.join(c) for c in macro.columns]
    macro.reset_index().to_csv(out/'lobo_macro_summary.csv',index=False,encoding='utf-8-sig')
    assignment=frame[['battery_id','cycle']].copy()
    assignment['split']=np.where(assignment.battery_id.isin(TRAIN_IDS),'train','test')
    assignment.to_csv(out/'split_assignment.csv',index=False,encoding='utf-8-sig')
    config={'train_ids':TRAIN_IDS,'test_ids':TEST_IDS,'train_rows':int(frame.battery_id.isin(TRAIN_IDS).sum()),
            'test_rows':int(frame.battery_id.isin(TEST_IDS).sum()),'seed':42,'features':FEATURES,
            'hyperparameter_selection':'Fixed in source before first model evaluation; no hyperparameter search or early stopping',
            'target_definition':'SOH_pct = capacity_ah / 2.0 * 100; MAE/RMSE in percentage points',
            'excluded_predictors':['capacity_ah','soh_pct','battery_id','discharge_duration_s','sample_count','full_discharge_Ah','future_cycles'],
            'preprocessing':'Training-only median imputation; training-only scaling for linear regression',
            'lobo_role':'Four-cell sensitivity analysis, not another independent confirmation of the fixed holdout',
            'predictions':'Unclipped predictions are scored and saved'}
    (out/'experiment_config.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
    print(scores.to_string(index=False),flush=True)
    return scores

if __name__=='__main__': train(Path(__file__).resolve().parents[1])
