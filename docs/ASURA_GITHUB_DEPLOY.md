# KAOS → Asura Hosting: one-time GitHub SSH setup

Current paid-checkout activation and cPanel environment settings are in [STRIPE_SETUP.md](STRIPE_SETUP.md). Staging alone does not activate checkout.

This is the simplest safe first step for the **existing domains**:

- Website: `https://tradingwithkaos.com`
- API: `https://api.tradingwithkaos.com`
- Existing API application root: `/home/itsabout/tradingwithkaos.com/backend` (Python 3.11)
- **Current live API is the older native WSGI application**: `passenger_wsgi.py` imports `wsgi_app.application`, reported build `1.1.11-full-admin-repair`.

The GitHub workflow `Prepare KAOS release on Asura Hosting` only uploads release ZIPs to `~/kaos_cpanel_releases/<commit-SHA>/`. It **does not** switch API runtimes, upload into the live app, modify the website, restart cPanel Python, or deploy live trading. The mismatch between the old native WSGI API and the new extension must still be resolved and tested. Do not replace the existing `passenger_wsgi.py` by itself.

## One-time Asura setup

1. In cPanel, check **Security → SSH Access**. If you cannot find it, ask Asura Hosting support to enable SSH for your account. Confirm the SSH **host**, **port**, **username**, and the server's **verified host-key fingerprint** directly with Asura Hosting.
2. In cPanel **SSH Access → Manage SSH Keys**, generate a dedicated deployment key pair, or import a new public key generated on your own machine. **Authorize the public key** for SSH login. Keep the private key out of GitHub source files, chats, screenshots, and website folders. Prefer a restricted deployment-only account/key when Asura supports it.
3. Ensure the SSH account can create files in a **private** directory under its home directory (`~/kaos_cpanel_releases`) and that it cannot accidentally overwrite production paths through account-level restrictions, if supported.

## One-time GitHub setup

Go to <https://github.com/affiliateleakz/KAOS/settings/environments> and create an environment named **`kaos-hosting`**. Enable required reviewers to prevent unintended upload runs (GitHub plan and repository visibility may constrain protection options). Then add:

| Type | Name | Value |
|---|---|---|
| Environment variable | `ASURA_SSH_HOST` | SSH hostname confirmed by Asura (hostname **only**, without `https://`) |
| Environment variable | `ASURA_SSH_PORT` | SSH port confirmed by Asura (normally `22`, but verify) |
| Environment variable | `ASURA_SSH_USER` | SSH username (your cPanel account if SSH uses that account) |
| Environment secret | `ASURA_SSH_PRIVATE_KEY` | Full text of the **dedicated SSH private key** |
| Environment secret | `ASURA_SSH_KNOWN_HOSTS` | Verified OpenSSH `known_hosts` entry for the SSH server and port |

**Host key security:** Obtain the fingerprint from a separate trusted channel with Asura support. An unverified `ssh-keyscan` alone does not establish identity. For a non-standard port, the `known_hosts` hostname is typically `[host]:port`; for default port 22 it is typically `host`. You can gather the key with `ssh-keyscan -p PORT HOST` from your own device and verify it against the trusted fingerprint **before** saving it. Never use `StrictHostKeyChecking=no`.

No MongoDB passwords, broker vault keys, Stripe secrets, or administrator passwords are needed in GitHub for this ZIP-upload workflow. The existing shared broker encryption key was previously disclosed in chat; it must be treated as compromised and migrated/rotated with a verified broker-credential recovery plan. Do **not** rotate it in place until existing encrypted broker credentials are accounted for.

## Running the upload

1. The workflow file is currently being developed on PR #54; **manual runs are available normally after an approved merge to the default branch**.
2. Once PR testing/security review and required approvals succeed, open <https://github.com/affiliateleakz/KAOS/actions/workflows/asura-prepare.yml>.
3. Select **Run workflow**, choose an approved source revision, and enter `STAGE-KAOS` in the confirmation field.
4. Approve the protected `kaos-hosting` environment when prompted.
5. The action compiles the backend Python sources, builds the web app with `REACT_APP_BACKEND_URL=https://api.tradingwithkaos.com`, builds both cPanel ZIPs, connects using SSH host-key verification, and copies them to a **non-public staging folder**.
6. In Actions, check the log for the final SHA-256 integrity checks. ZIPs being uploaded does **not** prove the live API is compatible or that end-to-end login works.

