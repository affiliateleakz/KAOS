# API verification handoff for hosting support

The Python app is configured under `/home/itsabout/tradingwithkaos.com/backend`, serving `api.tradingwithkaos.com`. Previous local WSGI testing returned JSON successfully; that does not verify the current public request path.

## Message to send to support

> External read-only API checks are receiving HTTP 200 `text/html` pages identified as **Bot Verification**, rather than application JSON, from these routes:
>
> - `https://api.tradingwithkaos.com/api`
> - `https://api.tradingwithkaos.com/api/billing/memberships`
> - `https://api.tradingwithkaos.com/api/v1/extension/google/config`
>
> This occurred with both KAOS API and Store-readiness user agents and a website Origin header. Earlier requests from another client received JSON, so please investigate differences in the hostname's security/routing path and correlate request logs. Please identify which layer produces the verification response and ensure legitimate API requests can reach Passenger without an interactive browser challenge. Stripe signed webhook requests to `/api/stripe/webhook` also need a browserless route to the application. Keep application authentication, webhook signatures and rate controls intact; do not broadly disable security. Please share the cause and the specific adjustment made so we can repeat external verification.

No support message has been sent automatically. Do not include API keys, cookies, tokens, `.env` contents or full private logs in the support request.

## Repeat after support responds

From the updated repository, run:

```bash
/home/itsabout/virtualenv/tradingwithkaos.com/backend/3.11/bin/python scripts/check_hosted_launch.py
```

The checker makes six GETs, prints only selected public result fields, and changes no settings. It does not submit webhook events or sign anyone in. Run it from an external computer as well if possible; cPanel-to-site traffic may take a different route. A single passing check is a point-in-time observation, not proof that every client is unblocked.

Expected: health and Google configuration return JSON, website-origin CORS matches the website, and the saved membership catalog matches the approved tiers. A failing catalog check is an application-settings issue separate from the verification page: review **Admin → Settings → Membership Plans → Use current KAOS plans → Save Plans**. Existing Stripe subscriptions are not repriced.

Actual Google sign-in, password recovery and signed Stripe delivery still require their own acceptance checks. Current login-validation hosting intentionally blocks billing; removing a challenge does not enable checkout or prove that billing is ready. Do not infer a fresh CPU/I/O exhaustion incident solely from these responses.
