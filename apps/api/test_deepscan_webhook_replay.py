"""Stripe webhook replay regression checks (no real Stripe calls)."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
import pytest
from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError
import routes_billing as billing

class DummyRequest:
    headers={"stripe-signature":"test"}
    async def body(self):
        return b"test"

def run(coro):
    return asyncio.run(coro)

def setup(monkeypatch, existing, claim_result=1):
    monkeypatch.setattr(billing, "WEBHOOK_SECRET", "test_secret")
    event={"id":"evt_123","type":"unknown.test","data":{"object":{}}}
    monkeypatch.setattr(billing.stripe.Webhook,"construct_event",lambda *args:event)
    def duplicate(*args,**kwargs):
        raise DuplicateKeyError("event exists")
    events=SimpleNamespace(
        insert_one=AsyncMock(side_effect=duplicate),
        find_one=AsyncMock(return_value=existing),
        update_one=AsyncMock(return_value=SimpleNamespace(modified_count=claim_result)),
    )
    monkeypatch.setattr(billing,"db",SimpleNamespace(webhook_events=events))
    return events

def test_completed_webhook_is_duplicate(monkeypatch):
    events=setup(monkeypatch,{"state":"completed"})
    assert run(billing.stripe_webhook(DummyRequest()))=={"status":"duplicate"}
    events.update_one.assert_not_awaited()

def test_processing_webhook_cannot_be_double_claimed(monkeypatch):
    events=setup(monkeypatch,{"state":"processing"},claim_result=0)
    with pytest.raises(HTTPException) as exc:
        run(billing.stripe_webhook(DummyRequest()))
    assert exc.value.status_code==503
    assert events.update_one.await_count==1

def test_stale_event_replay_claims_and_completes(monkeypatch):
    events=setup(monkeypatch,{"state":"processing"},claim_result=1)
    assert run(billing.stripe_webhook(DummyRequest()))=={"status":"ok"}
    assert events.update_one.await_count==2
    assert events.update_one.await_args_list[-1].args[1]["$set"]["state"]=="completed"
