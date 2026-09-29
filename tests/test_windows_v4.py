import unittest

import numpy as np
import pandas as pd

from research.public_battery.ev_experiment import FEATURES, extract_sessions, session_features
from research.public_battery.windows_v4 import WINDOWS, QUALITY_COLUMNS, extract_vehicle, window_features


class WindowV4Tests(unittest.TestCase):
    def group(self):
        return pd.DataFrame({'time': pd.date_range('2020', periods=181, freq='10s'),
                             'soc': np.linspace(20, 40, 181), 'voltage': np.linspace(320, 350, 181),
                             'current': -40., 'vmax': 3.9, 'vmin': 3.8, 'tmax': 30., 'tmin': 29.})

    def raw(self, group):
        frame = group.drop(columns=['time']).copy()
        frame['record_time'] = group.time.dt.strftime('%Y%m%d%H%M%S')
        return frame

    def test_every_prefix_ignores_all_later_signal_values(self):
        for window_s in WINDOWS:
            with self.subTest(window_s=window_s):
                group = self.group()
                before = window_features(group, window_s)
                later = (group.time - group.time.iloc[0]).dt.total_seconds() > window_s
                group.loc[later, ['soc', 'voltage', 'current', 'vmax', 'vmin', 'tmax', 'tmin']] = 99999
                self.assertEqual(before, window_features(group, window_s))

    def test_constant_current_formula_and_variable_step_trapezoid(self):
        for window_s in WINDOWS:
            with self.subTest(window_s=window_s):
                result = window_features(self.group(), window_s)
                self.assertAlmostEqual(result['formula_capacity_ah'], 100.)
                self.assertAlmostEqual(result['prefix_ah'], 40 * window_s / 3600)
        group = self.group().iloc[[0, 3, 12]].copy()
        group['current'] = [-20., -40., -60.]
        expected = (30 * 30 + 50 * 90) / 3600
        self.assertAlmostEqual(window_features(group, 120)['prefix_ah'], expected)

    def test_zero_soc_gain_yields_missing_formula_not_infinity(self):
        group = self.group()
        group['soc'] = 20.
        result = window_features(group, 120)
        self.assertTrue(np.isnan(result['formula_capacity_ah']))
        self.assertEqual(result['prefix_soc_gain_pct'], 0.)
        self.assertTrue(np.isfinite([result[name] for name in FEATURES]).all())

    def test_600_second_features_equal_frozen_implementation(self):
        group = self.group()
        new = window_features(group, 600)
        old = session_features(group)
        np.testing.assert_allclose([new[f] for f in FEATURES], [old[f] for f in FEATURES], atol=0, rtol=0)
        self.assertFalse(set(QUALITY_COLUMNS) & set(FEATURES))

    def test_voltage_normalized_positions_and_no_future_endpoint(self):
        group = self.group()
        result = window_features(group, 120)
        self.assertAlmostEqual(result['voltage_60'], 320.2)
        self.assertAlmostEqual(result['voltage_300'], 321.)
        self.assertAlmostEqual(result['voltage_600'], 322.)
        group = group.drop(index=12)
        result = window_features(group, 120)
        self.assertAlmostEqual(result['voltage_600'], 320 + 110 / 60)
        self.assertEqual(result['prefix_duration_s'], 110)

    def test_retained_cohort_labels_match_original_and_invalid_barriers(self):
        raw = self.raw(self.group())
        original, _ = extract_sessions(raw, 1)
        actual = extract_vehicle(raw, 1)
        self.assertEqual(len(actual), len(original) * 3)
        self.assertEqual(actual.window_s.tolist(), list(WINDOWS))
        np.testing.assert_allclose(actual.proxy_capacity_ah, [original[0]['proxy_capacity_ah']] * 3)
        self.assertEqual(actual.segment_id.nunique(), 1)
        raw.loc[90, 'voltage'] = np.nan
        self.assertEqual(extract_sessions(raw, 1)[0], [])
        self.assertTrue(extract_vehicle(raw, 1).empty)


if __name__ == '__main__':
    unittest.main()
