import asyncio
import copy
from datetime import datetime,timezone,timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from pydantic import ValidationError
import radar_opportunities as scanner
from radar_options import contracts

NOW=datetime.now(timezone.utc)


def quote(**extra):
 return {'feature_vector':[.01,.02,.03,.02,1.1,2,.02],'source_time':(NOW-timedelta(minutes=1)).isoformat(),'price':100,'source':'Fixture',**extra}


def test_quality_score_is_not_confidence_and_rejects_stale_conflicting_data():
 asset={'symbol':'AAPL','asset_class':'stock'}
 row=scanner.setup(asset,quote(),{'model_state':'collecting'},NOW)
 assert row['score']==80 and not row['ai_confirmed'] and 'not a win probability' in row['score_type']
 assert row['reference_stop']<row['reference_entry']<row['reference_target']
 assert scanner.setup(asset,quote(source_time=(NOW-timedelta(hours=1)).isoformat()),{},NOW) is None
 assert scanner.setup(asset,quote(),{'model_state':'active','direction':'SELL'},NOW) is None
 assert scanner.setup(asset,quote(feature_vector=[.5,.6,.7,.02,1.1,2,.02]),{},NOW) is None


def test_confirmed_ai_and_news_add_explicit_points_and_forex_omits_volume():
 ai={'model_state':'active','direction':'BUY','sentiment':{'sources':{'news':{'samples':2,'score':.5}}}}
 row=scanner.setup({'symbol':'AAPL','asset_class':'stock'},quote(),ai,NOW)
 assert row['score']==88 and row['ai_confirmed']
 fx=scanner.setup({'symbol':'EURUSD','asset_class':'forex'},quote(feature_vector=[.001,.002,.003,.002,1.1,0,.002]),{},NOW)
 assert fx and 'volume' not in fx['score_components'] and fx['score']<=100


def option_fixture(age=0):
 expiry=(NOW+timedelta(days=14)).strftime('%y%m%d')
 symbol='AAPL'+expiry+'C00100000'
 return {symbol:{'latestQuote':{'t':(NOW-timedelta(seconds=age)).isoformat(),'bp':2,'ap':2.1,'bs':10,'as':10},'greeks':{'delta':.5}}}


def test_options_require_real_fresh_bid_ask_greeks_and_correct_side():
 rows=contracts('AAPL','BUY',option_fixture(),100,NOW)
 assert len(rows)==1 and rows[0]['type']=='CALL' and rows[0]['strike']==100
 assert contracts('AAPL','SELL',option_fixture(),100,NOW)==[]
 assert contracts('AAPL','BUY',option_fixture(age=121),100,NOW)==[]
 wide=option_fixture();next(iter(wide.values()))['latestQuote']['ap']=4
 assert contracts('AAPL','BUY',wide,100,NOW)==[]
 unknown=option_fixture();next(iter(unknown.values()))['greeks']={}
 assert contracts('AAPL','BUY',unknown,100,NOW)==[]


class Store:
 def __init__(self):self.docs={}
 async def find_one(self,query):return copy.deepcopy(self.docs.get(query['_id']))
 async def update_one(self,query,update,**kwargs):self.docs.setdefault(query['_id'],{}).update(update.get('$set',{}))


def test_result_limit_filter_and_shared_cache_never_pad_with_fake_plays(monkeypatch):
 db=SimpleNamespace(kaos_opportunity_scans=Store(),kaos_opportunity_locks=Store(),kaos_opportunity_member_limits=Store())
 monkeypatch.setattr(scanner,'db',db)
 play=scanner.setup({'symbol':'AAPL','asset_class':'stock'},quote(),{},NOW)
 collector=AsyncMock(return_value={'plays':[play],'market':'stocks','scanned':16,'universe_size':16,'execution_enabled':False})
 monkeypatch.setattr(scanner,'collect',collector)
 async def run():
  first=await scanner.opportunities(scanner.OpportunityInput(limit=10),{'id':'alice'})
  assert len(first['plays'])==1 and first['execution_enabled'] is False
  second=await scanner.opportunities(scanner.OpportunityInput(limit=1,minimum_score=95),{'id':'bob'})
  assert second['plays']==[] and collector.await_count==1
 asyncio.run(run())


