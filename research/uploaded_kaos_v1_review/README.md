# Review of uploaded KAOS Strategy v1

**Conclusion: useful research structure, but the supplied package is not a proven profitable replacement and its headline study contains reproducible errors.** Its own bundled ledger is negative after its small modeled cost, before considering the additional defects below. No platform/live adapter was executed or installed. The original ZIP and extracted source remain outside Git; only an audit, small correction patch, numerical regression demonstrations and an independent diagnostic are committed.

Archive SHA256: `d312e80efb1c7eaf36c11c9a6bce4cd7fc326902db339aaec918e831d7020f6c`.

## What the strategy does

PULSE fades range-market price stretches using Kaufman efficiency ratio, EMA20/50 context, RSI14 and Bollinger20/2. The default target is three ATR and the stop five ATR, with a 24-candle maximum hold. DRIVE is an optional trend-pullback engine and is disabled by default. These are deterministic rules, not a trained AI model. Expressing parameters in candles/ATR does not establish profitability or execution compatibility on every asset, venue or timeframe.

## Bundled evidence

The included 1,564-trade ledger recomputes to net **-23.32 ATR**, profit factor **0.990**, **621** target exits, **318** stop exits and **625** time exits. The 66.13% figure is 621/(621+318), excluding all time exits. Only **56.52%** of all trades have positive net P&L under the bundled0.02ATR/side assumption. These are arithmetic checks of supplied rows, not confirmation of market data or an independent OOS result.

The wider stop and smaller target mechanically favor a higher target-hit rate. The 62.5% theoretical barrier parity is an idealized no-drift first-passage comparison, not a calibrated real-market win probability; expiry, gaps, costs and time-exit P&L also matter. The package itself acknowledges negative pooled expectancy at retail-like costs.

## Reproduced and inspected defects

| Finding | Evidence | Consequence |
|---|---|---|
| Misaligned ATR in headline test studies | `study.pulse_entries()` returns slice-relative indices, but `portability.run_pair()`, `study.evaluate_pair()`/`placebo()`, report collection, cost sensitivity and refinement pass full-history ATR into a sliced price frame. | A test trade at local index0 uses training-history ATR0 rather than ATR at the test offset. Brackets and normalized profits are wrong. Basic `backtest.run()` is not affected in the same way because it recomputes indicators on its slice. |
| Confidence interval encodes losses as wins | `bootstrap_wr()` concatenates selected ones from both the win and loss indicator arrays. A synthetic50/50 sample returns `[1.0,1.0]`. | Reported intervals cannot establish confidence. Correct encoding produces a non-degenerate interval around50%; independent-trade bootstrapping still ignores correlated dates/markets. |
| USDJPY classified as equity | `study.asset_class()` recognizes FX only by a USD suffix. All four USDJPY timeframe rows are labeled `equity`. | Asset-class totals, FX/equity claims and plots are distorted. Relabeling alone does not repair the ATR problem. |
| Wrong TradingView short PULSE bracket | The short-entry block selects geometry using `pulseLong`, which is false on a PULSE short. | Default short PULSE orders use DRIVE1.6ATR target/1ATR stop instead of the advertised3/5 geometry. Signal-close anchored Pine exits also differ from actual-entry anchored Python brackets. |
| Python paper runner default Coinbase product is wrong | `live_runner.fetch()` sends default `BTCUSD` directly to `/products/`, while the provider expects `BTC-USD`. | The documented default live feed fails. The registry mapping is already available but unused here. |
| Paper/research execution differs | Runner uses a completed historical close as entry, omits costs and gap-open stop fills, stores all symbols/timeframes in one shared state file and does not persist its last processed timestamp. | Its paper totals do not reproduce next-open/costed backtests; restarts and multiple instruments can corrupt interpretation. |
| Optional dual-engine positions can overlap | `backtest.run(mode=both)` simulates PULSE and DRIVE independently before concatenation. | A one-position-per-instrument claim does not hold in that optional mode. The default PULSE-only headline is not affected by this specific issue. |
| Data and platform equivalence unverified | Resampling keeps partial four-hour groups, live intent has no timestamp-based closed/stale-bar validation, native ATR/RSI initialization differs from pandas EWM, and the native adapters were not compiled here. | Bar-counted portability is not proof of matching signals/fills across platforms. |
| MT5 risk/lifecycle issues | EA contains actual `trade.Buy`/`trade.Sell` calls; minimum-lot clamping can raise size above its calculated risk budget, and entry-bar state is not restored after restart. | Real-order capability exists in that adapter, while risk limits and expiry recovery require separate native testing. It was never run in this review. |

