"""Member-scoped Coinbase connection verification. Never submits orders."""
import asyncio
import json
import os
import re

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from auth import get_current_user
from broker_vault import vault
from db import db, now_iso

router = APIRouter(prefix='/api/v1/broker-connections', tags=['broker-connections'])
KEY_NAME = re.compile(r'^organizations/[A-Za-z0-9_-]{1,100}/apiKeys/[A-Za-z0-9_-]{1,100}$')


def credentials(payload):
    if not isinstance(payload, dict):
        raise HTTPException(422, 'API key name and private key are required')
    name, secret = payload.get('key_name'), payload.get('private_key')
    if not isinstance(name, str) or not isinstance(secret, str) or len(secret) > 16000:
        raise HTTPException(422, 'Invalid Coinbase credentials')
    secret = secret.strip()
    if secret.startswith('{'):
        try:
            exported = json.loads(secret)
            if not isinstance(exported, dict):
                raise ValueError()
            exported_name = exported.get('name')
            if name.strip() and exported_name and name.strip() != exported_name:
                raise HTTPException(422, 'API key name differs from the credentials JSON')
            name = name.strip() or exported_name
            secret = exported['privateKey']
        except (ValueError, KeyError, TypeError):
            raise HTTPException(422, 'Invalid Coinbase credentials JSON') from None
    if not isinstance(name, str) or not KEY_NAME.fullmatch(name.strip()) or not isinstance(secret, str):
        raise HTTPException(422, 'Use the Coinbase CDP API key name and original private key')
    secret = secret.replace('\\n', '\n').strip()
    if not secret or len(secret) > 16000:
        raise HTTPException(422, 'Invalid Coinbase private key')
    try:
        # Validate the supported EC/Ed25519 key format locally; never return this JWT.
        from coinbase.jwt_generator import build_rest_jwt
        build_rest_jwt('GET api.coinbase.com/api/v3/brokerage/accounts', name.strip(), secret)
    except Exception:
        raise HTTPException(422, 'Unsupported Coinbase private key format; use the original CDP key export') from None
    return name.strip(), secret


def client_for(name, secret):
    from coinbase.rest import RESTClient
    return RESTClient(api_key=name, api_secret=secret, timeout=12)


def dictionary(value):
    value = value.to_dict() if hasattr(value, 'to_dict') else value
    if not isinstance(value, dict):
        raise ValueError('Invalid Coinbase response')
    return value


def public(row):
    return {'broker': 'coinbase', 'saved': True, 'verified': row.get('verified') is True,
            'key_hint': row.get('key_hint', ''), 'verified_at': row.get('verified_at'),
            'account_count': row.get('account_count', 0),
            'account_count_is_partial': row.get('account_count_is_partial', False),
            'permissions': {k: row.get('permissions', {}).get(k) is True for k in ('can_view', 'can_trade', 'can_transfer')},
            'live_order_authorized': False, 'mode': 'read_only'}


async def current(uid):
    return await db.broker_connections.find_one({'user_id': uid, 'broker': 'coinbase'})


async def connected_client(uid):
    row = await current(uid)
    if not row or row.get('verified') is not True:
        raise HTTPException(409, 'Verify and save Coinbase first')
    try:
        v = vault()
        name = v.decrypt(row['key_name_enc'].encode()).decode()
        secret = v.decrypt(row['private_key_enc'].encode()).decode()
        return client_for(name, secret)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(503, 'Saved Coinbase credentials are unavailable; check the broker vault configuration') from None


def private(response):
    response.headers['Cache-Control'] = 'private, no-store'


@router.get('')
async def list_connections(response: Response, user: dict = Depends(get_current_user)):
    private(response)
    row = await current(user['id'])
    return {'connections': [public(row)] if row else []}


@router.get('/coinbase/status')
async def status(response: Response, user: dict = Depends(get_current_user)):
    private(response)
    row = await current(user['id'])
    return public(row) if row else {'broker': 'coinbase', 'saved': False, 'verified': False,
                                   'live_order_authorized': False, 'mode': 'read_only'}


