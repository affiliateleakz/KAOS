"""Coinbase connection contract with fake provider I/O. No real accounts or orders."""
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519
from fastapi import FastAPI
from fastapi.testclient import TestClient

from auth import get_current_user
import routes_broker_connections as routes
import routes_coinbase as gateway
from broker_vault import vault


@pytest.fixture
def setup(monkeypatch):
    monkeypatch.setenv('KAOS_BROKER_VAULT_KEY', Fernet.generate_key().decode())
    monkeypatch.delenv('KAOS_BROKER_VAULT_PREVIOUS_KEYS', raising=False)
    monkeypatch.delenv('KAOS_COINBASE_LIVE_ORDERS', raising=False)
    secret = ec.generate_private_key(ec.SECP256R1()).private_bytes(serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
    payload = {'key_name': 'organizations/test-org/apiKeys/test-key', 'private_key': secret}
    connections = SimpleNamespace(find_one=AsyncMock(return_value=None), update_one=AsyncMock(), insert_one=AsyncMock(), delete_many=AsyncMock())
    database = SimpleNamespace(broker_connections=connections, coinbase_active_slots=SimpleNamespace(find_one=AsyncMock(return_value=None)))
    provider = SimpleNamespace(get_api_key_permissions=lambda: {'can_view': True, 'can_trade': False, 'can_transfer': False},
        get_accounts=lambda **kw: {'accounts': [{'currency': 'USD', 'uuid': 'private-account-id'}], 'has_next': True},
        get_products=lambda **kw: {'products': [{'product_id': 'BTC-USD', 'price': '100', 'private': 'not-public'},
                                              {'product_id': 'BTC-EUR', 'price': '90'}]})
    monkeypatch.setattr(routes, 'db', database)
    monkeypatch.setattr(routes, 'client_for', lambda *args: provider)
    app = FastAPI(); app.include_router(routes.router)
    app.dependency_overrides[get_current_user] = lambda: {'id': 'member-a'}
    with TestClient(app) as client:
        yield SimpleNamespace(client=client, app=app, connections=connections, database=database,
                              payload=payload, provider=provider)


def save(setup):
    return setup.client.put('/api/v1/broker-connections/coinbase', json=setup.payload)


def test_verification_encrypts_and_never_authorizes_orders(setup):
    response = save(setup)
    assert response.status_code == 200, response.text
    assert response.headers['cache-control'] == 'private, no-store'
    result = response.json()
    assert result['verified'] and result['account_count_is_partial']
    assert result['mode'] == 'read_only' and not result['live_order_authorized']
    query, update = setup.connections.update_one.call_args.args
    row = update['$set']
    assert query == {'_id': 'member-a:coinbase'}
    assert row['user_id'] == 'member-a'
    assert vault().decrypt(row['private_key_enc'].encode()).decode() == setup.payload['private_key'].strip()
    assert setup.payload['private_key'] not in str(row)
    assert 'private_key' not in response.text and 'key_name_enc' not in response.text
    assert not result['permissions']['can_trade']  # View-only keys are sufficient.


@pytest.mark.parametrize('permissions', [{'can_view': True, 'can_transfer': True},
                                         {'can_view': True}, {'can_view': False, 'can_transfer': False}])
def test_rejects_transfer_or_unknown_permissions_before_saving(setup, permissions):
    setup.provider.get_api_key_permissions = lambda: permissions
    assert save(setup).status_code == 422
    setup.connections.update_one.assert_not_awaited()


def test_upstream_failure_preserves_old_credentials_and_redacts_error(setup):
    def fail(): raise RuntimeError('sensitive upstream response containing submitted secrets')
    setup.provider.get_api_key_permissions = fail
    response = save(setup)
    assert response.status_code == 502
    assert 'sensitive' not in response.text
    setup.connections.update_one.assert_not_awaited()


def test_status_disconnect_and_accounts_are_member_scoped(setup):
    row = {'_id': 'saved', 'broker': 'coinbase', 'user_id': 'member-a', 'verified': True,
           'key_name_enc': vault().encrypt(setup.payload['key_name'].encode()).decode(),
           'private_key_enc': vault().encrypt(setup.payload['private_key'].encode()).decode()}
    setup.connections.find_one.return_value = row
    for path in ('', '/coinbase/status', '/coinbase/accounts', '/coinbase/products'):
        response = setup.client.get('/api/v1/broker-connections' + path)
        assert response.status_code == 200
        assert response.headers['cache-control'] == 'private, no-store'
        assert 'private_key_enc' not in response.text and 'private-account-id' not in response.text
    products = setup.client.get('/api/v1/broker-connections/coinbase/products').json()
    assert products['products'] == [{'product_id': 'BTC-USD', 'price': '100'}]
    assert products['partial_catalog'] is True
    for call in setup.connections.find_one.call_args_list:
        assert call.args[0] == {'user_id': 'member-a', 'broker': 'coinbase'}
    assert setup.client.delete('/api/v1/broker-connections/coinbase').status_code == 200
    setup.connections.delete_many.assert_awaited_once_with({'user_id': 'member-a', 'broker': 'coinbase'})


@pytest.mark.parametrize('live,slot', [(True,None), (False,{'product_id': 'BTC-USD'})])
def test_key_changes_are_blocked_when_gateway_or_positions_are_active(setup, monkeypatch, live, slot):
    if live:
        monkeypatch.setenv('KAOS_COINBASE_LIVE_ORDERS', 'enabled')
        setup.connections.find_one.return_value={'_id':'existing','user_id':'member-a','broker':'coinbase'}
    setup.database.coinbase_active_slots.find_one.return_value = slot
    assert save(setup).status_code == 409
    assert setup.client.delete('/api/v1/broker-connections/coinbase').status_code == 409
    setup.connections.update_one.assert_not_awaited()
    setup.connections.delete_many.assert_not_awaited()


def test_unauthenticated_requests_cannot_reach_vault(setup):
    setup.app.dependency_overrides.clear()
    assert setup.client.get('/api/v1/broker-connections').status_code == 401
    assert save(setup).status_code == 401
    setup.connections.find_one.assert_not_awaited()


@pytest.mark.parametrize('secret', ['a', 'PRIVATE-SENTINEL', '{"privateKey":', 123])
def test_invalid_credential_errors_do_not_echo_input(setup, secret):
    response = setup.client.put('/api/v1/broker-connections/coinbase',
                                json={**setup.payload, 'private_key': secret})
    assert response.status_code == 422
    assert 'PRIVATE-SENTINEL' not in response.text
    setup.connections.update_one.assert_not_awaited()


def test_exported_credentials_json_and_ed25519_are_supported(setup):
    key = ed25519.Ed25519PrivateKey.generate().private_bytes(serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
    name, secret = routes.credentials({'key_name': '', 'private_key': json.dumps({
        'name': setup.payload['key_name'], 'privateKey': key})})
    assert name == setup.payload['key_name'] and secret == key.strip()
    assert routes.credentials({**setup.payload, 'private_key': setup.payload['private_key'].replace('\n', '\\n')})[1] == setup.payload['private_key'].strip()


def test_live_gateway_can_read_previous_vault_key_during_rotation(setup, monkeypatch):
    old_key = Fernet.generate_key()
    row = {field: Fernet(old_key).encrypt(value.encode()).decode() for field, value in
           [('key_name_enc', setup.payload['key_name']), ('private_key_enc', setup.payload['private_key'])]}
    monkeypatch.setenv('KAOS_BROKER_VAULT_PREVIOUS_KEYS', old_key.decode())
    import coinbase.rest
    monkeypatch.setattr(coinbase.rest, 'RESTClient', lambda **kw: kw)
    client = gateway.make_client(row)
    assert client['api_key'] == setup.payload['key_name']
    assert client['api_secret'] == setup.payload['private_key']


def test_oversized_payload_is_rejected_and_invalid_vault_is_sanitized(setup, monkeypatch):
    assert setup.client.put('/api/v1/broker-connections/coinbase', content=b'x'*20001).status_code == 413
    monkeypatch.setenv('KAOS_BROKER_VAULT_KEY', 'invalid-vault-key')
    response = save(setup)
    assert response.status_code == 503 and 'invalid-vault-key' not in response.text


def test_initial_connection_can_be_created_live_without_overwriting_an_existing_key(setup,monkeypatch):
    monkeypatch.setenv('KAOS_COINBASE_LIVE_ORDERS','enabled')
    assert save(setup).status_code==200
    setup.connections.update_one.assert_not_awaited()
    assert setup.connections.insert_one.call_args.args[0]['_id']=='member-a:coinbase'


def test_concurrent_initial_live_connection_is_not_an_overwrite(setup,monkeypatch):
    from pymongo.errors import DuplicateKeyError
    monkeypatch.setenv('KAOS_COINBASE_LIVE_ORDERS','enabled')
    setup.connections.insert_one.side_effect=DuplicateKeyError('already saved')
    assert save(setup).status_code==409
    setup.connections.update_one.assert_not_awaited()
