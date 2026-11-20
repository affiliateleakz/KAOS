"""Point-in-time KAOS research examples for any explicitly configured holding period.

No executable trades, broker orders, or automated model fitting.
A quote must have a real bid/ask and a source/market identity. Event features
are restricted to observations actually available at decision time.
"""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

DEFAULT_HORIZONS = (5, 10, 15, 30, 60, 300, 900, 3600, 86400, 604800)

def instant(value):
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    else:
        raise ValueError("Unsupported timestamp")
    if dt.tzinfo is None:
        raise ValueError("Timestamp must include timezone")
    return dt.astimezone(timezone.utc).timestamp()

def money(value):
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("Invalid quote") from exc
    if not amount.is_finite() or amount <= 0:
        raise ValueError("Nonpositive or nonfinite quote")
    return amount

def validated_quote(quote):
    if quote.get("simulated") or not quote.get("source") or not quote.get("symbol"):
        raise ValueError("Untrusted quote provenance")
    at = instant(quote["observed_at"])
    bid, ask = money(quote["bid"]), money(quote["ask"])
    if bid > ask:
        raise ValueError("Crossed quote")
    return at, bid, ask

def make_example(entry, exit_quote, horizon_seconds, events=(), *, max_lag_seconds=2, fee_bps=0):
    """Build BUY and SELL net return labels at a measured execution horizon.

    Caller must supply snapshots of the SAME real market/broker and contract.
    Returns a research row, never a trading instruction.
    """
    if type(horizon_seconds) is not int or horizon_seconds < 1:
        raise ValueError("Invalid horizon")
    if type(max_lag_seconds) not in (float, int) or max_lag_seconds < 0:
        raise ValueError("Invalid maximum quote lag")
    if type(fee_bps) not in (float, int) or fee_bps < 0:
        raise ValueError("Invalid fee")
    if any(entry.get(k) != exit_quote.get(k) for k in ("source", "symbol", "asset_class", "contract_id")):
        raise ValueError("Quotes describe different instruments or sources")
    start, entry_bid, entry_ask = validated_quote(entry)
    finish, exit_bid, exit_ask = validated_quote(exit_quote)
    if not start + horizon_seconds <= finish <= start + horizon_seconds + max_lag_seconds:
        raise ValueError("Missing exact expiry observation; never interpolate from candles")
    available_events = []
    for event in events:
        published = instant(event["published_at"])
        received = instant(event["received_at"])
        # Both publication and first receipt must precede decision.
        if published <= start and received <= start:
            available_events.append({
                "event_id":event["event_id"], "kind":event["kind"],
                "source":event["source"], "age_seconds":start-max(published, received),
            })
    friction = Decimal(str(fee_bps)) / Decimal("10000")
    long_return = (exit_bid-entry_ask)/entry_ask - friction
    short_return = (entry_bid-exit_ask)/entry_bid - friction
    return {
        "symbol":entry["symbol"], "source":entry["source"],
        "asset_class":entry.get("asset_class"), "contract_id":entry.get("contract_id"),
        "issued_at":entry["observed_at"], "settled_at":exit_quote["observed_at"],
        "horizon_seconds":horizon_seconds,
        "buy_net_return":str(long_return), "sell_net_return":str(short_return),
        "buy_profitable":long_return>0, "sell_profitable":short_return>0,
        "no_trade_preferred":long_return<=0 and short_return<=0,
        "available_events":available_events,
        "research_only":True,
    }
