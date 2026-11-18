# Coinbase Advanced: connection stage

This release implements the server routes already called by the website's **Broker Connections** page and the extension's Coinbase setup panel. Before this release those routes were absent from the FastAPI app. It verifies read access and stores encrypted credentials; it is not an autonomous Coinbase bot or live-trading certification.

## Server setup

- Configure a separate, valid Fernet `KAOS_BROKER_VAULT_KEY` privately in the Python application's environment. Never paste it in chat, GitHub, or the browser. The commerce vault key is a separate setting.
- If a broker vault key already exists, preserve it. Replacing it makes saved credentials unreadable unless the old key is retained in `KAOS_BROKER_VAULT_PREVIOUS_KEYS` during rotation. New and existing gateway reads support that rotation chain. The `broker_vault.py rotate` utility imports the correct application database module; it is an explicit database write, not part of deployment.
- Restart the Python app after environment changes. Deploy the backend router and refreshed cPanel entrypoint together. The login-validation wrapper permits authenticated broker preference and Coinbase connection setup while continuing to block order submission, billing, and unrelated broker writes.
- Keep `KAOS_COINBASE_LIVE_ORDERS` disabled. Credential changes are refused if the live gateway is enabled, or if this member has an active/uncertain Coinbase position. Reconciliation must precede removing credentials needed to resolve such a position.

## Member setup

1. Create a Coinbase CDP key for Advanced Trade. Start with **View** permission, with **Transfer disabled**. Trade permission is not required for this stage. Restrict the key to the actual outbound hosting IP when using an IP allowlist.
2. Sign in to KAOS and open **Dashboard → Broker Connections** (`/dashboard/brokers`). Choose Coinbase as the preferred broker if desired; this does not authorize trading.
3. Enter the original key name and private key. A Coinbase export containing `name` and `privateKey` is also accepted; the separate name may be blank with that JSON. Supported key formats follow the installed Coinbase SDK, including EC/Ed25519 PEM and supported Ed25519 base64 exports. Literal escaped PEM newlines are normalized.
4. Click **Verify & save Coinbase**. The server checks key permissions and requests at most one page of accounts. It refuses transfer-enabled or unknown-transfer-permission keys and does not overwrite a saved connection if verification fails. Secrets are encrypted at rest and never returned to the browser.
5. Click **Check Coinbase markets** to request a read-only sample of USD spot products. It is a partial catalog, not a buy recommendation or verified order capability. Saved verification is timestamped and does not claim a continuously healthy connection.
6. Use **Disconnect** to remove the current member's stored connection, subject to the position/gateway restrictions above. It does not close orders or positions at Coinbase, and it does not revoke the key at Coinbase itself.

Never submit a wallet seed phrase, recovery phrase, password or withdrawal key. Verification makes no order or transfer calls. The current extension can call these new server routes after backend deployment; no new Chrome Store item is needed. Existing extension wording may recommend View + Trade; View-only is accepted by the new backend. Starting the bot with a Coinbase preference is not yet a supported automated Coinbase trading workflow.

## Market data and paper trading

KAOS already has a separate paper-trading feed using Coinbase Exchange public quotes/candles. It does not need a Coinbase account key and does not trade a real Coinbase account. Keep that simulation separate from the Advanced Trade account-connection badge. Current broker-native chart attachment, order execution, reconciliation and strategy validity require their own acceptance evidence before Coinbase can be advertised as an automated bot connector.

## Verification and remaining hosted work

Repository tests use fake provider responses and generated temporary test keys. They cover member scoping, authentication, encryption, permission rejection, key formats, failed updates, vault rotation, active-position restrictions, sanitized errors, bounded payloads, market-field filtering and cPanel routing. Browser fixtures cover save, secret clearing, explicit market reads, failure, disconnect and mobile layout. They do not verify a real Coinbase account.

Hosted acceptance still needs the owner's actual key entered privately in KAOS, correct broker vault configuration, a successful account/market check, and confirmation of disconnect. If the API hostname returns a Bot Verification HTML page, resolve the hosting/routing issue first; a server connection check cannot bypass it. No real keys or orders are used during repository development, and no live trading flag is enabled by this release.
