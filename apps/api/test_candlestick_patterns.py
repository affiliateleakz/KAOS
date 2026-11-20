import unittest
from kaos_candlestick_patterns import scan, catalog, CATALOG, IMPLEMENTED

def candle(o,h,l,c):
    return {"open":o,"high":h,"low":l,"close":c}

class ClassicPatternTests(unittest.TestCase):
    def test_catalog_explicit_implementation_state(self):
        items=catalog()
        self.assertEqual(len(items),50)
        self.assertEqual(len(set(x["name"] for x in items)),50)
        self.assertEqual(sum(x["implemented"] for x in items),len(IMPLEMENTED))
        self.assertTrue(any(not x["implemented"] for x in items))

    def test_bullish_engulfing_found_only_after_close(self):
        rows=[candle(104,105,103,103.5),candle(103.5,104,102,102.8),
              candle(102.8,103,101.5,102),candle(102,102.2,100,100.5),
              candle(100.6,100.8,99.5,99.8),
              candle(99.7,101.3,99.5,101.1)]
        matches=scan(rows)
        self.assertTrue(any(x["pattern"]=="Bullish Engulfing" and x["index"]==5 for x in matches))

    def test_doji_found(self):
        rows=[candle(100,101,99,100.5)]*4+[candle(100,101,99,100.02)]
        self.assertIn("Doji",[m["pattern"] for m in scan(rows)])

    def test_no_future_candle_read(self):
        rows=[candle(100,101,99,100.5)]*4+[candle(100,101,99,100.02)]
        prior=scan(rows)
        rows.append(candle(100,200,1,150))
        later=[m for m in scan(rows) if m["index"]<5]
        self.assertEqual(prior,later)

    def test_invalid_ohlc_fails(self):
        with self.assertRaisesRegex(ValueError,"inconsistent"):
            scan([candle(100,101,99,100)]*4+[candle(100,100.1,101,100)])

    def test_no_data_no_patterns(self):
        self.assertEqual(scan([]),[])
        self.assertEqual(scan([candle(100,101,99,100)]*4),[])

if __name__=="__main__":
    unittest.main()
