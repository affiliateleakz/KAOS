# KAOS broker integration roadmap (17 broker/platform targets)

This document describes product targets, **not** verified connectivity, permission to place orders, or a ranking based on market share. The authenticated broker connection and order handling must always enforce authorization on the server. An entry in `REGISTRY` does **not** grant execution access.

## Integration priority and truthfulness

| Broker ID | Customer segment | State at creation | Next evidence needed |
| --- | --- | --- | --- |
| coinbase | Crypto | authentication_implemented | Real user-initiated read-only connection; verify balances, fills, errors; no live orders |
| alpaca | Stocks and ETFs | planned | Developer/sandbox account, authenticated balances, market data permissions |
| oanda | Forex | planned | Practice v20 API credentials, account and instrument read |
| pocketoption | Short-duration contracts | adapter_development | Permission/compliance review and repair of legacy extension |
| webull | Stocks/options and eligible assets | planned | Approved OpenAPI access and allowed commercial use |
| schwab | Stocks/options | planned | Developer app/OAuth eligibility and commercial API authorization |
| ibkr | Multi-asset | planned | Gateway/account prerequisites and compliant deployment architecture |
| kraken | Crypto | planned | Read-only exchange API permission and sandbox/test design |
| tradier | Stocks/options | planned | Approved brokerage API and test credentials |
| tastytrade | Options/multi-asset | planned | OAuth/API eligibility and sandbox |
| mt5 | Broker-dependent forex/CFDs | planned | Specific broker + bridge deployment + permissions |
| robinhood | Popular retail stocks/options/crypto | planned | Official asset-specific APIs; do not assume crypto API covers stocks/options |
| fidelity | Retail brokerage | planned | Explicit authorized commercial account/trading integration |
| etrade | Stocks/options | planned | OAuth developer program and production permission |
| crypto_com | Crypto exchange | planned | Verify Exchange API eligibility, not retail app assumptions |
| tradestation | Stocks/options/futures | planned | API program access and commercial eligibility |
| forex_com | Forex | planned | Region/account-specific approved API details |

All broker-specific scopes, licensed market-data subscriptions, relevant geographic restrictions, market-hours handling, regulatory disclosures and product permissions must be confirmed before changing state.

## State transitions

`planned` → `adapter_development` → `authentication_implemented` → `read_only_verified` → `order_management_tested` → `trading_approved`. `temporarily_unavailable` is an exceptional state, not an advancement. Transitions require concrete dated test evidence for **that broker**, including source account, workflow and API response sanitization, without uploading credentials or customer data. UI labels must not infer connectivity from registry presence.

## Near-term delivery gates

1. Repair PR #11 recovery and cancellation safety with tests; preserve fail-closed live trading.
2. Founder enters Coinbase View-only credentials **directly in secure KAOS UI**, never in issue comments or Devin messages. Verify read-only balance/position/fill display across devices.
3. Build Alpaca read-only/sandbox authentication, connection and account views; test live third-party APIs only with owner-approved account access. No real orders.
4. Build OANDA practice-account read-only authentication and market-data adapter; same evidence gates.
5. Investigate Webull/Schwab official API eligibility and commercial rights, then prioritize implementations accordingly.
6. Build four-chart shared trading UI: Free 1; Pro 4; Ultimate 4. Enforce limits server-side.
7. Follow with IBKR, Kraken, Tradier, tastytrade, MT5, Robinhood (official asset-specific permissions), E*TRADE, Fidelity, Crypto.com Exchange, TradeStation, FOREX.com and Pocket Option according to approved access and customer demand.

## Mandatory broker-specific acceptance criteria

- **Connection**: secure consent/credential handling, key rotation/disconnect, member isolation, read-only verified account data.
- **Data**: sourced, timely quotes/candles and clear entitlement, rate limit and exchange delay labeling.
- **Orders**: only permitted order types, broker precision/rules, idempotency, unknown-outcome recovery, fills and fee reconciliation.
- **Controls**: close/cancel safety under emergency stop, global exposure limits, no unvalidated strategy/AI live execution.
- **Platforms**: website, extension, Android and iPhone all share account truth; unavailable platforms/features clearly labeled.
- **Commercial readiness**: explicit API terms, redistribution/data licenses, eligibility, security review, human approval.

**Live order submission remains disabled by default.** No mock test alone qualifies a broker for real trading. No deployment or PR merge is authorized by this document.