## Activation is intentionally separate

Before adding an actual production activation workflow, identify the current website document root, back up the existing native WSGI backend and data, verify whether both backends use the same DB schema/auth/session mechanisms, validate Python requirements in the host environment, and arrange a tested restore plan. Upgrade activation should use a maintenance/canary approach with automatic health verification and a clear rollback path.

Only after that validation should we implement a separately approved deployment that updates the live website and API. **Never switch `passenger_wsgi.py` alone.**

## If SSH is unavailable

The current workflow cannot connect through cPanel File Manager alone. Ask Asura to enable SSH or use the two prebuilt cPanel ZIPs for a manual upload. Do not expose FTP passwords or SSH private keys in chat.

## Staging integrity and retries

The staging transport is `scripts/asura_stage.sh`. It validates a full commit
SHA, refuses a symlink staging root, restricts directories to mode 700 and files
to 600, and refuses an existing revision directory. `COMPLETE` is written only
after both ZIP checksums and the release revision pass. A failed upload can leave
an incomplete private folder; it is never activated or automatically deleted.
An operator must inspect and move that incomplete folder aside before retrying
the same SHA. Keep complete releases for rollback; do not re-upload over them.
The account owner must verify the private staging directory is not exposed by
any Apache alias, symlink, or additional document root.

The SSH host and user are restricted to single hostname/account values before
writing OpenSSH configuration; newlines, options, and shell syntax are rejected.
Only independently verified host keys are trusted. No private deployment key is
available to repository tests; local transport tests simulate SSH/SCP and do not
prove a connection to Asura.

