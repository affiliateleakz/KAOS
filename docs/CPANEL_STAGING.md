# cPanel staging deployment

This guide describes a **private staging deployment** of the KAOS development branch; it is **not approval to update the live service**. Review [KNOWN_GAPS.md](KNOWN_GAPS.md) before testing. Keep real-money orders, real payment processing, affiliate payouts, and unvalidated AI execution disabled.

## Staging isolation and prerequisites

Prefer a separate **staging API hostname** and **staging website hostname**, rather than replacing `api.tradingwithkaos.com` or `tradingwithkaos.com` before release approval. If the existing production Python app is the only configured application, do **not** overwrite its files or change its environment. Back up the current site, application directory, and database configuration before any deployment.

Confirm that cPanel supports **Python 3.11**, **Setup Python App/Passenger**, virtual environments, and outbound connections to your staging MongoDB. This repo does not yet establish parity with the deployed production backend.

## Backend application layout

The repo-shaped layout below can be used with a *separate* cPanel Python application. The path `/home/itsabout/tradingwithkaos.com/backend/` is a proposed layout from the handoff, **not verified as your currently deployed application root**:

```text
/home/itsabout/tradingwithkaos.com/backend/
├── passenger_wsgi.py            # deploy/cpanel/passenger_wsgi.py
├── apps/
│   └── api/
│       ├── server.py
│       ├── requirements.txt
│       └── ...                   # full apps/api source
└── packages/
    └── kaos-core/                # full packages/kaos-core source
```

Keep the `apps/api` directory structure intact: the entry point expects `apps/api/server.py`. Upload `deploy/cpanel/passenger_wsgi.py` to the application root as `passenger_wsgi.py`. The pinned dependency list is `apps/api/requirements.txt` (there is **no root-level requirements.txt** in this layout).

In **Setup Python App**, choose Python 3.11, set the application root to your separate staging directory, startup file to `passenger_wsgi.py`, and entry point to `application` where supported. Activate cPanel's virtual environment, install dependencies with `pip install -r apps/api/requirements.txt`, then restart the staging application. The pinned dependencies are extensive and may exceed shared-hosting resources; installation and runtime support must be verified rather than assumed.

Configure application environment settings with **staging-only** values:

```dotenv
KAOS_ENV=staging
MONGO_URL=<staging MongoDB connection string>
DB_NAME=kaos_staging
JWT_SECRET=<unique randomly generated staging secret>
FRONTEND_URL=https://staging.tradingwithkaos.com
API_PUBLIC_ORIGIN=https://staging-api.tradingwithkaos.com
ADMIN_EMAIL=<staging administrator email>
ADMIN_PASSWORD=<unique staging password>
KAOS_DEMO_PASSWORD=
KAOS_COINBASE_LIVE_ORDERS=false
```

These example hostnames are proposed, not confirmed to exist. Change them to the **actual staging origins** and configure TLS/DNS first. Keep Stripe, broker order, and AI execution credentials unavailable to staging; confirm all financial and trading execution flags are disabled. Never commit .env files or credentials or paste secrets into chat. Allow only the staging server's outbound IP in the staging MongoDB provider's network access configuration.

The FastAPI backend already prefixes its routes with `/api`. Mount Passenger at the **API host root** to avoid accidental `/api/api/...` routing. Test:

```text
https://staging-api.tradingwithkaos.com/api
https://staging-api.tradingwithkaos.com/api/health
```

`/api/health` should return JSON with `"status":"ok"` and `"db":true` only when the service and MongoDB are available. A 404 can mean the wrong application/mount point is serving the URL. A successful health response **does not** prove Chrome extension login, CORS, membership, or broker integrations work.

## Static frontend

Build the React site from the repository root using the **actual staging API origin**:

```bash
cd apps/web
npm ci --no-audit --no-fund
REACT_APP_BACKEND_URL=https://staging-api.tradingwithkaos.com CI=false npm run build
```

The `REACT_APP_BACKEND_URL` value is embedded at build time; check the frontend's API routing to ensure it uses this value correctly. Upload the **contents** of `apps/web/build/` to the staging website's document root, not to production `public_html`. Copy `deploy/cpanel/frontend.htaccess` there as `.htaccess` only after backing up any existing rules and checking the host's Apache configuration. This preserves real files (including `privacy.html`) while routing React pages to `index.html`.

Check `https://staging.tradingwithkaos.com/privacy.html` from a normal browser and confirm it returns the actual full privacy policy, not a challenge or SPA homepage. Ensure the deployed frontend origin exactly matches `FRONTEND_URL` and CORS configuration.

## Validation before production approval

Test fresh registration, email and Google sign-in (where supported), KAOS extension authorization, Pocket Option login **while KAOS is logged out**, explicit broker connection, entitlement/chart limits, logout, and repeated browser restarts. Test payment and webhook integration only against explicitly configured test infrastructure. Keep real-money trading disabled.

Source control, GitHub CI, and these deployment instructions are **not evidence of a working cPanel deployment**. Record deployment revision, health checks, browser/network logs, and a rollback plan before requesting approval to merge or deploy.
