# Code audit and chart-data repair

**Subsequent extension release 1.7.17:** the owner explicitly requested enabling
extension trading after this audit. The four extension read-only switches are now
off and the manual Start/Stop interface is restored. This does not resolve the
open findings below, validate strategy profitability, or enable website/backend
trading or payments. The read-only statements in this report describe 1.7.16.
Regression fixtures verify authorized Start, unauthorized denial, stopped-order
rejection and absence of automatic Start during login/chart navigation. No real
broker orders were submitted by these tests.

Scope: development branch `chatgpt/deepscan-critical-repairs-20261018`, starting at
`7f053d4a1eeb53b6a3cb9833f2e7e1a24d0de0ae`, for issue #55 / draft PR #54.
This is a repository-wide automated sweep plus focused review of authentication,
device authorization, chart ingestion, order boundaries, billing and deployment.
It is **not a certification that every path is correct or safe for live trading**.
No production database, real broker account, payment account or hosting files were
changed by this audit. Trading remains disabled in extension 1.7.16.

## Chart defects repaired

* The dashboard mirrored chart canvases without starting the candle poller.
  Polling now starts after an authorized broker connection, continues across
  Dashboard/Charts navigation and stops on sign-out. Generation checks discard
  stale responses after logout; concurrent polls cannot overlap.
* The generic cloud message handler could answer attachment messages before their
  dedicated handler. Response ownership now excludes dedicated message types,
  including three previously unreachable training handlers.
* An early ping could report readiness before the content engine existed.
  Attachment recovery now checks the actual terminal-snapshot listener, with a
  timeout, and uses the authorized worker instead of repeatedly injecting and
  resetting WebSocket guards in an already-open page.
* Historical candle ingestion fabricated flat candles across missing timestamps.
  It now retains only supplied, finite, logically valid OHLC bars. Tick ingestion
  validates asset/price and rejects messages from other windows.
* Dashboard archives are labeled RECORDED rather than LIVE. Empty data shows
  receiver/store/waiting information. An unsupported hard-coded performance
  claim was removed. The connected sign-out control is visible and clickable.

Pocket Option is the currently implemented broker integration. Other broker
cards do not establish working market feeds. Browser regressions use explicit
candle fixtures; they do not prove the current provider's live wire format.

## Other repairs

* Stripe checkout completion no longer activates an unpaid or incomplete session.
  Paid asynchronous completion is handled explicitly. No real payments were made.
* Replaced the deprecated CRA/CRACO build chain with Vite; preserved `build/`,
  the public backend/Google configuration, alias, development proxy and Docker
  binding. Only explicitly public environment values enter the browser bundle.
* Updated vulnerable Python runtime libraries, including FastAPI/Starlette,
  MongoDB drivers, Pillow and JWT dependencies; removed unused JOSE/OAuth packages.
  Added a real PNG-rendering compatibility test and read-only hosting preflight.
* Local research HTTP service now validates loopback Host and explicit Origin,
  rejects wildcard/null origins, bounds request bodies and supports an optional
  bearer token. For an unpacked extension, configure its exact origin with
  `KAOS_RESEARCH_ALLOWED_ORIGINS`; the default published ID may differ. The
  extension does not currently supply the optional token automatically.
* Added durable browser regressions and CI coverage for research service security,
  dashboard candle polling, content ingestion and website authentication layout.

## Validation

| Component | Result |
| --- | --- |
| API, Python 3.11.18 / MongoDB 7 | 366 passed; 2 skipped; 1 expected failure; 5 subtests passed |
| cPanel/package/runtime scripts | 33 passed |
| Local research HTTP security | 6 passed |
| Collectors | 84 passed |
| Core library | 25 passed |
| Strategy v2 / v2.1 | 6 / 6 passed |
| Extension Node regressions | 28 passed |
| Broker-login isolation | 2 passed |
| Web unit tests | 5 passed |
| Chromium fixtures | Login at desktop/390px/320px; dashboard polling + sign-out; real content script ingestion with a history gap |
| Builds | Clean npm installation; production build; hosting Node 20.20.2 build compatibility |
| Static checks | Python syntax/fatal lint; JS/JSX/TS parsing; actionlint; diff whitespace checks |

The expected failure is `test_audit_session_revocation_gap.py`, a strict regression
documenting AUDIT-AUTH-1 below. It is not counted as a passing security check.
The two API skips are existing optional integration tests. Browser tests use
mock accounts/providers; no real Google OAuth flow or broker order is exercised.

Dependency advisories at the audit snapshot:

| Scope | Before | After |
| --- | --- | --- |
| Web npm dependency tree | 91 (22 high, 55 moderate, 14 low) | 0 known |
| Clean tested Python environment | 100 advisories across 13 packages | 0 known |
| Mobile dependency tree | 18 (5 high, 12 moderate, 1 low) | Unchanged; open |

Counts include development/build packages and are not counts of proven exploitable
application flaws. Registry results change over time. Updating repository pins
does not upgrade hosting or remove stale packages from an existing environment.
Bandit reported 0 high, 14 medium and 21 low findings, requiring contextual triage;
fallback IP strings and local-only model loading account for some findings.
History scanning found two instances of an existing deliberately fake test JWT
constant, not verified live credentials. This does not clear secrets exposed
outside Git. The initial inventory covered 534 tracked files and 223 Python files;
new tests/configuration are included in this change.

## Remaining findings and release blockers

