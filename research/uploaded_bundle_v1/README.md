# Uploaded content-main.js — static strategy review and replay

**Finding: neither source-default reproducible rule passed the reserved-week proof gate. The uploaded bundle was never executed, installed into KAOS, or connected to a broker.**

Source SHA-256: `cebc3e77ff0722bed5b175d1a08704cdbb1f13fe401cd5ad0bfa20cdcc77efea`. Original file remains outside Git. This report describes observed rules; it does not assert ownership or permission to redistribute the third-party bundle.

## Observed strategies

- Module10/15, CCI20: source computes `(open+high+low+close)/4`, mean absolute deviation over20 bars, divisor**0.02**, CALL crossing upward through**−115**, PUT crossing downward through**+115**. This differs from common HLC3/0.015 CCI; the replay uses the actual source formula.
- Module11, four candles: four completed bullish candles → PUT; four completed bearish candles → CALL. Any doji breaks the setup.
- Module14, pin bar: examines the **currently forming candle during its final third**, using dominant wick>4×body. Final OHLC cannot be used to claim this intrabar signal was known earlier; not backtested without suitable tick/partial-candle replay.
- Module12, platform signals: requires the broker’s `chafor` forecasts. Their historical values are not in the archive; no outcomes or price features were substituted for missing forecasts.
- Module13, martingale: position sizing/follow-up after manual trades, not a predictive strategy. It was not used to manufacture apparent profitability.
- Module19 defaults are M1 indicator candles and M1 expiry. Those exact source defaults were the two reserved-week primary tests. Author intent for other configurations is not known.

## Research protocol

18 predeclared descriptive configurations: two closed-candle rules ×15/30/60s chart intervals ×30/60/180s expiries. They were screened on the existing October proxy and broker-export validation. No sensitivity was promoted after looking at those results. Only the two source-default M1/M1 rules were evaluated on the new reserved November8–14 BTC/ETH/SOL proxy sample.

The new sample contains **355,929 five-second bars** from SHA-256 verified Binance one-second archives. Price data are public crypto proxies, not Pocket Option OTC or observed broker settlements. The preceding November1–7 sample had already been consumed by the video research and was not relabeled unseen.

Every trade uses completed indicator bars, next observed five-second open entry, exact observed expiry open, no gap bridging, no within-asset overlap and flat one-unit stake. Warmup resets on gaps and requires300 indicator bars. This is conservative relative to the source’s20-bar CCI initialization and severely reduces coverage at M1, particularly ETH/SOL. Reported counts reflect that limitation; missing bars were not filled.

## Reserved November8–14 results

| Rule | Trades | Wins / losses / ties | Decided win rate | Net at80% | Net at92% | Net80%,5s delay |
|---|---:|---|---:|---:|---:|---:|
| bundle_cci:source:60s:60s | 244 | 119 / 123 / 2 | 49.17% | -27.80 | -13.52 | -24.40 |
| bundle_four_candles:source:60s:60s | 507 | 266 / 238 / 3 | 52.78% | -25.20 | +6.72 | -26.00 |

P&L units are hypothetical one-unit stakes, not dollars or return percentages. Ties refund stake. Break-even is55.56% at80% payout and52.08% at92%. No fee, payout, latency, rejection or settlement behavior has been verified with a live broker. A five-second delay is a stress scenario, not a measured latency guarantee.

Both candidates fail the predeclared multi-day, sample-count, confidence, multiplicity, day-cluster-bootstrap, multi-asset and latency gate. The small92%-payout four-candle gain is not robust evidence. The six replay checks pass, but passing software checks is not a profitable strategy result.

## Full descriptive grid

