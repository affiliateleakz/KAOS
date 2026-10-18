# KAOS Sweep & Reclaim — experimental backtest strategy

A new research-only strategy was added to the existing Backtester selector. It does not alter live trading or KAOS AI.

Logic (completed candles only):
- Look back 12 completed chart bars, excluding the current signal bar.
- BUY when the current candle sweeps below the preceding lowest low, closes back above it, has a lower wick at least 45% of its range, and closes in the top 40% of its range.
- SELL symmetrically on a sweep above the preceding highest high.
- Suppress new signals for 3 chart bars after a signal. Historical execution continues to enforce one open position per market.
- Signal at bar close; fill and settle using next 5-second candle opens as a proxy, not verified broker fills.

Editable JSON parameters: `lookback`, `min_wick_ratio`, `close_position`, `cooldown_bars`.

Historical archive smoke test, 5s chart / 15s expiry:
- EURUSD_otc: 96 wins / 96 losses / 7 ties; 50.00% WR; 19.04 trades/market-hour.
- AUDUSD_otc: 418 wins / 397 losses / 30 ties; 51.29% WR; 23.35 trades/market-hour.
Neither passes 60% WR. These results are from the archived candle dataset, not live broker trades.

Installation: extract ZIP, stop any previous localhost research service with Ctrl+C, run `python research_service/server.py` from the newly extracted folder, then load the new unpacked extension in Chrome. Choose `KAOS Sweep & Reclaim` in Backtester. The engine and UI must come from the same version.
