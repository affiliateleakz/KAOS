# Trading-strategy catalog and new stock-session tests

Source: [Strike Money:70TradingStrategies](https://www.strike.money/stock-market/trading-strategies). The page contains70numbered entries. `source.json` identifies the source snapshot; common strategy titles and original assessments are in `catalog.csv`. Publisher performance claims were not independently verified and are not adopted as expected returns.

## What the list adds

The list mixes distinct mechanisms, broad trading styles, instruments, allocation approaches and implementation methods. Forex, crypto, options and futures are market/contract classes. Quantitative trading, algorithmic trading, automation and AI describe methods, not a complete profitable entry/exit rule. Position, swing, day trading and scalping specify aspects of holding or execution style. Each still needs exact signals, costs, sizing and exit rules. Dollar-cost averaging changes the timing of cash investment; it does not remove an asset's market risk.

Existing KAOS studies already sampled trend following, momentum allocation, range/mean reversion, breakouts, reversals, and seconds-level trading. A family having been sampled does not mean every variant is exhausted or that an edge was established. The catalog links the actual prior artifacts without claiming that a style itself was fully tested.

Catalog status counts: {'market_style_or_framework': 17, 'family_sampled': 11, 'new_session_tested': 2, 'additional_data_or_execution_model': 34, 'new_rule_to_specify': 6}. These are review classifications, not70backtest results or70deployable strategies.

The data-dependent families remain separate: option spreads/Greeks/theta/skew require historical contracts and executable option quotes; funding/basis arbitrage requires both legs and venue financing; order flow/profile/tape/market making/HFT need trade-print or book data; news/sentiment/insiders/macro need point-in-time publication histories; on-chain/yield/staking require their own transactions, fees and cash-flow models. An OHLC candle test cannot validate those claims. VWAP needs appropriate intraday volume/price data; hourly normalized OHLC alone is not true session VWAP.

## Three new fixed hypotheses

The plan was committed as `7b55287` before evaluation. These are deliberately specified tests inspired by the list, not claims to reproduce the article's chart examples or reported CAGR/win rates. No threshold, market, sample window or alternative selection was changed after observing results.

1. **Opening-range60:** first regular-session full hour defines high/low; the first subsequent completed hour closing above that high signals a long entry at the next observed hourly open. Stop at opening low, target twice entry-to-stop risk, session-close timeout. Skip invalid brackets and entries with less than one hour remaining.
2. **Gap-fade60:** a0.5%–2%opening gap down relative to the immediately previous scheduled session close, followed by a green first hour that has not already filled the gap. Enter second-hour open, target prior close, stop first-hour low, exit by session close.
3. **Overnight timing control:** unconditional long at regular-session final close and exit at the next scheduled regular-session open. No current closing-price pattern is used to decide the order. This differs from the article's broader EOD-analysis examples. No stop fill is inferred during unobserved overnight trading.

Each strategy is tested independently on **SPY, QQQ, IWM, DIA, AAPL, MSFT, NVDA and TSLA**. Both2025andJanuary–October2026results are disclosed; there is no champion selected from2026. These price snapshots and market regimes were already used in earlier studies, so this is retrospective descriptive research, not a fresh prospective or pristine OOS test. All previous reserved crypto and Pocket Option periods remain unscored. These stock-session strategies do not imply forex, crypto or fixed-expiry binary performance.

## Data, costs and controls

The normalized snapshots and original provider responses are hash checked. Original exchange-session metadata identifies the actual previous/next scheduled session. Only complete sessions are scored; missing hours/sessions are excluded rather than filled or bridged. This complete-session sampling can itself bias results if data gaps coincide with events.

The hourly execution model uses actual observed next opens, adverse open fills through stops, target limits without favorable gap improvement, and stop-first ordering when both barriers appear inside an hour. Approximate intrahour exit timestamps are recorded at that base-bar end, not asserted to be accepted broker fills. Intraday positions end at the observed regular-session close, including shorter closing bars. Market-on-close orders are approximated by that close with slippage; their execution is not verified.

Base execution cost is1basis point adverse price per side, with zero illustrative commission. Gross dividends are credited only if held before ex-date; a dividend-related price drop is not treated as free profit. Stress doubles adverse price costs and delays intraday entry by one observed hour. Late entries can therefore disappear under the fixed remaining-session rule. Overnight stress changes costs only, because an intervening after-hours quote is unavailable. Actual commissions, spreads, taxes and auction fills may erase a thin result. There are no shorts, borrow costs, leverage or compound-account claims.

Results use **independent trade-notional basis points** and profit factor. Arithmetic sums of those returns across instruments are diagnostic quantities, not achievable portfolioROI, CAGR or dollar income. Overnight risk between close/open is unobserved; no intranight drawdown or protective stop is claimed.

Controls are unconditional long after the first hour through session close and daily close-to-close buy-and-hold returns including gross dividends. The buy-and-hold daily marks carry no daily transaction charge because they represent continuous exposure, but this omits its initial/final dealing costs. These controls differ in holding time/exposure and are not risk-matched alpha controls. Positive active returns alone cannot establish superiority over holding the market.

The descriptive gate requires100trades,60active dates,PF≥1.10,five profitable assets,positive weekly-cluster lower mean(sum of normalized tradebps),and positive stress mean. The weekly lower bound uses5000resamples,seed719andquantile0.05/3. This within-round correction does not erase the many preceding research trials, dependence among stock markets, survivorship in the fixed universe or hindsight in the data selection. No production model is released even from a descriptive pass.

## Results

| Period | Setup/control | Trades | Mean net bps/trade | PF | Stress trades | Stress mean bps/trade | Descriptive gate |
|---|---|---:|---:|---:|---:|---:|---|
| 2025 | opening_range_60 | 744 | 2.567 | 1.097 | 641 | -4.347 | False |
| 2025 | gap_fade_60 | 115 | 6.789 | 1.326 | 100 | 9.683 | False |
| 2025 | overnight_control | 1944 | 2.845 | 1.072 | 1944 | 0.845 | False |
| 2025 | intraday_control | 1976 | 1.901 | 1.047 | 1976 | 2.538 | control |
| 2025 | buy_hold_daily_control | 1944 | 9.595 | 1.152 | 1944 | 9.595 | control |
| 2026 | opening_range_60 | 588 | -5.182 | 0.793 | 539 | -7.495 | False |
| 2026 | gap_fade_60 | 116 | -3.763 | 0.865 | 87 | -2.751 | False |
| 2026 | overnight_control | 1640 | 2.494 | 1.072 | 1640 | 0.493 | False |
| 2026 | intraday_control | 1656 | -0.794 | 0.976 | 1656 | -6.071 | control |
| 2026 | buy_hold_daily_control | 1640 | 6.825 | 1.118 | 1640 | 6.825 | control |

The opening-range and gap-fade rules change from positive2025samples to negative2026samples. The unconditional overnight control is positive after assumed costs in both periods but thin(PFabout1.07), and fails the fixed gate. Daily buy-and-hold mean returns are higher, with different exposure and unmeasured intrahold risk. No losing year or instrument was discarded, and no parameter was adjusted to force a pass.

## Coverage and verification

| Asset | Original calendar sessions | Complete sessions | Incomplete/missing |
|---|---:|---:|---:|
| SPY | 471 | 454 | 17 |
| QQQ | 471 | 454 | 17 |
| IWM | 471 | 454 | 17 |
| DIA | 471 | 454 | 17 |
| AAPL | 473 | 454 | 19 |
| MSFT | 473 | 454 | 19 |
| NVDA | 473 | 454 | 19 |
| TSLA | 473 | 454 | 19 |

Nine offline checks passed: next-open entry, stop-first ambiguity, adverse stop gaps, capped target gaps, gap confirmation/prior-close eligibility, delay/late-close rejection, dividend-offset economics, missing-calendar-session handling, losing expectancy despite high win rate, and separate overnight stress semantics. Individual checks cover multiple assertions. Tests verify implementation behavior, not future profitability.

Full per-asset arithmetic, all controls and confidence fields are in `stock_sessions_results.json`; the entire trade ledger is in `stock_sessions_trades.csv`. `stock_sessions_provenance.json` records source/plan/runner hashes. Original quotes and publisher HTML remain outside Git. No live bot, website, native platform adapter, payments or hosting was changed.

```bash
python scripts/research_stock_sessions.py --markets /private/all-in-one-hourly --market-cache /private/all-in-one-source-cache --equities /private/pulse-v2-equities --equity-cache /private/pulse-v2-equity-cache
python -m pytest -q scripts/tests/test_stock_sessions_research.py
```
