# File provenance

Source: `KAOS_DEVIN_COMPLETE_PROJECT_HANDOFF_2026-10-18.zip` (supplied by the founder on 2026-10-18).
The archive contents were checked against `docs/handoff/MANIFEST.json`. Every listed SHA-256 matched.
The originals are kept read-only outside Git. **None of them has been confirmed as the code running in production.**

## Supplied archives (from MANIFEST.json)

| Archive | Bytes | SHA-256 | Role |
|---|---|---|---|
| KAOS_TRADING_3_0_SOCIAL_SQUEEZE_FUSION_V0_9_DEV.zip | 10210459 | 4d46478e1af339538a3cc35c97fd5a1914cea62b839930a46c87c10e62995583 | **Imported baseline**: backend, website, extension, mobile, collectors |
| KAOS_TRADING_3_0_TRADER_FIRST_BRANDING_V0_8_1_DEV.zip | 10199692 | cfc766374b42714b9ab5699e224214eb3b74fb750ac40e9fea9ce8324f93b8a2 | Older sibling. Only `BRAND_MISSION_V0_8_1.md` was taken |
| KAOS_TRADING_ENGINE_2.0.2_FINBERT_SHADOW_DEV.zip | 107635 | 7b12643c47410a410310b69acdb6a440c89093a4a1434d48c76d9ae118599ea5 | Subsumed by the v0.9 backend |
| KAOS_MULTIBROKER_REGISTRY_1.7.32_DEV.zip | 99610 | 35518c728a00f2eebc5be1d1f8dcaac8ccfc6675514a0f09baba12c2551f7305 | Subsumed by the v0.9 backend |
| KAOS_WEBSITE_WITH_PRIVACY_POLICY_V0_7_1.zip | 8692883 | 564336619bfdc180bcb9213fb1dd2f8c9cf25290ff528460ea22c39eed5af2b6 | Subsumed by the v0.9 site |
| api.tradingwithkaos.com.zip | 289243 | f59051447d1817a324849e2bf815be532911d0a641a6ac082872aa9c944f5e2e | cPanel snapshot of a FastAPI+a2wsgi backend, older than v0.9. **Not imported**: it contains `memory/test_credentials.md`, logs, and a nested older zip |
| KAOS_REPAIRED_2026-10-14.zip | 299464 | 12107283405e20ad6606c95467eba56afde6f9979b0a22969bcc1fd574fd7e1e | Patches for a *different* hand-written `wsgi_app.py` runtime. Its parent zip is missing. Not imported, kept for reference |
| KAOS_All_In_One_Foundation_v0.7.zip | 14683 | 49273c72ef12db6be36f5a591bd220f560694fef8a2b6803e3c42e3f6ee8f835 | → `packages/kaos-core` |
| KAOS_Strategy_Structure_v2.zip | 46269 | 160c5f24b4919e53e51ea32f982bb440b66d49047a95d606644339baf54ad140 | → `research/strategy_v2` |
| KAOS_Strategy_v2_1_Replay_Audit.zip | 12193 | 06dc23023d96ebff2b22d55a0d807cdff8b4e2ad95687c2bc6fa7bd32833e995 | → `research/strategy_v2_1` (audit verdict: FAIL) |
| data/KAOS_ALL_DATA_2026-10-03T16-14-56.json | 197138751 | af5112f119d2e3f518ff05cdc4b065d7fb2afd219cd26f0e0a9afdbc16ba688f | Restricted market data (Pocket Option OTC 5 s candles). **Never committed** |

The handoff also contains packages that the manifest does not list (see `SOURCE_CATALOG.json`):
- `KAOS_PRO_MULTIBROKER_TERMINAL_DEV`: extension 1.7.12. It carries the manifest `key` that keeps the stable extension ID.
- The mobile v0.1/v0.2 starters. Mobile v0.2 is the same as `apps/mobile`.

## Repository mapping (commit 1 = unmodified copy, layout moves only)

| Repo path | Origin inside v0.9 zip |
|---|---|
| `apps/api` | `backend_foundation/` |
| `apps/web` | `site/tradingwithkaos.com/frontend/`. Build config (`package.json`, craco, tailwind, postcss, jsconfig) was **reconstructed** because none was shipped |
| `apps/extension` | `extension/` (v1.7.11) |
| `services/research` | `extension/research_service/` |
| `services/native_trainer` | `extension/native_trainer/` |
| `apps/mobile` | `kaos-mobile/` (v0.2.0) |
| `services/collectors` | `collectors/` |
| `docs/release-notes` | root `*.md` of v0.9 plus `BRAND_MISSION_V0_8_1.md` |
| `docs/handoff` | the handoff specifications |

## Chronology (latest file timestamp per zip)
REPAIRED 10-14 03:37 → api snapshot 10-14 05:02 → Pro Terminal 10-14 05:05 → Multibroker 1.7.32 10-14 19:44 → Engine 2.0.2 10-15 → mobile 10-16 03:5x → Website V0_7_1 10-16 05:39 → **3.0 V0_9 10-16 05:49** → 3.0 V0_8_1 10-16 17:00 (later timestamp, but its content is a subset of v0.9) → Foundation v0.7 10-17 → Strategy v2 10-17 → v2.1 audit 10-18.
