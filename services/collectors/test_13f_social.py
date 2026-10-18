import json
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch

from sec_13f_holdings import (validate_managers, find_information_tables,
    parse_information_table, observe_holdings, recent_filing, run as run_13f, _archive_url)
from bluesky_social import (validate_social_accounts, validate_cashtags,
    fetch_feed, observe_accounts, run as run_social)
from market_collection_runner import load_config, collect_once

NOW = datetime(2026,10,16,4,30,tzinfo=timezone.utc)
XML=b'''<?xml version="1.0" encoding="utf-8"?>
<informationTable xmlns="http://www.sec.gov/edgar/document/thirteenf/informationtable">
<infoTable><nameOfIssuer>EXAMPLE TECH</nameOfIssuer><titleOfClass>COM</titleOfClass><cusip>037833100</cusip>
<value>25000</value><shrsOrPrnAmt><sshPrnamt>200</sshPrnamt><sshPrnamtType>SH</sshPrnamtType></shrsOrPrnAmt></infoTable>
<infoTable><nameOfIssuer>EXAMPLE OTHER</nameOfIssuer><titleOfClass>COM</titleOfClass><cusip>594918104</cusip>
<value>12000</value><shrsOrPrnAmt><sshPrnamt>100</sshPrnamt><sshPrnamtType>SH</sshPrnamtType></shrsOrPrnAmt></infoTable>
</informationTable>'''
FILING={'cik': 320193, 'filings': {'recent': {
    'form':['13F-HR','4'], 'accessionNumber':['0000320193-26-000012','0000320193-26-000013'],
    'filingDate':['2026-10-15','2026-10-15'],
    'acceptanceDateTime':['2026-10-15T16:00:00','2026-10-15T17:00:00'],
    'reportDate':['2026-09-30','2026-10-15']}}}

def post(handle, uri, text, minutes=12, repost=False):
    stamp=(NOW-timedelta(minutes=minutes)).isoformat()
    item={'post': {'uri':'at://did:plc:abcd/app.bsky.feed.post/'+uri,
                   'author':{'handle':handle,'did':'did:plc:'+handle},
                   'indexedAt':stamp, 'record': {'text':text,'createdAt':stamp}}}
    if repost: item['reason']={'$type':'app.bsky.feed.defs#reasonRepost'}
    return item

class FakeResponse:
    def __init__(self,data): self.data=json.dumps(data).encode()
    def __enter__(self): return self
    def __exit__(self,*args): return False
    def read(self,*args): return self.data

