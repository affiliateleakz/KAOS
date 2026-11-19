import os
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, SecretStr
from auth import require_role
from db import db, now_iso
from services import audit_log
import commerce_providers as providers

router = APIRouter(prefix='/api/admin/commerce', tags=['commerce-setup'])
owner = require_role('super_admin')


@router.post('/vault/initialize')
async def initialize_commerce_vault(admin=Depends(owner)):
    providers.initialize_vault()
    await audit_log(admin, 'commerce_vault_initialized', 'commerce_vault')
    return {'vaultReady': True}


class ProviderSettings(BaseModel):
    mode: Literal['sandbox', 'live'] = 'sandbox'
    paymentsSelected: bool = False
    payoutsSelected: bool = False
    cryptoAsset: Literal['btc', 'eth', 'usdttrc20', 'usdterc20', 'usdtbsc', 'usdc'] = 'usdttrc20'
    credentials: dict[str, SecretStr] = Field(default_factory=dict)


@router.get('/providers')
async def get_providers(admin=Depends(owner)):
    from stripe_runtime import availability
    readiness=await availability()
    methods=[await providers.public_provider(p) for p in providers.CATALOG]
    from affiliate_payouts import availability as payout_availability
    payout_status=await payout_availability()
    for method in methods:
        if method['id']=='stripe':
            method['paymentsLive']=readiness['checkoutEnabled'] and readiness['mode']=='live'
            method['payoutsLive']=payout_status['payoutsEnabled']
    note=('Stripe membership checkout is enabled in '+readiness['mode']+' mode. Affiliate payouts remain separate; verify signed webhook delivery.'
          if readiness['checkoutEnabled'] else 'Settings and connection checks do not enable checkout or transfer funds. Checkout activation remains separate.')
    return {'stripeReadiness':readiness,'vaultReady':providers.vault_ready(),'providers':methods,'activationNote':note}


@router.put('/providers/{provider}')
async def save_provider(provider: str, request: ProviderSettings, admin=Depends(owner)):
    info = providers.provider_info(provider)
    if set(request.credentials) - set(info['fields']):
        raise HTTPException(400, 'Unknown credential field')
    updates = {**request.model_dump(exclude={'credentials'}), 'updatedAt': now_iso(), 'updatedBy': admin['id']}
    changed = []
    if provider=='stripe':
        previous=await providers.document(provider)
        if request.mode!=previous.get('mode','sandbox') and os.getenv('KAOS_STRIPE_CHECKOUT_ENABLED')=='true' and os.getenv('KAOS_LOGIN_VALIDATION_MODE')!='true':
            raise HTTPException(409,'Disable checkout before switching the active Stripe environment')
        # Preserve old single-environment ciphertext under its actual key prefix.
        if previous.get('encrypted'):
            old_mode=providers.legacy_stripe_mode(previous)
            for name,value in previous['encrypted'].items():
                actual=providers.stripe_mode(providers.decrypt(value)) if name in ('secret_key','connect_secret_key') else old_mode
                actual=actual or old_mode
                if not (previous.get('encryptedByMode') or {}).get(actual,{}).get(name):updates['encryptedByMode.'+actual+'.'+name]=value
    for name, secret in request.credentials.items():
        value = secret.get_secret_value().strip()
        if not value: continue  # Blank means keep the existing secret.
        if len(value) > 8192: raise HTTPException(400, 'Credential is too long')
        if provider=='stripe':
            if name in ('secret_key','connect_secret_key') and providers.stripe_mode(value)!=request.mode:
                raise HTTPException(400,'Stripe '+name.replace('_',' ')+' must match '+request.mode+' mode (use sk_live_/rk_live_ for live or sk_test_/rk_test_ for sandbox)')
            if name=='webhook_secret' and not value.startswith('whsec_'):raise HTTPException(400,'Use the webhook destination signing secret starting whsec_')
        path='encryptedByMode.'+request.mode+'.'+name if provider=='stripe' else 'encrypted.'+name
        updates[path] = providers.cipher().encrypt(value.encode()).decode()
        changed.append(name)
    # A mode/key/settings change invalidates the old connection-check badge.
    await db.commerce_provider_settings.update_one({'_id': provider}, {'$set':updates,'$unset':{'lastCheck':'',**({'encrypted':''} if provider=='stripe' else {})}}, upsert=True)
    await audit_log(admin, 'commerce_provider_configured', 'commerce_provider', provider,
                    {'mode': request.mode, 'credentialFieldsChanged': changed})
    return await providers.public_provider(provider)


@router.post('/providers/{provider}/test')
async def test_provider(provider: str, admin=Depends(owner)):
    providers.provider_info(provider)
    try:
        result = await providers.check_connection(provider)
    except HTTPException:
        await db.commerce_provider_settings.update_one({'_id': provider},
            {'$set': {'lastCheck': {'ok': False, 'checkedAt': now_iso(), 'message': 'API check failed; connection is not currently verified'}}}, upsert=True)
        await audit_log(admin, 'commerce_provider_check_failed', 'commerce_provider', provider)
        raise
    await audit_log(admin, 'commerce_provider_checked', 'commerce_provider', provider, {'mode': result['mode']})
    return result
