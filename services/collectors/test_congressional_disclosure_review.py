import tempfile
import unittest
from pathlib import Path
from datetime import date
from congressional_disclosure_review import inspect_row,inspect_file

TODAY=date(2026,10,16)

class CongressionalReviewTests(unittest.TestCase):
    def row(self,**changes):
        row={'report_id':'12345','chamber':'house','member':'Sample Member','ticker':'AAPL',
             'asset_description':'Sample company shares','transaction_type':'purchase',
             'transaction_date':'2026-09-01','filing_date':'2026-10-01',
             'amount_range':'$1,001–$15,000',
             'source_url':'https://disclosures-clerk.house.gov/FinancialDisclosure'}
        row.update(changes)
        return row
    def test_valid_local_only(self):
        d=inspect_row(self.row(),today=TODAY)
        self.assertTrue(d['valid'])
        self.assertEqual(d['review']['disclosure_lag_days'],30)
        self.assertFalse(d['permitted_for_paid_member_distribution'])
        self.assertFalse(d['verified_against_original'])
    def test_reject_unofficial_urls(self):
        self.assertIn('not_an_official_source_url',inspect_row(self.row(source_url='https://disclosures-clerk.house.gov.evil.com/x'),today=TODAY)['errors'])
        self.assertIn('not_an_official_source_url',inspect_row(self.row(source_url='http://disclosures-clerk.house.gov/'),today=TODAY)['errors'])
    def test_future_and_reversed_dates(self):
        self.assertIn('filing_predates_transaction',inspect_row(self.row(transaction_date='2026-10-01',filing_date='2026-09-01'),today=TODAY)['errors'])
    def test_no_inferred_symbol(self):
        d=inspect_row(self.row(ticker=''),today=TODAY)
        self.assertTrue(d['valid']);self.assertEqual(d['review']['ticker'],'')
    def test_csv_import(self):
        from csv import DictWriter
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'test.csv';row=self.row()
            with path.open('w',newline='') as f:
                w=DictWriter(f,fieldnames=list(row));w.writeheader();w.writerow(row)
            report=inspect_file(path,today=TODAY)
            self.assertEqual(report['valid_rows'],1)
            self.assertFalse(report['commercial_republication'])
if __name__=='__main__':unittest.main()
