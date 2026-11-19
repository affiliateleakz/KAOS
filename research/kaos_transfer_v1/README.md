# Fixed four-hour breakout: external-market test and forward-paper runner

One configuration was frozen in `plan.json` at commit `78d3eaa`: four-hour breakout20, three-ATR trailing/initial stop, seven-day maximum hold, same one-percent fee-budget filter. No parameter changes, alternate asset selection or additional configurations followed the result.

The new fixed markets are DOGE, LTC, LINK and AVAX against USDT, using checksum-verified public hourly archives. January2021-December2024 provides context; January2025-October2026 is the evaluated window. These new series share previously seen crypto regimes; this adaptive test is not pristine prospective proof. The earlier reserved BNB/XRP/ADA and Pocket Option results remain unscored.

Across all four markets: **113 trades**, net **8.66R**, profit factor **1.206**. Combined doubled-cost/one-hour delayed-entry stress: **0.54R**. The locked diagnostic gate passed: **False**. Sample size and the adjusted weekly confidence bound fail. Do not present the small positive sum as a validated edge. R is original price-risk normalization, not portfolio/dollar return.

| Market | Trades | Base net R | Stress net R |
|---|---:|---:|---:|
| DOGEUSDT | 26 | -3.20 | -4.04 |
| LTCUSDT | 28 | 0.21 | -4.52 |
| LINKUSDT | 34 | 8.12 | 6.45 |
| AVAXUSDT | 25 | 3.52 | 2.65 |

`trades.csv` discloses the entire simulated trade ledger, including losses. `result.json` includes both identical-exit baselines; `provenance.json` records source and rule hashes. Execution uses hourly OHLC approximations, assumed Binance-style costs, flat independent risk units, and retrospective price observations. No real order, accepted fill, borrowed short, or performance guarantee is implied.

## Prospective paper observations

`scripts/paper_kaos_swing.py` is a standalone one-shot recorder, with no authenticated API, broker credentials or order submission path. It retains immutable hourly history, records its bootstrap seed, hashes the strategy/configuration, and uses SQLite transactions and unique observation/event IDs to prevent duplicate entries. Replays and forward observations cannot share a journal. Feed changes, fee/slippage changes and code changes also require a separate journal.

The entry window is two minutes after a completed four-hour candle. It never backfills an old entry or infers an earlier favorable stop fill. Simulated buys use observed ask, exits observed bid, with explicit additional slippage and fees. Coverage gaps and late stop observations are recorded, and affected exits are flagged. Discrete snapshots cannot prove an intratick stop fill, available order size, or broker acceptance. All records remain research-only and ineligible for performance claims.

Coinbase is the explicit default public feed, using USD products mapped from the research labels. Its quotes and seed history differ from the Binance historical test, so results must remain distinct. The illustrative default fee is **60 basis points per side** for Coinbase and **10** for Binance, with **2 bps** additional slippage per side. Verify an actual account fee tier before interpreting results; defaults are not provider fee promises. `--fee-bps` and `--slippage-bps` are recorded and pinned in each journal. Coinbase BNB is explicitly unsupported.

A public Coinbase one-shot observation succeeded and recorded HOLD with no paper position; the journal contains one forward observation, no submitted order and no closed paper trade. Binance returned451 here and wrote no observation. Thirty offline checks passed, including replay separation, idempotence, freshness, rollback, quote-side fills, costs/feed pinning, gaps, conservative trailing timing and public adapters. `paper_smoke_check.json` records the actual status separately from unit fixtures.

**No continuous worker has been started or deployed.** The command processes one snapshot and exits; future collection needs an external scheduler or process on suitable hosting. It does not run on cPanel and does not change the website or extension.

```bash
python scripts/paper_kaos_swing.py --provider coinbase --symbol BTCUSDT --database /private/kaos-paper-coinbase.sqlite
python scripts/paper_kaos_swing.py --database /private/kaos-paper-coinbase.sqlite --status
```

For archived observation files, use a separate database and explicit `--replay --observation file.json`. Historical or synthetic fixtures must never be advertised as forward paper results. Input files contain symbol, observedAt(epoch milliseconds), bid, ask, source/feed/product, and closed UTC-aligned hourly OHLC rows. Forward files require fresh quote timestamps. Keep databases outside Git.

## Reproduce

```bash
python scripts/collect_swing_history.py --symbols DOGEUSDT LTCUSDT LINKUSDT AVAXUSDT --start-year 2021 --end-year 2026 --end-month 10 --out /private/transfer --cache /private/archives
python scripts/research_kaos_transfer.py --data /private/transfer
python -m pytest -q scripts/tests/test_paper_kaos_swing.py scripts/tests/test_kaos_swing_research.py
```