See [issue #55 validation and activation gates](ISSUE_55_VALIDATION.md) for the
current evidence, missing legacy-runtime inputs, and recovery procedure.

## cPanel Git with a private GitHub deploy key

For the existing checkout `/home/itsabout/repositories/KAOS`, `.cpanel.yml`
now runs `scripts/cpanel_prepare.sh` when **Deploy HEAD Commit** is selected.
The equivalent Terminal command is `bash scripts/cpanel_prepare.sh` from the
checkout. Node 20 comes from `/opt/alt/alt-nodejs20/root/usr/bin`; Python uses
the existing account's `virtualenv/tradingwithkaos.com/backend/3.11` environment.
No dependency installation into the live Python environment is performed.
The cPanel website build limits Rayon, Tokio and libuv worker pools to one
worker each to reduce thread pressure on shared hosting. This does not change
Passenger workers or guarantee a build under an exhausted account quota.

This builds the React website with the existing API domain, builds both cPanel
ZIPs, checks their hashes, and publishes an immutable private release under
`~/kaos_cpanel_releases/<full-commit>/`. The complete source backend package
includes API routes such as affiliates, and kaos-core. Extension distribution
is separate; services/research/mobile are not automatically started by cPanel.
A clean checkout is required. Preparation is serialized; a hard-killed process
may leave `.prepare-lock`, which an operator should remove only after verifying
no preparation is running. Failed temporary builds are cleaned on normal exit.

**Deploy HEAD Commit currently means prepare, not activate.** It does not copy
into `/home/itsabout/tradingwithkaos.com`, replace its `.htaccess`, change the
legacy API entrypoint, or modify any database. The target installation remains
the complete website plus backend at that path, but source/runtime parity and
session/device/license checks remain prerequisites for the first live switch.
Keep the existing root routing rule blocking backend/source folders. Existing
`.env` is at the backend root; the new server expects environment variables or
`apps/api/.env`, so activation must explicitly arrange loading the root settings
without moving secrets into Git. Do not extract both ZIPs blindly over the site.

Private GitHub access uses a read-only repository deploy key. Configure the
checkout's origin to `git@github.com:affiliateleakz/KAOS.git` and its local
`core.sshCommand` with the dedicated identity, `IdentitiesOnly=yes`, and
`StrictHostKeyChecking=yes`. Verify GitHub's host fingerprint independently.
Updating from Remote still requires a manual click/pull; this setup is not a
GitHub push webhook and does not automatically activate each new commit.

### Explicit first activation in login-validation mode

The owner has separately requested a live update and declined a full backup.
`scripts/cpanel_activate.py --revision FULL_PREPARED_SHA` verifies a prepared
release without installing it; adding `--activate` installs it into the existing
website/backend paths. The prepared SHA may precede the activation helper commit
when the application sources are unchanged. It checks hashes, archive paths,
symlink destinations and dependencies before writing. The live backend `.env`,
website `.htaccess`, uploads and legacy `wsgi_app.py` remain. It does not delete
obsolete assets, migrate the DB, seed accounts, install dependencies or restart
Passenger. Writes are atomic per file, not across the entire release; an I/O
failure can leave a partially installed release. No full backup is made.

The generated startup file loads the existing backend-root `.env`. It forces
Coinbase live orders and Stripe credentials off, and temporarily permits writes
only for authentication and device registration. Other write requests and all
`/api/billing` requests return 503. This is intentionally a sign-in validation
release, not approval to trade or charge users. Existing GET handlers retain
their normal behavior and may perform routine metadata updates. Restart through
cPanel after installation; check `/api`, extension email sign-in, registration,
licenses, revoked devices, refresh/logout, Google OAuth and browser session
behavior. Google remains dependent on correct server/provider client settings.
Do not remove the validation restrictions until separately authorized.

If the new API fails, restore the known legacy entrypoint importing
`from wsgi_app import application` with the backend directory in `sys.path`,
then restart through cPanel. This recovers the old runtime but does not undo
website asset updates or any account/session writes made during login tests.
Keep the extension login attempt disconnected from broker execution.

### Public request timeout with a working direct WSGI test

A standalone `/api` WSGI request succeeded on Asura while public requests timed
out. One reproducible failure mode is a server forking after the ASGI adapter
starts its event-loop thread: the child inherits the adapter but not its thread.
The adapter now initializes lazily in the serving process and resets its state
and lock after a fork. A regression test warms the adapter in a parent, forks,
and verifies the child responds; the former eager adapter hangs in that test.
This does not prove the Asura worker lifecycle was the cause; recheck public
HTTP after the change and inspect hosting configuration if it still times out.

Use the activation helper's `--entrypoint-only --activate` with the existing
prepared revision to refresh just `backend/passenger_wsgi.py`. Dependencies and
the release hashes are still checked first. Source files, frontend assets, .env,
.htaccess and databases are not rewritten by this option. Restart the API in
cPanel afterward. Login-validation restrictions remain enabled.

### Device management during login validation

The validation gate permits the existing authenticated single-device revocation
handlers: member DELETE `/api/v1/devices/{id}` and administrator POST
`/api/admin/devices/{id}/revoke`. Member ownership filters and administrator role
checks remain in those handlers. Mass revocation and other non-authentication
writes remain blocked; no plan, device limit or revoked flag is overridden.
Refresh only the entrypoint to apply this exception to an installed release.

Extension 1.7.14 preserves the registration endpoint's detail (device limit,
revoked installation or denied bot access) and displays it on the blocked screen.
The Manage Devices button opens the member devices page. Re-check still performs
registration and license checks; website sign-in alone cannot change them.
For an unpacked extension, update files in the existing installation directory
and click Reload: removing/reinstalling or selecting a different directory can
change extension/install identity and consume another device slot. Do not delete
or revoke devices belonging to other users to troubleshoot the owner account.

### Legacy device record management

Device lists now provide a stable selector for older MongoDB device documents
that lack a KAOS `id`. This is computed from MongoDB `_id` without changing the
record during a GET. Member revocation resolves that selector together with the
authenticated user's `userId`; administrator revocation retains its role check.
Selectors for legacy records cannot target records with a nonempty KAOS id.
Both endpoints now return 404 when no device matched instead of falsely reporting
success. Existing legacy installations can refresh their device metadata without
requiring a nonexistent `id`. Revoked installations remain denied.

Member and administrator pages display unknown/missing activity timestamps as
Unknown and report device-list loading errors. No automatic revocation, account
upgrade or device-limit increase is performed. Deploy a newly prepared release
containing both API and built website changes, restart the API, then revoke only
the obsolete device through the authenticated dashboard and re-check the current
extension. This record-shape incompatibility is covered by regression tests; the
actual live record was not exported or modified during development.

