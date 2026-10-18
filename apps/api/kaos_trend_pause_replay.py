"""Honest closed-candle replay for KAOS Trend-Pause research.

Input is a pair of real OHLC arrays with opening timestamps in milliseconds.
No lookahead: only bars closed as of each 15s confirmation are passed into signal().
Wins and losses are marked at the first candle open after confirmation and the
first candle open at/after the requested horizon. No trades can be sent.
"""
from collections import Counter
from math import isfinite
from kaos_trend_pause import signal, validate

def replay(minute_candles, fifteen_second_candles, *, horizon_seconds=60):
    if horizon_seconds <= 0 or horizon_seconds % 15:
        raise ValueError("Horizon must be a positive multiple of 15 seconds")
    minute = validate(minute_candles)
    fast = validate(fifteen_second_candles)
    if not fast:
        return {"trades": [], "summary": {"trades": 0, "wins": 0, "losses": 0, "ties": 0, "win_rate_ex_ties": None}}
    out = []
    last_exit = -1
    for i in range(1, len(fast)):
        confirmation = fast[i-1]
        entry = fast[i]
        if entry["ts"] <= last_exit:
            continue  # no overlapping open position in one replay
        if entry["ts"] != confirmation["ts"] + 15000:
            continue
        relevant_minutes = [c for c in minute if c["ts"] + 60000 <= entry["ts"]]
        result = signal(relevant_minutes, fast[:i])
        if not result:
            continue
        target = entry["ts"] + horizon_seconds * 1000
        exit_bar = next((bar for bar in fast[i+1:] if bar["ts"] == target), None)
        if exit_bar is None:
            continue  # incomplete future horizon, not a loss or an assumed win
        direction = result["direction"]
        entry_price = entry["open"]
        exit_price = exit_bar["open"]
        if entry_price == exit_price:
            outcome = "TIE"
        elif (exit_price > entry_price) == (direction == "CALL"):
            outcome = "WIN"
        else:
            outcome = "LOSS"
        out.append({"entry_ts": entry["ts"], "exit_ts": exit_bar["ts"], "direction": direction,
                    "entry_price": entry_price, "exit_price": exit_price, "outcome": outcome,
                    "pause_candles": result["pause_candles"], "research_only": True})
        last_exit = exit_bar["ts"]
    counts = Counter(x["outcome"] for x in out)
    decisive = counts["WIN"] + counts["LOSS"]
    duration_hours = (fast[-1]["ts"] - fast[0]["ts"]) / 3600000 if len(fast) > 1 else 0
    return {"trades": out, "summary": {"trades": len(out), "wins": counts["WIN"],
            "losses": counts["LOSS"], "ties": counts["TIE"],
            "win_rate_ex_ties": round(counts["WIN"] / decisive * 100, 2) if decisive else None,
            "trades_per_hour": round(len(out) / duration_hours, 2) if duration_hours else None,
            "data_hours": round(duration_hours, 3),
            "evaluation": "raw_directional_only_no_fees_slippage_or_payout",
            "profitable": None}}
