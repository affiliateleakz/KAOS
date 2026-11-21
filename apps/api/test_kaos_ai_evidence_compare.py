"""Regression tests for evidence-augmented paired research evaluation."""
import unittest
from datetime import datetime, timedelta, timezone

from kaos_ai_evidence_compare import compare_models

BASE = datetime(2026,11,17,0,0,tzinfo=timezone.utc)
BASE_MS = int(BASE.timestamp()*1000)

def candles(n=500):
    bars=[]
    price=110.
    for i in range(n):
        close=110+0.3*((i*13)%23-11)+i*.002
        previous=price
        bars.append({
            "symbol":"AAPL","asset_class":"stock","seconds":60,
            "source":"alpaca_iex","ts":BASE_MS+i*60000,
            "open":previous,"high":max(previous,close)+.2,
            "low":min(previous,close)-.2,"close":close,"volume":100+i%30,
        })
        price=close
    return bars

def events(rows, source="news", every=1, delay_minutes=0):
    items=[]
    for i in range(0,len(rows),every):
        event_time=BASE+timedelta(minutes=i+1)
        at=event_time+timedelta(minutes=delay_minutes)
        items.append({
            "asset":"AAPL","asset_class":"stock","source":source,
            "direction":"bullish" if i%4<2 else "bearish",
            "strength":.3 if i%3 else .9,
            "provider":"gdelt","event_id":"event-"+str(i),
            "event_at":event_time.isoformat(),
            "published_at":at.isoformat(),"observed_at":at.isoformat(),
        })
    return items

def compare(rows, observations):
    return compare_models(rows,observations,symbol="AAPL",
                          asset_class="stock",source_category="news")

class ComparisonTest(unittest.TestCase):
    def test_no_evidence_fails_closed(self):
        out=compare(candles(500),[])
        self.assertEqual(out["status"],"insufficient_paired_history")
        self.assertEqual(out["paired_samples"],0)
        self.assertFalse(out["promotable"])
        self.assertFalse(out["execution_enabled"])

    def test_future_published_evidence_not_used(self):
        bars=candles(500)
        # All original event times precede prices but observation arrives 1d later.
        late=events(bars, delay_minutes=1440)
        result=compare(bars,late)
        self.assertEqual(result["paired_samples"],0)

    def test_evidence_can_run_paired_comparison_without_deploying(self):
        bars=candles(500)
        report=compare(bars,events(bars))
        self.assertEqual(report["status"],"comparison_complete_unvalidated")
        self.assertEqual(report["holdout_test"]["candle_only"]["samples"],
                         report["holdout_test"]["candle_plus_evidence"]["samples"])
        self.assertGreaterEqual(report["train_samples"],100)
        self.assertFalse(report["promotable"])
        self.assertFalse(report["execution_enabled"])
        self.assertIn("brier_delta_enhanced_minus_candle",report)
        self.assertNotIn("model", report)
        self.assertNotIn("weights", str(report))

    def test_rejects_unsupported_category(self):
        with self.assertRaises(ValueError):
            compare_models(candles(),[],symbol="AAPL",
                asset_class="stock",source_category="future_known_profit")

if __name__=="__main__":
    unittest.main()
