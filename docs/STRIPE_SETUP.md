# Stripe membership checkout

The current flow is **choose a paid plan → sign up or sign in → Stripe Checkout → verified payment → paid membership**. It no longer sends a new paid buyer to the dashboard to choose/pay again. Signed-in buyers go directly to checkout for the selected plan. Free signup remains free and does not call Stripe.

## Activate the configured checkout on cPanel

The owner has requested paid membership checkout. Install the matching tested website/backend release first; the previous Passenger wrapper forced login-validation mode even when Stripe credentials were saved.

In **cPanel → Setup Python App → api.tradingwithkaos.com → Environment variables**, set:

```text
KAOS_STRIPE_CHECKOUT_ENABLED=true
KAOS_LOGIN_VALIDATION_MODE=false
```

Save and **restart the Python application**. These are nonsecret settings, not API keys. Setting only a shell variable in Terminal does not persist the Python app's environment. The updated wrapper also defaults validation off when checkout is explicitly requested and no validation override was set; an explicit `KAOS_LOGIN_VALIDATION_MODE=true` still blocks payments.

The explicit flag enables only membership checkout, billing status/portal/cancellation and the signed Stripe webhook route through the hosting policy. Other trading, payouts, refunds and unrelated write permissions are not enabled by it. Saving a key or installing the files with the flag absent does not activate checkout or create a charge. Coinbase has its own flag and worker requirements.

In **Admin → Commerce Setup → Stripe**, confirm:

- Membership payments are selected.
- The saved environment matches the payments key: Live uses `sk_live_` or a properly permitted `rk_live_`; sandbox uses the corresponding test key.
- The signing secret belongs to that environment's webhook destination: `https://api.tradingwithkaos.com/api/stripe/webhook`.
- Save before running the API connection check. Sandbox/live credentials are stored separately under the existing commerce vault key; do not replace that encryption key.

Use `/api/billing/availability` or **Admin → Launch Status** to check that `checkoutEnabled` is true and the mode is the one intended. If `configurationReady` is false, resolve the saved provider selection/mode/key/signing-secret configuration first. The connection check does not prove inbound webhook delivery.

## Customer behavior

Paid homepage and membership links open `/checkout?plan=<exact-plan-id>`, retaining monthly/yearly choice, referral and campaign. A new customer creates a sign-in on that checkout page, then proceeds automatically to Stripe; an existing customer signs in with the plan retained. No paid access is granted on account creation or session creation. Card details are entered at Stripe, not on a KAOS form.

If checkout is disabled/unavailable when the page loads, paid signup/Google account creation is not offered. The customer sees an availability message and an explicit Free option rather than being registered and dropped into the dashboard. If the service fails after signup, the existing account remains unpaid and checkout offers a retry without another registration.

The backend selects price/currency/billing interval from saved server plans using the exact selected plan ID; it ignores a browser-supplied price or redirect origin. Returning to an unchanged open checkout reuses it. An open session with superseded pricing is expired before replacing it. A completed payment waits for reconciliation rather than making a second subscription. Cancellation retains the chosen plan for returning to checkout. Failed/missing payment verification never displays “payment received” or grants membership just because the browser returned to a success URL.

## Hosted acceptance still required

Verify the four saved amounts: Pro $29.95/month or $299.95/year; Ultimate $99.95/month or $995.95/year. Existing subscriptions are not repriced automatically. Use an isolated sandbox website/API/database for test payments; test subscriptions must not grant production access or accrue production commissions.

Then validate actual new email/Google buyer checkout, returning member sign-in, monthly/annual selection, cancellation/retry, signed webhook delivery, activation, renewals, failed invoices, refunds/disputes and affiliate invoice reconciliation. Existing active subscribers manage billing instead of creating a second subscription. Stripe portal plan-change/proration settings need their own account configuration.

An external client has received **Bot Verification HTML** from the API hostname. This code cannot remove that hosting/security challenge. Resolve it for legitimate API clients and signed Stripe callbacks; see [API_HOSTING_HANDOFF.md](API_HOSTING_HANDOFF.md). Keep webhook signature validation and application authentication intact.

All repository/browser checks use fixtures or mocked Stripe APIs. No real customer, Stripe checkout session, charge, refund or payout is created by those tests. This workspace has not changed live hosting environment settings or Stripe Dashboard settings.
