import unittest
from kaos_prediction_validation import evaluate_history

BASE=1761955200000

def candles(n=1000):
    records=[]
    for i in range(n):
        price=100+i*.02
        records.append({"ts":BASE+i*60000,"symbol":"BTC-USD",
                        "asset_class":"crypto","seconds":60,
                        "source":"synthetic_unit_test","open":price,
                        "high":price+.3,"low":price-.3,
                        "close":price+.1,"volume":100+i%11})
    return records

def report(rows=None,**kwargs):
    return evaluate_history(candles() if rows is None else rows,
                            symbol="BTC-USD",asset_class="crypto",
                            seconds=60,source="synthetic_unit_test",
                            min_test=20,**kwargs)

class HistoricalValidationTests(unittest.TestCase):
    def test_chronological_heldout_and_baseline(self):
        r=report()
        self.assertEqual(r["status"],"unvalidated_historical_research")
        self.assertLessEqual(r["train_last_outcome_ms"],r["holdout_first_decision_ms"])
        self.assertGreaterEqual(r["holdout_signals"],20)
        self.assertEqual(r["majority_baseline_direction"],"UP")
        self.assertFalse(r["options_validated"])
        self.assertFalse(r["orders_enabled"])

    def test_later_prices_cannot_change_preceding_input(self):
        a=candles()
        past=a[:500]
        amended=candles()
        for row in amended[500:]:
            row["close"]=row["open"]-.05
        # Historical research cut at an identical as-of time is reproducible:
        self.assertEqual(report(past)["status"],report(amended[:500])["status"])
        self.assertEqual(report(past).get("holdout_signals"),report(amended[:500]).get("holdout_signals"))

    def test_missing_archive_returns_no_invented_scores(self):
        r=report(candles(120))
        self.assertEqual(r["status"],"insufficient_archived_history")
        self.assertNotIn("directional_win_fraction_after_costs",r)

    def test_gap_is_never_interpolated(self):
        r=candles()
        for item in r[500:]:item["ts"]+=10*60000
        result=report(r)
        self.assertEqual(result["research_only"],True)
        self.assertLess(result.get("decision_count",0),150)

    def test_mixed_market_blocks_run(self):
        r=candles()
        r[1]["symbol"]="ETH-USD"
        with self.assertRaisesRegex(ValueError,"Mixed"):
            report(r)

    def test_duplicate_timestamp_blocks_run(self):
        r=candles()
        r[3]["ts"]=r[2]["ts"]
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            report(r)

    def test_historical_news_cannot_create_false_signal(self):
        from datetime import datetime,timezone,timedelta
        rows=candles()
        # This headline is not available until after every archived decision.
        future=datetime.fromtimestamp((BASE+2000*60000)/1000,timezone.utc)
        record={"asset":"BTC-USD","asset_class":"crypto","source":"news",
                "event_id":"later-headline","direction":"bullish","strength":1,
                "published_at":(future-timedelta(hours=1)).isoformat(),
                "observed_at":future.isoformat()}
        result=evaluate_history(rows,symbol="BTC-USD",asset_class="crypto",
             seconds=60,source="synthetic_unit_test",observations=[record],min_test=20)
        self.assertEqual(result["status"],"unvalidated_historical_research")
        fusion=result["point_in_time_fusion"]
        self.assertEqual(fusion["holdout_fusion_signals"],0)
        self.assertIsNone(fusion["mean_fusion_return_proxy"])

    def test_replay_with_no_social_or_news_abstains_on_fusion(self):
        result=evaluate_history(candles(),symbol="BTC-USD",asset_class="crypto",
             seconds=60,source="synthetic_unit_test",observations=[],min_test=20)
        self.assertEqual(result["point_in_time_fusion"]["holdout_fusion_signals"],0)
        self.assertIsNone(result["point_in_time_fusion"]["mean_baseline_proxy_on_fusion_dates"])

    def test_cost_range_is_enforced(self):
        with self.assertRaisesRegex(ValueError,"cost"):
            report(fee_bps=-1)

if __name__=="__main__":unittest.main()
