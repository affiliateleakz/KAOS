import unittest
from kaos_market_assessment import assess
BASE=1761955200000

def candles(n=80):
    return [{"ts":BASE+i*60000,"seconds":60,"symbol":"BTC-USD",
             "asset_class":"crypto","source":"coinbase_exchange_public",
             "open":100+i*.02,"high":101+i*.02,"low":99+i*.02,
             "close":100.3+i*.02,"volume":100+i%9} for i in range(n)]

def evaluate(rows=None,now_ms=None):
    rows=candles() if rows is None else rows
    return assess(rows,[],symbol="BTC-USD",asset_class="crypto",
                  seconds=60,source="coinbase_exchange_public",
                  now_ms=now_ms or BASE+len(rows)*60000)

class AssessmentTests(unittest.TestCase):
    def test_unvalidated_no_option_contract(self):
        doc=evaluate()
        self.assertEqual(doc["options"]["call_put"],"NONE")
        self.assertIsNone(doc["options"]["expiry"])
        self.assertIsNone(doc["confidence"])
        self.assertIsNone(doc["target_price"])
        self.assertEqual(doc["score_type"],"uncalibrated_technical_alignment_index_not_win_probability")

    def test_missing_history_abstains(self):
        doc=evaluate(candles(35))
        self.assertEqual(doc["buy_sell"],"WAIT")
        self.assertIsNone(doc["score"])

    def test_gap_cannot_claim_direction(self):
        rows=candles()
        rows.pop(-25)
        doc=evaluate(rows,now_ms=BASE+80*60000)
        self.assertEqual(doc["buy_sell"],"WAIT")
        self.assertGreater(doc["coverage"]["gaps_in_sample"],0)

    def test_stale_chart_abstains(self):
        doc=evaluate(now_ms=BASE+1000*60000)
        self.assertEqual(doc["buy_sell"],"WAIT")
        self.assertEqual(doc["bias"],"unknown")

    def test_no_evidence_is_missing_not_bearish(self):
        doc=evaluate()
        self.assertIn("social",doc["coverage"]["missing_sources"])
        self.assertIn("news",doc["coverage"]["missing_sources"])
        self.assertEqual(doc["evidence"],[])

    def test_mixed_asset_rejected(self):
        rows=candles()
        rows[0]["symbol"]="ETH-USD"
        with self.assertRaisesRegex(ValueError,"mixed"):
            evaluate(rows)

if __name__=="__main__":
    unittest.main()
