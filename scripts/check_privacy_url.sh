#!/usr/bin/env bash
# Verify a privacy policy URL returns the policy itself in raw HTML (no JS, no bot challenge),
# which is what Chrome Web Store review requires.
set -euo pipefail
URL="${1:-https://tradingwithkaos.com/privacy.html}"
body=$(curl -sSL -m 30 -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36" -w '\n%{url_effective} %{http_code}' "$URL")
final=$(tail -n1 <<<"$body")
echo "final: $final"
fail=0
grep -qi "<title>Human verification" <<<"$body" && { echo "FAIL: bot challenge page served instead of policy"; fail=1; }
grep -q "<h1>Privacy Policy</h1>" <<<"$body" || { echo "FAIL: policy heading not in raw HTML (SPA shell or homepage served)"; fail=1; }
grep -q "Limited Use" <<<"$body" || { echo "FAIL: Chrome Web Store Limited Use section missing"; fail=1; }
[ "$fail" = 0 ] && echo "OK: $URL serves the privacy policy"
exit "$fail"
