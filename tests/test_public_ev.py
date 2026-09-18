import unittest
import numpy as np
import pandas as pd
from research.public_battery.ev_experiment import capacity_proxy, segment_ids, session_features, split_for, extract_sessions

class PublicEVTests(unittest.TestCase):
    def test_known_capacity(self):
        self.assertAlmostEqual(capacity_proxy(np.array([0,1800]), np.array([-40,-40]), np.array([20,40])),100)

    def test_gap_and_duplicate_split(self):
        t = pd.Series(pd.to_datetime(['2020-01-01 00:00:00','2020-01-01 00:00:10','2020-01-01 00:00:21','2020-01-01 00:00:21']))
        self.assertEqual(segment_ids(t).tolist(), [1,1,2,3])

    def test_prefix_ignores_future(self):
        g = pd.DataFrame({'time':pd.date_range('2020',periods=181,freq='10s'),'soc':np.linspace(20,40,181),
            'voltage':350.,'current':-40.,'vmax':3.9,'vmin':3.8,'tmax':30.,'tmin':29.})
        before = session_features(g)
        g.loc[61:, ['voltage','current','vmax','tmax']] = 9999
        self.assertEqual(before, session_features(g))

    def test_entity_split(self):
        self.assertEqual([split_for(i) for i in [1,14,15,16,17,20]], ['train','train','validation','validation','test','test'])

    def test_invalid_row_prevents_bridging(self):
        g = pd.DataFrame({'record_time':pd.date_range('2020',periods=181,freq='10s').strftime('%Y%m%d%H%M%S'),
            'soc':np.linspace(20,60,181),'voltage':350.,'current':-40.,'vmax':3.9,'vmin':3.8,'tmax':30.,'tmin':29.})
        self.assertEqual(len(extract_sessions(g,1)[0]),1)
        g.loc[90,'voltage'] = np.nan
        self.assertEqual(len(extract_sessions(g,1)[0]),0)

    def test_invalid_timestamp_prevents_bridging(self):
        g = pd.DataFrame({'record_time':pd.date_range('2020',periods=361,freq='5s').strftime('%Y%m%d%H%M%S'),
            'soc':np.linspace(20,60,361),'voltage':350.,'current':-40.,'vmax':3.9,'vmin':3.8,'tmax':30.,'tmin':29.})
        g.loc[180,'record_time'] = 'invalid'
        self.assertEqual(len(extract_sessions(g,1)[0]),0)
