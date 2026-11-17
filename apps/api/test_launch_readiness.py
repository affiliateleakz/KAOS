"""Owner-only read-only launch evidence, never a false launch certification."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from auth import get_current_user
import launch_readiness as launch


class Cursor:
    def sort(self,*a):return self
    def limit(self,*a):return self
    async def to_list(self,*a):return []


def test_launch_report_does_not_expose_credentials_or_claim_verified_launch(monkeypatch):
    db=SimpleNamespace(ai_worker_state=SimpleNamespace(find_one=AsyncMock(return_value=None)),ai_training_models=SimpleNamespace(count_documents=AsyncMock(return_value=0)),webhook_events=SimpleNamespace(find=lambda *a:Cursor()))
    monkeypatch.setattr(launch,'db',db)
    monkeypatch.setattr(launch,'get_plans',AsyncMock(return_value=[{'id':key,'amount':amount} for key,amount in {'pro':2995,'pro_yearly':29995,'ultimate':9995,'ultimate_yearly':99595}.items()]))
    monkeypatch.setattr(launch,'availability',AsyncMock(return_value={'configurationReady':True,'checkoutEnabled':False,'mode':'live','note':'Validation mode blocks billing'}))
    monkeypatch.setattr(launch.commerce_providers,'document',AsyncMock(return_value={'encrypted':{'secret_key':'fixture-secret-ciphertext'},'lastCheck':{'ok':True,'mode':'sandbox'}}))
    result=asyncio.run(launch.report());checks={c['id']:c for c in result['checks']}
    assert checks['plans']['state']=='configured'
    assert checks['stripe_connection']['state']=='unverified'
    assert checks['worker']['state']=='not_running'
    assert checks['models']['state']=='not_available'
    assert result['launchCertified'] is False and result['activationPerformed'] is False
    assert 'fixture-secret-ciphertext' not in str(result)


def test_launch_endpoint_requires_super_admin(monkeypatch):
    fake=AsyncMock(return_value={'launchCertified':False,'activationPerformed':False});monkeypatch.setattr(launch,'report',fake)
    app=FastAPI();app.include_router(launch.router)
    with TestClient(app) as client:
        path='/api/admin/launch/readiness'
        assert client.get(path).status_code==401
        app.dependency_overrides[get_current_user]=lambda:{'id':'member','role':'admin'}
        assert client.get(path).status_code==403;fake.assert_not_awaited()
        app.dependency_overrides[get_current_user]=lambda:{'id':'owner','role':'super_admin'}
        response=client.get(path)
        assert response.status_code==200 and response.headers['cache-control']=='private, no-store'
