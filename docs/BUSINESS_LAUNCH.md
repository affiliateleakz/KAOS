# KAOS business launch: working scope and acceptance checks

This is the current operational handoff. It supersedes historical pricing, branch, build and hosting assumptions in older audit notes. A passing repository test is not a verified hosted payment, delivered email, Chrome Store approval or profitable trading model.

## Current product and owner decisions

- Keep the approved Viking/black/gold homepage and current product screenshots. Do not restore older blue branding or illustrative profit/win-rate claims.
- Free: $0, one broker slot/device. Pro: $29.95/month or $299.95/year, four broker slots and three devices. Ultimate: $99.95/month or $995.95/year, four slots and five devices. Owner/super-admin device allowance is unlimited. Saved custom billing plans are not overwritten by this release.
- Pro private AI starts untrained; Ultimate may access separately validated/published pretrained models. Required service learning is disclosed. The dedicated worker is prepared but its hosting has not been chosen. Do not promise an operating continuous worker or available production pretrained models while launch status says otherwise.
- Affiliate rates remain Free 10/0/0%, Pro 30/15/0%, Ultimate 50/25/5% on qualifying actual payments, with the configured hold/refund accounting. Provider selections and ledger accrual do not mean cash payouts are active.
- Official Chrome item ID: `gbobopmnjgeeegniphckfpalhnebapjm`. Current packaged extension: 1.7.33, with separate owner-only experimental crypto paper testing. Public research did not establish a dependable live strategy. Sell supported tools and research capability, not guaranteed profits or an invented win rate.

## What this release fixes

### Billing and accounts

Initial membership expiry comes from the actual verified Stripe subscription period, including the newer single subscription-item period shape, rather than a guessed 30/365 days. Paid renewals update access through the actual billing period. An old/different/canceled subscription cannot reactivate or revoke the current one. A transient Stripe status/mapping race remains retryable.

Existing subscriptions cannot create a second checkout accidentally. Concurrent requests use an owner-scoped lease, repeated clicks reuse an open checkout, incomplete payments wait for reconciliation, and replaced open sessions are expired. Provider idempotency keys protect customer/price/checkout creation; plan/version prices are cached instead of creating a new product for every buyer. Disabled plans cannot be purchased. Billing SDK I/O runs off the ASGI event loop with bounded connection/read timeouts, and the installed Stripe SDK’s current exception class is used. Scheduled cancellation is labeled as end-of-period cancellation. Account/customer/subscription/checkout identities are checked before granting access. Test/live events cannot be mixed when the runtime mode is known.

Initial and renewal affiliate accrual uses stable invoice identities and actual paid amounts. Old checkout journal entries can acquire a stable invoice alias without double-crediting. A dispute resolves its exact Stripe charge before reversal. Cancellation alone does not reverse an already-earned payment; actual refunds/disputes retain reversal handling. Equal-sized partial refunds have distinct cumulative identities, so a second partial refund is not mistaken for a replay of the first. New webhook receipts use the natural unique Stripe event ID as Mongo `_id`. This does not send a payout or change the commission rates.

### Stripe credentials

Sandbox and live encrypted credentials are separate. Switching modes does not silently reuse another environment's saved key. Legacy ciphertext is preserved/moved by its actual key prefix when settings are saved. No encryption key is replaced. Invalid mode/key combinations are rejected before writing. Membership connection checks prioritize the payments key over a separate Connect key and support appropriately permitted restricted keys.

For live setup, select **Live credentials**, save a live payments key (`sk_live_` or an appropriately permitted `rk_live_`) and that live webhook destination's `whsec_` secret. A webhook secret does not encode its environment visibly, so only actual signed delivery can verify it. Blank fields retain only that environment's saved values. Changing the active Stripe environment is blocked while checkout is active, unless the deployment is explicitly in validation mode. Save changes, then run the connection check.

### Password recovery

The existing email integration remains supported. Secure SMTP can be used instead; no new email API provider is required. SMTP authentication requires SSL or STARTTLS with certificate verification. Network operations run off the event loop and have a timeout. Delivery failure never logs the password or reset token in production.

In cPanel Python App environment settings, configure privately:

```text
SMTP_HOST=<your hosting mailbox's outgoing SMTP server>
SMTP_PORT=465
SMTP_SECURITY=ssl
SMTP_USER=<your full mailbox address>
SMTP_PASSWORD=<mailbox password or app password>
SMTP_FROM=KAOS Trading <support@tradingwithkaos.com>
EMAIL_FROM_NAME=KAOS Trading
FRONTEND_URL=https://tradingwithkaos.com
```

Port 587 with `SMTP_SECURITY=starttls` is also supported. Use the actual mailbox/server details from hosting, not these placeholders. Never put credentials in Git or chat. Restart the Python app after environment changes. Test Forgot password with an owner-controlled account and confirm the delivered link works once and expires. A configured SMTP card does not prove inbox delivery, sender-domain authentication or spam placement.

## One operational screen

Sign in as super admin and open **Admin → Launch Status** (`/admin/launch`). It performs read-only local configuration/evidence checks, including catalog, Stripe environment/check state, checkout gate, email configuration, Google client configuration, worker heartbeat, published models and payout state. It never charges, transfers, sends an email, starts a worker or enables trading.

The installed-files revision is written only after a full successful cPanel activation. It proves which files were copied, not which Passenger process is running. Entrypoint-only repairs do not rewrite that full-release marker. Restart the API and verify hosted flows separately. No marker means an older/manual install; it is not proof of failure or success.

