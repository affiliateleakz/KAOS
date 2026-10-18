# Architecture audit (baseline v0.9 DEV)

## Components
| Component | Tech | Status |
|---|---|---|
| `apps/api` | FastAPI, Motor/MongoDB, slowapi rate limiting, Stripe, bcrypt/JWT cookies | Boots locally (`make dev`). 84 offline tests pass |
| `apps/web` | React 18 CRA + craco, Tailwind/shadcn, react-router 6, react-query, axios | Builds with the reconstructed config. Talks to the API through `/api` |
| `apps/extension` | Chrome MV3, v1.7.11. `content.js` is 13k lines and targets Pocket Option | Not loaded or tested yet. Its manifest has no `key` (see Known gaps) |
| `apps/mobile` | Expo/React Native 0.2.0 starter | Not run |
| `services/collectors` | Python market/news/SEC/social collectors | 84 offline tests pass |
| `services/research` | local research service used by the extension | Not exercised |
| `packages/kaos-core` | Foundation v0.7: memberships/referral prototype, backtest primitives | 12 tests pass |
| `research/strategy_v2*` | EMA/structure strategy and its replay audit | 6+6 tests pass. Audit verdict is FAIL |

## API surface (routers in `apps/api/server.py`)
auth (`/api/auth/*`), strategies, community, billing (Stripe), extension v1 (`/api/v1/*`: license/devices/sync), admin, trading (paper/durable paper pipeline), affiliate, botsync, AI, Coinbase (live orders behind `KAOS_COINBASE_LIVE_ORDERS`), FinBERT (shadow), opportunity radar. This PR adds `GET /api/health`, which pings MongoDB.

## Runtime / deploy
- Local: `docker-compose.yml` runs mongo:7, api (uvicorn :8001), and web (CRA dev :3000, which proxies `/api` to the API).
- Historical production (api snapshot): cPanel Passenger → `passenger_wsgi.py` → `a2wsgi(server.app)` under `/home/itsabout/...`.
- **Unresolved:** `KAOS_REPAIRED` patches a separate synchronous `wsgi_app.py`. We need the founder to confirm which runtime actually serves `api.tradingwithkaos.com`.

## Data model (Mongo collections, from `db.ensure_indexes`)
users, sessions, login_attempts, password_reset_tokens, settings (plans, branding, affiliate, trading config), strategies, community, devices/licenses, trade events, affiliate commissions, opportunity radar records.

## Startup side effects
On startup the app runs `ensure_indexes()`, `seed_admin()`, `seed_demo()`, and `write_credentials()`. Changes in this PR:
- Demo seeding runs only when `KAOS_ENV=development`.
- The admin password must come from the environment. The hard-coded fallback is gone.
- The plaintext credentials file is written only in dev and only when `KAOS_TEST_CREDENTIALS_PATH` is set. Previously it was written unconditionally to a hard-coded production path.
