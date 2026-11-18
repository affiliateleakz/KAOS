# Connect Coinbase without member API keys — 1.7.39

## Provider prerequisite

Coinbase's documentation, checked 18 November 2026, states that OAuth client
creation is currently restricted to approved partners. KAOS cannot grant itself
that approval. Apply through:

- https://www.coinbase.com/developer-platform/developer-interest
- https://portal.cdp.coinbase.com/oauth

Describe KAOS as a member-authorized, extension-driven Coinbase Advanced Trade
spot bot. Users retain their own Coinbase accounts. Request account/product read,
order submission, and order/fill reconciliation permissions, with no transfer,
withdrawal, payment, or custody access. No real orders were sent by this work.

## Owner setup after approval

Register this exact callback in the approved Coinbase OAuth application:

`https://api.tradingwithkaos.com/api/v1/broker-connections/coinbase/oauth/callback`

Requested scopes:

- `wallet:accounts:read`
- `wallet:user:read`
- `wallet:transactions:read`
- `wallet:buys:create` (the documented Advanced Trade order-create permission,
  including spot market SELL orders; not `wallet:trades:create`, which is convert)
- `offline_access`

In cPanel's backend Python application environment, set privately:

- `KAOS_COINBASE_OAUTH_CLIENT_ID`: approved application client ID
- `KAOS_COINBASE_OAUTH_CLIENT_SECRET`: approved application client secret
- `KAOS_COINBASE_OAUTH_REDIRECT_URI`: the callback above (also the code default)

Preserve the existing `KAOS_BROKER_VAULT_KEY` and rotation keys. Do not put secrets
in chat, GitHub, frontend environment variables, extension files, or URLs. Deploy
the matching website/backend and extension 1.7.39, restart the API, and confirm the
account-connection flow with Coinbase. Credentials being present makes the button
available; it does not prove Coinbase approval or successful authorization.

## Member flow

Choose Coinbase → Connect Coinbase account → sign in/approve on Coinbase's own
website → KAOS callback confirms connection → return to KAOS → Check connection
& use Coinbase. The website also offers the same account authorization under
Dashboard → Broker Connections. No Coinbase password or private key is entered
into KAOS for this method. Connecting alone never starts a trading session.
The manual API-key form remains under Advanced until OAuth is actually available.

## Security and recovery

Authorization-code flow uses PKCE S256 and a random single-use, ten-minute state
bound to the authenticated KAOS member. Only a hash of state is stored; the PKCE
verifier and access/rotating refresh tokens are encrypted with the broker vault.
Callback validation consumes state atomically. Provider errors and cancellation
cannot replace a saved connection. Callback pages are no-store, no-referrer, and
contain no provider payloads. Hosting access logs should redact callback query
parameters (authorization code and state).

The granted scopes must contain the documented order/account/fill permissions
and must not contain transfer or other unexpected permissions. The backend uses
a narrowly defined Advanced Trade bearer adapter, preserving the existing order
reservation and reconciliation gateway. The API-key-only `/key_permissions`
endpoint is not called for OAuth.

Refresh is serialized in MongoDB. A refresh timeout or interrupted process does
not retry a potentially rotated token: reauthorize the same Coinbase account.
Reauthorization cannot silently switch an existing connection to another Coinbase
identity and retains all holdings/order records. Broker vault rotation includes
OAuth access/refresh fields. Keep previous vault keys during in-flight ten-minute
OAuth authorizations as well.

Disconnect retains the existing gateway/position safety checks and requests
Coinbase token revocation before deleting local authorization. An unconfirmed
revocation leaves the connection available for review. Neither disconnect nor
OAuth approval liquidates positions. Existing API-key connections must be safely
disconnected before switching methods; no automatic migration is attempted.

## Verification limits

Production frontend build, backend import/syntax, and package checks are local
checks. The owner previously requested no new test execution; regression test
source is included but no new test suite was run. Partner provisioning, consent,
rotating refresh, revocation and live Coinbase trading have not been verified
against an approved KAOS OAuth app. Do not advertise OAuth as available before
those provider-dependent steps are completed.

Official sources:

- https://docs.cdp.coinbase.com/coinbase-app/oauth2-integration/overview
- https://docs.cdp.coinbase.com/coinbase-app/oauth2-integration/integrations
- https://docs.cdp.coinbase.com/coinbase-app/oauth2-integration/access-and-refresh-tokens
- https://docs.cdp.coinbase.com/coinbase-app/advanced-trade-apis/rest-scopes
