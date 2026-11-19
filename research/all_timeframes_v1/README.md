# Uploaded engine: broad timeframe study

This tests the latest supplied Avalisa pure indicator and decision functions. It does not load a third-party extension or send trades. No changes to KAOS trading behavior or the hosted website are part of this study.

## Frozen scope

14 candle durations: 5s, 10s, 15s, 30s, 1m, 2m, 3m, 5m, 10m, 15m, 30m, 1h, 4h, daily. Three source intensity settings and four expiry policies (source adaptive, one candle, two candles, three candles) produce 168 configurations. This covers the listed standard durations, not every mathematically possible duration. All source filters remain unchanged.

The reviewed JavaScript files are evaluated in an offline VM with calculation stubs. They remain private user-supplied inputs; they are not redistributed or incorporated into the KAOS extension. The engine is deterministic indicator/rule logic, not a trained predictive AI. Its confidence value measures rule agreement rather than a measured probability of winning.

## Data and timing

- 2,890,080 one-minute BTCUSDT, ETHUSDT, and SOLUSDT spot candles, January 2025–October 2026, from 66 checksum-verified Binance public monthly archives. These support timeframes of one minute and higher.
- Existing complete five-second public crypto samples and the user's Pocket Option export support the four shorter timeframes. The previously reserved final Pocket Option period remains unscored. The shorter results are descriptive; these samples have been used in earlier research.
- Resampling requires complete UTC-aligned candles. Gaps reset history. Prices are never interpolated or upsampled to imply finer observations.
- Decisions occur only after a requested candle closes. Entry is the next observed base-bar open. Settlement uses the exact expiry's observed open. Overlapping trades in an asset are excluded. Ties refund the stake.
- Minute-resolution data cannot verify the source engine's 30-second expiry. Those signals are counted as unresolved and excluded from performance calculations. No rounding to a convenient expiry.
- Delayed-entry stress moves both entry and expiry forward one source bar: five seconds for the short grid and one minute for the longer grid. This cannot establish five-second latency behavior from minute candles.
- Each asset is simulated independently; the aggregate is not an account equity curve with shared capital constraints.
- Simulated payouts are 70%, 80%, 90%, and 92%, with flat one-unit stakes, no martingale. These are assumptions, not verified broker payouts or available contracts. Net figures are directional-contract research units, not spot portfolio returns. Slippage, actual execution, spreads, fees, and account restrictions are unverified.

## Selection discipline

For the longer grid, development is 2025, validation is January–September 2026, and confirmation is October 2026. Warmup may use past candles; settlement cannot cross split boundaries. These dates' coarser prices have appeared in earlier studies, so chronological confirmation is not pristine unseen evidence.

At most one configuration is selected using validation only, requiring 200 decided trades, 30 active UTC days, a Wilson lower bound above the 90%-payout breakeven rate (52.63%), nominal binomial p < 0.05/168, positive lower daily-cluster bootstrap mean, positive results in at least two assets, and positive delayed-entry results at 90% payout. Binomial calculations assume independence; clustered daily resampling offers an additional check but does not eliminate dependence or selection risk.

Confirmation requires 200 decided trades, 15 active days, a Wilson lower bound above breakeven, positive lower daily-bootstrap mean, two profitable assets, and positive delayed-entry results. No replacement is selected after confirmation. The bootstrap uses 2,000 resamples and fixed seed 55. Sparse or zero-trade modes are insufficient evidence, rather than a demonstrated losing strategy.

See `plan.json`, `matrix.csv`, and `summary.json` for scope, all outcomes, source/archive hashes, and the frozen selection outcome. Public crypto proxy results do not establish an edge on Pocket Option OTC, stocks, forex, or actual binary contracts.

## Reproduce

Run with Python including numpy, scipy, httpx, and Node available:

```bash
python scripts/collect_timeframe_history.py --out /private/minutes --cache /private/source-cache
python scripts/backtest_all_timeframes.py --indicators /private/indicators.js --engine /private/signalEngine.js --minutes /private/minutes
python -m pytest -q scripts/tests/test_all_timeframes.py scripts/tests/test_video_strategy_replay.py scripts/tests/test_uploaded_bundle_replay.py
node scripts/check_uploaded_signal_engine.cjs /private/signalEngine.js
```

