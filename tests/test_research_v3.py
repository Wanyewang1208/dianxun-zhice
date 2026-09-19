import unittest
import pandas as pd
from research.public_battery.verify_v3 import assert_complete_groups, assert_sample_coverage

class V3EvidenceTests(unittest.TestCase):
    def test_missing_experiment_is_rejected(self):
        expected=pd.DataFrame({'model':['a','b'],'fold':[1,1]})
        with self.assertRaises(ValueError):assert_complete_groups(expected,expected.iloc[:1],['model','fold'])

    def test_duplicate_metric_group_is_rejected(self):
        expected=pd.DataFrame({'model':['a','a'],'fold':[1,1]})
        with self.assertRaises(ValueError):assert_complete_groups(expected,expected,['model','fold'])

    def test_sample_reordering_is_safe_but_id_loss_is_not(self):
        frame=pd.DataFrame({'segment_id':['x','y'],'vehicle':[17,18],'proxy_capacity_ah':[100.,101.]})
        assert_sample_coverage(frame,frame.iloc[::-1])
        with self.assertRaises(ValueError):assert_sample_coverage(frame,frame.iloc[:1])

    def test_wrong_vehicle_with_correct_label_is_rejected(self):
        frame=pd.DataFrame({'segment_id':['x'],'vehicle':[17],'proxy_capacity_ah':[100.]})
        bad=frame.copy();bad.vehicle=18
        with self.assertRaises(ValueError):assert_sample_coverage(frame,bad)
