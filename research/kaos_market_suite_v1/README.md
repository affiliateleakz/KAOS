# KAOS Market Strategy Suite v1

Five implemented, separate market profiles share input validation, state checks and conservative sizing. They emit **research/paper intents only**. Every profile has `executionEnabled:false` and `productionApproved:false`. None is an established dependable profitable model, and no website, extension, native adapter, hosting, payments or real-order setting has changed.

## Profiles

| Market | Strategy | Chart | Entry | Exits / contract |
|---|---|---|---|---|
| Stocks/ETFs | **KAOS Stocks Pullback** | Daily | Close above SMA200 and Wilder RSI2 below10; next regular-session open | Two-ATR initial stop; next-open exit after close above mean5 or five daily bars held |
| Forex | **KAOS Forex London Breakout** | Hourly | Complete00:00–07:00London box; first08:00–11:00closed breakout with EMA20/50 direction and0.1ATR buffer; mirrored long/short | Opposite box-side stop plus0.1ATR buffer, target2R, flat at16:00London |
| Crypto spot | **KAOS Crypto Swing Breakout** | Four-hour | Prior20-bar-high breakout, EMA50 above EMA200, close above EMA200; next observed open | Three-ATR initial stop, at least1%initial price risk; nonretroactive highest-close20/3ATR trail, EMA50/prior10low exit, max7days |
| Binary options | **KAOS Binary Trend Pullback** | One-minute | EMA20/50 trend and EMA50slope, confirmed pullback/reclaim and prior high/low break, directional RSI14 band | Fixed five-minute expiry from observed entry; CALL/PUT; quoted payout at least80%; no stop/target substitution or martingale |
| Stock options | **KAOS Options Call Spread** | Daily underlying + contract quotes | Bullish stock pullback plus EMA50 above EMA200; fresh liquid same-expiry calls30–60DTE | Long near-ATM call, short higher-strike call; modeled debit risk; exit at50%maxprofit,50%debit loss, underlyingEMA50break or21DTE |

All formulas are deterministic rules. These are not trained AI models. Timeframes and contract types are validated independently: a cash-stock chart, spot FX quote and fixed-expiry binary contract cannot silently share the wrong strategy. Source rules were frozen in `plan.json` before suite evaluation, at commit `c49c2bc`.

### Stock profile

The stock profile carries forward the existing daily RSI2 bull-pullback rule, without retuning it after outcomes. It requires200completed daily bars. Entry references the next regular-session quote rather than the signal day's close. Runtime validates New York regular-session daily candles and explicit prior/next session context. Protective stop quotes can trigger without waiting for indicator warmup; after-hours exits are scheduled for the next regular open. Daily signal exits wait for the next session rather than inventing a fill at a just-observed close.

Initial supported stock/ETF research symbols: SPY, QQQ, IWM, DIA, AAPL, MSFT, NVDA, TSLA. Earnings avoidance and a native brokerage connection are not implemented; overnight gaps can exceed planned stop risk.

### Forex profile

Seven complete hourly bars define the local pre-London box. Daylight-saving changes use `Europe/London`, not a hardcoded UTC offset. A complete close above/below the box plus0.1ATR must agree with EMA20/50. An earlier eligible signal cannot be reissued on a later hourly bar. The input state must also confirm no trade has already occurred on that London date. Target distance must cover at least five times the modeled base two-basis-point roundtrip execution cost.

Initial pairs: EUR/USD, GBP/USD, USD/JPY and AUD/USD. `EURUSD=X`-style aliases are normalized, including quote instrument checks. Stops/targets use actual observed entry reference. Missing required box/execution quotes mean no test trade, not fabricated prices. Unscheduled hourly gaps reset history; legitimate weekend closures are handled separately.

### Crypto profile

This reuses the earlier frozen four-hour breakout, including its indicator initialization and filters. It does not reinterpret the weak PULSE revision as a crypto winner. Initial research symbols: BTC, ETH, SOL, BNB, XRP, ADA, DOGE, LTC, LINK and AVAX against USDT. This does not imply all products are offered by every exchange; live broker capabilities need a separate adapter.

Trailing stops apply only after a requested candle closes. The router never retroactively applies a newly raised stop to an already completed candle's low. Existing positions are identified by profile and symbol, and duplicate entry/exit/stop-update intents have stable identifiers.

### Binary profile

CALL requires EMA20>EMA50 and EMA50 above its five-bar lag, a prior low touching EMA20, a green close above EMA20 and the previous high, and RSI14 in45–65. PUT mirrors direction/slope/body, with RSI in35–55. Sixty completed one-minute candles warm the entry. Runtime requires an explicitly identified Pocket Option fixed-expiry quote, a fresh observed price, and a known payout of80–100%. It holds on lower or unverified payouts.

Expiry is300seconds after the observed entry, not after the signal candle. The underlying bracket win rate from the uploaded strategy is not used. Existing contracts await authoritative settlement; a late current quote is not silently substituted for the broker's accepted expiry price. Stake sizing uses account-currency risk metadata and skips a broker minimum stake that would exceed the budget.

