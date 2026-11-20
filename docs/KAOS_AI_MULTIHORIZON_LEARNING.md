# KAOS AI Research — multi-horizon and catalyst learning (phase 1)

Status: research code, not a trained or deployed signal model.

## Product objective
Learn when **BUY, SELL, or NO TRADE** would have worked, per market, symbol, timeframe, strategy setup, and holding duration. Compare net, risk-adjusted outcomes after market friction and volatility. Do not optimize for raw accuracy alone.

## Horizons and timeframes
Candidate horizons in seconds: 5, 10, 15, 30, 60, 300, 900, 3600, 86400, 604800. These are initial research presets, not limits: models must store the exact horizon. Requested 5/15/30/60-second candle timeframes are only legitimate if the actual broker/source provides timestamped data at the required resolution. A 1-minute candle must **never** serve as proof of the entry or expiry price for a 5/10/15-second contract. Stocks, forex, crypto, options contracts and Pocket Option must keep broker-specific data and return math. Market closure means NO RESULT, not a fabricated fill.

## Feature families (as-of snapshots)
1. **Price action and chart patterns:** trend/regime, HH/HL and LH/LL sequences, support/resistance, break-and-retest, false breakout, continuation/pullback, candlestick rejection/engulfing, volume confirmation, VWAP, EMA slope, ATR/range, liquidity levels, multi-timeframe agreement.
2. **Microstructure:** bid/ask spread, quote freshness, volume, order-flow imbalance, liquidity/depth, volatility, trading session, gaps, trading halts.
3. **News/catalysts:** company news and sentiment, economic release calendar and surprises, Fed/rates, earnings/guidance, analyst revisions, sector/index sympathy, SEC 8-K/10-Q/10-K/Form 4, institutional 13F.
4. **Short/positioning:** dated reported short interest, days-to-cover, borrow fee/utilization (when licensed), fails-to-deliver, options open interest, put/call activity, IV/skew, unusual contracts, gamma exposures where justifiable.
5. **Cross-asset and risk:** index/sector strength, BTC/ETH correlations, FX rates, yields, commodities, float/market cap, corporate actions, seasonality and social interest with source quality.

## Critical timestamps
Every event needs event time, first published time, first **actually received/available** time, source, symbol mapping, revision, quality and provenance. A historical database timestamp cannot be substituted for original public availability. Short-interest numbers often describe an earlier settlement date and are publicly published later; training MUST use publication time, not settlement time. SEC filings and news corrections likewise must not leak future data into past decisions.

## Training and validation
- Collect immutable observations, versioned feature snapshots and post-horizon outcomes separately.
- Produce multi-target labels from exact real bid/ask quotes or broker settlement rules; allow NO TRADE.
- Track train/validation/untouched holdout chronologically, with embargo around overlapping multi-horizon outcomes.
- Report net returns, drawdowns, base rates, sample counts, coverage, slippage, calibration and stability by regime and asset. Avoid declaring a model successful based on a small holdout.
- Train separate specialized models for stocks, crypto, forex, PO short expiry and options contracts; use shared research infrastructure without assuming one model transfers unchanged across markets.
- Log every prediction with model version and outcome provenance. Only promote validated models after reproducible paper trading and explicit owner approval.

## Existing components to integrate next
- `apps/api/candle_research_worker.py`: closed spot, stock and forex bars (does not supply historical bid/ask microquotes).
- `services/collectors/market_collection_runner.py`: news, social, SEC, 13F, options activity and crypto. Implement event snapshot versioning and timed point-in-time joins.
- `apps/api/kaos_ai_trainer.py`: old 30-second, 104-feature XGB/LGBM trainer. Do not silently feed mixed-horizon observations into its current 30-second dedup buckets. A new trainer contract must key (market, symbol, timestamp, timeframe, horizon, model version) and use the vetted research dataset.
- `apps/api/routes_ai_outcomes.py`: current trusted quote settlement path; PR #51 is a partial closed-candle verification bridge. It must remain separate from the research dataset built here until integration tests pass.

## Verification and scope
Initial module: `research/multi_horizon_dataset.py`. Tests: `PYTHONPATH=research python -m pytest -q research/test_multi_horizon_dataset.py`. This starter labels quote-based long/short gross movement less an explicit fee estimate; broker-specific funding, borrow, payout schedules, stops, forced expiry and realized fills are future requirements. No models trained, no trading turned on, no live market performance claim.
