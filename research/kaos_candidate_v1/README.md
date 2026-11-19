# KAOS candidate research: separate spot and binary tracks

This is a new, bounded strategy experiment, not a renamed upload or a production strategy replacement. It contains deterministic candle rules, not a trained AI model. **No extension, website, hosted runtime, account, or live trading settings are changed.**

`plan.json` was committed as `d29c948` before evaluation. It fixes the 12 spot candidates, 12 binary candidates, costs, selection rules and reserved-data policy. A failing configuration is not replaced by a winner selected from its confirmation results.

## Crypto spot approach

Long-only trend following on complete five- and fifteen-minute candles:

- **Breakout:** a closed break of the preceding 20-bar high, aligned with EMA50 above EMA200.
- **Pullback:** a prior touch/close below EMA20 followed by a green closed reclaim, within the same longer uptrend.
- **Trend cross:** EMA20 crossing above EMA50, with green-body confirmation and the longer uptrend.

All require price above EMA200, 250 warmup candles, Wilder ATR14, and complete continuous history. Stops sit two ATR below the next observed entry; targets are 1.5 or 2 times that risk distance. Maximum holding time is twelve requested candles (one or three hours). Positions cannot overlap within an asset.

The simulator observes one-minute bars, handles a gap through a stop at its worse open, assumes the stop occurs first when both levels appear within one minute, and gives no favorable target gap-price improvement. Slippage is charged against entry and exit, including exits at a target. Exit timestamps identify the observed minute bucket, not a known exact intraminute fill; the entire exit minute is unavailable for re-entry. Full holding horizons must fit inside the continuous source and evaluation period, even if a trade might exit early.

Base costs are **10 bps fee plus 2 bps slippage per side**. Combined stress uses **20 bps fee plus 4 bps slippage per side and a one-minute entry delay**. These assumptions are not verified account-specific fees and may understate costs at some brokers. There are no borrow/funding charges because the test is long-only unlevered spot.

Results are reported in **R**, where one R is the original nominal two-ATR price risk per trade. Slippage and fees can make a stopped trade lose more than one R. Units are independently reset per trade; summed R is not a shared-capital portfolio return, a dollar profit, or a compound equity curve. No win-rate-only profitability inference is made.

### Data and selection

Six spot pairs: BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT, XRPUSDT, ADAUSDT. Monthly minute archives run from January 2025 through October 2026. Every archive is checksum verified, and local arrays are checked against manifest hashes before replay. Empty minute intervals are excluded, gaps reset history, and incomplete resampled candles are dropped. ADA has gaps and less usable history; `coverage.json` discloses ready validation bars per market and timeframe.

2025 supplies historical context; these fixed rules are not fitted to its outcomes. Validation is January–August 2026. At most one global configuration can advance to September–October confirmation on the newly collected BNB/XRP/ADA series. Existing BTC/ETH/SOL histories were already used elsewhere. Even the new series share crypto market conditions with those histories: this is retrospective transfer research, not pristine independent market-regime evidence or prospective validation.

Validation requires at least 200 trades, 30 active UTC dates, profit factor at least 1.10, positive net R, four profitable markets, positive multiplicity-adjusted day-bootstrap lower mean, positive combined stress, and higher mean R per trade than both risk-matched baselines. Baselines use always-long and EMA200 trend-long signals, with identical exits, costs, holding limits and position rules. Buy-and-hold percentage returns are also reported on validation, explicitly without risk matching.

Daily clustering pools correlated markets by entry date. The fixed bootstrap has 5,000 resamples, seed 5519, with the validation lower quantile at 0.05/12 and confirmation at 0.025. This does not eliminate dependence, research reuse, or selection bias. `spot_selection.json` is written before the optional final replay. If no candidate passes validation, confirmation remains unscored.

## Pocket Option approach

A separate mirrored CALL/PUT rule set uses one- and five-minute candles, with expiries of one or three candles. It compares trend breakouts, trend pullbacks and a range-band reclaim rule. The range rule requires a preceding close outside two population-standard-deviation bands, a reversal close back inside, and EMA20/50 distance below ATR14. All rules need 60 contiguous indicator candles.

This uses the user's actual archived five-second broker candles, without assuming they represent executable accepted orders or verified live-account quotes. Only the historical period before October 5, 2026 at 18:10:50 UTC is evaluated. The later reserved period is physically truncated before aggregation and indicators. No per-asset overlap, fabricated gap prices, crossing settlements, martingale or compounding is allowed. Ties refund stakes.

Payout scenarios are 70%, 80%, 90% and 92%. Combined stress delays entry five seconds **and** worsens its quote by one basis point in the trade direction. Expiry runs from the delayed entry. Historical eligibility uses the 80%-payout breakeven rate, sample size, day-bootstrap, asset diversity and adjusted significance checks specified in the plan. A historical pass would still require at least thirty days of prospective paper/demo evidence with actual accepted quotes, payouts and settlement rules; it would not authorize live trading.

## Paper signal interface

