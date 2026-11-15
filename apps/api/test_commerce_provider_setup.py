import asyncio
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import AsyncMock
from cryptography.fernet import Fernet
import httpx
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import SecretStr
from auth import get_current_user
import commerce_providers as providers
import routes_commerce_admin as routes
import routes_affiliate_connect as connect


@pytest.fixture
def setup(monkeypatch, tmp_path):
    monkeypatch.setattr(providers, 'key_path', lambda: tmp_path / 'private' / 'commerce.key')
    records = {}
    async def find(query): return deepcopy(records.get(query['_id']))
    async def update(query, change, **kwargs):
        doc = records.setdefault(query['_id'], {'_id': query['_id']})
        for key, value in change.get('$set', {}).items():
            if key.startswith('encrypted.'): doc.setdefault('encrypted', {})[key.split('.', 1)[1]] = value
            else: doc[key] = value
        for key in change.get('$unset', {}): doc.pop(key, None)
    database = SimpleNamespace(commerce_provider_settings=SimpleNamespace(find_one=find, update_one=update))
    monkeypatch.setattr(providers, 'db', database); monkeypatch.setattr(routes, 'db', database)
    audit = AsyncMock(); monkeypatch.setattr(routes, 'audit_log', audit)
    monkeypatch.setenv('KAOS_COMMERCE_VAULT_KEY', Fernet.generate_key().decode())
    for info in providers.CATALOG.values():
        for _, env in info['fields'].values(): monkeypatch.delenv(env, raising=False)
    return records, audit


def test_saved_credentials_are_encrypted_never_returned_or_audited(setup):
    records, audit = setup
    result = asyncio.run(routes.save_provider('paypal', routes.ProviderSettings(
        credentials={'client_secret': SecretStr('fixture-secret-only')}), {'id': 'owner'}))
    encrypted = records['paypal']['encrypted']['client_secret']
    assert encrypted != 'fixture-secret-only'
    assert providers.cipher().decrypt(encrypted.encode()).decode() == 'fixture-secret-only'
    assert 'fixture-secret-only' not in str(result)
    assert encrypted not in str(result)
    assert 'fixture-secret-only' not in str(audit.call_args)
    assert next(f for f in result['fields'] if f['name']=='client_secret')['configured']
    asyncio.run(routes.save_provider('paypal', routes.ProviderSettings(credentials={'client_secret':SecretStr('')}), {'id':'owner'}))
    assert records['paypal']['encrypted']['client_secret'] == encrypted
    assert result['paymentsLive'] is False and result['payoutsLive'] is False


def test_missing_dedicated_vault_never_falls_back_to_broker_key(setup, monkeypatch):
    monkeypatch.delenv('KAOS_COMMERCE_VAULT_KEY')
    monkeypatch.setenv('KAOS_BROKER_VAULT_KEY', Fernet.generate_key().decode())
    with pytest.raises(HTTPException) as error:
        asyncio.run(routes.save_provider('paypal', routes.ProviderSettings(credentials={'client_secret':SecretStr('fixture')}), {'id':'owner'}))
    assert error.value.status_code == 503
    assert not setup[0]


@pytest.mark.parametrize('role,expected', [('user',403),('moderator',403),('admin',403),('super_admin',200)])
def test_only_super_admin_can_read_provider_setup(setup, role, expected):
    app=FastAPI();app.include_router(routes.router)
    app.dependency_overrides[get_current_user]=lambda:{'id':'u','role':role}
    with TestClient(app) as client:
        assert client.get('/api/admin/commerce/providers').status_code == expected
        if expected==403:
            assert client.put('/api/admin/commerce/providers/paypal',json={}).status_code==403
            assert client.post('/api/admin/commerce/providers/paypal/test').status_code==403