def test_options_without_access_return_no_contracts_or_data_requests(monkeypatch):
 import radar_settings
 monkeypatch.setattr(radar_settings,'settings',AsyncMock(return_value={}))
 market=AsyncMock();monkeypatch.setattr(scanner.radar_signals,'market',market)
 result=asyncio.run(scanner.collect('options'))
 assert result['plays']==[] and 'OPRA' in result['status_message'] and market.await_count==0


@pytest.mark.parametrize('value',[0,11])
def test_count_is_limited_to_one_to_ten(value):
 with pytest.raises(ValidationError):scanner.OpportunityInput(limit=value)


def test_forex_reads_currency_candles_with_missing_volume(monkeypatch):
 import httpx
 import math
 now=datetime.now(timezone.utc).timestamp();closed=math.floor(now/900)*900
 times=[closed-(80-i)*900 for i in range(80)]
 def handler(request):
  assert request.url.path.endswith('/EURUSD=X')
  return httpx.Response(200,json={'chart':{'result':[{'timestamp':times,'indicators':{'quote':[{
   'low':[1.07]*80,'high':[1.09]*80,'open':[1.08]*80,'close':[1.081]*80,'volume':[None]*80}]}}]}})
 real=httpx.AsyncClient
 monkeypatch.setattr(scanner.radar_signals,'db',SimpleNamespace(kaos_market_signals=Store(),kaos_market_signal_locks=Store()))
 monkeypatch.setattr(scanner.radar_signals.httpx,'AsyncClient',lambda **kwargs:real(transport=httpx.MockTransport(handler),**kwargs))
 out=asyncio.run(scanner.radar_signals.market(SimpleNamespace(symbol='EURUSD',asset_class='forex')))
 assert out['asset_class']=='forex' and len(out['feature_vector'])==7
 assert out['feature_vector'][5]==0


def test_option_adapter_requests_only_read_only_opra(monkeypatch):
 import radar_options
 monkeypatch.setattr(radar_options.radar_settings,'settings',AsyncMock(return_value={'enabled':True,'api_key':'fixture-key','api_secret':'fixture-secret'}))
 request=AsyncMock(return_value={'snapshots':option_fixture()})
 monkeypatch.setattr(radar_options.Sources,'request',request)
 contract,note=asyncio.run(radar_options.chain('AAPL','BUY',100,NOW))
 assert contract['type']=='CALL' and 'win probability' in note
 assert request.call_args.args==('GET','https://data.alpaca.markets/v1beta1/options/snapshots/AAPL')
 assert request.call_args.kwargs['params']['feed']=='opra'
 assert 'fixture-secret' not in str(contract)


def test_discovery_checks_multiple_instruments_with_bounded_concurrency(monkeypatch):
 active=0;peak=0;seen=[]
 async def candles(asset):
  nonlocal active,peak
  active+=1;peak=max(peak,active);seen.append(asset.symbol)
  await asyncio.sleep(0)
  active-=1
  return quote()
 monkeypatch.setattr(scanner.radar_signals,'market',candles)
 monkeypatch.setattr(scanner.native,'ensure_indexes',AsyncMock())
 import radar_research
 monkeypatch.setattr(radar_research,'asset_report',AsyncMock(return_value={'model_state':'collecting'}))
 monkeypatch.setattr(radar_research,'context',AsyncMock(return_value={'evidence':[],'source_status':[]}))
 result=asyncio.run(scanner.collect('crypto'))
 assert len(seen)==12 and peak<=3 and result['scanned']==12
 assert len(result['plays'])==12 and not result['execution_enabled']
 assert all(r['score']>=70 and not r['ai_confirmed'] for r in result['plays'])


def test_expired_option_quotes_are_not_returned_from_cache(monkeypatch):
 db=SimpleNamespace(kaos_opportunity_scans=Store(),kaos_opportunity_locks=Store(),kaos_opportunity_member_limits=Store())
 play=scanner.setup({'symbol':'AAPL','asset_class':'stock'},quote(),{},NOW)
 play['expires_at']=(NOW-timedelta(seconds=1)).isoformat()
 db.kaos_opportunity_scans.docs['options:universe:intraday']={'checked':NOW.timestamp(),'report':{'plays':[play],'market':'options','scanned':10}}
 monkeypatch.setattr(scanner,'db',db)
 out=asyncio.run(scanner.opportunities(scanner.OpportunityInput(market='options',timeframe='intraday'),{'id':'member'}))
 assert out['plays']==[]
