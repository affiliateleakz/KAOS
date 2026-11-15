# Radar scans, social sources and evidence review

## What was disconnected

The previous Radar Refresh button queried saved observations; it did not run the
separate social collection worker. cPanel releases included the news helper but
not the Bluesky, SEC transaction or Ethereum adapters. The old local financial
classifier requires separately installed model weights and was not a general
Radar scan. Bluesky could also treat newly indexed old posts as fresh mentions.

## Current workflow

Use **Opportunity Radar → Scan sources + AI** with up to five `SYMBOL:class`
entries. Example: `AAPL:stock, NVDA:stock, BTC:crypto, ETH:crypto`.
Supported classes are stock, etf, option, crypto, dex, forex and future. Direct
source coverage differs by adapter; other market categories can use recent
observations from the separately deployed collectors.

The request gathers bounded source samples and recent saved evidence. A source
failure is shown separately from a successful search with no matching results.
Failures never become a zero-mention claim or a synthetic observation. Raw
social/quote/transfer/disclosure records are neutral evidence; an AI report is
not added back as an independent confirming source or an execution instruction.

The owner can use **Admin → Radar Sources & AI** to enable/disable sources and
save write-only credentials. Blank fields retain saved values. Values are
Fernet-encrypted in `radar_provider_settings` using the existing private server
vault (`KAOS_COMMERCE_VAULT_KEY`, or `~/.kaos/commerce.key`). Initialize/verify uses
the existing safe vault helper and never replaces an existing key. The Radar
settings and private scan reports require authenticated roles; settings are
super-admin-only and scans require scanner entitlements.

### Sources and actual scope

| Source | Configuration | Scope |
|---|---|---|
| Reddit (priority) | `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USER_AGENT` | Official OAuth application access; up to 25 recent search results per ticker, exact symbol/cashtag matching. API approval and permissions must be valid. Not a full comments/firehose scan. |
| X (priority) | `X_BEARER_TOKEN` | Official recent search; up to 10 cashtag posts per ticker, reposts excluded. Requires a plan entitled to recent search. |
| Bluesky | Public access, or `BLUESKY_IDENTIFIER` and `BLUESKY_APP_PASSWORD` | Up to 50 search results; authenticated PDS/AppView supported. Actual post creation time takes precedence over indexing time. Public endpoint availability is not assumed. |
| Facebook | `FACEBOOK_PAGE_ID`, `FACEBOOK_PAGE_ACCESS_TOKEN`, `FACEBOOK_GRAPH_VERSION` | Up to 25 posts from the authorized Page, reused across the scan watchlist. No claim to search all personal Facebook posts. |
| News | Existing keyless headline feed | Ticker headlines; actual source/discovery times retained. No full article scraping. |
| Market snapshot | Existing Coinbase public ticker / Yahoo chart metadata | One quote snapshot for supported stock/ETF/crypto tickers. Not a full technical chart strategy scan. |
| Insider transactions | `SEC_USER_AGENT` including organization/contact email | SEC ticker-to-CIK lookup, submissions and latest recent Form 4 primary XML. Only reported non-derivative P/S are parsed, retaining transaction/disclosure timing. |
| Ethereum whales | `ETH_RPC_URL` | One safe block, native ETH transactions valued at least 500 ETH. No BTC/ERC-20 scan, wallet ownership labels, exchange inflow/outflow claims or inferred buy/sell intent. Include ETH:crypto. |
| Government | `QUIVER_API_KEY` | Selected US stock/ETF Congressional disclosures via Quiver's documented historical Congress endpoint. Report date, transaction date and value range are retained. Not every government official or real-time trading. API access for the intended use must already be arranged. |

Credentials can be saved in the admin panel instead of environment variables.
Encrypted saved settings take precedence. No subscriptions are purchased, no
accounts are opened and no broker orders or transfers are sent by these adapters.

Official reference endpoints:
- https://developers.reddit.com/ / https://www.reddit.com/dev/api/
- https://docs.x.com/x-api/posts/recent-search
- https://docs.bsky.app/docs/api/app-bsky-feed-search-posts
- https://developers.facebook.com/docs/pages-api/posts/
- https://www.sec.gov/search-filings/edgar-application-programming-interfaces
- https://api.quiverquant.com/datasets/congress-trades

### AI

