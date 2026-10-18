# KAOS Strategy v2 — Structure Breakout + Pullback (research candidate)

**Not validated as profitable. Does not place live orders.** Replaces vague “score triggers” with deterministic candle-based entries. Exactly the same signals work on any regularly spaced OHLC/volume series; different market fee schedules and short-sale permissions must be supplied separately.

## Rules
- EMA20 / EMA50 trend filter, EMA20 slope over 4 finished candles.
- Setup A: 20-bar structural breakout in trend direction; candle body at least 45% of candle range; close beyond structure by 0.15 ATR; if volume supplied, require 1.2x prior 20-bar median.
- Setup B: touch near EMA20 during the prior three candles; resume through the previous candle high or low with a bullish/bearish candle; avoid overextended entries.
- Long/short mirrored. Signal at bar close; next bar open entry. ATR14, 1.5 ATR initial stop, 3 ATR target (2:1 initial R/R), time exit 48 candles. All rule parameters fixed in this version.
- One active trade per series. 0.5% account equity target risk per trade, capped by available cash; **spot longs only** with `--no-shorts`. (Shorts require permissions, margin and additional borrowing/financing costs not implemented.)
- Gap beyond stop fills at next open, and when OHLC has touched both target and stop on one candle, stop wins. Both opening and closing fills apply adverse slippage. Fees apply to entry and exit notional. The closed-trade drawdown proxy does NOT include intratrade drawdown or gaps between recorded candles.

## Run
Python 3.10+, `pip install pandas numpy`.

`python kaos_strategy.py your_candles.csv --fee-bps 10 --slippage-bps 5 --no-shorts --out results`

Input CSV headers: `time,open,high,low,close,volume`; volume is optional. Candles must be sorted by time, equally spaced and not have missing intervals. This first version does not detect gaps or split/adjust corporate actions; clean input first.

Outputs: `results/signals.csv`, `trades.csv`, `summary.json`.

Run correctness checks: `python -m unittest -v test_strategy.py`.

## Important limitations
- Research script, **not a validated live strategy**; no live orders, exchange APIs, or AI.
- Slippage and fees must be entered from real accounts; price impact and borrow costs not modeled. Only one-position fully funded backtest, including for options it is **not** a contract-level model.
- No untouched real stock / cryptocurrency / forex exchange data has been tested for this v2 candidate. Synthetic tests confirm software behavior, not edge.
- Before deploying: real instrument history, timestamp integrity, walk-forward splits, realistic execution, benchmark comparisons, portfolio tests, paper fills, stress and adverse gaps, third-party audit.
