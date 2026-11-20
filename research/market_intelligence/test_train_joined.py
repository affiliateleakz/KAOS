"""Synthetic-only tests; no real market-performance claims."""
import math
import unittest
from build_dataset import build
from train_joined import evaluate

START = 1761955200000


def fixture():
    bars = []
    for i in range(350):
        close = 100.0 + 2.0 * math.sin(i / 7.0) + 0.007 * i
        bars.append({
            "symbol": "BTC-USD", "asset_class": "crypto",
            "seconds": 60, "source": "test_feed", "ts": START + i * 60_000,
            "open": close - .05, "high": close + .2, "low": close - .2,
            "close": close, "volume": 100 + i % 11,
        })
    return build({"symbol": "BTC-USD", "asset_class": "crypto",
                  "seconds": 60, "candles": bars},
                 {"observations": []}, horizons=(300,))


class JoinedTrainerTests(unittest.TestCase):
    def test_separate_horizon_training_and_purging(self):
        r = evaluate(fixture(), 300, cost_bps=10.)
        self.assertEqual(r["status"], "research_only_not_deployed")
        self.assertGreater(r["validation_first_decision_ms"], r["train_last_label_ms"])
        self.assertGreater(r["test_first_decision_ms"], r["validation_last_label_ms"])
        self.assertLessEqual(r["test_accuracy"], 1)
        self.assertGreaterEqual(r["test_accuracy"], 0)
        self.assertEqual(r["symbol"], "BTC-USD")

    def test_unavailable_horizon_rejected(self):
        with self.assertRaisesRegex(ValueError, "180 labeled"):
            evaluate(fixture(), 3600)

    def test_mixed_market_rejected(self):
        doc = fixture()
        doc["rows"][1]["symbol"] = "ETH-USD"
        with self.assertRaisesRegex(ValueError, "mixed market"):
            evaluate(doc, 300)

    def test_bad_label_time_rejected(self):
        doc = fixture()
        doc["rows"][0]["label_end_ms"] = doc["rows"][0]["decision_ms"]
        with self.assertRaisesRegex(ValueError, "invalid forward label interval"):
            evaluate(doc, 300)

    def test_future_outcome_is_not_a_feature(self):
        doc = fixture()
        self.assertNotIn("future_return_proxy", doc["rows"][0]["features"])
        report = evaluate(doc, 300)
        self.assertNotIn("future_return_proxy", report["feature_names"])


if __name__ == "__main__":
    unittest.main()
