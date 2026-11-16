"""Settings advertise the actual membership catalog and reject corrupt paid amounts."""
import asyncio
from unittest.mock import AsyncMock, patch
import pytest
from fastapi import HTTPException
from models import SettingsReq
import routes_admin as admin
from routes_billing import DEFAULT_PLANS


def test_settings_include_free_and_current_plan_defaults_without_replacing_saved_prices():
    saved = [{**DEFAULT_PLANS[0], 'amount': 5900}, DEFAULT_PLANS[1]]
    async def setting(key, default=None):
        return saved if key == 'plans' else default
    with patch.object(admin, 'get_setting', new=setting):
        result = asyncio.run(admin.get_settings({'id': 'owner'}))
    assert result['plans'][0]['amount'] == 5900
    assert result['freePlan']['amount'] == 0
    assert result['freePlan']['entitlements']['chartLimit'] == 1
    assert [p['amount'] for p in result['planDefaults']] == [4900, 14900]
    assert [p['entitlements']['chartLimit'] for p in result['planDefaults']] == [4, 4]
    assert result['affiliateRates']['ultimate'] == [50, 25, 5]


@pytest.mark.parametrize('amount', [None, -1, 0, True, 49.5, 100000000])
def test_invalid_plan_price_is_not_saved(amount):
    req = SettingsReq(key='plans', value={'value': [{**DEFAULT_PLANS[0], 'amount': amount}]})
    with patch.object(admin, 'set_setting', new=AsyncMock()) as save:
        with pytest.raises(HTTPException) as error:
            asyncio.run(admin.update_settings(req, {'id': 'owner'}))
        assert error.value.status_code == 400
        save.assert_not_called()


def test_save_uses_configured_price_and_keeps_free_out_of_checkout():
    plans = [{**DEFAULT_PLANS[0], 'amount': 5900}, DEFAULT_PLANS[1]]
    with patch.object(admin, 'set_setting', new=AsyncMock()) as save, patch.object(admin, 'audit_log', new=AsyncMock()):
        asyncio.run(admin.update_settings(SettingsReq(key='plans', value={'value': plans}), {'id': 'owner'}))
        save.assert_awaited_once_with('plans', plans)
    with pytest.raises(HTTPException):
        asyncio.run(admin.update_settings(SettingsReq(key='plans', value={'value': [{'id':'free','name':'Free','amount':0}]}), {'id':'owner'}))
