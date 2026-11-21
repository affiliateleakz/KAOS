#!/usr/bin/env bash
# Targeted KAOS R2 Research Lab cPanel deploy. Preserves customized Passenger.
# Usage from ~/kaos-deploy-source after pulling main:
#   bash scripts/deploy-r2-research-lab-cpanel.sh
set -Eeuo pipefail
umask 077
SOURCE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LIVE="$HOME/tradingwithkaos.com/backend"
WEB="$HOME/tradingwithkaos.com"
PY="$HOME/virtualenv/tradingwithkaos.com/backend/3.11/bin/python"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP="$HOME/kaos-r2-lab-backups/$STAMP"
FILES=(routes_owner_candles.py kaos_r2_ai_lab.py kaos_r2_ai_cron.py)
[[ -x "$PY" && -d "$LIVE/apps/api" && -d "$WEB" ]] || { echo "Active cPanel paths missing"; exit 1; }
[[ -f "$LIVE/passenger_wsgi.py" && -f "$LIVE/apps/api/server.py" ]] || { echo "Live customized Passenger/API missing"; exit 1; }
grep -q 'routes_owner_candles.router' "$LIVE/apps/api/server.py" || { echo "Live server does not already mount owner candles router"; exit 1; }
[[ -f "$WEB/index.html" ]] || { echo "Expected KAOS website index missing. Refusing deployment."; exit 1; }
command -v npm >/dev/null || { echo "npm unavailable on cPanel; web build required before deployment"; exit 1; }
command -v rsync >/dev/null || { echo "rsync required"; exit 1; }
for f in "${FILES[@]}"; do [[ -s "$SOURCE/apps/api/$f" ]] || { echo "Missing source: $f"; exit 1; }; done
# Build before editing any live paths.
(
 cd "$SOURCE/apps/web"
 test -f package-lock.json
 npm ci --no-audit --no-fund
 CI=false REACT_APP_BACKEND_URL=https://api.tradingwithkaos.com npm run build
)
[[ -s "$SOURCE/apps/web/build/index.html" ]] || { echo "Website build not created"; exit 1; }
# Check all API code in source before touching live.
"$PY" -m py_compile "${FILES[@]/#/$SOURCE/apps/api/}" "$SOURCE/apps/api/kaos_r2_segmented_research.py"
mkdir -p "$BACKUP/api" "$BACKUP/web"
for f in "${FILES[@]}"; do
  [[ ! -f "$LIVE/apps/api/$f" ]] || cp -p "$LIVE/apps/api/$f" "$BACKUP/api/$f"
done
cp -p "$WEB/index.html" "$BACKUP/web/index.html"
# Keep existing old hashed assets for rollback; no deletes.
if [[ -f "$WEB/asset-manifest.json" ]]; then cp -p "$WEB/asset-manifest.json" "$BACKUP/web/"; fi
echo "Backups: $BACKUP"
for f in "${FILES[@]}"; do cp "$SOURCE/apps/api/$f" "$LIVE/apps/api/$f"; done
# NEVER overwrite Passenger config, server.py, .env, backend/ or .htaccess.
rsync -a --exclude='.htaccess' --exclude='backend/' --exclude='.env' \
  --exclude='passenger_wsgi.py' "$SOURCE/apps/web/build/" "$WEB/"
mkdir -p "$LIVE/tmp"
touch "$LIVE/tmp/restart.txt"
echo "R2 Research Lab deployed. Preserved Passenger / .env / customized server.py."
echo "Validate: https://api.tradingwithkaos.com/api/health"
echo "Page: https://tradingwithkaos.com/dashboard/backtests"
echo "Backup: $BACKUP"
