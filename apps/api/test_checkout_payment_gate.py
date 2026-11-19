"""Signed checkout completion alone is not proof that money was paid."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
import routes_billing as billing


@pytest.mark.parametrize('kind,paid,status,activates', [
    ('checkout.session.completed', 'unpaid', 'complete', False),
    ('checkout.session.completed', 'no_payment_required', 'complete', False),
    ('checkout.session.completed', 'paid', 'open', False),
    ('checkout.session.completed', 'paid', 'complete', True),
    ('checkout.session.async_payment_succeeded', 'paid', 'complete', True),
])
def test_membership_requires_paid_complete_checkout(monkeypatch, kind, paid, status, activates):
    monkeypatch.setattr(billing, 'active_configuration', AsyncMock(return_value={'secret':'fixture-only','key':'fixture-only'}))
    events = SimpleNamespace(insert_one=AsyncMock(), update_one=AsyncMock(return_value=SimpleNamespace(modified_count=1)))
    monkeypatch.setattr(billing, 'db', SimpleNamespace(webhook_events=events))
    event = {'id': 'event-test', 'type': kind, 'data': {'object': {
        'id': 'session-test', 'payment_status': paid, 'status': status,
        'metadata': {'user_id': 'u1', 'plan_id': 'pro'}, 'customer': 'customer-test', 'subscription': 'subscription-test'}}}
    monkeypatch.setattr(billing.stripe.Webhook, 'construct_event', lambda *a, **k: event)
    activate = AsyncMock()
    monkeypatch.setattr(billing, '_activate', activate)
    request = SimpleNamespace(body=AsyncMock(return_value=b'fixture'), headers={'stripe-signature': 'fixture'})
    assert asyncio.run(billing.stripe_webhook(request)) == {'status': 'ok'}
    if activates:
        activate.assert_awaited_once_with('u1', 'pro', 'customer-test', 'subscription-test', 'session-test')
    else:
        activate.assert_not_awaited()
