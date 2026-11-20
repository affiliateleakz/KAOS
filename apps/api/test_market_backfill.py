import unittest
from routes_market_backfill import validate_market,normalize_bars

NOW=1761955200000
def rows():
    return [{"ts":NOW-(i+1)*60000,"open":100.,"high":101.,"low":99.,"close":100.5,"volume":25} for i in range(8)]

class MarketHistoryTests(unittest.TestCase):
    def test_market_classes(self):
        self.assertEqual(validate_market("btc-usd","crypto",60),"BTC-USD")
        self.assertEqual(validate_market("aapl","stock",300),"AAPL")
        self.assertEqual(validate_market("eur_usd","forex",900),"EUR_USD")
        for symbol,kind in [("BTCUSD","crypto"),("EUR/USD","forex"),("AAPL!","stock")]:
            with self.assertRaises(ValueError):
                validate_market(symbol,kind,60)
    def test_closed_candles_sorted(self):
        bars,gaps=normalize_bars(rows(),symbol="BTC-USD",asset_class="crypto",
                     source="coinbase",seconds=60,now_ms=NOW)
        self.assertEqual(len(bars),8)
        self.assertEqual(gaps,0)
        self.assertLess(bars[0]["ts"],bars[-1]["ts"])
    def test_incomplete_candle_dropped(self):
        data=rows()+[{"ts":NOW-10000,"open":100.,"high":101.,"low":99.,"close":100.,"volume":25}]
        bars,_=normalize_bars(data,symbol="BTC-USD",asset_class="crypto",
                             source="coinbase",seconds=60,now_ms=NOW)
        self.assertEqual(len(bars),8)
    def test_gap_preserved(self):
        data=rows();data.pop(3)
        bars,gaps=normalize_bars(data,symbol="BTC-USD",asset_class="crypto",
                                source="coinbase",seconds=60,now_ms=NOW)
        self.assertEqual(len(bars),7)
        self.assertEqual(gaps,1)
    def test_bad_ohlc_rejected(self):
        data=rows();data[0]["high"]=2
        bars,_=normalize_bars(data,symbol="AAPL",asset_class="stock",
                              source="alpaca",seconds=60,now_ms=NOW)
        self.assertEqual(len(bars),7)
    def test_conflicting_duplicate_blocks(self):
        data=rows();other=dict(data[0]);other["close"]=100.6;data.append(other)
        with self.assertRaisesRegex(ValueError,"Conflicting"):
            normalize_bars(data,symbol="BTC-USD",asset_class="crypto",
                           source="coinbase",seconds=60,now_ms=NOW)
if __name__=="__main__":unittest.main()
