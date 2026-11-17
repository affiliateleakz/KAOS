# KAOS All-in-one Strategy — v1 backtest

**Decision: this fixed version failed the backtest. It is not ready for live trading and was not installed as a production strategy.**

The requested name is **KAOS All-in-one Strategy**. It is a price-based trend/pullback framework, separate from the experimental 15-second Micro Reversion model and the existing live signature strategy. Its broad name does not imply a profitable strategy for every broker, asset or contract type.

## Frozen rules

`plan.json` was written before the test and data evaluation. One fixed parameter set was used across all 11 instruments; no losing instrument was removed, and no later-period parameter tuning was performed.

1. Trend: last **completed four-hour** close above EMA200 and EMA50 above EMA200 for long bias; reverse for short bias.
2. Entry chart: hourly EMA20/EMA50 pullback zone. A bar touches the zone; within six completed entry bars, confirm a bullish close above the preceding high and EMA20 (reverse for shorts). Cancel a setup when the higher trend changes or an unscheduled quote gap occurs.
3. Enter at the next observed hourly open. Cancel a pending entry after an unscheduled quote gap, a delay over four calendar days, or a price gap over 0.25 signal ATR. These are explicit implementations of the earlier instruction to avoid chasing a moved entry.
4. Stop beyond the setup low/high with a 0.25 Wilder ATR14 buffer. Target twice actual entry-to-stop distance. Stops/targets are fixed, with no martingale or compounding of stake after losses.
5. Intended risk is 0.25% of each instrument sleeve’s realized equity, including estimated stop-fill/commission costs. Size is capped at 1x funded notional at entry. Stock shares/forex base units are whole units; crypto quantities use eight-decimal units. Gaps and holding costs can exceed intended stop risk.
6. Only one position per instrument. Each starts with a separately funded $10,000 sleeve, with no capital reallocation or borrowed leverage. Combined results represent 11 equal starting allocations ($110,000), not a single unrestricted account staking 0.25% independently on every signal. Intended aggregate risk is below the proposed 1% limit under these allocations.

EMA values use an initial SMA seed followed by standard recursion. ATR uses a 14-period seed followed by Wilder smoothing. Completed higher-bar timestamps are joined backward to hourly decision times; there is no higher-timeframe lookahead. Stock four-hour groups start at the exchange session open and include a final shorter group only when the actual session ends. Crypto/forex use UTC four-hour groups requiring four full hourly quotes. Missing hourly groups are excluded, not filled. Scheduled stock closures/weekend forex closures do not manufacture candles.

## Data and scope

Period: **January 1, 2025 through October 31, 2026**, with **2025 development/warmup** and a separate **January–October 2026 later evaluation**. The later run starts flat but retains indicators from earlier history. No parameters or learned model were fitted using later results.

- Stock-market proxies: SPY, QQQ, IWM and DIA ETFs, using Yahoo Finance hourly regular-session quotes and the supplied exchange-session schedule. Stock tests are **long only**; no short-borrow availability is assumed. Reported cash dividends are credited gross when a position was held before the ex-date. No split event occurred in these source snapshots. These are not tests of individual-stock earnings avoidance.
- Crypto: BTCUSDT, ETHUSDT and SOLUSDT, using Binance spot hourly archives. All **66 monthly source archives** were checked against their published SHA-256 checksums. Tests are **spot long only**; short funding is not assumed. USDT is treated at USD parity.
- Forex: EURUSD, GBPUSD, USDJPY and AUDUSD, using Yahoo indicative hourly quotes. Long and short directions are tested without leveraged notional. USDJPY quote P&L is converted back to dollars at exit. Indicative quotes are not verified fills from a particular broker.

Options contracts, binary payouts/expiries, taxes and event/news blackout filters are not tested. Those require separate execution/calendar/contract data. The exported quote snapshots are preserved in the download; current provider data may be revised in the future. The liquid instrument list was fixed in advance, not a historical universe/survivorship study.

## Execution assumptions

| Market | Adverse price each side | Commission each side | Holding cost |
|---|---:|---:|---:|
| Stock ETFs | 1 bp | 0 | Reported gross dividends credited |
| Crypto spot | 2 bp | 10 bp (0.10%) | 0 |
| Forex | 0.5 bp | 0 | 2 bp of entry notional per calendar day |

