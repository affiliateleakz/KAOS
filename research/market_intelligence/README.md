# KAOS Market Intelligence Research Dataset — phase 1

Research-only join of the existing owner candle archive and KAOS intelligence observations.

## Data source

- Candles: owner API `GET /api/v1/owner/candles/export?symbol=BTC-USD&asset_class=crypto&seconds=60&limit=5000`
- News/social: new owner API `GET /api/v1/owner/intelligence/export?asset=BTC-USD&asset_class=crypto&limit=5000`

Both owner APIs require an authenticated owner/admin and must not be exposed publicly. Do not store personal information, credentials, or raw licensed market feeds in Git.

## Build

```bash
python research/market_intelligence/build_dataset.py --candles candles.json --intelligence intelligence.json --horizons 300,3600 --output joined_dataset.json
PYTHONPATH=research/market_intelligence python -m unittest discover -s research/market_intelligence -p 'test_*.py' -v
```

The dataset joins ONLY events whose **collection time** is at or before the close of a completed candle. It computes counts of distinct news/social observation IDs in the last and previous hour and a difference. News coverage is not measured positive sentiment, nor are social observations full-platform counts. Unknown unique author counts and sentiment are explicitly null.

Existing owner candle exports are 60/300/900 seconds; **they cannot support 5-second or 30-second outcomes**, which need a separate genuine subminute archive. Price labels are indicative next-bar-open to end-of-horizon-close results. The 1h horizon requires sufficient continuous bars. Dataset rows overlap, so use purged chronological splits before fitting any model; do not feed test data into threshold selection.

## Next steps

Persist periodic structured social sample counts and unique-author counts instead of inferring them from summary strings; retain venue, sampling coverage and event timestamps. Add timestamped measured sentiment with provenance. Create source-specific collect/ingest workers, a joined dataset trainer, and walk-forward performance reports with market-appropriate fee/slippage models. None of these is implied to be deployed by this PR.

## Structured Bluesky social samples (PR phase 2)

The public search collector and monitored-account collector now attach `sample_metrics` to their existing neutral intelligence records:

- `provider`: explicitly identifies bounded public search vs. monitored accounts
- `sampled_posts`, `sampled_unique_authors`: de-duplicated observed posts/authors
- `previous_hour_posts`, `previous_hour_unique_authors`: available from bounded public search, unknown (null) for monitored-account sampling
- `search_results_inspected`, `search_limit`, `coverage`: source coverage caveats

The collectors use per-minute event IDs so each sampled minute can be retained in the intelligence archive rather than overwriting an entire hour. A zero-post sampling interval is not emitted as a false platform-wide zero; absent samples are unknown.

The dataset uses the latest fresh (at most one hour old) structured social sample **as of the candle close**, with sampled posts, distinct sampled authors, and within-sample prior-hour change. These are *sample observations*, not complete social-media mention velocity, account growth, or verified sentiment. Missing or old snapshots remain null. The public search API is capped at 100 results, and monitored-account sampling is bounded by 30 feeds × 100 posts.

### Important next integration

The legacy Bluesky collectors currently label observations as `asset_class=stock` and use symbols like `BTC`, while the candle archive identifies crypto pairs such as `BTC-USD`. A source-verified symbol mapping and explicit crypto asset classification are required before crypto social samples can be joined correctly. Until then the builder excludes mismatched identities rather than silently attaching unrelated observations. Also verify provider usage terms and worker uptime before claiming live monitoring.

## Crypto alias reconciliation and offline model testing

Legacy Bluesky collectors record cashtags as stock-class tickers, while Coinbase records crypto pairs. A strictly allowlisted, collector-event-specific mapping now recognizes:

| Bluesky cashtag | Coinbase pair |
|---|---|
| BTC | BTC-USD |
| ETH | ETH-USD |
| SOL | SOL-USD |

Owner intelligence exports include those legacy Bluesky events. The builder **will not** map arbitrary tickers or news records to a crypto pair.

