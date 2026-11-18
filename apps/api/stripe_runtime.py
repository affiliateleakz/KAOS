"""Use the encrypted admin vault without implicitly launching payments."""
import os
from fastapi import HTTPException
import commerce_providers as providers


async def configuration():
    doc = await providers.document('stripe')
    values = await providers.credentials('stripe', doc)
    key = values.get('secret_key', '')
    mode = 'test' if key.startswith(('sk_test_', 'rk_test_')) else 'live' if key.startswith(('sk_live_', 'rk_live_')) else 'unconfigured'
    selected = doc.get('mode', 'sandbox')
    matching = mode == ('live' if selected == 'live' else 'test')
    enabled = os.getenv('KAOS_STRIPE_CHECKOUT_ENABLED') == 'true'
    validation = os.getenv('KAOS_LOGIN_VALIDATION_MODE') == 'true'
    secret = values.get('webhook_secret', '')
    ready = bool(matching and key and secret.startswith('whsec_') and doc.get('paymentsSelected'))
    return {'key': key, 'secret': secret, 'mode': mode, 'ready': ready,
            'enabled': bool(ready and enabled and not validation), 'validation': validation,
            'selected': bool(doc.get('paymentsSelected')), 'matching': matching}


async def availability():
    try:
        config = await configuration()
    except HTTPException:
        return {'checkoutEnabled': False, 'mode': 'unconfigured', 'configurationReady': False,
                'note': 'Stripe configuration is unavailable. Check the private commerce vault.'}
    from mail_delivery import account_mail_ready
    return {'guestCheckoutEnabled': config['enabled'] and account_mail_ready(), 'checkoutEnabled': config['enabled'], 'mode': config['mode'],
            'configurationReady': config['ready'],
            'note': 'Login-validation hosting blocks billing and webhook delivery.' if config['validation'] else
                    'Stripe setup saved; checkout remains disabled until separately activated.' if not config['enabled'] else
                    'Checkout activated; webhook delivery must be verified separately.'}


async def active_configuration():
    config = await configuration()
    if not config['enabled']:
        raise HTTPException(503, 'Stripe billing is not activated. Complete configuration and deployment validation first.')
    return config
