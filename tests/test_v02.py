import unittest
import numpy as np
import pandas as pd
from backend.v03.rul_v02 import prefix_features, fit_priors, predict_prior, run_fold
from backend.v03.bms_validate import validate

def history(b='A',event=True):
    c=np.arange(1,81)
    return pd.DataFrame({'battery_id':b,'cycle':c,'capacity_ah':2-.01*c if event else 2-.003*c})

class RULV02Tests(unittest.TestCase):
    def test_prefix_ignores_future(self):
        h=history(); a=prefix_features(h,30)
        h.loc[h.cycle>30,'capacity_ah']=999
        self.assertEqual(a,prefix_features(h,30))
    def test_short_prefix(self):
        with self.assertRaises(ValueError): prefix_features(history(),10)
    def test_prior_finite_flat_capacity(self):
        prior=fit_priors(history())
        f=prefix_features(history(event=False).assign(capacity_ah=1.8),30)
        self.assertTrue(np.isfinite(predict_prior(f,prior,'blended_rate')))
    def test_censored_only_not_used_as_known_life(self):
        with self.assertRaises(ValueError): fit_priors(history(event=False))
    def test_fold_rejects_overlap(self):
        with self.assertRaises(ValueError): run_fold(history(),['A'],'A')

def frames():
    m=pd.DataFrame([{'battery_id':'SYNTHETIC_A','battery_chemistry':'LFP','rated_capacity_ah':100,
       'current_sign_convention':'discharge_positive','voltage_unit':'V','current_unit':'A',
       'temperature_unit':'degC','soc_unit':'%','data_origin':'synthetic_fixture'}])
    t=pd.DataFrame([{'battery_id':'SYNTHETIC_A','timestamp':f'2026-01-01T00:00:{i:02d}+08:00',
       'pack_voltage':320,'pack_current':10,'SOC':60,'cell_voltage_max':3.4,'cell_voltage_min':3.3,
       'temperature_max':30,'temperature_min':25,'charge_status':'discharging','mileage':100} for i in [0,10,20]])
    return t,m

class BMSTests(unittest.TestCase):
    def test_good_fixture(self):
        t,m=frames(); r=validate(t,m)
        self.assertEqual(len(r['accepted']),3)
        self.assertTrue(r['summary']['synthetic_fixture_present'])
    def test_duplicate_keys_all_quarantined(self):
        t,m=frames(); t=pd.concat([t,t.iloc[[0]]],ignore_index=True)
        r=validate(t,m); self.assertEqual(len(r['rejected']),2)
    def test_naive_time_rejected(self):
        t,m=frames();t.loc[0,'timestamp']='2026-01-01T00:00:00'
        self.assertEqual(len(validate(t,m)['rejected']),1)
    def test_soc_out_of_range(self):
        t,m=frames();t.loc[0,'SOC']=101
        self.assertEqual(len(validate(t,m)['rejected']),1)
    def test_wrong_unit_rejected(self):
        t,m=frames();m.loc[0,'voltage_unit']='mV'
        self.assertEqual(len(validate(t,m)['accepted']),0)
    def test_inverted_extrema(self):
        t,m=frames();t.loc[0,'cell_voltage_min']=3.5
        self.assertEqual(len(validate(t,m)['rejected']),1)
    def test_empty_is_not_ready(self):
        t,m=frames();r=validate(t.iloc[:0],m)
        self.assertFalse(r['summary']['schema_ready'])
    def test_sign_mismatch_warning(self):
        t,m=frames();t.loc[0,'pack_current']=-10
        r=validate(t,m)
        self.assertIn('current_status_mismatch',set(r['issues'].code))

    def test_current_sign_normalization_and_reimport(self):
        t,m=frames();m.loc[0,'current_sign_convention']='charge_positive'
        t['pack_current']=-10
        r=validate(t,m)
        self.assertTrue(r['accepted'].pack_current.eq(10).all())
        r2=validate(r['accepted'],r['normalized_metadata'])
        self.assertTrue(r2['accepted'].pack_current.eq(10).all())

    def test_missing_numeric_text(self):
        t,m=frames();t['pack_current']=t.pack_current.astype(str);t.loc[0,'pack_current']='missing'
        self.assertEqual(len(validate(t,m)['rejected']),1)

    def test_gap_warns(self):
        t,m=frames();t.loc[2,'timestamp']='2026-01-01T00:05:00+08:00'
        self.assertIn('time_gap',set(validate(t,m)['issues'].code))

if __name__=='__main__': unittest.main()
