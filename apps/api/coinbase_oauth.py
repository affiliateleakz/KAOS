"""Coinbase partner OAuth: PKCE, encrypted tokens, refresh serialization, bearer adapter.

No OAuth application is created or provider approval claimed by this module.
"""
import asyncio
import base64
import hashlib
import os
import secrets
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, urlsplit, quote

import httpx
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import HTMLResponse
from pymongo import ReturnDocument
from auth import get_current_user
from broker_vault import vault
from db import db, now_iso

router = APIRouter(prefix='/api/v1/broker-connections/coinbase/oauth', tags=['coinbase-oauth'])
SCOPES = frozenset(('wallet:accounts:read', 'wallet:user:read', 'wallet:transactions:read', 'wallet:buys:create'))
REQUEST_SCOPES = ' '.join(sorted(SCOPES | {'offline_access'}))
CALLBACK = 'https://api.tradingwithkaos.com/api/v1/broker-connections/coinbase/oauth/callback'
TOKEN_URL = 'https://login.coinbase.com/oauth2/token'


def settings():
    client = os.getenv('KAOS_COINBASE_OAUTH_CLIENT_ID', '').strip()
    secret = os.getenv('KAOS_COINBASE_OAUTH_CLIENT_SECRET', '').strip()
    redirect = os.getenv('KAOS_COINBASE_OAUTH_REDIRECT_URI', CALLBACK).strip()
    parsed = urlsplit(redirect)
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
            or parsed.query or parsed.fragment or parsed.path != urlsplit(CALLBACK).path):
        raise HTTPException(503, 'Coinbase OAuth callback configuration is invalid')
    if not client or not secret:
        raise HTTPException(503, 'Coinbase OAuth requires approved KAOS partner credentials')
    return client, secret, redirect


def scopes(value):
    if not isinstance(value, str):
        raise ValueError('Missing OAuth scope proof')
    granted = set(value.replace(',', ' ').split())
    if not SCOPES <= granted or granted - SCOPES - {'offline_access', 'openid'}:
        raise ValueError('Unexpected or missing OAuth permissions')
    return sorted(granted)


def token_fields(data):
    access, refresh = data.get('access_token'), data.get('refresh_token')
    if (str(data.get('token_type', '')).lower() != 'bearer'
            or not isinstance(access, str) or not 1 <= len(access) <= 16384
            or not isinstance(refresh, str) or not 1 <= len(refresh) <= 16384):
        raise ValueError('Invalid OAuth token response')
    expires = int(data['expires_in'])
    if isinstance(data['expires_in'], bool) or not 60 <= expires <= 86400:
        raise ValueError('Invalid OAuth expiry')
    v = vault()
    return {'oauth_access_enc': v.encrypt(access.encode()).decode(),
            'oauth_refresh_enc': v.encrypt(refresh.encode()).decode(),
            'oauth_expires_at': time.time() + expires, 'oauth_scopes': scopes(data['scope'])}


class OAuthClient:
    """Narrow Advanced Trade bearer transport. Never retries a POST automatically."""
    def __init__(self, access, granted):
        self.access = access
        self.granted = scopes(' '.join(granted))

    def _request(self, method, path, *, params=None, body=None):
        with httpx.Client(timeout=12, follow_redirects=False) as client:
            response = client.request(method, 'https://api.coinbase.com/api/v3/brokerage/' + path,
                                      headers={'Authorization': 'Bearer ' + self.access}, params=params, json=body)
        if not response.is_success:
            # Never propagate raw provider content/tokens into logs or API errors.
            raise RuntimeError('Coinbase OAuth request failed')
        data = response.json()
        if not isinstance(data, dict):raise ValueError('Invalid Coinbase response')
        return data

    def get_api_key_permissions(self):
        # /key_permissions is API-key-only. OAuth permissions were verified from
        # the token response; authenticated account requests independently verify access.
        return {'can_view': SCOPES <= set(self.granted), 'can_trade': 'wallet:buys:create' in self.granted,
                'can_transfer': False}

    def get_accounts(self, **kwargs):return self._request('GET', 'accounts', params=kwargs)
    def get_products(self, **kwargs):return self._request('GET', 'products', params=kwargs)
    def get_order(self, order_id):return self._request('GET', 'orders/historical/' + quote(str(order_id), safe=''))
    def get_fills(self, **kwargs):return self._request('GET', 'orders/historical/fills', params=kwargs)
    def market_order_buy(self, *, client_order_id, product_id, quote_size):
        return self._order(client_order_id, product_id, 'BUY', {'quote_size': quote_size})
    def market_order_sell(self, *, client_order_id, product_id, base_size):
        return self._order(client_order_id, product_id, 'SELL', {'base_size': base_size})
    def _order(self, identity, product, side, size):
        return self._request('POST', 'orders', body={'client_order_id': identity, 'product_id': product,
            'side': side, 'order_configuration': {'market_market_ioc': size}})


