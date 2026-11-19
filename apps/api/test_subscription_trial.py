"""Trial access requires canonical Stripe card/subscription proof; no real processor/mail calls."""

import asyncio
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
import pytest
from fastapi import HTTPException
import subscription_trial as trials
import services_trading as trading
import services


def run(coro):
    return asyncio.run(coro)


def test_trial_expiry_and_new_free_account_gates(monkeypatch):
    user = {"id": "u", "bot_trial_required": True, "membership_status": "EXPIRED"}
    assert run(trading.get_entitlements(user))["botAccess"] is False
    assert run(services.compute_license(user))["authorized"] is False
    user.update(
        membership_status="TRIAL",
        membership_expires_at=(trials.now() - timedelta(seconds=1)).isoformat(),
    )
    assert run(trading.get_entitlements(user))["botAccess"] is False
    assert run(services.compute_license(user))["authorized"] is False
    # Existing legacy free accounts are preserved, never silently migrated.
    assert (
        run(trading.get_entitlements({"id": "old", "membership_status": "EXPIRED"}))[
            "botAccess"
        ]
        is True
    )


@pytest.mark.parametrize(
    "bad",
    [
        "missing_card",
        "wrong_customer",
        "expired",
        "too_long",
        "unrequested",
        "wrong_claim",
        "unpaid",
    ],
)
def test_invalid_trial_never_grants_access(monkeypatch, bad):
    stamp = int(trials.now().timestamp())
    record = {
        "trial_key": "key",
        "trial_owner": "owner",
        "trial_days": trials.TRIAL_DAYS,
    }
    session = {
        "id": "cs_trial",
        "status": "complete",
        "payment_status": "no_payment_required",
        "metadata": {"kaos_trial_days": str(trials.TRIAL_DAYS)},
        "customer": "cus_trial",
    }
    sub = {
        "customer": "cus_trial",
        "status": "trialing",
        "trial_start": stamp - 10,
        "trial_end": stamp + trials.TRIAL_DAYS * 86400 - 10,
        "default_payment_method": "pm_fixture",
    }
    claim = {"owner": "owner", "session_id": "cs_trial", "used": False}
    method = {"type": "card", "customer": "cus_trial"}
    if bad == "missing_card":
        sub.pop("default_payment_method")
    if bad == "wrong_customer":
        method["customer"] = "cus_other"
    if bad == "expired":
        sub["trial_end"] = stamp - 1
    if bad == "too_long":
        sub["trial_end"] = stamp + 30 * 86400
    if bad == "unrequested":
        record.pop("trial_key")
    if bad == "wrong_claim":
        claim["owner"] = "other"
    if bad == "unpaid":
        session["payment_status"] = "unpaid"
    monkeypatch.setattr(
        trials,
        "db",
        SimpleNamespace(
            subscription_trials=SimpleNamespace(find_one=AsyncMock(return_value=claim))
        ),
    )
    monkeypatch.setattr(
        trials.stripe.PaymentMethod, "retrieve", Mock(return_value=method)
    )
    monkeypatch.setattr(
        trials.stripe.Customer,
        "retrieve",
        Mock(return_value={"id": "cus_trial", "invoice_settings": {}}),
    )
    with pytest.raises(HTTPException):
        run(trials.verify(record, session, sub, {"key": "sk_test_fixture"}))


def test_trial_only_on_monthly_pro_and_requires_card_collection():
    assert trials.eligible_plan({"tier": "pro", "interval": "month", "amount": 2995})
    for tier, interval in [("ultimate", "month"), ("pro", "year"), ("free", "month")]:
        assert not trials.eligible_plan(
            {"tier": tier, "interval": interval, "amount": 9995}
        )
    options = trials.checkout_arguments(True)
    assert options["payment_method_collection"] == "always" and options[
        "payment_method_types"
    ] == ["card"]
    assert trials.subscription_arguments({}, True)["trial_period_days"] == 7
    assert "trial_period_days" not in trials.subscription_arguments({}, False)


def test_used_trial_cannot_be_restarted(monkeypatch):
    monkeypatch.setattr(
        trials,
        "db",
        SimpleNamespace(
            subscription_trials=SimpleNamespace(
                find_one=AsyncMock(return_value={"used": True})
            )
        ),
    )
    with pytest.raises(HTTPException) as exc:
        run(trials.reserve("u@example.com", {"mode": "test"}, "user:u"))
    assert exc.value.status_code == 409


