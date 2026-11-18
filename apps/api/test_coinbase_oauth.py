"""Local-only OAuth regressions; no real accounts, provider calls or orders."""
import pytest
from fastapi import HTTPException
from cryptography.fernet import Fernet
import coinbase_oauth as oauth


def test_grant_proof_rejects_missing_and_transfer_permissions():
    granted = ' '.join(oauth.SCOPES | {'offline_access'})
    assert set(oauth.scopes(granted)) >= oauth.SCOPES
    for value in ('', None, granted+' wallet:transactions:send', granted+' wallet:transactions:transfer'):
        with pytest.raises(ValueError):oauth.scopes(value)


def test_rotating_tokens_encrypted_and_expiry_bounded(monkeypatch):
    monkeypatch.setenv('KAOS_BROKER_VAULT_KEY', Fernet.generate_key().decode())
    payload = {'access_token':'local-access-fixture','refresh_token':'local-refresh-fixture',
               'token_type':'Bearer','expires_in':3600,'scope':' '.join(oauth.SCOPES)}
    saved = oauth.token_fields(payload)
    assert 'local-access-fixture' not in str(saved)
    assert oauth.vault().decrypt(saved['oauth_access_enc'].encode()).decode() == payload['access_token']
    for changed in ({'scope':'wallet:accounts:read'}, {'expires_in':0}, {'token_type':'MAC'}, {'refresh_token':''}):
        with pytest.raises((ValueError,KeyError)):oauth.token_fields({**payload,**changed})


def test_owner_callback_requires_https_fixed_route(monkeypatch):
    monkeypatch.setenv('KAOS_COINBASE_OAUTH_CLIENT_ID','fixture')
    monkeypatch.setenv('KAOS_COINBASE_OAUTH_CLIENT_SECRET','fixture')
    for uri in ('http://api.example.com/api/v1/broker-connections/coinbase/oauth/callback',
                oauth.CALLBACK+'?redirect=evil', 'https://api.example.com/wrong'):
        monkeypatch.setenv('KAOS_COINBASE_OAUTH_REDIRECT_URI',uri)
        with pytest.raises(HTTPException):oauth.settings()


@pytest.mark.asyncio
async def test_callback_replay_and_expiry_do_not_exchange_tokens(monkeypatch):
    class States:
        async def find_one_and_delete(self, query):return None
    class Database:
        coinbase_oauth_states=States()
    monkeypatch.setattr(oauth,'db',Database())
    def forbidden(*args,**kwargs):raise AssertionError('Provider must not be contacted')
    monkeypatch.setattr(oauth.httpx,'AsyncClient',forbidden)
    assert (await oauth.callback(state='random-fixture-state-with-no-record',code='fixture')).status_code==400
