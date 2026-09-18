import unittest
from pathlib import Path
import pandas as pd
from backend.v03.bms_validate import validate
from backend.services.assessment import bms

BASE = Path(__file__).resolve().parents[1] / 'data/sample/bms/synthetic_fixtures'

class BMSFeedbackTests(unittest.TestCase):
    def setUp(self):
        self.t = pd.read_csv(BASE / 'good_telemetry.csv')
        self.m = pd.read_csv(BASE / 'metadata.csv')

    def test_unchecked_fields_cannot_look_fully_validated(self):
        self.t['batteryvoltage'] = 'INVALID_ARRAY'
        self.t['fault_code'] = 'CRITICAL'
        r = validate(self.t, self.m)
        self.assertTrue(r['summary']['schema_ready'])  # Existing core contract
        self.assertFalse(r['summary']['all_supplied_fields_validated'])
        self.assertEqual(r['summary']['unvalidated_telemetry_columns'], ['batteryvoltage', 'fault_code'])
        self.assertTrue(r['summary']['warnings_need_review'])
        self.assertIn('unvalidated_column', set(r['issues'].code))

    def test_standard_input_has_explicit_scope(self):
        r = validate(self.t, self.m)
        self.assertTrue(r['summary']['all_supplied_fields_validated'])
        self.assertFalse(r['summary']['model_inference_performed'])

    def test_extra_metadata_is_reported(self):
        self.m['insulation_resistance'] = 'bad'
        r = validate(self.t, self.m)
        self.assertFalse(r['summary']['all_supplied_fields_validated'])
        self.assertEqual(r['summary']['unvalidated_metadata_columns'], ['insulation_resistance'])

    def test_duplicate_csv_header_rejected_instead_of_mangled(self):
        text = self.t.to_csv(index=False).replace('pack_voltage,', 'SOC,', 1)
        with self.assertRaisesRegex(ValueError, 'Duplicate CSV columns'):
            bms({'telemetry_csv': text, 'metadata_csv': self.m.to_csv(index=False)})

    def test_optional_mileage_numeric_is_normalized(self):
        self.t['mileage'] = self.t.mileage.astype(str)
        r = validate(self.t, self.m)
        self.assertTrue(pd.api.types.is_numeric_dtype(r['accepted'].mileage))

    def test_leading_blank_lines_do_not_hide_duplicate_header(self):
        text = '   \n\t\n' + self.t.to_csv(index=False).replace('pack_voltage,', 'SOC,', 1)
        with self.assertRaisesRegex(ValueError, 'Duplicate CSV columns'):
            bms({'telemetry_csv': text, 'metadata_csv': self.m.to_csv(index=False)})
