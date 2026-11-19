# KAOS PULSE v2 — experimental revision and cross-market comparison

**The implementation improves entry confirmation, cost checks and risk-input handling. The entry revision did not establish a profitable cross-market strategy. It is isolated research/paper code, with execution disabled, and does not replace the live KAOS Strategy.**

The original plan was committed at `12f2afd`. The user then explicitly added stocks, forex and binary options; the pre-evaluation scope amendment was committed at `8e807ff`. The two documents disclose all candidates, costs, calendar treatment, warmups and decision gates. No tuning followed the results.

## What changed

The original uploaded PULSE enters a price stretch outside the Bollinger band. V2 waits for a completed reversal back inside the band, with a green body and increasing RSI for longs; shorts mirror the conditions only where explicitly tested. The preceding stretch must meet the original ER/range, RSI, EMA-distance and knife-guard conditions. An optional EMA200 trend guard is tested rather than assumed beneficial.

Stops are two ATR and targets three or four ATR. The maximum hold remains twenty-four requested candles. The cost guard rejects a bracket whose gross target is less than five times the assumed roundtrip fee/slippage fraction. Higher-cost stress uses the same base eligibility threshold, so it cannot improve performance by silently screening away additional trades.

ATR and RSI use explicit Wilder seeds. Flat RSI is50, an entirely rising window is100, and entirely falling is0. Both price and indicator arrays retain consistent indices. Unguarded entries need60closedbars (EMA50is their longest required average), guarded entries250(EMA200). Gaps reset indicator history. No martingale, trained-model claim, win-rate target or unverified broker order is involved.

`strategy.py` also provides `risk_quantity()`, which rounds **down**, caps funded notional and includes modeled stop-execution costs in planned risk. It returns zero when a minimum executable size would exceed that budget. The result is shares/base-unit quantity, **not MetaTrader lots**; broker contract multipliers and portfolio-wide exposure need a separate adapter. Gaps can still cause losses larger than planned risk.

`paper_intent()` validates supported crypto research symbols, finite/aligned/continuous closed candles, fresh observed quotes and signal timing. Brackets anchor to current observed ask rather than a stale signal close. Every result has `researchOnly:true`, `executionEnabled:false`, and `validatedProfitable:false`. This helper is currently a crypto quote interface; the stock/session, forex and binary paths are research replays, not installed broker adapters. It is separate from the earlier four-hour breakout paper journal and must not be mixed with that model's evidence.

## Market-specific testing

- **Crypto:** BTC, ETH, SOL, BNB, XRP and ADA spot, public checksum-verified hourly snapshots. Validation2021–2024. Only a configuration passing the frozen selection criteria could open2025BNB/XRP/ADAconfirmation. No candidate qualified, so that period remains unscored.
- **Stocks:** SPY, QQQ, IWM and DIA ETFs plus AAPL, MSFT, NVDA and TSLA individual stocks, indicative Yahoo hourly regular-session data. January–October2026 descriptive evaluation with2025context; all underlying market regimes are familiar retrospective data. Longs only, no short-borrow assumption. Gross dividends are credited when held before ex-date; no taxes. No in-window split series is silently traded without an adjustment audit.
- **Forex:** EUR/USD, GBP/USD, USD/JPY and AUD/USD indicative Yahoo hourly quotes, mirrored long/short entries. January–October2026 descriptive evaluation with2025context. Correct registry classes are used. These are not executable bid/ask quotes from a chosen broker and do not include its verified swaps or financing tiers.
- **Binary options:** actual user-supplied Pocket Option five-second OHLC archive, physically truncated before2026-10-05T18:10:50Z. The already-seen earlier history supports thirty-second and one-minute entry candles, with expiries of one or three candles. Different target/stop geometries are not duplicated as binary configurations because those exits do not exist in the fixed-expiry contract. The spot profit-target cost guard is inapplicable to binary payouts and is not used. No reserved later Pocket Option quotes or real trades are consumed.

## Fills, calendars and costs

