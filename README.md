# KAOS Trading (development monorepo)

**Status:** development baseline that was reconstructed from the 2026-10-18 founder handoff. **Not production. Paper/shadow only.**
Read `docs/KNOWN_GAPS.md` before changing anything.

## Quick start
```bash
make dev        # copies .env.example -> .env, starts mongo + api (:8001) + web (:3000)
```
- Site: http://localhost:3000
- API health: http://localhost:8001/api/health
- Demo login (dev only): `alice@demotrader.com`, using the password in `KAOS_DEMO_PASSWORD` from `.env`
- Owner login: `ADMIN_EMAIL` / `ADMIN_PASSWORD` from `.env`
- Paper orders (dev, logged in): `POST /api/v1/paper/orders` `{"symbol":"BTC-USD","quantity":"10","quote_price":"67000"}`; admin kill switch `POST /api/v1/paper/kill-switch`

## Layout
| Path | What |
|---|---|
| `apps/api` | FastAPI + MongoDB backend |
| `apps/web` | Website + member portal (React/Vite) |
| `apps/extension` | Chrome MV3 extension (v1.7.11) |
| `apps/mobile` | Expo mobile starter |
| `services/collectors`, `services/research` | Data collectors, local research service |
| `packages/kaos-core` | Membership/referral prototype, backtest primitives |
| `research/` | Strategy v2 and its v2.1 replay audit (**FAIL, unvalidated**) |
| `docs/` | Audit docs, handoff specs, release notes |

## Tests
`make test` (Python suites) · `make web-build` · `make scan` (gitleaks)

## Rules
No live trades, real charges, affiliate payouts or production deploys without explicit founder approval. Never commit `.env`, credentials or `data/`.

## Current code audit

See [the code audit and chart-data repair report](docs/CODE_AUDIT_AND_CHART_DATA.md) for verified fixes, tests, remaining release blockers and hosting update steps. Live orders and payments remain disabled.
