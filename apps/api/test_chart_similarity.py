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
