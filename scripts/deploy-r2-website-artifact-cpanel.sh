#!/usr/bin/env bash
# Deploy GitHub Actions' KAOS website artifact from a local zip uploaded to cPanel.
# No npm or Node required. Does not modify active backend or Passenger entrypoint.
set -Eeuo pipefail
umask 077
ZIP="${1:-$HOME/kaos-website-cpanel.zip}"
WEB="${KAOS_LIVE_WEB_ROOT:-$HOME/tradingwithkaos.com}"
test -s "$ZIP" || { echo "ERROR: Upload the GitHub Actions website zip to $ZIP first"; exit 1; }
test -s "$WEB/index.html" || { echo "ERROR: Live KAOS document root not found: $WEB"; exit 1; }
command -v unzip >/dev/null || { echo "ERROR: unzip is unavailable"; exit 1; }
command -v rsync >/dev/null || { echo "ERROR: rsync is unavailable"; exit 1; }
STAGE="$(mktemp -d "$HOME/kaos-web-stage.XXXXXXXX")"
trap 'rm -rf "$STAGE"' EXIT
unzip -q "$ZIP" -d "$STAGE"
test -s "$STAGE/index.html" || { echo "ERROR: Artifact missing root index.html"; exit 1; }
test -d "$STAGE/static" || { echo "ERROR: Artifact missing static build files"; exit 1; }
BACKUP="$HOME/kaos-deploy-backups/web-artifact-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$BACKUP"
cp -p "$WEB/index.html" "$BACKUP/index.html"
if test -f "$WEB/asset-manifest.json"; then
  cp -p "$WEB/asset-manifest.json" "$BACKUP/"
fi
# Never delete old hashed assets (needed for safe rollback), nor touch backend,
# .env, hidden server config, uploaded data or cPanel Passenger files.
rsync -a --exclude='index.html' --exclude='.htaccess' --exclude='backend/' \
  --exclude='.env' --exclude='.env.*' --exclude='passenger_wsgi.py' \
  "$STAGE/" "$WEB/"
cp "$STAGE/index.html" "$WEB/index.html"
echo "KAOS WEBSITE DEPLOYED"
echo "Old index backed up to $BACKUP"
echo "No backend code, Passenger entrypoints, secrets, broker orders, or crons modified."
echo "Open https://tradingwithkaos.com/dashboard/backtests after signing in."
