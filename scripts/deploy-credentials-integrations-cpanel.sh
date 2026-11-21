#!/usr/bin/env bash
# Stage the provider-credential loader and the new integration catalog entries
# onto a reviewed cPanel Passenger app.
#
# Touches ONLY:
#   apps/api/kaos_credentials.py        (new, secret-free loader)
#   apps/api/db.py                      (+1 import so keys load before os.environ reads)
#   apps/api/kaos_r2_archive.py         (+1 import for cron entry points)
#   apps/api/integration_config.py      (Alpha Vantage / FRED / R2 entries + probes)
#
# Deliberately does NOT copy server.py: the live server carries hosting-specific
# routers that this repository's copy does not know about.
#
# Secrets are never read, printed or written by this script. They live in the
# git-ignored apps/api/kaos_credentials_local.py, which you create separately.
set -Eeuo pipefail
umask 077

SOURCE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LIVE="${KAOS_LIVE_API_ROOT:-$HOME/tradingwithkaos.com/backend}"
PY="${KAOS_PYTHON_BIN:-$HOME/virtualenv/tradingwithkaos.com/backend/3.11/bin/python}"
STAMPFILE="$LIVE/kaos-credentials-revision.txt"

FILES=(
  apps/api/kaos_credentials.py
  apps/api/db.py
  apps/api/kaos_r2_archive.py
  apps/api/integration_config.py
)

command -v git >/dev/null
test -x "$PY" || { echo "Missing cPanel Python environment: $PY"; exit 1; }
test -d "$LIVE" || { echo "Missing live backend: $LIVE"; exit 1; }
test -f "$LIVE/apps/api/server.py" || { echo "Missing live FastAPI server"; exit 1; }

# Refuse to deploy an uncommitted or stale checkout, matching the other scripts.
git -C "$SOURCE" fetch origin main
HEAD="$(git -C "$SOURCE" rev-parse HEAD)"
MAIN="$(git -C "$SOURCE" rev-parse origin/main)"
test "$HEAD" = "$MAIN" || { echo "Checkout is not the latest GitHub main. Stop."; exit 1; }
test -z "$(git -C "$SOURCE" status --porcelain)" || {
  echo "Source checkout has uncommitted changes. Stop."
  exit 1
}

# Compile everything before touching the live tree.
for file in "${FILES[@]}"; do
  test -s "$SOURCE/$file" || { echo "Missing source: $file"; exit 1; }
  "$PY" -m py_compile "$SOURCE/$file"
done

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP="$HOME/kaos-deploy-backups/credentials-$STAMP"
mkdir -p "$BACKUP"
for file in "${FILES[@]}"; do
  mkdir -p "$BACKUP/$(dirname "$file")"
  if test -f "$LIVE/$file"; then
    cp -p "$LIVE/$file" "$BACKUP/$file"
  fi
done
echo "Backup: $BACKUP"

for file in "${FILES[@]}"; do
  mkdir -p "$LIVE/$(dirname "$file")"
  install -m 0644 "$SOURCE/$file" "$LIVE/$file"
  echo "staged $file"
done

# Warn (never fail) when the deployment-local secret file is absent: the host
# .env may already carry these values.
if test -s "$LIVE/apps/api/kaos_credentials_local.py"; then
  chmod 600 "$LIVE/apps/api/kaos_credentials_local.py"
  echo "deployment-local credentials: present (mode 600)"
else
  echo "NOTE: $LIVE/apps/api/kaos_credentials_local.py is absent."
  echo "      Keys will come from the process environment / .env only."
fi

"$PY" -m py_compile "$LIVE/apps/api/kaos_credentials.py" \
                    "$LIVE/apps/api/db.py" \
                    "$LIVE/apps/api/kaos_r2_archive.py" \
                    "$LIVE/apps/api/integration_config.py"

# Confirm the new catalog entries survived the copy.
grep -q '"alpha_vantage"' "$LIVE/apps/api/integration_config.py" \
  && grep -q '"fred"' "$LIVE/apps/api/integration_config.py" \
  && grep -q '"cloudflare_r2"' "$LIVE/apps/api/integration_config.py" \
  || { echo "Integration entries missing after copy. Restore from $BACKUP"; exit 1; }

printf '%s %s\n' "$STAMP" "$HEAD" > "$STAMPFILE"
chmod 644 "$STAMPFILE"

# Passenger picks this up without a panel restart.
mkdir -p "$LIVE/tmp"
touch "$LIVE/tmp/restart.txt"

echo "Deployed $HEAD at $STAMP"
echo "Verify: curl -sS https://api.tradingwithkaos.com/api/health"
echo "Rollback: cp -p $BACKUP/apps/api/*.py $LIVE/apps/api/ && touch $LIVE/tmp/restart.txt"
