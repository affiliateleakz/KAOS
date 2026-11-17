# Current known gaps

See [BUSINESS_LAUNCH.md](BUSINESS_LAUNCH.md) for the current operational handoff. Historical audit documents describe earlier states and are not current pricing, branding or deployment instructions.

## Confirmed decisions and implemented foundations

- Canonical site is tradingwithkaos.com with its approved Viking/black/gold homepage. The React build uses Vite and the low-thread cPanel preparation script.
- Free $0; Pro $29.95/month or $299.95/year; Ultimate $99.95/month or $995.95/year. Pro/Ultimate support four broker slots; owner device allowance is unlimited.
- The user confirmed the FastAPI API is responding through the production Passenger app. Application root is `/home/itsabout/tradingwithkaos.com/backend`; repository is `/home/itsabout/repositories/KAOS` on the development branch. A new full-release marker identifies installed files after activation; it is not a process-health certificate.
- Official Chrome item ID is gbobopmnjgeeegniphckfpalhnebapjm. Google sign-in previously worked for the owner. Current test package is 1.7.33; current Store publication still needs direct verification.
- Registration, entitlement/device checks, public membership catalog, private training queues, owner-only research, community and affiliate accounting have code/browser test coverage. Mocked integration tests do not prove current hosted behavior.
- New billing fixes reconcile authoritative periods and invoice identities, preserve earned commissions on cancellation, separate sandbox/live credentials, and block a second active subscription. Secure SMTP supports password recovery.

## Still requiring real evidence or a business decision

1. Install the tested release and confirm hosted registration, session restore, password reset and the official extension flow. Mail credentials and real delivery are not available in the development workspace.
2. Stripe account authentication, isolated test checkout, signed webhooks, renewal/failure/recovery, cancellation, refund/dispute and ledger reconciliation must be demonstrated before a billing-capable live rollout. The current cPanel validation gate remains on. Arbitrary portal plan changes/proration and catalog migration are not certified.
3. Payout settings are setup/accounting, not a connected active payout service. Provider permission, recipient onboarding, held/reversed balances and reconciliation need verification before release.
4. Dedicated training-worker hosting is still the owner's deferred decision. No production pretrained model or profitable strategy was established by the recent research.
5. Radar source settings and actual feed availability/rate budgets need checking on hosting. Do not imply unavailable sources are scanning or force shared-host CPU-heavy workers.
6. Chrome Store review/submission and installed-broker chart/order behavior need direct verification. Do not create a replacement Store item or claim compatibility with planned brokers that have no working connector.

No live hosting, payment, payout or strategy execution state can be inferred solely from GitHub commits. Use Admin → Launch Status for configuration evidence, then the hosted acceptance sequence in BUSINESS_LAUNCH.md.
