# KAOS easy cPanel upload (existing domains)

This is a **package-and-upload guide**, not permission to replace the currently running production website or backend. The packages come from PR #54 until it is validated and approved. Do not upload to the live domains until the release tests, backups, and owner approval are complete.

## Download the two ZIPs

1. Open [GitHub Actions](https://github.com/affiliateleakz/KAOS/actions) and select the successful CI run for the approved revision.
2. Under **Artifacts**, download `kaos-cpanel-website` and `kaos-cpanel-backend`. GitHub wraps each artifact in an outer ZIP; extract that outer ZIP on your computer to obtain `kaos-cpanel-website.zip` and `kaos-cpanel-backend.zip`.
3. These are **already packaged**. You do not need to run npm on cPanel or manually copy each repository folder.

## Upload website (tradingwithkaos.com)

1. In cPanel File Manager, identify the actual document root for `tradingwithkaos.com` (often `public_html`).
2. Make a full backup of the current site, `.htaccess`, and any non-generated files. Do not delete an unknown file or overwrite unrelated applications.
3. After release approval, upload `kaos-cpanel-website.zip` into the domain's document root; select **Extract**. Its `index.html`, `static/`, `privacy.html`, and `.htaccess` are at the ZIP root, so there should be no extra enclosing `build/` directory.
4. Confirm `https://tradingwithkaos.com/privacy.html` serves the real policy instead of an anti-bot challenge or React homepage.

## Upload API (api.tradingwithkaos.com)

1. In cPanel **Setup Python App**, first identify the currently running application root and startup file for `api.tradingwithkaos.com`. Back them up and save the existing environment settings **without exposing secrets**. If you cannot identify them, stop; the source does not prove which runtime is deployed.
2. After approval and a rollback plan, upload `kaos-cpanel-backend.zip` into that **Python application root outside the website document root**. Select **Extract**. The ZIP root contains `passenger_wsgi.py`, `apps/api/`, and `packages/kaos-core/`.
3. Confirm Python 3.11 and entry point `application` in Setup Python App. Activate the app's virtual environment and install `pip install -r apps/api/requirements.txt` (your host must support the dependencies).
4. Keep existing production secrets in cPanel environment settings; never copy secrets into GitHub or send them in chat. Verify `MONGO_URL`, `DB_NAME`, `JWT_SECRET`, and `FRONTEND_URL=https://tradingwithkaos.com`; set `API_PUBLIC_ORIGIN=https://api.tradingwithkaos.com` where used. Leave live-trading and unvalidated AI execution flags disabled.
5. Restart the Python app and check `https://api.tradingwithkaos.com/api/health`. The API should be mounted at the subdomain root, **not** at `/api`, because its own routes already start with `/api`.

## Verify and roll back

Test website registration, login, extension authentication, Pocket Option login while KAOS is signed out, broker connection, membership limits, logout, and `privacy.html` before declaring the deployment successful. A passed GitHub build or API health endpoint is insufficient. If authentication fails, restore the backed-up website and backend together and the previous environment configuration; do not modify the production database as a rollback shortcut.

**Chrome extension:** The separate `kaos-chrome-extension-zip` is for the Chrome Web Store/unpacked testing, not the website directory. **Mobile app:** The Expo source is not an installable APK/iOS release.

**Note:** CI packages use `REACT_APP_BACKEND_URL=https://api.tradingwithkaos.com` at web build time. Staging would require a separate build with its own API hostname.
