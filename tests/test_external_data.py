import unittest
import numpy as np
from scripts.prepare_oxford import relative_seconds, voltage_temperature_features, capacity_ah, threshold_interval
from scripts.prepare_road_ev import session_proxy

class OxfordTests(unittest.TestCase):
    def test_matlab_days_not_seconds(self):
        t=relative_seconds(np.array([735954.,735954.+600/86400]))
        self.assertAlmostEqual(t[-1],600,places=4)
    def test_declared_time_format_guard(self):
        with self.assertRaises(ValueError): relative_seconds([0,600])
    def test_no_future_sample_leakage(self):
        t=np.arange(0,701,10,dtype=float);v=4.2-t/1000;temp=40+t/1000
        expected=voltage_temperature_features(t,v,temp)
        v[t>600]=999;temp[t>600]=999
        self.assertEqual(expected,voltage_temperature_features(t,v,temp))
    def test_short_window_rejected(self):
        with self.assertRaises(ValueError):voltage_temperature_features([0,20,30],[4,4,4],[40,40,40])
    def test_capacity_sign_and_units(self):
        self.assertAlmostEqual(capacity_ah([0,-100,-740]),.740)
        with self.assertRaises(ValueError):capacity_ah([0,740])
    def test_interval_not_exact_eol(self):
        self.assertEqual(threshold_interval([0,100,300],[.74,.60,.58]),(100,300,False))
        self.assertEqual(threshold_interval([0,100],[.74,.60]),(100,None,True))

class RoadTests(unittest.TestCase):
    def test_capacity_proxy_arithmetic(self):
        value,status=session_proxy(np.arange(101)*10,np.full(101,-72.),np.linspace(20,40,101))
        self.assertAlmostEqual(value,100.);self.assertEqual(status,'accepted_proxy')
    def test_gap_not_integrated(self):
        t=np.arange(101)*10;t[50:]+=100
        self.assertEqual(session_proxy(t,np.full(101,-72.),np.linspace(20,40,101))[1],'time_gap')
    def test_small_soc_span_rejected(self):
        self.assertEqual(session_proxy(np.arange(101)*10,np.full(101,-72.),np.linspace(20,21,101))[1],'soc_span_below_20pp')
    def test_wrong_current_sign_rejected(self):
        self.assertEqual(session_proxy(np.arange(101)*10,np.full(101,72.),np.linspace(20,40,101))[1],'noncharging_sign')

if __name__=='__main__':unittest.main()
