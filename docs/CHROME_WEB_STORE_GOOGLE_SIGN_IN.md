# Google sign-in rejection — Red Potassium

**The only target item is `gbobopmnjgeeegniphckfpalhnebapjm`.** Upload an update
to this existing item. Do not create a different listing or register OAuth for
the previous unpacked ID `pnbakkallmfhliciobnamffmhclkgofb`.

Google sign-in is retained in extension **1.7.28**. The code checks backend configuration when the diagnostic route is available,
requires the official item ID,
checks that the server/manifest OAuth clients match, bounds network requests,
refreshes an invalid Chrome token once, and identifies hosting HTML challenges.
It never saves the Google access token as a KAOS session.

## Confirmed live blocker

Read-only health checks and an empty token-exchange request from the development
environment received HTTP 200 HTML titled **Bot Verification**, not API JSON.
This proves those requests are challenged from this network; it does not prove
that every user or Google's reviewer sees the same challenge. It prevents
confirming live OAuth readiness. No credentials or real Google tokens were sent.

Send Asura support:

> Requests to https://api.tradingwithkaos.com/api and
> https://api.tradingwithkaos.com/api/v1/extension/google/access-token return
> HTTP 200 text/html with title "Bot Verification" and lsrecaptcha instead of
> API JSON from an external network. This is an API used by our Chrome extension
> and Chrome Web Store reviewers; they cannot complete a JavaScript/CAPTCHA
> challenge. Please remove browser-verification challenges from this API host
> while retaining normal firewall/rate-limit protections, then confirm external
> requests reach Passenger and return JSON.

## Required OAuth configuration

1. In Google Cloud Console → APIs & Services → Credentials, use a **Chrome
   Extension** OAuth client registered for **`gbobopmnjgeeegniphckfpalhnebapjm`**.
   A web-app OAuth client and a client for another extension ID will not work.
2. Its public Client ID must match `apps/extension/manifest.json` →
   `oauth2.client_id` and the hosting environment's
   `KAOS_GOOGLE_EXTENSION_CLIENT_ID`. No client secret belongs in the extension.
   The current manifest ID is not proof that Google Cloud is correctly registered.
3. Verify the Google Auth Platform audience/publishing state permits the reviewer
   to sign in. A Testing app limited to named test users is not a public sign-in
   experience; complete any Google-required consent/verification work.
4. The backend must provide POST `/api/v1/extension/google/access-token` with
   Google token verification and its own configured OAuth allowlist. GET
   `/api/v1/extension/google/config` is an optional diagnostic on newer backends.
   Extension 1.7.28 continues to the verified exchange if that GET returns 404;
   it still rejects explicit configuration errors or mismatched clients.
5. Extension 1.7.27 includes the owner-provided manifest public key. Its SHA-256
   identity was verified against this exact store item. Unpacked installations
   must show `gbobopmnjgeeegniphckfpalhnebapjm` in `chrome://extensions`. A public
   key is not a private signing key; no private signing material is included.

The public store-download endpoint returned 404 during the original investigation.
The owner subsequently supplied the listing public key, which is now verified
and included in the manifest. Google Cloud and hosting configuration have not
been changed by this work.

## Before resubmitting

Run `python scripts/check_extension_google_login.py` from an external network.
A passing check confirms health/configuration only, **not a successful Google
sign-in**. On older backends, a missing diagnostic route makes this checker report
404; verify the environment setting manually and test the real Google exchange.
That missing diagnostic does not itself prevent sign-in in extension 1.7.28. Then test the actual store-ID build with a fresh Chrome profile:

1. Sign into Chrome with a Google account allowed by the production consent app.
2. Open KAOS and choose Continue with Google. Complete Google's consent.
3. Confirm the KAOS account is created/linked correctly, a KAOS session is saved,
   and reopening KAOS restores it. Do not start trading to test authentication.
4. Verify cancellation, signing out, email/password fallback, and a second Google
   account. Distinguish membership/device denial after successful authentication
   from a Google sign-in error.
5. Provide the reviewer reproducible steps and any required review-account access
   through the Developer Dashboard's private reviewer instructions. Do not put
   credentials in source, the public listing, or this document. Do not bypass
   membership/device controls for reviewers.

Suggested reviewer note after completing those checks:

> This update retains Google sign-in for item gbobopmnjgeeegniphckfpalhnebapjm.
> Open KAOS, click Continue with Google, and complete Google consent in Chrome.
> KAOS then exchanges the verified Google token for a KAOS session. Membership
> checks occur afterward. Email/password sign-in is also available. [Add the
> actual tested version, date and required account-access instructions privately.]

Do not claim the rejected functionality has been verified until the real Google
flow succeeds. The ZIP is a review candidate, not evidence of Google approval.

## Compatibility correction in 1.7.28

The live API health route returned valid JSON, the optional Google configuration
GET returned 404, and an empty request to the existing Google exchange returned
400 "Google access token required". This shows the exchange is installed and its
OAuth environment variable is set; no real token or account was used. Versions
1.7.26–1.7.27 incorrectly treated that missing GET as a missing server setting.
Version 1.7.28 fixes that compatibility error without weakening token verification.

## Microsoft Edge support — 1.7.36

Edge does not implement Chrome's `identity.getAuthToken`. This release uses
`identity.launchWebAuthFlow` for Edge (also falls back when a browser explicitly
reports that the Chrome API is unsupported). Chrome retains its manifest client.
The official extension ID and public key are unchanged.

Owner setup in Google Cloud Console:

1. Create an OAuth **Web application** client in the existing Google project.
2. Add this exact authorized redirect URI for the supplied store-ID build:
   `https://gbobopmnjgeeegniphckfpalhnebapjm.chromiumapp.org/google`
3. In the cPanel Python application's environment, set
   `KAOS_GOOGLE_BROWSER_CLIENT_ID` to that web client's public Client ID and
   restart the Python application after deploying `apps/api/routes_extension.py`.
   Keep `KAOS_GOOGLE_EXTENSION_CLIENT_ID` unchanged for Chrome. No client secret
   is needed or embedded for this browser token flow.
4. Install extension 1.7.36, confirming its ID remains
   `gbobopmnjgeeegniphckfpalhnebapjm`. An independently published Edge store item
   can have a different ID and needs a separately supported redirect/identity;
   this package does not claim to support an arbitrary store ID.

The client pins the redirect origin/path and validates a fresh, unpredictable
OAuth state before accepting a response. Google tokens are exchanged only with
the configured KAOS API and never saved in extension storage. The backend
verifies the token with Google, pins its audience to either configured client,
and verifies email ownership before issuing KAOS tokens. Provider errors and
cancellation cannot establish a KAOS session.

Syntax and packaging checks completed. Live Edge consent remains unverified
until the owner configures the web client and completes sign-in. This update
places no orders, sends no payouts, and changes no trading permissions.