`strategy.py` exposes `paper_signal(...)` for complete requested-timeframe candles, supported research symbols, a frozen rule family and an explicit current timestamp. It holds on unsupported markets, insufficient history, forming/stale candles, and rejects malformed or discontinuous inputs. Returned setups always carry `executionEnabled: false` and `researchOnly: true`. Stops and targets must be anchored to a subsequently observed entry, not the signal candle's close. This helper has no credentials, network access, order API or production integration. A BUY setup is not a profitability approval.

## Reproduce

Python needs numpy, pandas, scipy and httpx:

```bash
python scripts/collect_timeframe_history.py --symbols BNBUSDT XRPUSDT ADAUSDT --out /private/new-assets --cache /private/archive-cache
python scripts/research_kaos_candidates.py --minutes /private/existing-btc-eth-sol /private/new-assets --po /private/KAOS-export.zip
python -m pytest -q scripts/tests/test_kaos_candidate_research.py
```

The existing BTC/ETH/SOL arrays can be recreated with the collector's default symbols. Raw user data and full downloaded arrays remain outside Git. `provenance.json` records source hashes, plan hash, runner hash and strategy hash. See the result files for every candidate, the selection decision, benchmark results, data coverage, and whether confirmation was opened.

## Results

Spot: **12 candidates**, **0 eligible**, selected: **none**. Confirmation evaluated: **False**. Confirmation qualified: **False**.

The validation table discloses every fixed candidate. Its numbers combine independently sized one-risk-unit trades; they are not percentages or achievable pooled-account returns. Costs include both entry and exit.

| Candle | Rule | Target R | Trades | Net R | Mean R/trade | Profit factor | Combined-stress net R | Always-long mean R | Trend-long mean R | Eligible |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 5m | breakout20 | 1.5 | 5,107 | -4238.87 | -0.830 | 0.198 | -8558.77 | -0.807 | -0.830 | False |
| 5m | breakout20 | 2.0 | 4,842 | -3997.49 | -0.826 | 0.230 | -8077.53 | -0.799 | -0.820 | False |
| 5m | pullback20 | 1.5 | 7,554 | -6416.58 | -0.849 | 0.157 | -13079.34 | -0.807 | -0.830 | False |
| 5m | pullback20 | 2.0 | 7,491 | -6300.94 | -0.841 | 0.181 | -12862.47 | -0.799 | -0.820 | False |
| 5m | trend_cross | 1.5 | 1,090 | -990.64 | -0.909 | 0.151 | -1954.47 | -0.807 | -0.830 | False |
| 5m | trend_cross | 2.0 | 1,090 | -983.60 | -0.902 | 0.179 | -1955.13 | -0.799 | -0.820 | False |
| 15m | breakout20 | 1.5 | 1,595 | -620.13 | -0.389 | 0.450 | -1321.31 | -0.414 | -0.405 | False |
| 15m | breakout20 | 2.0 | 1,503 | -599.26 | -0.399 | 0.457 | -1254.41 | -0.414 | -0.401 | False |
| 15m | pullback20 | 1.5 | 2,346 | -986.95 | -0.421 | 0.376 | -1975.36 | -0.414 | -0.405 | False |
| 15m | pullback20 | 2.0 | 2,322 | -954.90 | -0.411 | 0.402 | -1941.06 | -0.414 | -0.401 | False |
| 15m | trend_cross | 1.5 | 306 | -141.84 | -0.464 | 0.369 | -268.61 | -0.414 | -0.405 | False |
| 15m | trend_cross | 2.0 | 306 | -134.88 | -0.441 | 0.407 | -266.53 | -0.414 | -0.401 | False |

### Pocket Option historical comparison

**12 candidates**. Historical selection: **none**. Reserved-period outcomes evaluated: **False**. This table uses assumed 80% payout and one-unit stakes.

| Candle | Rule | Expiry candles | Trades | Decided win rate | Net80 | Combined-stress net80 | Historical gate |
|---|---|---:|---:|---:|---:|---:|---|
| 1m | breakout20 | 1 | 494 | 50.20% | -47.40 | -101.60 | False |
| 1m | breakout20 | 3 | 444 | 48.87% | -53.20 | -112.80 | False |
| 1m | pullback20 | 1 | 459 | 50.44% | -42.00 | -81.00 | False |
| 1m | pullback20 | 3 | 413 | 50.73% | -35.60 | -60.20 | False |
| 1m | range_reclaim | 1 | 238 | 45.34% | -43.40 | -59.80 | False |
| 1m | range_reclaim | 3 | 226 | 47.77% | -31.40 | -44.20 | False |
| 5m | breakout20 | 1 | 67 | 46.27% | -11.20 | -7.60 | False |
| 5m | breakout20 | 3 | 58 | 50.00% | -5.80 | -5.80 | False |
| 5m | pullback20 | 1 | 51 | 37.25% | -16.80 | -13.20 | False |
| 5m | pullback20 | 3 | 48 | 43.75% | -10.20 | -12.00 | False |
| 5m | range_reclaim | 1 | 43 | 55.81% | 0.20 | -1.60 | False |
| 5m | range_reclaim | 3 | 37 | 54.05% | -1.00 | -2.80 | False |

Passing code checks verifies the replay mechanics, not investment performance. An unqualified candidate must not be described as a proven strategy or published as a profitable pretrained model. No real-money deployment follows from these artifacts.
