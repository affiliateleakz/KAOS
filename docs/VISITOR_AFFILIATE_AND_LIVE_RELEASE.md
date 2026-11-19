# Visitors, affiliate controls, social links and live release

This release adds production features to the existing website and backend. It does
not deploy itself or move funds merely by importing the application. The latest
changes were built and syntax-checked. Further automated test runs and test
transactions were stopped at the owner's request; do not describe this release
as fully tested or live-verified.

## Where to manage features

- **Admin → Visitors & Referrals**: site page views, link navigation, referral
  landings, approximate unique browsers/visits, sources/UTM campaigns, country
  summaries, account conversions and recent activity. Filter by period, source,
  country or affiliate. Detailed event and member lists are paginated.
- **Affiliate Program → Clicks, visitors & subscribers**: an active paid affiliate
  sees only their own traffic and referred accounts. Customer emails, raw IPs,
  other affiliates' reports and private authentication details are not returned.
- **Admin → Affiliates → Commission percentages by membership**: owner-editable
  Pro and Ultimate percentages for Levels 1–3. Monthly/yearly variants share tier
  rates. Rates belong to each receiving affiliate's current paid tier, not the
  buyer's purchased tier. Free and trial rates are fixed at zero and those users
  cannot enroll or earn new commissions. Past earned entries remain unchanged.
- **Admin → Follow Us Links**: edit the public title/introduction and HTTPS links,
  hide links, reorder them and publish changes. The public page is `/follow-us`
  and is linked from the homepage and member navigation. No social accounts or
  URLs are invented for the owner; add the actual official profile URLs.
- **AI Signals** is a separate Ultimate-only entitlement. Trial/Pro retain AI
  insights and private training. API signal/discovery/legacy AI scan endpoints
  enforce the restriction; hiding a tab alone does not grant or deny access.

## Visitor data

The React router captures broad page categories and link navigation. It does not
capture passwords, form content, full referrer URLs, private page IDs or URL query
strings in reports. Referral links are counted as successful tracked landings,
not independently verified clicks on an external social platform. Multiple opens,
privacy tools, bots, shared devices and storage resets affect estimates.

Random browser identifiers renew after 90 days, visit sessions after 30 minutes
of inactivity, and latest referral attribution expires after 30 days. Signup
acquisition fields are snapshotted on the account; later visits do not reassign
existing account referrals. Stripe guest/trial signup carries the pre-payment
acquisition snapshot into the confirmed account. Historical anonymous affiliate
click totals are retained independently of the 90-day individual-event TTL.
Old data is not backfilled with guessed countries or sources.

Country lookup uses the bundled public **DB-IP Lite** index, memory-mapped locally.
No geolocation API key, external IP lookup or runtime dataset download is needed.
Attribution and license are included in `apps/api/analytics_data`; country results
are estimates, not GPS/city addresses. Unknown/private addresses stay Unknown.
The public privacy policy includes the new data use and an analytics opt-out.
Do Not Track, Global Privacy Control and opt-out preferences stop optional capture.

If Asura/proxy requests expose a proxy IP instead of the client, configure only
known proxy CIDRs in `KAOS_ANALYTICS_TRUSTED_PROXIES` (comma-separated). Forwarded
headers are ignored by default and parsed right-to-left only from trusted peers.
Do not trust all addresses or arbitrary `X-Forwarded-For` headers. Ask the host for
its exact proxy ranges when necessary. Run `python scripts/build_country_database.py`
in the repository to refresh the public monthly country data before building a
new release; commit its provenance/license with the updated index.

Analytics writes have bounded per-peer ingestion limits and idempotent event IDs.
Reports use bounded time windows and aggregation limits; there is no background
market scan, per-tick visitor polling or individual runtime geolocation request.
Telemetry failures never prevent account creation, checkout or navigation.

## Rates and existing money

The API validates percentages from 0–100 with at most two decimal places. The sum
of the maximum possible Level 1, 2 and 3 rates across tiers cannot exceed 100%.
Saving requires the current revision to prevent lost updates. Each new qualifying
paid invoice snapshots rates/revision/currency in its journal. Retries reuse
existing entries; refunds use the rates originally recorded. Changing rates does
not rewrite existing commissions or their 30-day hold dates.

Free/trial users do not get affiliate access. Actual eligibility requires a
current active paid subscription, not a super-admin tool grant or a TRIAL label.
Previously earned account statements remain private service records. No enrollment
or zero-dollar trial creates a payable commission.

## Live trading

The Pocket Option extension retains explicit Start/Stop and its current live
broker execution. This release does not place orders or switch the broker's
account between demo/real. Coinbase live-order capability can be explicitly
activated after installation using the existing runtime repair command:

```
cd /home/itsabout/repositories/KAOS
/home/itsabout/virtualenv/tradingwithkaos.com/backend/3.11/bin/python scripts/cpanel_billing_runtime.py --enable-stripe --enable-trading
```

This persists the authorized live-order flag and requests a Passenger restart.
It preserves credentials, billing settings and stored user bot risk controls.
Coinbase still needs a connected trading account and a running execution worker;
a flag does not start a worker or place an order. Planned broker connectors remain
planned. No live order or simulated order was submitted while preparing this code.

## Live Stripe affiliate transfers

1. In **Payments & Payouts**, select Stripe payouts, live mode and valid live
   platform/Connect credentials. Recipients complete live Stripe Connect onboarding.
2. In **Affiliates → Live Stripe affiliate transfers**, enable live transfer release.
   The database must support MongoDB transactions (replica set or sharded cluster);
   incomplete/legacy journals must be reconciled. The release checks deployment
   capabilities without sending a test transaction and enables mandatory atomic
   journal writes. Pausing transfers does not turn transactional accounting off.
   This reads the approved Stripe platform account and saves a release bound to
   that platform/key and database deployment. It sends no funds. Key changes require a new release check.
3. Choose the affiliate, view the matured USD balance, enter an amount and select
   **Send live Stripe transfer**. This is a real transfer request, not a simulation.

Only the owner/super-admin can release or send transfers. The server binds the
recipient to the affiliate's approved live connected account and verifies its
provider metadata/capabilities. Amounts are bounded by the configured minimum,
30-day hold, refunds/chargebacks, previous transfers, pending reservations and
actual Stripe USD funding. Legacy records without currency provenance and non-USD
commission balances require review rather than being treated as USD.

The payout journal reserves funds before the processor call. Retries keep the
same request ID, amount, destination, platform and Stripe idempotency key. Unknown
outcomes remain reserved and block replacement requests. Requests older than the
processor idempotency window require reconciliation instead of blind resubmission.
Use **Reconcile**, optionally with the actual `tr_…` transfer ID from Stripe when
the bounded latest-transfer list does not include it. Canonical provider identity,
amount, currency, destination and metadata must match before confirmation. Returned
transfer reversals reduce the recorded transferred amount when reconciled; later
commission refunds may create a negative balance that offsets future earnings.

A confirmed transfer moves funds to the affiliate Stripe account. It is not
confirmation of a bank deposit; Stripe controls bank delivery and its own schedule.
PayPal and NOWPayments settings are retained, but this release's new executable
payout transport is **Stripe Connect in USD**. They must not be labeled live payout
transports merely because credentials/preferences were saved.

Code availability and hosting activation are separate. Deploy the release,
restart the Python app, allow the API through hosting bot challenges, and use the
admin session to enable release with the actual approved provider account. No
provider account was approved or funded from this workspace, and no payout was
sent while preparing the release.
