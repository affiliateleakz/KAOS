# KAOS Trading 3.0 v0.3 — multi-market collector integration DEVELOPMENT BUILD

## Changes relative to v0.2
- `collectors/alpaca_stocks.py`: real Alpaca market-data API adapter for US stocks/ETFs using completed 1m candles; validates feed, credentials, stale data, pagination and source timestamps.
- `collectors/tradier_options.py`: Tradier read-only options expiration/chain scanner. Liquidity and volume/OI are neutrally labeled; no options direction claim or broker orders.
- `collectors/collector_common.py`: authenticated KAOS server-only intake, up to 250 observations per request, HTTPS safeguard.
- `collectors/market_collection_runner.py`: configurable multi-provider runner (up to 150 stocks, 100 options underlyings, 150 crypto pairs, 20 DEX search terms), dry-run and opt-in server-loop modes.
- `collectors/market_universe.example.json`: editable sample universe.
- `backend_foundation/kaos_source_health.py` and `/api/v1/intelligence/health`: reports freshness of ingested observations; does not certify real-time feeds.
- `site/tradingwithkaos.com/frontend/src/pages/dashboard/OpportunityRadar.jsx`: website member dashboard data-source health panel.
- `kaos-mobile/app/index.tsx`, `kaos-mobile/src/api.ts`: mobile source health indicator using the same backend.
- Preserved prior extension launcher, site route, mobile screens, broker and research code.

## Validation in this environment
- Offline collector suite: 21 unit tests pass (mock HTTP requests; no external credentials).
- Backend source health: 3 unit tests pass.
- Python compilation: source modules compile.
- Frontend JSX and mobile TS/TSX: parser/transpilation syntax checks pass (does not substitute for complete dependency builds).
- ZIP integrity: verified after packaging.

## Not complete
- No credential-backed live Alpaca/Tradier/Binance/DexScreener API calls have been executed by this build, and no results are claimed.
- No integrated deployment to website, extension, Android, iOS, or cloud. No Android APK/iOS IPA.
- No production sign-in/Google OAuth on mobile, push alerts or trading from mobile.
- No raw 100+ market candle lake, incremental backfill, full option chain archive, news/social/insider/politician flows, large-scale model training, or automated trade performance proof.
- All market research remains read-only and separate from execution.

See `collectors/README_KAOS3_COLLECTORS.md` for setup, keys, rate-limit constraints, and operational caveats.

## v0.4 — GDELT headlines and SEC filing discovery (2026-10-16 development)
- Added `collectors/gdelt_news.py` and `collectors/sec_edgar_filings.py`, with explicit validated ticker/topic and ticker/CIK mappings.
- Integrated both adapters into `collectors/market_collection_runner.py`, with separate minimum polling intervals (news 15 min, SEC 60 min).
- Added `filing` evidence source in research API, added `gdelt` and `sec` source-health groups, and fixed opportunity ranking so neutral context alone cannot be promoted into a directional candidate. Evaluation uses source time, so repolling does not magically refresh old publications.
- Website and Android/iOS app: added source-evidence filters for News, SEC filings, and Form 4 discovery, with explicit source time caveats.
- Added offline tests for public GET endpoint behavior, GDELT first-seen times, SEC CIK identity validation, XML-path safety, neutral Form 4 semantics, polling controls, and source-age-based ranking.
- **Not yet implemented:** actual insider transaction extraction, 13F portfolio disclosures, Congressional disclosures, full text news sentiment, social scanning, historical headline archive, production ingestion, mobile app native binaries, push notifications, broker-integrated trading or verified prediction performance.
- See `collectors/README_NEWS_SEC_V04.md` for commands, API caveats and provider policies.


## v0.5 — Whale & reported insider transactions (2026-10-16 development)
- Added opt-in, research-only native Ethereum safe-block value scanner with persistent incrementing block cursor. The cursor is committed only after KAOS acknowledges ingestion; does not claim ERC-20 or all-chain coverage.
- Added SEC Form 4 primary XML parsing for non-derivative `P/A` purchase and `S/D` sale records on configured company CIKs. Transaction date and filing acceptance date are distinct; both are *neutral context* to Opportunity Radar. Existing SEC filing discovery still works.
- Expanded website/mobile evidence filters and source-health provider recognition; no modifications to existing trade execution. See `collectors/README_WHALES_V05.md`.
- Offline tests pass (43 collector tests and 7 backend research tests). No live provider credentials/network tests, production web/mobile builds, or deployment completed.

## v0.5.1 — Free-source policy
- Removed proprietary paid-data client, mobile promotion, documentation, and its test; no proprietary provider integration.
- Keep open/public Ethereum and SEC research adapters and existing read-only options research. Verify API terms and source quality even when access is free.

## v0.6 — SEC 13F + public social evidence (development only)
- Two new optional free-source adapters: SEC manager 13F-HR information-table XML, and Bluesky public author-feed cashtags.
- New evidence is neutral and timestamped. SEC quarter-end holdings are delayed; social sampling covers only configured public accounts.
- Added website/mobile evidence filter and backend source-health labels; existing extension/trading engine files unchanged from v0.5.1.
- See `RELEASE_3_0_V0_6.md` and `collectors/README_13F_SOCIAL_V06.md` for limitations and configuration.

## v0.9 additions
See `collectors/README_SOCIAL_SQUEEZE_V09.md` for opt-in public Bluesky search, local-only short-interest review, and conflict-aware research ranking. No paid Unusual Whales integration.