def test_reminder_uses_actual_subscription_snapshot_and_is_idempotent(monkeypatch):
    import mail_delivery

    end = int(trials.now().timestamp()) + 3 * 86400
    subscription = {
        "id": "sub_trial",
        "status": "trialing",
        "trial_end": end,
        "customer": "cus_trial",
        "cancel_at_period_end": False,
    }
    monkeypatch.setattr(
        trials.stripe.Subscription, "retrieve", Mock(return_value=subscription)
    )
    sent = AsyncMock(return_value=True)
    monkeypatch.setattr(mail_delivery, "send_account_email", sent)
    reminders = SimpleNamespace(
        find_one=AsyncMock(return_value=None), update_one=AsyncMock()
    )
    monkeypatch.setattr(
        trials,
        "db",
        SimpleNamespace(
            users=SimpleNamespace(
                find_one=AsyncMock(return_value={"id": "u", "email": "u@example.com"})
            ),
            subscriptions=SimpleNamespace(
                find_one=AsyncMock(
                    return_value={
                        "trial_days": trials.TRIAL_DAYS,
                        "amount": 3995,
                        "currency": "usd",
                        "interval": "month",
                    }
                )
            ),
            trial_reminders=reminders,
        ),
    )
    monkeypatch.setenv("FRONTEND_URL", "https://tradingwithkaos.com")
    run(trials.reminder({"id": "sub_trial"}, {"key": "sk_test_fixture"}))
    assert sent.call_count == 1 and "39.95 USD" in sent.call_args.args[2]
    assert (
        "/dashboard/subscription" in sent.call_args.args[2]
        and "unless canceled" in sent.call_args.args[2]
    )
    reminders.find_one.return_value = {"sent": True}
    run(trials.reminder({"id": "sub_trial"}, {"key": "sk_test_fixture"}))
    assert sent.call_count == 1
    subscription["cancel_at_period_end"] = True
    run(trials.reminder({"id": "sub_trial"}, {"key": "sk_test_fixture"}))
    assert sent.call_count == 1


def test_signed_in_trial_uses_stripe_card_collection_and_current_saved_price(
    monkeypatch,
):
    import routes_billing as billing

    plan = {**billing.DEFAULT_PLANS[0], "amount": 4495}
    user = {"id": "u", "email": "u@example.com"}
    subscriptions = SimpleNamespace(
        find_one=AsyncMock(return_value=None), update_one=AsyncMock()
    )
    monkeypatch.setattr(
        billing,
        "db",
        SimpleNamespace(
            users=SimpleNamespace(find_one=AsyncMock(return_value=user)),
            subscriptions=subscriptions,
            checkout_locks=SimpleNamespace(update_one=AsyncMock()),
        ),
    )
    monkeypatch.setattr(
        billing,
        "active_configuration",
        AsyncMock(return_value={"mode": "test", "key": "sk_test_fixture"}),
    )
    monkeypatch.setattr(billing, "get_plans", AsyncMock(return_value=[plan]))
    monkeypatch.setattr(billing, "_price", AsyncMock(return_value="price_current"))
    monkeypatch.setattr(
        billing.stripe.Customer,
        "create",
        Mock(return_value=SimpleNamespace(id="cus_trial")),
    )
    user["stripe_customer_id"] = "cus_trial"
    create = Mock(
        return_value=SimpleNamespace(
            id="cs_trial", url="https://checkout.stripe.com/c/pay/trial"
        )
    )
    monkeypatch.setattr(billing.stripe.checkout.Session, "create", create)
    monkeypatch.setattr(trials, "reserve", AsyncMock(return_value="trial-key"))
    monkeypatch.setattr(trials, "attach", AsyncMock())
    monkeypatch.setenv("FRONTEND_URL", "https://tradingwithkaos.com")
    result = run(
        billing.checkout(
            SimpleNamespace(plan_id="pro", lookup_key=None, start_trial=True), user
        )
    )
    assert result["session_id"] == "cs_trial"
    args = create.call_args.kwargs
    assert args["subscription_data"]["trial_period_days"] == 7
    assert args["payment_method_collection"] == "always"
    assert args["metadata"]["kaos_trial_days"] == "7"
    assert args["line_items"] == [{"price": "price_current", "quantity": 1}]
    assert "trial=1" in args["cancel_url"]
    billing._price.assert_awaited_once_with(
        plan, {"mode": "test", "key": "sk_test_fixture"}
    )


def test_trial_accepts_a_verified_card_inherited_from_the_same_stripe_customer(
    monkeypatch,
):
    stamp = int(trials.now().timestamp())
    record = {"trial_key": "key", "trial_owner": "owner", "trial_days": 7}
    session = {
        "id": "cs_trial",
        "customer": "cus_trial",
        "status": "complete",
        "payment_status": "no_payment_required",
        "metadata": {"kaos_trial_days": "7"},
    }
    sub = {
        "customer": "cus_trial",
        "status": "trialing",
        "trial_start": stamp,
        "trial_end": stamp + 7 * 86400,
        "default_payment_method": None,
    }
    monkeypatch.setattr(
        trials.stripe.Customer,
        "retrieve",
        Mock(
            return_value={
                "id": "cus_trial",
                "invoice_settings": {"default_payment_method": "pm_inherited"},
            }
        ),
    )
    monkeypatch.setattr(
        trials.stripe.PaymentMethod,
        "retrieve",
        Mock(return_value={"type": "card", "customer": "cus_trial"}),
    )
    monkeypatch.setattr(
        trials,
        "db",
        SimpleNamespace(
            subscription_trials=SimpleNamespace(
                find_one=AsyncMock(
                    return_value={
                        "owner": "owner",
                        "session_id": "cs_trial",
                        "used": False,
                    }
                )
            )
        ),
    )
    assert (
        run(trials.verify(record, session, sub, {"key": "sk_test_fixture"}))
        == sub["trial_end"]
    )
