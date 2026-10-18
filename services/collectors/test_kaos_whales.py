import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from ethereum_whales import observe_safe_block, rpc_call,fetch_observations
from sec_insider_transactions import parse_form4_xml,extract_form4_links,get_xml
from market_collection_runner import load_config,collect_once

NOW=datetime(2026,10,16,4,30,tzinfo=timezone.utc)
BLOCK_TIME=int(NOW.timestamp())-45
TXID='0x'+'a'*64
class Response:
    def __init__(self,obj=None,raw=None): self.raw=raw if raw is not None else json.dumps(obj).encode()
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def read(self,size=None):return self.raw if size is None else self.raw[:size]

FORM4=b'''<?xml version="1.0" encoding="UTF-8"?>
<ownershipDocument><reportingOwner><reportingOwnerId><rptOwnerName>Jane Doe</rptOwnerName></reportingOwnerId></reportingOwner>
<nonDerivativeTable>
<nonDerivativeTransaction><transactionDate><value>2026-10-14</value></transactionDate><transactionCoding><transactionCode>P</transactionCode></transactionCoding><transactionAmounts><transactionShares><value>1500</value></transactionShares><transactionPricePerShare><value>125.50</value></transactionPricePerShare><transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode></transactionAmounts></nonDerivativeTransaction>
<nonDerivativeTransaction><transactionDate><value>2026-10-15</value></transactionDate><transactionCoding><transactionCode>S</transactionCode></transactionCoding><transactionAmounts><transactionShares><value>200</value></transactionShares><transactionPricePerShare><value>140</value></transactionPricePerShare><transactionAcquiredDisposedCode><value>D</value></transactionAcquiredDisposedCode></transactionAmounts></nonDerivativeTransaction>
<nonDerivativeTransaction><transactionDate><value>2026-10-15</value></transactionDate><transactionCoding><transactionCode>A</transactionCode></transactionCoding><transactionAmounts><transactionShares><value>300</value></transactionShares><transactionPricePerShare><value>0</value></transactionPricePerShare><transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode></transactionAmounts></nonDerivativeTransaction>
</nonDerivativeTable></ownershipDocument>'''

