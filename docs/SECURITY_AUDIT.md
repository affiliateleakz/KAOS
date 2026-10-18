# Security audit (initial)

Tools: gitleaks 8.21.2 over the whole handoff and its nested zips, plus manual grep for keys, tokens, SSIDs, emails, and PEM blocks.

## Findings
| # | Severity | Finding | Status |
|---|---|---|---|
| S1 | High | `seed.py` had a hard-coded admin password fallback and a hard-coded demo password. It seeded demo users in every environment | Fixed: values come from env, demo seeding is dev-only |
| S2 | High | `write_credentials()` wrote admin and demo passwords in plaintext to `/home/itsabout/.../memory/test_credentials.md` on every production boot | Fixed: dev-only, explicit path opt-in |
| S3 | High | `api.tradingwithkaos.com.zip` contains `memory/test_credentials.md` (admin password, demo users) and Passenger logs | Not imported. **Rotate the production admin password** if it was ever used live |
| S4 | Medium | `public/index.html` loaded `assets.emergent.sh/scripts/emergent-main.js` and a PostHog snippet that sent analytics and **session recordings** to Emergent's PostHog (`ap.emergent.sh`) | Removed (third-party data flow, privacy-policy risk) |
| S5 | Medium | `routes_billing.py`: `stripe.api_key = ... or "sk_test_emergent"` | Fixed: no fallback key |
| S6 | Info | gitleaks: 2 `generic-api-key` hits in `KAOS_REPAIRED/evidence_verify_token_parity.txt`. Both values are already `REDACTED` | False positive, file not imported |
| S7 | Medium | Email goes through the Emergent integration proxy (`integrations.emergentagent.com`, `EMERGENT_EMAIL_KEY`). Google login goes through Emergent OAuth | Open: decide whether to replace with a KAOS-owned provider |
| S8 | Medium | `KAOS_COINBASE_LIVE_ORDERS` env flag can enable real Coinbase orders | Open: keep `false`. A server-side kill switch and approval gate are needed before any live use |
| S9 | Info | Restricted market-data export (197 MB) | Excluded by `.gitignore` (`data/`). No emails, tokens, or SSIDs were found in it |
| S10 | Info | Extension host permissions include `127.0.0.1:8765/8766` and several Pocket Option mirrors | Review before the next store submission |

The imported repo tree is clean under gitleaks (`make scan`).

## Required before production
Rotate every secret that ever appeared in the cPanel tree. Use a secrets manager or host env (never `.env` in Git). Run the security review gate in `docs/handoff/ACCEPTANCE_CRITERIA.md`.
