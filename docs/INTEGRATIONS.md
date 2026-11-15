# Integrations: what must be connected

Everything below was read out of the code, not from a design document. Each row states
the environment variable, the code that consumes it, and the behaviour when it is unset.

## 0. You can skip the shell: Admin → API Keys

Open `/admin/api-keys` as an admin. Every integration below is listed there with what it
powers, the site to get the credential from, whether there is a free tier, a live
"Test connection" button, and an encrypted input. Saving writes to
`kaos_integration_secrets`, encrypts with `KAOS_INTEGRATION_VAULT_KEY` (falling back to
`KAOS_BROKER_VAULT_KEY`, then to a key derived from `JWT_SECRET`), and applies the value
to the running process immediately — no redeploy, no restart. Values entered there take
precedence over the same variable in `.env`; removing one restores the `.env` value.

Environment variables still work exactly as before, so both paths are valid. The panel is
just the one that does not require shell access.

The three scanners also have a **no-key** path, so they are useful before anything is
configured:

| Page | No-key source | Notes |
|---|---|---|
| Crypto Scanner & Heat Map | DEX Screener public API for pair search; CoinGecko public API for the bubble map (Coinbase Exchange public stats as fallback) | Pair search runs automatically on page load. Bubble data covers the top 10–100 assets by market cap with 1h/24h/7d changes, cached server-side for 90s because CoinGecko's free tier allows only a few requests per minute; if CoinGecko is rate limited the map falls back to Coinbase majors sized by 24h dollar volume. |
| Stock Heat Map | Yahoo Finance public quote endpoint | Used automatically while Alpaca is unconfigured (`KAOS_STOCK_HEATMAP_FALLBACK=auto`). Grid and bubble views use the same snapshot. Unofficial, rate limited, not licensed for redistribution — add Alpaca for production. |
| Political & Wall Street Trades | SEC EDGAR + Google News RSS | Free; SEC only needs the User-Agent (app name + email) from Admin → API Keys. "Load latest SEC filings" imports real Form 4 insider transactions. The headline panel uses Google News' public RSS index (politics / Wall Street / markets), cached five minutes, and only keeps links on recognised news hosts. Congressional (House/Senate) rows additionally need the compliance switch in the same panel. |

## 1. Required for the application to boot at all

| Variable | Consumed by | If missing |
|---|---|---|
| `MONGO_URL` | `apps/api/db.py` | App starts but every query fails; `GET /api/health` reports `db: false` |
| `DB_NAME` | `apps/api/db.py` | Defaults to `kaos_dev` |
| `JWT_SECRET` | `apps/api/auth.py` | Sessions cannot be signed |
| `ADMIN_EMAIL` + `ADMIN_PASSWORD` | `apps/api/seed.py` | No admin account is seeded; there is no hard-coded fallback |
| `FRONTEND_URL` | CORS / links | Cookie auth from the dashboard is rejected |

Verified locally: with only these set, `uvicorn server:app` boots, seeds indexes/admin/demo
data, and `GET /api/health` returns `{"status":"ok","db":true}`.

## 2. Member-facing services

| Variable | Provider | Consumed by | If missing |
|---|---|---|---|
| `STRIPE_SECRET_KEY` | Stripe | `routes_billing.py` | Checkout returns "billing not configured"; no subscriptions, no affiliate commissions |
| `STRIPE_WEBHOOK_SECRET` | Stripe | `routes_billing.py` | Webhook events rejected; subscriptions never activate |
| `INTEGRATION_PROXY_URL` + `EMERGENT_EMAIL_KEY` | Emergent proxy (default `https://integrations.emergentagent.com`) | `routes_auth.py` | Password reset and email verification silently do nothing |
| `EMAIL_FROM_NAME` | local | `routes_auth.py` | Defaults to `KAOS Trading` |
| `OPENAI_API_KEY` | OpenAI | `routes_ai.py` | AI insights return a configuration error; strategy engine unaffected |
| `GOOGLE_CLIENT_ID` | Google Cloud OAuth client | `routes_auth.py:/google/credential` | Endpoint returns 503; the web Google button cannot sign anyone in |

## 3. Market-data feeds (research and scanners)

