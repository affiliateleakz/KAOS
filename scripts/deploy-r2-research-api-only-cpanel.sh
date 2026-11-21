#!/usr/bin/env bash
# KAOS R2 Research API-only cPanel deploy. No npm, web build, or generic deploy.
# Run from local git checkout after updating to the latest main.
# Preserves Passenger entry points and server.py while refreshing the existing
# owner-research route and its standalone research-only dependencies.
set -Eeuo pipefail
umask 077
SOURCE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LIVE="${KAOS_LIVE_API_ROOT:-$HOME/tradingwithkaos.com/backend}"
PY="${KAOS_PYTHON_BIN:-$HOME/virtualenv/tradingwithkaos.com/backend/3.11/bin/python}"
FILES=(
  routes_owner_candles.py
  kaos_r2_ai_lab.py
  kaos_r2_ai_cron.py
  kaos_r2_shadow_predict.py
  kaos_r2_shadow_cron.py
  kaos_candlestick_patterns.py
  kaos_r2_pattern_observer.py
  kaos_r2_pattern_cron.py
  kaos_r2_segmented_research.py
  kaos_r2_backtest_batch.py
)
test -x "$PY" || { echo "ERROR: Missing cPanel Python virtualenv: $PY"; exit 1; }
test -f "$LIVE/passenger_wsgi.py" || { echo "ERROR: Live Passenger entry point missing"; exit 1; }
test -f "$LIVE/apps/api/server.py" || { echo "ERROR: Live API server missing"; exit 1; }
grep -q 'routes_owner_candles.router' "$LIVE/apps/api/server.py" || {
  echo "ERROR: Live API does not mount owner research router; deployment stopped"
  exit 1
}
for file in "${FILES[@]}"; do
  test -s "$SOURCE/apps/api/$file" || { echo "ERROR: Missing $file"; exit 1; }
  "$PY" -m py_compile "$SOURCE/apps/api/$file"
done
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP="$HOME/kaos-r2-lab-backups/api-only-$STAMP"
mkdir -p "$BACKUP"
for file in "${FILES[@]}"; do
  if test -f "$LIVE/apps/api/$file"; then
    cp -p "$LIVE/apps/api/$file" "$BACKUP/$file"
  fi
done
for file in "${FILES[@]}"; do
  cp "$SOURCE/apps/api/$file" "$LIVE/apps/api/$file"
done
mkdir -p "$LIVE/tmp"
touch "$LIVE/tmp/restart.txt"
echo "KAOS RESEARCH API FILES INSTALLED"
echo "No npm or website build required."
echo "Backups at: $BACKUP"
echo "Existing Passenger, server.py, .env, API keys and broker routes untouched."
echo "Verify https://api.tradingwithkaos.com/api/health"
echo "Owner-only /api/v1/owner/candles/r2-lab/markets (unauthenticated 401 expected)"
