"""KAOS 2.0 fail-closed broker-neutral pretrade risk checks.
Pure, deterministic and independent of broker network/API.
NOT a substitute for persistent atomic reservations and exchange-side limits.
"""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone
from kaos_broker_core import OrderIntent, AssetClass, OrderKind, validate_intent, Capabilities

class RiskRejected(ValueError):
    pass

def amount(value, label, allow_zero=False):
    try:
        v = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise RiskRejected(f"Invalid {label}")
    if not v.is_finite() or v < 0 or (not allow_zero and v == 0):
        raise RiskRejected(f"Invalid {label}")
    return v

@dataclass(frozen=True)
class RiskLimits:
    max_order_notional: str = "25"
    max_total_exposure: str = "100"
    max_daily_loss: str = "20"
    max_open_positions: int = 4
    max_price_age_seconds: int = 10

@dataclass(frozen=True)
class RiskSnapshot:
    now: datetime
    quote_timestamp: datetime
    quote_price: str
    daily_realized_pnl: str
    open_exposure: str
    open_positions: int
    available_quote_balance: str
    emergency_stopped: bool = False
    account_authorized: bool = False
    live_consent: bool = False
    membership_active: bool = False
    broker_connection_verified: bool = False


def check_order(intent: OrderIntent, caps: Capabilities, limits: RiskLimits,
                snapshot: RiskSnapshot, *, live=False, closing_position=False):
    """Returns a normalized risk decision, never submits orders.

    Exposure/balance caps apply to new positions. Verified exits are allowed
    during a loss halt to reduce risk, but not during emergency stop.
    Caller MUST still enforce idempotency, position ownership and sizing.
    """
    try:
        validate_intent(intent, caps)
    except ValueError as exc:
        raise RiskRejected(str(exc)) from exc
    if snapshot.emergency_stopped:
        raise RiskRejected("Emergency stop active")
    if live and not (snapshot.account_authorized and snapshot.live_consent and
                     snapshot.membership_active and snapshot.broker_connection_verified and
                     caps.live_supported):
        raise RiskRejected("Live authorization, consent, membership or broker certification missing")
    if snapshot.now.tzinfo is None or snapshot.quote_timestamp.tzinfo is None:
        raise RiskRejected("Timezone-aware timestamps required")
    age = (snapshot.now - snapshot.quote_timestamp).total_seconds()
    if age < 0 or age > limits.max_price_age_seconds:
        raise RiskRejected("Missing or stale market quote")
    price = amount(snapshot.quote_price, "market price")
    quantity = amount(intent.quantity, "quantity")
    if intent.quantity_unit == "QUOTE" or intent.quantity_unit == "STAKE":
        notional = quantity
    elif intent.quantity_unit == "BASE":
        notional = quantity * price
    else:
        raise RiskRejected("Contract sizing requires broker-specific contract multiplier")
    max_order = amount(limits.max_order_notional, "max order notional")
    max_exposure = amount(limits.max_total_exposure, "max exposure")
    max_loss = amount(limits.max_daily_loss, "max daily loss")
    exposure = amount(snapshot.open_exposure, "open exposure", True)
    balance = amount(snapshot.available_quote_balance, "available quote balance", True)
    pnl = Decimal(str(snapshot.daily_realized_pnl))
    if not pnl.is_finite():
        raise RiskRejected("Invalid daily PnL")
    if not closing_position:
        if pnl <= -max_loss:
            raise RiskRejected("Daily loss limit reached")
        if snapshot.open_positions >= limits.max_open_positions or snapshot.open_positions < 0:
            raise RiskRejected("Open position limit reached")
        if notional > max_order or exposure + notional > max_exposure:
            raise RiskRejected("Notional or total exposure limit reached")
        if intent.side == "BUY" and notional > balance:
            raise RiskRejected("Insufficient quote balance")
    else:
        if intent.side != "SELL" or not intent.metadata.get("source_position_id"):
            raise RiskRejected("Only verified position-closing SELL can bypass entry limits")
    return {"approved": True, "notional": format(notional, "f"),
            "mode": "LIVE_ELIGIBLE" if live else "PAPER_ONLY"}
