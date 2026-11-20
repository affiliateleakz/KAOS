# KAOS Automatic Market Backfill — member Opportunity Radar integration

This research feature integrates historical candle retrieval into **KAOS Opportunity Radar → Market history & AI research data**. Authenticated members can enter a stock/ETF symbol (AAPL/SPY), crypto spot product (BTC-USD) or forex instrument (EUR_USD), select 1m/5m/15m, and click **Search market + backfill**.

Backend: `GET /api/v1/research/market-history/search?symbol=BTC-USD&asset_class=crypto&seconds=60`, authenticated. Query resolution triggers a bounded on-demand request, caches the result for five minutes in MongoDB `kaos_market_history_cache`, and prevents multiple simultaneous same-market fetches using a bounded in-database lease. One provider call returns at most 300 recent bars; source and market identity are retained. Bars that are malformed or still forming are excluded. Gaps are reported, not interpolated.

Providers used (not unofficial tvdatafeed):
- **Crypto**: Coinbase Exchange public product candles (the existing KAOS read-only market-data adapter); BTC-USD, ETH-USD, etc. Cannot represent Pocket Option OTC or every crypto venue.
- **Stocks/ETFs**: Alpaca Market Data, using configured server-side `APCA_API_KEY_ID`, `APCA_API_SECRET_KEY` and `KAOS_ALPACA_DATA_FEED=iex` (default). IEX is partial U.S. exchange coverage; SIP requires separately licensed subscription. If credentials/provider permissions are missing, return an explicit 503, never substitute fake candles.
- **Forex**: OANDA v20 instrument candles, if `KAOS_OANDA_DATA_TOKEN` and `KAOS_OANDA_ENVIRONMENT=practice|live` are configured; returned OANDA activity volume is **not central global forex volume**.

The **Load latest news** function remains independent on the same page. News and candle lookups must not imply that a news event caused a price movement unless point-in-time comparisons have been validated.

Market search is **manual user-triggered automatic fetch**; it is not a continuously running worker. Caching results to enable a repeat lookup does not, by itself, approve those results for AI training. `ai_training_approved: false` is explicitly returned and no bars are copied into `kaos_research_candles`. For the future always-on recorder, choose approved feed rights and add provenance/audit, persistence, deduplication, freshness health, and a supervisor separately.

## Deployment prerequisites

1. Merge PR only after CI and entitlement/security review.
2. Deploy both the API router and Opportunity Radar UI; keep provider credentials in server environment only.
3. Confirm each provider's terms, market-data rights, cost, quotas and commercial display permissions. The free/public endpoint of a provider does not grant unlimited commercial redistribution.
4. Test with a live valid symbol in each **actually configured** provider; unsupported markets must produce an unavailable state.
5. Add controls for operator-provider enablement and per-member volume quotas before large-scale public release.

The separate research-only tvdatafeed CLI PR can be used for **authorized manual backfills**, but this feature never starts unauthenticated TradingView scraping or persistent TvDatafeedLive threads.
