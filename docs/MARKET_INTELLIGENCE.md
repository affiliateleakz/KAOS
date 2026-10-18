# KAOS Market Intelligence Center

Member research workspace for stocks, crypto, social attention and options activity. It is a
presentation and aggregation layer over data KAOS is actually allowed to read. **It cannot place,
modify or cancel a broker order**, and every response is marked `research_only`.

## What ships

| Area | Backend | Frontend |
|---|---|---|
| Scanner catalog + source health | `GET /api/v1/intelligence/center/catalog` | Overview tab |
| Crypto scanner (live public candles) | `GET /api/v1/intelligence/scanners/crypto` | Crypto tab |
| Stock/ETF scanner (owner-supplied Alpaca key) | `GET /api/v1/intelligence/scanners/stocks` | Stocks tab |
| Social attention (stored collector observations) | `GET /api/v1/intelligence/scanners/social` | Social tab |
| Options research + SPY 0DTE snapshot list | `GET /api/v1/intelligence/options/research` | Options tab |
| Watchlists | `GET/POST /api/v1/intelligence/watchlists`, `POST/DELETE .../{id}/symbols`, `DELETE .../{id}` | Watchlists & Alerts tab |
| Research alerts | `GET/POST/DELETE /api/v1/intelligence/alerts`, `POST /api/v1/intelligence/alerts/evaluate` | Watchlists & Alerts tab |
| Admin source registry | `GET /api/admin/intelligence/sources`, `PUT .../sources/{provider}` | Admin → Data Sources |

Supporting modules: `apps/api/kaos_market_intel.py` (pure scanners/fusion), `kaos_rate_limit.py`
(per-member sliding windows), `market_data.py` (Coinbase + Alpaca adapters), `routes_market_intel.py`,
`routes_intel_admin.py`.

## Three data paths, never mixed

1. **Request-time public candles.** Crypto: Coinbase Exchange public candles (`60/300/900` seconds,
   max 8 symbols per scan). These rows are live market data; each row has `as_of` (bar close) and the
   response carries `source`, `source_url`, `fetched_at` and a coverage note.
2. **Ingested collector observations.** Social and options rows are read from `kaos_intelligence`,
   which only the out-of-process collectors write to with `KAOS_COLLECTOR_KEY`. Counts are *stored
   observations per ticker*, not platform-wide mentions.
3. **Provider-gated.** Stocks/ETFs need server-side Alpaca market-data keys
   (`APCA_API_KEY_ID`, `APCA_API_SECRET_KEY`, optional `KAOS_ALPACA_FEED=iex|sip`). Without them the
   endpoint returns `data_status: "provider_not_configured"` with `required_env` and **no rows**.

Nothing is simulated. A provider failure produces `rows: []` plus an `errors` list; an empty social
or options feed produces an explicit empty state.

## Scanner metrics

Per symbol (`MIN_BARS = 25` completed bars): last close, 5/15-bar change, volume ratio vs the prior
20-bar median, volume z-score, ATR%, bar-range ratio, EMA20/EMA50 trend (only with 50+ bars),
support/resistance proximity, price-action class, structure (`breakout`, `breakdown`,
`failed_breakout`, `failed_breakdown`, `inside_range`) and explicit signal codes with their evidence
text. `attention_score` is a capped additive heuristic; `score_type` says it is **not** a probability.

## Entitlements

* Scanner endpoints and alerts: `entitlements.scanners` (Pro/Ultimate). Free members receive `403`
  with a plain-language upgrade message; the UI renders an upgrade card.
* Watchlists are available to every signed-in member, limited per tier: Free 2 lists / 15 symbols,
  Pro 10 / 50, Ultimate 25 / 100. Limits are enforced in the API, not the client.

## Rate limits and isolation

* Per-member sliding windows (process-local): 12 scans/minute and 60 writes/minute. `429` responses
  include `Retry-After`. A multi-worker deployment needs a shared store (Redis) for a global limit.
* Every watchlist/alert query is scoped by `user_id` from the authenticated session; cross-member
  access returns `404`. There are unique indexes on `(user_id, id)`.
* Alert evaluation runs only when the member presses *Run checks*. It re-scans a bounded symbol set,
  stores `last_checked_at` / `last_triggered_at`, and sends at most one in-app notification per alert
  per hour. No background delivery is claimed.

## Options research boundaries

The authorized collector stores chain snapshots (`reported volume`, `open interest`, `bid/ask
spread`) and never trade side, implied volatility or Greeks. The API therefore reports
`metrics_unavailable: [implied_volatility, delta, gamma, theta, vega, trade_side]` instead of
estimating them. OCC contract symbols are parsed for root/expiry/type; `same_day_expiration` means
the parsed expiry equals today (UTC), which is how the SPY 0DTE list is produced.

## Admin controls

`GET /api/admin/intelligence/sources` lists each integration, whether its credentials are present
(booleans only — values are never returned), the last stored observation per collector provider and
an enable flag. `PUT /api/admin/intelligence/sources/{provider} {enabled}` toggles the source,
writes it to the `intel_sources` setting and records an audit log entry. Disabling a source makes the
member scanners return `data_status: "disabled_by_admin"`; stored observations are not deleted.
Only free/owner-supplied data is registered — there is no paid provider and no auto-charge.

## Tests

```bash
cd apps/api && PYTHONPATH=../../packages/kaos-core python -m pytest -q test_kaos_market_intel.py test_routes_market_intel.py
cd apps/web && CI=true npx craco test --watchAll=false
```

Covered: candle validation, breakout/failed-breakout/trend rules, insufficient-history behaviour,
provider-error honesty, symbol validation, entitlement 403, member isolation, watchlist tier limits,
alert validation/trigger/dedupe, rate limiting, admin credential-presence redaction, and the pure
frontend helpers (symbol parsing, formatting, sorting, sparklines, alert payloads).

## Known limitations

* Stock scanner is only as live as the owner's Alpaca key; the IEX feed is a single exchange.
* Social coverage is limited to what the Bluesky collectors sample. Reddit/X/Stocktwits are not
  integrated and are not shown as if they were.
* Options data is a filtered nearest-expiration snapshot, not market-wide flow.
* Alert notifications are in-app and on-demand; there is no scheduler or email/push delivery yet.
* Rate limits are per API process.
* The scanner is not execution-approved: no strategy validation, risk engine or order path is
  connected to it.
