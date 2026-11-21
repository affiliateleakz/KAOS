"""Safety regression tests for KAOS cross-source intelligence features."""
import unittest
from datetime import datetime, timedelta, timezone

from kaos_ai_evidence_features import make_feature_snapshot

NOW = datetime(2026, 11, 20, 12, tzinfo=timezone.utc)

def iso(at):
    return at.isoformat()

def evidence(source="news", *, symbol="AAPL", published=None, observed=None,
             event_at=None, event_id="headline-1", provider="gdelt",
             direction="bullish", strength=0.7):
    return {
        "symbol": symbol, "asset_class": "stock", "source": source,
        "provider": provider, "event_id": event_id,
        "direction": direction, "strength": strength,
        "published_at": iso(published or NOW - timedelta(minutes=10)),
        "observed_at": iso(observed or NOW - timedelta(minutes=5)),
        "event_at": iso(event_at or NOW - timedelta(minutes=15)),
    }

def snapshot(events, **kwargs):
    return make_feature_snapshot(symbol="AAPL", asset_class="stock",
        decision_at=NOW, observations=events, **kwargs)

class EvidenceFeaturesTest(unittest.TestCase):
    def test_provenance_and_research_safety(self):
        out = snapshot([evidence()])
        self.assertEqual(out["categories"]["news"]["state"], "fresh")
        self.assertEqual(out["categories"]["news"]["events_fresh"], 1)
        self.assertEqual(out["categories"]["social"]["state"], "missing")
        self.assertIsNone(out["categories"]["social"]["bullish_evidence"])
        self.assertFalse(out["execution_enabled"])
        self.assertFalse(out["signal_authorized"])
        self.assertFalse(out["prediction_available"])

    def test_late_publication_prevents_insider_leakage(self):
        insider = evidence("insider", event_at=NOW - timedelta(days=20),
            published=NOW + timedelta(minutes=1), observed=NOW - timedelta(days=1))
        out = snapshot([insider])
        self.assertEqual(out["categories"]["insider"]["state"], "missing")
        self.assertEqual(out["rejected"]["future_or_unpublished"], 1)

    def test_late_observation_prevents_lookahead(self):
        row = evidence(observed=NOW + timedelta(seconds=1))
        out = snapshot([row])
        self.assertEqual(out["categories"]["news"]["state"], "missing")
        self.assertEqual(out["rejected"]["future_or_unpublished"], 1)

    def test_stale_not_counted_as_current_signal(self):
        out = snapshot([evidence(published=NOW-timedelta(days=2),
            observed=NOW-timedelta(days=2))])
        self.assertEqual(out["categories"]["news"]["state"], "stale")
        self.assertIsNone(out["categories"]["news"]["bullish_evidence"])

    def test_no_duplicate_voting_or_foreign_symbol(self):
        item = evidence()
        out = snapshot([item, item, evidence(symbol="TSLA")])
        self.assertEqual(out["categories"]["news"]["events_seen"], 1)
        self.assertEqual(out["rejected"]["duplicate"], 1)
        self.assertEqual(out["rejected"]["wrong_asset"], 1)

    def test_provider_capped_independence(self):
        out = snapshot([evidence(event_id="a", strength=0.8),
                        evidence(event_id="b", strength=0.4),
                        evidence(event_id="c", provider="another", strength=0.6)])
        self.assertEqual(out["categories"]["news"]["independent_providers"], 2)
        self.assertAlmostEqual(out["categories"]["news"]["bullish_evidence"], 1.4)

    def test_existing_intelligence_collector_record(self):
        row = evidence()
        row["asset"] = row.pop("symbol")
        row.pop("provider")
        row.pop("event_at")
        row["event_id"] = "gdelt:apple:article-123"
        out = snapshot([row])
        self.assertEqual(out["categories"]["news"]["state"], "fresh")
        self.assertEqual(out["categories"]["news"]["independent_providers"], 1)
        self.assertEqual(out["rejected"]["invalid"], 0)

    def test_future_candle_rejected(self):
        with self.assertRaises(ValueError):
            snapshot([], candle_end_at=NOW + timedelta(seconds=5))

    def test_inputs_are_bounded(self):
        with self.assertRaises(ValueError):
            snapshot([{}] * 5001)

if __name__ == "__main__":
    unittest.main()
