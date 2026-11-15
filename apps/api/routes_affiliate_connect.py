"""Stripe Connect onboarding only. Transfers remain disabled until launch readiness."""
import asyncio
import os
from urllib.parse import urlsplit
import stripe
from fastapi import APIRouter, Depends, HTTPException
from auth import get_current_user
from db import db, now_iso
from routes_affiliate import referral_link, get_program
import commerce_providers

router = APIRouter(prefix='/api/affiliate/connect', tags=['affiliate-connect'])


def connect_key():
    key = os.getenv('STRIPE_CONNECT_SECRET_KEY', '')
    if os.getenv('KAOS_STRIPE_CONNECT_ENABLED') != 'true' or not key.startswith(('sk_test_', 'sk_live_')):
        raise HTTPException(503, 'Stripe Connect setup is not available yet')
    return key


async def resolved_connect_key():
    setup = await commerce_providers.document('stripe')
    if 'payoutsSelected' not in setup:
        return connect_key()
    if not setup.get('payoutsSelected'):
        raise HTTPException(503, 'Stripe Connect onboarding is not selected in admin provider setup')
    values = await commerce_providers.credentials('stripe', setup)
    key = values.get('connect_secret_key') or values.get('secret_key') or ''
    prefix = 'sk_live_' if setup.get('mode') == 'live' else 'sk_test_'
    if not key.startswith(prefix):
        raise HTTPException(503, 'Stripe Connect credentials are missing or do not match the selected environment')
    return key


async def active_affiliate(user):
    if user.get('account_status', 'active') in ('suspended', 'banned'):
        raise HTTPException(403, 'Account access is restricted')
    acc = await db.affiliate_accounts.find_one({'userId': user['id']})
    if not acc or acc.get('status') != 'active':
        raise HTTPException(403, 'An active affiliate account is required')
    return acc


def account_for_mode(acc, mode):
    account = (acc.get('stripeConnectAccounts') or {}).get(mode)
    if account: return account
    legacy = acc.get('stripeConnectAccountId')
    if legacy and (acc.get('stripeConnectMode') == mode or (mode == 'test' and not acc.get('stripeConnectMode'))):
        return legacy
    if legacy and not acc.get('stripeConnectMode'):
        raise HTTPException(409, 'Existing Stripe profile needs test/live environment verification before live onboarding')
    return None


@router.get('/status')
async def status(user=Depends(get_current_user)):
    acc = await active_affiliate(user)
    try:
        key = await resolved_connect_key()
    except HTTPException:
        key = ''
    configured = bool(key)
    result = {'configured': configured, 'connected': False, 'transfersEnabled': False,
              'mode': 'live' if key.startswith('sk_live_') else 'test'}
    if not configured:
        return result
    account_id = account_for_mode(acc, result['mode'])
    if not account_id: return result
    try:
        account = await asyncio.to_thread(stripe.Account.retrieve, account_id, api_key=key)
    except HTTPException:
        raise
    except stripe.StripeError as exc:
        raise HTTPException(503, 'Cannot check Stripe onboarding right now') from exc
    return {**result, 'connected': True, 'detailsSubmitted': bool(account.get('details_submitted')),
            'payoutsReady': bool(account.get('payouts_enabled')),
            'requirementsDue': bool((account.get('requirements') or {}).get('currently_due'))}


@router.post('/onboarding')
async def onboarding(user=Depends(get_current_user)):
    acc = await active_affiliate(user)
    if (await get_program()).get('enabled') is not True:
        raise HTTPException(503, 'Affiliate enrollment is currently paused')
    key = await resolved_connect_key()
    mode = 'live' if key.startswith('sk_live_') else 'test'
    account_id = account_for_mode(acc, mode)
    try:
        if not account_id:
            account = await asyncio.to_thread(stripe.Account.create, type='express',
                capabilities={'transfers': {'requested': True}}, metadata={'kaosUserId': user['id']},
                idempotency_key='kaos-connect-v1-' + mode + '-' + user['id'], api_key=key)
            account_id = account['id']
            await db.affiliate_accounts.update_one({'_id': acc['_id'], 'userId': user['id']},
                {'$set': {'stripeConnectAccounts.' + mode: account_id, 'connectUpdatedAt': now_iso()}})
        origin = urlsplit(referral_link(acc['code']))
        base = f'{origin.scheme}://{origin.netloc}/dashboard/affiliate'
        link = await asyncio.to_thread(stripe.AccountLink.create, account=account_id, type='account_onboarding',
            return_url=base+'?connect=return', refresh_url=base+'?connect=refresh', api_key=key)
    except stripe.StripeError as exc:
        raise HTTPException(503, 'Stripe onboarding could not be opened. Try again later.') from exc
    return {'url': link['url']}