def make_oauth_client(row):
    if row.get('oauth_reconnect_required'):
        raise HTTPException(409, 'Reconnect Coinbase authorization before trading')
    if row.get('oauth_expires_at', 0) <= time.time():
        raise HTTPException(409, 'Coinbase authorization expired; refresh connection')
    try:
        return OAuthClient(vault().decrypt(row['oauth_access_enc'].encode()).decode(), row['oauth_scopes'])
    except HTTPException:raise
    except Exception:raise HTTPException(503, 'Coinbase OAuth vault unavailable') from None


async def ready_connection(row):
    if row.get('auth_type') != 'oauth':return row
    settings()  # Missing owner credentials cannot be bypassed by cached access.
    if row.get('oauth_reconnect_required'):
        raise HTTPException(409, 'Reconnect Coinbase authorization before trading')
    if row.get('oauth_expires_at', 0) > time.time() + 90:return row
    nonce = secrets.token_urlsafe(24)
    locked = await db.broker_connections.find_one_and_update(
        {'_id': row['_id'], 'oauth_refresh_enc': row['oauth_refresh_enc'],
         'oauth_refresh_lock': {'$exists': False}},
        {'$set': {'oauth_refresh_lock': nonce, 'oauth_refresh_started': time.time()}},
        return_document=ReturnDocument.AFTER)
    if not locked:
        current = await db.broker_connections.find_one({'_id': row['_id']})
        if current and current.get('oauth_expires_at', 0) > time.time() + 30 and not current.get('oauth_refresh_lock') and not current.get('oauth_reconnect_required'):
            return current
        if current and current.get('oauth_refresh_started', time.time()) < time.time()-60:
            await db.broker_connections.update_one({'_id':current['_id'],'oauth_refresh_lock':current.get('oauth_refresh_lock')},{'$set':{'oauth_reconnect_required':True}})
            raise HTTPException(409,'Coinbase refresh was interrupted; reconnect Coinbase')
        raise HTTPException(409, 'Coinbase authorization refresh in progress; retry connection status shortly')
    # A crashed/uncertain refresh is never retried with a possibly rotated token.
    # Reauthorization is the recovery path; it can retain the same Coinbase identity.
    try:
        client_id, client_secret, _ = settings()
        refresh = vault().decrypt(locked['oauth_refresh_enc'].encode()).decode()
        async with httpx.AsyncClient(timeout=12, follow_redirects=False) as client:
            response = await client.post(TOKEN_URL, data={'grant_type': 'refresh_token',
                'client_id': client_id, 'client_secret': client_secret, 'refresh_token': refresh})
        response.raise_for_status()
        data = response.json()
        fields = token_fields(data)
        updated = await db.broker_connections.find_one_and_update(
            {'_id': row['_id'], 'oauth_refresh_lock': nonce},
            {'$set': fields, '$unset': {'oauth_refresh_lock': '', 'oauth_refresh_started': ''}},
            return_document=ReturnDocument.AFTER)
        if not updated:raise ValueError('Connection changed during refresh')
        return updated
    except Exception:
        await db.broker_connections.update_one({'_id': row['_id'], 'oauth_refresh_lock': nonce},
            {'$set': {'oauth_reconnect_required': True}})
        raise HTTPException(409, 'Coinbase authorization refresh was not confirmed; reconnect Coinbase') from None


@router.get('/config')
async def config(response: Response, user: dict = Depends(get_current_user)):
    response.headers['Cache-Control'] = 'private, no-store'
    try:settings(); vault(); available = True
    except HTTPException:available = False
    return {'available': available, 'requiresPartnerApproval': True,
            'callbackUrl': os.getenv('KAOS_COINBASE_OAUTH_REDIRECT_URI', CALLBACK),
            'message': 'Connect your account directly with Coinbase' if available else 'Coinbase account authorization is awaiting KAOS partner setup. API-key connection remains available.'}


@router.post('/start')
async def start(response: Response, user: dict = Depends(get_current_user)):
    response.headers['Cache-Control'] = 'private, no-store'
    if user.get('account_status', 'active') != 'active':raise HTTPException(403, 'Account disabled')
    client, _, redirect = settings()
    cipher = vault()
    previous = await db.broker_connections.find_one({'user_id': user['id'], 'broker': 'coinbase'})
    if previous and previous.get('auth_type') != 'oauth':
        raise HTTPException(409, 'Disconnect the API-key connection before changing connection methods')
    state, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
    await db.coinbase_oauth_states.create_index('expires_at', expireAfterSeconds=0)
    await db.coinbase_oauth_states.delete_many({'user_id': user['id']})
    await db.coinbase_oauth_states.insert_one({'_id': hashlib.sha256(state.encode()).hexdigest(),
        'user_id': user['id'], 'verifier_enc': cipher.encrypt(verifier.encode()).decode(),
        'redirect_uri': redirect, 'client_id': client,
        'expected_verified_at': previous.get('verified_at') if previous else None,
        'expires_at': datetime.now(timezone.utc) + timedelta(minutes=10)})
    return {'authorizationUrl': 'https://login.coinbase.com/oauth2/auth?' + urlencode({
        'response_type': 'code', 'client_id': client, 'redirect_uri': redirect,
        'scope': REQUEST_SCOPES, 'state': state, 'code_challenge': challenge, 'code_challenge_method': 'S256'})}


