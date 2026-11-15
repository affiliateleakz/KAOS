"""Local model tests use synthetic fixtures only, never claims of real performance."""
import asyncio
import copy
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
import kaos_radar_ai as ai


class Cursor:
    def __init__(self,rows): self.rows=rows
    def limit(self,*args): return self
    async def to_list(self,*args): return self.rows


class Samples:
    def __init__(self,rows=None): self.rows=rows or [];self.writes=[]
    def find(self,*args): return Cursor(self.rows)
    async def update_one(self,query,update,**kwargs): self.writes.append((query,update))


def quote(now):
    return {'feature_vector':[.01,.02,.03,.01,.7,1.2,.02], 'source_time':now.isoformat(),
            'price':100, 'closed_history':[[now.timestamp()-i*900,100] for i in range(8)]}


def row(now,**extra):
    return {'asset':'AAPL','asset_class':'stock','source':'news','id':'news-1',
            'published_at':(now-timedelta(minutes=5)).isoformat(),'observed_at':now.isoformat(),
            'summary':'AAPL delivers excellent profits','source_url':'https://example.com/news',**extra}


def dataset(n=200):
    return [{'schema':ai.SCHEMA,'asof':i*3600+1,'target_at':i*3600+2701,
             'x':[1 if i%2 else -1]+[0]*(len(ai.FEATURES)-1),'label':i%2} for i in range(n)]


def test_features_are_attributable_deduplicated_and_time_bounded():
    now=datetime.now(timezone.utc)
    examples=[row(now),row(now,id='copy'),row(now,asset='MSFT',summary='MSFT loss'),
              row(now,published_at=(now+timedelta(seconds=1)).isoformat()),
              row(now,summary='Old bankruptcy',published_at=(now-timedelta(days=2)).isoformat())]
    values,used=ai.evidence_features(examples,'AAPL','stock',now)
    assert len(values)==10 and len(used)==1
    assert values[0]>0 and used[0]['id']=='news-1'
    whales=row(now,source='onchain',summary='Unknown wallet transfers 500 ETH')
    assert ai.evidence_features([whales],'AAPL','stock',now)[0][0]==0


def test_model_is_trained_locally_and_insufficient_data_cannot_predict():
    assert ai.train(dataset(50))['state']=='collecting'
    output=ai.train(dataset())
    assert output['state']=='candidate'
    assert output['metrics']['train_samples']>=80
    assert output['metrics']['holdout_samples']>=30
    model=output['bundle']
    assert ai.probability(model,[1]+[0]*(len(ai.FEATURES)-1))>.6
    assert ai.probability(model,[-1]+[0]*(len(ai.FEATURES)-1))<.4
    with pytest.raises(ValueError): ai.probability({**model,'schema':'broker-104'},[0]*len(ai.FEATURES))


def test_holdout_cannot_change_fitted_normalization_or_weights_and_split_is_purged():
    rows=dataset()
    # A training-side outcome reaching into the holdout must be purged.
    rows[149]['target_at']=rows[150]['asof']+1
    first=ai.train(rows)
    changed=copy.deepcopy(rows)
    for r in changed[150:]: r['x'][0]*=1000
    second=ai.train(changed)
    assert first['metrics']['purged']==1
    for field in ('means','scales','weights','bias'):
        assert first['bundle'][field]==second['bundle'][field]


def test_no_model_collects_snapshot_and_returns_wait(monkeypatch):
    now=datetime(2026,11,15,12,tzinfo=timezone.utc)
    samples=Samples()
    monkeypatch.setattr(ai,'db',SimpleNamespace(kaos_radar_sentiment=Samples(),kaos_radar_samples=samples,kaos_radar_models=SimpleNamespace(find_one=AsyncMock(return_value=None))))
    out=asyncio.run(ai.assessment({'symbol':'AAPL','asset_class':'stock'},quote(now),[row(now)],now))
    assert out['direction']=='WAIT' and out['model_state']=='collecting'
    saved=samples.writes[0][1]['$setOnInsert']
    assert saved['asof']==now.timestamp() and saved['target_at']>now.timestamp()+ai.HORIZON
    assert 'label' not in saved and saved['schema']==ai.SCHEMA
    assert len(saved['x'])==len(ai.FEATURES)


def test_labels_use_actual_future_closed_prices_and_do_not_bridge_gaps(monkeypatch):
    now=datetime(2026,11,15,12,tzinfo=timezone.utc)
    pending={'_id':'prior','target_at':now.timestamp(),'source_at':now.timestamp()-3600,'price':99}
    samples=Samples([pending])
    monkeypatch.setattr(ai,'db',SimpleNamespace(kaos_radar_sentiment=Samples(),kaos_radar_samples=samples,kaos_radar_models=SimpleNamespace(find_one=AsyncMock(return_value=None))))
    asset={'symbol':'AAPL','asset_class':'stock'}
    asyncio.run(ai.assessment(asset,quote(now),[],now))
    assert samples.writes[0][1]['$set']['label']==1
    assert samples.writes[0][1]['$set']['forward_return']==pytest.approx(100/99-1)
    samples.writes=[]
    missing=quote(now);missing['closed_history'].pop(2)
    asyncio.run(ai.assessment(asset,missing,[],now))
    assert all('$set' not in update for _,update in samples.writes)


