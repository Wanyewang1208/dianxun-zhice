"""Web teammate integration: JSON functions/CLI, without any frontend implementation."""
import argparse
import json
from pathlib import Path
import pandas as pd
from .decision import load_inputs,rank
from .explain_soh import explain_sample

def handle_request(action,payload,root):
    if not isinstance(payload,dict):raise ValueError('JSON object required')
    if action=='explain':
        if set(payload)-{'battery_id','cycle'}:raise ValueError('Unexpected explain field')
        return explain_sample(root,payload.get('battery_id'),payload.get('cycle'))
    if action=='decision':
        if set(payload)-{'scenario','weights'}:raise ValueError('Unexpected decision field')
        config,rows=load_inputs(root)
        return rank(payload.get('scenario'),config,rows,payload.get('weights'))
    if action=='report':
        if set(payload)-{'model_case','scenario','weights'}:raise ValueError('Unexpected report field')
        explanation=handle_request('explain',payload.get('model_case'),root)
        decision=handle_request('decision',{'scenario':payload.get('scenario'),'weights':payload.get('weights')},root)
        data=pd.read_csv(root/'data/demo/results/rul_v02/predictions.csv')
        matched=data[(data.test_battery==explanation['battery_id'])&(data.cycle==explanation['cycle'])&(data.model=='random_forest_rul')]
        rul={'predicted_rul_cycles':float(matched.predicted_rul_cycles.iloc[0]),'method':'V0.2 leave-one-cell-out random forest',
             'input_requirement':'Historical measured capacities through completion of this cycle; later availability than 600-second SOH prediction',
             'validation_status':'exploratory_same_dataset_reuse'} if len(matched)==1 else None
        return {'schema_version':'0.3','model_evidence':{'soh_explanation':explanation,'rul':rul},
            'scenario_decision':decision,'automatic_model_to_pack_transfer':False,
            'integration_status':'separate_public_cell_evidence_and_illustrative_pack_scenario',
            'display_notice':'NASA电芯结果与模拟电池包决策须分区展示，不能标成同一辆车的实测评估。'}
    raise ValueError('Unknown action')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--action',choices=['explain','decision','report'],required=True)
    p.add_argument('--request',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();root=Path(__file__).resolve().parents[2]
    result=handle_request(a.action,json.loads(a.request.read_text(encoding='utf-8-sig')),root)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    print('Saved JSON result:',a.output)

if __name__=='__main__':main()
