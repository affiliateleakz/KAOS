# KAOS private R2 archive → Python API

This focused bridge only reads the **already existing private** Cloudflare R2 bucket `kaos-candle-archive`. The Cloudflare `kaos` Worker has its own R2 binding `CANDLE_ARCHIVE` and **does not need S3 credentials**. The separate KAOS Python API needs a restricted R2 S3 read-only token.

## Provision restricted credentials (KAOS API hosting, not GitHub)

1. Cloudflare → **R2 Object Storage → Manage API Tokens → Create API Token**.
2. Restrict the token to **read objects** in bucket `kaos-candle-archive` only. Save the **R2 Access Key ID** and **R2 Secret Access Key** privately.
3. On the KAOS API's cPanel Python application environment, add the following environment variables and restart the application:

| Variable | Value |
|---|---|
| `KAOS_R2_ENABLED` | `true` |
| `KAOS_R2_ACCOUNT_ID` | Cloudflare R2 account ID (from dashboard) |
| `KAOS_R2_ACCESS_KEY_ID` | R2 token Access Key ID |
| `KAOS_R2_SECRET_ACCESS_KEY` | R2 token Secret Access Key |
| `KAOS_R2_BUCKET` | `kaos-candle-archive` |
| `KAOS_R2_ALPACA_FEED` | `iex` (the same source as collector) |

Never put secrets in `wrangler.jsonc`, GitHub Actions or public frontend code. The R2 API token is **not** the Alpaca market data key and **not** a Cloudflare general API build token.

## Verify

Once this PR is merged and the **Python API** redeployed:

- Call `GET /api/v1/owner/candles/r2-status?symbol=BTC-USD&asset_class=crypto&seconds=60` with an authenticated KAOS owner session. An `archive_readable` result and `closed_bars>0` confirms server-side private R2 read access.
- Call `GET /api/v1/owner/candles/export?symbol=BTC-USD&asset_class=crypto&seconds=60&limit=300`. It returns `candle_origin: cloudflare_r2_private_archive` if R2 has more history than Mongo.

The reader validates symbol and provider identity, prohibits traversal, rejects invalid OHLCV and unresolved revisions, and returns only fully closed bars. It does not expose S3 credentials or publish the R2 bucket.

## Remaining scope

This PR does **not** activate the experimental AI prediction routes, which are still in separate, conflicting draft PR #62. Activating models requires resolving that PR, running backtest/forward validation, deploying the API, and explicit owner research approval. Never claim AI trading or options signals are active from R2 access alone.
