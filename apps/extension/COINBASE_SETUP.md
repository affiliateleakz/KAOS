# KAOS Coinbase 1.7.2 — API connectivity stage

This release implements a Coinbase connection screen with the user's referral link, a local Python bridge, Coinbase CDP JWT authentication, account retrieval, and product listing. **Read-only only: no order placement, WebSocket feed, persistence, or multi-user server credentials implemented.** Do not use for live automated Coinbase trading.

Install: `pip install PyJWT cryptography requests` then `python kaos_coinbase_bridge.py` on the same computer as the extension. Load the unpacked Chrome extension via chrome://extensions. Log in to KAOS and select Coinbase. Enter your own newly issued CDP key name and complete PEM private key. The credentials stay in the local Python process memory and are cleared on restart or failed authentication. Never place secrets in the ZIP.

The bridge accepts requests only from Chrome extension origins on 127.0.0.1. This is a **development-only** boundary, not production multi-tenant credential storage. It has no per-extension identity binding; other installed extensions may be able to reach it. For a commercial release use authenticated backend sessions, secret encryption, authorization and audits.

No real Coinbase account connection could be tested in this build environment because no authenticated broker session is available. The Coinbase authentication logic is implemented but must be validated with a newly generated key. Pocket Option source remains unchanged. Kraken and IBKR remain unimplemented.
