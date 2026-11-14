#!/usr/bin/env bash
# Uses the verified kaos-host SSH alias. Never extracts or activates a release.
set -euo pipefail
: "${GIT_SHA:?A full commit SHA is required}"
[[ "$GIT_SHA" =~ ^[0-9a-f]{40}$ ]] || { echo 'Invalid commit SHA' >&2; exit 1; }
for file in kaos-cpanel-website.zip kaos-cpanel-backend.zip SHA256SUMS RELEASE.txt; do
  test -f "dist/$file"
done
ssh kaos-host bash -s -- "$GIT_SHA" <<'REMOTE'
set -euo pipefail
umask 077
base="$HOME/kaos_release_staging"
# Refuse symlinks and existing releases rather than following/overwriting them.
test ! -L "$base"
if test -e "$base"; then test -d "$base"; else mkdir -m 700 "$base"; fi
chmod 700 "$base"
mkdir -m 700 "$base/$1"
REMOTE
stage="kaos_release_staging/${GIT_SHA}"
scp dist/kaos-cpanel-website.zip dist/kaos-cpanel-backend.zip \
    dist/SHA256SUMS dist/RELEASE.txt "kaos-host:${stage}/"
ssh kaos-host bash -s -- "$GIT_SHA" <<'REMOTE'
set -euo pipefail
cd "$HOME/kaos_release_staging/$1"
chmod 600 kaos-cpanel-website.zip kaos-cpanel-backend.zip SHA256SUMS RELEASE.txt
sha256sum -c SHA256SUMS
test "$(cat RELEASE.txt)" = "KAOS revision $1"
# Only this marker denotes a completely uploaded, verified release.
(umask 077; printf '%s\n' "$1" > COMPLETE)
REMOTE
printf '%s\n' 'Release verified in private staging. No live activation performed.'
