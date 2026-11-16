"""Training fixtures assert isolation and chronology, not real trading performance."""
import asyncio
import copy
from datetime import datetime,timezone,timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
import kaos_radar_ai as native
from radar_training_profiles import key,outcome
from test_kaos_radar_ai import dataset,Samples,quote


def test_profiles_are_market_and_horizon_specific_and_binary_cannot_leak():
    assert len({key(g,t) for g in ('stock','crypto','forex') for t in ('intraday','daily','weekly','monthly')})==12
    with pytest.raises(ValueError):key('binary','daily')
    with pytest.raises(ValueError):key('stock','30s')
    data=dataset()
    for row in data:row['profile']='stock:weekly'
    assert native.train(data,'crypto:weekly')['state']=='collecting'
    assert native.train(data)['state']=='collecting'
    result=native.train(data,'stock:weekly')
    assert result['bundle']['profile']=='stock:weekly'


def test_weekend_observation_labels_future_sessions_not_past_friday_news():
    friday=datetime(2026,11,13,21,tzinfo=timezone.utc).timestamp()
    sunday=friday+2*86400
    row={'timeframe':'daily','group':'stock','source_at':friday,'asof':sunday,'price':100}
    assert outcome(row,[(friday,100)]) is None
    monday=friday+3*86400
    result=outcome(row,[(friday,100),(monday,102)])
    assert result['label']==1 and result['target_at']==monday
    assert outcome(row,[(friday,50),(monday,51)]) is None,'Adjusted historical prices cannot relabel an unadjusted entry'
    assert outcome(row,[(friday,100),(friday+8*86400,102)]) is None


def test_monthly_labels_require_twenty_one_actual_completed_sessions():
    row={'timeframe':'monthly','group':'crypto','source_at':100000,'asof':100000,'price':100}
    history=[(100000+i*86400,100+i) for i in range(22)]
    assert outcome(row,history[:-1]) is None
    result=outcome(row,history)
    assert result['target_at']==history[-1][0] and result['forward_return']==pytest.approx(.21)
    assert outcome(row,history+[history[-1]]) is None


@pytest.mark.parametrize('group',['stock','crypto','forex'])
@pytest.mark.parametrize('frame',['daily','weekly','monthly'])
def test_snapshots_are_immutable_and_model_lookup_uses_exact_profile(monkeypatch,group,frame):
    now=datetime.now(timezone.utc)
    samples=Samples();models=SimpleNamespace(find_one=AsyncMock(return_value=None))
    monkeypatch.setattr(native,'db',SimpleNamespace(kaos_radar_samples=samples,kaos_radar_models=models))
    market={**quote(now-timedelta(days=2)),'planning':True,'timeframe':frame,'horizon':frame}
    report=asyncio.run(native.assessment({'symbol':'AAPL','asset_class':group},market,[],now))
    saved=samples.writes[-1][1]['$setOnInsert']
    assert saved['profile']==key(group,frame) and saved['asof']==now.timestamp()
    assert 'target_at' not in saved and 'label' not in saved
    assert len(saved['x'])==51 and saved['expires_at']>now+timedelta(days=700)
    assert models.find_one.call_args.args[0]=={'_id':key(group,frame),'state':'active'}
    assert report['model_state']=='collecting' and report['direction']=='WAIT'


def test_active_daily_model_decides_signal_and_wrong_profile_is_rejected(monkeypatch):
    now=datetime.now(timezone.utc)
    rows=dataset()
    for r in rows:r['profile']='stock:daily'
    bundle=native.train(rows,'stock:daily')['bundle']
    bundle['trained_through']=(now-timedelta(days=2)).timestamp()
    # Deterministic fixture model, not a performance claim.
    bundle.update(weights=[0.0]*len(native.FEATURES),bias=3)
    model={'bundle':bundle,'activated_at':now.timestamp(),'version':'fixture'}
    monkeypatch.setattr(native,'db',SimpleNamespace(kaos_radar_samples=Samples(),kaos_radar_models=SimpleNamespace(find_one=AsyncMock(return_value=model))))
    market={**quote(now-timedelta(days=2)),'planning':True,'timeframe':'daily','horizon':'1 session'}
    report=asyncio.run(native.assessment({'symbol':'AAPL','asset_class':'stock'},market,[],now))
    assert report['direction']=='BUY' and report['model_state']=='active' and len(report['factors'])==5
    model['bundle']=copy.deepcopy(bundle);model['bundle']['profile']='stock:monthly'
    report=asyncio.run(native.assessment({'symbol':'AAPL','asset_class':'stock'},market,[],now))
    assert report['model_state']=='incompatible' and report['direction']=='WAIT'


def test_admin_status_scopes_counts_and_candidates_to_requested_timeframe(monkeypatch):
    import routes_radar_admin as admin
    counts=AsyncMock(return_value=0);models=AsyncMock(return_value=None)
    monkeypatch.setattr(admin,'db',SimpleNamespace(kaos_radar_samples=SimpleNamespace(count_documents=counts),kaos_radar_models=SimpleNamespace(find_one=models)))
    report=asyncio.run(admin.model_status({'id':'owner'},'monthly'))
    assert all(r['timeframe']=='monthly' for r in report['groups'])
    assert {r['profile'] for r in report['groups']}=={'stock:monthly','crypto:monthly','forex:monthly'}
    assert all(call.args[0]['timeframe']=='monthly' for call in counts.call_args_list)
    assert report['binary_trainer']['admin_url']=='/admin/kaos-ai'


def test_admin_cannot_activate_a_model_from_another_timeframe(monkeypatch):
    import routes_radar_admin as admin
    import time
    from fastapi import HTTPException
    candidate={'bundle':{'schema':native.SCHEMA,'profile':'stock:weekly','trained_through':time.time()-86400}}
    monkeypatch.setattr(admin,'db',SimpleNamespace(kaos_radar_models=SimpleNamespace(find_one=AsyncMock(return_value=candidate))))
    with pytest.raises(HTTPException) as exc:
        asyncio.run(admin.activate_model(admin.ActivateInput(group='stock',timeframe='monthly',version='fixture'),{'id':'owner'}))
    assert exc.value.status_code==409
