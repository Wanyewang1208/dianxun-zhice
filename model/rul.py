"""Prefix-only rolling-capacity RUL baseline, with right-censored cells retained."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from .core import EOL_CAPACITY_AH,eol_cycle,estimate_rul
from .train_soh import metrics

def run(root):
    frame=pd.read_csv(root/'data/processed/cycles.csv')
    out=root/'data/demo/results/rul'; out.mkdir(parents=True,exist_ok=True)
    rows=[]; labels=[]
    for b,g in frame.groupby('battery_id'):
        g=g.sort_values('cycle'); event=eol_cycle(g.cycle,g.capacity_ah)
        for _,r in g.iterrows():
            cycle=int(r.cycle)
            label=None if event is None else max(event-cycle,0)
            labels.append({'battery_id':b,'cycle':cycle,'eol_cycle':event,'rul_cycles':label,
                           'right_censored':event is None,'post_eol':event is not None and cycle>event,
                           'remaining_observed_cycles_lower_bound':int(g.cycle.max())-cycle if event is None else None})
            # No post-EOL records and no trivial RUL=0 event rows included in evaluation.
            if event is not None and cycle>=event: continue
            prefix=g[g.cycle<=cycle]
            prediction=estimate_rul(prefix.cycle,prefix.capacity_ah)
            rows.append({'battery_id':b,'cycle':cycle,'true_rul_cycles':label,'right_censored':event is None,
                         'observed_history_rows':len(prefix),**prediction})
    predictions=pd.DataFrame(rows)
    predictions.to_csv(out/'rul_predictions.csv',index=False,encoding='utf-8-sig')
    pd.DataFrame(labels).to_csv(out/'rul_labels.csv',index=False,encoding='utf-8-sig')
    reports=[]
    for b,g in predictions.groupby('battery_id'):
        eligible=g[g.observed_history_rows>=30]
        valid=eligible.dropna(subset=['predicted_rul_cycles','true_rul_cycles'])
        m=metrics(valid.true_rul_cycles,valid.predicted_rul_cycles) if len(valid)>1 else {}
        reports.append({'battery_id':b,'eligible_prefixes':len(eligible),
                        'predicted_prefixes':int(eligible.predicted_rul_cycles.notna().sum()),
                        'evaluated_prefixes':len(valid),'right_censored':bool(g.right_censored.iloc[0]),
                        'MAE_cycles':m.get('MAE_pp'), 'RMSE_cycles':m.get('RMSE_pp'),'R2':m.get('R2'),
                        'coverage':float(eligible.predicted_rul_cycles.notna().mean()) if len(eligible) else 0})
    scores=pd.DataFrame(reports)
    scores.to_csv(out/'rul_metrics.csv',index=False,encoding='utf-8-sig')
    (out/'method.json').write_text(json.dumps({
        'method':'Least squares line on last 30 observed capacity measurements at each prefix; extrapolate to 1.4 Ah',
        'threshold_ah':EOL_CAPACITY_AH,'eol_definition':'First observed discharge capacity <= 1.4 Ah; first-passage event is absorbing',
        'threshold_source':'data/raw/README.txt; NASA FY08Q4, 30 percent fade from 2 Ah',
        'censoring':'No threshold crossing => true RUL missing, not last_cycle-current_cycle; omitted from MAE/RMSE/R2',
        'abstention':'Fewer than 30 observations or nondegrading slope => prediction missing',
        'input_assumption':'Measured diagnostic capacities through current cycle are available; not SOH model predictions',
        'evaluation':'Rolling-origin prefixes within each cell; no global training, tuning, or future prefix data',
        'uncertainty':'No calibrated interval; adjacent prefixes correlated; large extrapolation errors possible',
        'output_units':'Discharge-operation cycles, not calendar days, km or equivalent full cycles'},indent=2),encoding='utf-8')
    print(scores.to_string(index=False),flush=True)

if __name__=='__main__': run(Path(__file__).resolve().parents[1])
