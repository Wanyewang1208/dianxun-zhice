"""Smoke checks against an already running local API; no frontend required."""
import argparse
import json
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
ROOT=Path(__file__).resolve().parents[1]
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--base-url',default='http://127.0.0.1:8013');args=parser.parse_args()
    def post(body):
        with urlopen(Request(args.base_url+'/api/v1/assessment',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'}),timeout=30) as r:return json.load(r)
    for name in ['manual','manual_demo']:
        body=json.loads((ROOT/f'docs/examples/{name}.request.json').read_text(encoding='utf-8'))
        result=post(body);assert result['success'];d=result['data']
        assert abs(d['soh']['calculated_soh']-82.4)<1e-8
        assert not d['automatic_model_to_pack_transfer']
        assert d['explainability']['status']=='not_available'
        if name=='manual':assert d['rul']['status']=='not_available' and d['current_use_value'] is None
        else:assert d['current_use_value'] is not None
    body['manual_input']['rated_capacity_kwh']=10**400
    try:post(body);raise AssertionError('Expected invalid input')
    except HTTPError as error:assert error.code==400
    print('PASS: manual assessment, explicit Demo value, missing-evidence boundaries, invalid integer HTTP 400')
if __name__=='__main__':main()
