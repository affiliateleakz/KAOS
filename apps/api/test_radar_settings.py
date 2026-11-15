import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
from cryptography.fernet import Fernet
from fastapi import FastAPI
from fastapi.testclient import TestClient
import auth
import radar_settings
import routes_radar_admin as admin_api
import routes_radar
import routes_opportunity
import radar_trending  # registers keyless trending and the retired endpoint
import radar_opportunities  # registers the multi-market scanner

class SettingsStore:
 def __init__(self):self.docs={}
 async def find_one(self,query):return self.docs.get(query['_id'])
 async def update_one(self,query,update,**kwargs):
  row=self.docs.setdefault(query['_id'],{})
  for name,value in update['$set'].items():
   if name.startswith('encrypted.'):row.setdefault('encrypted',{})[name.split('.',1)[1]]=value
   else:row[name]=value

def test_saved_credentials_are_encrypted_and_never_returned(monkeypatch):
 store=SettingsStore();fake=SimpleNamespace(radar_provider_settings=store)
 monkeypatch.setenv('KAOS_COMMERCE_VAULT_KEY',Fernet.generate_key().decode())
 monkeypatch.setattr(radar_settings,'db',fake);monkeypatch.setattr(admin_api,'db',fake);monkeypatch.setattr(admin_api,'audit_log',AsyncMock())
 async def run():
  result=await admin_api.save('x',admin_api.ProviderInput(credentials={'bearer_token':'fixture-private-token'}),{'id':'owner'})
  assert result['configured'] is True and 'fixture-private-token' not in str(result)
  assert store.docs['x']['encrypted']['bearer_token']!='fixture-private-token'
  assert (await radar_settings.settings('x'))['bearer_token']=='fixture-private-token'
  await admin_api.save('x',admin_api.ProviderInput(credentials={'bearer_token':''}),{'id':'owner'})
  assert (await radar_settings.settings('x'))['bearer_token']=='fixture-private-token'
 asyncio.run(run())

def test_admin_setup_rejects_non_owner_and_member_scan_rejects_free_access(monkeypatch):
 app=FastAPI();app.include_router(admin_api.router);app.include_router(routes_radar.router)
 app.dependency_overrides[auth.get_current_user]=lambda:{'id':'member','role':'user'}
 monkeypatch.setattr(routes_opportunity,'get_entitlements',AsyncMock(return_value={'scanners':False}))
 with TestClient(app) as client:
  assert client.get('/api/admin/radar/providers').status_code==403
  assert client.post('/api/admin/radar/model/train',json={'group':'stock'}).status_code==403
  assert client.post('/api/admin/radar/model/activate',json={'group':'stock','version':'fixture'}).status_code==403
  assert client.put('/api/admin/radar/providers/x',json={'credentials':{'bearer_token':'fixture'}}).status_code==403
  assert client.get('/api/v1/intelligence/scan/status').status_code==403
  assert client.post('/api/v1/intelligence/social/mentions').status_code==403
  assert client.post('/api/v1/intelligence/signals/opportunities',json={'market':'stocks'}).status_code==403
  assert client.post('/api/v1/intelligence/scan',json={'assets':[{'symbol':'AAPL','asset_class':'stock'}]}).status_code==403


def test_radar_provider_catalog_has_no_external_ai_key_or_model():
 assert 'openai' not in radar_settings.CATALOG
 assert 'model' not in admin_api.ProviderInput.model_fields


def test_model_activation_rejects_unvalidated_candidates(monkeypatch):
 from fastapi import HTTPException
 import pytest
 monkeypatch.setattr(admin_api,'db',SimpleNamespace(kaos_radar_models=SimpleNamespace(find_one=AsyncMock(return_value=None))))
 with pytest.raises(HTTPException) as error:
  asyncio.run(admin_api.activate_model(admin_api.ActivateInput(group='stock',version='fixture'),{'id':'owner'}))
 assert error.value.status_code==409


def test_validated_local_model_activation_expires_cache_without_enabling_orders(monkeypatch):
 import time
 from kaos_radar_ai import SCHEMA,FEATURES
 candidate={'_id':'candidate:crypto','state':'candidate','version':'fixture-v1','bundle':{'schema':SCHEMA,'features':list(FEATURES),'means':[0]*len(FEATURES),'scales':[1]*len(FEATURES),'weights':[0]*len(FEATURES),'bias':0,'trained_through':time.time()-3600}}
 models=SimpleNamespace(find_one=AsyncMock(return_value=candidate),update_one=AsyncMock())
 scans=SimpleNamespace(update_many=AsyncMock())
 monkeypatch.setattr(admin_api,'db',SimpleNamespace(kaos_radar_models=models,kaos_radar_scans=scans))
 monkeypatch.setattr(admin_api,'audit_log',AsyncMock())
 out=asyncio.run(admin_api.activate_model(admin_api.ActivateInput(group='crypto',version='fixture-v1'),{'id':'owner'}))
 assert out['state']=='active' and out['execution_enabled'] is False
 assert models.update_one.call_args.args[0]=={'_id':'crypto'}
 assert models.update_one.call_args.args[1]['$set']['state']=='active'
 assert scans.update_many.await_count==1


def test_alpha_vantage_key_is_encrypted_and_write_only(monkeypatch):
 store=SettingsStore();fake=SimpleNamespace(radar_provider_settings=store)
 monkeypatch.setenv('KAOS_COMMERCE_VAULT_KEY',Fernet.generate_key().decode())
 monkeypatch.setattr(radar_settings,'db',fake);monkeypatch.setattr(admin_api,'db',fake);monkeypatch.setattr(admin_api,'audit_log',AsyncMock())
 async def run():
  response=await admin_api.save('alphavantage',admin_api.ProviderInput(credentials={'api_key':'fixture-alpha-key'}),{'id':'owner'})
  assert response['configured'] is True
  assert 'fixture-alpha-key' not in str(response)
  assert store.docs['alphavantage']['encrypted']['api_key']!='fixture-alpha-key'
  assert (await radar_settings.settings('alphavantage'))['api_key']=='fixture-alpha-key'
 asyncio.run(run())
