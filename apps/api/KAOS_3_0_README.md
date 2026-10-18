# KAOS Trading 3.0 — Opportunity Radar foundation

This development build adds an authenticated, research-only intelligence ingestion and opportunity ranking API to the existing 2.0.2 backend. It does NOT add live data providers, web UI, model training, broker execution, or a working 100-market collector.

## Routes
- `POST /api/v1/intelligence/ingest`: authenticated server-side collector batch using `X-KAOS-Collector-Key` and env `KAOS_COLLECTOR_KEY` (keep key secret). Max 250 observations/request.
- `GET /api/v1/intelligence/opportunities?asset_class=crypto`: active-member research feed based on ingested evidence only.
- `GET /api/v1/intelligence/status`: source and collector configuration status.

Records are stored in MongoDB collection `kaos_intelligence` and deduplicated by source + event_id. Event timestamps must be offset-aware; `observed_at` is when KAOS first saw the event and `published_at` is when it became public. No score represents a win probability. The API deliberately returns empty results until a real provider supplies data.

## Before deployment
1. Back up current production code and database. Compare this dev archive to deployed code; do not overwrite later hotfixes blindly.
2. Configure a long random `KAOS_COLLECTOR_KEY` on the backend and separately on a trusted collector service; never in browser code.
3. Add MongoDB unique index on `(source,event_id)` and indexes on `(asset,observed_at)` and `(asset_class,observed_at)`.
4. Implement provider adapters for market candles, options chains, DEX pools, filings, social and news; respect licensing and rate limits.
5. Add quotas, API rate limits, schema/source URL validation, monitoring, and out-of-sample model evaluation before production rollout.
6. Keep live broker execution disabled for these intelligence signals until separately authorized and tested.
