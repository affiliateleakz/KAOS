"""Platform-agnostic runner for KAOS Strategy v1.

It does one thing: on every closed bar it asks `strategy.evaluate()` for an intent and
either prints it (paper) or hands it to a broker callback you implement. No broker
credentials, no order code that could fire by accident - paper mode is the default and
the only mode that ships enabled.

    python3 platforms/live_runner.py --symbol BTCUSD --tf 5m --source coinbase --paper
    python3 platforms/live_runner.py --symbol EURUSD --tf 5m --source csv --paper

The paper account lives in platforms/paper_state.json so a restart does not lose the
open position or the realised ATR total.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import data  # noqa: E402
from strategy import DEFAULT, brackets, evaluate  # noqa: E402

STATE = HERE / "paper_state.json"
TF_SECONDS = {"1m": 60, "5m": 300, "15m": 900, "1h": 3600, "4h": 14400}

PROFILE = DEFAULT  # validated profile: 3.0 ATR target, 5.0 ATR stop, 24-bar expiry


def load_state() -> dict:
    if STATE.exists():
        return json.loads(STATE.read_text())
    return {"position": None, "closed": [], "total_atr": 0.0, "equity_atr": 0.0}


def save_state(state: dict) -> None:
    STATE.write_text(json.dumps(state, indent=2))


def fetch(symbol: str, tf: str, source: str, bars: int) -> pd.DataFrame:
    """CSV cache for offline work, Coinbase public candles for live crypto."""
    if source == "csv":
        return data.load(symbol, tf).tail(bars).reset_index(drop=True)
    if source == "coinbase":
        if tf in data.COINBASE_GRANULARITY:
            return data.fetch_coinbase(symbol, tf, bars).tail(bars).reset_index(drop=True)
        base = data.base_timeframe_for_4h(tf, symbol)
        frame = data.fetch_coinbase(symbol, base, bars * 4)
        return data.resample(frame, tf).tail(bars).reset_index(drop=True)
    raise SystemExit(f"unsupported source {source!r}")


def manage_open(state: dict, bar: dict) -> None:
    """Score the open paper position against the bar that just closed."""
    pos = state["position"]
    if not pos:
        return
    side, stop, target = pos["side"], pos["stop"], pos["target"]
    hit_stop = bar["low"] <= stop if side == "long" else bar["high"] >= stop
    hit_tp = bar["high"] >= target if side == "long" else bar["low"] <= target
    if hit_stop:                       # pessimistic: stop wins a same-bar tie
        exit_price, outcome = stop, "stop"
    elif hit_tp:
        exit_price, outcome = target, "target"
    else:
        pos["bars"] += 1
        if pos["bars"] >= pos["expiry_bars"]:
            exit_price, outcome = bar["close"], "expiry"
        else:
            return
    pnl_atr = (exit_price - pos["entry"]) / pos["atr"] * (1 if side == "long" else -1)
    state["position"] = None
    state["total_atr"] = round(state["total_atr"] + pnl_atr, 4)
    state["closed"].append({"entry_ts": pos["entry_ts"], "exit_ts": str(bar["ts"]),
                            "side": side, "entry": pos["entry"], "exit": exit_price,
                            "outcome": outcome, "pnl_atr": round(pnl_atr, 4)})
    print(f"  closed {side} {outcome} at {exit_price} -> {pnl_atr:+.3f} ATR "
          f"(total {state['total_atr']:+.3f})")


def main() -> None:
    ap = argparse.ArgumentParser(description="KAOS Strategy v1 runner (paper only)")
    ap.add_argument("--symbol", default="BTCUSD")
    ap.add_argument("--tf", default="5m")
    ap.add_argument("--source", default="coinbase", choices=("coinbase", "csv"))
    ap.add_argument("--bars", type=int, default=600)
    ap.add_argument("--paper", action="store_true", default=True,
                    help="only paper trading is implemented; live routing needs your broker code")
    args = ap.parse_args()

    bar_seconds = TF_SECONDS.get(args.tf, 300)
    state = load_state()
    print(f"KAOS v1 | {args.symbol} {args.tf} | source={args.source} | paper only")
    if not args.paper:
        raise SystemExit("live order routing is intentionally not implemented")

    last_ts = None
    while True:
        try:
            frame = fetch(args.symbol, args.tf, args.source, args.bars)
        except Exception as exc:
            print(f"  feed error: {exc}; retrying in 30s")
            time.sleep(30)
            continue
        if frame.empty:
            time.sleep(10)
            continue

        last_bar = frame.iloc[-2] if len(frame) > 1 else frame.iloc[-1]
        if last_ts is not None and str(last_bar["ts"]) == last_ts:
            time.sleep(max(5, bar_seconds // 10))
            continue
        last_ts = str(last_bar["ts"])

        manage_open(state, last_bar)
        intent = evaluate(frame.iloc[:-1].reset_index(drop=True), PROFILE, bar_seconds)
        if intent["tradeable"] and state["position"] is None:
            entry_price = float(last_bar["close"])
            tp, sl = brackets(1 if intent["side"] == "long" else -1,
                              entry_price, intent["atr"], PROFILE, intent["engine"])
            state["position"] = {"side": intent["side"], "entry": entry_price, "stop": sl,
                                 "target": tp, "atr": intent["atr"], "bars": 0,
                                 "expiry_bars": intent["expiry_bars"],
                                 "entry_ts": str(last_bar["ts"])}
            print(f"  {last_bar['ts']} OPEN {intent['side']} {entry_price} "
                  f"stop {sl:.6f} target {tp:.6f} atr {intent['atr']:.6f} "
                  f"expiry {intent['expiry_bars']} bars ({intent['expiry_seconds']}s)")
        else:
            print(f"  {last_bar['ts']} {intent['side']:5s} regime={intent['regime']:10s} "
                  f"er={intent['er'] if intent['er'] is None else round(intent['er'], 3)}")
        save_state(state)
        time.sleep(max(5, bar_seconds // 10))


if __name__ == "__main__":
    main()
