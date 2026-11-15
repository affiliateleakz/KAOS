# KAOS membership upgrades and affiliate launch

## What this release changes

Restricted scanner, disclosure, heatmap, AI-insight and cloud-strategy pages show
a black-and-gold upgrade experience rather than a raw access error. The server's
entitlements determine access. Locked pages do not request their restricted feed.
An account-service outage shows a retry/sign-in message, never a demand to upgrade.
Free chart users see a four-chart comparison invitation. AI execution still needs
independent validation; purchasing a plan does not remove that lock.

The affiliate hub offers explicit enrollment, a personal signup referral link,
campaign-tagged emails/social/community copy, PNG banners (1200×628, 1080×1080,
728×90), published administrator copy, referral statistics, commission ledger and
Stripe-hosted onboarding. Text includes affiliate disclosure and risk language;
email users must replace sender/address/unsubscribe placeholders and use their
own permission-based sending process. KAOS does not send these emails.

Campaign links go directly to `/register?ref=...` so registration receives the
code. Signup-page tracking records the campaign once per code/campaign/tab
session. This is not a complete fraud-resistant attribution system or a verified
30-day attribution policy. Existing affiliate codes remain valid; newly generated
codes derive from user IDs, avoiding collisions from shared/truncated usernames.
Referral URLs use trusted frontend configuration, not the request's Origin header.
Suspended/banned accounts, paused enrollment and inactive affiliates cannot enroll.

## Current commission schedule

| Recipient's membership | Direct referral / L1 | L2 | L3 |
| --- | --- | --- | --- |
| Free | 10% | 0% | 0% |
| Pro | 30% | 15% | 0% |
| Ultimate | 50% | 25% | 5% |

Rates come from `kaos.memberships.RATES`, the same source used by the ledger.
Each recipient's membership at the qualifying payment determines their rate;
tool access granted to a super-admin does not rewrite their affiliate billing
membership. Qualifying initial subscription payments and renewals accrue
commissions, not recruitment or unpaid signups. The ledger holds credits for 30
days and offsets refunds/chargebacks. For a $149 payment with three Ultimate
recipients, the nominal commissions are $74.50, $37.25 and $7.45: $119.20 total,
leaving $29.80 before payment fees, tax, refunds and other costs. No earnings or
trading returns are guaranteed. This release does not change the rates.

## Stripe Connect: implemented versus pending

The owner requested live paid memberships and Stripe Connect payouts. That is
authorization to work on activation, not evidence that hosting/Stripe is ready.

Implemented: authenticated Express-account onboarding, stable account-creation
idempotency keys, account reuse and server-verified profile status. Stripe collects
identity/tax/bank information on its hosted page. No banking information is
collected in KAOS or requested in chat. Errors are sanitized. Creating a profile
does not transfer funds. Test mode is identified separately.

Not activated: live checkout/webhooks and cash transfers. The hosting validation
wrapper still clears checkout/webhook keys and blocks billing. `payoutsEnabled`
and `transfersEnabled` remain false. The UI states this explicitly. No automatic
transfer worker or production payout-release flow has been enabled by this
release. The previously documented financial/session findings remain open.

First run the new read-only check on hosting after pulling the release:

```bash
cd /home/itsabout/repositories/KAOS
/home/itsabout/virtualenv/tradingwithkaos.com/backend/3.11/bin/python scripts/check_commerce_readiness.py
```

It prints PASS/BLOCKED labels, not secret values. It checks live-key presence,
webhook-secret presence, transaction mode/topology, required unique indexes and
the billing wrapper. It does not create indexes, start payments, send payouts,
rotate keys or change data. A PASS is necessary but not a full launch approval.
The owner must configure keys in cPanel, never in chat or Git:

* Existing checkout: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`.
* Separate Connect onboarding: `STRIPE_CONNECT_SECRET_KEY` and
  `KAOS_STRIPE_CONNECT_ENABLED=true` (off by default).
* Affiliate finance: `KAOS_AFFILIATE_TXN_MODE=required`, backed by a verified
  replica-set/sharded MongoDB deployment and unique journal indexes.

Before money moves, verify the Stripe platform's Connect/live capabilities,
price/lookup configuration, signed live/test webhook delivery, event ordering,
subscription expiry, refunds, reconciliation and recovery. Implement and review
the transaction-safe payout reservation/release process, funding, transfer
idempotency/retry/reconciliation and webhook-driven connected-account state.
Do not replace the wrapper with an unrestricted app to bypass these checks.
The existing wrapper now permits only authenticated affiliate enrollment and
Connect onboarding in addition to its prior authentication/device paths.

## Extension 1.7.20

Compact restores the KAOS app window to normal state, narrows it to 430px and
aligns it with the right side of the saved Pocket Option window. It never resizes
the broker window. Chrome does not provide true native docking/always-on-top;
this is a companion layout, not an injected panel. Expand restores the larger
workspace. The worker validates the extension sender/window before resizing.
Compact hides the sidebar, while session status, Expand and Stop remain available.

Repeated chart-ready events no longer reopen the membership-check screen in an
already verified, authorized popup session. Sign-out clears this presentation
state, and explicit Re-check still revalidates. This is not an offline license
bypass or persistent authorization cache. A newly opened/reloaded app still
requires server verification. No trading-strategy/order logic was changed.

## Validation and deployment

Tests use fixture accounts, mocked Stripe, disposable MongoDB and fixture broker
data only. Browser checks exercise direct-route upgrade gates, owner access,
outage/retry behavior, mobile layout, enrollment, personalized copy, actual PNG
downloads, compact/expand layout, repeated chart-ready events and Stop/sign-out.
No real account, checkout, Stripe onboarding, email or trade was executed.

Use GitHub's prebuilt website/backend artifacts to avoid compiling on the
resource-limited hosting account. Preserve `.env`, `.htaccess`, uploads and
application settings. Activation/restart is still necessary: pulling Git does not
install the live release. Extension 1.7.20 must be extracted into the same
existing unpacked folder and reloaded separately. Do not reinstall/clear storage.
