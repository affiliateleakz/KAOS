import asyncio
from unittest.mock import AsyncMock
import pytest
import services_trading as trading


def test_super_admin_gets_top_features_without_paid_membership(monkeypatch):
    monkeypatch.setattr(trading, '_membership_entitlements', AsyncMock(side_effect=AssertionError('No paid plan required')))
    monkeypatch.setattr(trading, 'apply_ai_execution_lock', AsyncMock(side_effect=lambda ent: {**ent, 'modes': ['STRATEGY'], 'aiExecutionLocked': True}))
    result = asyncio.run(trading.get_entitlements({'role': 'super_admin', 'membership_status': 'EXPIRED'}))
    assert result['tier'] == 'ultimate'
    assert result['chartLimit'] == 4
    assert result['devicesUnlimited'] is True
    assert result['deviceLimit'] is None
    assert all(result[name] for name in ('scanners', 'aiInsights', 'cloudStrategies', 'premiumTools', 'botAccess'))
    assert result['modes'] == ['STRATEGY']
    assert result['aiExecutionLocked'] is True


@pytest.mark.parametrize('user', [
    {'role': 'user', 'name': 'super_admin'}, {'role': 'admin'}, {'role': 'moderator'},
    {'role': 'super_admin', 'account_status': 'suspended'},
    {'role': 'super_admin', 'account_status': 'banned'},
    {'role': 'super_admin', 'extension_access_revoked': True},
])
def test_other_roles_and_restricted_accounts_do_not_get_override(monkeypatch, user):
    membership = AsyncMock(return_value={'chartLimit': 1, 'deviceLimit': 1})
    monkeypatch.setattr(trading, '_membership_entitlements', membership)
    result = asyncio.run(trading.get_entitlements(user))
    assert result['chartLimit'] == 1
    assert not result.get('roleGranted')
    membership.assert_awaited_once_with(user)
