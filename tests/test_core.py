import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import pandas as pd
from backend.v03.core import assert_disjoint, early_features, eol_cycle, estimate_rul, FEATURES
from backend.v03.carbon import calculate

class BatteryTests(unittest.TestCase):
    def test_split_rejects_overlap(self):
        with self.assertRaises(ValueError):
            assert_disjoint(['a', 'b'], ['b'])
        assert_disjoint(['a'], ['b'])

    def test_no_target_predictors(self):
        for c in FEATURES:
            self.assertFalse(any(x in c.lower() for x in ['capacity', 'soh', 'rul', 'duration', 'end_voltage']))

    def test_fixed_window_is_causal(self):
        t = np.arange(0, 1210, 10.)
        d = {'Time':t, 'Voltage_measured':4.2-t/4000,
             'Current_measured':np.full(len(t),-2.), 'Temperature_measured':25+t/1000}
        a = early_features(d)
        d['Voltage_measured'][t>600] = 0
        d['Temperature_measured'][t>600] = 999
        b = early_features(d)
        self.assertEqual(a,b)
        self.assertAlmostEqual(a['voltage_600s_v'],4.05)

    def test_short_window_rejected(self):
        with self.assertRaises(ValueError):
            early_features({'Time':[0,10], 'Voltage_measured':[4,3.9],
                            'Current_measured':[-2,-2], 'Temperature_measured':[25,25]})

    def test_eol_censoring(self):
        self.assertIsNone(eol_cycle([1,2,3], [2,1.6,1.5]))
        self.assertIsNone(eol_cycle([1,2], [2,1.400455]))
        self.assertEqual(eol_cycle([1,2,3,4], [2,1.5,1.4,1.45]),3)

    def test_rul_causal_trend(self):
        cycles=np.arange(1,31)
        r=estimate_rul(cycles,2-.01*cycles)
        self.assertAlmostEqual(r['predicted_rul_cycles'],30,places=5)
        self.assertIsNone(estimate_rul(cycles,np.ones(30)*1.8)['predicted_rul_cycles'])

class CarbonTests(unittest.TestCase):
    def setUp(self):
        self.f=pd.DataFrame([{'factor_id':'grid','value':.5,'activity_unit':'kWh',
                            'output_unit':'kgCO2e','status':'official'}])
        self.a=pd.DataFrame([{'activity_id':'u1','stage':'use','quantity':100,
                            'activity_unit':'kWh','factor_id':'grid'}])
    def test_arithmetic(self):
        detail,summary=calculate(self.a,self.f)
        self.assertEqual(summary['total_kgCO2e'],50)
    def test_missing_factor(self):
        self.a.loc[0,'factor_id']='missing'
        with self.assertRaises(ValueError): calculate(self.a,self.f)
    def test_bad_units(self):
        self.a.loc[0,'activity_unit']='km'
        with self.assertRaises(ValueError): calculate(self.a,self.f)
    def test_duplicate_factor(self):
        with self.assertRaises(ValueError): calculate(self.a,pd.concat([self.f,self.f]))
    def test_negative_quantity(self):
        self.a.loc[0,'quantity']=-1
        with self.assertRaises(ValueError): calculate(self.a,self.f)
    def test_demo_requires_optin(self):
        self.f.loc[0,'status']='illustrative'
        with self.assertRaises(ValueError): calculate(self.a,self.f)
        self.assertTrue(calculate(self.a,self.f,allow_demo=True)[1]['contains_illustrative_factors'])

    def test_nan_quantity_is_not_zero(self):
        self.a.loc[0,'quantity']=np.nan
        with self.assertRaises(ValueError): calculate(self.a,self.f)

    def test_missing_factor_value(self):
        self.f.loc[0,'value']=np.nan
        with self.assertRaises(ValueError): calculate(self.a,self.f)

    def test_incomplete_scope_is_visible(self):
        summary=calculate(self.a,self.f)[1]
        self.assertFalse(summary['scope_complete'])
        self.assertIn('manufacturing',summary['missing_stages'])

    def test_demo_activity_remains_labelled_with_official_factor(self):
        self.a['data_status']='illustrative'
        with self.assertRaises(ValueError): calculate(self.a,self.f)
        summary=calculate(self.a,self.f,allow_demo=True)[1]
        self.assertTrue(summary['contains_illustrative_activities'])
        self.assertIn('Illustrative',summary['interpretation'])

if __name__=='__main__': unittest.main()
