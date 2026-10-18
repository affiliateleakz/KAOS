import json
import unittest
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse
from alpaca_stocks import fetch_bars, observe, run, validate_symbols
from tradier_options import next_expiration, market_get, scan_chain
from collector_common import submit

NOW = datetime(2026, 10, 16, 15, 30, tzinfo=timezone.utc)

class Response:
    def __init__(self, payload): self.payload = payload
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, *args): return json.dumps(self.payload).encode()

# json.load accepts file with .read

def bars(symbol='AAPL', count=25, now=NOW, delta=0.2):
    return [{'t': (now-timedelta(minutes=(count-i))).isoformat(),
             'c': 100 + i*delta, 'v': 1000} for i in range(count)]

class StockAdapterTests(unittest.TestCase):
    def test_validation(self):
        self.assertEqual(validate_symbols(['aapl', 'AAPL', 'SPY']), ['AAPL','SPY'])
        with self.assertRaises(ValueError): validate_symbols(['../../secret'])
        with self.assertRaises(ValueError): validate_symbols(['AAPL']*151 + [f'TEST{i}' for i in range(151)])

    def test_observe_bullish_and_stale(self):
        item = observe('AAPL', bars(), now=NOW)
        self.assertEqual(item['direction'], 'bullish')
        self.assertEqual(item['asset_class'], 'stock')
        self.assertLessEqual(item['strength'],1)
        self.assertIn('IEX',item['summary'])
        self.assertIsNone(observe('AAPL', bars(now=NOW-timedelta(hours=3)), now=NOW))

    def test_forming_candle_excluded(self):
        series = bars()
        future = {'t': (NOW-timedelta(seconds=30)).isoformat(), 'c': 9999, 'v': 9999}
        result = observe('AAPL', series+[future], now=NOW)
        self.assertNotIn('9999', result['summary'])
        self.assertEqual(result['direction'], 'bullish')

    def test_alpaca_global_pagination(self):
        calls=[]
        def opener(req,timeout):
            params=parse_qs(urlparse(req.full_url).query)
            self.assertEqual(req.get_header('Apca-api-key-id'),'key')
            calls.append(params.get('page_token',[None])[0])
            if len(calls)==1:
                return Response({'bars':{'AAPL':bars()}, 'next_page_token':'PAGE2'})
            return Response({'bars':{'MSFT':bars()}, 'next_page_token':None})
        result=fetch_bars(['AAPL','MSFT'], 'key','secret',now=NOW,opener=opener)
        self.assertEqual(calls,[None,'PAGE2'])
        self.assertEqual(len(result['MSFT']),25)
        self.assertEqual(len(result['AAPL']),25)

    def test_incomplete_page_detection(self):
        def opener(req,timeout):
            return Response({'bars':{'AAPL':bars()}, 'next_page_token':'MORE'})
        with self.assertRaisesRegex(ValueError,'incomplete'):
            fetch_bars(['AAPL'], 'key','secret',now=NOW,max_pages=1,opener=opener)

    def test_etf_explicit_classification(self):
        def opener(req,timeout):
            return Response({'bars':{'SPY':bars()},'next_page_token':None})
        result, errors=run(['SPY'],'key','secret',etfs=['SPY'],now=NOW,opener=opener)
        self.assertFalse(errors)
        self.assertEqual(result[0]['asset_class'],'etf')

class TradierAdapterTests(unittest.TestCase):
    def test_expiry_validation(self):
        self.assertEqual(next_expiration({'expirations':{'date':['2026-10-15','2026-10-23','2026-10-16']}},NOW.date()),'2026-10-16')
        self.assertIsNone(next_expiration({'expirations':{'date':None}},NOW.date()))

    def test_market_get_only_authorized_endpoints(self):
        calls=[]
        def opener(req,timeout):
            calls.append(req)
            return Response({'expirations':{'date':['2026-10-16']}})
        market_get('expirations','aapl','token',opener=opener)
        self.assertEqual(calls[0].get_header('Authorization'),'Bearer token')
        self.assertEqual(urlparse(calls[0].full_url).path,'/v1/markets/options/expirations')
        with self.assertRaises(ValueError):market_get('orders','AAPL','token',opener=opener)

    def test_contracts_neutral_and_liquid(self):
        chain={'options':{'option':[
            {'symbol':'AAPL261016C00100000','option_type':'call','volume':200,'open_interest':100,'bid':1,'ask':1.08,'strike':100},
            {'symbol':'AAPL261016P00100000','option_type':'put','volume':600,'open_interest':200,'bid':1,'ask':1.20,'strike':100},
            {'symbol':'AAPL261016C00110000','option_type':'call','volume':500,'open_interest':100,'bid':.01,'ask':.99,'strike':110},
            {'symbol':'AAPL261016P00090000','option_type':'put','volume':1,'open_interest':100,'bid':1,'ask':1.05,'strike':90}
        ]}}
        obs=scan_chain('AAPL','2026-10-16',chain,NOW)
        self.assertEqual(len(obs),3)  # 2 contracts + underlying summary
        self.assertEqual({o['direction'] for o in obs},{'neutral'})
        self.assertEqual(obs[-1]['asset'],'AAPL')
        self.assertEqual(obs[-1]['asset_class'],'stock')
        self.assertEqual(obs[0]['source'],'options_flow')
        self.assertNotIn('ratio',obs[-1].keys())
        self.assertTrue(all(o['trade_recommendation'] is False for o in []))

    def test_empty_illiquid(self):
        self.assertEqual(scan_chain('AAPL','2026-10-16',{'options':{'option':[]}},NOW),[])

class TransportTests(unittest.TestCase):
    def test_batching_and_loopback(self):
        calls=[]
        def opener(req,timeout):
            data=json.loads(req.data)
            calls.append((req.full_url, len(data), req.get_header('X-kaos-collector-key')))
            return Response({'accepted':len(data),'mode':'research_only'})
        result=submit([{'asset': 'AAPL'}]*501,'http://127.0.0.1:8765','token',opener=opener)
        self.assertEqual(result['submitted'],501)
        self.assertEqual([n for _,n,_ in calls],[250,250,1])
        self.assertTrue(all(u.endswith('/api/v1/intelligence/ingest') for u,_,_ in calls))
        with self.assertRaises(ValueError):submit([], 'http://insecure.example','token',opener=opener)

if __name__=='__main__': unittest.main()
