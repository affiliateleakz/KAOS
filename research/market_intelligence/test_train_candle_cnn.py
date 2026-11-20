"""Lightweight split and leakage tests; torch is optional research dependency."""
import math
import unittest
from chart_windows import windows
from train_candle_cnn import validate_and_split

BASE=1761955200000

def fixture(n=300):
    bars=[]
    for i in range(n):
        close=100+3*math.sin(i/9)+.002*i
        bars.append({"ts":BASE+i*60000,"seconds":60,"symbol":"BTC-USD",
                     "source":"synthetic","open":close-.08,
                     "high":close+.3,"low":close-.3,
                     "close":close,"volume":50+i%7})
    return windows({"seconds":60,"symbol":"BTC-USD","candles":bars},
                   lookback=20,horizon_bars=5)

class CandleCnnValidationTests(unittest.TestCase):
    def test_chronological_purging(self):
        rows,tr,va,te=validate_and_split(fixture())
        self.assertLess(rows[tr[-1]]["label_end_ms"],rows[va[0]]["decision_ms"])
        self.assertLess(rows[va[-1]]["label_end_ms"],rows[te[0]]["decision_ms"])

    def test_future_price_not_used_as_input(self):
        doc=fixture()
        for row in doc["rows"]:
            self.assertEqual(len(row["tensor_ohlcv"]),20)
            self.assertTrue(all(len(b)==5 for b in row["tensor_ohlcv"]))
            self.assertLess(row["decision_ms"],row["label_end_ms"])

    def test_duplicate_decisions_blocked(self):
        doc=fixture()
        doc["rows"][1]["decision_ms"]=doc["rows"][0]["decision_ms"]
        with self.assertRaisesRegex(ValueError,"duplicate"):
            validate_and_split(doc)

    def test_mixed_symbols_blocked(self):
        doc=fixture()
        doc["rows"][0]["symbol"]="ETH-USD"
        with self.assertRaisesRegex(ValueError,"mixed"):
            validate_and_split(doc)

    def test_bad_future_feature_blocked(self):
        doc=fixture()
        doc["rows"][0]["tensor_ohlcv"][0][0]=float("nan")
        with self.assertRaisesRegex(ValueError,"invalid chart"):
            validate_and_split(doc)

    def test_mixed_timeframe_blocked(self):
        doc=fixture()
        doc["rows"][0]["seconds"]=300
        with self.assertRaisesRegex(ValueError,"mixed"):
            validate_and_split(doc)

if __name__=="__main__":unittest.main()
