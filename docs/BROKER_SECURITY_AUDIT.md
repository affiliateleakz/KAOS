# Broker connection security audit (Coinbase Advanced)

Scope: `apps/api/routes_broker_coinbase.py` (read-only connection), `apps/api/routes_coinbase.py` (order gateway),
`apps/api/broker_vault.py`, the website Broker Connections page, the extension Coinbase panels and the Expo Coinbase screen.
Status of the account sync itself: **UNVERIFIED**, never run against a real Coinbase account.

## Credential handling
| Check | Result |
|---|---|
| Who enters the key | The member types it into the KAOS website (Broker Connections) or the extension connect panel. Devin, GitHub and chat never receive it. |
| Transfer-capable keys | Refused on connect (`get_api_key_permissions().can_transfer`). Keys without View are refused. |
| Encryption at rest | Fernet/MultiFernet with `KAOS_BROKER_VAULT_KEY`. Without the key the server answers 503 and stores nothing. |
| Key rotation | **Added.** Set the new `KAOS_BROKER_VAULT_KEY`, put the old one in `KAOS_BROKER_VAULT_PREVIOUS_KEYS`, run `python broker_vault.py rotate`, then drop the old key (`test_broker_vault.py`). |
| Disconnect / replace | `DELETE /api/v1/broker-connections/coinbase` deletes the row. Reconnecting overwrites it. |
| Echo in responses | Responses are field-whitelisted (`key_hint` = last 4 chars of the key id only). **Fixed:** FastAPI 422 validation errors used to echo the submitted body (`input`), which could include `private_key`. They now return only `loc/msg/type` (`server.py`, `test_broker_vault.py`). |
| Echo in errors | Coinbase SDK exceptions are reduced to their class name; signed JWTs in exception text never leave the server. |
| Server logs / audit log | No request-body logging middleware. The audit log stores only the action and the key hint. |
| Frontend / extension | No `console.*` of the form or payload. The website form clears after submit. The extension sends the key straight to the KAOS API through the background worker and does not store it in `chrome.storage`. |
| Transport | Clients call the API over HTTPS in production (`REACT_APP_BACKEND_URL`). The local dev stack is HTTP on localhost only. |

## Auth and CORS
- Every broker route requires `get_current_user` (bearer/cookie JWT). Rows are always filtered by `user_id`. Cross-member isolation is tested.
- CORS allows `FRONTEND_URL` and `http://localhost:3000` with credentials, and no wildcard. **Before staging/production:** set `FRONTEND_URL` to the exact staging origin and drop `localhost:3000` from the production image.
- The extension calls the API from its service worker (host permissions), not through CORS. Its broker proxy only allows the five `/broker-connections` paths.

## Coinbase key permissions each action needs
| KAOS action | Coinbase endpoint | Permission |
|---|---|---|
| Connect check | `get_api_key_permissions` | View |
| Balances, open orders, fills, fee tier, products | `get_accounts`, `list_orders`, `get_fills`, `get_transaction_summary`, `get_products` | View |
| Order **preview** | `preview_market_order_buy/sell` | Expected **Trade** (untested). A View-only key is expected to get a permission error, which KAOS shows as "preview failed". |
| Submit / cancel | `market_order_*`, `cancel_orders` | Trade, plus `KAOS_COINBASE_LIVE_ORDERS=enabled` plus unexpired founder consent. **Not authorized.** |
| Withdraw / transfer | — | Never used. Keys with Transfer are refused. |

A key with Trade permission needs separate, explicit founder approval and a controlled live test.
