"""Platform translation.

A strategy produces one platform-neutral intent:

    {side, entry, stop, target, atr, expiry_bars, ...}

This module turns that intent into the order payload each venue actually accepts. Nothing here
places an order or needs an API key - it builds the request body so the trader (or a runner)
can post it, and so the rule set is provably portable instead of "portable in principle".

    python platforms.py                # print one example intent per platform
    python platforms.py kraken BTCUSD 5m pulse-range
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import core
import evaluate
import strategies  # noqa: F401  (registers the library)

PLATFORMS = {
    "pocketoption": {"name": "Pocket Option", "class": "binary", "order": "binary direction + fixed expiry",
                     "min": "$1 stake", "notes": "Payout 20-92%. Break-even = 1/(1+payout)."},
    "kraken": {"name": "Kraken", "class": "crypto", "order": "limit entry + stop-loss + take-profit",
               "min": "0.0001 BTC", "notes": "Spot. Use `close` for the stop and a second order for the target."},
    "coinbase": {"name": "Coinbase Advanced", "class": "crypto", "order": "limit entry + stop-limit",
                 "min": "$1", "notes": "Spot. Bracket via two conditional orders; no native OCO."},
    "binance": {"name": "Binance", "class": "crypto", "order": "OCO (limit + stop-limit)",
                "min": "$5 notional", "notes": "OCO covers target and stop in one request."},
    "mt5": {"name": "MetaTrader 5", "class": "fx", "order": "pending limit with SL/TP",
            "min": "0.01 lot", "notes": "Broker fills the brackets server-side; expiry via ORDER_TIME_SPECIFIED."},
    "oanda": {"name": "OANDA v20", "class": "fx", "order": "market/limit with stopLossOnFill + takeProfitOnFill",
              "min": "1 unit", "notes": "Positions can be partially closed; units are exact."},
    "tastytrade": {"name": "tastytrade", "class": "equity, options", "order": "equity bracket or multi-leg option",
                   "min": "1 share / 1 contract", "notes": "Options need a chain for strikes; equity brackets are native."},
    "alpaca": {"name": "Alpaca", "class": "equity", "order": "bracket order (order_class=bracket)",
               "min": "1 share", "notes": "Fractional shares do not support brackets."},
}


def _round(price: float, tick: float) -> float:
    return float(np.round(price / tick) * tick)


def intent(strategy_id: str, asset: str, tf: str, bar: int = -1) -> dict:
    """Evaluate the latest closed bar of a cached series and return the neutral intent."""
    strategy = core.get(strategy_id)
    df = evaluate.load_cached(asset, tf)
    if df is None:
        raise SystemExit(f"no cached data for {asset} {tf}")
    if strategy.signal_fn is None:
        # signal-only strategies (options) still need the regime that chooses the structure
        ind = core.indicators(df)
        er = float(ind["er"].iloc[bar])
        trend_up = float(ind["ema_fast"].iloc[bar]) > float(ind["ema_slow"].iloc[bar])
        side = 0 if er <= 0.28 else (1 if trend_up else -1)
        idx = len(ind) + bar if bar < 0 else bar
    else:
        ind, sig = strategy.signal_fn(df, dict(strategy.params))
        idx = len(ind) + bar if bar < 0 else bar
        side = int(sig[idx])
        bars_ago = 0
        while side == 0 and bars_ago < 500 and idx - bars_ago > 0:
            bars_ago += 1
            side = int(sig[idx - bars_ago])
        idx -= bars_ago
    row = ind.iloc[idx]
    atr = float(row["atr"])
    entry = float(row["close"])
    tp, sl = strategy.exit.get("tp_atr"), strategy.exit.get("sl_atr")
    if strategy.mode == "bracket":
        stop = entry - side * sl * atr
        target = entry + side * tp * atr
    else:
        stop = target = float("nan")
    return {"strategy": strategy_id, "asset": asset, "tf": tf, "ts": str(row["ts"]),
            "bars_ago": (len(ind) - 1 - idx),
            "side": "long" if side > 0 else ("short" if side < 0 else "flat"),
            "side_sign": side, "entry": entry, "stop": stop, "target": target,
            "atr": atr, "expiry_bars": strategy.exit.get("expiry_bars"),
            "mode": strategy.mode, "regime": ("range" if row.get("er", 1) <= 0.28 else "trend"),
            "er": float(row.get("er", float("nan"))), "rsi": float(row.get("rsi", float("nan")))}


# --------------------------------------------------------------------------- venues
def pocketoption(it: dict, stake: float = 1.0, payout: float = 0.80) -> dict:
    be = 1 / (1 + payout)
    return {"venue": "pocketoption", "asset": it["asset"], "direction": it["side"],
            "expiry_minutes": 3, "stake": stake, "payout": payout,
            "break_even_win_rate": round(be * 100, 1),
            "note": "Direction only - no stop, no target. Skip when side == flat."}


def kraken(it: dict, volume: float = 0.0001) -> dict:
    pair = {"BTCUSD": "XBTUSD", "ETHUSD": "ETHUSD", "SOLUSD": "SOLUSD", "XRPUSD": "XRPUSD"}.get(it["asset"], it["asset"])
    px = lambda v: _round(v, 0.5)
    return {"venue": "kraken", "pair": pair, "type": "buy" if it["side_sign"] > 0 else "sell",
            "ordertype": "limit", "price": px(it["entry"]), "volume": str(volume),
            "close": {"ordertype": "stop-loss", "price": px(it["stop"])},
            "take_profit_order": {"ordertype": "take-profit", "price": px(it["target"])},
            "validate": True}


def coinbase(it: dict, quote_size: float = 25.0) -> dict:
    return {"venue": "coinbase", "product_id": it["asset"].replace("USD", "-USD"),
            "side": "BUY" if it["side_sign"] > 0 else "SELL",
            "order_configuration": {"sor_limit_ioc": {"limit_price": f"{it['entry']:.2f}",
                                                      "quote_size": f"{quote_size:.2f}"}},
            "exit_orders": [{"type": "stop_limit", "stop_price": f"{it['stop']:.2f}",
                             "limit_price": f"{it['stop'] * (0.999 if it['side_sign'] > 0 else 1.001):.2f}"},
                            {"type": "limit", "limit_price": f"{it['target']:.2f}"}]}


def binance(it: dict, qty: float = 0.0005) -> dict:
    """Spot OCO. A long exits above at the target and below at the stop; a short is the mirror,
    and on Binance spot a short also needs margin/futures enabled."""
    sym = it["asset"].replace("USD", "USDT")
    long_ = it["side_sign"] > 0
    above = it["target"] if long_ else it["stop"]
    below = it["stop"] if long_ else it["target"]
    payload = {"venue": "binance", "symbol": sym, "side": "BUY" if long_ else "SELL",
               "quantity": qty, "order_type": "OCO",
               "above_type": "LIMIT_MAKER", "above_price": round(above, 2),
               "below_type": "STOP_LOSS_LIMIT", "below_stop": round(below, 2),
               "below_price": round(below * (1.001 if long_ else 0.999), 2)}
    if not long_:
        payload["note"] = "Binance spot cannot short; enable margin or use the USD-M futures payload."
    return payload


def mt5(it: dict, lot: float = 0.01, magic: int = 20261120) -> dict:
    sym = it["asset"] if len(it["asset"]) == 6 else f"{it['asset'][:3]}{it['asset'][3:]}"
    digits = 3 if "JPY" in sym else 5
    return {"venue": "mt5", "action": "TRADE_ACTION_PENDING", "symbol": sym, "volume": lot,
            "type": "ORDER_TYPE_BUY_LIMIT" if it["side_sign"] > 0 else "ORDER_TYPE_SELL_LIMIT",
            "price": round(it["entry"], digits), "sl": round(it["stop"], digits),
            "tp": round(it["target"], digits), "magic": magic,
            "type_time": "ORDER_TIME_GTC", "type_filling": "ORDER_FILLING_RETURN",
            "comment": "KAOS"} | ({} if it["expiry_bars"] is None else {"expiry_bars": it["expiry_bars"]})


def oanda(it: dict, units: int = 1000) -> dict:
    sym = f"{it['asset'][:3]}_{it['asset'][3:]}"
    return {"venue": "oanda", "order": {"type": "MARKET", "instrument": sym,
                                        "units": str(units * (1 if it["side_sign"] > 0 else -1)),
                                        "timeInForce": "FOK", "positionFill": "DEFAULT",
                                        "stopLossOnFill": {"price": f"{it['stop']:.5f}"},
                                        "takeProfitOnFill": {"price": f"{it['target']:.5f}"}}}


def alpaca(it: dict, qty: int = 10) -> dict:
    return {"venue": "alpaca", "symbol": it["asset"], "qty": str(qty),
            "side": "buy" if it["side_sign"] > 0 else "sell", "type": "market",
            "time_in_force": "day", "order_class": "bracket",
            "take_profit": {"limit_price": f"{it['target']:.2f}"},
            "stop_loss": {"stop_price": f"{it['stop']:.2f}"}}


def tastytrade_equity(it: dict, qty: int = 10) -> dict:
    return {"venue": "tastytrade", "legs": [{"instrument_type": "Equity", "symbol": it["asset"],
                                             "action": "Buy to Open" if it["side_sign"] > 0 else "Sell to Open",
                                             "quantity": qty}],
            "order_type": "Limit", "price": f"{it['entry']:.2f}",
            "bracket": {"stop": f"{it['stop']:.2f}", "target": f"{it['target']:.2f}"}}


def tastytrade_option(it: dict, dte: int = 35, short_delta: float = 0.18, width: float = 5.0,
                      credit: float | None = None) -> dict:
    """Defined-risk structure from the regime: range -> iron condor, trend -> debit spread."""
    condor = it["regime"] == "range"
    return {"venue": "tastytrade", "underlying": it["asset"], "strategy": "iron_condor" if condor else "vertical_debit",
            "dte": dte, "short_delta": short_delta, "width": width,
            "legs": (["sell put", "buy put", "sell call", "buy call"] if condor else
                     ([f"buy {dte}d call", f"sell {dte}d call"] if it["side_sign"] > 0 else
                      [f"buy {dte}d put", f"sell {dte}d put"])),
            ("credit" if condor else "debit"): credit,
            "management": {"profit_target": 0.5, "stop_multiple": 2.0, "close_at_dte": 21},
            "note": "Needs a live option chain to resolve strikes; the rule is complete, the strikes are not."}


BUILDERS = {"pocketoption": pocketoption, "kraken": kraken, "coinbase": coinbase, "binance": binance,
            "mt5": mt5, "oanda": oanda, "alpaca": alpaca, "tastytrade": tastytrade_equity}


def build(strategy_id: str, platform: str, asset: str, tf: str) -> dict:
    it = intent(strategy_id, asset, tf)
    if core.get(strategy_id).mode == "manual":
        return tastytrade_option(it) if platform == "tastytrade" else {
            "venue": platform, "action": "none", "reason": "structure-only strategy", "intent": it}
    if it["side_sign"] == 0:
        return {"venue": platform, "action": "none", "reason": "no signal on the last closed bar", "intent": it}
    if platform == "pocketoption":
        return pocketoption(it)
    return BUILDERS[platform](it)


def main(argv: list[str]) -> None:
    if len(argv) >= 5:
        print(json.dumps(build(argv[4], argv[1], argv[2], argv[3]), indent=2))
        return
    demo = [("pulse-range", "kraken", "BTCUSD", "5m"), ("pulse-range", "mt5", "EURUSD", "5m"),
            ("orb-equity", "alpaca", "SPY", "5m"), ("crypto-ignition", "binance", "ETHUSD", "15m"),
            ("binary-fade", "pocketoption", "BTCUSD", "5m"), ("options-credit", "tastytrade", "SPY", "1h")]
    for sid, plat, asset, tf in demo:
        try:
            out = build(sid, plat, asset, tf)
        except Exception as exc:  # noqa: BLE001 - demo must keep going
            out = {"error": str(exc)}
        print(f"\n--- {sid} -> {plat} ({asset} {tf}) ---")
        print(json.dumps(out, indent=2))


if __name__ == "__main__":
    import sys

    main(sys.argv)
