"""Synthetic offline regression tests: no real-money performance claims."""
import unittest
from datetime import datetime, timezone, timedelta
from build_dataset import build


BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)
MS = int(BASE.timestamp()*1000)


def candles(n=100):
    return {"symbol": "BTC-USD", "asset_class": "crypto", "seconds": 60,
            "candles": [
                {"symbol": "BTC-USD", "asset_class": "crypto", "seconds": 60,
                 "source": "coinbase_exchange_public_candles", "ts": MS+i*60000,
                 "open": 100+i*.1, "high": 101+i*.1, "low": 99+i*.1,
                 "close": 100.1+i*.1, "volume": 10}
                for i in range(n)
            ]}


def observed(source, i, event_id="a"):
    return {"asset": "BTC-USD", "asset_class": "crypto", "source": source,
            "event_id": event_id, "direction": "neutral",
            "observed_at": (BASE+timedelta(minutes=i)).isoformat(),
            "published_at": (BASE+timedelta(minutes=max(0, i-60))).isoformat()}


class IntelligencePipelineTests(unittest.TestCase):
    def test_future_observation_never_leaks_into_past(self):
        results = build(candles(), {"observations": [observed("news", 80)]}, (300,))
        old = next(r for r in results["rows"] if r["decision_ms"] == MS+31*60000)
        later = next(r for r in results["rows"] if r["decision_ms"] == MS+81*60000)
        self.assertEqual(old["features"]["news_observations_last_hour"], 0)
        self.assertEqual(later["features"]["news_observations_last_hour"], 1)

    def test_future_published_time_is_not_used_to_backdate(self):
        event = observed("social", 80)
        event["published_at"] = BASE.isoformat()
        results = build(candles(), {"observations": [event]}, (300,))
        old = next(r for r in results["rows"] if r["decision_ms"] == MS+31*60000)
        self.assertEqual(old["features"]["social_observations_last_hour"], 0)

    def test_missing_intrabar_horizon_fails(self):
        with self.assertRaisesRegex(ValueError, "horizons"):
            build(candles(), {"observations": []}, (5,))

    def test_contiguous_requirement_skips_gap(self):
        source = candles()
        source["candles"].pop(55)
        results = build(source, {"observations": []}, (300,))
        self.assertFalse(any(MS+55*60000 <= r["decision_ms"] < MS+75*60000 for r in results["rows"]))

    def test_duplicate_events_dedup(self):
        e = observed("news", 30)
        results = build(candles(), {"observations": [e,e]}, (300,))
        self.assertEqual(results["observation_count"], 1)

    def test_cross_asset_records_excluded(self):
        foreign = observed("social", 30)
        foreign["asset"] = "ETH-USD"
        results = build(candles(), {"observations": [foreign]}, (300,))
        self.assertEqual(results["observation_count"], 0)

    def test_structured_sample_count_only_after_collector_observed(self):
        event = observed("social", 80)
        event["sample_metrics"] = {
            "provider": "bluesky_search", "sampled_posts": 12,
            "sampled_unique_authors": 8, "previous_hour_posts": 3,
            "previous_hour_unique_authors": 3, "search_results_inspected": 60,
            "search_limit": 100,
            "coverage": "bounded_search_sample_not_platform_total",
        }
        output = build(candles(), {"observations": [event]}, (300,))
        before = next(r for r in output["rows"] if r["decision_ms"] == MS+50*60000)
        after = next(r for r in output["rows"] if r["decision_ms"] == MS+81*60000)
        self.assertIsNone(before["features"]["social_sampled_posts"])
        self.assertIsNone(before["features"]["social_unique_authors"])
        self.assertEqual(after["features"]["social_sampled_posts"], 12)
        self.assertEqual(after["features"]["social_unique_authors"], 8)
        self.assertEqual(after["features"]["social_sampled_post_change"], 9)

    def test_inconsistent_sample_author_count_rejected(self):
        event = observed("social", 30)
        event["sample_metrics"] = {
            "provider": "bluesky_search", "sampled_posts": 1,
            "sampled_unique_authors": 12,
            "coverage": "bounded_search_sample_not_platform_total",
        }
        output = build(candles(), {"observations": [event]}, (300,))
        self.assertEqual(output["observation_count"], 0)
        self.assertEqual(output["ignored_observations"]["invalid"], 1)

    def test_unknown_sentiment_is_not_invented(self):
        result = build(candles(), {"observations": [observed("social", 30)]}, (300,))
        self.assertIsNone(result["rows"][0]["features"]["social_sentiment"])
        self.assertIsNone(result["rows"][0]["features"]["social_unique_authors"])

    def test_future_price_label_exists_separate_from_features(self):
        result = build(candles(), {"observations": []}, (300,))
        row = result["rows"][0]
        self.assertGreater(row["label_end_ms"], row["decision_ms"])
        self.assertNotIn("future_return_proxy", row["features"])


if __name__ == "__main__":
    unittest.main()
