# DELIVERY GATES & ACCEPTANCE TESTS

Gate 0: Extract and inventory all assets with hashes, evidence-based source-of-truth selection, list missing production repositories/keys. Secret/PII scanner runs before any git upload.
Gate 1: Staging website/api/mobile/extension compile and start; CI lint/type/unit/integration tests; versioned project architecture and migrations.
Gate 2: Shared KAOS login/test membership/broker choice complete end-to-end across website/extension/phone; one login window, correct browser ID and callbacks.
Gate 3: Paper broker lifecycle end-to-end; no live orders; correct fee and P&L calculations; risk kill switch, idempotent orders, concurrency and outages tested.
Gate 4: Data pipelines and reproducible backtest on independently sourced stock/crypto/forex data with realistic fees and strict untouched holdout; REJECT failed strategies.
Gate 5: Scanners operate on authorized real data with traceable freshness, quality and licensing.
Gate 6: AI research collects lawful labeled examples, stores versioned models, shows calibration/drift and honest validation; Pro AI advisory only. Ultimate AI approval remains explicit separate gate.
Gate 7: Stripe test billing, webhook reconciliation, membership entitlements, mixed-tier affiliate referral commission ledger and refund/chargeback tests. No real payouts.
Gate 8: Android Play internal test and iPhone TestFlight compatible artifact after accounts/signing; login, watchlist, paper controls, alerts all exercised on devices.
Gate 9: Legal/security/production readiness review; release only with founder explicit approval, gradual feature flags, observability, backups, incident runbook.

Output per milestone: actual files, commit/PR, test log, deployment reference, before/after screenshot or screen recording where appropriate, known failures and blockers, next 3 engineering tasks. Do not label placeholders done.