## Limited corrective patch

`limited_review_fixes.patch` fixes ATR slicing and adds a length guard, corrects bootstrap loss encoding, uses registry-based asset classification, corrects the Pine short ternaries, and maps the documented Coinbase symbol. `patch_manifest.json` identifies eight changed files and their before/after hashes.

The patch applies cleanly to the uploaded package (`git apply --check` passed). Patched Python files compile. Three offline source smoke checks passed for50/50 CI behavior, rejection of mismatched ATR lengths and USDJPY-as-FX classification. Four repository audit regression tests also passed. No network or order adapter was executed by these checks.

**This is a limited patch, not a completed production repair.** Pine/MT5 compilation, platform parity, partial/resampled candles, realistic broker fills/costs, mixed-engine position arbitration, restart-safe paper state and risk-size enforcement remain unresolved. Old `out/` results must be regenerated after correction; applying the patch does not make those results valid.

## Independent corrected diagnostic

A bounded plan was committed as `f3e260b` before this replay. It tests the exact uploaded default PULSE rule on reused Binance BTC/ETH/SOL one-minute history aggregated to complete five-minute candles, January–October2026. This is a diagnostic on extensively reused data, not a fresh OOS test or a reproduction of the missing original42-market snapshots.

ATR and prices retain the same original index. Each segment warms up60 closed candles. Entries occur at the next requested-candle open, stop-first ordering is preserved, favorable target gaps are capped at the target, incomplete holding horizons are excluded, and no trade crosses a data gap. Hypothetical long/short mode has no borrow/funding model; long-only mode is the applicable spot comparison. Price-cost stress doubles fees/slippage only, without an entry-delay claim.

| Mode | Trades | Target/stop win rate | Net at0.02ATR/side | PF at0.02ATR/side | Net with10bps fee+2bps slip/side | PF with price costs |
|---|---:|---:|---:|---:|---:|---:|
| hypothetical_long_and_short | 3386 | 67.36% | -119.62ATR | 0.973 | -5951.28ATR | 0.235 |
| long_only_spot | 1919 | 67.13% | -3.60ATR | 0.999 | -3293.58ATR | 0.241 |

The high target/stop win rate persists while expectancy is negative. It does not justify choosing this as a profitable bot or claiming the same win rate for Pocket Option. ATR-normalized sums are not compounded account returns or dollar profits. The uploaded `binary_option_intent()` only maps direction to CALL/PUT; no supporting fixed-expiry binary backtest is supplied. Five-second performance is also untested.

## Reproduction limits and commands

The ZIP claims64 cached source CSV series, but contains **zero** cached candle CSVs. It includes results and trade ledgers, not the original price snapshots. Downloading current provider history would not recreate those snapshots. Therefore the corrected original42-pair claim cannot be fully reproduced from this ZIP. The source/plan hashes and full independent diagnostic trade ledger are supplied in this review directory.

```bash
python scripts/review_uploaded_kaos_v1.py --package /private/extracted/research/kaos_strategy --minutes /private/existing-minute-data
python -m pytest -q scripts/tests/test_uploaded_kaos_v1_review.py
```

The runner executes only the two reviewed, SHA256-pinned pure calculation files. It never imports data fetchers or native/live adapters. Any change to those calculation files requires a new review and hash. The original package is preserved and no production strategy, extension, homepage, hosting, payments or real trading settings changed.
