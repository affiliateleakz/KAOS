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
  assert client.put('/api/admin/radar/providers/x',json={'credentials':{'bearer_token':'fixture'}}).status_code==403
  assert client.get('/api/v1/intelligence/scan/status').status_code==403
  assert client.post('/api/v1/intelligence/scan',json={'assets':[{'symbol':'AAPL','asset_class':'stock'}]}).status_code==403
