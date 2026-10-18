# KAOS release integration gates (2026-10-18)

This repository being merged is not equivalent to a production deployment. No live-money order execution is enabled by this checklist.

## Integrated and source-controlled
- Authenticated research replay API: Trend Pause plus structural price action (this PR).
- CSV/JSON historical import, diagnostics, W/L/T reporting, and historical entry/exit markers.
- Four-chart read-only terminal and per-member chart settings.
- Member broker *preference* selection (not proof of broker connectivity).
- Admin Free API Manager; keys must be provided and licensed for intended use.

## Required before release
1. **Deployment parity:** build current main, run API and website under real environment configuration, verify routes/proxy/CORS, complete health/DB checks.
2. **Account and payments:** test email/Google login, session refresh, free vs paid entitlement enforcement, Stripe checkout, cancellation/refunds, restore purchases and cross-device behavior.
3. **Market feeds:** verify timestamp units, market identity, stable data sourcing, symbol mapping and disconnected/no-feed states. Never substitute another broker's data silently.
4. **Research validity:** test separate chronological out-of-sample periods for each setup, symbol and timeframe, realistic spreads, fees, slippage and broker payout before setting a strategy live. Track sample counts and drawdowns.
5. **Broker adapters:** broker selection alone does not mean integration. Validate read-only Coinbase/Alpaca/OANDA practice connections separately and handle credential recovery securely.
6. **Order safety:** only after user chooses a specific account, explicit consent, risk limits, duplicate-order prevention, restart reconciliation, order status acknowledgment, emergency stop and realistic end-to-end paper tests. Keep real-money execution off until separately approved.
7. **Extension and mobile:** authenticate first, choose broker, open the appropriate platform only when needed; verify no blank charts, single sign-in window, independent chart positions and updated KAOS branding.
8. **Privacy and security:** verify public /privacy.html returns HTTP 200 from production domain; test Web Store policy disclosures, secrets scanning, audit logging and data deletion.
9. **Admin operations:** verify monitoring, alerting, billing webhooks, incident recovery, backups and rollbacks.
10. **Release smoke test:** fresh account -> choose broker -> check data -> import real candles -> run replay -> observe individual trades -> logout and re-login; perform same flow at free and premium chart limits.

### Explicitly not yet verified
No production deployment, no broker order certification, no demonstrated profitability, and no full end-to-end smoke run have been confirmed by merging these files.
