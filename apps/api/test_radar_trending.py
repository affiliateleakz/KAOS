import asyncio
from datetime import datetime,timezone,timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from pymongo.errors import DuplicateKeyError
from fastapi import HTTPException
import radar_trending as trending
from radar_sources import SourceIssue


def payload():
 return {'results':[{'ticker':'NVDA','name':'Nvidia','rank':1,'mentions':100,'mentions_24h_ago':80,'rank_24h_ago':3,'upvotes':2000}]}


class Store:
 def __init__(self):self.value=None
 async def find_one(self,q):return self.value
 async def update_one(self,q,update,**kwargs):
  self.value={**(self.value or {}),**update.get('$set',{})}
  for k in update.get('$unset',{}):self.value.pop(k,None)


@pytest.fixture
def stores(monkeypatch):
 fake=SimpleNamespace(kaos_trending_cache=Store(),kaos_trending_locks=Store())
 monkeypatch.setattr(trending,'db',fake)
 return fake


def test_counts_and_rank_changes_are_provider_facts_not_sentiment():
 row=trending.normalize(payload())[0]
 assert row['mentions']==100 and row['mention_change']==20 and row['rank_change']==2
 assert 'sentiment' not in row and 'x' not in row and 'posts' not in row
 raw=payload();raw['results'][0]['mentions_24h_ago']=None
 assert trending.normalize(raw)[0]['mention_change'] is None


@pytest.mark.parametrize('bad',[-1,'NaN',True])
def test_invalid_counts_never_become_zero_mentions(bad):
 raw=payload();raw['results'][0]['mentions']=bad
 with pytest.raises(ValueError):trending.normalize(raw)


def test_shared_cache_requires_no_auth_and_prevents_repeat_fetch(monkeypatch,stores):
 request=AsyncMock(return_value=payload())
 monkeypatch.setattr(trending.Sources,'request',request)
 async def run():
  first=await trending.snapshot();second=await trending.snapshot()
  assert first['state']=='complete' and first['provider_updated_at'] is None
  assert second['cached'] is True and request.await_count==1
  assert request.call_args.args==('GET',trending.URL)
  assert not request.call_args.kwargs
 asyncio.run(run())


def test_outage_is_cached_and_old_rows_are_explicitly_stale(monkeypatch,stores):
 stamp=datetime.now(timezone.utc)
 stores.kaos_trending_cache.value={'checked':stamp.timestamp()-3600,'report':{'fetched_at':(stamp-timedelta(hours=1)).isoformat(),'rankings':trending.normalize(payload()),'state':'complete'}}
 request=AsyncMock(side_effect=SourceIssue('access_denied','Enter a key'))
 monkeypatch.setattr(trending.Sources,'request',request)
 async def run():
  first=await trending.snapshot();second=await trending.snapshot()
  assert first['state']=='unavailable' and first['stale'] is True
  assert first['rankings'][0]['mentions']==100
  assert 'key' not in first['message'] and second['stale'] is True
  assert request.await_count==1
 asyncio.run(run())


def test_lease_does_not_start_another_request(monkeypatch,stores):
 monkeypatch.setattr(stores.kaos_trending_locks,'update_one',AsyncMock(side_effect=DuplicateKeyError('Locked')))
 request=AsyncMock();monkeypatch.setattr(trending.Sources,'request',request)
 out=asyncio.run(trending.snapshot())
 assert out['rankings']==[] and out['state']=='unavailable' and request.await_count==0


def test_retired_scanner_returns_clear_response_and_default_scan_omits_social():
 from routes_radar import ScanInput
 from radar_settings import VISIBLE_PROVIDERS
 with pytest.raises(HTTPException) as error:asyncio.run(trending.retired_social_scanner({'id':'member'}))
 assert error.value.status_code==410
 assert not {'reddit','x','bluesky','facebook'}.intersection(ScanInput(assets=[{'symbol':'AAPL','asset_class':'stock'}]).sources)
 assert not {'reddit','x','bluesky','facebook'}.intersection(VISIBLE_PROVIDERS)
