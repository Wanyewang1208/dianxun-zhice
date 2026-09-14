"""Standalone result figures for scientific inspection and export."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

COLORS=['#087f8c','#e09f3e','#6750a4','#c25252']
MODELS=['linear_regression','random_forest','xgboost']
LABELS=['Linear regression','Random forest','XGBoost']

def finish(fig,path):
    fig.savefig(path,dpi=180,bbox_inches='tight')
    fig.savefig(path.with_suffix('.svg'),bbox_inches='tight')
    plt.close(fig)

def draw(root):
    out=root/'data/demo/results/figures'; out.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,
                         'figure.facecolor':'white','axes.grid':True,'grid.alpha':.18})
    data=pd.read_csv(root/'data/processed/cycles.csv')
    pred=pd.read_csv(root/'data/demo/results/soh/holdout_predictions.csv')
    scores=pd.read_csv(root/'data/demo/results/soh/holdout_metrics.csv').set_index('model')
    fig,ax=plt.subplots(figsize=(10,5.2))
    for (b,g),color in zip(data.groupby('battery_id'),COLORS):
        ax.plot(g.cycle,g.soh_pct,label=b+(' (holdout)' if b=='B0018' else ' (train)'),color=color,lw=1.8)
    ax.axhline(70,color='#333333',ls='--',label='NASA EOL: 1.4 Ah / 2 Ah = 70%')
    ax.set(xlabel='Discharge cycle index',ylabel='SOH (% of rated 2 Ah)',title='NASA FY08Q4 | observed capacity degradation')
    ax.legend(ncol=2,fontsize=9); finish(fig,out/'degradation_curves.png')
    fig,axes=plt.subplots(3,1,figsize=(10,10),sharex=True)
    for ax,model,label,color in zip(axes,MODELS,LABELS,COLORS):
        g=pred[pred.model==model].sort_values('cycle')
        ax.plot(g.cycle,g.true_soh_pct,color='#222222',label='Measured SOH',lw=1.8)
        ax.plot(g.cycle,g.predicted_soh_pct,color=color,label='Predicted SOH',lw=1.5)
        ax.axhline(70,color='#777777',ls=':',lw=1)
        m=scores.loc[model]
        ax.set(ylabel='SOH (%)',title=f'{label} | MAE {m.MAE_pp:.2f} pp | RMSE {m.RMSE_pp:.2f} pp | R2 {m.R2:.3f}')
        ax.legend(loc='upper right',fontsize=9)
    axes[-1].set_xlabel('Discharge cycle index')
    fig.suptitle('Unseen cell B0018 | train: B0005, B0006, B0007',fontsize=14,y=1.01)
    fig.tight_layout(); finish(fig,out/'soh_true_vs_predicted.png')
    fig,axes=plt.subplots(1,3,figsize=(12,4),sharex=True,sharey=True)
    for ax,model,label,color in zip(axes,MODELS,LABELS,COLORS):
        g=pred[pred.model==model]
        ax.scatter(g.true_soh_pct,g.predicted_soh_pct,c=color,s=15,alpha=.65)
        low=min(pred.true_soh_pct.min(),pred.predicted_soh_pct.min())-2
        high=max(pred.true_soh_pct.max(),pred.predicted_soh_pct.max())+2
        ax.plot([low,high],[low,high],color='#444444',ls='--',lw=1)
        ax.set(title=label,xlabel='Measured SOH (%)')
    axes[0].set_ylabel('Predicted SOH (%)'); fig.suptitle('B0018 holdout parity plots'); fig.tight_layout()
    finish(fig,out/'soh_parity.png')
    lobo=pd.read_csv(root/'data/demo/results/soh/lobo_metrics_by_cell.csv')
    fig,ax=plt.subplots(figsize=(10,5))
    ids=sorted(lobo.test_battery.unique()); x=np.arange(len(ids)); width=.24
    for j,(model,label,color) in enumerate(zip(MODELS,LABELS,COLORS)):
        g=lobo[lobo.model==model].set_index('test_battery').loc[ids]
        ax.bar(x+(j-1)*width,g.MAE_pp,width,label=label,color=color)
    ax.set_xticks(x,ids); ax.set(xlabel='Held-out battery',ylabel='MAE (percentage points)',
        title='Leave-one-battery-out sensitivity | fixed hyperparameters')
    ax.legend(); finish(fig,out/'lobo_mae.png')
    r=pd.read_csv(root/'data/demo/results/rul/rul_predictions.csv')
    fig,axes=plt.subplots(2,2,figsize=(11,8))
    for ax,(b,g),color in zip(axes.flat,r.groupby('battery_id'),COLORS):
        g=g[g.observed_history_rows>=30]
        if g.true_rul_cycles.notna().any():
            ax.plot(g.cycle,g.true_rul_cycles,color='#222222',label='Observed first-passage RUL')
        ax.plot(g.cycle,g.predicted_rul_cycles,color=color,label='30-cycle capacity trend')
        ax.set(title=b+(' | right-censored' if g.right_censored.iloc[0] else ''),
               xlabel='Current discharge cycle',ylabel='Remaining discharge cycles')
        ax.legend(fontsize=8)
    fig.suptitle('RUL baseline | measured-capacity prefixes only; no future input',fontsize=13)
    fig.tight_layout(); finish(fig,out/'rul_baseline.png')
    carbon=json.loads((root/'data/demo/results/carbon/carbon_summary.json').read_text(encoding='utf-8'))
    fig,ax=plt.subplots(figsize=(10,4.5))
    labels=['Manufacturing','Use electricity','Maintenance / transport','End-of-life']
    vals=list(carbon['by_stage_kgCO2e'].values())
    ax.barh(labels,vals,color=COLORS)
    for i,v in enumerate(vals): ax.text(v+max(vals)*.015,i,f'{v:,.1f}',va='center')
    ax.set_xlim(0,max(vals)*1.2)
    ax.set(xlabel='kg CO2e',title='Illustrative carbon scenario | NOT a verified product footprint')
    finish(fig,out/'carbon_example.png')
    print('Saved six PNG figures and six editable SVG figures',flush=True)

if __name__=='__main__': draw(Path(__file__).resolve().parents[2])
