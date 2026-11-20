# KAOS strategy library

One rule set per asset class, one translation layer per broker. Every strategy is scored on the
same out-of-sample slice with the same costs, against two controls: barrier parity (what a
driftless random walk would produce with identical brackets) and a drift-matched placebo (same
number of entries, same long/short mix, random bars).

**Bottom line, stated before the tables:** six of the seven rules are complete and executable,
and exactly two of them - `orb-equity` and `crypto-ignition` - make money after realistic costs.
Neither clears the placebo at p <= 0.05 on the data we have, so they are candidates for forward
paper trading, not for a funded account. The binary rule loses at every payout Pocket Option
offers. That is the finding, not a hedge.

## The library

| id | Name | Asset class | Timeframes | Exit model | OOS trades | Win rate | Exp / trade | Status |
|---|---|---|---|---|---|---|---|---|
| `pulse-range` | KAOS Pulse - range mean reversion | crypto, FX, equity | 1m 5m 15m 1h 4h | 3.0 ATR TP / 5.0 ATR SL / 24 bars | 2,229 | 68.6% | +0.010 ATR | break-even after costs |
| `drive-trend` | KAOS Drive - trend pullback | crypto, FX, equity | 15m 1h 4h | 1.6 ATR TP / 1.0 ATR SL / 24 bars | 554 | 40.0% | -0.023 ATR | no edge |
| `orb-equity` | KAOS ORB - US opening range | equity | 5m 15m | 2.0 ATR TP / 1.0 ATR SL / 24 bars | 279 | 39.8% | **+0.229 ATR** | best candidate |
| `fx-session-breakout` | KAOS FX Session - London open | FX | 5m 15m | 2.0 ATR TP / 1.0 ATR SL / 24 bars | 258 | 34.9% | -0.004 ATR | no edge |
| `crypto-ignition` | KAOS Ignition - expansion breakout | crypto | 5m 15m 1h 4h | 3.0 ATR TP / 1.5 ATR SL / 24 bars | 483 | 35.4% | **+0.106 ATR** | second candidate |
| `binary-fade` | KAOS Binary - range fade | binary | 1m 5m | fixed 3-bar expiry | 2,387 | 48.1% | -0.134 / unit | loses at all payouts |
| `options-credit` | KAOS Options - defined-risk premium | options | 1h decisions | 35 DTE, 0.18 delta, $5 wide | - | - | not measured | signal-only |

Full rules: [SPECS.md](SPECS.md). Numbers, controls and limitations: [RESULTS.md](RESULTS.md).

## Why a 68.6% win rate is not an edge

`pulse-range` wins 68.6% of its trades and still only breaks even. With a 3 ATR target and a
5 ATR stop, a driftless random walk already wins 62.5% of the time (parity = stop / (target +
stop) once you account for the time exit), and each round turn costs 0.04 ATR. The strategy's
6.1pp edge over parity is real in the sample (z = 4.40) but its expectancy is +0.010 ATR, which
is indistinguishable from zero, and its drift-matched placebo gets within 0.1pp of it.

This is the single most useful thing in this directory: **win rate without expectancy is a
marketing number.** Every table here reports both, plus the control.

## Platform coverage

`platforms.py` turns one neutral intent (`side, entry, stop, target, atr`) into each venue's
native order payload. No API keys, no network calls - it builds the request body.

| Platform | Class | Order shape | `pulse-range` | `drive-trend` | `orb-equity` | `fx-session` | `crypto-ignition` | `binary-fade` | `options-credit` |
|---|---|---|---|---|---|---|---|---|---|
| Kraken | crypto spot | limit + stop-loss + take-profit | yes | yes | - | - | yes | - | - |
| Coinbase Advanced | crypto spot | limit + stop-limit pair | yes | yes | - | - | yes | - | - |
| Binance | crypto spot/futures | OCO | yes | yes | - | - | yes | - | - |
| MetaTrader 5 | FX / CFD | pending limit with SL/TP | yes | yes | yes | yes | - | - | - |
| OANDA v20 | FX | market + stopLossOnFill/takeProfitOnFill | yes | yes | - | yes | - | - | - |
| tastytrade | equity + options | bracket / multi-leg | yes | yes | yes | - | - | - | yes |
| Alpaca | equity | `order_class=bracket` | yes | yes | yes | - | - | - | - |
| Pocket Option | binary | direction + fixed expiry | yes | - | - | - | yes | yes | - |

```
python platforms.py kraken BTCUSD 5m crypto-ignition
python platforms.py mt5 EURUSD 5m pulse-range
python platforms.py                       # one example payload per venue
```

Binance spot cannot short; the payload says so instead of pretending. Pocket Option has no stop
or target - the payload reports the payout break-even win rate next to the direction.

## Running it

```bash
python run.py       # scoreboard -> out/results.json, out/pairs.csv, out/RESULTS-table.md
python stress.py    # cost and payout stress -> out/STRESS.md
python charts.py    # out/fig-scoreboard.png, out/fig-equity.png, out/fig-equity-binary.png
```

Data comes from the cached CSVs in `../kaos_strategy/data/` (public Yahoo/CryptoCompare candles,
64 files). Nothing is fetched at scoring time, so results are reproducible offline.

## Files

| File | Purpose |
|---|---|
| `core.py` | strategy registry, session clocks, indicator set, signal helpers |
| `strategies.py` | the seven rules, registered declaratively with their exit model |
| `evaluate.py` | bracket and fixed-expiry simulators, parity baseline, matched placebo, verdicts |
| `run.py` | scores everything, writes the tables |
| `stress.py` | re-scores at 0 / 0.02 / 0.05 / 0.10 ATR per side and at 60 / 80 / 92% payout |
| `charts.py` | scoreboard and equity-curve figures |
| `platforms.py` | neutral intent -> Kraken / Coinbase / Binance / MT5 / OANDA / tastytrade / Alpaca / Pocket Option payloads |
| `out/` | results.json, pairs.csv, STRESS.md, figures, per-strategy trade lists |

## Design rules this library follows

1. **Fixed geometry before looking.** The two v1 engines keep the brackets frozen in the v1
   study (3.0/5.0 and 1.6/1.0 ATR); the breakout rules use the textbook 1 ATR stop / 2 ATR
   target. No parameter in this directory was chosen by searching the test slice.
2. **Next-open fills, stop wins ties, gaps fill worse.** No intrabar optimism.
3. **One position at a time per pair.** No pyramiding, no overlapping trades.
4. **Costs always charged.** 0.02 ATR per side by default, plus a stress table at 10x that.
5. **A control for every claim.** Parity for the barrier geometry, matched placebo for entry
   timing. A rule that cannot beat random entries on the same bars is not a rule.

## Known limitations

- 5m and 15m history is 83 days, 1m is 11 days. The bracketed short-timeframe results are one
  market regime, not a decade.
- 4h candles are resampled from 1h; 5s candles do not exist in any free feed, so sub-minute
  claims are out of scope.
- Options results are not measured at all: without a chain feed there is no honest P&L.
- Crypto drift over the sample flatters every long-biased rule; the placebo is there to absorb
  exactly that, which is why `pulse-range`'s 4.4-sigma parity edge collapses to 0.1pp of lift.
