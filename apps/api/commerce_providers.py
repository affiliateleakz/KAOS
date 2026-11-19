"""Provider setup and credential checks. No invoice, charge or payout execution."""
import os
from pathlib import Path
import stat
from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException
import httpx
from db import db, now_iso

CATALOG = {
    'stripe': {'name': 'Stripe', 'description': 'Membership payments and Stripe Connect affiliate payouts.',
        'dashboard': 'https://dashboard.stripe.com/',
        'fields': {'secret_key': ('Payments secret key', 'STRIPE_SECRET_KEY'),
                   'webhook_secret': ('Webhook signing secret', 'STRIPE_WEBHOOK_SECRET'),
                   'connect_secret_key': ('Connect secret key', 'STRIPE_CONNECT_SECRET_KEY')}},
    'paypal': {'name': 'PayPal', 'description': 'PayPal payments and Payouts; Payouts requires PayPal approval.',
        'dashboard': 'https://developer.paypal.com/dashboard/',
        'fields': {'client_id': ('Client ID', 'PAYPAL_CLIENT_ID'),
                   'client_secret': ('Client secret', 'PAYPAL_CLIENT_SECRET'),
                   'webhook_id': ('Webhook ID', 'PAYPAL_WEBHOOK_ID')}},
    'nowpayments': {'name': 'NOWPayments', 'description': 'Crypto payment and payout configuration. Payout permissions and funding must be verified separately.',
        'dashboard': 'https://account.nowpayments.io/',
        'fields': {'api_key': ('API key', 'NOWPAYMENTS_API_KEY'),
                   'ipn_secret': ('IPN signing secret', 'NOWPAYMENTS_IPN_SECRET')}},
}
CRYPTO_ASSETS = ('btc', 'eth', 'usdttrc20', 'usdterc20', 'usdtbsc', 'usdc')


def key_path():
    return Path.home() / '.kaos' / 'commerce.key'


def cipher():
    try:
        key = os.environ.get('KAOS_COMMERCE_VAULT_KEY')
        if not key:
            path = key_path()
            if path.is_symlink() or path.parent.is_symlink() or path.stat().st_mode & 0o077:
                raise ValueError('Unsafe key file')
            key = path.read_text().strip()
        return Fernet(key.encode())
    except (OSError, ValueError, TypeError) as exc:
        raise HTTPException(503, 'Commerce encryption key is not configured; add KAOS_COMMERCE_VAULT_KEY in hosting settings') from exc


def initialize_vault():
    if os.environ.get('KAOS_COMMERCE_VAULT_KEY'):
        cipher(); return
    path = key_path()
    try:
        if path.parent.is_symlink(): raise ValueError('Unsafe vault directory')
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if stat.S_IMODE(path.parent.stat().st_mode) & 0o077:
            raise ValueError('Vault directory must be private')
        if path.exists() or path.is_symlink():
            cipher(); return  # Never replace an existing key, including invalid keys.
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, 'wb') as handle:
            handle.write(Fernet.generate_key())
    except (OSError, ValueError) as exc:
        raise HTTPException(503, 'Cannot initialize the private vault. Check hosting permissions or configure KAOS_COMMERCE_VAULT_KEY.') from exc


def vault_ready():
    try:
        cipher(); return True
    except HTTPException:
        return False


def provider_info(provider):
    if provider not in CATALOG:
        raise HTTPException(404, 'Unknown payment provider')
    return CATALOG[provider]


async def document(provider):
    provider_info(provider)
    return await db.commerce_provider_settings.find_one({'_id': provider}) or {}


def stripe_mode(key):
    if key.startswith(('sk_live_','rk_live_')):return 'live'
    if key.startswith(('sk_test_','rk_test_')):return 'sandbox'
    return None


def decrypt(value):
    try:return cipher().decrypt(value.encode()).decode()
    except (InvalidToken,UnicodeError,ValueError) as exc:
        raise HTTPException(503,'Stored commerce credentials cannot be decrypted; restore the original commerce vault key') from exc


def legacy_stripe_mode(doc):
    fields=doc.get('encrypted') or {}
    for name in ('secret_key','connect_secret_key'):
        if fields.get(name):
            mode=stripe_mode(decrypt(fields[name]))
            if mode:return mode
    return doc.get('mode','sandbox')


def stored_fields(provider,doc):
    if provider!='stripe':return doc.get('encrypted') or {}
    mode=doc.get('mode','sandbox');fields=dict((doc.get('encryptedByMode') or {}).get(mode) or {})
    if doc.get('encrypted'):
        try:legacy_mode=legacy_stripe_mode(doc)
        except HTTPException:legacy_mode=mode  # Display stored presence; actual use still fails closed.
        if legacy_mode==mode:
            for name,value in doc['encrypted'].items():fields.setdefault(name,value)
    return fields


