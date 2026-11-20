#!/usr/bin/env bash
# KAOS cPanel one-command deploy from its local Git checkout.
# Executes on hosting terminal. No live broker/AI activation is performed.
set -Eeuo pipefail
umask 077

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="${KAOS_API_DIR:-/home/itsabout/kaos_backend}"
WEB_DIR="${KAOS_WEB_DIR:-/home/itsabout/public_html}"
DO_WEB="${KAOS_DEPLOY_WEB:-0}"
DO_PIP="${KAOS_INSTALL_DEPS:-0}"
DO_RESTART="${KAOS_RESTART:-1}"
REV="$(git -C "$HERE" rev-parse --short=12 HEAD)"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)-$REV"

if [[ "$API_DIR" == "$WEB_DIR" || "$API_DIR" == "/" || "$WEB_DIR" == "/" ]]; then
  echo "ERROR: Invalid deployment directories"; exit 1
fi
if [[ ! -d "$API_DIR" ]]; then
  echo "ERROR: API directory is missing: $API_DIR"; exit 1
fi
if [[ "$DO_WEB" == "1" && ! -d "$WEB_DIR" ]]; then
  echo "ERROR: Web directory is missing: $WEB_DIR"; exit 1
fi
for file in "$HERE/apps/api/server.py" "$HERE/apps/api/passenger_wsgi.KAOS" "$HERE/apps/api/requirements.txt" "$HERE/apps/api/kaos_r2_archive.py"; do
  test -s "$file" || { echo "ERROR: Missing $file"; exit 1; }
done
test -d "$HERE/packages/kaos-core" || { echo "ERROR: KAOS core package missing"; exit 1; }
command -v rsync >/dev/null || { echo "ERROR: rsync required"; exit 1; }
echo "KAOS release $REV"
echo "API directory: $API_DIR"
echo "Website directory: $WEB_DIR"
echo "Website build enabled: $DO_WEB"
echo "Dependency install enabled: $DO_PIP"
echo "Changes will preserve .env, server secrets and existing files not in this release."

STAGE="$(mktemp -d "${TMPDIR:-/tmp}/kaos-deploy.XXXXXXXX")"
trap 'rm -rf "$STAGE"' EXIT
mkdir -p "$STAGE/api/packages/kaos-core" "$STAGE/web"
find "$HERE/apps/api" -maxdepth 1 -type f \\( -name '*.py' -o -name requirements.txt \\) ! -name 'test_*.py' -exec cp {} "$STAGE/api/" \\;
cp -R "$HERE/packages/kaos-core/." "$STAGE/api/packages/kaos-core/"
cp "$HERE/apps/api/passenger_wsgi.KAOS" "$STAGE/api/passenger_wsgi.py"
printf '%s\\n' "$REV" > "$STAGE/api/.kaos-release-sha"

if [[ "$DO_WEB" == "1" ]]; then
  command -v npm >/dev/null || { echo "ERROR: npm missing. Use KAOS_DEPLOY_WEB=0 to update API only."; exit 1; }
  echo "Building KAOS website from repo..."
  (
    cd "$HERE/apps/web"
    test -f package-lock.json || { echo "ERROR: package-lock.json missing"; exit 1; }
    npm ci --no-audit --no-fund
    CI=false REACT_APP_BACKEND_URL=https://api.tradingwithkaos.com npm run build
  )
  test -s "$HERE/apps/web/build/index.html" || { echo "ERROR: website build failed"; exit 1; }
  cp -R "$HERE/apps/web/build/." "$STAGE/web/"
  printf '%s\\n' "$REV" > "$STAGE/web/.kaos-release-sha"
fi

BACKUPS="$HOME/kaos-deploy-backups/$STAMP"
mkdir -p "$BACKUPS/api" "$BACKUPS/web"
echo "Deploying API with backups at $BACKUPS ..."
rsync -a --backup --backup-dir="$BACKUPS/api" \\
  --exclude='.env' --exclude='.env.*' --exclude='*.log' \\
  "$STAGE/api/" "$API_DIR/"

if [[ "$DO_PIP" == "1" ]]; then
  PY="${KAOS_PYTHON_BIN:-}"
  if [[ -z "$PY" || ! -x "$PY" ]]; then
    echo "ERROR: set KAOS_PYTHON_BIN to your existing cPanel Python venv/bin/python"; exit 1
  fi
  "$PY" -m pip install -r "$API_DIR/requirements.txt"
fi

if [[ "$DO_WEB" == "1" ]]; then
  echo "Deploying website..."
  rsync -a --backup --backup-dir="$BACKUPS/web" --exclude=index.html \\
    --exclude='.env' --exclude='.env.*' "$STAGE/web/" "$WEB_DIR/"
  if [[ -f "$WEB_DIR/index.html" ]]; then cp -p "$WEB_DIR/index.html" "$BACKUPS/web/index.html"; fi
  cp "$STAGE/web/index.html" "$WEB_DIR/index.html"
fi

if [[ "$DO_RESTART" == "1" ]]; then
  mkdir -p "$API_DIR/tmp"
  touch "$API_DIR/tmp/restart.txt"
  echo "Passenger restart requested. If cPanel uses a different restart method, click Restart in Setup Python App."
fi
echo "KAOS installed from commit $REV"
echo "Verify: https://api.tradingwithkaos.com/api/health"
echo "Owner-only R2 route: /api/v1/owner/candles/r2-status"
echo "Existing R2 environment variables remain on the server; this script never writes credentials."
