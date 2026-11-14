# KAOS → Asura Hosting: one-time GitHub SSH setup

This is the simplest safe first step for the **existing domains**:

- Website: `https://tradingwithkaos.com`
- API: `https://api.tradingwithkaos.com`
- Existing API application root: `/home/itsabout/tradingwithkaos.com/backend` (Python 3.11)
- **Current live API is the older native WSGI application**: `passenger_wsgi.py` imports `wsgi_app.application`, reported build `1.1.11-full-admin-repair`.

The GitHub workflow `Prepare KAOS release on Asura Hosting` only uploads release ZIPs to `~/kaos_release_staging/<commit-SHA>/`. It **does not** switch API runtimes, upload into the live app, modify the website, restart cPanel Python, or deploy live trading. The mismatch between the old native WSGI API and the new extension must still be resolved and tested. Do not replace the existing `passenger_wsgi.py` by itself.

## One-time Asura setup

1. In cPanel, check **Security → SSH Access**. If you cannot find it, ask Asura Hosting support to enable SSH for your account. Confirm the SSH **host**, **port**, **username**, and the server's **verified host-key fingerprint** directly with Asura Hosting.
2. In cPanel **SSH Access → Manage SSH Keys**, generate a dedicated deployment key pair, or import a new public key generated on your own machine. **Authorize the public key** for SSH login. Keep the private key out of GitHub source files, chats, screenshots, and website folders. Prefer a restricted deployment-only account/key when Asura supports it.
3. Ensure the SSH account can create files in a **private** directory under its home directory (`~/kaos_release_staging`) and that it cannot accidentally overwrite production paths through account-level restrictions, if supported.

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
