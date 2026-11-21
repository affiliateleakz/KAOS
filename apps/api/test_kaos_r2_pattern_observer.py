"""Offline regression tests for Codex R2 observer; no broker or database."""
import os
import sys
import unittest
sys.path.insert(0,os.path.dirname(__file__))

from kaos_r2_pattern_observer import observe_market,HORIZONS

def rows(n=30, start=1700000040000):
    out=[]
    for i in range(n):
        p=100+(i%3)*0.1
        out.append({"ts":start+i*60000,"open":p,
                    "high":p+1,"low":p-1,"close":p+.01,
                    "volume":3})
    return out

class PatternObserverTests(unittest.TestCase):
    def test_observes_without_any_trades(self):
        sample=rows(45)
        result=observe_market(sample,"BTC-USD","crypto",60,"coinbase_exchange_public")
        self.assertEqual(result["bars"],45)
        self.assertGreater(result["events_count"],0)
        self.assertFalse(result["based_on_trades"])
        self.assertFalse(result["execution_enabled"])
        self.assertEqual(result["implemented_count"],21)
        self.assertEqual(result["catalog_count"],50)
        self.assertTrue(all(x["based_on_trades"] is False for x in result["events"]))

    def test_no_outcome_crosses_missing_candles(self):
        a=rows(20)
        b=rows(20,start=a[-1]["ts"]+5*60000)
        result=observe_market(a+b,"BTC-USD","crypto",60,"coinbase_exchange_public")
        self.assertEqual(result["segments"],2)
        first_end=a[-1]["ts"]
        for e in result["events"]:
            for future in e["horizons"]:
                if future["status"]=="settled":
                    self.assertTrue((e["observed_ts"]<=first_end and future["settlement_ts"]<=first_end) or
                                    (e["observed_ts"]>first_end and future["settlement_ts"]>first_end))

    def test_no_future_candles_needed_for_detection(self):
        a=rows(20)
        result=observe_market(a,"BTC-USD","crypto",60,"coinbase_exchange_public")
        old=[(x["id"],x["pattern"],x["observed_ts"]) for x in result["events"]]
        b=a+rows(5,start=a[-1]["ts"]+60000)
        after=observe_market(b,"BTC-USD","crypto",60,"coinbase_exchange_public")
        now=[(x["id"],x["pattern"],x["observed_ts"]) for x in after["events"]
             if x["observed_ts"]<=a[-1]["ts"]]
        self.assertEqual(old,now)

    def test_last_candle_observation_has_pending_future_labels(self):
        r=observe_market(rows(22),"BTC-USD","crypto",60,"coinbase_exchange_public")
        latest=max(x["observed_ts"] for x in r["events"])
        final=[x for x in r["events"] if x["observed_ts"]==latest]
        self.assertTrue(final)
        self.assertTrue(any(x["status"]=="pending" for event in final for x in event["horizons"]))

    def test_duplicate_timestamp_rejected(self):
        r=rows(25)
        r[12]["ts"]=r[11]["ts"]
        with self.assertRaises(ValueError):
            observe_market(r,"BTC-USD","crypto",60,"coinbase_exchange_public")

if __name__=="__main__":
    unittest.main()
