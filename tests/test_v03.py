import copy
import unittest
from backend.v03.decision import pareto_ids,safety_gate,weights_checked,resource_value,npv

def scenario():
    return {'scenario_id':'DEMO','data_kind':'illustrative','assessed_at':'2026-09-14T12:00:00+08:00',
        'inspection_at':'2026-09-14T10:00:00+08:00','health':{'soh_pct':85,'rul_cycles':120},
        'safety':{'critical_event':False,'electrical_pass':True,'thermal_pass':True,'mechanical_pass':True,
            'post_repair_pass':True,'second_life_approved':True,'recycler_approved':True,'transport_approved':True}}

POLICY={'inspection_valid_days':30,'continue_soh_min':80,'continue_rul_min':50,'second_life_soh_min':65}

class DecisionTests(unittest.TestCase):
    def test_pareto_directions(self):
        rows=[{'route_id':'a','carbon_kgco2e':1,'npv_cny':10,'recovered_kg':5,'technical_score':90},
              {'route_id':'b','carbon_kgco2e':2,'npv_cny':9,'recovered_kg':4,'technical_score':80},
              {'route_id':'c','carbon_kgco2e':3,'npv_cny':20,'recovered_kg':5,'technical_score':95}]
        self.assertEqual(set(pareto_ids(rows)),{'a','c'})
    def test_unknown_critical_holds_all(self):
        s=scenario();s['safety']['critical_event']=None
        self.assertFalse(any(x['eligible'] for x in safety_gate(s,POLICY).values()))
    def test_critical_holds_even_recycle(self):
        s=scenario();s['safety']['critical_event']=True
        self.assertFalse(any(x['eligible'] for x in safety_gate(s,POLICY).values()))
    def test_string_false_not_boolean(self):
        s=scenario();s['safety']['critical_event']='false'
        with self.assertRaises(ValueError):safety_gate(s,POLICY)
    def test_inspection_expired(self):
        s=scenario();s['inspection_at']='2020-01-01T00:00:00Z'
        self.assertFalse(any(x['eligible'] for x in safety_gate(s,POLICY).values()))
    def test_missing_repair_evidence_blocks_repair(self):
        s=scenario();s['safety']['post_repair_pass']=None
        self.assertFalse(safety_gate(s,POLICY)['repair_then_use']['eligible'])
    def test_real_input_not_auto_approved(self):
        s=scenario();s['data_kind']='vehicle_unvalidated'
        self.assertFalse(any(x['eligible'] for x in safety_gate(s,POLICY).values()))
    def test_weight_validation(self):
        with self.assertRaises(ValueError):weights_checked({'carbon':-1,'economic':1,'resource':1,'technical':1})
        with self.assertRaises(ValueError):weights_checked({'carbon':0,'economic':0,'resource':0,'technical':0})
    def test_resource_mass_value(self):
        r=resource_value(100,[{'material_id':'Cu','mass_fraction':.1,'recovery_yield':.9,'price_cny_per_kg':50}],1)
        self.assertAlmostEqual(r['recovered_kg'],9)
        self.assertAlmostEqual(r['material_value_cny'],450)
    def test_resource_mass_balance(self):
        with self.assertRaises(ValueError):resource_value(100,[{'material_id':'a','mass_fraction':.8,'recovery_yield':1,'price_cny_per_kg':1},{'material_id':'b','mass_fraction':.8,'recovery_yield':1,'price_cny_per_kg':1}],1)
    def test_discounting(self):
        self.assertAlmostEqual(npv([{'year':0,'cash_cny':-100},{'year':1,'cash_cny':110}],.1),0)

if __name__=='__main__':unittest.main()
