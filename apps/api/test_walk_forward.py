"""Synthetic robustness checks for owner's expanding-window evaluation."""
import unittest
from datetime import datetime,timezone,timedelta
from kaos_walk_forward import walk_forward
from test_multifactor_baseline import bars, news, BASE

def run(data=None,observations=None,**kwargs):
    params={"folds":3,"min_train":60,"min_test":15,**kwargs}
    return walk_forward(bars() if data is None else data,
        news() if observations is None else observations,
        symbol="AAPL",asset_class="stock",seconds=60,source="test_local",
        **params)

class WalkForwardTests(unittest.TestCase):
    def test_folds_chronological_and_disjoint(self):
        r=run()
        self.assertEqual(r["status"],"research_walk_forward_completed")
        self.assertEqual(r["folds_completed"],3)
        prior_end=None
        for fold in r["folds"]:
            self.assertLessEqual(fold["train_last_outcome_ms"],
                                 fold["test_first_decision_ms"])
            if prior_end is not None:
                self.assertLessEqual(prior_end,fold["test_first_decision_ms"])
            prior_end=fold["test_last_outcome_ms"]
            self.assertEqual(fold["technical_only"]["samples"],fold["test_samples"])
        self.assertFalse(r["independent_validation_passed"])
        self.assertFalse(r["orders_enabled"])

    def test_missing_news_does_not_fabricate_gain(self):
        r=run(observations=[])
        self.assertFalse(r["all_folds_comparable"])
        self.assertEqual(r["folds_with_usable_intelligence"],0)
        self.assertIsNone(r["accuracy_improvement_fold_count"])
        self.assertTrue(all(f["multifactor"] is None for f in r["folds"]))

    def test_future_news_never_valid_in_prior_windows(self):
        future=datetime.fromtimestamp((BASE+9000*60000)/1000,timezone.utc)
        article={"asset":"AAPL","asset_class":"stock","source":"news",
            "event_id":"too-late","direction":"bullish","strength":1,
            "published_at":(future-timedelta(days=1)).isoformat(),
            "observed_at":future.isoformat()}
        r=run(observations=[article])
        self.assertFalse(r["all_folds_comparable"])

    def test_insufficient_data_has_no_accuracy(self):
        r=run(data=bars(180),observations=[])
        self.assertEqual(r["status"],"insufficient_walk_forward_history")
        self.assertNotIn("accuracy_improvement_fold_count",r)

    def test_bad_fold_number_rejected(self):
        with self.assertRaisesRegex(ValueError,"folds"):
            run(folds=10)

    def test_cannot_mix_source_prices(self):
        data=bars()
        data[50]["source"]="another_provider"
        with self.assertRaisesRegex(ValueError,"mixed"):
            run(data=data)
if __name__=="__main__":unittest.main()
