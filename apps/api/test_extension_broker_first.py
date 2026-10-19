"""Selected broker determines referral eligibility during extension startup."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
import routes_botsync as bot

@pytest.mark.parametrize("selected,expected", [
    ("coinbase","coinbase"),
    ("pocketoption","pocket_option"),
    (None,"unselected"),
])
def test_extension_me_uses_selected_broker(monkeypatch,selected,expected):
    db=SimpleNamespace(
        devices=SimpleNamespace(find_one=AsyncMock(return_value=None)),
        member_broker_selections=SimpleNamespace(find_one=AsyncMock(
            return_value={"broker":selected} if selected else None)))
    seen=[]
    async def license_for(user,device,broker):
        seen.append(broker)
        return {"authorized":True}
    monkeypatch.setattr(bot,"db",db)
    monkeypatch.setattr(bot,"compute_license",license_for)
    monkeypatch.setattr(bot,"get_entitlements",AsyncMock(return_value={}))
    req=SimpleNamespace(headers={"X-Device-Id":"install-test"})
    result=asyncio.run(bot.ext_me(req,user={"id":"user1","email":"a@example.test"}))
    assert result["license"]["authorized"] is True
    assert seen==[expected]