### Targeted hosting-operator recovery of the obsolete owner device

When dashboard revocation cannot be completed, the account owner can run
`scripts/retire_legacy_owner_device.py` using the existing hosting virtualenv.
Default execution is read-only. `--retire` explicitly retires the known obsolete
device only if there is exactly one `owner` account, exactly one active device
for that account, and that device has version `1.1.6`. It updates only the matched
MongoDB `_id` with the same owner, version and active-state filters. All ambiguous
cases stop without mutation; a failed/racing update is not reported as success.
It reads credentials from the existing backend `.env` without printing them.
No website deployment or API restart is needed. The current extension must still
register normally through the account/device limit and license checks. This is
an explicit operator repair, not an automatic device replacement policy.

### Extension 1.7.15 chart session and Viking account login

The popup broker picker now uses `KAOS_CONNECT_PLATFORM`, which verifies the
server/device license, attaches the authorized broker integration, and reuses
an existing supported broker tab. It no longer merely opens a new broker tab.
The popup receives only chart-readiness fields through a DOM event (no user,
account, token or device identifiers) and restores charts
through the same authorized handler. It retries chart discovery when its saved
broker tab finishes loading. Sign-out invalidates pending connection responses and prevents stale worker
registrations from completing after logout;
unselected, signed-out and unlicensed states do not restore a broker session.
Connection failures remain visible in the broker picker. No Start Bot/order
messages are sent by the new chart-session bridge. Real Pocket Option login and
market-feed behavior still require installed-extension validation without orders.

Website account pages use the existing KAOS Viking artwork with black/gold form
styling. Email/password login, Google sign-in, registration and recovery routes
retain their API contracts. Email/password labels and autofill attributes are
provided, and the Google button width fits the form on small screens. The prior
blue split-panel design was discarded at the owner's request.

Validation: 20 Node cloud/chart-session tests, broker isolation guards, production
web build, and headless Chromium checks. The real popup HTML reached its chart
dashboard after fresh sign-in/broker selection and a restored session using
mock Chrome/broker responses, with no JavaScript errors or Start Bot messages.
Website checks covered 1440px, 390px and 320px widths, login failure messaging,
unchanged credential payload and successful dashboard navigation using mocked
API/Google provider responses. This does not certify live Google provisioning,
broker market data, strategy performance or real-money execution.

Update an unpacked extension in its existing folder and Reload it to preserve
its installation/device identity. Deploy a newly prepared website package for
the login design; installing website files does not update Chrome extensions.

### Administrator device capacity

Active, non-revoked accounts whose server-stored role is `admin` or `super_admin`
have unlimited device capacity. Entitlements expose `devicesUnlimited: true` and
`deviceLimit: null`; registration uses the same role policy and does not apply a
numeric device-count cap. This changes only device capacity, not chart counts,
paid feature access, trading approval, billing or account roles.

Members and moderators retain their membership limits. Usernames (including
`owner`), client request fields and a plan's `devicesUnlimited` flag cannot grant
the capability. Suspended/banned accounts, revoked extension access and revoked
installations remain rejected. Apply through a newly prepared backend release
and restart the API; no database role edits or key rotation are needed.
# Chart-data audit release (extension 1.7.16)

See [the audit report](CODE_AUDIT_AND_CHART_DATA.md) before upgrading. This release
repairs dashboard candle polling and keeps extension order execution disabled.
Update the existing unpacked extension folder and reload it; a website update
alone does not update browser extension files.

The updated Python dependencies require MongoDB 4.4+. Run the read-only
`scripts/check_cpanel_runtime.py` using the hosting Python environment before any
dependency upgrade. Review environment rollback separately from file activation.
Authentication session revocation, payments readiness and recovery remain open
release blockers described in the report. Do not enable live trading/payments
or merge the draft PR as part of installing the chart fix.

### Extension 1.7.17: owner-approved trading