class WhaleTests(unittest.TestCase):
    def test_native_eth_large_transfer_neutral(self):
        b={'number':'0x100','timestamp':hex(BLOCK_TIME),'transactions':[
            {'hash':TXID,'value':hex(501*10**18)}, {'hash':'0x'+'b'*64,'value':hex(20*10**18)}]}
        rows=observe_safe_block(b,500,NOW)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['direction'],'neutral')
        self.assertEqual(rows[0]['source'],'onchain')
        self.assertNotIn('BUY signal',rows[0]['summary'])
        self.assertEqual(rows[0]['event_id'],'eth-mainnet:'+TXID)
    def test_stale_block_ignored(self):
        b={'number':'0x100','timestamp':hex(BLOCK_TIME-9000),'transactions':[]}
        self.assertEqual(observe_safe_block(b,500,NOW),[])
    def test_rpc_only_safe_block_no_secrets_leaked(self):
        calls=[]
        def opener(req,timeout):
            calls.append(req)
            return Response({'jsonrpc':'2.0','result':{'number':'0x1','timestamp':hex(BLOCK_TIME),'transactions':[]}})
        rpc_call('https://example.org/secret-key','eth_getBlockByNumber',['safe',True],opener)
        self.assertEqual(json.loads(calls[0].data)['params'],['safe',True])
        self.assertEqual(calls[0].get_method(),'POST')
        with self.assertRaises(ValueError):rpc_call('http://example.com','eth_getBlockByNumber',['safe',True],opener)
        with self.assertRaises(ValueError):rpc_call('https://example.com','eth_sendTransaction',[{}],opener)
    def test_form4_buy_and_sale_are_neutral_and_delayed(self):
        kw={'symbol':'AAPL','cik':'0000320193','accession':'0000320193-26-000001',
            'published':datetime(2026,10,15,20,tzinfo=timezone.utc),
            'source_url':'https://www.sec.gov/Archives/edgar/data/320193/000032019326000001/doc.xml','now':NOW}
        rows=parse_form4_xml(FORM4,**kw)
        self.assertEqual(len(rows),2)
        self.assertTrue(all(r['direction']=='neutral' for r in rows))
        self.assertIn('purchase',rows[0]['summary'])
        self.assertIn('sale',rows[1]['summary'])
        self.assertIn('transaction date 2026-10-14',rows[0]['summary'])
        self.assertIn('2026-10-15T20:00:00+00:00',rows[0]['published_at'])
        self.assertEqual(rows[0]['event_id'],parse_form4_xml(FORM4,**kw)[0]['event_id'])
    def test_form4_disallows_futures_and_external_entities(self):
        with self.assertRaises(ValueError):parse_form4_xml('<root/>',symbol='AAPL',cik='1',accession='abc',published=NOW,source_url='https://sec.gov',now=NOW)
        with self.assertRaises(ValueError):get_xml('https://evil.test/x.xml','test@example.com')
    def test_filing_links_only_real_primary_xml(self):
        doc={'filings':{'recent':{'form':['4','4','4/A'],
          'accessionNumber':['0000320193-26-000001']*3,
          'primaryDocument':['real.xml','index.html','amend.xml'],
          'filingDate':['2026-10-15']*3,
          'acceptanceDateTime':['2026-10-15T16:00:00']*3}}}
        links=extract_form4_links('0000320193',doc,NOW)
        self.assertEqual(len(links),1)
    def test_runner_eth_missing_rpc(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'config.json'
            p.write_text(json.dumps({'eth_whales_enabled':True,'eth_whales_min_eth':500}))
            cfg=load_config(p)
        with patch.dict('os.environ',{'ETH_RPC_URL':''}):
            rows,issues=collect_once(cfg,pause=0)
        self.assertFalse(rows)
        self.assertTrue(any(e['provider']=='ethereum' for e in issues))
    def test_runner_disallows_invalid_threshold(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'config.json';p.write_text(json.dumps({'eth_whales_min_eth':0}))
            with self.assertRaises(ValueError):load_config(p)

if __name__=='__main__':unittest.main()

class SafeScannerTests(unittest.TestCase):
    def test_incremental_ethereum_safe_blocks_with_checkpoint(self):
        from ethereum_worker import scan_safe_blocks,load_state
        from unittest.mock import patch
        calls=[]
        def mock_block(url,tag,opener=None):
            calls.append(tag)
            h=100 if tag=='safe' else int(tag,16)
            return {'number':hex(h),'timestamp':hex(int(datetime.now(timezone.utc).timestamp())-70),
                    'transactions':[{'hash':'0x'+format(h,'064x'),'value':hex(600*10**18)}]}
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'cursor.json'
            with patch('ethereum_worker.fetch_block',side_effect=mock_block):
                first,progress=scan_safe_blocks('https://example.com',path,500,max_blocks=4,commit=True)
            self.assertEqual(len(first),1)
            self.assertEqual(load_state(path),100)
            calls.clear()
            def next_block(url,tag,opener=None):
                calls.append(tag)
                h=103 if tag=='safe' else int(tag,16)
                return {'number':hex(h),'timestamp':hex(int(datetime.now(timezone.utc).timestamp())-70),
                        'transactions':[{'hash':'0x'+format(h,'064x'),'value':hex(600*10**18)}]}
            with patch('ethereum_worker.fetch_block',side_effect=next_block):
                rows,progress=scan_safe_blocks('https://example.com',path,500,max_blocks=4,commit=True)
            self.assertEqual(len(rows),3)
            self.assertEqual(load_state(path),103)
            self.assertEqual(calls,['safe','0x65','0x66']) # block 103 comes from safe
    def test_checkpoint_doesnt_advance_on_rpc_error(self):
        from ethereum_worker import scan_safe_blocks,save_state,load_state
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'cursor.json';save_state(path,98)
            def bad(url,tag,opener=None):
                if tag=='safe':return {'number':'0x64','timestamp':'0x42','transactions':[]}
                raise ValueError('HTTP unavailable')
            with patch('ethereum_worker.fetch_block',side_effect=bad):
                with self.assertRaises(ValueError):scan_safe_blocks('https://example.com',path,max_blocks=2,commit=True)
            self.assertEqual(load_state(path),98)
    def test_corrupt_checkpoint_fails_closed(self):
        from ethereum_worker import load_state
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'cursor.json';p.write_text('{"last_safe_block":-10}')
            with self.assertRaises(ValueError):load_state(p)
