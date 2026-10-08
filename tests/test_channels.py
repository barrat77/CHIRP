import unittest
from channels import read_csv, export_csv, validate


class ChannelTests(unittest.TestCase):
    def test_roundtrip_preserves_codes_quotes_and_columns(self):
        sample = b'Location,Frequency,DtcsCode,Comment,Extra\r\n1,146.520000,023,"Hello, world",custom\r\n'
        headers, rows = read_csv(sample)
        self.assertEqual(read_csv(export_csv(headers, rows)), (headers, rows))
        self.assertEqual(rows[0]['DtcsCode'], '023')

    def test_bad_input(self):
        for sample in [b'', b'Name,Frequency\nA,146\n', b'Location,Frequency\n1\n']:
            with self.assertRaises(ValueError):
                read_csv(sample)

    def test_duplicate_locations_and_nonfinite_frequencies(self):
        rows = [{'Location': '1', 'Frequency': '146.52'},
                {'Location': '1', 'Frequency': 'NaN'}]
        self.assertEqual(len(validate(rows)), 2)
        with self.assertRaises(ValueError):
            export_csv(['Location', 'Frequency'], rows)

    def test_bom_and_comments(self):
        headers, rows = read_csv(b'\xef\xbb\xbf# example\nLocation,Frequency\n0,146.52\n')
        self.assertEqual(rows[0]['Location'], '0')


if __name__ == '__main__':
    unittest.main()
