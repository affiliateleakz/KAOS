import asyncio
import copy
from datetime import datetime,timezone,timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
import radar_research as research
import radar_scoring as scoring
import radar_opportunities as opportunities
from kaos_radar_ai import evidence_features,reported_transactions

NOW=datetime.now(timezone.utc)
ASSET={'symbol':'AAPL','asset_class':'stock'}


def item(source='news',**extra):
 return {'asset':'AAPL','asset_class':'stock','source':source,'direction':'neutral','strength':.8,
         'event_id':'event:'+source,'published_at':(NOW-timedelta(minutes=5)).isoformat(),'observed_at':NOW.isoformat(),
         'summary':'Distinct '+source+' fixture','source_url':'https://example.com/'+source,**extra}


def quote(price=100):
 return {'price':price,'feature_vector':[.01,.02,.03,.02,1.1,2,.02],
         'source':'Fixture candles','source_time':(NOW-timedelta(minutes=1)).isoformat()}


def trending(mentions=64):
 return {'state':'complete','stale':False,'fetched_at':NOW.isoformat(),
         'rankings':[{'symbol':'AAPL','name':'Apple','mentions':mentions,'previous_mentions':32,'rank':1,'mention_change':mentions-32}]}


class Cursor:
 def __init__(self,rows):self.rows=rows
 def sort(self,*args):return self
 def limit(self,*args):return self
 async def to_list(self,*args):return copy.deepcopy(self.rows)


class Store:
 def __init__(self,rows=None):self.docs={};self.rows=rows or []
 async def find_one(self,q):return copy.deepcopy(self.docs.get(q['_id']))
 async def update_one(self,q,update,**kwargs):self.docs.setdefault(q['_id'],{}).update(copy.deepcopy(update.get('$set',{})))
 def find(self,q,*args):return Cursor([r for r in self.rows if r['source']==q['source']])


def test_all_evidence_categories_contribute_without_promoting_neutral_whales():
 rows=[item(source,direction='bullish') for source in ('insider','politician','filing','institutional','options_flow','liquidity','macro','dark_pool','short_interest')]
 rows.append(item('onchain',direction='neutral'))
 channel_data=scoring.channels(rows,NOW)
 ai={'model_state':'collecting','sentiment':{},'evidence_channels':channel_data,'attention':scoring.attention(ASSET,trending())}
 card=scoring.score(ASSET,quote(),ai,NOW)
 assert card['components']['disclosures']>0
 assert card['components']['large_holder_activity']>0
 assert card['components']['derivatives_macro_liquidity']>0
 assert card['components']['attention']>0
 assert channel_data['onchain']['balance']==0 and channel_data['onchain']['count']==1
 assert card['coverage_percent']<100 and card['direction']=='BUY'
 # Opposing evidence lowers the shared score rather than being ignored.
 bearish=scoring.channels([item(source,direction='bearish') for source in ('insider','macro','institutional')],NOW)
 assert scoring.score(ASSET,quote(),{**ai,'evidence_channels':bearish},NOW)['score']<card['score']


def test_duplicates_future_events_and_common_disclosure_urls_are_handled_correctly():
 first=item('insider',event_id='sec-form4-txn:cik:accession:0:date:P',summary='Reported purchase')
 second=item('insider',event_id='sec-form4-txn:cik:accession:1:date:S',summary='Reported sale')
 _,cited=evidence_features([first,copy.deepcopy(first),second],'AAPL','stock',NOW)
 assert len(cited)==2,'Different transactions in one filing URL must not collapse'
 counts=reported_transactions(cited)
 assert counts[0]>0 and counts[1]>0
 data=scoring.channels(cited+[first,item('macro',published_at=(NOW+timedelta(hours=1)).isoformat())],NOW)
 assert data['insider']['count']==2 and data['macro']['count']==0
 assert data['insider']['balance']==0,'Reported buying/selling is context, not guessed price direction'


