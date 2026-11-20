"""Synthetic tests of offline multifactor model boundaries, not performance."""
import unittest
from datetime import datetime,timezone,timedelta
from kaos_multifactor_baseline import evaluate,dataset,split,FEATURES

BASE=1761955200000
def bars(n=1250):
    out=[]
    for i in range(n):
        # Alternating trends; no claims about real market accuracy.
        price=100+i*.003+2*__import__("math").sin(i/17)
        out.append({"ts":BASE+i*60000,"seconds":60,"symbol":"AAPL",
             "asset_class":"stock","source":"test_local","open":price,
             "high":price+.5,"low":price-.5,"close":price+.04,"volume":100+i%11})
    return out

def news(n=1250):
    result=[]
    for i in range(100,n,30):
        observed=datetime.fromtimestamp((BASE+i*60000)/1000,timezone.utc)
        result.append({"asset":"AAPL","asset_class":"stock","source":"news",
             "direction":"bullish" if i%2 else "bearish","strength":.6,
             "event_id":str(i),"observed_at":observed.isoformat(),
             "published_at":(observed-timedelta(minutes=1)).isoformat()})
    return result

def run(data=None,observations=None):
    return evaluate(bars() if data is None else data,
                    news() if observations is None else observations,
                    symbol="AAPL",asset_class="stock",seconds=60,
                    source="test_local")

class MultiFactorTests(unittest.TestCase):
    def test_split_purge_and_metrics(self):
        r=run()
        self.assertEqual(r["status"],"unvalidated_multifactor_baseline")
        self.assertLessEqual(r["train_last_outcome_ms"],r["validation_first_decision_ms"])
        self.assertLessEqual(r["validation_last_outcome_ms"],r["test_first_decision_ms"])
        self.assertEqual(len(r["feature_names"]),len(FEATURES))
        self.assertFalse(r["scores_calibrated"])
        self.assertFalse(r["model_deployed"])
        self.assertFalse(r["orders_enabled"])
        self.assertIsNone(r.get("recommended_option"))
    def test_heldout_only_metrics_no_training_result_leak(self):
        r=run()
        self.assertGreater(r["test_samples"],20)
        self.assertEqual(r["holdout"]["samples"],r["test_samples"])
        self.assertIn("holdout_majority_accuracy",r)
        self.assertNotIn("train_accuracy",r)
    def test_no_data_no_fabricated_score(self):
        r=run(bars(300),[])
        self.assertEqual(r["status"],"insufficient_point_in_time_training_data")
        self.assertNotIn("holdout",r)
    def test_future_article_excluded_from_past_features(self):
        past=bars(190)
        late=datetime.fromtimestamp((BASE+500*60000)/1000,timezone.utc)
        article={"asset":"AAPL","asset_class":"stock","source":"news",
            "direction":"bullish","strength":1,"event_id":"late",
            "observed_at":late.isoformat(),
            "published_at":(late-timedelta(hours=2)).isoformat()}
        a=dataset(past,[],symbol="AAPL",asset_class="stock",seconds=60,source="test_local")
        b=dataset(past,[article],symbol="AAPL",asset_class="stock",seconds=60,source="test_local")
        self.assertEqual([x["x"] for x in a],[x["x"] for x in b])
    def test_missing_evidence_flags_explicit(self):
        rows=dataset(bars(220),[],symbol="AAPL",asset_class="stock",seconds=60,source="test_local")
        self.assertTrue(rows)
        self.assertEqual(rows[-1]["x"][-4:],[0.,0.,0.,0.])
    def test_discontinuous_bars_skipped(self):
        data=bars()
        for row in data[630:]:
            row["ts"]+=60*60000
        rows=dataset(data,[],symbol="AAPL",asset_class="stock",seconds=60,source="test_local")
        self.assertLess(len(rows),len(dataset(bars(),[],symbol="AAPL",asset_class="stock",seconds=60,source="test_local")))
    def test_invalid_market_metadata_rejected(self):
        data=bars()
        data[20]["source"]="another_feed"
        with self.assertRaisesRegex(ValueError,"mixed"):
            run(data)
    def test_invalid_cost_rejected(self):
        with self.assertRaisesRegex(ValueError,"cost"):
            evaluate(bars(),[],symbol="AAPL",asset_class="stock",
                     seconds=60,source="test_local",cost_bps=-5)
if __name__=="__main__":unittest.main()