The owner subsequently approved enabling trading in the extension. Version
1.7.17 restores the Start button and disables the four temporary audit-only
execution blocks. Broker authorization and explicit Start/Stop remain required;
sign-in and chart monitoring do not start trading. It operates on the connected
broker account, including a real account if that is selected in Pocket Option.
Update the existing unpacked extension folder and Reload; no hosting rebuild is
needed for this extension-only change. Backend/payment restrictions and the
audit's unresolved findings remain unchanged. No real orders were used in tests.

### Extension 1.7.18: Viking trading desk

The extension adopts the website's existing Viking artwork, black/gold sign-in
and gold controls. Sign-in has visible email/password labels, autofill hints,
empty-field feedback and a website recovery link. Both sidebars share Dashboard,
Charts, Strategies, Trade History, Risk Controls and Settings; Backtester, AI and
Performance are grouped under Advanced tools. Separate website links open account,
membership, devices, stock/crypto scanners, research and affiliate pages in new
tabs. These links do not transfer extension tokens or bypass website sign-in.

A persistent session strip reports broker authorization, the snapshot's confirmed
Demo/Real account type (otherwise explicitly unconfirmed), running/stopped state,
and Stop. It reuses existing state and Stop behavior; it makes no additional API
requests. Returning to Dashboard retains the authorized candle poller. Existing
execution logic and owner-approved trading remain unchanged. No hosting rebuild
is required. Update the existing unpacked extension folder and Reload.

Chromium fixtures cover gold login styles, labels, compact login width, validation,
all primary navigation, website-link destinations, chart polling, Demo/Real
status, Stop, sign-out and absence of automatic Start. Fixture quotes/account
states are not a live-broker validation. No real orders were submitted.

### Extension 1.7.19: broker loading recovery

Repeated attachment requests during a broker reload no longer fail Connect with
`ATTACH_RETRY_COOLDOWN`. They report a loading state; Connect waits up to 20 seconds
for the actual terminal snapshot receiver, without requesting further reloads.
Success requires that receiver, not merely a successful reload request. Logout
or authorization-generation changes cancel the wait. A timed-out load shows a
plain message to keep the broker tab open and retry Connect. Attachment is saved
only after the receiver is ready. No hosting update or trading-logic change is
required. Tests cover concurrent/recent reloads, receiver readiness, bounded
timeout and logout cancellation. No real broker orders were submitted.

### Super-admin feature tier

Active server-stored `super_admin` accounts with non-revoked access receive the
Ultimate feature tier, four charts, scanners, premium tools and unlimited devices
without purchasing a subscription. This grants capabilities without changing
Stripe/subscription records. Ordinary admins keep their plan feature tier and
existing unlimited-device capability. Suspensions, bans, revoked access and the
independent AI-execution validation lock are not bypassed. The website and
extension use the same `get_entitlements` policy. Deploy the updated
`apps/api/services_trading.py` to the backend, restart the Python app and refresh
the signed-in website/extension to retrieve the corrected entitlements.

### Current membership setup after the homepage release

The approved three-card Viking hero uses current extension and website captures. The public membership catalog supplies pricing, feature comparisons and affiliate examples; there is no public hardcoded paid price override.

After activation and a cPanel Python restart, use Admin → Platform Settings → Membership Plans. If retired plans or old limits remain, select **Use current KAOS plans**, review Free $0 / Pro $29.95 monthly or $299.95 yearly / Ultimate $99.95 monthly or $995.95 yearly and the allowances, then **Save Plans**. Loading defaults alone does not save. Already configured custom prices should be retained unless intentionally changed.

The validation adapter allows only the `plans` key at `POST /api/admin/settings`; the underlying handler still requires an authenticated admin and validates plan amounts. This makes Save Plans work on cPanel while other settings writes, real payment processing and live-order restrictions remain unchanged. No database migration or automatic billing activation occurs.

## Compiled releases without a cPanel build

GitHub preparation and local `cpanel_prepare.sh` now publish to the same private directory: `~/kaos_cpanel_releases/<full-commit-SHA>/`. The SSH upload remains preparation only: it verifies both ZIP checksums and revision before writing `COMPLETE`; it does not install files or restart Passenger. Older uploads under `~/kaos_release_staging` are not automatically moved or activated.

