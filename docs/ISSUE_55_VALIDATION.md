# Issue #55: validation evidence and remaining gates

Reviewed development baseline `868c58e95e3a09364ccf98cc1947afa990164097`
and draft PR #54 on 2026-11-13 (Pacific time). Production remains on hold.

## Login compatibility

A read-only GET to `https://api.tradingwithkaos.com/api` returned native-wsgi
build `1.1.11-full-admin-repair`; `/openapi.json` returned 404. No real user
credentials were submitted. The issue reports the live v1 login route is absent.
The deployed `wsgi_app.py` is not in the reviewed source tree. Its account schema,
password verification, session cookies, token signing and revocation mechanisms
cannot be inferred from a health response.

The extension now identifies a missing login route as `INCOMPATIBLE_SERVER`,
recognizes the legacy runtime through GET `/api`, and explains the required
server compatibility update. It never resends passwords to guessed legacy
routes or treats a cookie-only response as an extension bearer session.
**This improves diagnosis; it does not restore sign-in on the live legacy API.**

A new isolated test verifies the source FastAPI web/extension paths use the same
account password hash, user ID, token version and access/refresh claims, and that
extension tokens resolve through the common authentication authority. Existing
suites test lockout, revoked accounts/devices, license checks, Google identity
verification, CORS and broker login isolation. These tests do not establish
parity with the unavailable deployed legacy source or provider/browser behavior.

The least disruptive next step is an offline review of the deployed native WSGI
source and sanitized schema documentation. If it can issue and verify the v1
bearer contract with existing account/revocation authority, implement the full
login/refresh/logout/device/license contract there, with regression tests; merely
aliasing the login URL is insufficient. Otherwise migrate to validated FastAPI
as a separately approved release. Do not deploy a speculative WSGI shim.

## Automated evidence

- Python 3.11.18 installed the pinned API requirements successfully.
- API suite against local MongoDB 7: 338 passed, 2 skipped, 5 subtests passed.
- Collectors: 84 passed; core: 25; strategy_v2: 6; strategy_v2_1: 6.
- Node login compatibility tests: 4 passed; broker isolation tests: 2 passed.
- Staging/package tests: 5 passed, including symlink refusal, checksum failure,
  immutable revision directories, private permissions, ZIP layout and secrets.
- React production build used `REACT_APP_BACKEND_URL=https://api.tradingwithkaos.com`.
- Both real cPanel ZIPs built; extracted backend served GET `/api` through the
  Passenger/a2wsgi adapter under Python 3.11 using a local test database.
- actionlint, Bash syntax, extension JS syntax, Python compilation and focused
  fatal-error Python lint passed. This is not a full repository style audit.
- The optional research learning files are absent, so that CI job's conditional
  suite is skipped as on the original branch.

Resource limits and installed system libraries on Asura remain untested. The
WSGI smoke test covers an HTTP request, not ASGI lifespan handling. Source ASGI
startup creates indexes and seeds accounts/demo data; never run it against the
production database as a supposed read-only compatibility test. Validate startup
and Passenger lifecycle explicitly in an isolated host environment first.

## GitHub-to-Asura status

GitHub reported no configured environments, and only CI registered as an Actions
workflow. The upload file is absent from default branch `main`, so normal
`workflow_dispatch` cannot yet be exercised. Do not merge merely to bypass this
gate. The owner must configure `kaos-hosting`, environment approval protection,
verified SSH host/user/port and dedicated deployment secrets through GitHub.
No Asura credentials were available in this environment. No SSH connection or
actual private upload was attempted; remote staging acceptance remains open.

The manual workflow builds ZIPs and invokes the tested staging script. It never
extracts ZIPs, restarts Passenger, changes database settings, or activates releases.
A completed release has checksummed ZIPs, RELEASE.txt and COMPLETE. Incomplete
uploads cannot masquerade as verified releases and cannot overwrite prior ones.

## Recoverable activation procedure (requires separate owner approval)

1. Inventory actual document roots, proxy routes, Python environment, current
   entrypoint/source and dependency versions. Back up the complete live website,
   native WSGI app, environment configuration and database through restricted
   owner-controlled storage. Record checksums and test restoration in isolation.
2. Restore a database snapshot into an isolated database with a separate account.
   Disable outbound mail, payments, collectors and all broker execution. Preserve
   IDs, bcrypt hashes, token versions, membership, devices, revoked status and
   licenses. Compare legacy/source schema without logging private records.
3. Test email login, refresh/restart/logout, old-session behavior and revocation;
   Google OAuth client/audience/origin configuration; actual extension ID and
   CORS/preflight; paid/free licenses and device limits. Independently test Pocket
   Option login with KAOS signed out and through MV3 restarts. No trading orders.
4. Explicitly document whether old sessions survive or require re-login; do not
   weaken signature checks or reuse an incompatible legacy token format. Review
   index/schema changes, seeding and any data transformations. Backward-incompatible
   database changes require their own recovery plan before activation.
5. Present the exact verified SHA, backups, parity results, maintenance window,
   database change plan and rollback steps for owner approval. Approval for a
   private upload is not approval for activation, payments or live trading.
6. Only after that approval, activate the reviewed release with controlled writes.
   Check GET `/api` (do not assume legacy `/api/health`), website assets, CORS,
   login/refresh and device/license paths. On failure restore the entire old app,
   entrypoint, dependency environment and website, restart Passenger and recheck.
   Restore DB only under the approved write-freeze/reconciliation plan; avoid
   discarding writes made after a backup. Retain the previous release and backups.

The disclosed broker-vault key requires a separate reviewed re-encryption or
broker reconnection plan with verified backups. Do not rotate it in place or put
it in GitHub. Keep real payments and live trading disabled until separately
validated and approved.
