import json
import tempfile
import unittest
from pathlib import Path
from datetime import datetime,timezone,timedelta
from urllib.parse import parse_qs,urlparse
from options_activity import capture,compare,read_state,save_state,run
from market_collection_runner import load_config

NOW=datetime(2026,10,16,15,30,tzinfo=timezone.utc)

def chain(volume=100,oi=200,bid=1,ask=1.05,which='C'):
    return {'options':{'option':[{'symbol':'SPY261016'+which+'00500000',
       'option_type':'call' if which=='C' else 'put','volume':volume,'open_interest':oi,
       'strike':500,'bid':bid,'ask':ask}]}}

class FakeResponse:
    def __init__(self, data):self.data=data
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def read(self):return json.dumps(self.data).encode()

class ActivityTests(unittest.TestCase):
    def test_volume_increase_neutral(self):
        a=capture('SPY','2026-10-16',chain(),now=NOW)
        b=capture('SPY','2026-10-16',chain(volume=400),now=NOW+timedelta(minutes=5))
        obs=compare(a,b)
        self.assertEqual(len(obs),1)
        self.assertEqual(obs[0]['direction'],'neutral')
        self.assertEqual(obs[0]['source'],'options_flow')
        self.assertIn('300',obs[0]['summary'])
        self.assertNotIn('buying detected',obs[0]['summary'])

    def test_no_initial_baseline(self):
        b=capture('SPY','2026-10-16',chain(volume=999),now=NOW)
        self.assertEqual(compare(None,b),[])

    def test_no_day_rollover(self):
        a=capture('SPY','2026-10-16',chain(),now=NOW)
        b=capture('SPY','2026-10-16',chain(volume=400),now=NOW+timedelta(days=1))
        self.assertEqual(compare(a,b),[])

    def test_no_sandbox_comparison(self):
        a=capture('SPY','2026-10-16',chain(),now=NOW,sandbox=True)
        b=capture('SPY','2026-10-16',chain(volume=400),now=NOW+timedelta(minutes=5),sandbox=False)
        self.assertEqual(compare(a,b),[])

    def test_no_expiration_change(self):
        a=capture('SPY','2026-10-16',chain(),now=NOW)
        b=capture('SPY','2026-10-23',chain(volume=400),now=NOW+timedelta(minutes=5))
        self.assertEqual(compare(a,b),[])

    def test_no_disappearing_volume(self):
        a=capture('SPY','2026-10-16',chain(volume=500),now=NOW)
        b=capture('SPY','2026-10-16',chain(volume=50),now=NOW+timedelta(minutes=5))
        self.assertEqual(compare(a,b),[])

    def test_quote_filters_and_inf(self):
        self.assertEqual(capture('SPY','2026-10-16',chain(ask=2),now=NOW)['contracts'],{})
        self.assertEqual(capture('SPY','2026-10-16',chain(volume=float('inf')),now=NOW)['contracts']['SPY261016C00500000']['volume'],0)

    def test_age_limit(self):
        a=capture('SPY','2026-10-16',chain(),now=NOW)
        b=capture('SPY','2026-10-16',chain(volume=400),now=NOW+timedelta(hours=2))
        self.assertEqual(compare(a,b),[])

    def test_saved_state_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'cache.json'
            self.assertEqual(read_state(path)['snapshots'],{})
            state={'version':1,'snapshots':{'0:SPY':capture('SPY','2026-10-16',chain(),now=NOW)}}
            save_state(path,state)
            self.assertEqual(read_state(path),state)
            self.assertFalse(list(Path(tmp).glob('*.tmp')))

    def test_mocked_transport_and_no_auto_commit(self):
        def opener(req,timeout):
            path=urlparse(req.full_url).path
            if path.endswith('/expirations'):
                return FakeResponse({'expirations':{'date':['2026-10-16']}})
            if path.endswith('/chains'):
                return FakeResponse(chain(volume=400))
            raise AssertionError(path)
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'state.json'
            save_state(p,{'version':1,'snapshots':{'1:SPY':capture('SPY','2026-10-16',chain(),now=NOW,sandbox=True)}})
            alerts,issues,pending=run(['SPY'],'fake-token',state_path=p,now=NOW+timedelta(minutes=5),sandbox=True,opener=opener,pause_seconds=0)
            self.assertFalse(issues)
            self.assertEqual(len(alerts),1)
            self.assertEqual(read_state(p)['snapshots']['1:SPY']['contracts']['SPY261016C00500000']['volume'],100)
            self.assertEqual(pending['snapshots']['1:SPY']['contracts']['SPY261016C00500000']['volume'],400)

    def test_runner_optional_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'cfg.json';p.write_text(json.dumps({'options_activity_underlyings':['spy','AAPL','SPY']}))
            self.assertEqual(load_config(p)['options_activity_underlyings'],['SPY','AAPL'])
            p.write_text(json.dumps({'options_activity_underlyings':['bad&symbol']}))
            with self.assertRaises(ValueError):load_config(p)
            p.write_text(json.dumps({'options_activity_underlyings':['SPY']*31}))
            with self.assertRaises(ValueError):load_config(p)
if __name__=='__main__':unittest.main()
