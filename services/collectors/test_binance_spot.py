import unittest
from datetime import datetime,timezone
from binance_spot import observe,fetch
class Tests(unittest.TestCase):
    def test_bullish(self):
        now=datetime(2026,10,16,4,0,tzinfo=timezone.utc)
        ms=int(now.timestamp()*1000)
        candles=[{'close_ms':ms-(25-i)*60000,'close':100+i*.2} for i in range(25)]
        result=observe('BTCUSDT',candles,'https://api.binance.com',now)
        self.assertEqual(result['direction'],'bullish')
        self.assertFalse(result.get('trade_recommendation',False))
    def test_stale(self):
        now=datetime(2026,10,16,4,0,tzinfo=timezone.utc)
        candles=[{'close_ms':int(now.timestamp()*1000)-3600000,'close':100}]*21
        self.assertIsNone(observe('BTCUSDT',candles,'https://api.binance.com',now))
    def test_invalid_symbol(self):
        with self.assertRaises(ValueError):fetch('../secret')
if __name__=='__main__':unittest.main()
