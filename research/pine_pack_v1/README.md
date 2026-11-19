# KAOS Pine Script Pack v1 — rule backtest

**Conclusion: no robust trading edge demonstrated. Keep all three scripts as research drafts.**

These original Pine v6 strategy templates provide chart styling, inputs, closed-bar alerts and ATR brackets. This study executes equivalent default signal rules in Python, not Pine or TradingView. Pine compilation and TradingView Strategy Tester results are unverified.

## Method

- Fixed rules were declared before this run; no parameter search, symbol removal or post-result tuning was performed.
- Hourly SPY/QQQ ETF and BTCUSDT/ETHUSDT/SOLUSDT crypto candles: 2025-01-01 through 2026-10-31. Early period is 2025; later evaluation is 2026. Each period starts flat, with earlier indicator warmup.
- This cached public history was used in earlier KAOS research. The later period is chronological evaluation, **not pristine unseen out-of-sample evidence**.
- Each instrument/strategy starts with $10,000 and invests 10% of current equity per position, long only, no leverage. Results are separate sleeves, not a shared portfolio.
- Crypto commission assumption: 0.4% per side; ETF commission assumption: zero. Both use 2 basis points adverse slippage per side. Stress doubles both fee and slippage assumptions. These are assumptions, not verified personal broker fee schedules.
- Confirmed-close signals fill at the next observed open. Signal ATR is frozen for stop/target offsets from actual entry. Stops take priority if both brackets touch. Stop gaps fill at the worse observed open; end positions liquidate at the last close with costs.
- Drawdown below uses the close-marked equity curve, not all intrabar excursions. Fractional units are modeled; broker lot sizes, taxes, dividends and margin/funding are not. USDT is assumed equal to USD.
- Pine uses tick-rounded bracket distances and slippage measured in ticks; this Python study uses raw ATR distances and basis points. TradingView historical intrabar path rules can also differ. These results are **not claimed exact Pine parity**.

## Later-period net results (baseline costs)

| Strategy | Instrument | Net return | Trades | Win rate | Close-marked max DD |
|---|---|---:|---:|---:|---:|
| trend | SPY | -0.40% | 22 | 31.8% | 0.50% |
| reclaim | SPY | +0.02% | 15 | 53.3% | 0.33% |
| breakout | SPY | -0.01% | 33 | 36.4% | 0.58% |
| trend | QQQ | -0.13% | 19 | 42.1% | 0.73% |
| reclaim | QQQ | -0.91% | 9 | 0.0% | 0.97% |
| breakout | QQQ | +0.74% | 30 | 43.3% | 0.65% |
| trend | BTCUSDT | -8.09% | 87 | 24.1% | 8.15% |
| reclaim | BTCUSDT | -3.43% | 44 | 18.2% | 3.50% |
| breakout | BTCUSDT | -8.73% | 120 | 30.0% | 8.78% |
| trend | ETHUSDT | -8.50% | 90 | 26.7% | 8.93% |
| reclaim | ETHUSDT | -3.74% | 42 | 23.8% | 3.87% |
| breakout | ETHUSDT | -8.23% | 118 | 33.9% | 8.43% |
| trend | SOLUSDT | -7.56% | 96 | 30.2% | 7.71% |
| reclaim | SOLUSDT | -2.09% | 39 | 43.6% | 2.35% |
| breakout | SOLUSDT | -7.48% | 119 | 32.8% | 7.74% |

## Full early/later and stress results

