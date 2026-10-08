import unittest
from unittest.mock import patch, Mock
from channels import DEFAULTS, append_channels, export_csv, read_csv
from repeaters import convert_results, fetch_repeaters


def listing(**changes):
    item = {'State': 'Virginia', 'County': 'Loudoun', 'Frequency': '462.550',
            'Input Freq': '467.550', 'PL': '100.0', 'TSQ': 'CSQ', 'Use': 'PRIVATE',
            'Operational Status': 'On-air', 'Callsign': 'TEST'}
    item.update(changes)
    return item


class RepeaterTests(unittest.TestCase):
    def test_county_filter_access_and_offset(self):
        rows, skipped = convert_results([listing(), listing(County='Fairfax')], 'Virginia', 'Loudoun County')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['Offset'], '5.000000')
        self.assertEqual(rows[0]['Tone'], 'Tone')
        self.assertIn('PRIVATE', rows[0]['Comment'])
        self.assertFalse(skipped)

    def test_unsupported_tone_and_wrong_pair_are_skipped(self):
        rows, skipped = convert_results([listing(PL='Restricted'), listing(Frequency='146.52')], 'Virginia', 'Loudoun')
        self.assertEqual(rows, [])
        self.assertEqual(len(skipped), 2)

    def test_different_transmit_receive_tones(self):
        rows, _ = convert_results([listing(PL='D023', TSQ='100.0')], 'Virginia', 'Loudoun')
        self.assertEqual(rows[0]['Tone'], 'Cross')
        self.assertEqual(rows[0]['CrossMode'], 'DTCS->Tone')
        self.assertEqual(rows[0]['DtcsCode'], '023')

    def test_all_52_defaults_preserved_and_additions_deduplicated(self):
        base = [dict(DEFAULTS, Location=str(i), Name=f'BASE{i}') for i in range(1, 53)]
        found, _ = convert_results([listing()], 'Virginia', 'Loudoun')
        merged = append_channels(base, found + found, list(DEFAULTS))
        self.assertEqual(merged[:52], base)
        self.assertEqual(len(merged), 53)
        self.assertEqual(merged[-1]['Location'], '53')
        _, exported = read_csv(export_csv(list(DEFAULTS), merged))
        self.assertEqual(exported[:52], base)

    @patch('repeaters.requests.get')
    def test_scoped_authenticated_request(self, get):
        get.return_value = Mock(status_code=200)
        get.return_value.json.return_value = {'results': [listing()]}
        rows = fetch_repeaters('Virginia', 'Loudoun', 'rbuapp_test', 'CHIRP/1.0 contact@example.com')
        self.assertEqual(len(rows), 1)
        args = get.call_args.kwargs
        self.assertEqual(args['params'], {'state_id': '51', 'county': 'loudoun', 'stype': 'gmrs'})
        self.assertFalse(args['allow_redirects'])

    @patch('repeaters.requests.get')
    def test_denial_and_rate_limit_do_not_retry(self, get):
        for status in (403, 429):
            get.reset_mock()
            get.return_value = Mock(status_code=status)
            with self.assertRaises(ValueError):
                fetch_repeaters('Virginia', 'Loudoun', 'rbuapp_test', 'CHIRP/1.0 contact@example.com')
            self.assertEqual(get.call_count, 1)
