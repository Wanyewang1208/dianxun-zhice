"""Exact native XGBoost TreeSHAP for the preserved V0.1 model, not causal inference."""
import hashlib
import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import xgboost as xgb

def explain_frame(root,frame):
    obj=joblib.load(root/'model/xgboost.joblib')
    features=obj['features'];pipe=obj['model'];raw=frame[features]
    transformed=pipe[:-1].transform(raw)
    booster=pipe[-1].get_booster()
    values=booster.predict(xgb.DMatrix(transformed),pred_contribs=True,approx_contribs=False)
    prediction=pipe.predict(raw)
    errors=np.abs(values.sum(axis=1)-prediction)
    if not np.allclose(values.sum(axis=1),prediction,rtol=0,atol=1e-4):
        raise AssertionError('SHAP additivity failed')
    return features,values,prediction,errors

def explain_sample(root,battery_id,cycle):
    if not isinstance(battery_id,str) or type(cycle) is not int:raise ValueError('battery_id must be text and cycle an integer')
    data=pd.read_csv(root/'data/processed/cycles.csv')
    row=data[(data.battery_id==battery_id)&(data.cycle==cycle)]
    if len(row)!=1:raise ValueError('Unknown NASA battery/cycle')
    names,values,pred,error=explain_frame(root,row)
    contributions=[{'feature':f,'feature_value':float(row.iloc[0][f]),'shap_soh_pp':float(values[0,i]),
                    'direction':'raises_prediction' if values[0,i]>0 else 'lowers_prediction' if values[0,i]<0 else 'zero'}
                   for i,f in enumerate(names)]
    return {'schema_version':'0.3','battery_id':battery_id,'cycle':cycle,'evidence_kind':'public_experimental_cell',
        'split_role':'held_out' if battery_id=='B0018' else 'training_cell',
        'predicted_soh_pct':float(pred[0]),'measured_soh_pct':float(row.soh_pct.iloc[0]),
        'base_value_soh_pct':float(values[0,-1]),'additivity_error_pp':float(error[0]),
        'contributions':sorted(contributions,key=lambda r:abs(r['shap_soh_pp']),reverse=True),
        'interpretation':'Contributions explain this model prediction relative to its tree baseline, not physical degradation causes',
        'scope':'NASA experimental discharge at 600 seconds; no validated whole-vehicle transfer'}

def run(root):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    out=root/'data/demo/results/shap';out.mkdir(parents=True,exist_ok=True)
    figdir=root/'data/demo/results/figures'
    data=pd.read_csv(root/'data/processed/cycles.csv');test=data[data.battery_id=='B0018']
    names,values,pred,errors=explain_frame(root,test)
    table=pd.DataFrame(values[:,:-1],columns=['shap__'+f for f in names])
    table.insert(0,'cycle',test.cycle.to_numpy());table.insert(0,'battery_id','B0018')
    table['base_value_soh_pct']=values[:,-1];table['predicted_soh_pct']=pred
    table['additivity_error_pp']=errors
    table.to_csv(out/'shap_values.csv',index=False,encoding='utf-8-sig')
    importance=pd.DataFrame({'feature':names,'mean_abs_shap_pp':np.mean(np.abs(values[:,:-1]),axis=0),
                             'mean_shap_pp':np.mean(values[:,:-1],axis=0)}).sort_values('mean_abs_shap_pp',ascending=False)
    importance.to_csv(out/'global_importance.csv',index=False,encoding='utf-8-sig')
    fig,ax=plt.subplots(figsize=(10,6));g=importance.sort_values('mean_abs_shap_pp')
    ax.barh(g.feature,g.mean_abs_shap_pp,color='#087f8c')
    ax.set(xlabel='Mean absolute SHAP contribution (SOH percentage points)',title='B0018 held-out samples | model attribution, NOT causal effects')
    fig.tight_layout()
    for ext in ['png','svg']:fig.savefig(figdir/f'shap_global.{ext}',dpi=170,bbox_inches='tight')
    plt.close(fig)
    locals=[]
    for cycle in [30,66,100]:
        result=explain_sample(root,'B0018',cycle);locals.append(result)
        (out/f'B0018_cycle_{cycle}.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    fig,axes=plt.subplots(3,1,figsize=(11,13))
    for ax,result in zip(axes,locals):
        c=list(reversed(result['contributions']))
        ax.barh([r['feature'] for r in c],[r['shap_soh_pp'] for r in c],
                color=['#087f8c' if r['shap_soh_pp']>=0 else '#d78c42' for r in c])
        ax.axvline(0,color='#444444',lw=.7)
        ax.set(xlabel='Signed contribution to predicted SOH (percentage points)',
            title=f"Cycle {result['cycle']} | baseline {result['base_value_soh_pct']:.2f}% -> prediction {result['predicted_soh_pct']:.2f}%")
    fig.suptitle('Local SHAP explanations | no claim of physical causation',fontsize=14)
    fig.tight_layout()
    for ext in ['png','svg']:fig.savefig(figdir/f'shap_local.{ext}',dpi=170,bbox_inches='tight')
    plt.close(fig)
    metadata={'method':'Native exact XGBoost TreeSHAP; pred_contribs=True, approx_contribs=False',
        'sample_count':len(test),'features':names,'max_additivity_error_pp':float(errors.max()),
        'model_sha256':hashlib.sha256((root/'model/xgboost.joblib').read_bytes()).hexdigest(),
        'reference':'https://xgboost.readthedocs.io/en/stable/python/python_api.html',
        'causal_caution':'https://shap.readthedocs.io/en/latest/example_notebooks/overviews/Be%20careful%20when%20interpreting%20predictive%20models%20in%20search%20of%20causal%20insights.html',
        'background':'Tree path cover from trained model; no held-out background fit or new training',
        'limitations':'Correlated early voltage features share attribution; ambient condition nearly constant; zero attribution is not evidence of no physical temperature effect'}
    (out/'method.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    print(importance.to_string(index=False));print('Max SHAP additivity error:',errors.max())

if __name__=='__main__':run(Path(__file__).resolve().parents[1])