| Strategy | Instrument | Period | Costs | Return | Trades | Profit factor |
|---|---|---|---|---:|---:|---:|
| trend | SPY | early | 1x | -0.01% | 28 | 0.99 |
| trend | SPY | early | 2x | -0.18% | 28 | 0.84 |
| trend | SPY | later | 1x | -0.40% | 22 | 0.56 |
| trend | SPY | later | 2x | -0.47% | 22 | 0.51 |
| reclaim | SPY | early | 1x | -0.16% | 17 | 0.71 |
| reclaim | SPY | early | 2x | -0.21% | 17 | 0.64 |
| reclaim | SPY | later | 1x | +0.02% | 15 | 1.04 |
| reclaim | SPY | later | 2x | -0.06% | 15 | 0.88 |
| breakout | SPY | early | 1x | +0.36% | 37 | 1.25 |
| breakout | SPY | early | 2x | +0.30% | 36 | 1.21 |
| breakout | SPY | later | 1x | -0.01% | 33 | 0.99 |
| breakout | SPY | later | 2x | -0.11% | 33 | 0.92 |
| trend | QQQ | early | 1x | +0.44% | 25 | 1.38 |
| trend | QQQ | early | 2x | +0.05% | 25 | 1.04 |
| trend | QQQ | later | 1x | -0.13% | 19 | 0.89 |
| trend | QQQ | later | 2x | -0.18% | 19 | 0.85 |
| reclaim | QQQ | early | 1x | -0.51% | 18 | 0.43 |
| reclaim | QQQ | early | 2x | -0.56% | 18 | 0.39 |
| reclaim | QQQ | later | 1x | -0.91% | 9 | 0.00 |
| reclaim | QQQ | later | 2x | -0.94% | 9 | 0.00 |
| breakout | QQQ | early | 1x | +1.13% | 33 | 1.97 |
| breakout | QQQ | early | 2x | +1.04% | 33 | 1.84 |
| breakout | QQQ | later | 1x | +0.74% | 30 | 1.49 |
| breakout | QQQ | later | 2x | +0.65% | 30 | 1.41 |
| trend | BTCUSDT | early | 1x | -10.45% | 114 | 0.13 |
| trend | BTCUSDT | early | 2x | -18.92% | 115 | 0.02 |
| trend | BTCUSDT | later | 1x | -8.09% | 87 | 0.18 |
| trend | BTCUSDT | later | 2x | -14.77% | 89 | 0.04 |
| reclaim | BTCUSDT | early | 1x | -4.90% | 62 | 0.07 |
| reclaim | BTCUSDT | early | 2x | -9.93% | 62 | 0.01 |
| reclaim | BTCUSDT | later | 1x | -3.43% | 44 | 0.08 |
| reclaim | BTCUSDT | later | 2x | -6.90% | 44 | 0.01 |
| breakout | BTCUSDT | early | 1x | -14.84% | 157 | 0.20 |
| breakout | BTCUSDT | early | 2x | -25.62% | 158 | 0.05 |
| breakout | BTCUSDT | later | 1x | -8.73% | 120 | 0.36 |
| breakout | BTCUSDT | later | 2x | -17.62% | 121 | 0.11 |
| trend | ETHUSDT | early | 1x | -9.44% | 102 | 0.34 |
| trend | ETHUSDT | early | 2x | -16.91% | 102 | 0.14 |
| trend | ETHUSDT | later | 1x | -8.50% | 90 | 0.23 |
| trend | ETHUSDT | later | 2x | -15.14% | 90 | 0.05 |
| reclaim | ETHUSDT | early | 1x | -4.68% | 54 | 0.16 |
| reclaim | ETHUSDT | early | 2x | -9.02% | 54 | 0.00 |
| reclaim | ETHUSDT | later | 1x | -3.74% | 42 | 0.13 |
| reclaim | ETHUSDT | later | 2x | -7.04% | 42 | 0.01 |
| breakout | ETHUSDT | early | 1x | -12.46% | 148 | 0.47 |
| breakout | ETHUSDT | early | 2x | -22.54% | 148 | 0.25 |
| breakout | ETHUSDT | later | 1x | -8.23% | 118 | 0.48 |
| breakout | ETHUSDT | later | 2x | -16.77% | 118 | 0.21 |
| trend | SOLUSDT | early | 1x | -9.53% | 93 | 0.37 |
| trend | SOLUSDT | early | 2x | -16.25% | 93 | 0.18 |
| trend | SOLUSDT | later | 1x | -7.56% | 96 | 0.40 |
| trend | SOLUSDT | later | 2x | -15.29% | 96 | 0.14 |
| reclaim | SOLUSDT | early | 1x | -4.16% | 57 | 0.42 |
| reclaim | SOLUSDT | early | 2x | -8.58% | 57 | 0.14 |
| reclaim | SOLUSDT | later | 1x | -2.09% | 39 | 0.28 |
| reclaim | SOLUSDT | later | 2x | -5.23% | 39 | 0.02 |
| breakout | SOLUSDT | early | 1x | -11.01% | 143 | 0.54 |
| breakout | SOLUSDT | early | 2x | -20.98% | 143 | 0.31 |
| breakout | SOLUSDT | later | 1x | -7.48% | 119 | 0.55 |
| breakout | SOLUSDT | later | 2x | -16.12% | 118 | 0.26 |

## Provenance and reproduction

Source manifest retrieval timestamp: `2026-11-17T04:36:46.798030+00:00`. Rule-plan SHA-256: `462b74f5d49322163946c0906b911e9d8df5e90b50c168b50a815883e34773ae`.

ETF prices come from Yahoo indicative hourly history. Crypto prices come from Binance public spot archives (these are not Coinbase/Kraken fills). Source JSON hashes are recorded in `results/summary.json`; the runner verifies them against the collection manifest. Reuse `scripts/collect_all_in_one_history.py` to obtain the same collection range and preserve the manifest/cache; provider revisions may differ.

Run: `python scripts/backtest_pine_pack.py --data /path/to/all-in-one-hourly`.
Fill-assumption checks: `python -m pytest -q scripts/tests/test_pine_pack_backtest.py` (four passed).
Full individual trade ledger: `research/pine_pack_v1/results/trades.csv`. Summary: `research/pine_pack_v1/results/summary.json`.

No real orders were placed. No profitable, production-ready, options/binary or cross-broker strategy claim is supported by these results.