The short input directories are the existing collectors' outputs beneath the repository's parent, as named in the runner. The Pocket Option input path must be adapted to the private local attachment. Raw member data and original third-party code are not committed. The source hashes must match the report to reproduce the same study.

## Results

Completed **168 configurations**. Validation-selected configuration: **none met the frozen qualification gate**. No replacement configuration is selected from October results.

The table below always shows **mid intensity with one-candle expiry**, rather than choosing each row’s best-performing setting. Short intervals use the already-seen descriptive pool; minute and higher use chronological validation. It is not a like-for-like comparison across data sources. Net figures use one-unit stakes; zero trades means insufficient evidence.

| Candle duration | Sample | Trades | Win rate | Net at 80% | Net at 90% | Delayed net at 90% |
|---|---|---:|---:|---:|---:|---:|
| 5 seconds | descriptive | 38,670 | 55.56% | 1.00 | 1658.00 | 67.80 |
| 10 seconds | descriptive | 15,002 | 53.92% | -373.60 | 309.20 | 157.30 |
| 15 seconds | descriptive | 8,623 | 52.49% | -419.00 | -21.00 | -111.90 |
| 30 seconds | descriptive | 3,210 | 53.79% | -94.20 | 65.40 | 7.60 |
| 1 minute | validation | 24,983 | 51.25% | -1833.40 | -621.70 | -923.40 |
| 2 minutes | validation | 10,144 | 51.22% | -769.00 | -264.50 | -272.70 |
| 3 minutes | validation | 5,854 | 51.30% | -437.40 | -144.70 | -199.60 |
| 5 minutes | validation | 2,988 | 50.69% | -258.40 | -108.70 | -165.10 |
| 10 minutes | validation | 1,080 | 49.48% | -116.20 | -63.60 | -35.40 |
| 15 minutes | validation | 608 | 51.49% | -44.20 | -13.10 | -27.40 |
| 30 minutes | validation | 236 | 49.58% | -25.40 | -13.70 | -14.60 |
| 1 hour | validation | 55 | 53.70% | -1.80 | 1.10 | -3.70 |
| 4 hours | validation | 0 | — | 0.00 | 0.00 | 0.00 |
| Daily | validation | 0 | — | 0.00 | 0.00 | 0.00 |

### Five-minute detail

Every five-minute configuration below is disclosed. These are exploratory comparisons, not twelve independently validated edges. Only the globally preselected validation candidate, if any, can pass the frozen confirmation gate.

| Intensity | Expiry | Validation trades | Validation win rate | Validation net90 | Confirmation trades | Confirmation win rate | Confirmation net90 | Confirmation delayed net90 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| low | source_adaptive | 5,193 | 50.20% | -202.90 | 986 | 54.12% | 23.30 | -23.70 |
| low | 1_candle | 101,601 | 48.40% | -8038.20 | 13,019 | 47.32% | -1293.90 | -1211.60 |
| low | 2_candles | 63,228 | 48.34% | -5095.20 | 8,094 | 47.74% | -747.60 | -930.80 |
| low | 3_candles | 46,158 | 48.41% | -3672.80 | 5,868 | 46.43% | -686.40 | -719.40 |
| mid | source_adaptive | 2,988 | 49.26% | -181.00 | 362 | 50.57% | -13.60 | -2.60 |
| mid | 1_candle | 2,988 | 50.69% | -108.70 | 362 | 49.44% | -21.80 | -9.30 |
| mid | 2_candles | 2,521 | 51.04% | -75.40 | 304 | 50.99% | -9.40 | -11.40 |
| mid | 3_candles | 2,307 | 51.05% | -69.10 | 285 | 49.65% | -16.10 | -17.90 |
| high | source_adaptive | 135 | 49.25% | -8.60 | 11 | 81.82% | 6.10 | -1.50 |
| high | 1_candle | 135 | 49.25% | -8.60 | 11 | 63.64% | 2.30 | 0.40 |
| high | 2_candles | 125 | 53.66% | 2.40 | 11 | 45.45% | -1.50 | -3.40 |
| high | 3_candles | 122 | 49.18% | -8.00 | 11 | 27.27% | -5.30 | -5.30 |

The full matrix includes development, validation, and confirmation figures, every intensity/expiry combination, missing-resolution counts, and all payout scenarios. No profitable guarantee, broker execution claim, or live approval follows from this study.
