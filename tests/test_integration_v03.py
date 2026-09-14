import copy
import json
import threading
import unittest
import urllib.request
import urllib.error
from pathlib import Path
from backend.v03.api_server import make_server
from backend.v03.integration import handle_request
from backend.v03.decision import load_inputs,rank,evaluate_routes

ROOT=Path(__file__).resolve().parents[1]

class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=make_server(ROOT,port=0)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.url='http://127.0.0.1:'+str(cls.server.server_address[1])
        cls.request=json.loads((ROOT/'docs/v03_integration/example_report_request.json').read_text(encoding='utf-8'))
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join(timeout=3)
    def post(self,path,body):
        req=urllib.request.Request(self.url+path,data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=15) as r:return json.load(r)
    def test_http_health(self):
        with urllib.request.urlopen(self.url+'/health') as r:self.assertEqual(json.load(r)['schema_version'],'0.3')
    def test_http_explain_additivity(self):
        r=self.post('/v0.3/explain',{'battery_id':'B0018','cycle':66})
        self.assertLess(abs(r['base_value_soh_pct']+sum(x['shap_soh_pp'] for x in r['contributions'])-r['predicted_soh_pct']),1e-4)
    def test_http_report_keeps_evidence_separate(self):
        r=self.post('/v0.3/report',self.request)
        self.assertFalse(r['automatic_model_to_pack_transfer'])
        self.assertEqual(r['scenario_decision']['status'],'simulation_recommendation')
        self.assertIsNotNone(r['model_evidence']['rul'])
    def test_http_malformed_flag_rejected(self):
        body=copy.deepcopy(self.request);body['scenario']['safety']['critical_event']='false'
        with self.assertRaises(urllib.error.HTTPError) as err:self.post('/v0.3/report',body)
        self.assertEqual(err.exception.code,400)
    def test_unknown_battery_rejected(self):
        with self.assertRaises(ValueError):handle_request('explain',{'battery_id':'VEHICLE','cycle':66},ROOT)
    def test_bad_weight_cannot_bypass_gate(self):
        config,rows=load_inputs(ROOT);s=copy.deepcopy(self.request['scenario']);s['safety']['critical_event']=True
        r=rank(s,config,rows,{'carbon':0,'economic':100,'resource':0,'technical':0})
        self.assertIsNone(r['recommended_route'])
    def test_low_rul_disables_energy_claim(self):
        config,rows=load_inputs(ROOT);s=copy.deepcopy(self.request['scenario']);s['health']['rul_cycles']=1
        r=rank(s,config,rows)
        self.assertEqual(r['feasible_routes'],['recycle'])
    def test_missing_unit_blocks_life_routes(self):
        config,rows=load_inputs(ROOT);s=copy.deepcopy(self.request['scenario']);s['health'].pop('rul_unit',None)
        self.assertEqual(rank(s,config,rows)['feasible_routes'],['recycle'])
    def test_whole_pack_and_material_value_not_double_counted(self):
        import pandas as pd
        config,_=load_inputs(ROOT)
        routes=pd.read_csv(ROOT/'data/demo/decision/routes.csv').to_dict('records');routes[0]['recovery_fraction']=1
        with self.assertRaises(ValueError):evaluate_routes(config,routes,pd.read_csv(ROOT/'data/demo/decision/materials.csv').to_dict('records'),pd.read_csv(ROOT/'data/demo/decision/carbon_factors.csv'))
    def test_no_nan_in_report_json(self):
        json.dumps(handle_request('report',self.request,ROOT),allow_nan=False)

if __name__=='__main__':unittest.main()