def test_research_and_discovery_use_the_same_score_snapshot_and_price(monkeypatch):
 fake=SimpleNamespace(kaos_asset_reports=Store())
 monkeypatch.setattr(research,'db',fake)
 monkeypatch.setattr(research.native,'ensure_indexes',AsyncMock())
 async def assessment(asset,market,evidence,now,discovery):
  return {'symbol':'AAPL','asset_class':'stock','model_state':'collecting','direction':'WAIT',
          'source_time':market['source_time'],'sentiment':{'sources':{'news':{'samples':3,'score':.5,'bullish':2,'bearish':1,'neutral':0}}},
          'attention':scoring.attention(asset,discovery),'evidence_channels':scoring.channels([],now)}
 model=AsyncMock(side_effect=assessment);monkeypatch.setattr(research.native,'assessment',model)
 async def run():
  context={'evidence':[],'source_status':[]}
  report=await research.asset_report(ASSET,context,trending(),quote())
  play=opportunities.setup(ASSET,quote(),report,NOW)
  assert play['score']==report['scorecard']['score']
  assert play['score_components']==report['scorecard']['components']
  assert report['attention']['mentions']==64
  assert report['sentiment']['sources']['news']['samples']==3
  cached=await research.asset_report(ASSET,context,trending(),quote(110))
  reused=opportunities.setup(ASSET,quote(110),cached,NOW)
  assert model.await_count==1 and reused['reference_entry']==100,'Cached score cannot be paired with a different price frame'
 asyncio.run(run())


def test_context_reuses_sources_and_maps_explicit_underlying_options_flow(monkeypatch):
 flow=item('options_flow',asset_class='option',direction='bullish')
 fake=SimpleNamespace(kaos_evidence_cache=Store(),kaos_evidence_locks=Store(),kaos_intelligence=Store([flow,item('institutional',asset_class='etf'),item('institutional',asset_class='crypto',event_id='unrelated-crypto')]))
 monkeypatch.setattr(research,'db',fake)
 monkeypatch.setattr(research.radar_settings,'settings',AsyncMock(return_value={}))
 async def source(session,provider,asset):
  return {'provider':provider,'asset':asset['symbol'],'asset_class':asset['asset_class'],
          'state':'no_matches','records':[],'observations':0}
 fetch=AsyncMock(side_effect=source)
 # Bind the session argument explicitly for this controlled source fixture.
 async def call(self,p,a):return await fetch(self,p,a)
 monkeypatch.setattr(research.Sources,'run',call)
 async def run():
  first=await research.context([ASSET]);second=await research.context([ASSET])
  assert fetch.await_count==4,'Second research view must not repeat provider fetches'
  used_flow=next(r for r in first['evidence'] if r['source']=='options_flow')
  assert used_flow['asset_class']=='stock'
  assert used_flow['original_asset_class']=='option'
  assert any(r.get('original_asset_class')=='etf' for r in first['evidence'])
  assert all(r['event_id']!='unrelated-crypto' for r in first['evidence'])
  assert second['evidence'][0]['id']==first['evidence'][0]['id']
 asyncio.run(run())


def test_one_article_can_inform_multiple_stocks_without_being_dropped(monkeypatch):
 assets=[ASSET,{'symbol':'MSFT','asset_class':'stock'}]
 fake=SimpleNamespace(kaos_evidence_cache=Store(),kaos_evidence_locks=Store(),kaos_intelligence=Store())
 monkeypatch.setattr(research,'db',fake)
 monkeypatch.setattr(research.radar_settings,'settings',AsyncMock(return_value={}))
 async def run_source(self,provider,asset):
  records=[item(asset=asset['symbol'])] if provider=='news' else []
  return {'provider':provider,'asset':asset['symbol'],'asset_class':'stock','state':'collected' if records else 'no_matches','records':records}
 monkeypatch.setattr(research.Sources,'run',run_source)
 rows=asyncio.run(research.context(assets))['evidence']
 assert {r['asset'] for r in rows}=={'AAPL','MSFT'}
 assert len(rows)==2


def test_news_query_article_ids_are_preserved_but_tracking_duplicates_are_not():
 first=item(event_id='one',summary='Headline one',source_url='https://example.com/news?id=1')
 second=item(event_id='two',summary='Headline two',source_url='https://example.com/news?id=2')
 tracked={**first,'event_id':'tracked','source_url':first['source_url']+'&utm_source=feed'}
 _,used=evidence_features([first,second,tracked],'AAPL','stock',NOW)
 assert len(used)==2
 assert scoring.channels([item('macro',direction='bullish',strength=float('nan'))],NOW)['macro']['count']==0
