# KAOS Strategy v1

A rule-based, instrument-agnostic trading strategy plus the harness used to test it honestly.

- **Spec:** [`spec.md`](spec.md) - exact rules, indicator definitions, execution assumptions,
  platform mapping, parameter table.
- **Evidence:** [`RESULTS.md`](RESULTS.md) - out-of-sample results, barrier-parity and placebo
  controls, cost sensitivity, and the variants that failed.
- **Platforms:** [`platforms/tradingview_kaos.pine`](platforms/tradingview_kaos.pine),
  [`platforms/kaos_mt5.mq5`](platforms/kaos_mt5.mq5),
  [`platforms/live_runner.py`](platforms/live_runner.py).

## What it is

Two engines sharing one execution model, gated by a Kaufman efficiency-ratio regime:

| Regime | Engine | Entry | Target | Stop | Expiry |
|---|---|---|---|---|---|
| range (ER ≤ 0.28) | PULSE | price stretched ≥1 ATR from EMA20, RSI ≤42 / ≥58, outside Bollinger 20/2 | 3.0 ATR | 5.0 ATR | 24 bars |
| trend (ER ≥ 0.30) | DRIVE (off by default) | pullback into EMA20 that closes back with the trend | 1.6 ATR | 1.0 ATR | 24 bars |

Parameters are bars or ATR multiples only, so the same numbers run on a 5s crypto candle and
a 4h equity candle. The module never places an order - it returns an intent that a platform
adapter translates.

## Quick start

```bash
cd research/kaos_strategy
PYTHONPATH=. python3 strategy.py                 # last-bar intent for BTCUSD 5m
PYTHONPATH=. python3 portability.py              # frozen-parameter test, 42 pairs
PYTHONPATH=. python3 report_charts.py            # pooled portfolio + figures
PYTHONPATH=. python3 cost_sensitivity.py         # expectancy vs dealing cost
```

Live intent on any supported chart:

```python
import data
from strategy import evaluate

df = data.load("EURUSD", "5m")
intent = evaluate(df, bar_seconds=300)
# {'side': 'long'|'short'|'flat', 'price':…, 'stop':…, 'target':…,
#  'expiry_bars': 24, 'expiry_seconds': 7200, 'regime':…, 'atr':…}
```

Paper loop (no broker, no credentials):

```bash
PYTHONPATH=. python3 platforms/live_runner.py --symbol BTCUSD --tf 5m --source coinbase
```

## The number that matters

Out of sample, frozen parameters, 42 asset/timeframe pairs: **66.1% win rate over 1,564
trades**, against a **62.5% barrier parity** for the 3.0/5.0 bracket. The 65% target is met;
the skill component is +3.6 pp. At 0.05 ATR per side the pooled expectancy is **-0.075 ATR**
per trade, so the configuration is a research baseline, not a profitable retail system.
`RESULTS.md` has the full breakdown and the list of failed variants.

Read it before trading anything.

## Repository layout

```
strategy.py           indicators, regime, signals, brackets, platform intents
backtest.py           next-open fills, stop-first tie-break, gap handling, placebo-ready
data.py               Coinbase + Yahoo loaders, local CSV cache, 4h resampling
study.py              per-pair geometry selection, train/test, placebo control
portability.py        one frozen parameter set across every pair
cost_sensitivity.py   expectancy vs dealing cost
refine.py             entry-filter variants (documents an overfit result)
report_charts.py      pooled portfolio and the four figures in out/
platforms/            TradingView, MetaTrader 5, generic live runner
out/                  generated results (JSON/CSV/MD/PNG)
```

## Data

Public feeds only, cached in `data/` (64 series, ~41 MB). Crypto from Coinbase Exchange,
FX and equities from Yahoo. 5-second candles are not available from any free feed; 4h series
are resampled from 1h.
