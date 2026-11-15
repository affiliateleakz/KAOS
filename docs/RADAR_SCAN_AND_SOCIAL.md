# Radar scans, social sources and evidence review

## What was disconnected

The previous Radar Refresh button queried saved observations; it did not run the
separate social collection worker. cPanel releases included the news helper but
not the Bluesky, SEC transaction or Ethereum adapters. The old local financial
classifier requires separately installed model weights and was not a general
Radar scan. Bluesky could also treat newly indexed old posts as fresh mentions.

## Current workflow

Radar now has five simple top tabs: **News**, **Trending**, **AI Signal**,
**Sentiment**, and **Bot Entries**. News opens first. Each tab shows only its own
controls/content. Technical model/source details are collapsed. The older
multi-source research workspace is no longer mounted on the member screen.

Use News for headlines, Trending for keyless ApeWisdom stock-mention rankings, or choose one
ticker and market in AI Signal. The analysis model still uses available data
from all configured sources; its internal sources are not separate member setup
steps. Owner configuration and training remain under Admin → Radar Sources & AI.

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
| Alpha Vantage | Admin write-only API key, or `ALPHAVANTAGE_API_KEY` | Market headlines cached globally per key for one hour, at most 20 KAOS requests per UTC day. Provider free-plan limits/access still apply. The same headlines can feed local KAOS analysis; third-party sentiment scores are not substituted for KAOS inference. |
| News | Existing keyless headline feed | Ticker headlines; actual source/discovery times retained. No full article scraping. |
| Market snapshot | Existing Coinbase public ticker / Yahoo chart metadata | One quote snapshot for supported stock/ETF/crypto tickers. Not a full technical chart strategy scan. |
| Insider transactions | `SEC_USER_AGENT` including organization/contact email | SEC ticker-to-CIK lookup, submissions and latest recent Form 4 primary XML. Only reported non-derivative P/S are parsed, retaining transaction/disclosure timing. |
| Ethereum whales | `ETH_RPC_URL` | One safe block, native ETH transactions valued at least 500 ETH. No BTC/ERC-20 scan, wallet ownership labels, exchange inflow/outflow claims or inferred buy/sell intent. Include ETH:crypto. |
| Government | `QUIVER_API_KEY` | Selected US stock/ETF Congressional disclosures via Quiver's documented historical Congress endpoint. Report date, transaction date and value range are retained. Not every government official or real-time trading. API access for the intended use must already be arranged. |

Credentials can be saved in the admin panel instead of environment variables.
Encrypted saved settings take precedence. No subscriptions are purchased, no
accounts are opened and no broker orders or transfers are sent by these adapters.

Official reference endpoints:
- https://www.sec.gov/search-filings/edgar-application-programming-interfaces
- https://api.quiverquant.com/datasets/congress-trades

### KAOS-owned AI and sentiment

Radar makes **no OpenAI request** and no longer offers an OpenAI key/model in
its provider settings. Historical encrypted OpenAI settings are ignored. The
separate short-expiry broker AI is not repurposed for market opportunities.

`kaos_radar_ai.py` is a local supervised logistic evidence model with a versioned
23-feature schema: price returns, trend/range, relative volume/volatility, news
and social sentiment/activity, insider and Congressional disclosure activity,
whale activity, source coverage and aggregate mention counts/rank with explicit provider and comparison availability flags. Available records must match the symbol and
asset class, have valid availability timestamps, and be deduplicated. Missing
feeds remain gaps, never invented directional observations.

Text sentiment uses bundled **VADER 3.3.2**, running locally with no external AI
service or runtime model download. It is English lexical sentiment rather than
full article comprehension or a trained financial language model; sarcasm,
financial vocabulary and multilingual sources can be misread. Model scores
are not calibrated win probabilities. Model feature contributions are
associations, not causal explanations.

Scans save immutable evidence snapshots per asset/closed bar. Later actual
closed candles label 45–60 minute forward moves; missing/session-gap candles
cannot be bridged, and moves under 10 basis points are excluded from directional
training. This threshold is not a fee/slippage model. Training requires at least
120 non-overlapping labeled samples (80 training, 30 held-out, both directions),
uses at most 2,000 recent rows, and purges outcomes crossing the chronological
holdout split. Normalization is fitted on training rows only.

**Admin → Radar Sources & AI** shows training progress, candidate metrics and
separate stock/crypto train buttons. Training is manual, bounded, runs off the
request event loop, and has a five-minute group cooldown. A candidate must pass
historical gates (balanced directional accuracy >=55%, at least 15 strong-score
signals with >=60% directional accuracy, both holdout classes represented)
before the owner can activate it for research signals. These small-sample gates
are initial screening, not evidence of profitability. Models expire after 30
days and cannot be activated with stale/future training data. No order execution
is enabled by training or activation. Untrained/unvalidated inputs yield WAIT.

