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
    return {'vaultReady': providers.vault_ready(), 'providers': [await providers.public_provider(p) for p in providers.CATALOG],
        'activationNote': 'Settings and connection checks do not enable checkout or transfer funds. Live adapters and financial launch checks remain required.'}


@router.put('/providers/{provider}')
async def save_provider(provider: str, request: ProviderSettings, admin=Depends(owner)):
    info = providers.provider_info(provider)
    if set(request.credentials) - set(info['fields']):
        raise HTTPException(400, 'Unknown credential field')
    updates = {**request.model_dump(exclude={'credentials'}), 'updatedAt': now_iso(), 'updatedBy': admin['id']}
    changed = []
    for name, secret in request.credentials.items():
        value = secret.get_secret_value().strip()
        if not value: continue  # Blank means keep the existing secret.
        if len(value) > 8192: raise HTTPException(400, 'Credential is too long')
        updates['encrypted.' + name] = providers.cipher().encrypt(value.encode()).decode()
        changed.append(name)
    # A mode/key/settings change invalidates the old connection-check badge.
    await db.commerce_provider_settings.update_one({'_id': provider}, {'$set': updates, '$unset': {'lastCheck': ''}}, upsert=True)
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