Train an isolated model *after* building the dataset with enough contiguous real candles:

```bash
python research/market_intelligence/train_joined.py --input joined_dataset.json --horizon-seconds 300 --cost-bps 10 --output evaluation.json
```

The evaluator fits a small hist-gradient-boosted classifier on training rows, chooses a hypothetical threshold from validation rows, and reports held-out test classification and indicative return statistics. It uses purged chronological train/validation/test splits. Each market and forecast horizon requires a **separate** run. It will refuse short, mixed-source, or invalid datasets.

Tests use synthetic market fixtures only. **No real-world win-rate or profitability has been established.** Missing news/social counts often reflect missing collection coverage, not absence of market attention. The evaluator does not model overlapping holdings, realistic order book fills, or broker-specific trading constraints; research results cannot be treated as deployable signals.

## Experimental candle-image learning inspiration

The external public project [amit-agni/candlesticks-deeplearning](https://github.com/amit-agni/candlesticks-deeplearning) explored candlestick-image CNN and MobileNet classification for next-day price movement. The author's README reports unsatisfactory model performance. No clear license file was present in the root listing when reviewed; **no upstream source code has been copied** into KAOS.

KAOS includes an independently written `chart_windows.py` dataset generator. Instead of screenshots, it produces normalized, fixed-length OHLCV sequences. The format can later feed a separately evaluated 1D CNN or other sequence model, with consistent source/horizon definitions and timestamps. It does **not** fit a neural network or claim an advantage over KAOS's tabular model.

Example:

```bash
python research/market_intelligence/chart_windows.py --input candles.json --lookback 24 --horizon-bars 5 --output chart_windows.json
```

Important safeguards: window-only normalization, source consistency, closed-candle decisions, contiguous bars, separate forward labels, and a standard-library-only dataset build. Train a future sequence model with purged chronological splits, comparing against the same held-out periods and transaction-cost assumptions as `train_joined.py`. Do not random-shuffle overlapping windows into train and test.

## Original PyTorch OHLCV CNN baseline — external research inspiration

The public [hardyqr/CNN-for-Stock-Market-Prediction-PyTorch](https://github.com/hardyqr/CNN-for-Stock-Market-Prediction-PyTorch) project explored both rendered candlestick images and direct 5-row OHLCV matrices, with an early PyTorch CNN. It includes older training/test methods and model artifacts, **not validated KAOS trading strategies**. Its source directory uses legacy PyTorch and pandas APIs; its evaluation routines do not provide a dependable, modern, time-safe comparison. No license was listed in the top-level repository files inspected. **No external code, datasets or pretrained weights were copied into KAOS.**

KAOS now has independently implemented `train_candle_cnn.py`: a small 1D PyTorch CNN for the `chart_windows.py` OHLCV sequences. It is optional, offline and isolated from all production APIs and trading logic. It uses deterministic CPU training, an original lightweight architecture, chronological splitting, purging on future-label completion, and a validation-selected epoch before a single held-out test assessment.

```bash
# Dependencies only for an isolated training environment, NOT the KAOS API:
python -m pip install numpy torch
python research/market_intelligence/chart_windows.py --input candles.json --lookback 24 --horizon-bars 5 --output chart_windows.json
python research/market_intelligence/train_candle_cnn.py --input chart_windows.json --epochs 12 --cost-bps 10 --output candle_cnn_report.json
```

Compare the CNN `test_accuracy` and `test_majority_baseline_accuracy` on exactly the same market and held-out period. To compare with the joined intelligence model, align its market, source, timeframe, target horizon, test dates, execution-cost assumptions and underlying outcome definitions first. The CNN's `test_all_direction_net_return_mean_proxy` is an illustrative *overlapping* signal-return proxy, not feasible portfolio P&L or validated trade win rate.

No CNN weights are registered or deployed; no production screenshot image prediction is connected. This offline baseline is preparation for the future always-running candle recorder, not evidence that it is already collecting candles.