def completion(ok):
    message = ('Coinbase connected. Return to KAOS and choose Use Coinbase or reload Broker Connections. No trading session was started.'
               if ok else 'Coinbase connection was not completed. Return to KAOS and start Connect Coinbase again. Existing connections were not replaced.')
    return HTMLResponse('<!doctype html><html><head><meta name="viewport" content="width=device-width"><title>KAOS Coinbase connection</title></head><body><h1>KAOS Coinbase connection</h1><p>' + message + '</p><p><a href="https://tradingwithkaos.com/dashboard/brokers">Return to KAOS Broker Connections</a></p></body></html>',
        status_code=200 if ok else 400, headers={'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer',
        'Content-Security-Policy': "default-src 'none'; frame-ancestors 'none'; base-uri 'none'", 'X-Content-Type-Options': 'nosniff'})


@router.get('/callback')
async def callback(state: str = '', code: str = '', error: str = ''):
    if not 20 <= len(state) <= 200:return completion(False)
    record = await db.coinbase_oauth_states.find_one_and_delete({'_id': hashlib.sha256(state.encode()).hexdigest(),
        'expires_at': {'$gt': datetime.now(timezone.utc)}})
    if not record or error or not code or len(code) > 4096:return completion(False)
    try:
        client_id, secret, redirect = settings()
        if redirect != record['redirect_uri'] or client_id != record['client_id']:raise ValueError('Settings changed')
        user = await db.users.find_one({'id': record['user_id']})
        if not user or user.get('account_status', 'active') != 'active':raise ValueError('Account unavailable')
        async with httpx.AsyncClient(timeout=12, follow_redirects=False) as client:
            response = await client.post(TOKEN_URL, data={'grant_type': 'authorization_code', 'code': code,
                'client_id': client_id, 'client_secret': secret, 'redirect_uri': redirect,
                'code_verifier': vault().decrypt(record['verifier_enc'].encode()).decode()})
            response.raise_for_status()
            tokens = response.json()
            fields = token_fields(tokens)
            headers = {'Authorization': 'Bearer ' + tokens['access_token']}
            profile = await client.get('https://api.coinbase.com/v2/user', headers=headers)
            profile.raise_for_status()
            remote_id = profile.json()['data']['id']
            if not isinstance(remote_id, str) or not remote_id:raise ValueError('Identity missing')
            identity = hashlib.sha256(remote_id.encode()).hexdigest()
            accounts = await client.get('https://api.coinbase.com/api/v3/brokerage/accounts', headers=headers, params={'limit':50})
            accounts.raise_for_status()
            account_data = accounts.json()
            if not isinstance(account_data.get('accounts'), list):raise ValueError('Accounts unavailable')
        uid = record['user_id']
        old = await db.broker_connections.find_one({'user_id': uid, 'broker': 'coinbase'})
        if (old.get('verified_at') if old else None) != record.get('expected_verified_at'):
            raise ValueError('Connection changed during authorization')
        row = {'user_id': uid, 'broker': 'coinbase', 'auth_type': 'oauth', 'verified': True,
               'oauth_identity': identity, 'verified_at': now_iso(), 'account_count': len(account_data['accounts']),
               'account_count_is_partial': account_data.get('has_next') is True,
               'oauth_reconnect_required': False, 'permissions': {'can_view': True, 'can_trade': True, 'can_transfer': False}, **fields}
        if old:
            if old.get('auth_type') != 'oauth' or old.get('oauth_identity') != identity:raise ValueError('Cannot replace a different connection')
            # Reauthorizing the SAME identity preserves all position/exposure records.
            result = await db.broker_connections.update_one({'_id': old['_id'],
                'oauth_refresh_enc': old['oauth_refresh_enc'], 'oauth_identity': identity, 'verified_at':record.get('expected_verified_at')},
                {'$set': row, '$unset': {'oauth_refresh_lock': '', 'oauth_refresh_started': ''}})
            if result.matched_count != 1:raise ValueError('Connection changed')
        else:
            if await db.coinbase_active_slots.find_one({'user_id': uid}):raise ValueError('Unresolved holdings')
            await db.broker_connections.insert_one({'_id': uid + ':coinbase', **row})
        return completion(True)
    except Exception:
        # No provider payloads, authorization codes or secrets in public errors/logs.
        return completion(False)
