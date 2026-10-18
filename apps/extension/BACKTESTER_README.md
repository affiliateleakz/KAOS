# KAOS Strategy Backtester (research-only)

1. Start Python 3 from this extension directory: `python research_service/server.py` (on Windows: `py research_service/server.py`). Keep the terminal open.
2. Load this unpacked Chrome extension from `chrome://extensions` → Developer mode → Load unpacked.
3. Open **Charts** → **OPEN BACKTESTER**. This opens a separate Chrome tab; historical calculations execute in Python at `127.0.0.1:8765`, not in the extension's trading loop.
4. Import your KAOS `ALL_DATA.json` file, select a market, choose **MACD+RSI** or **Candle Streak**, then **Run historical backtest**. `Test all` evaluates 20 TF/expiry combinations. Export individual trades to CSV.

## Scope and limitations
- The JSON input must contain `rawCandleHistory.byAsset` with `ts`, `open`, `high`, `low`, `close` 5-second candles, or a single array of those candles.
- The engine sorts/deduplicates timestamps, splits recording gaps, rejects incomplete resampled bars, uses only completed candles for signals, and enters/settles at the relevant next 5-second bar open.
- This is a historical **price proxy**, not a verified broker fill or Pocket Option payout backtest. Ties are excluded from win rate. Market-hours are measured per market, not combined live portfolio hours.
- The engine only implements **two exact defined rule sets** currently: MACD histogram zero-cross with RSI 50 confirmation, and N same-color candles. It does **not** execute arbitrary Pine, JS, natural-language rules, or any imported script. Add new strategies explicitly in `research_service/backtest.py` before claiming exact reproduction.
- The local service binds only to loopback. No live trading API is called. Keep the backtester separate from the execution strategy and AI learning.
- No automatic integration with live chart signals or strategy execution. This intentionally preserves the live trading logic.

### Candidate 7B specification reconstruction (experimental)
A separate selector now runs the **partial** B32 Candidate 7B three-engine specification with native expiries (reversal 30s, runner 15s, breakout 30s), not the 20-grid sweep. This is NOT an exact implementation of the original Candidate 7B source: ZigZag 5/3/1 regime and the efficient-bull-run veto remain unimplemented. Do not compare its results to the historical 80.85% claim as if equivalent. Original live trading logic is untouched.
