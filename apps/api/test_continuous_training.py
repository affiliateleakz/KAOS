"""Service data minimization, model ownership, held-out timing and deployment boundaries."""
import asyncio
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
import training_samples as samples
import training_service as service
import training_worker as worker
from continuous_models import eligible,fit,prospective


def sample(**changes):
    stamp=1700000000000
    return {'sampleId':'trade-1','platform':'pocket_option','asset':'EURUSD_OTC','timeframe':'5s','expiration':'20s','direction':'BUY','outcome':'WIN','entryPrice':1.0,'settlementPrice':1.1,'decisionAt':stamp,'settledAt':stamp+20000,'sampleType':'REAL','accountMode':'REAL','features':{'x':[.1]*104,'email':'private@example.com','balance':9999},**changes}


def test_training_sample_is_whitelisted_and_masks_account_visual_context():
    row=samples.minimized(sample(),1700000100000)
    assert row['scope']=='pocket_option:binary:5s:20s:real' and row['label']==1
    assert 'email' not in str(row) and 'balance' not in row and 'features' not in row
    assert row['x'][88:]==[0.0]*16 and row['timingQuality']=='explicit'
    assert samples.minimized(sample(decisionAt=None),1700000100000)['timingQuality']=='inferred'


@pytest.mark.parametrize('changes',[{'outcome':'LOSS'},{'decisionAt':1700000050000},{'features':{'x':[float('nan')]*104}},{'features':{'x':[0]*88}},{'platform':'coinbase'},{'timeframe':'1m'}])
def test_bad_or_mixed_scope_samples_are_rejected(changes):
    with pytest.raises(ValueError):samples.minimized(sample(**changes),1700000100000)


def test_required_learning_does_not_depend_on_legacy_opt_in_and_scopes_dedup_per_member(monkeypatch):
    monkeypatch.setattr(samples,'ensure_indexes',AsyncMock())
    store=SimpleNamespace(update_one=AsyncMock(return_value=SimpleNamespace(upserted_id='new')))
    monkeypatch.setattr(samples,'db',SimpleNamespace(ai_training_samples=store,users=SimpleNamespace(update_one=AsyncMock())))
    a=asyncio.run(samples.ingest({'id':'a','collective_learning_consent':False},sample()))
    first=store.update_one.call_args.args
    asyncio.run(samples.ingest({'id':'b'},sample()))
    second=store.update_one.call_args.args
    assert first[0]['_id']!=second[0]['_id']
    assert a['sharedLearningRequired'] is True and a['policy']==samples.POLICY
    assert 'userId' not in first[1]['$setOnInsert'] and 'email' not in str(first)


def test_pro_cannot_download_shared_or_other_users_models(monkeypatch):
    model_store=SimpleNamespace(find_one=AsyncMock(return_value=None))
    monkeypatch.setattr(service,'get_entitlements',AsyncMock(return_value={'aiTraining':True,'pretrainedModels':False}))
    monkeypatch.setattr(service,'db',SimpleNamespace(ai_training_models=model_store))
    user={'id':'pro-member','role':'user'}
    with pytest.raises(HTTPException) as denied:asyncio.run(service.bundle(source='shared',user=user))
    assert denied.value.status_code==403;model_store.find_one.assert_not_awaited()
    result=asyncio.run(service.bundle(user=user))
    query=model_store.find_one.call_args.args[0]
    assert query['owner']==service.contributor(user) and query['audience']=='personal'
    assert result['available'] is False and result['executionEnabled'] is False
    with pytest.raises(HTTPException):asyncio.run(service.bundle(source='owner',user=user))


def test_shared_model_publication_requires_later_validation(monkeypatch):
    monkeypatch.setattr(service,'db',SimpleNamespace(ai_training_models=SimpleNamespace(find_one=AsyncMock(return_value={'metrics':{'passed':True},'prospective':{'passed':False}}))))
    with pytest.raises(HTTPException) as denied:asyncio.run(service.publish('x',{'id':'owner'}))
    assert denied.value.status_code==409


def test_worker_refuses_a_second_active_process(monkeypatch):
    from pymongo.errors import DuplicateKeyError
    monkeypatch.setattr(worker,'db',SimpleNamespace(ai_worker_locks=SimpleNamespace(update_one=AsyncMock(side_effect=worker.DuplicateKeyError('locked')))))
    assert asyncio.run(worker.cycle(False))['state']=='another_worker_running'


def observations(n=650,offset=0):
    out=[]
    for i in range(n):
        t=1600000000000+(i+offset)*60000;label=i%2
        out.append({'_id':str(i+offset),'asset':'TEST','schema':samples.SCHEMA,'scope':service.DEFAULT_SCOPE,'expirySeconds':20,'timingQuality':'explicit','decisionAt':t,'targetAt':t+20000,'label':label,'x':[float(label)]+[0.0]*103,'contributor':'test-only'})
    return out


def test_native_model_uses_purged_chronology_and_requires_new_future_rows():
    # Artificial separable vectors verify the algorithm only; never stored/published as market models.
    rows=observations();result=fit(rows,service.DEFAULT_SCOPE,int(time.time()*1000))
    assert result['state']=='candidate'
    assert result['trainingEnd']<result['holdoutStart']
    assert result['bundle']['targetHorizonMs']==20000 and result['liveApproved'] is False
    assert prospective(result,rows)['actionableSamples']==0
    assert prospective(result,observations(200,offset=1000))['passed'] is True
    assert eligible(rows,'pocket_option:binary:5s:45s:real')==[]
    assert eligible([{**r,'timingQuality':'inferred'} for r in rows],service.DEFAULT_SCOPE)==[]


def test_model_routes_require_auth_and_owner_publication(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    app=FastAPI();app.include_router(service.router);app.include_router(service.admin_router)
    with TestClient(app) as client:
        assert client.get('/api/v1/ai/training/bundle').status_code==401
        app.dependency_overrides[service.get_current_user]=lambda:{'id':'pro','role':'user'}
        assert client.post('/api/admin/ai/continuous/publish/'+'a'*64).status_code==403


def test_revoked_installation_cannot_download_model(monkeypatch):
    request=SimpleNamespace(headers={'X-Device-Id':'revoked'})
    monkeypatch.setattr(service,'db',SimpleNamespace(devices=SimpleNamespace(find_one=AsyncMock(return_value={'revoked':True}))))
    with pytest.raises(HTTPException) as denied:asyncio.run(service.download_bundle(request,service.DEFAULT_SCOPE,'auto',{'id':'user'}))
    assert denied.value.status_code==403