Forex holding cost is a conservative assumed calendar-time charge, not observed positive/negative broker swaps or a broker-specific rollover schedule. Adverse price includes a spread/slippage allowance and is applied to entries and exits. A gap through a stop fills at the worse observed opening price. A gap beyond a target receives no favorable price improvement. If a candle touches both stop and target, the stop executes first. Open positions are liquidated at the final actual quote. The cash ledger reconciles exactly to recorded trade P&L, including commissions, financing and dividends.

The stress run doubles all adverse-fill, commission and assumed forex holding costs without changing signals or parameters. Stop/target execution is still an OHLC approximation; order-book liquidity, intrabar paths and actual broker rejection/latency are unavailable.

## Later-period results: January–October 2026

| Market sleeve | Trades | Net winning trades | Net return | Maximum daily drawdown | Return with doubled costs |
|---|---:|---:|---:|---:|---:|
| Stocks | 144 | 28.47% | -2.08% | 2.59% | -2.14% |
| Crypto | 247 | 31.58% | -4.55% | 5.08% | -6.65% |
| Forex | 520 | 31.35% | -5.73% | 6.42% | -9.21% |

Combined equal-starting-allocation portfolio: **911 trades**, **-4.08% net return**, **4.47% maximum daily drawdown**. These are simulated account returns at the stated conservative sizing, not raw price changes. Profit factors below 1 indicate more gross cash losses than gains after modeled costs. Daily/hourly marking can miss larger intrabar drawdowns.

| Instrument | Trades | Net win rate | Profit factor | Net return |
|---|---:|---:|---:|---:|
| SPY | 38 | 28.95% | 0.752 | -1.52% |
| QQQ | 33 | 30.30% | 0.666 | -2.07% |
| IWM | 35 | 25.71% | 0.646 | -2.29% |
| DIA | 38 | 28.95% | 0.667 | -2.43% |
| EURUSD=X | 141 | 34.04% | 0.722 | -4.56% |
| GBPUSD=X | 134 | 26.12% | 0.588 | -7.87% |
| USDJPY=X | 114 | 30.70% | 0.628 | -6.42% |
| AUDUSD=X | 131 | 34.35% | 0.794 | -4.08% |
| BTCUSDT | 78 | 30.77% | 0.611 | -5.16% |
| ETHUSDT | 86 | 37.21% | 0.855 | -1.95% |
| SOLUSDT | 83 | 26.51% | 0.558 | -6.52% |

The combined weekly-block bootstrap interval is recorded in the JSON report. It is conditional on this short sample and correlated markets, not proof of a future return distribution. All market sleeves lose in the later period; doubled costs worsen every sleeve. Even stock ETFs, with no assumed commission, fail. The fixed strategy has not established an edge.

The full report also includes the 2025 development results; those are not presented as out-of-sample performance. No alternative parameters, inverse trading or post-hoc winning-market subset were selected after reading this evaluation.

## Reproduce and inspect

The downloadable `downloads/KAOS-All-in-one-Backtest-v1.zip` contains the frozen source/rules, normalized hourly snapshots, source manifest, summary and trade CSV. Raw Yahoo/ZIP downloads remain in the private workspace cache; normalized snapshots and their hashes preserve this exact replay. No account data, credentials or API key were used.

```bash
python scripts/collect_all_in_one_history.py --out data/all_in_one_v1 --cache /private/kaos-hourly-cache
python scripts/backtest_all_in_one.py --data data/all_in_one_v1 --out audit/reproduced-all-in-one
python -m pytest apps/api/test_all_in_one_backtest.py -q
```

To reproduce the exact existing sample, use the normalized `data/all_in_one_v1` files in the download rather than refreshing the providers. `source_manifest.json` records input hashes; `audit/summary.json` records plan, runner and strategy hashes. `audit/trades.csv` contains every development, later-period and cost-stress trade.

Tests protect completed higher-timeframe causality, next-open entries, gap stops, stale-entry cancellation, stop-first ambiguity, whole-share/exposure limits, cash-dividend accounting, calendar-time carry and USDJPY conversion. No website, extension strategy selection, broker order, payment setting or live hosting was changed by this work.
