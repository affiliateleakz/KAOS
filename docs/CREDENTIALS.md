# Provider credentials

`apps/api/kaos_credentials.py` installs provider keys into the process
environment before any `os.getenv(...)` call runs. It is imported by `db.py`,
which every route module and cron worker reaches.

## Where the values live

`kaos_credentials.py` is committed and contains **no secrets**. Real values come
from one of two places, both outside version control:

| Source | Committed? | Priority |
| --- | --- | --- |
| Process environment (`export`) | no | 1 (highest) |
| `.env` on the host | no (git-ignored) | 2 |
| `apps/api/kaos_credentials_local.py` | no (git-ignored) | 3 |
| `DEFAULTS` in `kaos_credentials.py` | yes, empty | 4 |

`install()` never overwrites a variable that is already set.

**Why not commit them:** `github.com/affiliateleakz/KAOS` is a public
repository. A secret committed here is published immediately and stays in git
history after deletion. Verified 2026-11-21: an anonymous `git clone` succeeds.

## Variable reference

| Variable | Provider | Used by |
| --- | --- | --- |
| `ALPHA_VANTAGE_API_KEY` | Alpha Vantage | integration probe, quotes |
| `FRED_API_KEY` | St. Louis Fed | integration probe, macro series |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare | R2 endpoint host |
| `CLOUDFLARE_API_TOKEN` | Cloudflare REST | reference only; **not** used by R2 |
| `KAOS_R2_ACCOUNT_ID` | Cloudflare R2 | archive, training, paper loop |
| `KAOS_R2_ACCESS_KEY_ID` | Cloudflare R2 | same |
| `KAOS_R2_SECRET_ACCESS_KEY` | Cloudflare R2 | same |
| `KAOS_R2_BUCKET` | Cloudflare R2 | same |
| `KAOS_R2_ENABLED` | feature flag | enables R2 reads |
| `APCA_API_KEY_ID` / `APCA_API_SECRET_KEY` | Alpaca market data | heat map, collectors |
| `KAOS_ALPACA_STOCK_FEED` | Alpaca feed | `iex` or `sip` |

Alpaca **paper orders** are deliberately not configurable here. They require a
verified per-member connection in the encrypted broker vault
(`routes_alpaca_paper.py`), because a trading credential must be attributable to
the member who placed the order. A server-side Alpaca key enables market data
only, not order placement.

## Installing on the cPanel host

Create the git-ignored file once with restrictive permissions:

```bash
LIVE="$HOME/tradingwithkaos.com/backend"
umask 077
cat > "$LIVE/apps/api/kaos_credentials_local.py" <<'PYEOF'
DEFAULTS = {
    "ALPHA_VANTAGE_API_KEY": "<key>",
    "FRED_API_KEY": "<key>",
    "CLOUDFLARE_ACCOUNT_ID": "<account id>",
    "KAOS_R2_ACCOUNT_ID": "<account id>",
    "KAOS_R2_ACCESS_KEY_ID": "<access key>",
    "KAOS_R2_SECRET_ACCESS_KEY": "<secret>",
    "KAOS_R2_BUCKET": "kaos-candle-archive",
    "KAOS_R2_ENABLED": "true",
}
PYEOF
chmod 600 "$LIVE/apps/api/kaos_credentials_local.py"
```

Then deploy the loader and catalog entries:

```bash
bash "$HOME/kaos-deploy-source/scripts/deploy-credentials-integrations-cpanel.sh"
```

`git pull` never removes this file, and the deploy script's clean-checkout test
does not see it.

## Rotation

1. Create replacement keys at the provider.
2. Either edit `kaos_credentials_local.py` on the host, or set the variable in
   the host `.env`, which takes priority.
3. `touch "$LIVE/tmp/restart.txt"` to restart Passenger.
4. Confirm in **Admin → Integrations** that the provider probe returns OK.

Rotate immediately if a key has ever been committed, pasted into a chat, or
shared. Deleting the file does not remove it from git history; the key itself
must be replaced at the provider.

## Handling rules

1. Never commit `kaos_credentials_local.py` or `.env`.
2. Never paste key values into logs, tickets or chat. The admin panel masks
   secret fields before rendering (`integration_config._public_entry`).
3. The Cloudflare REST token being invalid or revoked does not affect R2. R2
   authenticates with its own S3 access key and secret.
