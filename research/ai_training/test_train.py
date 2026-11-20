"""Synthetic fixture tests only; not real market validation."""
import unittest
import numpy as np
from train import prepare, purged_splits, train


def fixture(n=280):
    rng = np.random.default_rng(123)
    close = 100 * np.exp(np.cumsum(rng.normal(0, .004, n)))
    rows = []
    for i in range(n):
        o = float(close[i-1]) if i else 100.
        c = float(close[i])
        rows.append({"symbol": "BTC-USD", "source": "fixture", "seconds": 60,
                     "ts": 1700000000000+i*60000, "open": o,
                     "high": max(o, c)*1.001, "low": min(o, c)*.999,
                     "close": c, "volume": 10.})
    return {"symbol": "BTC-USD", "seconds": 60, "candles": rows}


class ResearchTests(unittest.TestCase):
    def test_contiguous_preparation(self):
        X, y, entry, ending, dt, et = prepare(fixture(), 3)
        self.assertEqual(X.shape[1], 11)
        self.assertTrue(np.all(et > dt))

    def test_future_label_boundary_is_purged(self):
        X, y, entry, ending, dt, et = prepare(fixture(), 5)
        a, b, c = purged_splits(dt, et)
        self.assertLess(et[a[-1]], dt[b[0]])
        self.assertLess(et[b[-1]], dt[c[0]])

    def test_gaps_are_not_filled(self):
        f = fixture()
        f["candles"][110]["ts"] += 1000
        self.assertLess(len(prepare(f)[1]), len(prepare(fixture())[1]))

    def test_mixed_source_rejected(self):
        f = fixture()
        f["candles"][3]["source"] = "other"
        with self.assertRaisesRegex(ValueError, "mixed source"):
            prepare(f)

    def test_end_to_end_research(self):
        result = train(fixture())
        self.assertEqual(result["status"], "research_only_not_deployed")
        self.assertGreater(result["split_counts"]["test"], 20)


if __name__ == "__main__":
    unittest.main()
