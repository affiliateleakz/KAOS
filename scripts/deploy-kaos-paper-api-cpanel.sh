#!/usr/bin/env bash
# Stage ONLY KAOS paper/chart/R2 API modules on a reviewed cPanel Passenger app.
# Preserve existing live server.py logic, passenger_wsgi.py, .env and homepage.
# Nothing enables AI auto orders or real-money Alpaca orders.
set -Eeuo pipefail
umask 077

SOURCE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LIVE="${KAOS_LIVE_API_ROOT:-$HOME/tradingwithkaos.com/backend}"
PY="${KAOS_PYTHON_BIN:-$HOME/virtualenv/tradingwithkaos.com/backend/3.11/bin/python}"
FILES=(
  alpaca_paper_client.py
  alpaca_paper_quotes.py
  alpaca_paper_fill_audit.py
  alpaca_paper_fifo.py
  alpaca_paper_recovery.py
  kaos_ai_alpaca_readiness.py
  kaos_ai_paper_review.py
  kaos_ai_bot_signal.py
  kaos_ai_training_jobs.py
  kaos_ai_intelligence_training.py
  routes_alpaca_paper.py
  routes_alpaca_paper_orders.py
  routes_broker_connections.py
  routes_chart_settings.py
  routes_owner_candles.py
  routes_paper.py
  market_data.py
)

command -v git >/dev/null
test -x "$PY" || { echo "Missing cPanel Python environment"; exit 1; }
test -f "$LIVE/passenger_wsgi.py" || { echo "Missing existing Passenger startup file"; exit 1; }
test -f "$LIVE/apps/api/server.py" || { echo "Missing existing FastAPI server"; exit 1; }
test -s "$SOURCE/apps/api/server.py" || { echo "Missing source FastAPI server"; exit 1; }
test -s "$SOURCE/apps/api/routes_alpaca_paper.py" || { echo "Missing source Alpaca module"; exit 1; }
git -C "$SOURCE" fetch origin main
HEAD="$(git -C "$SOURCE" rev-parse HEAD)"
MAIN="$(git -C "$SOURCE" rev-parse origin/main)"
test "$HEAD" = "$MAIN" || { echo "Checkout is not the latest GitHub main. Stop."; exit 1; }
test -z "$(git -C "$SOURCE" status --porcelain)" || {
  echo "Source checkout has uncommitted changes. Stop."; exit 1;
}
# Never deploy a redesigned server.py over an unknown hosting-specific server:
# install the 2 Alpaca routers at known, previously-tested integration anchors.
grep -q '^import routes_broker_connections$' "$LIVE/apps/api/server.py" || {
  echo "Existing API server lacks broker-connection import anchor; stop for review."; exit 1;
}
grep -q '^app.include_router(routes_broker_connections.router)$' "$LIVE/apps/api/server.py" || {
  echo "Existing API server lacks broker-connection router anchor; stop for review."; exit 1;
}
grep -q '^app.include_router(routes_owner_candles.router)$' "$LIVE/apps/api/server.py" || {
  echo "Existing API server lacks research router; stop for review."; exit 1;
}
grep -q '^app.include_router(routes_paper.router)$' "$LIVE/apps/api/server.py" || {
  echo "Existing API server lacks paper router; stop for review."; exit 1;
}
for file in "${FILES[@]}"; do
  test -s "$SOURCE/apps/api/$file" || { echo "Missing source: $file"; exit 1; }
  "$PY" -m py_compile "$SOURCE/apps/api/$file"
done

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP="$HOME/kaos-deploy-backups/paper-api-$STAMP"
mkdir -p "$BACKUP/old"
cp -p "$LIVE/apps/api/server.py" "$BACKUP/server.py"
if test -f "$LIVE/kaos-paper-api-revision.txt"; then
  cp -p "$LIVE/kaos-paper-api-revision.txt" "$BACKUP/kaos-paper-api-revision.txt"
fi
for file in "${FILES[@]}"; do
  if test -f "$LIVE/apps/api/$file"; then
    cp -p "$LIVE/apps/api/$file" "$BACKUP/old/$file"
  else
    printf '%s\n' "$file" >> "$BACKUP/created-files.txt"
  fi
done

rollback() {
  status=$?
  trap - ERR
  echo "API deployment failed; restoring backed-up API files." >&2
  for file in "${FILES[@]}"; do
    if test -f "$BACKUP/old/$file"; then
      cp -p "$BACKUP/old/$file" "$LIVE/apps/api/$file"
    fi
  done
  if test -f "$BACKUP/created-files.txt"; then
    while IFS= read -r file; do
      rm -f "$LIVE/apps/api/$file"
    done < "$BACKUP/created-files.txt"
  fi
  cp -p "$BACKUP/server.py" "$LIVE/apps/api/server.py"
  if test -f "$BACKUP/kaos-paper-api-revision.txt"; then
    cp -p "$BACKUP/kaos-paper-api-revision.txt" "$LIVE/kaos-paper-api-revision.txt"
  else
    rm -f "$LIVE/kaos-paper-api-revision.txt"
  fi
  mkdir -p "$LIVE/tmp"
  touch "$LIVE/tmp/restart.txt"
  exit "$status"
}
trap rollback ERR

for file in "${FILES[@]}"; do
  cp "$SOURCE/apps/api/$file" "$LIVE/apps/api/$file"
  chmod 644 "$LIVE/apps/api/$file"
done
# Targeted idempotent insertion; preserve other live Python modules and routes.
"$PY" - "$LIVE/apps/api/server.py" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1])
code=p.read_text(encoding="utf-8")
imports="import routes_broker_connections\n"
routers="app.include_router(routes_broker_connections.router)\n"
if imports not in code or routers not in code:
    raise SystemExit("Missing backend routing anchors")
if "import routes_alpaca_paper\n" not in code:
    code=code.replace(imports, imports+"import routes_alpaca_paper\n",1)
if "import routes_alpaca_paper_orders\n" not in code:
    code=code.replace("import routes_alpaca_paper\n",
                      "import routes_alpaca_paper\nimport routes_alpaca_paper_orders\n",1)
if "app.include_router(routes_alpaca_paper.router)\n" not in code:
    code=code.replace(routers,routers+"app.include_router(routes_alpaca_paper.router)\n",1)
if "app.include_router(routes_alpaca_paper_orders.router)\n" not in code:
    code=code.replace("app.include_router(routes_alpaca_paper.router)\n",
                      "app.include_router(routes_alpaca_paper.router)\n"
                      "app.include_router(routes_alpaca_paper_orders.router)\n",1)
p.write_text(code,encoding="utf-8")
PY
"$PY" -m py_compile "$LIVE/apps/api/server.py"
# Backend revision is the prerequisite for a matching static portal release.
printf '%s\n' "$MAIN" > "$LIVE/kaos-paper-api-revision.txt.tmp"
mv "$LIVE/kaos-paper-api-revision.txt.tmp" "$LIVE/kaos-paper-api-revision.txt"
chmod 600 "$LIVE/kaos-paper-api-revision.txt"
mkdir -p "$LIVE/tmp"
touch "$LIVE/tmp/restart.txt"
trap - ERR
echo "KAOS PAPER API INSTALLED (research and paper-only routes)"
echo "Revision: $MAIN"
echo "Backup: $BACKUP"
echo "Trading flags are unchanged; AI paper and real-money orders remain disabled."
echo "Next: verify https://api.tradingwithkaos.com/api/health before deploying portal."
