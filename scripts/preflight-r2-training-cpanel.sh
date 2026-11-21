#!/usr/bin/env bash
# Read-only preflight for enabling the KAOS R2 research training cron.
# Reports PASS/FAIL per gate and never prints a secret value.
# Changes nothing: no writes, no crontab edits, no restarts.
set -Eeuo pipefail

LIVE="${KAOS_LIVE_API_ROOT:-$HOME/tradingwithkaos.com/backend}"
PY="${KAOS_PYTHON_BIN:-$HOME/virtualenv/tradingwithkaos.com/backend/3.11/bin/python}"
ENVFILE="$LIVE/.env"
pass=0
fail=0

ok() { printf '  PASS  %s\n' "$1"; pass=$((pass + 1)); }
no() { printf '  FAIL  %s\n' "$1"; fail=$((fail + 1)); }
info() { printf '  INFO  %s\n' "$1"; }

echo "KAOS R2 training preflight (read-only)"
echo "live root: $LIVE"
echo

echo "[1] runtime"
if [ -x "$PY" ]; then ok "python venv present"; else no "python venv missing: $PY"; fi
if [ -s "$LIVE/apps/api/kaos_ai_training_jobs.py" ]; then
  ok "training worker deployed"
else
  no "training worker not deployed in live API"
fi

echo
echo "[2] paper API revision stamp"
if [ -s "$LIVE/kaos-paper-api-revision.txt" ]; then
  ok "stamp present: $(cat "$LIVE/kaos-paper-api-revision.txt")"
else
  no "missing -> installer refuses; run scripts/deploy-kaos-paper-api-cpanel.sh first"
fi
if [ -s "$LIVE/kaos-credentials-revision.txt" ]; then
  ok "credentials revision: $(cat "$LIVE/kaos-credentials-revision.txt")"
else
  info "no kaos-credentials-revision.txt (credentials deploy may not have run here)"
fi

echo
echo "[3] backend .env keys (names only, never values)"
if [ -s "$ENVFILE" ]; then
  ok ".env present, mode $(stat -c %a "$ENVFILE" 2>/dev/null || echo unknown)"
  "$PY" - "$ENVFILE" <<'PYEOF'
import sys
from dotenv import dotenv_values

values = dotenv_values(sys.argv[1])
required = [
    "MONGO_URL",
    "DB_NAME",
    "KAOS_R2_ACCOUNT_ID",
    "KAOS_R2_ACCESS_KEY_ID",
    "KAOS_R2_SECRET_ACCESS_KEY",
    "KAOS_CANDLE_OWNER_USER_ID",
]
missing = [k for k in required if not values.get(k)]
if values.get("KAOS_R2_ENABLED", "").lower() != "true":
    missing.append("KAOS_R2_ENABLED=true")
if missing:
    print("  FAIL  .env missing: " + ", ".join(missing))
else:
    print("  PASS  .env has every required research setting")
PYEOF
else
  no ".env missing at $ENVFILE"
fi

echo
echo "[4] live server.py router anchors"
for anchor in \
  '^import routes_broker_connections$' \
  '^app.include_router(routes_broker_connections.router)$' \
  '^app.include_router(routes_owner_candles.router)$' \
  '^app.include_router(routes_paper.router)$'
do
  if grep -q "$anchor" "$LIVE/apps/api/server.py" 2>/dev/null; then
    ok "anchor: $anchor"
  else
    no "anchor MISSING: $anchor"
  fi
done

echo
echo "[5] cron state"
if crontab -l 2>/dev/null | grep -qF "KAOS_R2_RESEARCH_TRAINING_CRON_V1"; then
  ok "training cron already installed"
else
  info "training cron not installed yet"
fi

echo
echo "[6] R2 reachability from this host (read-only list)"
if [ ! -x "$PY" ]; then
  no "skipped: no python venv at $PY"
elif "$PY" - <<'PYEOF'
import os
import sys

sys.path.insert(0, os.path.join(os.path.expanduser("~"), "tradingwithkaos.com/backend/apps/api"))
try:
    import kaos_credentials  # noqa: F401  installs env vars
except Exception as exc:
    print(f"  FAIL  cannot import kaos_credentials: {type(exc).__name__}")
    raise SystemExit(1)

account = os.getenv("KAOS_R2_ACCOUNT_ID", "")
key = os.getenv("KAOS_R2_ACCESS_KEY_ID", "")
secret = os.getenv("KAOS_R2_SECRET_ACCESS_KEY", "")
bucket = os.getenv("KAOS_R2_BUCKET", "kaos-candle-archive")
if not all((account, key, secret)):
    print("  FAIL  R2 credentials not present in the process environment")
    raise SystemExit(1)

import boto3
from botocore.config import Config

client = boto3.client(
    "s3",
    endpoint_url=f"https://{account}.r2.cloudflarestorage.com",
    aws_access_key_id=key,
    aws_secret_access_key=secret,
    region_name="auto",
    config=Config(signature_version="s3v4", connect_timeout=8, read_timeout=12),
)
try:
    page = client.list_objects_v2(Bucket=bucket, MaxKeys=1)
except Exception as exc:
    print(f"  FAIL  R2 rejected the request: {type(exc).__name__}")
    raise SystemExit(1)
count = int(page.get("KeyCount", 0))
print(f"  PASS  bucket '{bucket}' readable ({count} object(s) in first page)")
PYEOF
then
  pass=$((pass + 1))
else
  fail=$((fail + 1))
fi

echo
echo "-----------------------------------------"
echo "PASS: $pass   FAIL: $fail"
if [ "$fail" -eq 0 ]; then
  echo "Ready: bash \"$HOME/kaos-deploy-source/scripts/install-kaos-r2-train-cron-cpanel.sh\""
else
  echo "Resolve the FAIL lines above before enabling the training cron."
fi
exit 0