@router.put('/coinbase')
async def save(request: Request, response: Response, user: dict = Depends(get_current_user)):
    private(response)
    live_enabled = os.getenv('KAOS_COINBASE_LIVE_ORDERS', 'disabled') == 'enabled'
    if live_enabled and await current(user['id']):
        raise HTTPException(409, 'Pause the Coinbase live gateway before replacing broker credentials')
    # Bound and sanitize validation: errors never echo the submitted key material.
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > 20000:
            raise HTTPException(413, 'Coinbase credentials payload is too large')
    try:
        payload = json.loads(body)
    except (ValueError, UnicodeError):
        raise HTTPException(422, 'Invalid credentials payload') from None
    name, secret = credentials(payload)
    v = vault()  # Fail before contacting Coinbase if encryption is unavailable.
    if await db.coinbase_active_slots.find_one({'user_id': user['id']}):
        raise HTTPException(409, 'Resolve active or uncertain Coinbase positions before replacing credentials')
    def verify():
        client = client_for(name, secret)
        permissions = dictionary(client.get_api_key_permissions())
        if permissions.get('can_view') is not True or permissions.get('can_transfer') is not False:
            raise HTTPException(422, 'Use a Coinbase key with View enabled and Transfer disabled')
        accounts = dictionary(client.get_accounts(limit=50))
        if not isinstance(accounts.get('accounts'), list):
            raise ValueError('Invalid account response')
        return permissions, accounts
    try:
        permissions, accounts = await asyncio.to_thread(verify)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(502, 'Coinbase verification failed; check key permissions, IP allowlist and Coinbase availability') from None
    previous = await current(user['id'])
    identity = {'_id': previous['_id']} if previous else {'_id': user['id'] + ':coinbase'}
    row = {'user_id': user['id'], 'broker': 'coinbase', 'verified': True,
           'key_name_enc': v.encrypt(name.encode()).decode(), 'private_key_enc': v.encrypt(secret.encode()).decode(),
           'key_hint': name[-4:], 'verified_at': now_iso(), 'account_count': len(accounts['accounts']),
           'account_count_is_partial': accounts.get('has_next') is True,
           'permissions': {k: permissions.get(k) is True for k in ('can_view', 'can_trade', 'can_transfer')}}
    if live_enabled:
        if previous:raise HTTPException(409, 'A Coinbase key was saved concurrently; pause the gateway before replacing it')
        from pymongo.errors import DuplicateKeyError
        try:await db.broker_connections.insert_one({'_id':user['id']+':coinbase',**row})
        except DuplicateKeyError:raise HTTPException(409, 'Coinbase is already saved; refresh connection status') from None
    else:
        await db.broker_connections.update_one(identity, {'$set': row}, upsert=True)
    return public(row)


@router.delete('/coinbase')
async def disconnect(response: Response, user: dict = Depends(get_current_user)):
    private(response)
    if os.getenv('KAOS_COINBASE_LIVE_ORDERS', 'disabled') == 'enabled':
        raise HTTPException(409, 'Pause the Coinbase live gateway before disconnecting')
    if await db.coinbase_active_slots.find_one({'user_id': user['id']}):
        raise HTTPException(409, 'Resolve active or uncertain Coinbase positions before disconnecting')
    await db.broker_connections.delete_many({'user_id': user['id'], 'broker': 'coinbase'})
    return {'broker': 'coinbase', 'saved': False, 'live_order_authorized': False}


@router.get('/coinbase/accounts')
async def accounts(response: Response, user: dict = Depends(get_current_user)):
    private(response)
    client = await connected_client(user['id'])
    try:
        data = dictionary(await asyncio.to_thread(client.get_accounts, limit=50))
        rows = data['accounts']
        if not isinstance(rows, list):
            raise ValueError()
        # Read-only summary; no raw provider response, account UUIDs or balances.
        currencies = sorted({row['currency'] for row in rows if isinstance(row, dict) and isinstance(row.get('currency'), str)})
        return {'account_count': len(rows), 'account_count_is_partial': data.get('has_next') is True,
                'currencies': currencies, 'mode': 'read_only'}
    except Exception:
        raise HTTPException(502, 'Coinbase accounts unavailable; verify the saved key and connection') from None


@router.get('/coinbase/products')
async def products(response: Response, user: dict = Depends(get_current_user)):
    private(response)
    client = await connected_client(user['id'])
    try:
        data = dictionary(await asyncio.to_thread(client.get_products, limit=50, product_type='SPOT'))
        rows = data['products']
        if not isinstance(rows, list):
            raise ValueError()
        fields = ('product_id', 'base_currency_id', 'quote_currency_id', 'base_increment', 'quote_increment',
                  'base_min_size', 'quote_min_size', 'trading_disabled', 'view_only', 'price')
        return {'products': [{k: row[k] for k in fields if k in row} for row in rows
                             if isinstance(row, dict) and re.fullmatch(r'[A-Z0-9]{2,20}-USD', str(row.get('product_id', '')))],
                'partial_catalog': True, 'mode': 'read_only', 'live_order_authorized': False}
    except Exception:
        raise HTTPException(502, 'Coinbase markets unavailable; verify the saved key and connection') from None
