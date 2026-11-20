# Connect Cloudflare R2 candle archives to KAOS AI research

**Implementation state:** the private R2 reader and integrations are committed in draft [PR #62](https://github.com/affiliateleakz/KAOS/pull/62). They are NOT deployed to the live KAOS API until the API code is reviewed/merged and redeployed. The Cloudflare `kaos` collector currently writes archives to `kaos-candle-archive` independently. An R2 archive does **not** itself train or approve an AI model.

## How it works

- Cloudflare Workers → private R2 daily JSON market archives, using the existing Alpaca IEX stock/ETF and Coinbase crypto source identities.
- On member `/api/v1/research/market-history/prediction`, if the legacy Mongo archive does not contain 100 provider-matched bars, KAOS reads the private R2 bucket via signed S3 requests. The model must already be approved for that exact source, symbol and timeframe. No public R2 objects and no mixed providers.
- Owner `POST /api/v1/owner/candles/prediction-candidates/build` can use up to 5000 closed R2 candles if Mongo has fewer than 500. Owner still must evaluate and explicitly approve a quality-screened model. The scores remain experimental and uncalibrated. Member predictions are advisory; orders and options recommendations are disabled.
- Owner can smoke-test R2 read connectivity with `GET /api/v1/owner/candles/r2-status?symbol=BTC-USD&asset_class=crypto&seconds=60` before any model operation.
- Only KAOS API has R2 read credentials. Cloudflare Worker does not need them because it uses the R2 binding `CANDLE_ARCHIVE`.

## One-time private R2 API credentials

Cloudflare Dashboard → R2 Object Storage → **Manage API Tokens** → **Create API Token**. Grant **Object Read** permissions (or the minimum supported read-only permission) **only for `kaos-candle-archive`**. Record the R2-specific Access Key ID and Secret Access Key. This is NOT the Alpaca key pair and NOT the Cloudflare account API token.

Place these secrets in the deployment environment of **KAOS Python API** (cPanel environment, secrets manager, or hosting settings; never commit to GitHub). Existing `boto3` is already in the API requirements:

```dotenv
KAOS_R2_ENABLED=true
KAOS_R2_ACCOUNT_ID=<Cloudflare R2 account ID>
KAOS_R2_ACCESS_KEY_ID=<R2 API token Access Key ID>
KAOS_R2_SECRET_ACCESS_KEY=<R2 API token Secret Access Key>
KAOS_R2_BUCKET=kaos-candle-archive
KAOS_R2_ALPACA_FEED=iex
```

The account ID is displayed on the R2 page. `KAOS_R2_BUCKET` and `KAOS_R2_ALPACA_FEED` may use their defaults but make the intended bindings explicit. Do not set R2 credentials on the Cloudflare Worker: the credentials are for the separate KAOS Python API.

## Deploy and verify

1. Review/merge the required API research changes from PR #62, then redeploy the **Python API** using the existing hosting process. The independent Cloudflare cron collector is already on `main`; its data remains stored in R2 while the API is prepared.
2. Provision the restricted R2 credentials and environment variables above to the Python API. Restart the API to load them.
3. Sign in as KAOS owner and request `GET /api/v1/owner/candles/r2-status?symbol=BTC-USD&asset_class=crypto&seconds=60`. Expected `status: archive_readable`, `closed_bars > 0`. A `not_configured` or `read_failed` result means fix Python API secrets or bucket permissions.
4. Assess sample quality and data coverage. Historical R2 candles cannot automatically qualify a live AI model. Build a candidate with `POST /api/v1/owner/candles/prediction-candidates/build?symbol=BTC-USD&asset_class=crypto&seconds=60&horizon=5`. If insufficient history, continue collecting. Require independent forward validation before approving any model.
5. Approved member predictions consume provider-matched R2 history without publishing R2. A fresh candle must exist, and 100 recent bars must be contiguous for the experimental model to predict. Stock market closures, IEX gaps, model training cutoff and stale feeds may correctly yield WAIT.

## Important

- The Cloudflare collector's status `"mirror":"disabled"` is **expected** with direct R2 reading. No need to send daily candles into Mongo just for predictions.
- R2 data is not necessarily continuous or gap-free; do not fill missing trading-session bars with synthetic candles.
- The R2 API client only reads individual known daily objects; it does not enumerate the bucket, grant public access, or write back.
- Each authenticated request reads at most 10 days of R2 objects for member predictions or 32 days for owner research. Add strict caching and rate controls before production scaling to many simultaneous members. Existing API member route has authentication/AI entitlement checks.
- Verify stock/crypto provider licenses before redistributing raw prices to members. This is research only with no order authority, options selections, or performance guarantees.
