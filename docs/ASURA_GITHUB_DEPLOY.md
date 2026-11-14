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
