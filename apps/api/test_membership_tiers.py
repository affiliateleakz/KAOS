import os
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "kaos_test")
import asyncio
import pytest
from services import compute_license
from services_trading import get_entitlements
from fastapi import HTTPException
from routes_trading import _check_mode  # imported at collection, before mock tests stub `db`


def run(coro):
    return asyncio.run(coro)


@pytest.mark.parametrize("status", ["EXPIRED", "PAST_DUE", None])
def test_free_tier_gets_strategy_bot_without_ai(status):
    ent = run(get_entitlements({"membership_status": status}))
    assert ent["botAccess"] is True and ent["modes"] == ["STRATEGY"] and ent["tier"] == "free"
    assert ent["deviceLimit"] == 1 and ent["chartLimit"] == 1 and not ent["scanners"] and not ent["aiInsights"] and not ent["premiumTools"]


def test_ai_modes_locked_by_default_for_every_tier(monkeypatch):
    import routes_billing
    import services

    async def plans():
        return routes_billing.DEFAULT_PLANS

    async def unset(key, default=None):
        return default
    monkeypatch.setattr(routes_billing, "get_plans", plans)
    monkeypatch.setattr(services, "get_setting", unset)
    pro = run(get_entitlements({"membership_status": "ACTIVE", "membership_plan": "pro"}))
    ult = run(get_entitlements({"membership_status": "ACTIVE", "membership_plan": "yearly"}))
    assert pro["tier"] == "pro" and "AI" not in pro["modes"] and pro["scanners"]
    assert ult["tier"] == "ultimate" and ult["modes"] == ["STRATEGY"] and ult["aiExecutionLocked"] is True
    assert (pro["chartLimit"], ult["chartLimit"]) == (4, 8)


def test_ultimate_ai_modes_only_after_admin_validation(monkeypatch):
    import routes_billing
    import services

    async def plans():
        return routes_billing.DEFAULT_PLANS

    async def validated(key, default=None):
        return True if key == "ai_execution_validated" else default
    monkeypatch.setattr(routes_billing, "get_plans", plans)
    monkeypatch.setattr(services, "get_setting", validated)
    ult = run(get_entitlements({"membership_status": "ACTIVE", "membership_plan": "ultimate"}))
    pro = run(get_entitlements({"membership_status": "ACTIVE", "membership_plan": "pro"}))
    assert {"AI", "STRATEGY_AI"} <= set(ult["modes"]) and ult["aiExecutionLocked"] is False
    assert pro["modes"] == ["STRATEGY"]


def test_suspended_account_gets_nothing():
    ent = run(get_entitlements({"account_status": "suspended", "membership_status": "ACTIVE"}))
    assert ent["botAccess"] is False and ent["modes"] == []


def test_license_allows_free_but_keeps_affiliate_and_suspension_checks():
    free = run(compute_license({"membership_status": "EXPIRED", "affiliate_status": "VERIFIED"}))
    assert free["authorized"] is True and free["tier"] == "free"
    assert run(compute_license({"membership_status": "EXPIRED", "affiliate_status": "PENDING"}))["authorized"] is False
    banned = run(compute_license({"account_status": "banned", "membership_status": "ACTIVE", "affiliate_status": "VERIFIED"}))
    assert banned["authorized"] is False


@pytest.mark.parametrize("mode", ["AI", "STRATEGY_AI"])
def test_free_member_cannot_select_ai_trading(mode):
    free = {"membership_status": "EXPIRED"}
    assert run(_check_mode(free, "STRATEGY"))["tier"] == "free"
    with pytest.raises(HTTPException) as e:
        run(_check_mode(free, mode))
    assert e.value.status_code == 403


def test_free_member_has_no_premium_capabilities():
    ent = run(get_entitlements({"membership_status": None}))
    assert ent["chartLimit"] == 1 and not ent["cloudStrategies"]
    assert not any(ent.get(k) for k in ("scanners", "aiInsights", "premiumTools"))


def test_pocket_option_referral_requirement_applies_only_to_pocket_option():
    from services import compute_license
    free = {"id": "u1", "membership_status": None, "affiliate_status": "PENDING"}
    po = run(compute_license(free))
    assert po["authorized"] is False and po["reasons"] == ["affiliate_not_verified"]
    assert "Pocket Option" in po["reasonMessages"][0]
    assert po["brokerEligibility"]["pocket_option"]["eligible"] is False
    other = run(compute_license(free, broker="coinbase"))
    assert other["authorized"] is True and other["reasons"] == []


def test_verified_pocket_option_free_member_gets_strategy_license():
    from services import compute_license
    lic = run(compute_license({"id": "u2", "membership_status": None, "affiliate_status": "VERIFIED"}))
    assert lic["authorized"] is True and lic["tier"] == "free"
