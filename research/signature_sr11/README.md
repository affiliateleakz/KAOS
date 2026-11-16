# KAOS Strategy SR1.1 replay

The current extension uses support/resistance SR1.1, not the older C9 two-candle continuation module. `apps/api/kaos_signature.py` ports the actual extension engine. Its four signal families are support/resistance rejection (20 seconds), failed-break reclaim (20 seconds), breakout retest (25 seconds) and trend pullback (15 seconds). Context uses closed 5/15/30/60-second bars, 20-bar support/resistance and EMA9/21 trend context.

## Observed result

The checked-in bounded Coinbase BTC/ETH/SOL public trade sample contains 3,944 observed five-second bars across 114 contiguous segments, with 111 gaps. Missing bars are not filled. These markets are price proxies, not Pocket Option OTC or observed binary settlements.

Full replay: 5 trades, 3 wins, 2 losses. Last-quarter temporal holdout: **2 trades, 0 wins, 2 losses**. At the assumed 80% binary payout that is +0.4 units overall and -2 units in holdout. The result is **insufficient_samples** and provides no reliable evidence of an edge. No parameters were tuned to turn this result positive. No live approval is granted.

The replay enters at the next five-second candle open and settles at the exact strategy expiry using a later open. It disallows overlapping trades per asset and settlement across gaps. Spreads, rejected orders, latency and actual broker payouts are not modeled. The historical gate needs at least 100 decided holdout trades and a Wilson lower confidence bound above payout break-even. Historical success alone would still require later prospective validation.

## Reproduce

From the repository root, with API dependencies installed:

```bash
PYTHONPATH=apps/api python apps/api/signature_backtest.py research/signature_sr11/data/combined_5s.json --out research/signature_sr11/audit --source 'Coinbase BTC/ETH/SOL public observed five-second bars; not Pocket Option OTC; no gap filling'
```

`audit/summary.json` records strategy/data hashes and assumptions. `audit/trades.csv` records entries and settlements. `scripts/collect_signature_replay.py` documents the bounded public trade collection. A real Pocket Option candle archive is required before making broker-specific performance claims.
