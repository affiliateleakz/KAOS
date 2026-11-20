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
