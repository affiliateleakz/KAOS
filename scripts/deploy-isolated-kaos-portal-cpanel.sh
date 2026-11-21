#!/usr/bin/env bash
# Restore the KAOS React member/admin portal without replacing the cinematic
# Viking homepage at /index.html. Does NOT restart Passenger or touch .env.
# Run only after a reviewed GitHub build exists for the intended main revision.
set -Eeuo pipefail
umask 077
REPO="${KAOS_REPO:-$HOME/kaos-deploy-source}"
WEB="${KAOS_LIVE_WEB_ROOT:-$HOME/tradingwithkaos.com}"
command -v git >/dev/null
command -v rsync >/dev/null
command -v tar >/dev/null
test -s "$WEB/index.html" || { echo "Missing working Viking homepage"; exit 1; }
test -f "$WEB/.htaccess" || { echo "No existing LiteSpeed rewrite config. Stop: manual review required."; exit 1; }
grep -q '^RewriteEngine On' "$WEB/.htaccess" || { echo "Unknown rewrite syntax. Stop."; exit 1; }
git -C "$REPO" fetch origin main
MAIN="$(git -C "$REPO" rev-parse origin/main)"
STAGE="$(mktemp -d "$HOME/kaos-portal-stage.XXXXXX")"
trap 'rm -rf "$STAGE"' EXIT
if [ -n "${KAOS_PORTAL_BUILD_DIR:-}" ]; then
  # Use GitHub Actions' version-stamped web build artifact, downloaded and
  # extracted to a private folder before this script is invoked.
  test -d "$KAOS_PORTAL_BUILD_DIR" || { echo "Build directory missing"; exit 1; }
  rsync -a --no-perms --no-owner --no-group "$KAOS_PORTAL_BUILD_DIR/" "$STAGE/"
else
  # Legacy compiled branch is safe only when it EXACTLY matches main.
  git -C "$REPO" fetch origin kaos-cpanel-build
  git -C "$REPO" archive origin/kaos-cpanel-build | tar -xf - -C "$STAGE"
fi
test -s "$STAGE/index.html" || { echo "Compiled portal missing"; exit 1; }
test -d "$STAGE/static" || { echo "Compiled assets missing"; exit 1; }
# The front-end includes new Alpaca and research API routes; do not deploy
# until the Python Passenger API installer has staged the same revision.
LIVE_API="${KAOS_LIVE_API_ROOT:-$HOME/tradingwithkaos.com/backend}"
test -s "$LIVE_API/kaos-paper-api-revision.txt" || {
  echo "Missing matching paper API install marker. Deploy verified API first."
  exit 1
}
API_BUILT="$(cat "$LIVE_API/kaos-paper-api-revision.txt")"
test "$API_BUILT" = "$MAIN" || {
  echo "API deployment revision ($API_BUILT) does not match main ($MAIN). Stop."
  exit 1
}
BUILT="$(cat "$STAGE/kaos-build-revision.txt")"
test "$BUILT" = "$MAIN" || {
  echo "Compiled portal build ($BUILT) differs from main ($MAIN). Stop safely."
  exit 1
}
# This portal-specific rewrite assumes CREATE_REACT_APP emits absolute /static
# asset URLs; never silently deploy a relative-path build under /portal/.
grep -q 'src="/static/js/' "$STAGE/index.html" || {
  echo "Portal assets are not absolute /static paths. Stop."; exit 1;
}
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP="$HOME/kaos-deploy-backups/isolated-portal-$STAMP"
mkdir -p "$BACKUP"
cp -p "$WEB/index.html" "$BACKUP/viking-homepage-index.html"
cp -p "$WEB/.htaccess" "$BACKUP/.htaccess"
mkdir -p "$WEB/portal"
# Keep old content-hashed assets so existing open browser sessions still work.
rsync -a --no-perms --no-owner --no-group "$STAGE/static/" "$WEB/static/"
find "$WEB/static" -type d -exec chmod 755 {} +
find "$WEB/static" -type f -exec chmod 644 {} +
cp "$STAGE/index.html" "$WEB/portal/index.html"
chmod 755 "$WEB/portal"
chmod 644 "$WEB/portal/index.html"
# Rewrite only known React routes. Preserve all homepage, privacy,
# backend, assets and all other existing server rewrite rules as-is.
MARKER='# KAOS_PORTAL_ROUTE_REWRITE_V1'
if ! grep -qF "$MARKER" "$WEB/.htaccess"; then
  awk '
    /^RewriteEngine On$/ && !injected {
      print
      print "# KAOS_PORTAL_ROUTE_REWRITE_V1"
      print "RewriteRule ^(admin|dashboard|login|register|forgot-password|reset-password|onboarding|payment|community|u|s)(/|$) portal/index.html [L]"
      injected=1
      next
    }
    {print}
    END {if (!injected) exit 2}
  ' "$BACKUP/.htaccess" > "$BACKUP/.htaccess.new"
  cp "$BACKUP/.htaccess.new" "$WEB/.htaccess"
fi
chmod 644 "$WEB/.htaccess"
chmod 711 "$WEB"
chmod 644 "$WEB/index.html"
echo "KAOS isolated portal staged. Homepage index unchanged."
echo "Build: $BUILT"
echo "Backup: $BACKUP"
echo "Check /admin/trading-ops, /dashboard/paper, /login and /"
echo "If a route fails: cp '$BACKUP/.htaccess' '$WEB/.htaccess'"
