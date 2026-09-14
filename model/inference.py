"""Inference adapter over preserved V0.3 models. No retraining or vehicle transfer."""
import joblib
import pandas as pd
from .explain_soh import explain_sample
from .rul_v02 import prefix_features

def soh(root,case):
    explanation=explain_sample(root,**case)
    return {'status':'available','battery_id':case['battery_id'],'cycle':case['cycle'],
            'predicted_soh_pct':explanation['predicted_soh_pct'],
            'measured_soh_pct':explanation['measured_soh_pct'],
            'model':'V0.1 XGBoost','unit':'%','evidence_kind':'public_experimental_cell',
            'validation_status':'public_dataset_only','scope':explanation['scope']}

def rul(root,case):
    data=pd.read_csv(root/'data/processed/cycles.csv')
    cell=data[data.battery_id==case['battery_id']]
    if not (cell.cycle==case['cycle']).any():raise ValueError('Unknown NASA battery/cycle')
    history=cell[cell.cycle<=case['cycle']]
    common={'battery_id':case['battery_id'],'cycle':case['cycle'],'unit':'reference_discharge_cycles',
            'input_requirement':'At least 30 measured capacities in Ah through the current completed cycle',
            'evidence_kind':'public_experimental_cell','validation_status':'exploratory_same_dataset_reuse',
            'operating_condition_caution':'Not calendar life; depends on discharge conditions and measured capacities'}
    if len(history)<30:
        return {**common,'status':'not_available','predicted_rul_cycles':None,'reason':'insufficient_capacity_history'}
    from .core import EOL_CAPACITY_AH
    if float(history.iloc[-1].capacity_ah)<=EOL_CAPACITY_AH:
        return {**common,'status':'not_available','predicted_rul_cycles':None,'reason':'at_or_below_public_cell_eol_threshold'}
    obj=joblib.load(root/'model/rul_v02'/('leave_out_'+case['battery_id']+'.joblib'))
    features=prefix_features(history,case['cycle'])
    prediction=float(obj['model'].predict(pd.DataFrame([features])[obj['features']])[0])
    return {**common,'status':'available','predicted_rul_cycles':prediction,'method':'V0.2 leave-one-cell-out random forest',
            'features':features,'train_ids':obj['train_ids'],'capacity_history_rows':len(history)}
