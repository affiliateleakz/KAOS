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

## Owner-only historical directional validation (experimental)

The owner-only endpoint `GET /api/v1/owner/candles/validate-direction?symbol=BTC-USD&asset_class=crypto&seconds=60&horizon=5&fee_bps=10` analyzes up to 5,000 existing permanently archived closed bars from a **single feed**, without making an external provider call. It is controlled by the existing `KAOS_CANDLE_OWNER_USER_ID` and admin role guard.

`kaos_prediction_validation.py` replays the deterministic technical assessment at historical bar closes, using *only* past OHLCV at every decision. Next-bar open is the hypothetical entry, and the selected future bar close is the hypothetical exit. The model uses no overlapping decisions (one entry every `horizon+1` bars), rejects windows spanning missing candle times, makes a 70% chronological training calibration / 30% held-out test split, and purges training decisions whose future outcome reaches into the holdout decision time. The benchmark is a **constant majority-direction baseline** selected from training outcomes only. Held-out scored signals, WAITs, win fraction after a configurable bps cost, and a matched baseline are reported only when enough clean samples remain. All metrics are explicitly **historical price-movement proxies**, not executable equity curves or options returns.

Important caveats: this is validation of the fixed technical heuristic, **not a trained Kronos/CNN/news/social AI model**. Historical news, social observations, and option chains are not point-in-time joined yet, so no results represent the requested all-information stock forecaster. Do not present these metrics as an established buy/sell signal. The intraday contiguous-run requirement can dramatically reduce samples for U.S. stocks with normal overnight breaks. No approach is enabled for live trading and no historical performance numbers are prefilled or invented. If data are insufficient, the endpoint returns a neutral unavailable status.

Run synthetic tests: `python -m unittest discover -s apps/api -p 'test_prediction_validation.py'`. Production validation is not performed merely by passing these synthetic tests. Market data licenses and archive completeness must be verified.

## Point-in-time news/social/filings replay — owner-only experiment

The owner endpoint accepts `include_intelligence=true` on `/api/v1/owner/candles/validate-direction` and fetches at most 5000 stored `kaos_intelligence` observations for the exact asset/class. For each historical decision cutoff it only admits an observation if its **original observed_at (first available to KAOS) and published_at are valid timezone-aware timestamps and BOTH are no later than the decision**. An article published at 9 AM but first ingested at noon cannot influence a 10 AM replay. Missing observation times fail closed. Sources, events, and asset identity are checked; duplicate source/event records cannot multiply votes; data over seven days old are excluded.

The first fusion rule is fixed and inspectable: an existing uncalibrated technical direction requires two independently observed directional **source categories** agreeing with it and no opposing category. Neutral or unavailable evidence cannot become bullish/bearish. Technical-only and fusion filtering share the same historical decision cutoffs; the matched majority-direction baseline is scored only on fusion-selected dates. This is a deliberately conservative **research filter, not a trained AI model or a proven prediction**. Historical headline/news records collected after the fact cannot be backdated into earlier tests.

Output `point_in_time_fusion` contains holdout sample counts and mean after-assumed-cost proxies only when at least 20 matched signals exist. Otherwise it reports `insufficient_matched_fusion_signals` with null metrics; never fabricates wins. This work is owner-only, read-only, no trades, no option contract predictions. Needs real archived data, independent evidence-quality calibration and careful source/date synchronization before member-facing predictions.

Synthetic tests: `test_point_in_time.py` and expanded `test_prediction_validation.py`. These tests establish code behavior, **not strategy performance**.

## Offline trainable multi-factor baseline — development, no production model

Added `apps/api/kaos_multifactor_baseline.py` and `test_multifactor_baseline.py`. This original standard-library logistic-regression research baseline builds samples from complete, contiguous *single-provider* closed candle windows and evidence with independently verified original `observed_at` and `published_at` timestamps no later than each decision. Input features include EMA20/50, RSI14, MACD difference, ATR14, volume ratio, recent returns, point-in-time news/social/filing/options-flow/other directional vote aggregates and explicit missing-category flags.

The model uses a chronological **60% train / 20% validation / 20% untouched test** sequence, with boundaries purged for forward-label overlap. Standardization is fitted on TRAIN ONLY. A fixed model architecture, learning rate and score threshold are used without peeking at test outcomes. Validation and test metrics report class direction accuracy, Brier score, signal coverage, and illustrative cost-adjusted underlying-direction returns; the majority-class comparator uses training labels only. It does not infer option contract P&L or real fills. The scores are **uncalibrated logistic outputs**, not proven win probabilities; calibration, tuning, walk-forward studies and independent live data are prerequisites to marketing any predictions. Missing or insufficient archives return a no-data status.

The private, owner-only, read-only API is:
`GET /api/v1/owner/candles/evaluate-multifactor?symbol=BTC-USD&asset_class=crypto&seconds=60&horizon=5&fee_bps=10`

It reads at most 5000 archive candles + 5000 recorded evidence observations, never downloads provider candles, writes weights, alters models, authorizes trades or returns production signals. No actual model run or accuracy claim is made by adding this code. Results are generated only on request against available real historical archives. The independent always-running recorder and properly licensed market history remain important future prerequisites.

## Paired technical-only vs. multi-factor ablation (November 2026)

The owner-only `evaluate-multifactor` report now evaluates a **technical-only logistic model** (the original eight candle-derived indicators/returns) and the **full technical+point-in-time intelligence model** on the exact same chronological train/validation/test partitions. Both use train-only scaling, fixed optimization settings, a fixed abstention threshold and the same label horizon / assumed costs. Technical-only test metrics are retained even where the news/social archive has no useful historical evidence.

The report includes `technical_only_validation`, `technical_only_holdout`, `point_in_time_evidence_coverage`, and paired descriptive differences in held-out accuracy and Brier score. Positive `holdout_multifactor_minus_technical_accuracy` means the combined model's observed accuracy was higher on that particular test sample; positive `holdout_technical_minus_multifactor_brier` means its Brier score was lower. **Neither means a dependable causal contribution or a profitable trading strategy.**

Crucially, if **zero training examples** have genuinely point-in-time-observed external evidence, `multifactor_comparison_available=false`, full-model `holdout=null` and comparison fields are null. This avoids claiming news/social gains when none of those sources were actually available to train on. Sparse/biased evidence, late discovery, market-regime changes, delayed data, and repeated testing remain major limitations; the full model needs an untouched fresh walk-forward test before any use in member-facing buy/sell or options predictions.

This is not deployed; no trained weights are persisted, no option expirations are recommended, and no live trades are authorized.
