"""Stripe Connect onboarding only. Transfers remain disabled until launch readiness."""
import asyncio
import os
from urllib.parse import urlsplit
import stripe
from fastapi import APIRouter, Depends, HTTPException
from auth import get_current_user
from db import db, now_iso
from routes_affiliate import referral_link, get_program

router = APIRouter(prefix='/api/affiliate/connect', tags=['affiliate-connect'])


def connect_key():
    key = os.getenv('STRIPE_CONNECT_SECRET_KEY', '')
    if os.getenv('KAOS_STRIPE_CONNECT_ENABLED') != 'true' or not key.startswith(('sk_test_', 'sk_live_')):
        raise HTTPException(503, 'Stripe Connect setup is not available yet')
    return key


async def active_affiliate(user):
    if user.get('account_status', 'active') in ('suspended', 'banned'):
        raise HTTPException(403, 'Account access is restricted')
    acc = await db.affiliate_accounts.find_one({'userId': user['id']})
    if not acc or acc.get('status') != 'active':
        raise HTTPException(403, 'An active affiliate account is required')
    return acc


@router.get('/status')
async def status(user=Depends(get_current_user)):
    acc = await active_affiliate(user)
    configured = os.getenv('KAOS_STRIPE_CONNECT_ENABLED') == 'true' and bool(os.getenv('STRIPE_CONNECT_SECRET_KEY'))
    result = {'configured': configured, 'connected': False, 'transfersEnabled': False,
              'mode': 'live' if os.getenv('STRIPE_CONNECT_SECRET_KEY', '').startswith('sk_live_') else 'test'}
    if not configured or not acc.get('stripeConnectAccountId'):
        return result
    try:
        account = await asyncio.to_thread(stripe.Account.retrieve, acc['stripeConnectAccountId'], api_key=connect_key())
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
    key = connect_key()
    account_id = acc.get('stripeConnectAccountId')
    try:
        if not account_id:
            account = await asyncio.to_thread(stripe.Account.create, type='express',
                capabilities={'transfers': {'requested': True}}, metadata={'kaosUserId': user['id']},
                idempotency_key='kaos-connect-v1-' + user['id'], api_key=key)
            account_id = account['id']
            await db.affiliate_accounts.update_one({'_id': acc['_id'], 'userId': user['id']},
                {'$set': {'stripeConnectAccountId': account_id, 'connectUpdatedAt': now_iso()}})
        origin = urlsplit(referral_link(acc['code']))
        base = f'{origin.scheme}://{origin.netloc}/dashboard/affiliate'
        link = await asyncio.to_thread(stripe.AccountLink.create, account=account_id, type='account_onboarding',
            return_url=base+'?connect=return', refresh_url=base+'?connect=refresh', api_key=key)
    except stripe.StripeError as exc:
        raise HTTPException(503, 'Stripe onboarding could not be opened. Try again later.') from exc
    return {'url': link['url']}