All decisions use completed requested candles. Price-based entries use the next observed base-hour open, stop gaps fill at the adverse open, targets receive no favorable gap improvement, and ambiguous intrabar stop/target touches resolve to the stop. Stop/target levels use the decision ATR anchored to observed entry. No same-hour re-entry, per-asset overlap, gap crossing or split-crossing holding horizon is allowed. The full horizon must be observable before a trade is scored. OHLC fills cannot verify actual tick paths or broker acceptance.

Stock bars follow the supplied exchange sessions, including the final shorter hourly bar. Session-based four-hour groups include a final shorter closing group (normally2.5h); these are labeled session groups, not identical calendar four-hour durations. Forex allows legitimate Friday-to-Sunday/Monday weekend closures, not arbitrary multi-day midweek gaps. Crypto requires continuous UTC hours. Missing/partial groups are excluded; missing whole stock sessions cannot be conclusively audited from normalized quote tags alone.

The price-based maximum hold expires at the close of the twenty-fourth subsequent requested candle. During entry-delay stress the signal's expiry is unchanged, so the delay consumes part of the available hold. Stock/forex expiries count observed trading candles rather than assuming twenty-four calendar hours. Partial-session candles count as one requested candle. Approximate exit timestamps use the base-bar end for holding/dividend accounting; exact intrahour fill times are unknown.

| Class | Base fee per side | Base adverse fill per side | Holding/dividends | Combined stress |
|---|---:|---:|---|---|
| Crypto | 10bps | 2bps | No funding for long-only spot | 20bpsfee+4bpsfill and one observed-hour delay |
| Stocks | 0 illustrative commission | 1bp | Gross reported cash dividends | 2bpsfill and one observed-base-bar delay; commission remains zero |
| Forex | 0 separate commission | 1bp assumed spread/slippage | 2bps/notional/calendar day illustrative carry | 2bpsfill,4bps/daycarry,one observed-base-bar delay |

Real broker commissions, spreads, FX swaps, taxes and fill quality can differ or erase a small gain. Session/weekend delays can exceed one calendar hour. Normalized R divides each trade's net price-unit profit by its original stop distance; mean netbps divides by observed entry. These are independent trade statistics, **not** compound portfolio returns, funded-account equity or USD income. Inverse FX quotes need conversion before making actual dollar-account claims.

Binary entry is next observed five-second open with exact observed fixed-expiry settlement. Ties refund stakes. Payout assumptions70/80/90/92% are all disclosed. Combined binary stress delays entry five seconds and worsens entry one basis point; expiry moves with that delayed entry. The original bracket win rate is never reused as a binary win rate. Actual accepted quotes, payout availability and broker tie rules remain unverified.

## Selection and verification

Eight price configurations across three classes yield24class/config comparisons; eight unique binary configurations are separate. Two corrected original-entry controls (plain and with its own cost filter) are shown for every price timeframe. Original-entry binary controls use the same fixed expiries. Gate requirements and the24-way validation adjustment are in the pre-evaluation documents. Only crypto had a reserved confirmation decision; other classes are descriptive and no post-hoc class winner is promoted.

Five thousand cluster bootstrap resamples use price-week seed219 and binary-day seed5519. Weekly clusters apply to price-based R; daily clusters apply to binary unit payouts. Correlated assets, serial dependence, many previous research trials, fixed surviving universes and extensive historical-data reuse prevent pristine independent performance claims. Sparse/zero samples mean insufficient evidence, not profitable abstention. `coverage.json` shows source segments, requested history bars and readiness for both warmups by class and asset.

Sixteen offline tests passed for indicator causality/seeding, actual reversal confirmation, explicit short eligibility, fee budgets, minimum-size skips, planned risk/notional caps, quote/time controls, stop-first ambiguity, target-gap caps, dividend eligibility, exchange-session shorter groups, legitimate FX weekends, split purging and separate binary expiry/stress. Replay mechanics passing does not prove predictive skill. No native Pine/MT5 adapter was compiled or executed and no production files were modified.

## Reproduce

Requires numpy, pandas, scipy and httpx. The original reviewed ZIP calculation files remain private and are SHA-pinned by the audit loader. Raw market data and personal archive remain outside Git.

