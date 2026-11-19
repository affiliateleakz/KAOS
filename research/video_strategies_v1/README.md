# Three supplied video strategies — proof-of-concept research

**Finding: no strategy passed the predefined proof gate. Do not market these replays as demonstrated live profitability.**

144 predeclared configurations were replayed on the supplied Pocket Option OHLC export and a public October crypto sample. Three video-derived primary interpretations and one validation-selected sensitivity were then evaluated on a freshly collected November 1–7 sample. No settings were tuned after those fresh results.

## Data

- Pocket Option member export: **145,341 five-second bars, 30 markets, 165 contiguous segments**. Recorded trade outcomes were not used: the earlier audit found inconsistent labels. Broker payout, account mode and exact tick executions remain unverified.
- Public development/validation proxy: **357,634 five-second bars**, BTC/ETH/SOL, October 1–7, 2026. These data were used in prior KAOS research and are not new holdout evidence.
- Fresh confirmatory proxy: **355,140 five-second bars**, BTC/ETH/SOL, November 1–7, 2026. Downloaded from Binance public one-second archives, verified against published SHA-256 checksums, then aggregated only from complete five-second buckets. No-trade buckets are excluded; resulting gaps reset indicator warmup.
- Total replay input: **858,115 five-second candles**. These are OHLC price proxies, not 858,115 independent trials. Overlapping candidate tests reuse the same prices.
- Public crypto candles cannot prove a Pocket Option OTC edge. OTC prices are broker-specific. Exact broker settlements and accepted payouts are required for that claim.

## Rules recovered from the videos

| Video | Observed evidence | Explicit test interpretation / uncertainty |
|---|---|---|
| (2), 4m44s | Narration 0–4s: 10s candles. 12–17s and screenshot16s: MACD10/15/5. 26s: RSI10, midpoint50. 47s/119s: three-minute expiry. | Two directional crossovers agree within two closed bars, with a new crossover on the current bar. Same-bar strict crossover tested separately. Exact visual discretionary range/candle-strength judgments are not fully specified. |
| (3), 4m57s | Screenshot30s: MACD10/20/9. Screenshot50s: RSI14; guides80/20 at60s. Final examples show two MAs and one-minute expiry. Local transcription detected no intelligible narration. | MA periods/type are unreadable: primary assumes EMA5/20, with EMA10/20 and SMA5/20 sensitivity. Entry is MA crossover with MACD/RSI agreement. This is a reconstruction, not claimed exact replication. |
| (4), 11m26s | Narration154–174s: five-second candles, SAR + Supertrend, defaults. 198–210s: 30s expiry. 259–276s: Supertrend flip plus SAR on matching side, wait for candle close. | Primary assumes Supertrend ATR10/multiplier3 and SAR start/increment0.02/max0.2. Exact Pocket Option defaults are not shown; ATR7/3,10/2,14/3 are predefined sensitivity. Calculator/session targets and six selected demo wins are not evidence of an edge. |

All rules are causal, evaluated on completed candles after 300 indicator-bar warmup per contiguous segment. Entry is the next observed five-second open after confirmation; settlement is an exact later observed open. Trades never settle across a data gap and do not overlap within an asset.

## Fresh November results

Flat one-unit stake per trade. Wins earn the stated net payout; losses lose one unit; ties refund stake. Units are hypothetical P&L, not dollars or portfolio returns. The delayed replay enters five seconds later and can have a different non-overlapping trade count.

| Rule | Trades | Wins / losses / ties | Decided win rate | P&L at 80% payout | P&L at 92% payout | P&L at 80%, 5s entry delay |
|---|---:|---|---:|---:|---:|---:|
| Video 2 · MACD/RSI | 1,646 | 832 / 812 / 2 | 50.61% | -146.40 | -46.56 | -181.80 |
| Video 3 · MA/MACD/RSI approximation | 4,788 | 2,556 / 2,138 / 94 | 54.45% | -93.20 | +213.52 | -209.20 |
| Video 4 · Supertrend/SAR approximation | 5,610 | 3,045 / 2,367 / 198 | 56.26% | +69.00 | +434.40 | -237.80 |
| Validation-selected sensitivity | 2,809 | 1,498 / 1,120 / 191 | 57.22% | +78.40 | +258.16 | -155.40 |

At 80% payout, decided-trade break-even is **55.56%**; at 92%, it is **52.08%**. A high win rate alone is not sufficient. Quotes/settlement boundaries, latency, payout changes and dependence can erase small apparent advantages.

## Pocket Option export validation replay

| Primary interpretation | Trades | Win rate | Net units at 80% payout |
|---|---:|---:|---:|
| Video 2 · MACD/RSI | 315 | 48.57% | -39.60 |
| Video 3 · MA/MACD/RSI approximation | 773 | 48.38% | -99.60 |
| Video 4 · Supertrend/SAR approximation | 842 | 51.01% | -68.60 |

