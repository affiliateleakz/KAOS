# KAOS 3.0 — First public market-data collector

Adds `collectors/binance_spot.py`, a Python standard-library collector for **public Binance spot 1-minute OHLC candles**. Defaults to BTCUSDT, ETHUSDT and SOLUSDT, accepts up to 150 exchange symbols, and converts closed candles into *research-only* technical observations accepted by `/api/v1/intelligence/ingest`. It deliberately does not trade or predict win probabilities. It is not a Pocket Option OTC feed; do not merge those prices.

## Setup

1. Deploy the existing `backend_foundation` Opportunity Radar routes with your existing FastAPI application, database, membership authentication and entitlements; configure `KAOS_COLLECTOR_KEY` to a long random secret on the backend.
2. On an always-on Python worker, configure the same `KAOS_COLLECTOR_KEY` and `KAOS_API_BASE=https://api.tradingwithkaos.com` (or the actual deployed base URL).
3. Run `python collectors/binance_spot.py --symbols BTCUSDT,ETHUSDT,SOLUSDT --dry-run` to inspect current observations without uploading them.
4. After validating output and backend authentication, run without `--dry-run`. Schedule approximately once per minute on an external worker; respect provider limits and availability. Use the API's ingested-source status and dashboard to verify successful delivery.
5. Run `cd collectors && python -m unittest -v` for deterministic offline unit tests.

## Limitations

No live API connection was tested in this environment; Binance access may be blocked in some jurisdictions. This is **one real public-source adapter**, not yet a universal 100+ market production collector. No social, options, stock, news or DEX sources are wired. Website and mobile interfaces still require build/device testing. No deployed systems have been changed. For production add retry/backoff, historical backfill, provider failover, persistent candle storage, metrics, and timezone-aware candle completeness checks.

## v0.2: DexScreener DEX liquidity activity collector

`collectors/dexscreener_pairs.py` retrieves public search results from DexScreener and emits **neutral liquidity activity** observations, not directional predictions. Example: `python collectors/dexscreener_pairs.py --queries SOL,ETH,BTC --dry-run`. The default minimum reported pool liquidity is $25,000; use `--min-liquidity 100000` to increase it. The search endpoint is **not** a comprehensive DEX market scanner or real-time on-chain indexing service; matching pools can include irrelevant tokens. Pair identity is chain + pair address, so do not confuse identical tickers across chains. Liquidity and volume are provider-reported snapshots; they are not independently audited and can be manipulated. The collector uses five-minute observation IDs to reduce duplicates and submits up to 250 observations per batch. The source's `observed_at` is the **collection time**, not the time of a historical trade. Validate provider terms and rate limits before continuous operation. No external requests or live integrations have been verified in this build.

## v0.6 institutional + social extension
Read `collectors/README_13F_SOCIAL_V06.md`. New modules use configured manager CIKs and public Bluesky handles, and do not require Unusual Whales or any paid data-service subscription. Both emit neutral research-only observations; neither proves trades, price direction, or social sentiment. They remain off until populated in the configuration file.

## v0.9 additions
See `collectors/README_SOCIAL_SQUEEZE_V09.md` for opt-in public Bluesky search, local-only short-interest review, and conflict-aware research ranking. No paid Unusual Whales integration.