The GitHub workflow also retains a `kaos-cpanel-<full-commit-SHA>` Actions artifact for 14 days, before attempting SSH. It contains the website/backend ZIPs, `SHA256SUMS` and `RELEASE.txt`, so an SSH failure does not require rebuilding the frontend on shared hosting. Treat source archives and compiled deployment archives as different files. Do not extract a backend ZIP directly over the site using File Manager; the installer preserves the live routing and environment files.

A separately supplied `KAOS-Website-Backend-<short-SHA>.zip` is an outer upload bundle whose top-level directory is the full commit SHA and includes the verified `COMPLETE` marker. Upload this outer bundle to `/home/itsabout/`, outside the web document root. Extract it under `/home/itsabout/kaos_cpanel_releases/` only when that revision directory does not already exist; do not overwrite a previously prepared revision. Then run the existing installer with `--revision <full-SHA>` **without** `--activate` first to check the checksums and package layout. This check does not change live files. Adding `--activate` is the separate live installation step; the existing login-validation/payment and order restrictions remain in effect. Restart the Python app only after an authorized installation.

Prebuilt files reduce hosting build work; they do not repair the API hostname's verification page, change saved catalog prices, install missing Python dependencies or configure a payment provider. Use the corresponding launch checks for those items.

### Payment before account creation

Paid homepage choices now open `/checkout?plan=...` with only a receipt email.
KAOS does **not** create an account or ask for a password before Stripe payment.
Existing email addresses must sign in first to protect their account and avoid
creating duplicate subscriptions; the selected plan is retained.

After Stripe confirms payment, a cookie-protected receipt handler or signed
webhook creates the new account, attaches the verified subscription and emails
an expiring, one-use password-setup link. A Checkout session ID or receipt cookie
never logs a buyer in or sets a password. Free signup remains free signup.
Account setup mail must work: configure the existing secure SMTP settings
(`SMTP_HOST`, `SMTP_PORT`, `SMTP_SECURITY`, `SMTP_USER`, `SMTP_PASSWORD`,
`SMTP_FROM`) or existing email integration, plus HTTPS `FRONTEND_URL`.
New-account checkout stays unavailable without configured account mail.
Never put SMTP/Stripe credentials in Git or paste them into chat.

In **cPanel → Setup Python App → api.tradingwithkaos.com**, save these non-secret
runtime variables after installing this release, then restart the Python app:

```
KAOS_STRIPE_CHECKOUT_ENABLED=true
KAOS_LOGIN_VALIDATION_MODE=false
```

This requires the saved Stripe payment credentials, matching live/sandbox mode
and webhook secret in the private commerce settings. No keys change by setting
these flags. Neither flag enables trading or affiliate payouts. Confirm your
Stripe webhook points to `https://api.tradingwithkaos.com/api/stripe/webhook`
and verify actual delivery in Stripe; do not rely only on the health check.

Read-only checks:

```
curl -sS --max-time 20 https://api.tradingwithkaos.com/api
curl -sS --max-time 20 https://api.tradingwithkaos.com/api/billing/availability
```

The first should return the KAOS service status. The second should show
`checkoutEnabled: true` and `guestCheckoutEnabled: true` before accepting new
buyers. `/` on the API hostname intentionally has no route and may return
`{"detail":"Not Found"}`. HTML verification pages are hosting responses, not
Stripe status. An `EXPIRED` account without a confirmed paid subscription must
not be promoted to paid membership manually as a workaround.

### Repair stale Passenger billing flags

When availability reports `mode: live`, `configurationReady: true` but still
says login-validation blocks billing after cPanel settings were saved, the
running process has not applied those settings. This does not establish whether
the cause is an older installed startup wrapper, inherited Passenger environment,
or a restart that did not replace the workers.

The owner can apply the billing-only startup repair from the repository:

```
cd /home/itsabout/repositories/KAOS
git pull --ff-only
/home/itsabout/virtualenv/tradingwithkaos.com/backend/3.11/bin/python scripts/cpanel_billing_runtime.py --enable-stripe
```

This installs the current startup wrapper, writes only the two intended runtime
flags via private `backend/.kaos-billing-runtime.json`, and touches Passenger's
`backend/tmp/restart.txt`. If this host ignores that restart request, restart the
Python application in cPanel. It does not replace website/API source, copy keys,
modify `.env`, query the database, or enable trading/payouts. It does not require
rebuilding the website or a prepared release merely to repair billing flags.
Install any pending website/backend release separately for payment-first signup.

