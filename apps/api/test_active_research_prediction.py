"""Synthetic candidate lifecycle/inference checks; no actual training claims."""
import copy
import unittest
from datetime import datetime,timezone
from kaos_active_research_prediction import build_candidate,infer_candidate
from kaos_multifactor_baseline import train_logistic, TECHNICAL_INDICES
from test_multifactor_baseline import bars,BASE

def artifact():
    rows=bars(1100)
    input_rows=[{"x":[0.]*17,"up":1},{"x":[.1]*17,"up":0}]*70
    return {
        "schema":"kaos_research_logistic_v1",
        "symbol":"AAPL","asset_class":"stock","seconds":60,
        "source":"test_local","horizon_bars":5,
        "model":train_logistic(input_rows,feature_indices=TECHNICAL_INDICES,epochs=4),
        "last_training_candle_ms":BASE+900*60000,
        "quality_screen_pass":True,"approved":True,
        "model_digest":"e"*64,"selected_features":"technical_only",
    }

class PredictionLifecycleTests(unittest.TestCase):
    def test_missing_data_no_candidate(self):
        result=build_candidate(bars(200),[],symbol="AAPL",asset_class="stock",
                   seconds=60,source="test_local")
        self.assertEqual(result["status"],"insufficient_data")
        self.assertIsNone(result["candidate"])

    def test_unapproved_candidate_abstains(self):
        m=artifact();m["approved"]=False
        r=infer_candidate(m,bars(1100),[],now_ms=BASE+1100*60000)
        self.assertEqual(r["direction"],"WAIT")
        self.assertEqual(r["status"],"model_not_approved")

    def test_approved_candidate_is_advisory_only(self):
        r=infer_candidate(artifact(),bars(1100),[],now_ms=BASE+1100*60000)
        self.assertIn(r["status"],("experimental_prediction","experimental_abstention"))
        self.assertFalse(r["orders_enabled"])
        self.assertEqual(r["options"]["call_put"],"NONE")
        self.assertEqual(r["score_type"],"uncalibrated_model_output_not_a_win_probability")
        self.assertEqual(r["horizon_seconds"],300)

    def test_stale_history_abstains(self):
        r=infer_candidate(artifact(),bars(1100),[],now_ms=BASE+2000*60000)
        self.assertEqual(r["status"],"stale_or_incomplete_candles")
        self.assertEqual(r["direction"],"WAIT")

    def test_wrong_market_or_source_abstains(self):
        rows=bars(1100)
        rows[-1]["source"]="fake"
        r=infer_candidate(artifact(),rows,[],now_ms=BASE+1100*60000)
        self.assertEqual(r["status"],"source_or_market_mismatch")

    def test_missing_100_bar_history_abstains(self):
        r=infer_candidate(artifact(),bars(90),[],now_ms=BASE+90*60000)
        self.assertEqual(r["status"],"insufficient_live_history")

    def test_older_than_training_does_not_infer(self):
        m=artifact();m["last_training_candle_ms"]=BASE+1200*60000
        r=infer_candidate(m,bars(1100),[],now_ms=BASE+1100*60000)
        self.assertEqual(r["status"],"model_not_forward_of_training")

    def test_unvalidated_quality_screen_rejects(self):
        m=artifact();m["quality_screen_pass"]=False
        r=infer_candidate(m,bars(1100),[],now_ms=BASE+1100*60000)
        self.assertEqual(r["direction"],"WAIT")

if __name__=="__main__":
    unittest.main()
