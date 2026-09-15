"""Checks a real running HTTP service using the complete bundled assessment request."""
import argparse
import json
from pathlib import Path
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser();p.add_argument('--base-url',default='http://127.0.0.1:8013');a=p.parse_args()
    with urllib.request.urlopen(a.base_url+'/api/v1/health',timeout=30) as r:
        health=json.load(r);assert health['data']['models_ready']
    body=(ROOT/'docs/examples/assessment.request.json').read_bytes()
    req=urllib.request.Request(a.base_url+'/api/v1/assessment',data=body,headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=60) as r:response=json.load(r)
    assert response['success'];d=response['data']
    assert d['data_quality']['summary']['schema_ready']
    assert d['soh']['status']=='available' and d['rul']['status']=='available'
    assert d['carbon']['summary']['total_kgCO2e']>0
    assert len(d['candidate_paths'])==4 and not d['automatic_model_to_pack_transfer']
    shap=d['explainability']
    assert abs(shap['base_value_soh_pct']+sum(x['shap_soh_pp'] for x in shap['contributions'])-shap['predicted_soh_pct'])<1e-4
    print(json.dumps({'status':'PASS','checks':['health','BMS','SOH','RUL','real_SHAP','carbon','four_paths','evidence_separation'],
          'soh_pct':d['soh']['predicted_soh_pct'],'rul_cycles':d['rul']['predicted_rul_cycles'],
          'carbon_kgCO2e':d['carbon']['summary']['total_kgCO2e']},ensure_ascii=False))

if __name__=='__main__':main()
