import unittest
from quick_search import parse_candidates, quick_local_search


class QuickSearchTests(unittest.TestCase):
    def test_listing_extraction_and_receive_only(self):
        rows = parse_candidates('<p>WARRENTON 725 - Most of NOVA - rx462.725/tx467.725</p>'
                                '<p>WARRENTON 725 - duplicate - rx462.725/tx467.725</p>'
                                '<script>WINCHESTER 550 - fake - rx462.550/tx467.550</script>', 'Loudoun')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['Name'], 'WARRENTON 725')
        self.assertEqual(rows[0]['Duplex'], 'off')
        self.assertIn('tones/access unconfirmed', rows[0]['Comment'])

    def test_unsupported_region(self):
        with self.assertRaises(ValueError):
            quick_local_search('California', 'Loudoun')