| Period | Rule | Trades | Win rate | Net80% |
|---|---|---:|---:|---:|
| po_validation | bundle_cci:source:15s:30s | 454 | 49.22% | -51.20 |
| po_validation | bundle_cci:source:15s:60s | 428 | 46.23% | -71.20 |
| po_validation | bundle_cci:source:15s:180s | 325 | 47.38% | -47.80 |
| po_validation | bundle_cci:source:30s:30s | 223 | 46.40% | -36.60 |
| po_validation | bundle_cci:source:30s:60s | 223 | 50.00% | -22.20 |
| po_validation | bundle_cci:source:30s:180s | 185 | 49.19% | -21.20 |
| po_validation | bundle_cci:source:60s:30s | 107 | 47.17% | -16.00 |
| po_validation | bundle_cci:source:60s:60s | 107 | 45.79% | -18.80 |
| po_validation | bundle_cci:source:60s:180s | 104 | 46.15% | -17.60 |
| po_validation | bundle_four_candles:source:15s:30s | 573 | 44.62% | -111.60 |
| po_validation | bundle_four_candles:source:15s:60s | 467 | 49.78% | -48.00 |
| po_validation | bundle_four_candles:source:15s:180s | 298 | 48.65% | -36.80 |
| po_validation | bundle_four_candles:source:30s:30s | 453 | 52.99% | -20.80 |
| po_validation | bundle_four_candles:source:30s:60s | 306 | 55.92% | +2.00 |
| po_validation | bundle_four_candles:source:30s:180s | 224 | 52.25% | -13.20 |
| po_validation | bundle_four_candles:source:60s:30s | 230 | 46.05% | -39.00 |
| po_validation | bundle_four_candles:source:60s:60s | 230 | 49.34% | -25.60 |
| po_validation | bundle_four_candles:source:60s:180s | 135 | 55.97% | +1.00 |
| october_proxy | bundle_cci:source:15s:30s | 2278 | 49.76% | -219.20 |
| october_proxy | bundle_cci:source:15s:60s | 2174 | 51.66% | -146.20 |
| october_proxy | bundle_cci:source:15s:180s | 1721 | 51.18% | -133.80 |
| october_proxy | bundle_cci:source:30s:30s | 943 | 51.58% | -63.40 |
| october_proxy | bundle_cci:source:30s:60s | 943 | 52.00% | -57.80 |
| october_proxy | bundle_cci:source:30s:180s | 849 | 56.12% | +8.60 |
| october_proxy | bundle_cci:source:60s:30s | 372 | 56.29% | +4.60 |
| october_proxy | bundle_cci:source:60s:60s | 372 | 54.34% | -7.80 |
| october_proxy | bundle_cci:source:60s:180s | 365 | 54.67% | -5.80 |
| october_proxy | bundle_four_candles:source:15s:30s | 3166 | 44.75% | -585.60 |
| october_proxy | bundle_four_candles:source:15s:60s | 2511 | 46.06% | -420.60 |
| october_proxy | bundle_four_candles:source:15s:180s | 1712 | 49.68% | -180.40 |
| october_proxy | bundle_four_candles:source:30s:30s | 2252 | 45.22% | -396.80 |
| october_proxy | bundle_four_candles:source:30s:60s | 1482 | 47.33% | -213.40 |
| october_proxy | bundle_four_candles:source:30s:180s | 1018 | 47.48% | -147.20 |
| october_proxy | bundle_four_candles:source:60s:30s | 907 | 49.00% | -100.20 |
| october_proxy | bundle_four_candles:source:60s:60s | 907 | 48.57% | -110.00 |
| october_proxy | bundle_four_candles:source:60s:180s | 516 | 52.05% | -32.40 |

## Transport findings (static inspection only)

The bundle installs a broker WebSocket hook, follows account mode, submits orders and calls an external `api.pobot.net` capabilities service using platform UID. It is not merely a standalone indicator. Those network/authorization paths were not executed, copied into KAOS, or bypassed. Broker-account access would require a separate implementation/security review.

## Reproduce

`python scripts/backtest_uploaded_bundle.py --source /private/content-main.js --po /private/KAOS_ALL_DATA_2026-10-08T18-42-12.zip --october /path/public-candles-20261001 --fresh /path/bundle-proxy-holdout-20261108`

Use the existing collector with `--start 2026-11-08 --days 7` to reproduce the fresh archive. Summary source manifests include hashes and URLs. Member export/source files remain private and outside Git. The old reserved PO final trade-replay period was not scored.

Checks: `python -m pytest -q scripts/tests/test_video_strategy_replay.py scripts/tests/test_uploaded_bundle_replay.py` —6passed. These cover payout/ties, aggregation, causal signals, next-open settlement, gap handling, source CCI formulation and doji handling. No real orders were placed.

Plan SHA-256: `6237b58a03ff8b37114a00d6899c8856860e30098fa75325ec102a09a6bb8118`.

## Operational scope

Only the two closed-candle decision rules are reproduced. The bundle’s global deal limit, current payout filter, symbol eligibility, capability service, manual entries, account balance stops and real/demo routing are not reproduced by the replay. Missing historical payout/forecast/permission data cannot be inferred. Pooled per-asset unit totals are not a shared-account equity curve.