class NewCollectorTests(unittest.TestCase):
    def test_sec_13f_validate(self):
        self.assertEqual(validate_managers([{'name':'Example Manager','cik':320193}])[0]['cik'],'0000320193')
        for bad in [[{'name':'x','cik':'../3'}], [{'name':'x','cik':'123'},{'name':'x','cik':'123'}], [{'name':'a'}]]:
            with self.assertRaises(ValueError): validate_managers(bad)
        with self.assertRaises(ValueError): _archive_url('0000320193','0000320193-26-000012','../passwd.xml')
    def test_index_discovery(self):
        doc={'directory':{'item':[{'name':'cover.htm'},{'name':'primary_doc.xml'},
               {'name':'infotable.xml'},{'name':'other.xml'}]}}
        self.assertEqual(find_information_tables(doc)[0],'infotable.xml')
    def test_13f_parse_holdings(self):
        data=parse_information_table(XML)
        self.assertEqual(len(data),2)
        self.assertEqual(data[0]['cusip'],'037833100')
        self.assertEqual(data[0]['value_as_filed'],'25000')
        for x in [b'<!DOCTYPE x><informationTable/>',b'<ownershipDocument/>']:
            with self.assertRaises(ValueError): parse_information_table(x)
    def test_13f_recent_filing_acceptance_not_quarter_date(self):
        filing=recent_filing('0000320193', FILING, NOW)
        self.assertEqual(filing['period'],'2026-09-30')
        self.assertEqual(filing['published_at'],datetime(2026,10,15,20,tzinfo=timezone.utc))
        self.assertIsNone(recent_filing('0000320193',FILING,NOW+timedelta(days=14)))
        with self.assertRaises(ValueError): recent_filing('0000000001', FILING, NOW)
    def test_13f_snapshots_are_not_trades(self):
        filing=recent_filing('0000320193',FILING,NOW)
        obs=observe_holdings({'name':'Example Fund','cik':'0000320193'},filing,parse_information_table(XML),
                             'https://www.sec.gov/Archives/edgar/data/320193/000032019326000012/infotable.xml',NOW)
        self.assertEqual(len(obs),2)
        self.assertEqual(obs[0]['asset'],'CUSIP:037833100')
        self.assertEqual(obs[0]['source'],'institutional')
        self.assertEqual(obs[0]['direction'],'neutral')
        self.assertIn('NOT a live buy', obs[0]['summary'])
        self.assertEqual(obs[0]['event_id'],observe_holdings({'name':'Example Fund','cik':'0000320193'},filing,parse_information_table(XML),'https://x',NOW+timedelta(hours=1))[0]['event_id'])
    def test_13f_run_full_filing_mock(self):
        agent='KAOS contact@example.org'
        def fake_submissions(cik,agent,opener=None):return FILING
        def fake_get(url,agent,max_size,opener=None):
            if url.endswith('index.json'):return json.dumps({'directory':{'item':[{'name':'infotable.xml'}]}}).encode()
            return XML
        with patch('sec_13f_holdings.get_submissions',side_effect=fake_submissions),patch('sec_13f_holdings._get_limited',side_effect=fake_get):
            items,issues=run_13f([{'name':'Example Fund','cik':320193}],user_agent=agent,now=NOW,pause_seconds=0)
        self.assertEqual(issues,[])
        self.assertEqual(len(items),2)
    def test_social_validation(self):
        self.assertEqual(validate_social_accounts(['Market.bsky.social','market.bsky.social']), ['market.bsky.social'])
        for bad in [['http://example.com'],['../secret'],['no-dots']]:
            with self.assertRaises(ValueError): validate_social_accounts(bad)
        with self.assertRaises(ValueError): validate_cashtags(['$GME'])
        with self.assertRaises(ValueError): validate_cashtags(['gme'])
    def test_social_public_get(self):
        requests=[]
        def opener(req,timeout=None):
            requests.append(req)
            return FakeResponse({'feed':[]})
        self.assertEqual(fetch_feed('market.bsky.social',opener=opener),[])
        self.assertIn('app.bsky.feed.getAuthorFeed',requests[0].full_url)
        self.assertEqual(requests[0].get_method(),'GET')
    def test_social_samples_only_explicit_cashtags(self):
        obs=observe_accounts({
          'one.bsky.social':[post('one.bsky.social','aaa','GME news'),post('one.bsky.social','bbb','Watching $GME $AMC'),post('one.bsky.social','bbb','Watching $GME $AMC'),post('one.bsky.social','ccc','$GME',repost=True)],
          'two.bsky.social':[post('two.bsky.social','ddd','Another $GME',minutes=2),post('two.bsky.social','eee','Old $GME',minutes=130)]
        },['GME','AMC'],NOW)
        gme=next(x for x in obs if x['asset']=='GME')
        self.assertEqual(gme['source'],'social');self.assertEqual(gme['direction'],'neutral')
        self.assertIn('2 distinct post(s)',gme['summary'])
        self.assertIn('2 public author(s)',gme['summary'])
        self.assertNotIn('acceleration',gme['summary'].split('NOT')[0])
        self.assertEqual(len(obs),2)
    def test_social_failure_not_faked(self):
        with patch('bluesky_social.fetch_feed',side_effect=PermissionError('403')):
            result,issues=run_social(['test.bsky.social'],['GME'],now=NOW,pause_seconds=0)
        self.assertEqual(result,[])
        self.assertEqual(issues[0]['reason'],'PermissionError')
    def test_config_integration(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'settings.json'
            path.write_text(json.dumps({'institutional_managers':[{'name':'Example Fund','cik':320193}],
                                        'social_accounts':['test.bsky.social'],'social_cashtags':['GME']}))
            cfg=load_config(path)
        self.assertEqual(len(cfg['institutional_managers']),1)
        with patch('market_collection_runner.run_13f',return_value=([{'source':'institutional','event_id':'a'}],[])) as thirteen,\
             patch('market_collection_runner.run_social',return_value=([{'source':'social','event_id':'b'}],[])) as social:
            rows,issues=collect_once(cfg,pause=0,include_news=False,include_sec=False)
        self.assertEqual(len(rows),2)
        thirteen.assert_called_once();social.assert_called_once()

if __name__=='__main__':unittest.main()