def test_stale_or_missing_market_never_collects_or_predicts(monkeypatch):
    now=datetime.now(timezone.utc)
    samples=Samples()
    monkeypatch.setattr(ai,'db',SimpleNamespace(kaos_radar_sentiment=Samples(),kaos_radar_samples=samples))
    for data in ({},quote(now-timedelta(hours=1))):
        out=asyncio.run(ai.assessment({'symbol':'AAPL','asset_class':'stock'},data,[],now))
        assert out['direction']=='WAIT'
    assert not samples.writes


def test_analysis_never_calls_an_external_ai_service(monkeypatch):
    import radar_signals
    import httpx
    import radar_trending
    monkeypatch.setattr(radar_trending,'snapshot',AsyncMock(return_value={'state':'unavailable'}))
    monkeypatch.setattr(ai,'ensure_indexes',AsyncMock())
    monkeypatch.setattr(ai,'db',SimpleNamespace(kaos_radar_sentiment=Samples(),kaos_social_mentions=SimpleNamespace(find_one=AsyncMock(return_value=None))))
    monkeypatch.setattr(radar_signals,'market',AsyncMock(return_value={}))
    def no_client(*args,**kwargs): raise AssertionError('External AI call attempted')
    monkeypatch.setattr(httpx,'AsyncClient',no_client)
    out=asyncio.run(ai.analyze([{'symbol':'AAPL','asset_class':'stock'}],[],[{'provider':'x','state':'access_denied'}]))
    assert out['report']['assets'][0]['direction']=='WAIT'
    assert 'x: access_denied' in out['report']['coverage_gaps']
    assert out['trade_execution_enabled'] is False


def test_vader_sentiment_and_missing_samples_remain_distinct():
    from radar_sentiment import text_score,summarize
    assert text_score('This is good')>text_score('This is not good')
    result=summarize([{'source':'news','summary':'Excellent growth and profits'}])
    assert result['sources']['news']['bullish']==1
    assert result['sources']['social']['samples']==0
    assert result['sources']['social']['score'] is None


def test_failed_validation_and_old_model_cannot_issue_signal(monkeypatch):
    data=dataset()
    for r in data:r['x']=[0]*len(ai.FEATURES)
    assert ai.train(data)['state']=='validation_failed'
    now=datetime.now(timezone.utc)
    model=ai.train(dataset())['bundle']
    samples=Samples()
    monkeypatch.setattr(ai,'db',SimpleNamespace(kaos_radar_sentiment=Samples(),kaos_radar_samples=samples,
        kaos_radar_models=SimpleNamespace(find_one=AsyncMock(return_value={'bundle':model,'activated_at':now.timestamp()}))))
    out=asyncio.run(ai.assessment({'symbol':'AAPL','asset_class':'stock'},quote(now),[],now))
    assert out['direction']=='WAIT' and out['model_state']=='expired'


def test_recent_discussion_counts_feed_the_native_model_with_missing_source_flags(monkeypatch):
    now=datetime.now(timezone.utc)
    samples=Samples()
    monkeypatch.setattr(ai,'db',SimpleNamespace(kaos_radar_sentiment=Samples(),kaos_radar_samples=samples,
        kaos_radar_models=SimpleNamespace(find_one=AsyncMock(return_value=None))))
    discovery={'state':'complete','fetched_at':now.isoformat(),'stale':False,
               'rankings':[{'symbol':'AAPL','mentions':10,'previous_mentions':5,'rank':2,'upvotes':100}]}
    out=asyncio.run(ai.assessment({'symbol':'AAPL','asset_class':'stock'},quote(now),[],now,discovery))
    assert out['feature_values']['trending_mentions']>0
    assert out['feature_values']['trending_available']==1
    assert out['sentiment']['sources']['social']['score'] is None
    assert out['direction']=='WAIT'
    for missing in ({**discovery,'fetched_at':(now-timedelta(hours=2)).isoformat()}, {**discovery,'rankings':[]}, {**discovery,'stale':True}):
        out=asyncio.run(ai.assessment({'symbol':'AAPL','asset_class':'stock'},quote(now),[],now,missing))
        assert out['feature_values']['trending_available']==0


def test_forex_never_loads_the_stock_or_crypto_model(monkeypatch):
    now=datetime.now(timezone.utc)
    model=SimpleNamespace(find_one=AsyncMock(return_value=None))
    monkeypatch.setattr(ai,'db',SimpleNamespace(kaos_radar_sentiment=Samples(),kaos_radar_samples=Samples(),kaos_radar_models=model))
    out=asyncio.run(ai.assessment({'symbol':'EURUSD','asset_class':'forex'},quote(now),[],now))
    assert out['direction']=='WAIT'
    assert model.find_one.call_args.args[0]=={'_id':'forex','state':'active'}
