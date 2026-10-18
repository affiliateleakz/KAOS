# KAOS Trading 3.0 — v0.5 Whale & Insider Research Development

This package is the prior KAOS 3.0 v0.4 integrated development source, with incremental v0.5 modules for native Ethereum high-value transactions, reported SEC Form 4 purchases/sales. Existing broker trading code is carried over unchanged.

**Start with:** `collectors/README_WHALES_V05.md` and `INTEGRATION_STATUS.md`.

## Distinctions
- Ethereum native value movements are **neutral** observations, not token/DEX trades and not verified large-investor buys.
- Form 4 ownership XML reports historical insider transactions; SEC acceptance can happen after the transaction date, and coverage is incomplete under issuer-only lookup.
- Full 13F holding extraction, politician transactions, options trade tape ingestion, social scanning, push notifications, full database candle archive, trained AI, production mobile binary, and cloud deployment are not included.

## Validation
42 offline collector tests + 7 backend research tests passed before this removal; rerun verification; Python sources compile; four changed UI JSX/TSX files passed TypeScript syntactic transpilation (NOT a full Expo or website build). No live feed/API credentials were used and no on-device testing was performed.
