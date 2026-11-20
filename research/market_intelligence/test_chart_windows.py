"""Deterministic fixtures for independent candle-window learning inputs."""
import unittest
from chart_windows import windows


def archive(count=70):
    base = 1761955200000
    return {"symbol": "BTC-USD", "seconds": 60, "candles": [
        {"ts": base+60000*i, "seconds": 60, "symbol": "BTC-USD",
         "source": "coinbase_test", "open": 100+i*.2,
         "high": 101+i*.2, "low": 99+i*.2,
         "close": 100.1+i*.2, "volume": (i % 6) * 10}
        for i in range(count)
    ]}


class WindowTests(unittest.TestCase):
    def test_shape_and_future_is_not_part_of_input(self):
        result = windows(archive(), lookback=12, horizon_bars=5)
        first = result["rows"][0]
        self.assertEqual(result["feature_shape"], [12, 5])
        self.assertEqual(len(first["tensor_ohlcv"]), 12)
        self.assertTrue(all(len(row) == 5 for row in first["tensor_ohlcv"]))
        self.assertEqual(first["label_up"], 1)
        self.assertLess(first["decision_ms"], first["label_end_ms"])

    def test_future_price_mutation_cannot_change_input_tensor(self):
        old = archive()
        first = windows(old, lookback=12, horizon_bars=5)["rows"][0]
        later = archive()
        later["candles"][16]["close"] = later["candles"][16]["open"]-.5
        future = windows(later, lookback=12, horizon_bars=5)["rows"][0]
        self.assertEqual(first["tensor_ohlcv"], future["tensor_ohlcv"])

    def test_missing_candle_discards_contaminated_windows(self):
        data = archive()
        data["candles"].pop(30)
        result = windows(data, lookback=12, horizon_bars=5)
        affected = 1761955200000 + 31*60000
        self.assertFalse(any(r["decision_ms"] == affected for r in result["rows"]))

    def test_mixed_source_rejected(self):
        data = archive()
        data["candles"][3]["source"] = "other"
        with self.assertRaisesRegex(ValueError, "mixed"):
            windows(data)

    def test_duplicate_candle_rejected(self):
        data = archive()
        data["candles"][4]["ts"] = data["candles"][3]["ts"]
        with self.assertRaisesRegex(ValueError, "duplicate"):
            windows(data)

    def test_not_enough_candles_rejected(self):
        with self.assertRaisesRegex(ValueError, "not enough"):
            windows(archive(10))


if __name__ == "__main__":
    unittest.main()
