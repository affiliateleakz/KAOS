# KAOS Strategy v2.1 — recorded candle rejection audit

This package reproduces a strict replay of Strategy v2 as originally implemented. The core trading algorithm is unchanged; **v2.1 is an audit, NOT a profitable replacement**.

## Verified result (archived KAOS historical OTC candle data)

- Source: KAOS_ALL_DATA_2026-10-03T16-14-56.json, field rawCandleHistory.byAsset, 5-second OHLC.
- Only consecutive 5-second candle segments of 100+ rows are considered. 60-second aggregation requires 12 complete 5-second bars per minute and at least 115 contiguous resampled minutes.
- Evaluation is not a clean future holdout; historical data was already used extensively in prior KAOS research.
- No volume data was present, therefore volume confirmation is bypassed as the original code specifies.
- Simulations use a fresh hypothetical $10,000 for each independent contiguous segment, 0.5% risk budget per trade, shorting permitted. Dollar P&L is summed across these separate *simulations*, **not an achievable consolidated account equity outcome**.
- Brokerage costs are illustrative 0 or 10 basis points commission per side, plus 2 bps adverse slippage per side. Not broker-verified OTC execution costs. Prices on OTC contracts may not be executable in regular stop/target positions.

| Timeframe | Fee / side | Segments | Markets | Trades | Win rate | Sum of simulated net P&L |
|---|---:|---:|---:|---:|---:|---:|
| 5s | 0 bps | 74 | 27 | 4,698 | 15.54% | -$16,114.22 |
| 5s | 10 bps | 74 | 27 | 4,698 | 6.09% | -$71,978.06 |
| 60s | 0 bps | 7 | 7 | 187 | 26.20% | -$742.25 |
| 60s | 10 bps | 7 | 7 | 187 | 21.93% | -$3,889.77 |

These low win rates are influenced by adverse stop-first candle ordering and fixed stop/target; they are **not daily investment returns**.

**Conclusion: FAIL. Do not deploy Strategy v2 for live trading.** This is not a test of exchange stocks, crypto or spot forex; separate licensed data and instrument-specific transaction costs are required. No profitability can be inferred from this archival replay.

## Reproduce

Install `pandas numpy`, then from this folder:

```
python -m unittest -v test_strategy.py
python replay_archive.py path/to/KAOS_ALL_DATA_2026-10-03T16-14-56.json --out audit
```

Outputs: `audit/segment_results.csv` and `audit/summary.json`. Original `kaos_strategy.py` remains available for independent CSVs:

```
python kaos_strategy.py your_ohlcv.csv --fee-bps 10 --slippage-bps 2 --no-shorts --out output
```

Safety: backtester is research only. No real orders or AI trading, and no proven advantage. Inputs require accurate uniform candles, correct fees and validated spread; v2 short accounting and portfolio simulation are simplified.
