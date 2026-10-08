import tempfile
import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest
from channels import DEFAULTS, export_csv


class AppTests(unittest.TestCase):
    def test_default_export_and_addition(self):
        with tempfile.TemporaryDirectory() as folder:
            fixture = Path(folder) / 'defaults.csv'
            base = [dict(DEFAULTS, Location=str(i), Name=f'BASE{i}') for i in range(1, 53)]
            fixture.write_bytes(export_csv(list(DEFAULTS), base))
            code = Path('app.py').read_text(encoding='utf-8-sig')
            code = code.replace("BASE_FILE = ROOT / 'local_data' / 'default_52.csv'", f'BASE_FILE = Path({str(fixture)!r})')
            app = AppTest.from_string(code, default_timeout=30).run()
            self.assertFalse(app.exception)
            name = next(t for t in app.text_input if t.label == 'Channel name')
            name.set_value('NEW')
            next(b for b in app.button if b.label == 'Add channel').click()
            app.run()
            self.assertFalse(app.exception)
            query = next(t for t in app.text_input if t.label.startswith('Filter additional'))
            query.set_value('NO MATCH').run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.dataframe[-1].value), 52)
            query.set_value('NEW').run()
            self.assertEqual(len(app.dataframe[-1].value), 53)
            self.assertEqual(app.dataframe[-1].value.iloc[-1]['Location'], '53')
            self.assertEqual(fixture.read_bytes(), export_csv(list(DEFAULTS), base))
