import unittest
import numpy as np
import pandas as pd
from research.public_battery.upgrade_v4 import error_metrics, bin_edges, assign_bins, nested_vehicle_sets, choose_quality_gate, check_windows


class ResearchV4Tests(unittest.TestCase):
    def test_metrics_include_direction_and_tail(self):
        m = error_metrics([1, 2, 3], [2, 0, 4], ['a', 'a', 'b'])
        self.assertAlmostEqual(m['mae_ah'], 4 / 3)
        self.assertAlmostEqual(m['bias_ah'], 0)
        self.assertAlmostEqual(m['vehicle_macro_mae_ah'], 1.25)
        self.assertEqual(m['max_ae_ah'], 2)

    def test_bins_train_only_and_cover_outliers(self):
        edges = bin_edges(pd.Series([0, 0, 3, 6, 9, 9]))
        actual = assign_bins(pd.Series([-100, 0, 5, 100]), edges)
        self.assertFalse(actual.isna().any())
        self.assertEqual(len(edges), len(set(edges)))

    def test_constant_bins(self):
        e = bin_edges(pd.Series([2] * 9))
        self.assertFalse(assign_bins(pd.Series([1, 2, 3]), e).isna().any())

    def test_learning_curve_nested_training_only(self):
        rows = nested_vehicle_sets(list(range(1, 15)), [4, 8, 14], [17, 42])
        for seed in [17, 42]:
            sets = [set(x['vehicles']) for x in rows if x['repeat_seed'] == seed]
            self.assertTrue(sets[0] < sets[1] < sets[2])
            self.assertFalse(sets[-1] & {15, 16, 17, 18, 19, 20})
        self.assertEqual(rows, nested_vehicle_sets(list(range(1, 15)), [4, 8, 14], [17, 42]))

    def test_quality_choice_rejects_test_input(self):
        t = pd.DataFrame({'split': ['test'], 'threshold': [0], 'coverage': [1.], 'minimum_vehicle_coverage': [1.], 'vehicle_macro_mae_ah': [2.]})
        with self.assertRaises(ValueError):
            choose_quality_gate(t)

    def test_quality_choice_enforces_coverage_and_tie(self):
        t = pd.DataFrame({'split': ['validation'] * 3, 'threshold': [0, 1, 5], 'coverage': [1., .9, .3], 'minimum_vehicle_coverage': [1., .8, .2], 'vehicle_macro_mae_ah': [3., 2., .1]})
        self.assertEqual(choose_quality_gate(t), 1)

    def test_windows_reject_changed_targets(self):
        x = pd.DataFrame({'window_s': [120, 300, 600], 'segment_id': ['a'] * 3, 'proxy_capacity_ah': [2., 2., 3.]})
        with self.assertRaises(ValueError):
            check_windows(x)

    def test_windows_reject_different_cohorts(self):
        x = pd.DataFrame({'window_s': [120, 300, 600], 'segment_id': ['a', 'a', 'b'], 'proxy_capacity_ah': [2., 2., 2.]})
        with self.assertRaises(ValueError):
            check_windows(x)


if __name__ == '__main__':
    unittest.main()