```bash
python scripts/collect_pulse_equities.py --out /private/pulse-equities --cache /private/equity-cache
python scripts/research_pulse_v2.py --package /private/extracted/research/kaos_strategy --crypto /private/kaos-swing-hourly --markets /private/all-in-one-hourly --equities /private/pulse-equities --po /private/KAOS-export.zip
python -m pytest -q scripts/tests/test_pulse_v2.py
```

`provenance.json` contains all snapshot and implementation hashes. `price_results.json`, `baselines.json`, `binary_results.json`, `coverage.json`, `selection.json`, `confirmation.json` and `paper_release.json` expose full results and release state. No successful profitability or live-deployment state is inferred merely from a BUY research intent.

## Results

Completed24price-class/config comparisons plus8uniquebinaryconfigurations. Primarycrypto selection: **none**. Confirmation evaluated: **False**; finalqualified: **False**. There is no qualified production release.


### crypto

| TF | EMA200 guard | Target ATR | Trades | Net R | PF | Mean net bps/trade | Combined-stress R | Gate |
|---|---|---:|---:|---:|---:|---:|---:|---|
| 1h | 0 | 3 | 1102 | -174.28 | 0.734 | -31.304 | -275.11 | False |
| 1h | 0 | 4 | 1131 | -164.02 | 0.766 | -24.811 | -271.95 | False |
| 1h | 1 | 3 | 553 | -85.70 | 0.739 | -30.416 | -138.42 | False |
| 1h | 1 | 4 | 564 | -84.90 | 0.757 | -25.734 | -137.45 | False |
| 4h | 0 | 3 | 223 | -33.82 | 0.740 | -37.000 | -40.94 | False |
| 4h | 0 | 4 | 223 | -31.85 | 0.759 | -44.719 | -34.65 | False |
| 4h | 1 | 3 | 75 | -12.63 | 0.717 | -63.560 | -14.51 | False |
| 4h | 1 | 4 | 75 | -10.01 | 0.776 | -52.205 | -11.53 | False |

Both corrected original controls:

| TF | Baseline | Trades | Net R | PF | Mean net bps/trade |
|---|---|---:|---:|---:|---:|
| 1h | corrected_original | 1742 | -146.28 | 0.709 | -30.478 |
| 1h | cost_filtered_original | 1650 | -119.83 | 0.739 | -29.567 |
| 4h | corrected_original | 362 | -31.96 | 0.692 | -73.827 |
| 4h | cost_filtered_original | 362 | -31.96 | 0.692 | -73.827 |

### stocks

| TF | EMA200 guard | Target ATR | Trades | Net R | PF | Mean net bps/trade | Combined-stress R | Gate |
|---|---|---:|---:|---:|---:|---:|---:|---|
| 1h | 0 | 3 | 34 | 3.98 | 1.208 | 2.213 | 1.83 | False |
| 1h | 0 | 4 | 34 | 4.64 | 1.225 | 14.666 | 5.72 | False |
| 1h | 1 | 3 | 20 | -2.58 | 0.807 | -38.592 | -5.08 | False |
| 1h | 1 | 4 | 20 | 0.11 | 1.008 | -22.032 | -4.14 | False |
| 4h | 0 | 3 | 10 | 4.02 | 1.998 | 117.953 | 1.37 | False |
| 4h | 0 | 4 | 10 | 3.72 | 1.736 | 161.443 | 1.39 | False |
| 4h | 1 | 3 | 3 | -0.54 | 0.732 | -106.157 | -3.23 | False |
| 4h | 1 | 4 | 3 | -3.04 | 0.000 | -186.130 | -3.23 | False |

Both corrected original controls:

| TF | Baseline | Trades | Net R | PF | Mean net bps/trade |
|---|---|---:|---:|---:|---:|
| 1h | corrected_original | 64 | 2.12 | 1.121 | 2.065 |
| 1h | cost_filtered_original | 64 | 2.12 | 1.121 | 2.065 |
| 4h | corrected_original | 18 | 2.84 | 1.772 | 75.064 |
| 4h | cost_filtered_original | 18 | 2.84 | 1.772 | 75.064 |

