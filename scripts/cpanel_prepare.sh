#!/usr/bin/env bash
# cPanel's Deploy HEAD Commit prepares a complete release, never activates it.
set -euo pipefail
umask 077
repo="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$repo"
python="$HOME/virtualenv/tradingwithkaos.com/backend/3.11/bin/python"
export PATH="/opt/alt/alt-nodejs20/root/usr/bin:$PATH"
test -x "$python"
command -v node >/dev/null
command -v npm >/dev/null
sha="$(git rev-parse HEAD)"
[[ "$sha" =~ ^[0-9a-f]{40}$ ]]
if test -n "$(git status --porcelain --untracked-files=normal)"; then
  echo 'Repository has local changes. Commit or resolve them before preparing a release.' >&2
  exit 1
fi
base="$HOME/kaos_cpanel_releases"
test ! -L "$base"
if test -e "$base"; then test -d "$base"; else mkdir -m 700 "$base"; fi
chmod 700 "$base"
# A private directory lock prevents concurrent builds sharing apps/web/build.
mkdir "$base/.prepare-lock" || { echo 'Another preparation may be running.' >&2; exit 1; }
work=''
cleanup() {
  if test -n "$work" && test -d "$work"; then rm -rf -- "$work"; fi
  rmdir "$base/.prepare-lock"
}
trap cleanup EXIT
test ! -e "$base/$sha" && test ! -L "$base/$sha" || {
  echo 'This revision already has a prepared release; it will not be overwritten.' >&2
  exit 1
}
work="$(mktemp -d "$base/.preparing.XXXXXX")"
(
  cd apps/web
  npm ci --no-audit --no-fund
  CI=false REACT_APP_BACKEND_URL=https://api.tradingwithkaos.com npm run build
)
"$python" scripts/build_cpanel_packages.py
cp dist/kaos-cpanel-website.zip dist/kaos-cpanel-backend.zip "$work/"
(
  cd "$work"
  sha256sum kaos-cpanel-website.zip kaos-cpanel-backend.zip > SHA256SUMS
  sha256sum -c SHA256SUMS
  printf 'KAOS revision %s\n' "$sha" > RELEASE.txt
  printf '%s\n' \
    'Website destination: /home/itsabout/tradingwithkaos.com' \
    'Backend destination: /home/itsabout/tradingwithkaos.com/backend' \
    'Preserve existing .htaccess, .env, uploads and unrelated applications.' \
    'PREPARED ONLY: no live files changed, no Passenger restart, no database changes.' > INSTALL_PLAN.txt
  printf '%s\n' "$sha" > COMPLETE
  chmod 600 ./*
)
# Publication occurs only after successful build, packaging and verification.
mv -- "$work" "$base/$sha"
work=''
printf 'Prepared release: %s/%s\n' "$base" "$sha"
printf '%s\n' 'Live installation has NOT been changed. Activation is a separate step.'
