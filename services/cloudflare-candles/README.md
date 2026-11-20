# KAOS Cloudflare Workers + private R2 candle archive

**Status:** deployment-ready *draft source*, not deployed or connected to any Cloudflare account. This design avoids operating a VPS and avoids a 500MB hosted SQL database cap for long-term raw candles. Existing KAOS API currently depends on MongoDB for users, research reports, AI results and other app data. This Worker only replaces the need for a continuously running **market candle recording process** and adds a private long-term R2 data store; it does not automatically migrate the existing KAOS database.

Cloudflare official references:
- Scheduled Workers / Cron Triggers: https://developers.cloudflare.com/workers/configuration/cron-triggers/
- R2 storage bindings: https://developers.cloudflare.com/r2/get-started/workers-api/
- Worker free/paid limits: https://developers.cloudflare.com/workers/platform/limits/
- R2 pricing: https://developers.cloudflare.com/r2/pricing/

## The architecture

Cloudflare triggers `scheduled()` every **five minutes**. The Worker reads up to 20 configured markets per deployment: stocks/ETFs from your **existing Alpaca credentials** (IEX by default; subscription required for SIP), Coinbase Exchange crypto, or authorized OANDA FX. It validates that the bar has **finished**, checks OHLCV and timestamps, and writes an immutable-history, deduplicated JSON file per source, market, interval and UTC calendar day to an R2 private bucket. A repeated run merges already-stored bars and skips no-op writes, so it does not create a separate object for every candle.

Example R2 path:
`candles/v1/alpaca_iex/stock/AAPL/60s/2026-11-20.json`.

R2 will be **private**: the Worker responds with HTTP 404 and publishes no member-readable object URLs. The app should expose authenticated, rate-limited backend APIs rather than making R2 public. The optional `KAOS_API_BASE` and `KAOS_COLLECTOR_KEY` secrets mirror each batch into KAOS's existing authenticated Mongo archive. Mirroring is optional and does **not** make Mongo unnecessary for the rest of KAOS.

The cron is periodic, not a true live WebSocket feed or 1-second trading quote. Minute bars during stock/FX closures do not exist and must not be fabricated. Cron runs can be delayed, fail or overlap; R2 read-merge-write is **not atomic across concurrent executions**. Large-scale production requires collision-safe sharding/serialization (e.g., Cloudflare Queues or a Durable Object), backfill audits, quota monitoring and provider entitlement review.

## Cloudflare account setup

1. Create/sign into an account at https://dash.cloudflare.com. Enable R2 (Cloudflare might request a payment method, even if initial usage fits the free tier).
2. On your computer with Node.js installed, run `cd services/cloudflare-candles`, `npm install`, then `npx wrangler login`. Cloudflare login is a browser authorization step that only you can complete.
3. Create the private bucket (once): `npx wrangler r2 bucket create kaos-candle-archive`.
4. Store your existing Alpaca credentials **as Cloudflare Worker secrets**, never in GitHub or wrangler vars:

```bash
npx wrangler secret put APCA_API_KEY_ID
npx wrangler secret put APCA_API_SECRET_KEY
```

Optional forex, provided you have access: `npx wrangler secret put OANDA_TOKEN`.

Optional KAOS database mirror, provided PR #62's API is deployed and matching server-side collector key is set:

```bash
npx wrangler secret put KAOS_COLLECTOR_KEY
```

Add `"KAOS_API_BASE":"https://api.tradingwithkaos.com"` to `vars` in `wrangler.jsonc` **only after** the collector ingestion API has been deployed. If not set, R2 storage still works; KAOS's existing Mongo-backed predictor will **not** see the new R2-only history yet.

5. Review and edit `wrangler.jsonc`'s `MARKETS_JSON`, `ALPACA_FEED`, and 5-minute cron schedule. The example starts with AAPL, NVDA, SPY, BTC-USD, ETH-USD. These are exact supported data source symbols, not Pocket Option OTC prices. Do not put secrets in `MARKETS_JSON`.
6. Run `npm test`, then `npx wrangler deploy`. Scheduled triggers run after deployment; `npx wrangler tail` streams your Worker logs. Verify that a new dated R2 object appears after a scheduled run, and check its source, candle count and most recent closed timestamp. There is no need to give KAOS a Cloudflare root API token. Use scoped permissions for GitHub Actions if configuring CI deployment later.

## Quotas and cost management

Cloudflare R2's current published Standard storage free tier includes 10 GB-month, a monthly allowance of Class A writes and Class B reads; check live pricing as quotas can change. This design reduces R2 write amplification by **merging bars into daily files**. A five-minute schedule across 100 markets is approximately **864,000 market-cycle opportunities per 30-day month** (100 x 12 x 24 x 30), before skipped no-op writes, cross-day objects and retries. This can approach free Class A limits and still incur paid Worker/runtime/provider usage. The sample is intentionally 5 markets and capped at 20 per Worker. Use more than one Worker/shard for larger universes and monitor request quotas, API limits, storage growth and collision-safe scheduling. Cloudflare free-tier CPU/runtime restrictions may require the Workers Paid plan for larger market universes.

## Tests and current integration boundary

```bash
cd services/cloudflare-candles
npm test
```

Local tests mock R2 and provider calls. Actual provider network access and your personal Cloudflare deployment cannot be verified from CI alone.

The prior `services/collectors/continuous_candle_worker.py` remains an optional VPS alternative; **do not run both** against the same markets without clear duplicate policies and one authoritative source. The Opportunity Radar and experimental prediction endpoints still require approved model artifacts and sufficient recent **Mongo archived** data; enabling Cloudflare **without** the mirror does not automatically make member AI predictions live.

This Worker does not authorize trades, supply calibrated AI accuracy, or provide options contract recommendations.
