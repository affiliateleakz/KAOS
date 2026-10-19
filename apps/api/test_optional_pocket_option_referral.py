"""Broker referrals are optional: onboarding must not advertise a fake mandatory signup."""
import asyncio
from unittest.mock import AsyncMock
import routes_extension as ext
import services

def test_referral_config_is_optional_without_demo_link(monkeypatch):
    monkeypatch.setattr(services,"get_setting",AsyncMock(return_value={}))
    result=asyncio.run(ext.affiliate_config())
    assert result["referralRequired"] is False
    assert result["affiliateUrl"] is None
    assert "optional" in result["instructions"].lower()

def test_referral_config_keeps_owner_link_but_not_a_requirement(monkeypatch):
    monkeypatch.setattr(services,"get_setting",AsyncMock(return_value={
        "affiliateUrl":"https://example.com/optional-referral",
        "instructions":"You must register via this link",
    }))
    result=asyncio.run(ext.affiliate_config())
    assert result["affiliateUrl"]=="https://example.com/optional-referral"
    assert result["referralRequired"] is False
    assert "never required" in result["instructions"]
