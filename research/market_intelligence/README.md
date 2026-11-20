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