### forex

| TF | EMA200 guard | Target ATR | Trades | Net R | PF | Mean net bps/trade | Combined-stress R | Gate |
|---|---|---:|---:|---:|---:|---:|---:|---|
| 1h | 0 | 3 | 139 | -48.55 | 0.531 | -7.992 | -61.03 | False |
| 1h | 0 | 4 | 136 | -48.17 | 0.537 | -7.991 | -60.71 | False |
| 1h | 1 | 3 | 74 | -34.42 | 0.425 | -10.481 | -42.00 | False |
| 1h | 1 | 4 | 74 | -35.41 | 0.424 | -10.546 | -42.75 | False |
| 4h | 0 | 3 | 31 | -6.97 | 0.645 | -10.657 | -8.97 | False |
| 4h | 0 | 4 | 30 | -3.67 | 0.801 | -5.211 | -5.53 | False |
| 4h | 1 | 3 | 7 | -2.27 | 0.432 | -21.464 | -1.38 | False |
| 4h | 1 | 4 | 7 | -1.78 | 0.556 | -16.275 | -0.41 | False |

Both corrected original controls:

| TF | Baseline | Trades | Net R | PF | Mean net bps/trade |
|---|---|---:|---:|---:|---:|
| 1h | corrected_original | 254 | -23.19 | 0.691 | -3.358 |
| 1h | cost_filtered_original | 254 | -23.19 | 0.691 | -3.358 |
| 4h | corrected_original | 50 | -10.13 | 0.503 | -12.916 |
| 4h | cost_filtered_original | 50 | -10.13 | 0.503 | -12.916 |

### Fixed-expiry Pocket Option history

These outcomes use observedfive-secondentry/settlementopens, not target/stop exits. Payouts are assumptions, tiesrefund. None of the reserved later quotes were scored.

| Candle | Trend guard | Expiry candles | Trades | Decided WR | Net70 | Net80 | Net90 | Net92 | Combined-stress net80 | Gate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 30s | 0 | 1 | 165 | 48.77% | -27.70 | -19.80 | -11.90 | -10.32 | -44.40 | False |
| 30s | 0 | 3 | 161 | 49.69% | -24.70 | -16.80 | -8.90 | -7.32 | -38.60 | False |
| 30s | 1 | 1 | 85 | 42.35% | -23.80 | -20.20 | -16.60 | -15.88 | -31.00 | False |
| 30s | 1 | 3 | 83 | 45.12% | -19.10 | -15.40 | -11.70 | -10.96 | -25.40 | False |
| 60s | 0 | 1 | 61 | 27.87% | -32.10 | -30.40 | -28.70 | -28.36 | -35.80 | False |
| 60s | 0 | 3 | 57 | 36.84% | -21.30 | -19.20 | -17.10 | -16.68 | -22.80 | False |
| 60s | 1 | 1 | 29 | 24.14% | -17.10 | -16.40 | -15.70 | -15.56 | -21.80 | False |
| 60s | 1 | 3 | 26 | 30.77% | -12.40 | -11.60 | -10.80 | -10.64 | -13.40 | False |

Original-entry binary controls:

| Candle | Expiry candles | Trades | Decided WR | Net80 | Stress net80 |
|---|---:|---:|---:|---:|---:|
| 30s | 1 | 360 | 51.12% | -28.60 | -91.80 |
| 30s | 3 | 266 | 47.74% | -37.40 | -51.80 |
| 60s | 1 | 176 | 45.14% | -32.80 | -41.00 |
| 60s | 3 | 129 | 44.53% | -25.40 | -31.80 |

The first fixed hourly unguarded3ATR-target stock configuration improved PF from1.121 to1.208 and mean netbps/trade from2.065 to2.213, but had only34trades and a negative confidence lower bound. Four-hour stock gains used only10trades or fewer. Those are weak retrospective leads, not proven improvements. Crypto and forex candidates lost after modeled costs; binary revision results were below80%payoutbreakeven and weaker than the original entry. Tighter risk controls do not establish better entry alpha. No losing variant or market was removed.
