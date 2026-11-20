"""Pure validation checks for authenticated research candle ingest."""
import os
import unittest
from unittest.mock import patch
from fastapi import HTTPException
from routes_candle_recording import validate_bars,require_collector

BASE=1761955200000
def item(**kwargs):
    row={"symbol":"BTC-USD","asset_class":"crypto",
         "source":"coinbase_exchange_public","seconds":60,"ts":BASE,
         "open":100.,"high":101.,"low":99.,"close":100.5,"volume":30.}
    row.update(kwargs)
    return row

class CandleIngestTests(unittest.TestCase):
    def test_normalized_immutable_record_id(self):
        records=validate_bars([item()],BASE+2*60000)
        self.assertEqual(records[0]["_id"],f"coinbase_exchange_public:crypto:BTC-USD:60:{BASE}")
    def test_reject_wrong_provider_asset(self):
        with self.assertRaisesRegex(ValueError,"Coinbase"):
            validate_bars([item(asset_class="stock")],BASE+2*60000)
    def test_refuse_incomplete_bar(self):
        with self.assertRaisesRegex(ValueError,"Invalid"):
            validate_bars([item()],BASE+1000)
    def test_reject_duplicate_bar_in_batch(self):
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            validate_bars([item(),item()],BASE+2*60000)
    def test_conflicting_ohlc_fails(self):
        with self.assertRaisesRegex(ValueError,"Invalid OHLCV"):
            validate_bars([item(high=1)],BASE+2*60000)
    def test_collector_token_fail_closed(self):
        with patch.dict(os.environ,{"KAOS_COLLECTOR_KEY":"known"}):
            with self.assertRaises(HTTPException):
                require_collector("wrong")
            require_collector("known")
    def test_unconfigured_token_fails_closed(self):
        with patch.dict(os.environ,{"KAOS_COLLECTOR_KEY":""}):
            with self.assertRaises(HTTPException):
                require_collector("anything")
if __name__=="__main__":
    unittest.main()
