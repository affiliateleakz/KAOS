import json
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch
from gdelt_news import fetch_articles, observe_articles, parse_seen_at, validate_watchlist as validate_news
from sec_edgar_filings import get_submissions, observe_filings, validate_watchlist as validate_sec, run as run_sec
from market_collection_runner import load_config, collect_once

NOW=datetime(2026,10,16,4,0,0,tzinfo=timezone.utc)

class FakeResponse:
    def __init__(self,data):self.data=json.dumps(data).encode()
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def read(self,*args):return self.data

class ProviderTests(unittest.TestCase):
    def test_gdelt_request_is_read_only_encoded(self):
        calls=[]
        def opener(req,timeout=None):
            calls.append((req.full_url,req.get_method()))
            return FakeResponse({'articles':[{'title':'news','url':'https://example.org/x','seendate':'20261016035000'}]})
        result=fetch_articles('"Apple Inc"',opener=opener)
        self.assertEqual(len(result),1)
        self.assertEqual(calls[0][1],'GET')
        self.assertIn('mode=artlist',calls[0][0]); self.assertIn('Apple+Inc',calls[0][0])
    def test_neutral_news_and_stable_events(self):
        a=[{'url':'https://example.com/apple','title':'Apple announcement',
            'seendate':'20261016035000','domain':'example.com'}]
        first=observe_articles('AAPL','"Apple Inc"',a,NOW)
        second=observe_articles('AAPL','"Apple Inc"',a,NOW+timedelta(minutes=15))
        self.assertEqual(first[0]['event_id'],second[0]['event_id'])
        self.assertEqual(first[0]['published_at'],second[0]['published_at'])
        self.assertEqual(first[0]['direction'],'neutral')
        self.assertIn('NOT verified publication',first[0]['summary'])
    def test_gdelt_bad_dates_and_urls_filtered(self):
        articles=[{'url':'http://unsafe','title':'x','seendate':'20261016035000'},
                  {'url':'https://safe.com','title':'x','seendate':'20261018035000'},
                  {'url':'https://safe.com','title':'x','seendate':'bad'}]
        self.assertEqual(observe_articles('AAPL','"Apple Inc"',articles,NOW),[])
    def test_news_validation(self):
        with self.assertRaises(ValueError):validate_news([{'symbol':'AAPL','query':''}])
        with self.assertRaises(ValueError):validate_news([{'symbol':'AAPL','query':'x'*121}])
        with self.assertRaises(ValueError):validate_news([{'symbol':'AAPL','query':'"Apple"'}, {'symbol':'AAPL','query':'"Apple"'}])

    def test_sec_company_identity_and_links(self):
        doc={'cik':320193,'filings':{'recent':{'form':['4','8-K','10-Q','13F-HR'],
                  'accessionNumber':['0000320193-26-000001','0000320193-26-000002','0000320193-26-000003','0000320193-26-000004'],
                  'filingDate':['2026-10-15']*4,
                  'acceptanceDateTime':['2026-10-15T16:00:00']*4,
                  'primaryDocument':['ownership.xml','report.htm','quarter.htm','portfolio.htm']}}}
        items=observe_filings('AAPL','0000320193',doc,NOW)
        self.assertEqual(len(items),3)
        self.assertEqual(items[0]['source'],'insider')
        self.assertEqual(items[1]['source'],'filing')
        self.assertTrue(all(x['direction']=='neutral' for x in items))
        self.assertIn('does NOT establish insider BUY/SELL',items[0]['summary'])
        self.assertEqual(items[0]['published_at'],'2026-10-15T20:00:00+00:00')
        self.assertIn('000032019326000001/ownership.xml',items[0]['source_url'])
        self.assertEqual(items[0]['event_id'],observe_filings('AAPL','0000320193',doc,NOW+timedelta(hours=2))[0]['event_id'])
        with self.assertRaises(ValueError):observe_filings('AAPL','0000320193',dict(doc,cik=9999),NOW)
    def test_sec_rejects_path_traversal(self):
        doc={'cik':320193,'filings':{'recent':{'form':['4'],'accessionNumber':['0000320193-26-000001'],
          'filingDate':['2026-10-15'],'acceptanceDateTime':[],'primaryDocument':['../bad.html']}}}
        self.assertEqual(observe_filings('AAPL','0000320193',doc,NOW),[])
    def test_sec_requires_contact_identification(self):
        with self.assertRaises(ValueError):get_submissions('0000320193','KAOS Trading')
        result,issues=run_sec([{'symbol':'AAPL','cik':'0000320193'}],user_agent='')
        self.assertEqual(result,[])
        self.assertEqual(issues[0]['reason'],'missing_valid_SEC_USER_AGENT')
    def test_sec_get_uses_only_public_submissions(self):
        calls=[]
        def opener(req,timeout=None):
            calls.append((req.full_url,req.get_method(),req.get_header('User-agent')))
            return FakeResponse({'cik':320193,'filings':{'recent':{}}})
        get_submissions('0000320193','KAOS Research support@example.com',opener=opener)
        self.assertEqual(calls[0][1],'GET')
        self.assertIn('data.sec.gov/submissions/CIK0000320193.json',calls[0][0])
        self.assertIn('support@example.com',calls[0][2])
    def test_sec_config_validation(self):
        self.assertEqual(validate_sec([{'symbol':'AAPL','cik':320193}])[0]['cik'],'0000320193')
        with self.assertRaises(ValueError):validate_sec([{'symbol':'AAPL','cik':'ABC'}])
    def test_runner_loads_news_sec(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'config.json'
            p.write_text(json.dumps({'news_watchlist':[{'symbol':'AAPL','query':'"Apple Inc"'}],
                                     'sec_watchlist':[{'symbol':'AAPL','cik':'320193'}]}))
            cfg=load_config(p)
        self.assertEqual(cfg['news_watchlist'][0]['symbol'],'AAPL')
        self.assertEqual(cfg['sec_watchlist'][0]['cik'],'0000320193')
        with patch('market_collection_runner.run_news',return_value=([{'source':'news','event_id':'a'}],[])) as news,\
             patch('market_collection_runner.run_sec',return_value=([{'source':'filing','event_id':'b'}],[])) as sec:
            obs,_=collect_once(cfg,pause=0,include_news=True,include_sec=False)
            self.assertEqual(len(obs),1);news.assert_called_once();sec.assert_not_called()

if __name__=='__main__':unittest.main()
