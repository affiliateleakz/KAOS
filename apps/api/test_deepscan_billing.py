"""Regression tests for account ownership in checkout status lookup."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
import routes_billing as api

def run(coro):
    return asyncio.run(coro)

def test_checkout_status_rejects_other_user(monkeypatch):
    find=AsyncMock(return_value=None)
    monkeypatch.setattr(api,"db",SimpleNamespace(subscriptions=SimpleNamespace(find_one=find)))
    with pytest.raises(HTTPException) as raised:
        run(api.status("cs_test_someone_else", user={"id":"member2"}))
    assert raised.value.status_code == 404
    assert find.await_args.args[0] == {"session_id":"cs_test_someone_else","userId":"member2"}

def test_cancel_failed_stripe_call_does_not_mark_member_canceled(monkeypatch):
    class StripeFailure(api.stripe.StripeError):
        pass
    def fail(*args, **kwargs):
        raise StripeFailure("failed")
    monkeypatch.setattr(api,"active_configuration",AsyncMock(return_value={"key":"fixture-only"}))
    update=AsyncMock()
    monkeypatch.setattr(api.stripe.Subscription,"modify",fail)
    monkeypatch.setattr(api,"db",SimpleNamespace(users=SimpleNamespace(update_one=update)))
    with pytest.raises(HTTPException) as raised:
        run(api.cancel(user={"id":"user1","stripe_subscription_id":"sub_test"}))
    assert raised.value.status_code == 502
    update.assert_not_awaited()
