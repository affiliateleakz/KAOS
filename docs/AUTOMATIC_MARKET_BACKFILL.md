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

## New: Opportunity Radar multi-factor assessment

After a member initiates a market search, the authenticated `/api/v1/research/market-history/assessment` reads the same cached completed candles and already-ingested `kaos_intelligence` observations for that exact market and asset class. It computes an inspectable technical alignment index (EMA20, EMA50, RSI14, MACD12/26 difference, ATR14, volume ratio when available, and simple breakout / doji-like structures). Research evidence is deduplicated and labeled by source, with missing news/social/filing coverage disclosed.

**Do not mistake the current technical index for a price forecast or calibrated BUY/SELL model.** It is a rough heuristic research score. No target price, verified accuracy, or probability is supplied; missing/stale/incomplete data yields WAIT. Candle-source time gaps prevent directional calls. Because stocks can have normal overnight/session gaps, a future session-aware continuity validator is required before treating regular session bars as complete enough for current directional scoring. This route does not automatically query news providers or expand archive coverage; only already collected evidence is displayed.

Options output deliberately abstains (NONE, no expiration or contract) until an independently validated options pipeline can examine a contemporaneous listed option chain, available contracts/expirations, strikes, bid/ask, open interest, fees, liquidity and underlying forecasts. Do not invent a call/put expiration from a stock-only trend score.

## TradingView-API evaluated — opt-in local research experiment

Reviewed [Mathieu2301/TradingView-API](https://github.com/Mathieu2301/TradingView-API), JS/TS Node 20+ npm package `@mathieuc/tradingview` v4 (ISC-licensed source). Its data API supports historical candles, indicators, market search, technical ratings, screeners and strategy reports; its backtest module has chronological splits, costs and a random-entry baseline. The project's anonymous TradingView access may return delayed/substitute feeds; session cookies give only the account's own entitlements. Third-party package licensing DOES NOT grant the right to obtain, store or redistribute TradingView's data commercially.

Added an **optional offline-first** `research/market_intelligence/tradingview_api_adapter.mjs` with no-copy original normalization code, strict exchange-qualified symbols, bounded candles, completed-bar checks and explicit provider tagging. Run local tests with `node --test research/market_intelligence/tradingview_api_adapter.test.mjs`. Fixture-based use only by default. To fetch from the unofficial provider requires separately verified authorization, installed `@mathieuc/tradingview` in an isolated Node environment, and an explicit rights acknowledgement; no member-search route uses this package. These second-based interval strings express *possible requested intervals*, **not** proof the TradingView account/provider supplies valid true 1s/5s/15s/30s data.

Automatic KAOS backfill continues to use configured Coinbase, Alpaca or OANDA connections. Never treat community TradingView access as an authorized fallback or silently combine quote sources.

## Real options chain shortlist (development, no buy/put decision yet)

The Market Research search for a stock or ETF also calls `GET /api/v1/research/market-history/options/chain-review?symbol=AAPL` after the research assessment succeeds. This endpoint uses **configured Tradier GET market-data endpoints only** to retrieve actual listed expirations and the nearest available expiration's chain; it does not place options orders. The sandbox default is explicitly delayed. The returned shortlist ranks only liquidity (valid bid/ask, spread <=25%, volume >=10, OI >=25), and shows exact contract ID, call or put, strike, expiration, bid, ask, volume and open interest.

The UI calls it **Verified listed options — liquidity research**: "verified" here means contract entries came from an available provider response; it is not a claim of an official contractual trade guarantee, execution eligibility or an AI-proven future direction. If Tradier is not configured or no listings qualify, it reports unavailable/no contracts, not invented expirations. Requires server-side `TRADIER_TOKEN`. Uses `KAOS_TRADIER_SANDBOX=true` by default; setting false does not guarantee real-time entitlement, which is determined by the provider subscription.

The directional technical-index research and the liquidity ranking are intentionally separated. A bullish index is not a validated basis for a CALL; a bearish index is not a validated PUT signal. For a future ranked **options prediction**, implement reproducible directional stock forecast with held-out evaluation, time-aware options pricing (bid/ask, IV, Greeks and theta), risk/profit scenarios, realistic fees, verified contract expirations and option market-data freshness. Keep no-order fallback for missing pieces. Avoid claiming guaranteed returns or 0DTE gains.

Additional synthetic tests: `apps/api/test_options_candidates.py`.
