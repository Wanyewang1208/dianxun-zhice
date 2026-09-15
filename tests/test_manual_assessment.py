import copy
import unittest
from pathlib import Path
from backend.services.assessment import assessment

ROOT=Path(__file__).resolve().parents[1]

def manual():
    return {'input_mode':'manual','data_kind':'user_declared','manual_input':{
        'rated_capacity_kwh':60,'current_available_capacity_kwh':49.44,'cycle_count':1126}}

def demo():
    p=manual();p['data_kind']='demo'
    p['manual_input'].update(new_battery_reference_price=50000,cell_voltage_delta_mv=18,
        fault_code_present=False,thermal_event_history=False)
    p['prototype_assumptions']={'reference_cycle_life':2500,'safety_factor':0.9,'consistency_factor':0.91}
    return p

class ManualTests(unittest.TestCase):
    def assess(self,p):return assessment(ROOT,p)
    def test_abnormal_condition_blocks_demo_value(self):
        for key,value in [('current_temperature_c',150),('cell_voltage_delta_mv',3000),('historical_max_temperature_c',80)]:
            p=demo();p['manual_input'][key]=value
            d=self.assess(p)
            self.assertEqual(d['safety']['status'],'hold_for_professional_review')
            self.assertIsNone(d['current_use_value'])
    def test_inconsistent_small_delta_cannot_hide_large_voltage_gap(self):
        p=demo();p['manual_input'].update(max_cell_voltage_v=4.2,min_cell_voltage_v=3.2,cell_voltage_delta_mv=18)
        self.assertIsNone(self.assess(p)['current_use_value'])
    def test_huge_integer_is_validation_error(self):
        p=manual();p['manual_input']['rated_capacity_kwh']=10**400
        with self.assertRaises(ValueError):self.assess(p)
    def test_no_bms_capacity_ratio(self):
        d=self.assess(manual())
        self.assertAlmostEqual(d['soh']['calculated_soh'],82.4)
        self.assertEqual(d['data_quality']['bms']['status'],'not_provided')
        self.assertEqual(d['rul']['status'],'not_available')
        self.assertEqual(d['explainability']['status'],'not_available')
    def test_measured_not_overwritten(self):
        p=manual();p['manual_input']['measured_soh']=80
        d=self.assess(p)['soh']
        self.assertEqual(d['measured_soh'],80);self.assertAlmostEqual(d['calculated_soh'],82.4)
        self.assertAlmostEqual(d['difference_pp'],2.4)
    def test_missing_capacity_does_not_invent(self):
        p=manual();p['manual_input']['current_available_capacity_kwh']=None
        d=self.assess(p)
        self.assertIsNone(d['soh']['calculated_soh'])
        self.assertIsNone(d['residual_value']['index'])
        self.assertIsNone(d['residual_value']['estimated_value_range_cny'])
    def test_validation(self):
        for key,value in [('rated_capacity_kwh',0),('current_available_capacity_kwh',90),('cycle_count',-1),
                          ('cycle_count',1.5),('fast_charge_ratio',101),('mileage_km',True),('measured_soh',float('nan'))]:
            with self.subTest(key=key):
                p=manual();p['manual_input'][key]=value
                with self.assertRaises(ValueError):self.assess(p)
    def test_unknown_field(self):
        p=manual();p['manual_input']['secret_default']=100
        with self.assertRaises(ValueError):self.assess(p)
    def test_voltage_difference(self):
        p=manual();p['manual_input'].update(max_cell_voltage_v=3.4,min_cell_voltage_v=3.382)
        d=self.assess(p);self.assertAlmostEqual(d['effective_condition']['cell_voltage_delta_mv'],18)
    def test_inverted_voltage(self):
        p=manual();p['manual_input'].update(max_cell_voltage_v=3,min_cell_voltage_v=4)
        with self.assertRaises(ValueError):self.assess(p)
    def test_inverted_soc(self):
        p=manual();p['manual_input'].update(usual_charge_upper_soc=20,usual_discharge_lower_soc=80)
        with self.assertRaises(ValueError):self.assess(p)
    def test_partial_index_bounds(self):
        r=self.assess(manual())['residual_value']
        self.assertEqual(r['status'],'insufficient_evidence');self.assertIsNone(r['index'])
        self.assertAlmostEqual(r['index_bounds']['lower'],0.35*82.4)
        self.assertAlmostEqual(r['index_bounds']['upper'],0.35*82.4+65)
    def test_demo_valuation_formula(self):
        d=self.assess(demo());r=d['residual_value'];life=(2500-1126)/2500
        self.assertAlmostEqual(r['index'],0.35*82.4+0.30*life*100+0.20*90+0.15*91)
        midpoint=50000*0.824*life*0.9*0.91
        self.assertAlmostEqual(r['estimated_value_range_cny']['midpoint'],midpoint)
        self.assertAlmostEqual(r['estimated_value_range_cny']['lower'],midpoint*0.88)
        self.assertEqual(d['rul']['status'],'prototype_assumption')
    def test_no_price_still_index_for_complete_demo(self):
        p=demo();p['manual_input'].pop('new_battery_reference_price')
        r=self.assess(p)['residual_value'];self.assertIsNotNone(r['index']);self.assertIsNone(r['estimated_value_range_cny'])
    def test_real_data_cannot_use_demo_assumptions(self):
        p=demo();p['data_kind']='user_declared'
        with self.assertRaises(ValueError):self.assess(p)
    def test_thermal_history_blocks_price_and_paths(self):
        p=demo();p['manual_input']['thermal_event_history']=True
        d=self.assess(p)
        self.assertIsNone(d['residual_value']['estimated_value_range_cny'])
        self.assertIsNone(d['recommendation']['route_id'])
        self.assertTrue(all(not r['eligible'] for r in d['candidate_paths']))
    def test_fault_blocks_ordinary_valuation(self):
        p=demo();p['manual_input']['fault_code_present']=True
        self.assertIsNone(self.assess(p)['residual_value']['estimated_value_range_cny'])
    def test_no_fake_carbon(self):
        self.assertEqual(self.assess(manual())['carbon']['status'],'not_provided')
    def test_carbon_inventory(self):
        import json
        p=manual();p['carbon']=json.loads((ROOT/'docs/examples/carbon.request.json').read_text(encoding='utf-8'))
        self.assertAlmostEqual(self.assess(p)['carbon']['summary']['total_kgCO2e'],5560.654)
    def test_bms_precedence_and_original_preserved(self):
        import json
        p=manual();p['manual_input']['max_cell_voltage_v']=3.1
        p['bms']=json.loads((ROOT/'docs/examples/bms.request.json').read_text(encoding='utf-8'))
        d=self.assess(p)
        self.assertEqual(d['input_snapshot']['max_cell_voltage_v'],3.1)
        self.assertEqual(d['field_sources']['max_cell_voltage_v'],'bms_latest_accepted')
        self.assertNotEqual(d['effective_condition']['max_cell_voltage_v'],3.1)
    def test_wrong_bms_identity_not_used(self):
        import json
        p=manual();p['battery_id']='UNRELATED'
        p['bms']=json.loads((ROOT/'docs/examples/bms.request.json').read_text(encoding='utf-8'))
        d=self.assess(p);self.assertFalse(d['data_quality']['bms_used_for_condition'])
    def test_null_optional_booleans_not_safe(self):
        p=demo();p['manual_input']['fault_code_present']=None
        d=self.assess(p);self.assertEqual(d['safety']['status'],'unknown')
        self.assertIsNone(d['residual_value']['estimated_value_range_cny'])
    def test_scenario_gate_blocks_ordinary_price(self):
        import json
        p=demo();p['decision_scenario']=json.loads((ROOT/'docs/examples/decision.request.json').read_text(encoding='utf-8'))['scenario']
        p['decision_scenario']['safety']['critical_event']=True
        d=self.assess(p)
        self.assertIsNone(d['recommendation']['route_id'])
        self.assertIsNone(d['current_use_value'])
    def test_demo_scenario_never_overrides_reported_fault(self):
        import json
        p=demo();p['manual_input']['fault_code_present']=True
        p['decision_scenario']=json.loads((ROOT/'docs/examples/decision.request.json').read_text(encoding='utf-8'))['scenario']
        d=self.assess(p);self.assertIsNone(d['recommendation']['route_id']);self.assertIsNone(d['current_use_value'])
    def test_zero_demo_safety_factor_blocks(self):
        p=demo();p['prototype_assumptions']['safety_factor']=0
        self.assertEqual(self.assess(p)['safety']['status'],'hold_for_professional_review')
    def test_request_is_not_mutated(self):
        p=demo();before=copy.deepcopy(p);self.assess(p);self.assertEqual(p,before)

if __name__=='__main__':unittest.main()
