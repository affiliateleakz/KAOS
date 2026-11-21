#!/usr/bin/env bash
# Install KAOS R2 Research API AND precompiled React website from git.
# No cPanel npm, Node, GitHub auth, ZIP download, or manual uploads.
# Preserves customized Passenger, backend, .env, .htaccess, and old hashed assets.
set -Eeuo pipefail
umask 077
REPO="${KAOS_REPO:-$HOME/kaos-deploy-source}"
WEB="${KAOS_LIVE_WEB_ROOT:-$HOME/tradingwithkaos.com}"
LIVE="${KAOS_LIVE_API_ROOT:-$HOME/tradingwithkaos.com/backend}"
command -v rsync >/dev/null || { echo "ERROR: rsync not installed"; exit 1; }
command -v git >/dev/null || { echo "ERROR: git not installed"; exit 1; }
command -v tar >/dev/null || { echo "ERROR: tar not installed"; exit 1; }
test -s "$WEB/index.html" || { echo "ERROR: KAOS document root not found: $WEB"; exit 1; }
test -s "$LIVE/passenger_wsgi.py" || { echo "ERROR: Customized Passenger file missing"; exit 1; }
test -s "$REPO/scripts/deploy-r2-research-api-only-cpanel.sh" || {
  echo "ERROR: Update local repo main first"; exit 1;
}
git -C "$REPO" fetch origin refs/heads/kaos-cpanel-build:refs/remotes/origin/kaos-cpanel-build
test "$(git -C "$REPO" cat-file -t origin/kaos-cpanel-build)" = commit || {
  echo "ERROR: GitHub website build branch not available yet"; exit 1;
}
STAGE="$(mktemp -d "$HOME/kaos-website-stage.XXXXXXXX")"
trap 'rm -rf "$STAGE"' EXIT
git -C "$REPO" archive origin/kaos-cpanel-build | tar -xf - -C "$STAGE"
test -s "$STAGE/index.html" || { echo "ERROR: Compiled website index missing"; exit 1; }
test -d "$STAGE/static" || { echo "ERROR: Compiled website static assets missing"; exit 1; }
BUILT_FOR="$(cat "$STAGE/kaos-build-revision.txt")"
SOURCE_HEAD="$(git -C "$REPO" rev-parse HEAD)"
if [[ "$BUILT_FOR" != "$SOURCE_HEAD" ]]; then
  echo "ERROR: Website build revision ($BUILT_FOR) does not match local main ($SOURCE_HEAD)"
  echo "Do not combine an old website with a new API; check GitHub website build status."
  exit 1
fi
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP="$HOME/kaos-deploy-backups/terminal-only-$STAMP"
mkdir -p "$BACKUP"
cp -p "$WEB/index.html" "$BACKUP/index.html"
if test -f "$WEB/asset-manifest.json"; then cp -p "$WEB/asset-manifest.json" "$BACKUP/"; fi
echo "=== INSTALL RESEARCH API (BACKUP INCLUDED) ==="
bash "$REPO/scripts/deploy-r2-research-api-only-cpanel.sh"
echo "=== INSTALL GITHUB-BUILT WEBSITE ==="
# Preserve backend, secrets, server configs. Keep older hashed assets for rollback.
(umask 022; rsync -a --no-perms --no-owner --no-group --exclude='index.html' --exclude='.htaccess' --exclude='backend/' \
  --exclude='.env' --exclude='.env.*' --exclude='passenger_wsgi.py' \
  "$STAGE/" "$WEB/")
# A mktemp staging directory has mode 700; rsync must never copy that
# directory mode onto the public domain document root (2026-11 incident).
# Ensure generated static assets can be read by LiteSpeed without exposing
# the backend tree; keep the document root non-listable by other users.
if test -d "$WEB/static"; then
  find "$WEB/static" -type d -exec chmod 755 {} +
  find "$WEB/static" -type f -exec chmod 644 {} +
fi
chmod 711 "$WEB"
chmod 644 "$WEB/index.html"
cp "$STAGE/index.html" "$WEB/index.html"
chmod 644 "$WEB/index.html"
echo "KAOS WEBSITE + RESEARCH API INSTALLED; no npm required."
echo "Revision: $BUILT_FOR"
echo "Previous index backup: $BACKUP/index.html"
echo "Open: https://tradingwithkaos.com/dashboard/backtests"
echo "Live AI trading remains locked; scheduled research crons not activated."