## Required hosted acceptance sequence

1. Deploy the tested development release using the existing prepare/activate workflow, preserving `.env`, `.htaccess`, uploads and application secrets. Restart Passenger, hard-refresh and check the installed revision in Launch Status.
2. Verify email and Google registration/login, logout/session restore, password recovery and revoked-account behavior. Use the existing official extension item/key. No new Store item is needed.
3. Use a **separate sandbox database/account environment**, website and API origins for Stripe test subscriptions. Do not test-grant memberships or accrue test commissions into the production user database. Current cPanel login-validation installation still blocks checkout/webhook delivery; this patch does not remove that boundary or provide proof of a billing-capable staging environment.
4. In that isolated environment, verify Free enrollment, monthly/annual Pro/Ultimate checkout, actual paid membership access, duplicate webhook delivery, renewals, failed invoices, recovery, end-of-period cancellation, refunds/partial refunds and dispute reconciliation. Both the initial payment and recurring invoice must reconcile to the same ledger identities on retries. Verify Google and password recovery again with the deployed origins.
5. Review the active Stripe account's portal settings, supported products/prices, billing terms and existing-customer plan-change behavior. This release prevents double subscriptions; it does not certify arbitrary Stripe portal price changes, proration policies or an untested catalog migration. Do not advertise an unverified one-click upgrade path.
6. Resolve live account/platform approvals and repeat the relevant acceptance checks with the matching live configuration through a reviewed billing-capable deployment. A successful account-key check alone is insufficient. Keep automatic payout release off until provider permissions, hold/refund balances and reconciliation are demonstrated.
7. Validate the installed extension's membership, device limits, four-chart controls, broker-native data and explicit Start/Stop. Extension code tests/mock browsers are not proof of broker execution quality or a profitable signature strategy. Store publishing remains a separate review/submission step.
8. Choose a dedicated training host before offering an always-on worker. Keep it out of shared Passenger. Pro/Ultimate benefits must reflect genuinely delivered training/model availability.

## What remains outside repository verification

The workspace has no authenticated session on the owner's Asura account, Stripe account or Chrome Store. Real DNS/deployment, selected mailbox credentials, payment delivery, account approvals, Store acceptance and worker hosting must be verified on those services. No new confirmation is needed for already-authorized reversible code fixes; missing credentials/access/evidence cannot be replaced by a fabricated success state.

Do not declare the business launched because every local test is green. The immediate milestone is a verified customer signup → payment → membership → supported product → support/refund lifecycle, followed by the independently gated payout/training/automation capabilities.

## External API verification finding

During this work, external GET requests to both `https://api.tradingwithkaos.com/api` and `/api/billing/memberships` returned HTTP 200 `text/html` with title **Bot Verification**, rather than JSON. The Google extension-config probe also timed out once. These are observations from one external network/client, not proof that every visitor receives the same response or that Passenger is the source.

The website client now rejects an HTML verification/routing page as an API failure instead of accepting it as account data. The extension already distinguishes bot-verification/invalid-JSON responses. Neither client change bypasses a challenge or makes webhook delivery work through it.

Hosting/support needs to investigate the API hostname's browser-verification/routing layer and allow legitimate browserless API and signature-verified Stripe webhook requests to reach Passenger without an interactive challenge. Confirm from an external client that GET `/api` returns JSON, and that Stripe's destination delivers signed POSTs to `/api/stripe/webhook` with the intended application response. An unsigned webhook may correctly return an application-level rejection; it must not receive an HTML challenge. Retain application authentication, signatures and rate controls. Do not interpret an outgoing Stripe account-key check as inbound webhook verification.

## Repeatable public deployment check

Run from the repository (local computer or cPanel; standard-library Python only):

```bash
python3 scripts/check_hosted_launch.py
```

On this cPanel account, use `/home/itsabout/virtualenv/tradingwithkaos.com/backend/3.11/bin/python` instead of `python3` if needed. This issues six bounded GET requests: health, public memberships and extension Google configuration with two client user agents, including the Store readiness checker. It checks website CORS, approved catalog prices and chart/device limits, and the official extension OAuth client/item configuration. It does not log response bodies or credentials, follow redirects, authenticate, change plans or send payments. Exit status 1 means a public check failed; even a passing report does not verify checkout, signed webhook delivery or an actual sign-in.

The follow-up external check found health/catalog JSON reachable for one client while the Store checker still encountered bot verification. The public catalog exposed legacy `monthly` ($29/month) and `yearly` ($279/year) records, with checkout disabled by login-validation hosting. Repository defaults do not overwrite these saved database settings. To apply the approved catalog, open **Admin → Settings → Membership Plans → Use current KAOS plans**, review Pro $29.95/$299.95 and Ultimate $99.95/$995.95, then **Save Plans**. This changes the offered catalog, not existing Stripe subscription prices, and does not enable checkout. Re-run the public check afterward. If older code lacks the button, deploy/restart the tested release first.

For a copyable hosting support request and the post-fix check, see [API_HOSTING_HANDOFF.md](API_HOSTING_HANDOFF.md). The owner Launch Status catalog card also checks billing period, currency, tier, chart/device limits and private/pretrained AI eligibility; matching amounts alone cannot mark an inconsistent catalog configured. It only flags review and never overwrites saved settings.