**Precedence:** when present, this explicit local policy controls Stripe checkout
and login-validation mode ahead of cPanel's inherited environment and `.env`.
Subsequent releases preserve it. To turn checkout off, run the same script with
`--disable-stripe`; to return to cPanel environment management, remove only this
non-secret policy file and restart the app. Saved matching Stripe credentials,
the webhook secret, provider selection and mail requirements remain enforced.

Recheck `/api/billing/availability` after restart. Current API releases also return
`runtimeSource`, `loginValidationMode`, and `checkoutRequested` for diagnosis.
These fields never contain credentials. A checkout-enabled response does not
prove successful webhook delivery or email delivery; verify those separately.

### Seven-day Pro free trial

The public button is **7-day free trial**. It opens a name/email form with Pro
and Ultimate choices. Pro monthly offers all configured Pro entitlements for
seven days; Ultimate and annual plans are paid choices. Switching to Ultimate
removes the trial flag. Stripe collects a card, shows the exact renewal date and
saved price, and renews after seven days unless canceled. No live price is
rewritten by this release: the website, API and Stripe price creation all use
admin-saved plan amounts. Existing subscriber renewal amounts remain their
Stripe subscription amounts, rather than changing when the public price changes.

No KAOS account or bot access is created from an unfinished checkout. A completed
trial requires a canonical trialing Stripe subscription, a matching saved card,
valid trial dates, the expected checkout metadata and a reserved customer email.
One used trial is recorded per normalized customer email and Stripe environment.
This prevents email/account reuse; it is not a guarantee against someone using
multiple identities. Trial signup and its $0 invoice do not generate commissions;
qualifying actual paid renewals use their invoice identity as before.

New accounts require confirmed trial or paid access for the bot. Legacy Free
accounts retain their existing allowance. Existing paid plan entitlements and
super-admin access are unchanged. Trial expiry is checked server-side even if
webhooks are delayed. The updated extension also checks the trial deadline before
new entries; stopped sessions are never restarted automatically after renewal.
Stop controls and broker position management remain available. The cookie-protected
trial receipt also offers Cancel trial renewal before account email setup is
finished; a public checkout ID alone cannot cancel anything. Submit the new
extension build to the **existing** Chrome Web Store listing; an already installed
old build cannot acquire the new local deadline guard from a website deployment.

Stripe webhook endpoint: `https://api.tradingwithkaos.com/api/stripe/webhook`.
Include the existing checkout, invoice, cancellation/refund/dispute events and
**`customer.subscription.trial_will_end`**. This event normally arrives about three
days before trial end; KAOS verifies the current subscription and sends an email
using configured account SMTP, with the actual stored subscription price, end
date and Manage billing link. Canceled trials do not get a renewal reminder.
Delivery failures return a retryable error. Enable and test Stripe Customer Portal
cancellation. Hosting CAPTCHA challenges must not intercept Stripe webhooks or
API preflights. A live availability response alone does not verify these services.

Before publishing the trial, test in Stripe sandbox (preferably a test clock):
finish card setup, verify TRIAL/full Pro access and the setup email, cancel before
expiry, verify the reminder event, advance to expiry, and verify a successful
paid invoice converts TRIAL to ACTIVE exactly once. Check failed payment access,
repeat email eligibility and Ultimate's normal paid checkout. Automated repository
tests mock Stripe/mail and cannot certify live email or webhook delivery.


## Current visitor, affiliate and live-release controls

See [VISITOR_AFFILIATE_AND_LIVE_RELEASE.md](VISITOR_AFFILIATE_AND_LIVE_RELEASE.md)
for the new visitor reports, paid-only affiliate rules, percentage editor, Follow
Us editor, Ultimate AI Signals restriction and live Stripe transfer controls.
This supersedes older setup-only payout descriptions when the new release is
installed and actual live Stripe release is enabled. Provider approval, user
connections and hosting activation are still required; a badge or saved key does
not move funds. The latest changes were built and syntax-checked; test runs were
stopped at the owner's request.