### Market Sentiment Monitoring

The main Radar shows news/social bullish, bearish and neutral sample counts,
mean VADER score, watchlist movers and relative volume. Raw sentiment does not
itself produce a BUY/SELL; the separately validated KAOS model decides. Aggregate
history has one point per asset/five-minute scan bucket, seven-day TTL retention
and an authenticated last-100-points endpoint. Training snapshots have a 90-day
TTL. No synthetic history or continuous background worker is introduced.

Reference reviewed: https://github.com/gabotechs/market-monitor (MIT). Its Reddit
and Twitter collectors also use VADER; its Docker/InfluxDB deployment, five-second
quote polling and old dependencies are not copied into cPanel. KAOS uses its
existing authenticated adapters, MongoDB and React UI. VADER's package includes
its own license; no upstream Market Monitor source code is copied.

Install the updated backend requirements before activating the new release.
If VADER is omitted, Radar returns dependency-missing WAIT while unrelated login
routes remain usable. Social platform API approval/keys are still needed for
those data feeds. No software can bypass those access requirements.

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

**Market opportunities** now invokes source collection and the local KAOS model,
not the technical breakout rule alone. Coinbase/Yahoo closed 15-minute candles
provide price/volume features for stock/ETF/crypto. Unsupported markets or stale,
missing and gapped candles cannot produce an AI direction. Optional sources
are configured once by the owner. Scans remain watchlist-bounded; this is not an
all-internet/firehose scanner. Reference technical rules are not represented as
trained AI. Model signals expire locally after 15 minutes and require a new scan.

**Bot entries** remains independent: only the signed-in user's recorded
SIGNAL_GENERATED entries, exact broker/OTC identifiers, explicit 30s/45s expiry,
and no simulated/future/expired records. Extension versions without uploaded
signals show an empty state. This is not a new short-expiry prediction service.

## Alpha Vantage key handling

Save the key once under Admin → Radar Sources & AI → Alpha Vantage. It is
Fernet-encrypted server-side and never returned in metadata or included in
browser bundles, release ZIPs or Git source. Environment fallback is supported.
A key supplied in conversation is not automatically configured on Asura: this
workspace has no authenticated hosting/admin session. No real key is embedded
in tests or examples. HTTP request logs redact Alpha Vantage query URLs.

News is requested when its tab opens or Refresh news is pressed. A shared
hourly cache and atomic lease prevent per-member request multiplication, and an
atomic 20-request UTC-day budget reserves room below the standard free quota.
Provider error/limit payloads (including HTTP 200 Information responses) are
cached as failures rather than treated as empty successful feeds. Saved
headlines can still be shown when the provider is unavailable. No stock price
or longer-horizon AI model is claimed to come from this news-only integration.

## Current replacement: Trending Stocks via ApeWisdom

The direct Reddit/X scanner, individual-post view and member Social tab have
been removed. `/social/mentions` now returns 410 to old clients. Direct-social
providers are omitted from default scans and owner setup listings; existing
encrypted settings are retained without being required. The retired scanner's
frontend/backend files are removed, not just hidden behind a failing key prompt.

The replacement **Trending** tab uses ApeWisdom's documented public endpoint:
https://apewisdom.io/api/v1.0/filter/all-stocks/page/1
It requires no Reddit/X API credentials. One shared Mongo cache lasts 30 minutes;
an atomic lease prevents duplicate upstream refreshes, and errors are cached for
five minutes. Failures may display a clearly marked saved snapshot up to one
day old. Stale rankings never feed the KAOS model. The public endpoint was
verified returning HTTP 200 and 100 rows during development; uptime is external.

ApeWisdom reports aggregated mentions/upvotes and previous-day rank/count
snapshots for selected Reddit stock communities. This filter excludes its
separate crypto/4chan feeds. It does not provide X coverage, individual posts,
post sentiment or a provider update timestamp. UI timestamps explicitly mean
fetch time. Missing comparisons display an em dash, not a fabricated zero.

KAOS receives six separate attention features: mention level, log change,
inverse rank, upvote activity, comparison availability and ranking availability.
A stock absent from the top 100 is missing coverage, not zero mentions. Counts
are never converted into bullish/bearish text sentiment. The model schema is
now `kaos-radar-vader-trending-v1`; older direct-social models cannot be reused
and need fresh training/validation. No trading authority changes.

Provider documentation: https://apewisdom.io/api/
Methodology/coverage: https://apewisdom.io/methodology/
No paid alternative service or subscription is enabled.