def env_value(provider,name,env,doc):
    if provider!='stripe':return os.getenv(env,'')
    mode=doc.get('mode','sandbox');prefix='LIVE' if mode=='live' else 'TEST'
    alias={'secret_key':'SECRET_KEY','connect_secret_key':'CONNECT_SECRET_KEY','webhook_secret':'WEBHOOK_SECRET'}[name]
    direct=os.getenv('STRIPE_'+prefix+'_'+alias,'')
    if direct:return direct if name=='webhook_secret' or stripe_mode(direct)==mode else ''
    value=os.getenv(env,'')
    if name!='webhook_secret':return value if stripe_mode(value)==mode else ''
    return value if stripe_mode(os.getenv('STRIPE_SECRET_KEY',''))==mode else ''


async def credentials(provider,doc=None):
    info=provider_info(provider);doc=await document(provider) if doc is None else doc;stored=stored_fields(provider,doc);result={}
    for name,(_,env) in info['fields'].items():
        value=decrypt(stored[name]) if stored.get(name) else env_value(provider,name,env,doc)
        if value and (provider!='stripe' or name=='webhook_secret' or stripe_mode(value)==doc.get('mode','sandbox')):result[name]=value
    return result


async def public_provider(provider):
    info=provider_info(provider);doc=await document(provider);encrypted=stored_fields(provider,doc)
    return {'id':provider,'name':info['name'],'description':info['description'],'dashboard':info['dashboard'],
        'mode':doc.get('mode','sandbox'),'paymentsSelected':doc.get('paymentsSelected',False),
        'payoutsSelected':doc.get('payoutsSelected',False),'cryptoAsset':doc.get('cryptoAsset','usdttrc20'),
        'fields':[{'name':name,'label':label,'environmentVariable':env,
            'configured':bool(encrypted.get(name) or env_value(provider,name,env,doc)),
            'source':'encrypted storage' if encrypted.get(name) else 'hosting environment' if env_value(provider,name,env,doc) else 'not configured'} for name,(label,env) in info['fields'].items()],
        'lastCheck':doc.get('lastCheck'),'paymentsLive':False,'payoutsLive':False}


async def check_connection(provider):
    doc = await document(provider); values = await credentials(provider, doc)
    mode = doc.get('mode', 'sandbox')
    try:
        async with httpx.AsyncClient(timeout=12, follow_redirects=False) as client:
            if provider == 'stripe':
                key = values.get('secret_key') or values.get('connect_secret_key')
                if not key: raise HTTPException(400, 'Add a Stripe secret key first')
                if stripe_mode(key)!=mode:
                    raise HTTPException(400, 'Stripe key does not match the selected sandbox/live mode')
                response = await client.get('https://api.stripe.com/v1/account', headers={'Authorization': 'Bearer ' + key})
                response.raise_for_status(); data = response.json()
                accepted = isinstance(data, dict) and str(data.get('id', '')).startswith('acct_')
                message = 'Stripe account credentials accepted. Connect capability, webhooks and launch readiness still require verification.'
            elif provider == 'paypal':
                if not values.get('client_id') or not values.get('client_secret'):
                    raise HTTPException(400, 'Add the PayPal client ID and client secret first')
                host = 'https://api-m.paypal.com' if mode == 'live' else 'https://api-m.sandbox.paypal.com'
                response = await client.post(host + '/v1/oauth2/token', data={'grant_type': 'client_credentials'},
                    auth=(values['client_id'], values['client_secret']))
                response.raise_for_status(); data = response.json()
                accepted = isinstance(data, dict) and bool(data.get('access_token'))
                message = 'PayPal app credentials accepted. This does not verify Payouts approval or enable payments.'
            else:
                if not values.get('api_key'): raise HTTPException(400, 'Add the NOWPayments API key first')
                host = 'https://api.nowpayments.io' if mode == 'live' else 'https://api-sandbox.nowpayments.io'
                response = await client.get(host + '/v1/balance', headers={'x-api-key': values['api_key']})
                response.raise_for_status(); data = response.json()
                accepted = isinstance(data, dict) and 'message' not in data and 'statusCode' not in data
                message = 'NOWPayments balance API responded. IPN verification, supported assets, payout authorization and funding still require verification.'
        if not accepted: raise HTTPException(502, 'Provider returned an unexpected response; connection was not verified')
        result = {'ok': True, 'checkedAt': now_iso(), 'mode': mode, 'message': message}
    except httpx.HTTPError as exc:
        # Never expose provider bodies, OAuth tokens, balances or credential URLs.
        raise HTTPException(502, 'Provider connection failed. Check credentials, selected mode and provider permissions.') from exc
    except (ValueError, TypeError) as exc:
        raise HTTPException(502, 'Provider returned an invalid response') from exc
    await db.commerce_provider_settings.update_one({'_id': provider}, {'$set': {'lastCheck': result}}, upsert=True)
    return result
