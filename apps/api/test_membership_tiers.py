import os
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "kaos_test")
import asyncio
import pytest
from services import compute_license
from services_trading import get_entitlements


def run(coro):
    return asyncio.run(coro)


@pytest.mark.parametrize("status", ["EXPIRED", "PAST_DUE", None])
def test_free_tier_gets_strategy_bot_without_ai(status):
    ent = run(get_entitlements({"membership_status": status}))
    assert ent["botAccess"] is True and ent["modes"] == ["STRATEGY"] and ent["tier"] == "free"
    assert ent["deviceLimit"] == 1 and not ent["scanners"] and not ent["aiInsights"] and not ent["premiumTools"]


def test_pro_has_no_ai_modes_and_ultimate_does(monkeypatch):
    import routes_billing

    async def plans():
        return routes_billing.DEFAULT_PLANS
    monkeypatch.setattr(routes_billing, "get_plans", plans)
    pro = run(get_entitlements({"membership_status": "ACTIVE", "membership_plan": "pro"}))
    ult = run(get_entitlements({"membership_status": "ACTIVE", "membership_plan": "yearly"}))
    assert pro["tier"] == "pro" and "AI" not in pro["modes"] and pro["scanners"]
    assert ult["tier"] == "ultimate" and {"AI", "STRATEGY_AI"} <= set(ult["modes"])


def test_suspended_account_gets_nothing():
    ent = run(get_entitlements({"account_status": "suspended", "membership_status": "ACTIVE"}))
    assert ent["botAccess"] is False and ent["modes"] == []


def test_license_allows_free_but_keeps_affiliate_and_suspension_checks():
    free = run(compute_license({"membership_status": "EXPIRED", "affiliate_status": "VERIFIED"}))
    assert free["authorized"] is True and free["tier"] == "free"
    assert run(compute_license({"membership_status": "EXPIRED", "affiliate_status": "PENDING"}))["authorized"] is False
    banned = run(compute_license({"account_status": "banned", "membership_status": "ACTIVE", "affiliate_status": "VERIFIED"}))
    assert banned["authorized"] is False