### Options profile and current data block

The underlying must satisfy the stock entry and EMA50>EMA200. Entry is15–60minutes after a verified regular-session open. Each call requires a fresh timestamp, explicit contract multiplier, positive bid/ask, open interest at least100 and bid/ask width at most20%of midpoint. Long call delta is0.45–0.60; the higher-strike short call delta0.20–0.35. Expiry must match and fall30–60calendar days out; selection prioritizes nearest45DTE, near-ATM long strike and short delta closest0.30.

Debit uses **long ask minus short bid**, never assumed midpoint fills. The modeled max-profit/risk ratio must be at least1, including an illustrative$0.65per contract/leg entry-and-exit commission reserve. The quantity remains unspecified until broker/account sizing metadata exists. This requires an atomic complex-spread order; two independent leg fills are not assumed guaranteed. Early assignment, exercise, exercise fees, partial fills, spreads and actual broker commissions need separate validation.

Existing spreads are marked for possible exit using long bid minus short ask and the supplied actual entry ledger; quotes must remain fresh and match both contracts. These are modeled quote-based exit intents, not accepted execution claims.

**No historical option-chain/Greek/assignment data is available here. No historical options P&L, win rate or profitability is claimed.** Missing/invalid current chains produce HOLD. Synthetic examples verify software arithmetic only.

## Shared risk and state controls

- Planned risk budget is0.5%of account equity per trade, with1%aggregate planned risk and1x gross-notional caps.
- `size_contracts()` requires explicit broker-provided risk per contract and notional per contract **in account currency**, minimum volume, volume step, existing risk and existing gross exposure. It floors quantity and skips below-minimum quantities. It never guesses forex lots, JPY conversion or option multipliers from a symbol.
- Entry quotes must be fresh within30seconds, or5seconds for binary. Entry signals expire after2minutes, or10seconds for binary. Stocks additionally require the next regular-session window.
- Input must identify market, symbol, timeframe, contract type, quote instrument, closed chronological OHLC, position/pending-order state and already consumed intent IDs. Unknown or inconsistent inputs hold or raise validation errors with no execution.
- Position management cannot cross profile/symbol ledgers. A caller must persist consumed intent IDs, actual positions, last processed decision, forex daily-entry state, fills and aggregate account exposure. This pure evaluator is not an execution daemon or a substitute for broker-side protective orders.

The quantity field on actionable intents remains `null` until a broker adapter performs verified account-currency sizing. Fees, adverse gaps, disconnected feeds and assignment can cause losses beyond planned stop risk. Cash-equity quantities, forex base units/lots, crypto units, binary stake and option contracts are different units. No martingale, leverage inference or live credential/order API exists in this package.

## CLI and labeled examples

Python3.11was used. The runtime needs numpy, pandas and timezone data; tests additionally need pytest. Use a repository checkout or the supplied research ZIP:

```bash
python -m pip install -r requirements.txt
python scripts/evaluate_market_strategy.py --list
python scripts/evaluate_market_strategy.py --input research/kaos_market_suite_v1/examples/stocks.json --replay
```

When running from the repository, the requirements files are in `research/kaos_market_suite_v1/`. The research ZIP also places them at its top level for convenience.

Five example JSON files demonstrate the schemas. **Every example contains synthetic software fixtures, not real historical market data or trading results.** They use fake prices/contracts and cannot serve as forward evidence. `--replay` labels archived/example evaluation as `historical_replay`; the default CLI uses the actual current system clock and will HOLD on stale example quotes. Every output remains ineligible for performance claims. No data feed, automated schedule, hosting deployment or real-money broker integration is installed by these commands.

For real paper evaluation, supply your verified feed's completed requested-timeframe bars, actual session/calendar/position state and fresh instrument-matched quote. The optional option chain has its own contract quote fields. `catalog.json`, `plan.json`, the examples and source functions document the profile-specific schema.

## Historical checks

These are **one fixed profile per market**, not another parameter grid or a search for the best-looking year. Prices and market regimes have been extensively reused in earlier research. The choice of familiar rules follows many prior trials, so even a positive confidence interval does not erase selection bias or prove prospective skill. All profiles retain production approval=false.

### Stocks

The old clean daily ETF snapshots cover2006–2024, with reported gross dividends. New direct daily snapshots cover2025–October2026for all eight current stocks/ETFs, replacing incomplete-hour aggregation before outcomes, as disclosed in `daily_snapshot_plan.json` at commit `5288ca6`. The collector aborts on in-window split events and invalid daily rows for the new snapshots. Current data has459valid daily bars per symbol.

Replays use the existing cash-reconciled daily engine,0.5%risk and1x entry notional cap per separately funded$10,000instrument sleeve, with no capital transfer among sleeves. Stock costs assume zero commission plus1bp adverse fill each side; stress doubles adverse fill. Fractional quantities are allowed. Historical broker commissions, taxes or fills may materially worsen small results. Dividends are credited when entitled. Intraday daily-stop timestamps are approximations, not observed exact fills. Daily drawdown misses intraday/overnight path extremes.

