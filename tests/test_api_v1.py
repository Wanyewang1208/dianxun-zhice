import copy
import json
import threading
import unittest
import urllib.request
import urllib.error
from pathlib import Path
from backend.app import make_server

ROOT = Path(__file__).resolve().parents[1]

class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = make_server(ROOT, port=0, allowed_origin='http://localhost:5173')
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = 'http://127.0.0.1:' + str(cls.server.server_address[1])
        cls.legacy = json.loads((ROOT/'docs/v03_integration/example_report_request.json').read_text())
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join()
    def request(self, path, body=None, headers=None):
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(self.url+path, data=data, headers=headers or {'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=60) as r: return r.status, json.load(r)
        except urllib.error.HTTPError as e: return e.code, json.load(e)
    def test_health(self):
        status,r=self.request('/api/v1/health')
        self.assertEqual(status,200);self.assertTrue(r['success']);self.assertEqual(r['data']['status'],'ok')
    def test_assessment(self):
        status,r=self.request('/api/v1/assessment',self.legacy)
        self.assertEqual(status,200);d=r['data']
        self.assertEqual(set(['battery_id','data_quality','soh','rul','explainability','carbon','safety','candidate_paths','recommendation','decision_reason'])-set(d),set())
        self.assertFalse(d['automatic_model_to_pack_transfer']);self.assertEqual(len(d['candidate_paths']),4)
        self.assertEqual(d['carbon']['status'],'not_provided')
    def test_soh_real_inference(self):
        status,r=self.request('/api/v1/soh',self.legacy['model_case'])
        self.assertEqual(status,200);self.assertTrue(0<r['data']['predicted_soh_pct']<120)
    def test_carbon_arithmetic(self):
        payload={'activities':[{'activity_id':'a','stage':'use','quantity':10,'activity_unit':'kWh','factor_id':'f'}],
          'factors':[{'factor_id':'f','value':0.5,'activity_unit':'kWh','output_unit':'kgCO2e','status':'illustrative'}],'allow_demo':True}
        status,r=self.request('/api/v1/carbon',payload)
        self.assertEqual(status,200);self.assertEqual(r['data']['summary']['total_kgCO2e'],5)
    def test_rul_real_inference(self):
        status,r=self.request('/api/v1/rul',self.legacy['model_case'])
        self.assertEqual(status,200);self.assertEqual(r['data']['status'],'available')
        self.assertGreater(r['data']['predicted_rul_cycles'],0)
    def test_rul_short_history(self):
        _,r=self.request('/api/v1/rul',{'battery_id':'B0018','cycle':10})
        self.assertEqual(r['data']['status'],'not_available')
    def test_shap_additivity(self):
        _,r=self.request('/api/v1/explain',self.legacy['model_case']);d=r['data']
        self.assertLess(abs(d['base_value_soh_pct']+sum(x['shap_soh_pp'] for x in d['contributions'])-d['predicted_soh_pct']),1e-4)
    def test_invalid_payload(self):
        for payload in [[],{'battery_id':'../secret','cycle':66},{'battery_id':'B0018','cycle':True}]:
            status,r=self.request('/api/v1/soh',payload)
            self.assertEqual(status,400);self.assertFalse(r['success']);self.assertEqual(r['error']['code'],'INVALID_REQUEST')
    def test_unknown_route(self):
        status,r=self.request('/api/v1/nope')
        self.assertEqual(status,404);self.assertEqual(r['error']['code'],'NOT_FOUND')
    def test_critical_event_no_recommendation(self):
        body=copy.deepcopy(self.legacy);body['scenario']['safety']['critical_event']=True
        _,r=self.request('/api/v1/assessment',body)
        self.assertIsNone(r['data']['recommendation']['route_id'])
        self.assertTrue(all(x['weighted_score'] is None for x in r['data']['candidate_paths']))
    def test_legacy_unchanged(self):
        status,r=self.request('/v0.3/report',self.legacy)
        self.assertEqual(status,200);self.assertEqual(r['schema_version'],'0.3');self.assertNotIn('success',r)
    def test_bms_json_csv(self):
        base=ROOT/'data/sample/bms/synthetic_fixtures'
        body={'telemetry_csv':(base/'good_telemetry.csv').read_text(encoding='utf-8-sig'),
              'metadata_csv':(base/'metadata.csv').read_text(encoding='utf-8-sig')}
        status,r=self.request('/api/v1/bms/validate',body)
        self.assertEqual(status,200);self.assertTrue(r['data']['summary']['schema_ready'])
    def test_multipart_upload(self):
        base=ROOT/'data/sample/bms/synthetic_fixtures'
        boundary='dianxun-test-boundary'
        chunks=[]
        for field,filename in [('telemetry','good_telemetry.csv'),('metadata','metadata.csv')]:
            chunks.append(('--'+boundary+'\r\nContent-Disposition: form-data; name="'+field+'"; filename="'+filename+'"\r\nContent-Type: text/csv\r\n\r\n').encode()+(base/filename).read_bytes()+b'\r\n')
        raw=b''.join(chunks)+('--'+boundary+'--\r\n').encode()
        req=urllib.request.Request(self.url+'/api/v1/bms/validate',data=raw,headers={'Content-Type':'multipart/form-data; boundary='+boundary})
        with urllib.request.urlopen(req) as r:self.assertTrue(json.load(r)['data']['summary']['schema_ready'])
    def test_bad_bms_not_mislabeled_as_vehicle_inference(self):
        base=ROOT/'data/sample/bms/synthetic_fixtures'
        body=copy.deepcopy(self.legacy)
        body['bms']={'telemetry_csv':(base/'bad_telemetry.csv').read_text(encoding='utf-8-sig'),'metadata_csv':(base/'metadata.csv').read_text(encoding='utf-8-sig')}
        _,r=self.request('/api/v1/assessment',body)
        self.assertFalse(r['data']['data_quality']['summary']['schema_ready'])
        self.assertEqual(r['data']['soh']['evidence_kind'],'public_experimental_cell')
        self.assertFalse(r['data']['automatic_model_to_pack_transfer'])
    def test_carbon_unit_mismatch(self):
        body={'activities':[{'activity_id':'a','stage':'use','quantity':10,'activity_unit':'MWh','factor_id':'f'}],
        'factors':[{'factor_id':'f','value':0.5,'activity_unit':'kWh','output_unit':'kgCO2e','status':'illustrative'}],'allow_demo':True}
        status,r=self.request('/api/v1/carbon',body);self.assertEqual(status,400)
    def test_payload_size_limit(self):
        status,r=self.request('/api/v1/soh',{'padding':'a'*(2*1024*1024)})
        self.assertEqual(status,413)
    def test_cors(self):
        req=urllib.request.Request(self.url+'/api/v1/assessment',method='OPTIONS',headers={'Origin':'http://localhost:5173'})
        with urllib.request.urlopen(req) as r:self.assertEqual(r.headers['Access-Control-Allow-Origin'],'http://localhost:5173')
    def test_nonfinite_json(self):
        status,r=self.request('/api/v1/soh',{'battery_id':'B0018','cycle':float('nan')})
        self.assertEqual(status,400);self.assertEqual(r['error']['code'],'INVALID_REQUEST')

if __name__=='__main__':unittest.main()