@pytest.mark.parametrize('provider', ['stripe','paypal','nowpayments'])
def test_checks_only_use_fixed_credential_or_read_endpoints(setup, monkeypatch, provider):
    env={'stripe':{'STRIPE_CONNECT_SECRET_KEY':'sk_test_fixture'},
         'paypal':{'PAYPAL_CLIENT_ID':'fixture-id','PAYPAL_CLIENT_SECRET':'fixture-secret'},
         'nowpayments':{'NOWPAYMENTS_API_KEY':'fixture-key'}}
    for key,value in env[provider].items():monkeypatch.setenv(key,value)
    requests=[]
    def respond(request):
        requests.append((request.method,str(request.url)))
        return httpx.Response(200,json={'stripe':{'id':'acct_fixture'},'paypal':{'access_token':'fixture-token'},'nowpayments':{'btc':{'amount':0}}}[provider])
    client=httpx.AsyncClient
    monkeypatch.setattr(providers.httpx,'AsyncClient',lambda **kwargs:client(transport=httpx.MockTransport(respond),**kwargs))
    result=asyncio.run(providers.check_connection(provider))
    assert result['ok'] is True
    assert requests == [ {'stripe':('GET','https://api.stripe.com/v1/account'),
        'paypal':('POST','https://api-m.sandbox.paypal.com/v1/oauth2/token'),
        'nowpayments':('GET','https://api-sandbox.nowpayments.io/v1/balance')}[provider] ]
    assert 'fixture-token' not in str(result)
    assert 'amount' not in str(result)


def test_connection_failure_never_exposes_provider_error_body(setup,monkeypatch):
    monkeypatch.setenv('PAYPAL_CLIENT_ID','fixture-id');monkeypatch.setenv('PAYPAL_CLIENT_SECRET','fixture-secret')
    client=httpx.AsyncClient
    monkeypatch.setattr(providers.httpx,'AsyncClient',lambda **kwargs:client(transport=httpx.MockTransport(lambda request:httpx.Response(401,json={'message':'sensitive-provider-value'})),**kwargs))
    with pytest.raises(HTTPException) as error:asyncio.run(routes.test_provider('paypal',{'id':'owner'}))
    assert error.value.status_code==502
    assert 'sensitive-provider-value' not in error.value.detail
    assert setup[0]['paypal']['lastCheck']['ok'] is False


def test_unknown_fields_are_rejected_before_storage(setup):
    with pytest.raises(HTTPException):asyncio.run(routes.save_provider('paypal',routes.ProviderSettings(credentials={'seed_phrase':SecretStr('fixture')}),{'id':'owner'}))
    assert not setup[0]


def test_vault_initialization_creates_private_key_without_replacing_it(setup,monkeypatch):
    monkeypatch.delenv('KAOS_COMMERCE_VAULT_KEY')
    providers.initialize_vault()
    path=providers.key_path();original=path.read_bytes()
    assert path.stat().st_mode & 0o777 == 0o600
    assert path.parent.stat().st_mode & 0o777 == 0o700
    assert providers.vault_ready()
    providers.initialize_vault();assert path.read_bytes()==original
    path.write_text('invalid-existing-key')
    with pytest.raises(HTTPException):providers.initialize_vault()
    assert path.read_text()=='invalid-existing-key'


def test_vault_rejects_symlink(setup,monkeypatch,tmp_path):
    monkeypatch.delenv('KAOS_COMMERCE_VAULT_KEY')
    path=providers.key_path();path.parent.mkdir(mode=0o700)
    target=tmp_path/'elsewhere';target.write_text('do-not-change')
    path.symlink_to(target)
    with pytest.raises(HTTPException):providers.initialize_vault()
    assert target.read_text()=='do-not-change'


def test_admin_stripe_credentials_override_legacy_environment_for_onboarding(setup,monkeypatch):
    monkeypatch.setenv('KAOS_STRIPE_CONNECT_ENABLED','true')
    monkeypatch.setenv('STRIPE_CONNECT_SECRET_KEY','sk_test_old_fixture')
    asyncio.run(routes.save_provider('stripe',routes.ProviderSettings(payoutsSelected=True,
        credentials={'connect_secret_key':SecretStr('sk_test_new_fixture')}),{'id':'owner'}))
    assert asyncio.run(connect.resolved_connect_key())=='sk_test_new_fixture'
    asyncio.run(routes.save_provider('stripe',routes.ProviderSettings(payoutsSelected=False),{'id':'owner'}))
    with pytest.raises(HTTPException):asyncio.run(connect.resolved_connect_key())


def test_stripe_profiles_never_cross_test_and_live_environments():
    account={'stripeConnectAccounts':{'test':'acct_test_fixture','live':'acct_live_fixture'}}
    assert connect.account_for_mode(account,'test')=='acct_test_fixture'
    assert connect.account_for_mode(account,'live')=='acct_live_fixture'
    with pytest.raises(HTTPException):connect.account_for_mode({'stripeConnectAccountId':'acct_unknown'},'live')
