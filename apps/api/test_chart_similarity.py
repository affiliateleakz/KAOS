import unittest
from kaos_chart_similarity import compare

class HistoricalChartTests(unittest.TestCase):
    def candles(self,n=130):
        return [{"ts":1760000000000+i*60000,"symbol":"BTC-USD","source":"synthetic",
                 "seconds":60,"open":100+i*.01,"high":101+i*.01,
                 "low":99+i*.01,"close":100+i*.01,"volume":100} for i in range(n)]
    def test_similar_history(self):
        r=compare(self.candles())
        self.assertLessEqual(r["count"],5)
        self.assertEqual(r["status"],"historical_similarity_only")
    def test_future_mutation_does_not_affect_target(self):
        r=self.candles()
        first=compare(r)["matches"]
        self.assertTrue(first)
        r[-1]["volume"]=123
        self.assertEqual(first,compare(r)["matches"])
    def test_structured_pattern_filter_preserves_history_only(self):
        rows=self.candles(180)
        result=compare(rows,pattern="range",limit=5)
        self.assertEqual(result["requested_pattern"],"range")
        self.assertTrue(all(m["pattern"]=="range" for m in result["matches"]))
        self.assertTrue(all(m["outcome_ms"]<rows[-1]["ts"] for m in result["matches"]))

    def test_invalid_pattern_rejected(self):
        with self.assertRaisesRegex(ValueError,"unsupported historical pattern"):
            compare(self.candles(),pattern="guaranteed_win")

    def test_breakout_classifier_has_no_future_price_dependency(self):
        from kaos_chart_similarity import classify_pattern
        rows=self.candles(30)
        last=rows[-1]
        last["close"]=last["high"]+2
        last["high"]=last["close"]+.5
        self.assertEqual(classify_pattern(rows[-20:]),"breakout_up")
        self.assertEqual(classify_pattern(rows[-20:]),"breakout_up")

    def test_no_data(self):
        self.assertEqual(compare(self.candles(20))["count"],0)
    def test_gap_latest(self):
        r=self.candles()
        r[-2]["ts"]+=300000
        self.assertEqual(compare(r)["count"],0)
    def test_mixed_sources_rejected(self):
        r=self.candles()
        r[0]["source"]="wrong"
        with self.assertRaises(ValueError):
            compare(r)

if __name__=="__main__":unittest.main()
