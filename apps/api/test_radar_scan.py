import asyncio
import copy
from datetime import datetime,timezone,timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError
import routes_radar as radar

class Cursor:
 def __init__(self,rows):self.rows=rows
 def sort(self,*args):return self
 def limit(self,n):self.rows=self.rows[:n];return self
 async def to_list(self,n=None,*,length=None):return copy.deepcopy(self.rows[:length if length is not None else n])
class Store:
 def __init__(self):self.docs={};self.writes=[]
 async def find_one(self,query):return copy.deepcopy(self.docs.get(query['_id']))
 async def find_one_and_update(self,query,update,**kwargs):
  key=query['_id'];field=next(iter(query['$or'][0]));stamp=query['$or'][0][field]['$lte']
  if self.docs.get(key,{}).get(field,'')>stamp:raise DuplicateKeyError('Fixture duplicate lease')
  self.docs.setdefault(key,{'_id':key}).update(update['$set']);return self.docs[key]
 async def update_one(self,query,update,**kwargs):self.docs.setdefault(query['_id'],{'_id':query['_id']}).update(update.get('$set',{}))
 async def delete_many(self,query):pass
 async def bulk_write(self,writes,**kwargs):self.writes.extend(writes)
 def find(self,query,*args):return Cursor([value for value in self.docs.values() if value.get('user_id')==query.get('user_id') and 'result' in value])

@pytest.fixture
def db(monkeypatch):
 value=SimpleNamespace(kaos_radar_scans=Store(),kaos_radar_limits=Store(),kaos_intelligence=Store(),kaos_social_mentions=Store(),kaos_radar_models=Store())
 monkeypatch.setattr(radar,'db',value)
 monkeypatch.setattr(radar,'analyze',AsyncMock(return_value={'state':'complete','model':'KAOS local fixture','report':{'assets':[]}}))
 async def config(provider):return {'enabled':True,'api_key':'','model':'fixture-model'}
 monkeypatch.setattr(radar.radar_settings,'settings',config)
 return value

def sample():
 now=datetime.now(timezone.utc)
 return {'asset':'AAPL','asset_class':'stock','source':'social','provider':'reddit','direction':'neutral','strength':.3,
         'event_id':'reddit:fixture','observed_at':now.isoformat(),'published_at':(now-timedelta(minutes=1)).isoformat(),
         'summary':'Public AAPL earnings discussion','source_url':'https://www.reddit.com/comments/fixture'}

def collected():return [{'provider':'reddit','asset':'AAPL','asset_class':'stock','state':'collected','observations':1,'records':[sample()]}]
def request():return radar.ScanInput(assets=[{'symbol':'AAPL','asset_class':'stock'}],sources=['reddit'])

def test_scan_caches_results_without_repeating_network_or_ai(monkeypatch,db):
 gather=AsyncMock(side_effect=lambda *args:copy.deepcopy(collected()));monkeypatch.setattr(radar,'collect',gather)
 async def run():
  first=await radar.scan(request(),{'id':'owner'});second=await radar.scan(request(),{'id':'owner'})
  assert first['ai']['state']=='complete'
  assert second['cached'] is True and gather.await_count==1
  assert first['trade_execution_enabled'] is False
  assert first['evidence'][0]['provider']=='reddit' and len(db.kaos_intelligence.writes)==1
 asyncio.run(run())

def test_concurrent_identical_scans_have_one_collector_run(monkeypatch,db):
 async def run():
  entered=asyncio.Event();release=asyncio.Event()
  async def gather(*args):entered.set();await release.wait();return copy.deepcopy(collected())
  monkeypatch.setattr(radar,'collect',gather)
  task=asyncio.create_task(radar.scan(request(),{'id':'owner'}));await entered.wait()
  with pytest.raises(HTTPException) as error:await radar.scan(request(),{'id':'owner'})
  assert error.value.status_code==409;release.set();await task
 asyncio.run(run())

def test_distinct_watchlists_cannot_bypass_user_cooldown(monkeypatch,db):
 monkeypatch.setattr(radar,'collect',AsyncMock(side_effect=lambda *args:copy.deepcopy(collected())))
 async def run():
  await radar.scan(request(),{'id':'owner'})
  other=radar.ScanInput(assets=[{'symbol':'BTC','asset_class':'crypto'}],sources=['reddit'])
  with pytest.raises(HTTPException) as error:await radar.scan(other,{'id':'owner'})
  assert error.value.status_code==429
 asyncio.run(run())

def test_latest_scan_is_user_scoped(monkeypatch,db):
 db.kaos_radar_scans.docs['first']={'user_id':'alice','result':{'private_watchlist':'AAPL'}}
 assert asyncio.run(radar.latest_scan({'id':'bob'}))=={'scan':None}
 assert asyncio.run(radar.latest_scan({'id':'alice'}))['scan']=={'private_watchlist':'AAPL'}

def test_failed_source_is_not_replaced_with_synthetic_evidence(monkeypatch,db):
 monkeypatch.setattr(radar,'collect',AsyncMock(return_value=[{'provider':'x','asset':'AAPL','state':'access_denied','observations':None,'records':[]}]))
 out=asyncio.run(radar.scan(request(),{'id':'owner'}))
 assert out['evidence']==[] and out['source_status'][0]['observations'] is None and not db.kaos_intelligence.writes


def test_evidence_sampling_keeps_whales_insiders_and_government_among_social_volume():
    rows=[{**sample(),'id':str(i)} for i in range(100)]
    for source in ('onchain','insider','politician'):
        rows.append({**sample(),'source':source,'provider':source,'id':source})
    output=radar.balanced_evidence(rows,60)
    assert {'onchain','insider','politician'} <= {row['source'] for row in output}
    assert len(output)==60


def test_social_filter_finds_evidence_that_general_recent_sample_would_omit(monkeypatch):
    import routes_opportunity as opportunity
    stamp=datetime.now(timezone.utc)
    social={**sample(),'asset':'GME','observed_at':(stamp-timedelta(minutes=2)).isoformat(),'published_at':(stamp-timedelta(minutes=3)).isoformat()}
    news=[{**sample(),'source':'news','asset':'OTHER','event_id':'headline:'+str(i),'observed_at':stamp.isoformat()} for i in range(5001)]
    class Collection:
        def find(self,query,*args):
            return Cursor([row for row in news+[social] if not query.get('source') or row['source']==query['source']])
    monkeypatch.setattr(opportunity,'db',SimpleNamespace(kaos_intelligence=Collection()))
    async def run():
        general=await opportunity.opportunities(limit=30,user={'id':'member'})
        filtered=await opportunity.opportunities(limit=30,user={'id':'member'},source_filter='social')
        assert not any(row['asset']=='GME' for row in general['results'])
        assert [row['asset'] for row in filtered['results']]==['GME']
        assert filtered['results'][0]['status']=='context_only'
        assert filtered['results'][0]['independent_sources']==1
        assert filtered['results'][0]['evidence'][0]['source']=='social'
    asyncio.run(run())
