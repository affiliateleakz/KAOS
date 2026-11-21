"""Pure offline tests for KAOS no-trade model forecasts and settlement."""
import os
import sys
import unittest
sys.path.insert(0,os.path.dirname(__file__))
from kaos_r2_ai_lab import FEATURES
from kaos_r2_shadow_predict import prediction, settle

S=60_000
START=1700000040000

def candles(n=30,start=START,source="coinbase_exchange_public"):
    return [{"ts":start+i*S,"open":100.0+i*.01,"high":101.0+i*.01,
             "low":99.0+i*.01,"close":100.0+i*.01,"volume":10.0,
             "symbol":"BTC-USD","asset_class":"crypto","seconds":60,
             "source":source} for i in range(n)]

def model(bias=3.0):
    return {"id":"r2model1","symbol":"BTC-USD","asset_class":"crypto",
            "source":"coinbase_exchange_public","status":"candidate",
            "research_only":True,"execution_enabled":False,
            "horizon_bars":4,"seconds":60,
            "validation_status":"candidate_not_validated",
            "model":{"schema":"kaos_r2_ohlc_logistic_v1",
                     "features":list(FEATURES),
                     "weights":[0.0]*len(FEATURES),
                     "mean":[0.0]*len(FEATURES),
                     "std":[1.0]*len(FEATURES),"bias":bias}}

def predict_rows(rows,rec=None,now_ms=None):
    return prediction(rows,symbol="BTC-USD",asset_class="crypto",
                      seconds=60,source="coinbase_exchange_public",
                      record=rec or model(),
                      now_ms=now_ms or rows[-1]["ts"]+S+1000)

class ShadowPredictionTests(unittest.TestCase):
    def test_real_model_forecast_has_no_order_permission(self):
        out=predict_rows(candles())
        self.assertEqual(out["direction"],"UP")
        self.assertEqual(out["outcome_status"],"pending")
        self.assertEqual(out["validation_status"],"candidate_not_validated")
        self.assertFalse(out["execution_enabled"])
        self.assertFalse(out["broker_order_authorized"])
        self.assertFalse(out["paper_order_authorized"])
        self.assertGreater(out["prob_up"],.9)

    def test_abstains_when_not_confident(self):
        out=predict_rows(candles(),model(0))
        self.assertEqual(out["direction"],"HOLD")

    def test_refuses_stale_candle(self):
        with self.assertRaisesRegex(ValueError,"stale"):
            predict_rows(candles(),now_ms=START+60*S)

    def test_refuses_gap_in_feature_window(self):
        r=candles()
        r[-4]["ts"]+=2*S
        with self.assertRaisesRegex(ValueError,"Missing candle"):
            predict_rows(r)

    def test_refuses_different_provider(self):
        rec=model()
        rec["source"]="alpaca_iex"
        with self.assertRaisesRegex(ValueError,"another data provider"):
            predict_rows(candles(),rec)

    def test_refuses_nonresearch_or_bad_schema(self):
        rec=model()
        rec["execution_enabled"]=True
        with self.assertRaisesRegex(ValueError,"research-only"):
            predict_rows(candles(),rec)
        rec=model()
        rec["model"]["schema"]="other"
        with self.assertRaisesRegex(ValueError,"schema"):
            predict_rows(candles(),rec)

    def test_only_settles_after_future_candle_present(self):
        a=candles(20)
        f=predict_rows(a)
        self.assertIsNone(settle(f,a))
        future=candles(4,start=a[-1]["ts"]+S)
        result=settle(f,a+future)
        self.assertEqual(result["outcome_status"],"settled")
        self.assertTrue(result["correct"])
        self.assertFalse(result["actual_trade"])

    def test_never_settles_across_missing_future_bar(self):
        a=candles(20)
        f=predict_rows(a)
        future=candles(4,start=a[-1]["ts"]+S)
        self.assertIsNone(settle(f,a+future[:1]+future[2:]))

    def test_never_settles_across_provider_switch(self):
        a=candles(20)
        f=predict_rows(a)
        future=candles(4,start=a[-1]["ts"]+S)
        future[-2]["source"]="fake_source"
        self.assertIsNone(settle(f,a+future))

if __name__=="__main__":
    unittest.main()
