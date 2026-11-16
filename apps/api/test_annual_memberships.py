import asyncio
from copy import deepcopy
from unittest.mock import AsyncMock
import routes_billing as billing
import services_trading as trading


def test_monthly_and_annual_catalog_has_distinct_prices_and_checkout_keys():
    plans = billing.DEFAULT_PLANS
    assert {p['id']:p['amount'] for p in plans} == {'pro':2995,'ultimate':9995,'pro_yearly':29995,'ultimate_yearly':99595}
    assert len({p['lookup_key'] for p in plans}) == 4
    for tier in ('pro','ultimate'):
        month = billing.find_plan(plans,tier)
        year = billing.find_plan(plans,tier+'_yearly')
        assert year['interval']=='year' and year['tier']==tier
        assert year['entitlements']==month['entitlements']
    assert billing.find_plan(plans,'ultimate')['recommended'] is True
    assert billing.find_plan(plans,'ultimate_yearly')['recommended'] is False


def test_annual_membership_keeps_tier_limits_and_ai_validation(monkeypatch):
    monkeypatch.setattr(billing,'get_plans',AsyncMock(return_value=deepcopy(billing.DEFAULT_PLANS)))
    import services
    monkeypatch.setattr(services,'get_setting',AsyncMock(side_effect=lambda key,default=None:default))
    for tier,devices in [('pro',3),('ultimate',5)]:
        ent=asyncio.run(trading.get_entitlements({'id':'member','membership_status':'ACTIVE','membership_plan':tier+'_yearly'}))
        assert ent['tier']==tier and ent['chartLimit']==4 and ent['deviceLimit']==devices
        assert ent['modes']==['STRATEGY'] and ent['aiExecutionLocked'] is True
