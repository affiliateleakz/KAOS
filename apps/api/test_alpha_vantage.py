import asyncio
import logging
from datetime import datetime,timezone,timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from pymongo.errors import DuplicateKeyError
import pytest
import alpha_vantage as alpha
from radar_sources import SourceIssue
from radar_news import normalize


class Store:
 def __init__(self):self.rows={}
 async def find_one(self,q):return self.rows.get(q['_id'])
 async def update_one(self,q,update,**kwargs):
  row=self.rows.get(q['_id'])
  if row and q.get('count') and row.get('count',0)>=q['count']['$lt']:raise DuplicateKeyError('Quota')
  if row and q.get('until') and row.get('until',0)>=q['until']['$lt']:raise DuplicateKeyError('Lease')
  row=self.rows.setdefault(q['_id'],{})
  row.update(update.get('$set',{}))
  for k,v in update.get('$inc',{}).items():row[k]=row.get(k,0)+v
  for k in update.get('$unset',{}):row.pop(k,None)


@pytest.fixture
def stores(monkeypatch):
 value=SimpleNamespace(kaos_alpha_cache=Store(),kaos_alpha_locks=Store(),kaos_alpha_usage=Store())
 monkeypatch.setattr(alpha,'db',value)
 monkeypatch.setattr(alpha.radar_settings,'settings',AsyncMock(return_value={'api_key':'fixture-private-key','enabled':True}))
 return value


def test_one_shared_news_request_and_no_credentials_in_report(monkeypatch,stores):
 call=AsyncMock(return_value={'feed':[{'title':'Fixture news'}]})
 monkeypatch.setattr(alpha.Sources,'request',call)
 async def run():
  assert await alpha.news()==[{'title':'Fixture news'}]
  assert await alpha.news()==[{'title':'Fixture news'}]
  assert call.await_count==1
  assert call.call_args.kwargs['params']['function']=='NEWS_SENTIMENT'
  assert 'fixture-private-key' not in str(stores.kaos_alpha_cache.rows)
 asyncio.run(run())


def test_free_quota_blocks_before_outbound_request(monkeypatch,stores):
 from hashlib import sha256
 key=sha256(b'fixture-private-key').hexdigest()+':'+datetime.now(timezone.utc).strftime('%Y-%m-%d')
 stores.kaos_alpha_usage.rows[key]={'count':20}
 call=AsyncMock();monkeypatch.setattr(alpha.Sources,'request',call)
 with pytest.raises(SourceIssue) as error:asyncio.run(alpha.news())
 assert error.value.state=='rate_limited' and call.await_count==0


def test_provider_limit_response_is_cached_instead_of_fake_empty_success(monkeypatch,stores):
 call=AsyncMock(return_value={'Information':'Provider daily allowance exhausted'})
 monkeypatch.setattr(alpha.Sources,'request',call)
 async def run():
  for _ in range(2):
   with pytest.raises(SourceIssue) as error:await alpha.news()
   assert error.value.state=='unavailable'
  assert call.await_count==1
 asyncio.run(run())


def test_missing_key_never_calls_provider(monkeypatch,stores):
 monkeypatch.setattr(alpha.radar_settings,'settings',AsyncMock(return_value={}))
 call=AsyncMock();monkeypatch.setattr(alpha.Sources,'request',call)
 with pytest.raises(SourceIssue) as error:asyncio.run(alpha.news())
 assert error.value.state=='setup_required' and call.await_count==0


def test_news_normalization_retains_sources_and_rejects_future_or_unsafe_links():
 now=datetime.now(timezone.utc)-timedelta(minutes=1)
 good={'title':'Real headline','source':'Publisher','url':'https://example.com/article','time_published':now.strftime('%Y%m%dT%H%M%S'),'ticker_sentiment':[{'ticker':'AAPL'}]}
 rows=normalize([good,{**good,'url':'javascript:alert(1)'},{**good,'time_published':(now+timedelta(days=1)).strftime('%Y%m%dT%H%M%S')}])
 assert len(rows)==1 and rows[0]['tickers']==['AAPL'] and rows[0]['source']=='Publisher'


def test_alpha_query_secrets_are_redacted_from_http_logs(caplog):
 import httpx
 import radar_sources  # installs the request log filter
 with caplog.at_level(logging.INFO,logger='httpx'):
  logging.getLogger('httpx').info('HTTP Request: %s %s "%s %d %s"','GET',httpx.URL('https://www.alphavantage.co/query?apikey=fixture-secret'), 'HTTP/1.1',200,'OK')
 assert 'fixture-secret' not in caplog.text and 'redacted-provider-path' in caplog.text
