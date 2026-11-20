"""Offline tests; never contact TradingView."""
import unittest
from datetime import datetime, timezone
from tvdatafeed_adapter import normalize_history

BASE=1761955200000
def sample(n=8):
    return [{"timestamp":datetime.fromtimestamp((BASE+i*60000)/1000,timezone.utc),
             "open":100+i,"high":101+i,"low":99+i,
             "close":100.5+i,"volume":100+i} for i in range(n)]
def build(records,now=BASE+8*60000,**kw):
    return normalize_history(records,symbol="BTCUSDT",exchange="BINANCE",
              asset_class="crypto",seconds=60,observed_at_ms=now,**kw)

class AdapterTests(unittest.TestCase):
    def test_closed_bars_and_metadata(self):
        r=build(sample())
        self.assertEqual(r["closed_bar_count"],8)
        self.assertEqual(r["noncontiguous_intervals"],0)
        self.assertEqual(r["source"],"tradingview_unofficial")
        self.assertTrue(all("seconds" in c for c in r["candles"]))
    def test_partial_last_bar_discarded(self):
        r=build(sample(),now=BASE+7*60000+10000)
        self.assertEqual(r["closed_bar_count"],7)
    def test_naive_timestamp_rejected(self):
        rows=sample()
        rows[0]["timestamp"]=rows[0]["timestamp"].replace(tzinfo=None)
        with self.assertRaisesRegex(ValueError,"timezone-naive"):
            build(rows)
    def test_duplicate_bar_rejected(self):
        rows=sample()
        rows[4]["timestamp"]=rows[3]["timestamp"]
        with self.assertRaisesRegex(ValueError,"duplicate"):
            build(rows)
    def test_gap_reported_not_filled(self):
        rows=sample()
        rows.pop(3)
        r=build(rows)
        self.assertEqual(r["closed_bar_count"],7)
        self.assertEqual(r["noncontiguous_intervals"],1)
    def test_inconsistent_ohlcv_rejected(self):
        rows=sample()
        rows[3]["high"]=1
        with self.assertRaisesRegex(ValueError,"inconsistent"):
            build(rows)
    def test_subminute_rejected(self):
        with self.assertRaisesRegex(ValueError,"unsupported"):
            normalize_history(sample(),symbol="BTCUSDT",exchange="BINANCE",
              asset_class="crypto",seconds=5,observed_at_ms=BASE+8*60000)
    def test_future_prices_not_used(self):
        rows=sample()
        rows.append({"timestamp":datetime.fromtimestamp((BASE+8*60000)/1000,timezone.utc),
                     "open":900,"high":1000,"low":800,"close":990,"volume":999})
        r=build(rows)
        self.assertEqual(r["candles"],build(sample())["candles"])
if __name__=="__main__":
    unittest.main()