| Stock sample | Trades | Net sleeve-basket return | Doubled-cost return | Daily drawdown | Buy-and-hold return | Weekly bootstrap interval |
|---|---:|---:|---:|---:|---:|---|
| etf_2018_2020 | 104 | -1.52% | -1.59% | 2.51% | 52.65% | -4.61% to 1.58% |
| etf_2021_2024 | 149 | 3.05% | 2.79% | 0.82% | 48.03% | 0.03% to 6.32% |
| eight_stocks_2026 | 78 | 0.60% | 0.57% | 0.27% | 9.40% | -0.48% to 1.63% |

Passive exposure is substantially higher than the active rule. Returns/drawdowns are not proof of alpha or matched risk. The earlier2018–2020period loses money and the recent interval crosses zero. A small positive2021–2024interval does not override the prior strategy search or historical data reuse.

### Forex and crypto

Forex uses four indicative Yahoo hourly pairs, one entry per London date,1bp adverse fill each side. Combined stress doubles that cost and delays entry one observed hour. No position is carried past the observed16:00London quote; missing execution/flatten hours exclude the trade. These are normalized price-risk units, not a leveraged dollar account.

| Forex period | Trades | Net R | PF | Combined-stress net R |
|---|---:|---:|---:|---:|
| 2025 | 346 | 11.39 | 1.104 | -20.49 |
| 2026 | 271 | 3.23 | 1.036 | -15.17 |

Crypto2021–2024six-asset replay: **319trades**, **57.46R**, PF**1.463**; doubled-cost/one-hour-delay stress**42.20R**. The adjusted weekly lower bound is-0.446R, still below zero. Base costs are10bpsfee+2bpsslippage per side; stress20+4. Source data gaps and full-holding-horizon restrictions can bias the observed sample.

The R sums use independently normalized trades across assets, without a shared-capital portfolio or compounding claim. Actual broker liquidity, fees, quoted spreads and supported products can differ. Prior swing, backfill and transfer reports retain their failures and per-market losses; no market is removed here. No previously reserved2025BNB/XRP/ADAperiod is opened.

### Binary options

Recorded Pocket Option five-second candles before2026-10-05T18:10:50Z support completed one-minute entries and exactly observed five-minute settlements. There is no gap-crossing or per-asset overlap. Ties assume refunded stakes; actual payout/tie rules are unverified. Stress combines five-second delayed entry and a one-basis-point adverse quote.

Base sample: 373trades, 194wins, 177losses, 2ties, decided win rate**52.29%**. At80%payout, break-even is55.56%; net result**-21.80unit stakes** and combined-stress net**-43.60units**. Only4active dates are represented.

| Assumed payout | Net unit stakes |
|---|---:|
| 70% | -41.20 |
| 80% | -21.80 |
| 90% | -2.40 |
| 92% | 1.48 |

The tiny positive92%scenario is not used to change the frozen80%minimum or declare an edge. The confidence bound and stress results remain limiting. Operational quotes below80%payout produce HOLD; the70%row is sensitivity analysis only. No reserved later Pocket Option data was scored.

### Options

No historical option P&L was generated. Tests use explicitly synthetic chains to verify ask-minus-bid entry debit, bid-minus-ask liquidation credit, common expiry/multiplier, stale/illiquid quote rejection, modeled risk/commission reserve and exit conditions. Underlying stock gains cannot establish option-spread profitability.

## Evidence and reproducibility

Nineteen targeted tests passed for typed market routing, quantity/risk caps, minimum-lot skips, closed/fresh inputs, daily session timing, profile-position identity, London DST, first-signal-only behavior, binary direction/expiry/payout, fixed crypto rule parity, option-chain pricing/exit gates and CLI replay labeling. Five labeled synthetic examples also produced their expected paper intents, with execution disabled. Software checks are not financial performance validation.

`provenance.json` records implementation/plan/source hashes. `stocks_results.json`, `forex_results.json`, `crypto_results.json`, `binary_results.json`, `options_status.json` and the ledgers expose actual results. Raw public price snapshots and the private user archive remain outside Git and the download.

Historical reproduction requires a full repository checkout, scipy/httpx in addition to the runtime dependencies, and the referenced verified source snapshots:

```bash
python scripts/backtest_market_strategy_suite.py --daily /private/daily-edge-data --recent-daily /private/market-suite-daily --hourly /private/kaos-swing-hourly --fx /private/all-in-one-hourly --po /private/KAOS-export.zip
python -m pytest -q scripts/tests/test_market_strategy_suite.py
```

No profile is installed into the production extension/website or enabled for live orders. Broker execution, account sizing conversions, persistent state, server-side protection and any future deployment require their own concrete integration and review. No PR was merged.
