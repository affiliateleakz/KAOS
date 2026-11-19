# Supplied Avalisa rule engine — static review and reserved replay

**Finding: the missing deterministic decision engine is now available, but no tested mode passed the declared proxy proof gate. No code was integrated into KAOS and no live orders were placed.**

## What the engine actually does

It is a hand-coded rule system, not a trained predictive model or LLM. The `confidence` field is `round(rulesMatched/4*100)`: 2/4=50%,3/4=75%,4/4=100%. This is agreement strength, **not calibrated probability of a winning trade**.

It uses a SMA-slope/standard-deviation regime classifier. Trending rules score trend direction, proximity to SMA20, RSI40–60, and confirming candle color. Ranging rules score RSI30/70 extremes, a2σ band break, five-bar momentum, and candle color. Conflicting equal-strength sides are skipped. High volatility (stdev/price>0.0025) vetoes entries.

Low/Mid/High require2/3/4 agreeing rules respectively. Despite comments describing a single dial, the implemented mode also changes expiry and warmup:

| Mode | Minimum buffered candles | Normal expiry | Quiet expiry (stdev/price<0.0005) |
|---|---:|---|---|
| Low |12|30s|60s|
| Mid |16|60s|180s|
| High |20|180s|300s|

Analysis candles are30seconds; buffer maximum50. The helper uses rolling simple-average RSI rather than Wilder smoothing, and dynamic shorter windows during initial warmup. Price/SMA/volatility rounding is preserved by calling the actual supplied indicator helper, not a Python approximation.

`state.js` defaults to **martingale mode, alternating direction, infinite steps**; it does not automatically activate the rule engine. Only explicit `strategy: ai` uses these indicator decisions. Martingale is sizing, not evidence of predictive edge, and is disabled in this replay.

## Replay design

Only the reviewed pure `indicators.js` and `signalEngine.js` were evaluated in a local JavaScript context without browser, broker or network APIs. The extension, WebSocket tap, affiliate claims, login and execution modules were not run. Original uploaded source remains outside Git; the harness takes local file paths and records hashes.

Two timing assumptions are shown for each intensity, fixed before replay:
- `sampled5`: build the currently forming30-second candle from already observed5-second OHLC, evaluate every5seconds. This approximates the live partial-candle behavior; it is **not tick-exact**.
- `closed30`: evaluate only at completed30-second boundaries. This changes live execution timing and is a separate candidate, not an interchangeable backtest result.

Entry is the next observed5-second open after the available observation; settlement is the exact adaptive-expiry later observed open. A second run delays entry by5seconds. Gaps reset buffers, missing initial partial candles are discarded, settlements cannot cross gaps or evaluation boundaries, and trades do not overlap within an asset. Flat1-unit stakes; ties refund stake. No martingale, adaptive bankroll, favorite rotation or cross-asset shared-account limit is modeled. Pooled units are not an achievable account equity curve.

New confirmatory public sample: **154,469 five-second bars**, BTC/ETH/SOL, November15–17,2026; complete prior UTC days. Source one-second Binance archives were verified against published SHA-256 checksums before aggregation. No-trade buckets remain excluded. This is a different reserved sample from the preceding November1–14 studies. Public crypto is not Pocket Option OTC or actual broker execution.

The supplied PO export validation is also replayed, with the previously reserved final PO trade period unscored. Historical payout, account mode, market eligibility and actual order acceptance are not verified. The source default payout filter is90%; replay tables show70/80/90/92% scenarios instead of pretending to know every historical accepted payout.

## Reserved November15–17 proxy results

Win rates exclude refunded ties. Units assume one-unit stakes and no separate commission beyond the stated binary payout.

| Timing / mode | Trades | Wins / losses / ties | Win rate | Net80% | Net90% | Net92% | Net80%,5s entry delay |
|---|---:|---|---:|---:|---:|---:|---:|
| sampled5:low | 13,623 | 6893 / 6446 / 284 | 51.68% | -931.60 | -242.30 | -104.44 | -1213.20 |
| sampled5:mid | 655 | 349 / 300 / 6 | 53.78% | -20.80 | +14.10 | +21.08 | -4.00 |
| sampled5:high | 7 | 6 / 1 / 0 | 85.71% | +3.80 | +4.40 | +4.52 | +0.20 |
| closed30:low | 11,003 | 5430 / 5371 / 202 | 50.27% | -1027.00 | -484.00 | -375.40 | -973.80 |
| closed30:mid | 308 | 180 / 120 / 8 | 60.00% | +24.00 | +42.00 | +45.60 | -1.60 |
| closed30:high | 2 | 1 / 1 / 0 | 50.00% | -0.20 | -0.10 | -0.08 | -0.20 |

## Supplied Pocket Option export validation

| Timing / mode | Trades | Win rate | Net80% | Net92% |
|---|---:|---:|---:|---:|
| sampled5:low | 2760 | 49.87% | -279.60 | -116.04 |
| sampled5:mid | 152 | 48.68% | -18.80 | -9.92 |
| sampled5:high | 2 | 0.00% | -2.00 | -2.00 |
| closed30:low | 2239 | 50.27% | -211.80 | -77.52 |
| closed30:mid | 60 | 40.00% | -16.80 | -13.92 |
| closed30:high | 0 | n/a | +0.00 | +0.00 |

## Interpretation

Closed30/Mid is the most interesting descriptive variant (60% over308 trades), but it is a changed timing assumption, has only three fresh days, and does not pass the predeclared gate. Its80%-payout gain of24units becomes−1.6units in delayed replay. The sampled Mid primary is negative at80% and positive at92%; that payout sensitivity does not establish a stable edge.

High’s sampled85.71% win rate comes from **only seven trades**. Reporting it as an85% accurate bot would be misleading. All modes fail one or more sample count, confidence, multiplicity, day-cluster-bootstrap, multi-asset or latency requirements. Reused PO data and a three-day public sample cannot validate a general or broker-specific profitable strategy.

## Execution/result observations

The surrounding code has explicit trade locks, persisted recovery state, asset matching and broker deal-ID reconciliation. These are useful implementation patterns, not proof of profitable signals. `tradeResult.js` also includes balance-derived fallbacks; concurrent/manual transactions or delayed balance updates can make those unreliable. Performance evidence should retain actual order IDs and broker-confirmed per-deal settlements rather than treating a balance classification as ground truth.

No KAOS source, trading settings, owner credentials, payout settings or live hosting was changed by this review. Do not transplant third-party licensing/affiliate flows or execute the full extension as part of offline research.

## Reproduce

`python scripts/backtest_uploaded_signal_engine.py --indicators /private/indicators.js --engine /private/signalEngine.js --po /private/KAOS_ALL_DATA_2026-10-08T18-42-12.zip --fresh /path/avalisa-proxy-20261115`

Use the existing collector with `--start 2026-11-15 --days 3`. Full manifests, source URLs and checksums are in `results/summary.json`. Individual fresh replay decisions/trades are in `results/fresh_trades.csv`. No source ownership or redistribution right is inferred.

Pure-source checks: `node scripts/check_uploaded_signal_engine.cjs /private/signalEngine.js`. Checks passed for rule-count confidence, mode-dependent expiry, insufficient agreement, volatility veto and missing-data veto. The shared replay engine’s six causal/fill-accounting checks passed in the previous study. These are software checks, not predictive validation.

Plan SHA-256: `99a226390932ec6f69a9eff202a510e834902c128690ef18b6967e811972892d`.
