import asyncio
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
import httpx
import pytest
from pymongo.errors import DuplicateKeyError
from fastapi import HTTPException
import radar_mentions as mentions
from radar_sources import Sources

NOW=datetime.now(timezone.utc)
SYMBOLS={s:{'name':s,'asset_class':'stock'} for s in ('AAPL','NVDA','IT','AI','BRK.B')}


def post(identity='one',text='$AAPL $AAPL NVDA excellent growth',when=NOW,author='user'):
    return {'id':identity,'text':text,'published_at':when.isoformat(),'author':author,'url':'https://www.reddit.com/comments/'+identity}


def test_extract_counts_tickers_not_ambiguous_words_or_substrings():
    assert mentions.extract('IT is up, AI is good. $IT $AI $brk.b AAPL',SYMBOLS)=={'IT','AI','BRK.B','AAPL'}
    assert mentions.extract('pineAAPL $AAPLfake IT AI nonsense',SYMBOLS)==set()


def test_rank_deduplicates_per_post_and_ignores_stale_future_and_unknown_symbols():
    feeds=[{'provider':'reddit','posts':[post(),post(),post('old',when=NOW-timedelta(days=2)),post('future',when=NOW+timedelta(hours=1)),post('none','UNKNOWN')]},
           {'provider':'x','posts':[post('two','$AAPL terrible loss')]}]
    rows,oldest=mentions.rank(feeds,SYMBOLS,NOW)
    assert rows[0]['symbol']=='AAPL' and rows[0]['mentions']==2
    assert rows[0]['reddit']==1 and rows[0]['x']==1 and rows[0]['unique_authors']==2
    assert rows[0]['bullish']==1 and rows[0]['bearish']==1
    assert rows[1]['symbol']=='NVDA' and rows[1]['mentions']==1
    assert oldest==NOW.isoformat()


def test_platform_feed_uses_authorized_access_and_never_needs_an_ai_provider():
    calls=[]
    def handler(request):
        calls.append(request)
        if request.url.host=='www.reddit.com':return httpx.Response(200,json={'access_token':'fixture-token'})
        if request.url.host=='oauth.reddit.com':
            assert request.url.path=='/r/stocks+wallstreetbets+investing/new'
            return httpx.Response(200,json={'data':{'children':[{'data':{'id':'abc','title':'$AAPL growth','created_utc':NOW.timestamp()}}]}})
        assert request.url.host=='api.x.com' and request.url.params['max_results']=='100'
        assert 'start_time' in request.url.params and '-is:retweet' in request.url.params['query']
        return httpx.Response(403,json={})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            source=Sources({'reddit':{'client_id':'test','client_secret':'test','user_agent':'test'},'x':{'bearer_token':'test'}},client)
            try:return await asyncio.gather(mentions.feed(source,'reddit'),mentions.feed(source,'x'))
            finally:await source.close()
    reddit,x=asyncio.run(run())
    assert reddit['state']=='collected' and reddit['posts'][0]['text'].startswith('$AAPL')
    assert x['state']=='access_denied' and x['inspected'] is None
    assert len(calls)==3


def test_missing_credentials_produce_no_requests_or_zero_mention_claim():
    def no_network(request):raise AssertionError('Unexpected provider request')
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(no_network)) as client:
            source=Sources({},client)
            try:return await mentions.feed(source,'x')
            finally:await source.close()
    result=asyncio.run(run())
    assert result['state']=='setup_required' and result['inspected'] is None


class Store:
    def __init__(self):self.value=None
    async def find_one(self,query):return self.value
    async def update_one(self,query,update,**kwargs):
        self.value={**(self.value or {}),**update.get('$set',{})}


def test_shared_cache_prevents_repeated_collection(monkeypatch):
    cache=Store();locks=Store()
    monkeypatch.setattr(mentions,'db',SimpleNamespace(kaos_social_mentions=cache,kaos_social_mentions_locks=locks))
    monkeypatch.setattr(mentions.radar_settings,'settings',AsyncMock(return_value={}))
    collect=AsyncMock(side_effect=lambda session,p:{'provider':p,'state':'collected','posts':[post()], 'inspected':1})
    monkeypatch.setattr(mentions,'feed',collect)
    monkeypatch.setattr(mentions,'directory',AsyncMock(return_value=(SYMBOLS,'Fixture stock directory')))
    async def run():
        first=await mentions.social_mentions({'id':'alice'})
        second=await mentions.social_mentions({'id':'bob'})
        assert first['rankings'][0]['symbol']=='AAPL'
        assert second['cached'] is True and collect.await_count==2
        assert first['execution_enabled'] is False
    asyncio.run(run())


def test_concurrent_scan_never_launches_another_collector(monkeypatch):
    lock=SimpleNamespace(update_one=AsyncMock(side_effect=DuplicateKeyError('Fixture lock')))
    monkeypatch.setattr(mentions,'db',SimpleNamespace(kaos_social_mentions=Store(),kaos_social_mentions_locks=lock))
    monkeypatch.setattr(mentions.radar_settings,'settings',AsyncMock(return_value={}))
    with pytest.raises(HTTPException) as error:asyncio.run(mentions.social_mentions({'id':'member'}))
    assert error.value.status_code==409
