"""Payment-first lifecycle against an isolated local Mongo database; Stripe/mail are fixtures."""

import asyncio
import os
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock, Mock
import pytest
from fastapi import FastAPI
import httpx
from motor.motor_asyncio import AsyncIOMotorClient
import guest_checkout as guest
import routes_billing as billing
import routes_auth as auth
import subscription_trial as trials


@pytest.mark.parametrize("trial", [False, True])
def test_payment_first_lifecycle(monkeypatch, trial):
    assert os.environ["MONGO_URL"] in (
        "mongodb://127.0.0.1:27017",
        "mongodb://localhost:27017",
    )
    assert os.environ["DB_NAME"] == "kaos_test"

    async def run():
        client = AsyncIOMotorClient(
            os.environ["MONGO_URL"], serverSelectionTimeoutMS=2000
        )
        database = client["kaos_test_guest_" + uuid4().hex]
        for module in (guest, billing, auth, trials):
            monkeypatch.setattr(module, "db", database)
        config = {"mode": "test", "key": "sk_test_fixture", "enabled": True}
        monkeypatch.setattr(
            guest, "active_configuration", AsyncMock(return_value=config)
        )
        monkeypatch.setattr(
            billing, "active_configuration", AsyncMock(return_value=config)
        )
        monkeypatch.setattr(guest, "account_mail_ready", lambda: True)
        monkeypatch.setenv("FRONTEND_URL", "https://website.example")
        monkeypatch.setattr(
            billing, "get_plans", AsyncMock(return_value=billing.DEFAULT_PLANS)
        )
        monkeypatch.setattr(billing, "_price", AsyncMock(return_value="price_fixture"))
        monkeypatch.setattr(billing, "_initial_commission", AsyncMock())
        sent = AsyncMock(return_value=True)
        monkeypatch.setattr(auth, "send_password_reset_email", sent)
        customer = Mock(return_value=SimpleNamespace(id="cus_guest"))
        session_create = Mock(
            return_value=SimpleNamespace(
                id="cs_guest", url="https://checkout.stripe.com/c/pay/fixture"
            )
        )
        monkeypatch.setattr(guest.stripe.Customer, "create", customer)
        monkeypatch.setattr(guest.stripe.checkout.Session, "create", session_create)
        session = {
            "id": "cs_guest",
            "customer": "cus_guest",
            "subscription": "sub_guest",
            "invoice": "in_guest",
            "status": "open",
            "payment_status": "unpaid",
            "url": "https://checkout.stripe.com/c/pay/fixture",
            "customer_details": {"email": "buyer@example.com", "name": "Buyer"},
        }
        monkeypatch.setattr(
            guest.stripe.checkout.Session, "retrieve", lambda *a, **k: dict(session)
        )
        subscription = {
            "id": "sub_guest",
            "customer": "cus_guest",
            "status": "trialing" if trial else "active",
            "trial_start": int(guest.time.time()) - 10,
            "trial_end": int(guest.time.time()) + trials.TRIAL_DAYS * 86400 - 10,
            "default_payment_method": "pm_fixture",
            "current_period_end": int(guest.time.time())
            + (trials.TRIAL_DAYS * 86400 - 10 if trial else 86400),
        }
        monkeypatch.setattr(
            guest.stripe.Subscription, "retrieve", lambda *a, **k: dict(subscription)
        )
        invoice = {
            "id": "in_guest",
            "customer": "cus_guest",
            "subscription": "sub_guest",
            "status": "paid",
            "amount_paid": 0 if trial else 2995,
        }
        monkeypatch.setattr(
            guest.stripe.Invoice, "retrieve", lambda *a, **k: dict(invoice)
        )
        charges = {"data": [{"paid": True, "status": "succeeded"}], "has_more": False}
        monkeypatch.setattr(guest.stripe.Charge, "list", lambda **k: charges)
        monkeypatch.setattr(
            trials.stripe.PaymentMethod,
            "retrieve",
            lambda *a, **k: {
                "id": "pm_fixture",
                "type": "card",
                "customer": "cus_guest",
            },
        )
        app = FastAPI()
        app.include_router(guest.router)
        app.include_router(auth.router)
        try:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app), base_url="https://api.example"
            ) as browser:
                payload = {
                    "plan_id": "pro",
                    "name": "Buyer",
                    "start_trial": trial,
                    "email": "BUYER@example.com",
                    "refCode": "REF",
                }
                monkeypatch.setattr(guest, "account_mail_ready", lambda: False)
                assert (
                    await browser.post("/api/billing/guest-intent", json=payload)
                ).status_code == 503
                assert await database.users.count_documents({}) == 0
                monkeypatch.setattr(guest, "account_mail_ready", lambda: True)
                r = await browser.post("/api/billing/guest-intent", json=payload)
                assert r.status_code == 200, r.text
                assert (
                    "HttpOnly" in r.headers["set-cookie"]
                    and "Secure" in r.headers["set-cookie"]
                )
                purchase = await database.guest_purchases.find_one({})
                session["metadata"] = {
                    **({"kaos_trial_days": str(trials.TRIAL_DAYS)} if trial else {}),
                    "guest_purchase_id": purchase["_id"],
                    "plan_id": "pro",
                }
                assert await database.users.count_documents({}) == 0
                customer.assert_not_called()
                session_create.assert_not_called()
                r = await browser.post("/api/billing/guest-checkout")
                assert r.status_code == 200, r.text
                assert session_create.call_args.kwargs["customer"] == "cus_guest"
                assert "customer_email" not in session_create.call_args.kwargs
                assert session_create.call_args.kwargs["payment_method_types"] == [
                    "card"
                ]
                assert await database.users.count_documents({}) == 0
                r = await browser.post("/api/billing/guest-checkout")
                assert r.status_code == 200
                assert session_create.call_count == 1
                r = await browser.get("/api/billing/guest-status/cs_guest")
                assert r.json() == {"state": "pending"}, r.text
                assert await database.users.count_documents({}) == 0
                async with httpx.AsyncClient(
                    transport=httpx.ASGITransport(app), base_url="https://api.example"
                ) as stranger:
                    assert (
                        await stranger.get("/api/billing/guest-status/cs_guest")
                    ).status_code == 403
                    assert (
                        await stranger.post("/api/billing/guest-resend/cs_guest")
                    ).status_code == 403
                # Account registration racing a pending guest payment cannot be overwritten.
                await database.users.insert_one(
                    {
                        "id": "existing",
                        "email": "buyer@example.com",
                        "password_hash": "unchanged",
                    }
                )
                session.update(
                    status="complete",
                    payment_status="no_payment_required" if trial else "paid",
                )
                assert (await browser.get("/api/billing/guest-status/cs_guest")).json()[
                    "state"
                ] == "signin_required"
                existing = await database.users.find_one({"id": "existing"})
                assert (
                    existing["password_hash"] == "unchanged"
                    and "membership_status" not in existing
                )
                await database.users.delete_one({"id": "existing"})
                for key, bad in [
                    ("customer", "cus_other"),
                    ("metadata", {"guest_purchase_id": "forged", "plan_id": "pro"}),
                ]:
                    before = session[key]
                    session[key] = bad
                    r = await browser.get("/api/billing/guest-status/cs_guest")
                    assert r.status_code == 409, r.text
                    assert await database.users.count_documents({}) == 0
                    session[key] = before
                charges["data"][0]["refunded"] = True
                assert (
                    await browser.get("/api/billing/guest-status/cs_guest")
                ).status_code == 409
                assert await database.users.count_documents({}) == 0
                charges["data"][0]["refunded"] = False
                # Simulate a lost local write after Stripe session creation.
                await database.subscriptions.delete_many({})
                r = await browser.get("/api/billing/guest-status/cs_guest")
                assert r.status_code == 200, r.text
                assert r.json()["state"] == "active" and r.json()["setupRequired"]
                user = await database.users.find_one({"email": "buyer@example.com"})
                assert (
                    user["membership_status"] == ("TRIAL" if trial else "ACTIVE")
                    and user["membership_plan"] == "pro"
                )
                assert user.get("password_hash") is None and not user["email_verified"]
                assert (
                    user["referredByCode"] == "REF"
                    and user["auth_provider"] == "stripe_checkout"
                )
                assert (
                    sent.call_count == 1
                    and sent.call_args.kwargs["account_setup"] is True
                )
                if trial:
                    import stripe_runtime

                    monkeypatch.setattr(
                        stripe_runtime,
                        "configuration",
                        AsyncMock(return_value={**config, "ready": True}),
                    )
                    cancel = Mock(return_value={"cancel_at_period_end": True})
                    monkeypatch.setattr(trials.stripe.Subscription, "modify", cancel)
                    cancelled = await browser.post("/api/billing/guest-cancel/cs_guest")
                    assert cancelled.status_code == 200, cancelled.text
                    assert cancelled.json()["cancelAtPeriodEnd"] is True
                    assert cancel.call_args.kwargs["cancel_at_period_end"] is True
                    import routes_affiliate

                    commission = AsyncMock()
                    monkeypatch.setattr(
                        routes_affiliate, "record_commission", commission
                    )
                    zero = dict(invoice, billing_reason="subscription_create")
                    await billing._paid_invoice(zero)
                    assert (await database.users.find_one({"id": user["id"]}))[
                        "membership_status"
                    ] == "TRIAL"
                    commission.assert_not_called()
                    subscription.update(
                        status="active",
                        current_period_end=int(guest.time.time()) + 30 * 86400,
                    )
                    renewal = dict(
                        invoice,
                        id="in_first_paid",
                        amount_paid=2995,
                        billing_reason="subscription_cycle",
                    )
                    await billing._paid_invoice(renewal)
                    assert (await database.users.find_one({"id": user["id"]}))[
                        "membership_status"
                    ] == "ACTIVE"
                    assert (
                        commission.call_count == 1
                        and commission.call_args.kwargs["event_id"]
                        == "invoice:in_first_paid"
                    )
                token = sent.call_args.args[1]
                # Repeated receipts/webhooks cannot restore a canceled/upgraded membership.
                await database.users.update_one(
                    {"id": user["id"]},
                    {
                        "$set": {
                            "membership_status": "EXPIRED",
                            "membership_plan": "ultimate",
                        }
                    },
                )
                purchase = await database.guest_purchases.find_one(
                    {"_id": purchase["_id"]}
                )
                assert (await guest.from_webhook("cs_guest"))["state"] == "active"
                assert (
                    await browser.get("/api/billing/guest-status/cs_guest")
                ).status_code == 200
                fresh = await database.users.find_one({"id": user["id"]})
                assert (
                    fresh["membership_status"] == "EXPIRED"
                    and fresh["membership_plan"] == "ultimate"
                )
                assert await database.users.count_documents({}) == 1
                assert billing._initial_commission.call_count == (0 if trial else 1)
                # Receipt/session IDs are never password setup credentials.
                assert (
                    await browser.post(
                        "/api/auth/reset-password",
                        json={"token": "cs_guest", "password": "fixture-password-123"},
                    )
                ).status_code == 400
                r = await browser.post(
                    "/api/auth/reset-password",
                    json={"token": token, "password": "fixture-password-123"},
                )
                assert r.status_code == 200, r.text
                fresh = await database.users.find_one({"id": user["id"]})
                assert fresh["email_verified"] and fresh["auth_provider"] == "password"
                assert auth.verify_password(
                    "fixture-password-123", fresh["password_hash"]
                )
                assert (
                    await browser.post(
                        "/api/auth/reset-password",
                        json={"token": token, "password": "changed-password-123"},
                    )
                ).status_code == 400
                r = await browser.post("/api/billing/guest-intent", json=payload)
                assert (
                    r.status_code == 409
                    and r.json()["detail"]["code"] == "SIGN_IN_REQUIRED"
                )
        finally:
            await client.drop_database(database.name)
            client.close()

    asyncio.run(run())


def test_setup_mail_has_fragment_token_and_no_token_logs(monkeypatch):
    monkeypatch.setenv("FRONTEND_URL", "https://website.example")
    monkeypatch.setattr(auth, "smtp_ready", lambda: True)
    send = AsyncMock(return_value=True)
    monkeypatch.setattr(auth, "send_smtp", send)
    assert asyncio.run(
        auth.send_password_reset_email(
            "buyer@example.com", "one-time-fixture", account_setup=True
        )
    )
    assert (
        "/reset-password#token=one-time-fixture&amp;setup=checkout"
        in send.call_args.args[2]
    )
    assert send.call_args.args[1] == "Finish your KAOS account setup"