This validation window has only one UTC day; it does not establish multi-day robustness. The old reserved final PO trade-replay period was **not scored**. Signals settling across a split boundary were purged.

## Selection and statistics

All 144 configurations and their development/validation results are disclosed in `results/summary.json`. The grid covers four candle timeframes, four expiries, two MACD/RSI interpretations, three MA interpretations and four Supertrend settings. No reverse-direction searches, learned models, adaptive bet sizes, martingale, or post-result market removal were added.

Validation-qualified sensitivities: **5**. Only the best preregistered rank was selected for the fresh comparison: `sar_supertrend:7_3:10s:15s`. It failed the fresh gate. The selected settings are not a recommendation.

The gate requires at least200 decided trades, multiple days, a Wilson95% lower win-rate bound above 80%-payout break-even, a one-sided binomial p-value after Bonferroni correction (144 validation trials; four fresh comparisons), a positive lower day-cluster-bootstrap bound, at least two profitable assets, and positive five-second latency-stressed P&L. Win-rate/binomial intervals assume IID observations; market dependence makes that assumption optimistic. Day-cluster bootstrap resamples whole UTC days pooled across assets, but only seven fresh days remain a small sample.

## Baselines on identical primary signal times

These are diagnostic direction baselines, not additional selected strategies. Previous direction uses the immediately preceding five-second candle; a doji means no baseline position. Their different tie/no-position counts mean they are not equal-turnover benchmarks.

| Rule | Own net80 | Always CALL net80 | Always PUT net80 | Previous5s direction net80 |
|---|---:|---:|---:|---:|
| Video 2 · MACD/RSI | -146.40 | -207.60 | -121.20 | -101.60 |
| Video 3 · MA/MACD/RSI approximation | -93.20 | -509.00 | -429.80 | -131.60 |
| Video 4 · Supertrend/SAR approximation | +69.00 | -462.00 | -620.40 | +68.00 |
| Validation-selected sensitivity | +78.40 | -357.20 | -166.40 | +161.40 |

## Practical decision

The Supertrend/SAR primary is worth further investigation, but its proxy gain is concentrated in BTC and becomes a loss with entry delay. Both other proxy assets lose at 80%. It also loses in the supplied broker-export validation. **Do not replace the live KAOS strategy or advertise a verified edge on this evidence.**

Next proof step: freeze one candidate and record new, prospective Pocket Option quotes, signal timestamps, requested/accepted entry, accepted expiry, payout and broker-confirmed outcomes. Separate OTC and regular markets, account mode and assets. Paper/demo results must be labeled. Do not cherry-pick sessions or re-optimize on the reserved evaluation. Actual latency is especially important at these horizons.

## Reproduce / artifacts

`python scripts/backtest_video_strategies.py --po /private/KAOS_ALL_DATA_2026-10-08T18-42-12.zip --october /path/public-candles-20261001 --november /path/video-proxy-holdout-20261101`

Use `scripts/collect_public_candles.py --start 2026-11-01 --days 7 --out /path/video-proxy-holdout-20261101 --cache /path/cache` for the fresh archive. Original member export/video files and transcripts remain outside Git. `video_manifest.json` and summary source manifests record hashes and archive URLs.

Four targeted offline checks passed: complete aligned aggregation, indicator-prefix causality for all variants, next-open/exact settlement and gap rejection, and payout/tie accounting. JavaScript syntax and extension ZIP checks passed. No broker credentials, orders, live hosting or trading settings were changed.

Frozen rule-plan SHA-256: `b07b8567d10f3e3a74a44e25735db177a17c0d436f43ffd2d101badd871d2230`. Runner SHA-256: `9335dd3328190dcb8d4c1e52bf73ff555dcd3147f7cecf64cbeb99aeb481717e`.

The initial visual plan was corrected **before any replay** after audio extraction clarified video(2) as10-second candles/180-second expiry. The correction and initial hash are retained in `plan.json`.

## Extension label correction

Extension1.7.41 changes the visible `HOLD · CANDIDATE 7B · ...` and controller label to `KAOS STRATEGY`. Saved IDs and trading logic are unchanged. This naming correction is independent of the video research.

## Additional uploaded source

The subsequent `content-main.js` upload was reviewed and its reproducible rules tested separately on a new reserved week. See [uploaded-bundle research](../uploaded_bundle_v1/README.md). It did not change this video plan, parameters or evaluated results.

At92% payout, delayed MA/MACD/RSI and primary Supertrend/SAR proxy replays remain positive in raw units (+89.12 and +107.68), but their delayed Wilson lower bounds (51.64% and51.79%) remain below the52.08% break-even threshold; the broker-export checks are negative even at92%. This sensitivity is disclosed rather than treated as proof.

## Portfolio scope

These are pooled per-asset signal-quality replays, not a four-chart account simulation. A four-chart simultaneous-slot limit, global capital allocation, discretionary symbol switching and the video’s session take-profit/stop-loss calculator are not modeled. Pooled unit totals cannot be presented as an achievable shared-account equity curve.
