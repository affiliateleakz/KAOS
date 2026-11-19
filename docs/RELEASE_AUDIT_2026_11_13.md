# KAOS release audit — 2026-11-13

**Scope:** Existing `affiliateleakz/KAOS` draft PR #54, branches and release packages. Reviewed the monorepo tree (~550 entries), critical API/extension/frontend/deployment/mobile sources, and GitHub CI evidence. This is **not** a line-by-line certification of every file, a hosted-browser test, a payment certification, or an independent trading-strategy validation.

**Release decision: HOLD production deployment and live trading.** Keep PR draft until live parity and release-gate evidence are collected.

## Confirmed and addressed in development branch

1. The Chrome extension previously installed Pocket Option's main-world WebSocket wrapper through unconditional manifest content scripts. Manifest injections were removed; explicit authorization/connection now registers temporary scripts. This still needs Chrome tests for service-worker suspension, logout, extension restart, and previously attached broker tabs.
2. Extension email login route mismatch (`/extension/login` vs actual `/auth/login`), device/me sequencing, and missing `/extension/me` were repaired earlier in PR #54; suite coverage expanded.
3. Web login requests `POST /api/auth/google/credential` and extension Google login requests `POST /api/v1/extension/google/access-token`. Both backend routes were missing. This audit added identity verification routes, with server-controlled Google OAuth client IDs; browser OAuth provisioning and endpoint integration remain untested.
4. The website account-response helper previously exposed nearly all database fields except password hash. Replaced with an explicit allowlist, and `GET /api/auth/me` now uses it. Development verification tokens now require explicitly configured dev/test environment.
5. v1 trading authorization previously permitted missing/unregistered device identity via `compute_license(user, None)`. It now requires a registered non-revoked device before trading telemetry/execution lifecycle operations.
6. Stripe Checkout and portal previously trusted the client-provided `origin_url` for payment redirect destinations. Redirect URLs now use server `FRONTEND_URL`.
7. cPanel website and backend ZIP builders added and passed on the previous baseline. These artifacts are **not** a proof of API hosting compatibility or safe production replacement.

## Known high-priority unresolved issues

**Hosting / runtime:** The backend deployed on `api.tradingwithkaos.com` has not been compared to the source backend; previous cPanel configurations mention different application roots / WSGI implementations. MongoDB, SSL, reverse-proxy path mapping, account migration, data backups and rollback have not been inspected. Hosted auth endpoints and privacy.html need direct tests.

**Google OAuth:** The new routes require `KAOS_GOOGLE_WEB_CLIENT_ID` and `KAOS_GOOGLE_EXTENSION_CLIENT_ID` set on the server. The React Google ID client and Chrome manifest client ID must match the intended Google OAuth configuration, registered origins and extension ID. Chrome extension manifest currently lacks a pinned extension `key`. Google sign-in is not ready without live provider verification. The old Emergent Google session endpoint is separate and may be obsolete.

**Registration/email:** Production no longer returns verification tokens in API responses. However, a verified production transactional email registration flow must be designed and tested. Password-reset emails still depend on an external Emergent integration key.

**Pocket Option:** Dynamic content-script registration is not a confirmed browser sandbox; it can still persist within a browser session across MV3 worker suspension. Test signed-out login, repeated browser tabs, broker navigations, worker restarts and logout while orders are not active. Test whether browser reloads affect independent Pocket Option sessions. Do not enable trading until the isolation and real execution path are fully validated.

**Financial correctness:** Stripe webhooks contain retry/lease and partial reconciliation code; integration against actual test-mode Stripe events including duplicates, timeouts, refunds, disputes, subscription changes, and idempotent affiliate reversals has not been verified. Do not enable real billing/affiliate payouts on unverified infrastructure.

**Execution:** Coinbase real orders are gated behind `KAOS_COINBASE_LIVE_ORDERS=enabled`, membership, consent, verified connection, and emergency stop checks, but no independent broker sandbox/live validation is present. Pocket Option market login and order lifecycle are not certified. Keep real-money trading off.

**Data / strategies:** Paper API accepts caller-supplied quote prices and explicitly labels them as simulations. Some source-side intelligence placeholders are not market-live. There is no verified out-of-sample profitability proof, audited real feed provenance, or approved AI trading authority.

**Mobile:** Expo app is a research-feed development foundation. It lacks production OAuth/PKCE, native Android/iOS release builds, and the complete website trading feature set.

**Web/extension release:** GitHub web build and extension smoke checks cannot verify actual login, session cookie behavior, CORS in production, Chrome extension ID, independent Pocket Option login, appearance on devices, Stripe flows, or Chrome Web Store policy review.

## Required evidence before deployment

- A documented inventory of currently deployed cPanel application root, frontend document root, Python/WSGI entrypoint, database/secret configuration (without disclosing secrets), reverse proxy configuration and rollback backup.
- API health + DB readiness, verified CORS/preflight from actual website and Chrome extension origin, exact route parity.
- Fresh account email and Google OAuth sign-in, browser restart/session refresh/logout, revoked devices, and plan-specific chart entitlement checks.
- Repeatable isolated Pocket Option login test while KAOS extension is installed but logged out. Regression tests for authorized connect, logout and MV3 restart.
- Staged Stripe test-mode checkout, cancellations, refunds/disputes, webhook retries and affiliate ledger reconciliation; signed test payloads.
- Paper trading with verified feed, journal persistence across restart and risk limits; **separate** real-money trading approval only after independent strategy/broker validation.
- Public privacy URL returns the actual policy with HTTP 200 from a normal browser and no anti-bot page.
- Full CI success at final commit, Chrome Web Store extension ID continuity, signed mobile builds if mobile distribution is required.

## Release posture

GitHub CI confirms automated test/build behavior only. ZIP presence means files are installable *in principle*, not that cPanel dependencies, settings, routes, and existing data will survive replacement. Do not automatically merge or deploy this branch. Explicit owner approval and recovery plan are required.
