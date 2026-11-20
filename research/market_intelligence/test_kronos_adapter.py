"""Synthetic-only smoke tests for optional Kronos research adapter."""
import unittest
from datetime import datetime, timezone
from kronos_adapter import MODEL_CONFIGS, prepare

START=1761955200000

def fixture(n=140, seconds=60):
    bars=[]
    for i in range(n):
        price=100+i*.02
        bars.append({"ts":START+i*seconds*1000,"symbol":"BTC-USD",
                     "asset_class":"crypto","seconds":seconds,"source":"synthetic",
                     "open":price,"high":price+.4,"low":price-.4,
                     "close":price+.1,"volume":100+i})
    return {"symbol":"BTC-USD","asset_class":"crypto","seconds":seconds,
            "candles":bars}

class AdapterTests(unittest.TestCase):
    def test_ready_format_and_no_future_prices(self):
        p=prepare(fixture(),lookback=128,pred_len=5)
        self.assertEqual(p["status"],"research_input_ready_not_forecast")
        self.assertEqual(len(p["ohlcv"]),128)
        self.assertEqual(len(p["future_timestamps_utc"]),5)
        self.assertEqual(p["model_id"],MODEL_CONFIGS["mini"]["model"])
        expected=START+140*60000
        self.assertEqual(p["decision_ms"],expected)
        self.assertEqual(
            datetime.fromisoformat(p["future_timestamps_utc"][0]).timestamp()*1000,
            expected)
        self.assertNotIn("future_ohlcv",p)

    def test_no_future_price_contamination(self):
        base=fixture(140)
        p1=prepare(base,lookback=128)
        base["candles"].append({"ts":START+140*60000,
            "symbol":"BTC-USD","asset_class":"crypto","seconds":60,
            "source":"synthetic","open":900,"high":1000,"low":800,
            "close":999,"volume":50})
        # Changed cutoff changes context; slicing a historical export at the
        # earlier decision point must produce the exact same input.
        base["candles"]=base["candles"][:-1]
        p2=prepare(base,lookback=128)
        self.assertEqual(p1["ohlcv"],p2["ohlcv"])

    def test_gap_fails(self):
        data=fixture()
        data["candles"][-10]["ts"]+=60000
        with self.assertRaisesRegex(ValueError,"duplicate|missing"):
            prepare(data)

    def test_mixed_asset_fails(self):
        data=fixture()
        data["candles"][-2]["symbol"]="ETH-USD"
        with self.assertRaisesRegex(ValueError,"mixed"):
            prepare(data)

    def test_variant_context_limit(self):
        data=fixture()
        with self.assertRaisesRegex(ValueError,"outside supported context"):
            prepare(data,lookback=513,model_name="small")

    def test_invalid_prices_fail(self):
        data=fixture()
        data["candles"][-1]["close"]=-1
        with self.assertRaisesRegex(ValueError,"inconsistent"):
            prepare(data)

    def test_forecast_not_run_by_preparer(self):
        p=prepare(fixture())
        self.assertNotIn("forecast_ohlcv",p)
        self.assertNotIn("verified_accuracy",p)

if __name__=="__main__":
    unittest.main()
