# Optional TradingView historical research adapter

Source inspiration: [rongardF/tvdatafeed](https://github.com/rongardF/tvdatafeed), MIT-licensed code fork of StreamAlpha's tvdatafeed. This does **not** mean TradingView market-data access, resale, redistribution, scraping, automated collection or licensing rights are granted. Check TradingView's latest service/data terms, exchange agreements and permission requirements *before* using the provider for KAOS commercial operation.

## What is implemented

- `research/market_intelligence/tvdatafeed_adapter.py` is an original bounded **one-shot** source adapter.
- It optionally imports `TvDatafeed` from a separately installed Python environment, or processes offline fixture records without dependencies.
- The result preserves provider, exchange, asset class, bar interval, UTC timestamps and every closed OHLCV candle; it reports missing intervals rather than filling them.
- It rejects missing volume and price fields, invalid OHLC, time ambiguities, duplicate timestamps and still-open bars. It never sends requests to KAOS broker or execution endpoints, never writes to the live archive and never starts a background thread.
- Research tests are offline and do not authenticate to TradingView.

## Explicit manual experiment

Start with a permitted sample and review access terms. In a disposable separate virtualenv (the project's old pinned dependencies may conflict with current KAOS packages):

```bash
python -m pip install git+https://github.com/rongardF/tvdatafeed.git
python research/market_intelligence/tvdatafeed_adapter.py \
  --fetch --acknowledge-provider-terms \
  --symbol BTCUSDT --exchange BINANCE --asset-class crypto \
  --seconds 60 --n-bars 300 --source-timezone UTC \
  --output tv_btc_research.json
```

Only set `--source-timezone UTC` if you have independently confirmed the provider's timestamps are UTC; otherwise use the correct exchange timezone. Naive timestamps without an explicit timezone are rejected. TradingView username/password, if required and permitted, must be supplied separately via `TRADINGVIEW_USERNAME` and `TRADINGVIEW_PASSWORD`; do not commit them or pass them to the browser. No-loop manual use only. Even with a library MIT license, this command must NOT be run before appropriate provider rights are established.

Offline fixture mode:

```bash
python research/market_intelligence/tvdatafeed_adapter.py \
  --input-json fixtures/example.json \
  --symbol BTCUSDT --exchange BINANCE --asset-class crypto \
  --seconds 60 --output normalized.json
```

## Critical constraints

The upstream README advertises up to 5000 historical bars per request and minute-or-longer intervals. `TvDatafeedLive` polls new bars using threads; its README expressly says it does **not** provide true realtime samples. It offers no 5s/15s/30s validated native candles and cannot be used as an OTC Pocket Option quote proxy.

A 24/7 KAOS candle recorder must use authorized feed contracts, a separate supervised long-running worker, retries, historical catch-up, immutable source/timeframe/asset IDs, idempotent archive writing, last-complete-bar checks, gap/duplicate detection and quality monitoring. Market closures and exchange sessions must be modeled explicitly. If an optional TradingView research sample is later compared against exchange feeds, **do not blend their OHLCV histories** into one synthetic record.

This code is not a continuously running recorder and does not establish that market feeds or historical archives are available. Nothing is merged or deployed.

## KAOS Historical Candle Backfill — on-demand script

The convenient entry point is `kaos_backfill.py`, which supports permitted one-shot provider fetches or offline fixture normalization and writes a versioned, immutable-by-default JSON research archive:

```bash
python research/market_intelligence/kaos_backfill.py \
  --provider tvdatafeed --symbol BTCUSDT --exchange BINANCE \
  --asset-class crypto --seconds 60 --bars 500 \
  --source-timezone UTC --fetch --acknowledge-provider-terms \
  --output ./research_data/btcusdt_1m_20261120.json
```

This requires installation of the third-party client in an isolated environment, sufficient permission from TradingView and relevant data providers, and a manually confirmed timestamp timezone. The `--acknowledge-provider-terms` flag **does not grant permission**. The result is local and deliberately does not ingest into KAOS's production DB.

The output includes source, exchange, asset class, interval, UTC OHLCV candles, gap count, and an *indicative* `usable_for_training` flag for a contiguous sample of at least 64 completed candles. This flag is only a minimal structural check, not evidence of licensing, provider accuracy, enough history to train, or any measured predictive edge. Downstream models must perform their own point-in-time integrity checks.

Offline verification (no provider access needed):

```bash
python -m unittest discover -s research/market_intelligence -p 'test_tvdatafeed_adapter.py'
python -m unittest discover -s research/market_intelligence -p 'test_kaos_backfill.py'
```

KAOS's existing `chart_windows.py` can consume the exported JSON as candle input for testing once the export is checked for training suitability. The pipeline branch is separate from this PR, so merge integration carefully and avoid assuming data collection already runs.

For your eventual always-on recorder, prefer an **authorized, supervised market-feed worker** that archives incremental closed bars and backfills gaps. The manual script is a research tool that can help recover history on demand; it cannot create missing sub-minute bars or guarantee that previously unavailable candles can be recovered.