| Variable | Provider | Consumed by | If missing |
|---|---|---|---|
| `APCA_API_KEY_ID`, `APCA_API_SECRET_KEY` | Alpaca | `routes_stock_heatmap.py`, `services/collectors/alpaca_stocks.py` | Stock heat map shows "feed not configured" |
| `KAOS_ALPACA_STOCK_FEED` | Alpaca | same | Defaults to `iex` (free tier) |
| `TRADIER_TOKEN` | Tradier | `services/collectors/options_activity.py`, `tradier_options.py` | Options-activity collector refuses to run (requires the token explicitly) |
| `OANDA_API_TOKEN`, `OANDA_ENV` | OANDA | `apps/api/multiasset_sources.py` | FX source disabled; `practice` is the default host |
| `ETH_RPC_URL` | Any HTTPS JSON-RPC (Alchemy, Infura, own node) | `services/collectors/ethereum_whales.py` | Collector exits with `ETH_RPC_URL required` |
| `KAOS_SEC_USER_AGENT` | SEC EDGAR | `sec_13f_collector.py`, `sec_form4_collector.py` | 13F/Form-4 collectors raise at start: SEC requires an identifiable app + contact email |

Crypto candles currently come from Coinbase's public ticker endpoint, which needs no key.
Binance/DexScreener collectors post to `KAOS_API_BASE` and need nothing else.

The crypto bubble map and the political/Wall Street headline strip are keyless by design:
CoinGecko `/coins/markets` (cached 90s), Coinbase `/products/{SYM}-USD/stats` as fallback, and
Google News RSS (cached 5 min). They are research/discovery surfaces, not licensed market data,
so a paid feed can replace them later without changing the pages.

## 4. Execution and broker connectivity

| Variable | Purpose | If missing |
|---|---|---|
| `KAOS_BROKER_VAULT_KEY` | Fernet key that encrypts stored Coinbase API secrets | `PUT /api/v1/broker-connections/coinbase` returns 503 before it ever contacts the broker; live Coinbase orders also return 503 |
| `KAOS_BROKER_VAULT_PREVIOUS_KEYS` | Rotation-only decryption | Old ciphertext cannot be read |
| `KAOS_COINBASE_LIVE_ORDERS` | Master flag for real orders | Must stay `false` until a kill switch and approval gate exist |
| `KAOS_COLLECTOR_KEY` | Auth for collector → API ingest | Ingest endpoints reject |
| `KAOS_API_BASE` | Collector → API HTTPS base | Collectors cannot post results |

Pocket Option is not an API integration: the Chrome extension drives the broker UI. There is
no server credential for it, and the only Pocket Option secret in the tree is `PO_SSID`
(a demo web-session id) used by a research script and explicitly barred from production.

## 5. Blocking third-party dependencies to replace

1. **Emergent Google OAuth is still mounted, but is no longer required.** The web app posts
   the Google Identity credential to `POST /api/auth/google/credential`, which verifies the
   ID token against Google's published keys (signature, issuer, expiry, audience
   `GOOGLE_CLIENT_ID`) and then issues KAOS cookies. That path needs no third party.
   `POST /api/auth/google/session` still forwards an `X-Session-ID` to
   `https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data` and trusts the
   returned `session_token`; nothing in this repo calls it any more. Remove that route (and
   the `session_token` branch in `auth.get_current_user`) once you have confirmed no deployed
   client uses it — it accepts an identity asserted by a demo backend outside KAOS control.
2. **Transactional email defaults to the Emergent proxy.** Overridable via
   `INTEGRATION_PROXY_URL`, which is why it is listed in §2 rather than here.
3. **Stripe price objects are created on demand** (`stripe.Price.create` inside checkout).
   That keeps the plan table in Mongo authoritative and needs no dashboard setup, but it means
   every checkout mints a new Price object and the product name comes from the plan metadata.

## 6. Not environment variables, still required to go live

- Production host for `apps/api` (the historical target is cPanel Passenger → `a2wsgi(server.app)`;
  confirm which runtime actually serves `api.tradingwithkaos.com`).
- Static host for the `apps/web` build plus a `/api` reverse proxy so cookies stay first-party.
- DNS + TLS for the API and site domains, and the same domains allow-listed in Stripe.
- A Stripe webhook endpoint at `POST /api/billing/webhook` with its signing secret.
- MongoDB (Atlas or self-hosted) with authentication enabled; the compose file runs it unauthenticated.
- Chrome Web Store listing and the extension `key` that pins ID `gbobopmnjgeeegniphckfpalhnebapjm`.
- Rotated secrets for anything that ever lived in the cPanel tree (see `docs/SECURITY_AUDIT.md` S3).

## 7. Minimum set for a working local demo

```
MONGO_URL, DB_NAME, JWT_SECRET, ADMIN_EMAIL, ADMIN_PASSWORD, FRONTEND_URL
```

Nothing else is needed to boot, log in, and walk every page. Billing, email, AI, scanners and
brokers each fail closed with a visible message until their keys are supplied.
