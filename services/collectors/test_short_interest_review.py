import unittest
import tempfile
from datetime import date
from pathlib import Path
from short_interest_review import row_metrics,review_csv

TODAY=date(2026,10,16)
def row(**kwargs):
    d={'symbol':'GME','as_of':'2026-10-01','published_at':'2026-10-08',
       'short_shares':'20000000','float_shares':'100000000','avg_daily_volume':'4000000',
       'source_url':'https://www.finra.org/'}
    d.update(kwargs);return d

class Tests(unittest.TestCase):
    def test_review_conditions_not_probability(self):
        o=row_metrics(row(),today=TODAY)
        self.assertEqual(o['screen_label'],'review_conditions')
        self.assertEqual(o['short_float_percent'],20)
        self.assertEqual(o['days_to_cover'],5)
        self.assertEqual(o['redistribution'],'local_review_only')
    def test_age_stale(self):
        self.assertEqual(row_metrics(row(published_at='2026-09-12',as_of='2026-09-01'),today=TODAY)['screen_label'],'stale_publication')
    def test_bad_dates(self):
        with self.assertRaises(ValueError):row_metrics(row(published_at='2026-09-01'),today=TODAY)
    def test_invalid_float(self):
        with self.assertRaises(ValueError):row_metrics(row(float_shares='0'),today=TODAY)
    def test_can_exceed_float_with_warning(self):
        r=row_metrics(row(float_shares='10000000'),today=TODAY)
        self.assertEqual(r['short_float_percent'],200)
        self.assertTrue(r['short_exceeds_estimated_float'])
    def test_stale_snapshot_not_recommended(self):
        r=row_metrics(row(as_of='2026-08-01'),today=TODAY)
        self.assertEqual(r['screen_label'],'stale_snapshot')
    def test_csv(self):
        with tempfile.TemporaryDirectory() as td:
            file=Path(td)/'positions.csv'
            file.write_text('symbol,as_of,published_at,short_shares,float_shares,avg_daily_volume,source_url\nGME,2026-10-01,2026-10-08,20000000,100000000,4000000,https://www.finra.org/\n')
            self.assertEqual(len(review_csv(file,today=TODAY)),1)

if __name__=='__main__':unittest.main()
