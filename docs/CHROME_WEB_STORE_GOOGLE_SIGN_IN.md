# Google sign-in rejection — Red Potassium

**The only target item is `gbobopmnjgeeegniphckfpalhnebapjm`.** Upload an update
to this existing item. Do not create a different listing or register OAuth for
the previous unpacked ID `pnbakkallmfhliciobnamffmhclkgofb`.

Google sign-in is retained in extension **1.7.26**. The code now checks backend
configuration before opening Chrome OAuth, requires the official item ID,
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
4. Deploy the matching backend (including GET
   `/api/v1/extension/google/config`) only when the owner authorizes installation.
5. For an unpacked test build, obtain **this item's public key** from the Chrome
   Web Store dashboard and add it as the manifest `key` in the local build. Verify
   `chrome://extensions` shows the exact item ID above. A public key is not a
   private signing key. Uploaded updates to the existing listing keep its ID.

The public store-download endpoint returned 404 during this investigation, so
no listing public key was recovered or invented. Google Cloud and hosting
configuration have not been changed by this work.

## Before resubmitting

Run `python scripts/check_extension_google_login.py` from an external network.
A passing check confirms health/configuration only, **not a successful Google
sign-in**. Then test the actual store-ID build with a fresh Chrome profile:

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