| ID / severity | Evidence and consequence | Required follow-up |
| --- | --- | --- |
| AUDIT-AUTH-1 / High | Extension refresh JWTs contain user/version claims but no revocable installation/session binding. Device revocation and local logout do not invalidate an already-issued refresh token. The strict expected-failure regression reproduces this. | Design server-side session binding, rotation/reuse detection and a deliberate legacy-session migration. Test revoke/logout/re-enrollment and all clients before rollout. Do not blindly rotate keys or invalidate every account. |
| AUDIT-FINANCE-1 / High | Legacy affiliate writes can partially complete without required transaction mode; complete provider reconciliation, retry/order/expiry coverage and production index readiness are unproven. Checkout paid gating alone does not establish financial correctness. | Verify replica-set transactions, required indexes, idempotent reconciliation and signed Stripe test-event cases before enabling payments. |
| AUDIT-DEPLOY-1 / High | Passenger WSGI wrapping does not establish ASGI lifespan/index setup. Startup includes writes/seeding, so importing successfully is not proof of production readiness. Hosting MongoDB version is unverified. | Run read-only compatibility preflight, inspect indexes and perform a separately reviewed migration/readiness check. Never invoke startup against production as a read-only test. |
| AUDIT-UI-1 / Medium | Some broker/research strings still enter legacy popup `innerHTML` templates. MV3 CSP reduces some paths but is not a substitute for escaping. | Replace dynamic HTML interpolation or consistently escape/validate external fields; add hostile-payload regressions. |
| AUDIT-XML-1 / Medium | External feed parsing uses ElementTree without a complete application-specific resource/DTD policy. | Bound downloads and harden parsing; exercise hostile and oversized feeds. |
| AUDIT-MOBILE-1 / High | Mobile has 18 dependency advisories, including Expo/router dependencies needing coordinated upgrades; authentication remains a development-token starter. | Upgrade/test the supported Expo SDK and complete production authentication before distribution. TypeScript passed; no device build/OAuth integration was validated. |
| AUDIT-OPS-1 / High | Previously disclosed broker-vault key remains compromised; no authorized reconnection/re-encryption has occurred. Whole-release rollback and private GitHub-to-host SSH staging are not fully proven. | Reviewed key migration/reconnect and recovery rehearsal with owner approval. Do not expose or blindly rotate the key. |

Native Windows installer/trainer behavior, model availability and all model outputs
were statically inspected only. Windows, native messaging, signed mobile builds,
external providers and real-money execution were not validated here. Archived
strategy results include failing/negative results; unit tests do not prove
profitability. The full historical datasets needed to reproduce all claims are
not available in this checkout. A full human line-by-line review and independent
security assessment remain appropriate before handling live funds.

## Install the chart fix

Use the **1.7.16** extension artifact from the successful CI run for this commit.
Extract over the same existing unpacked extension folder, then click **Reload**
in `chrome://extensions`. Do not remove the extension or clear its storage:
that changes the installation identity. Keep Pocket Option open and signed in,
then open KAOS and connect that broker. The dashboard should begin receiving
closed candles without first opening Charts. The primary feed repair is in the
extension; updating the website alone cannot install it.

This build rejects extension start/order commands at the popup, worker, content
and MAIN-world bridge boundaries. Manual broker WebSocket traffic is preserved.
No approval to enable live trading or payments is inferred from installing charts.

## Hosting update constraints

The new Python pins require Python 3.11+ and **MongoDB 4.4+**. Before upgrading
the hosting virtual environment, run this read-only check from the updated checkout:

```bash
/home/itsabout/virtualenv/tradingwithkaos.com/backend/3.11/bin/python scripts/check_cpanel_runtime.py
```

Stop on failure. Do not assume a newer PyMongo can connect to an older server.
Review environment rollback first: changing dependencies affects the retained
legacy WSGI app too. Prefer validating a separate virtual environment before
changing the active one. Installing the new requirements will not uninstall
unused vulnerable packages left by older releases. Do not blindly uninstall
packages required by the legacy application.

Vite requires Node >=20.19; the discovered hosting Node 20.20.2 meets this.
`npm run build` still produces `apps/web/build`; packaging/deployment uses that
directory. Preserve backend `.env`, root `.htaccess`, uploads and hosting settings.
Follow `ASURA_GITHUB_DEPLOY.md` for preparation and explicit activation; this audit
does not activate hosting, merge PR #54 or configure missing SSH credentials.
Existing file-by-file activation is not a whole-release atomic swap. A complete
backup/restore was declined earlier and has not been demonstrated.

## Reproduce the main checks

Run each Python component from its own directory (the two strategy suites share
a test-module basename). Set `PYTHONPATH` to the absolute `packages/kaos-core`
directory. API tests additionally require a disposable MongoDB and test-only
`MONGO_URL`, `DB_NAME`, and `JWT_SECRET`.

```bash
python -m pytest -q scripts/tests
node --test apps/extension/test_cloud_login.cjs apps/extension/test_chart_session.cjs apps/extension/test_chart_data_audit.cjs
python -m pytest -q apps/extension/test_broker_login_isolation.py
cd apps/web
npm ci
npm test
REACT_APP_BACKEND_URL=https://api.tradingwithkaos.com npm run build
node ../../scripts/browser/run.cjs
```

Browser checks require installed Chrome/Chromium (`CHROME_BIN` is supported) or
the matching Playwright Chromium download. They use fixture accounts and candles.
