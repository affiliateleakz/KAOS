"""Offline tests for long-running KAOS recording cycle and recovery."""
import unittest
from continuous_candle_worker import validate_config,prepare_rows,cycle

BASE=1761955200000
MARKET={"symbol":"BTC-USD","asset_class":"crypto","seconds":60}

def history(n=10):
    return [{"ts":BASE+i*60000,"open":100.+i*.1,"high":101.+i*.1,
             "low":99.+i*.1,"close":100.1+i*.1,"volume":20} for i in range(n)]

class RecorderTests(unittest.TestCase):
    def test_validate_market_universe(self):
        r=validate_config({"markets":[MARKET]})
        self.assertEqual(r[0]["symbol"],"BTC-USD")
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            validate_config({"markets":[MARKET,MARKET]})
    def test_future_and_open_candles_not_stored(self):
        rows=prepare_rows(MARKET,history(10),"coinbase_exchange_public",
                           now_ms=BASE+9*60000+100)
        self.assertEqual(len(rows),9)
        self.assertEqual(rows[-1]["ts"],BASE+8*60000)
    def test_cycle_and_replay_overlap_without_losing_progress(self):
        captured=[];state={}
        def fetch(market):return history(10),"coinbase_exchange_public"
        def post(url,batch,*,key):
            captured.append(list(batch))
            return {"accepted":len(batch)}
        report=cycle([MARKET],api_base="https://api.example.com",key="test",
                     now_ms=BASE+10*60000,pause=0,fetch=fetch,post=post,last_seen=state)
        self.assertEqual(report["markets_ok"],1)
        self.assertEqual(report["bars_submitted"],10)
        report2=cycle([MARKET],api_base="https://api.example.com",key="test",
                     now_ms=BASE+10*60000,pause=0,fetch=fetch,post=post,last_seen=state)
        self.assertEqual(report2["bars_submitted"],6)
        self.assertEqual(len(captured),2)
    def test_failed_ingest_does_not_advance_checkpoint(self):
        state={}
        def post(*_,**__):raise RuntimeError("backend down")
        report=cycle([MARKET],api_base="https://api.example.com",key="test",
                     now_ms=BASE+10*60000,pause=0,
                     fetch=lambda _: (history(),"coinbase_exchange_public"),
                     post=post,last_seen=state)
        self.assertEqual(report["markets_failed"],1)
        self.assertEqual(state,{})
    def test_gaps_are_preserved_no_fake_history(self):
        rows=history(10);rows.pop(4)
        p=prepare_rows(MARKET,rows,"coinbase_exchange_public",now_ms=BASE+11*60000)
        self.assertEqual(len(p),9)
        self.assertEqual(p[4]["ts"],BASE+5*60000)
if __name__=="__main__":
    unittest.main()