Configure the OpenAI API key and model in the admin panel, or set
`OPENAI_API_KEY` and `KAOS_RADAR_MODEL` (default `gpt-4.1-mini`). One Responses API
request reviews a balanced, bounded evidence sample, with no tools or browsing.
The model must return structured results for the requested assets and cite known
evidence IDs belonging to those assets. Unknown citations, missing assets,
incomplete output or unsupported high priority fail validation. Missing model
configuration is shown explicitly; raw source collection can still succeed.

Evidence sampling is balanced across assets and source providers so frequent
social posts do not crowd out less frequent insider, whale or government data.
The UI reports how many observations were reviewed; the full collected evidence
remains visible. Source content is untrusted input, not executable instructions.
Research priority is not a probability or trading authorization.

## Bounds and hosting

- At most five symbols, nine requested adapters and four concurrent outbound
  requests per scan; SEC requests are spaced at least 0.2 seconds apart.
- Source collection has a 24-second total budget, with explicit timeout states;
  AI has a 15-second HTTP timeout and 2,600-output-token cap.
- Identical reports are cached five minutes, keyed to user, watchlist, sources,
  AI choice and provider configuration. Mongo atomic leases prevent concurrent
  duplicates across workers. New watchlists have a per-user one-minute cooldown.
- Auto scan is opt-in, every five minutes while the Radar page is visible, and
  its timer is removed when leaving the page. Opening the page does not silently
  start a paid AI request. This is not a background cron/firehose service.
- Reports older than seven days are pruned during a new scan. No ASGI startup
  hook or new database index/migration is required for lease correctness.
- Provider rate limits, plan eligibility and live availability remain external
  prerequisites. A bounded sample is not all posts or all market activity.
- cPanel packages include the required pure-Python collector helpers. The
  activation wrapper permits the narrow authenticated Radar scan/admin routes;
  payment, arbitrary collector ingestion and order restrictions remain intact.

## Bubble motion

The browser collision simulation now maintains a gentle minimum drift and wander
instead of settling at zero velocity. A single filtered bubble also animates.
Explicit pause, reduced-motion preference, hidden tabs and offscreen maps retain
resource/accessibility controls; no server requests drive animation.

## Validation

Mocked-provider tests cover Reddit OAuth, X access/rate-limit failures, authenticated
Bluesky and old-post timing, authorized Facebook scope, native-ETH safe-block
reads, SEC P/S XML and Congressional disclosure dates/stable IDs. API tests cover
scan caches/leases, cooldowns, owner/member permissions, encryption/redaction,
AI citations and balanced evidence. Browser fixtures cover source statuses,
social filtering, optional auto-scan cleanup, admin settings and mobile layout.
These checks do not establish that production credentials or live provider access
are configured; run a hosting scan and inspect each returned source status.

## Signal dashboard: separate horizons

Radar opens on **Market opportunities**, with a keyless Coinbase/Yahoo candle scan
for up to five crypto, stock or ETF symbols. Closed 15-minute bars feed an EMA9/21
and 20-bar breakout rule, with ATR reference stop/target levels and a 45-minute
research horizon. This is a technical baseline, **not a trained AI forecast or a
validated profitable strategy**. The existing cited AI evidence workspace is now
lazy-loaded under Advanced evidence; paid AI/source calls never run on opening
this dashboard. No automatic orders are placed.

Missing, stale, malformed or incomplete recent bars produce WAIT. Free providers
can refuse requests or delay data. Stocks require a complete recent 20-bar
session, so early-session scans may wait. Five-minute shared Mongo caches and
per-symbol 20-second leases limit repeated outbound work across members/workers.

**Bot entries** reads only the signed-in user's recorded SIGNAL_GENERATED entries,
retains exact platform/OTC identifiers, and excludes simulated, future, expired or
unknown-expiry records. Only explicit 30s/45s expiries are accepted. Entries expire
in the browser too. These are extension-reported, not independently verified;
extension versions that do not upload signals will show an empty state. Opening
a broker chart does not itself guarantee telemetry. This view is not a new
seconds-long prediction service or an instruction to chase an existing entry.

A separate trained longer-horizon AI model is not deployed by this change. The
broker model cannot be applied to 15-minute stock/crypto candles without new
training and chronological validation. Social, whale and delayed disclosure
sources remain optional research context rather than mandatory signal gates.
