import unittest
import numpy as np
import pandas as pd
from research.public_battery import validation_v2 as v


class ValidationV2Tests(unittest.TestCase):
    def frame(self):
        rows = []
        for vehicle in range(1, 21):
            rows.append(dict(vehicle=vehicle, split='train' if vehicle <= 14 else 'validation' if vehicle <= 16 else 'test',
                             start_local_unspecified='2020-01-01', proxy_capacity_ah=100.,
                             **{f: float(vehicle) for f in v.FEATURES}))
        return pd.DataFrame(rows)

    def test_reject_wrong_vehicle_split(self):
        d = self.frame()
        d.loc[0, 'split'] = 'test'
        with self.assertRaises(ValueError):
            v.validate_data(d)

    def test_reject_duplicate_sessions_and_infinity(self):
        d = self.frame()
        with self.assertRaises(ValueError):
            v.validate_data(pd.concat([d, d.iloc[:1]]))
        d.loc[0, v.FEATURES[0]] = np.inf
        with self.assertRaises(ValueError):
            v.validate_data(d)

    def test_train_folds_exclude_external_holdouts(self):
        d = self.frame()
        folds = list(v.training_folds(d))
        seen = set()
        for tr, va in folds:
            self.assertFalse(set(tr.vehicle) & set(va.vehicle))
            self.assertTrue(set(tr.vehicle) | set(va.vehicle) <= set(range(1, 15)))
            seen.update(va.vehicle)
        self.assertEqual(seen, set(range(1, 15)))

    def test_vehicle_equal_weight_not_row_weight(self):
        result = v.scores([0, 0, 0, 0], [0, 0, 0, 8], [1, 1, 1, 2])
        self.assertEqual(result['mae_ah'], 2.)
        self.assertEqual(result['vehicle_macro_mae_ah'], 4.)

    def test_cluster_interval_preserves_vehicle_unit(self):
        lo, hi = v.cluster_interval([1., 9.])
        self.assertEqual((lo, hi), (1., 9.))
        self.assertEqual(v.cluster_interval([3., 3., 3.]), (3., 3.))

    def test_perturbation_uses_train_statistics_without_mutation(self):
        train = pd.DataFrame({'a': [1., 3.], 'b': [10., 10.]})
        test = pd.DataFrame({'a': [100., 200.], 'b': [90., 80.]})
        before = test.copy()
        changed = v.stress_input(train, test, 'missing', level=1.)
        np.testing.assert_allclose(changed, [[2., 10.], [2., 10.]])
        pd.testing.assert_frame_equal(test, before)
        pd.testing.assert_frame_equal(v.stress_input(train, test, 'noise', level=0.), test)


if __name__ == '__main__':
    unittest.main()
