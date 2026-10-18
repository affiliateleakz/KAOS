import unittest
from datetime import datetime,timezone,timedelta
from urllib.parse import urlparse,parse_qs
from bluesky_search import summarize_search,fetch_search,run

NOW=datetime(2026,10,16,5,tzinfo=timezone.utc)

def post(symbol='GME',minute=5,uri='a',did='did:plc:hello'):
    at=(NOW-timedelta(minutes=minute)).isoformat()
    return {'uri':f'at://did:plc:hello/app.bsky.feed.post/{uri}',
            'author':{'did':did,'handle':'trader.bsky.social'},
            'record':{'text':f'Watching ${symbol} today','createdAt':at},'indexedAt':at}

class FakeResponse:
    def __enter__(self):return self
    def __exit__(self,*args):pass

def opener(req,timeout=20):
    import io
    url=req.full_url
    assert urlparse(url).hostname=='public.api.bsky.app'
    assert parse_qs(urlparse(url).query)['q']==['$GME']
    return io.BytesIO(b'{"posts":[]}')

class Tests(unittest.TestCase):
    def test_sample(self):
        r=summarize_search('GME',[post(),post(),post(minute=70,uri='b')],now=NOW)
        self.assertEqual(r['direction'],'neutral')
        self.assertIn('1 matched posts',r['summary'])
        self.assertIn('1 posts / 1 authors in preceding',r['summary'])
        self.assertTrue(r['event_id'].startswith('bsky-search:'))
        self.assertLessEqual(datetime.fromisoformat(r['published_at']),datetime.fromisoformat(r['observed_at']))
    def test_reject_not_tag(self):
        self.assertIsNone(summarize_search('GME',[post(symbol='AMC')],now=NOW))
    def test_old_or_future(self):
        self.assertIsNone(summarize_search('GME',[post(minute=121),post(minute=-1,uri='b')],now=NOW))
    def test_allow_public_search(self):
        self.assertEqual(fetch_search('GME',opener=opener),[])
    def test_errors_not_fabricated(self):
        def fail(*a,**k):raise RuntimeError('Unavailable')
        items,issues=run(['GME'],now=NOW,opener=fail)
        self.assertEqual(items,[]);self.assertEqual(issues[0]['provider'],'bluesky_search')
    def test_no_invalid_symbol(self):
        with self.assertRaises(ValueError):fetch_search('../SECRET')

if __name__=='__main__':unittest.main()
