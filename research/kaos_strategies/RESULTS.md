# Results - KAOS strategy library

Machine-readable versions: [`out/results.json`](out/results.json), [`out/pairs.csv`](out/pairs.csv),
[`out/STRESS.md`](out/STRESS.md). Figures: [`out/fig-scoreboard.png`](out/fig-scoreboard.png),
[`out/fig-equity.png`](out/fig-equity.png).

## Data and windows

| Timeframe | Pairs | Median bars | Span | Out-of-sample slice |
|---|---|---|---|---|
| 1m | 8 | ~11,000 | 11 days | last 4.4 days |
| 5m | 16 | ~24,000 | 83 days | last 33 days |
| 15m | 14 | ~8,000 | 83 days | last 33 days |
| 1h | 14 | ~24,500 | 1,021 days | last 408 days |
| 4h | 14 | ~6,100 | 1,021 days | last 408 days |

Universe: BTCUSD, ETHUSD, SOLUSD, XRPUSD; EURUSD, GBPUSD, USDJPY, AUDUSD; AAPL, MSFT, NVDA, SPY,
QQQ, TSLA. Public candles, cached locally, nothing fetched during scoring.

The short timeframes are the weak link and they are stated as such: 33 out-of-sample days on 5m
is roughly 60 US sessions per symbol, which is enough to see an effect and not enough to trust
one.

## Method

- **Split.** Chronological 60/40 by bar. Indicators are computed on the full causal series and
  only entries after the cutoff are scored.
- **Fills.** Entry at the next bar's open. If the stop and target are both inside one bar, the
  stop is assumed hit first. Gaps fill at the open, not at the stop price.
- **Overlap.** One position at a time per pair, enforced by the same code path as v1.
- **Costs.** 0.02 ATR per side (0.04 ATR round turn) in the headline table; 0 / 0.05 / 0.10 in
  the stress table.
- **Parity baseline.** For a target/stop pair (T, S) the driftless hit rate is S/(T+S) once the
  time exit is accounted for: 62.5% for 3.0/5.0, 33.3% for 2.0/1.0, 38.5% for 1.6/1.0.
- **Placebo.** 12 replications per pair. Each draws the same number of longs and the same number
  of shorts as the real signal, at random bars inside the same test window, and runs them through
  the identical exit engine. `p` is the share of replications that match or beat the strategy's
  excess over parity.

## Scoreboard (out of sample)

| Strategy | Trades | Win rate | Parity | Excess | z | Exp/trade | PF | Placebo exp | Lift | p | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Pulse - range MR | 2,229 | 68.6% | 62.5% | +6.1pp | 4.40 | +0.010 | 1.01 | -0.050 | +0.1pp | 0.58 | break-even after costs |
| Drive - trend pullback | 554 | 40.0% | 38.5% | +1.6pp | 0.76 | -0.023 | 0.97 | -0.017 | +0.6pp | 0.58 | no edge |
| ORB - US open | 279 | 39.8% | 33.3% | +6.5pp | 2.23 | +0.229 | 1.38 | -0.162 | +10.4pp | 0.21 | promising, not significant |
| FX session - London | 258 | 34.9% | 33.3% | +1.6pp | 0.53 | -0.004 | 0.99 | -0.029 | +1.1pp | 0.46 | no edge |
| Ignition - expansion | 483 | 35.4% | 33.3% | +2.0pp | 0.91 | +0.106 | 1.11 | -0.017 | +4.5pp | 0.33 | promising, not significant |
| Binary - range fade | 2,387 | 48.1% | 55.6% | -7.5pp | -7.34 | -0.134/unit | 0.74 | -0.177 | +2.3pp | 0.12 | loses at all payouts |
| Options - premium | - | - | - | - | - | - | - | - | - | - | not measured |

Read the Pulse row carefully. It beats parity by 4.4 standard deviations and still earns
+0.010 ATR per trade, because the barrier geometry already gives a driftless walk 62.5%. Its
placebo - random entries with the same long/short mix - lands within 0.1pp of it. The win rate is
a property of the brackets, not evidence of skill.

## Per-class breakdown

| Strategy | Crypto | FX | Equity |
|---|---|---|---|
| Pulse | 1,015 trades, 65.4% WR, -0.073 ATR | 855, 72.7%, +0.175 | 359, 64.6%, +0.041 |
| Drive | 147, 39.7%, +0.048 | 281, 42.7%, +0.029 | 126, 34.3%, -0.443 |
| ORB | - | - | 279, 39.8%, +0.224 (9/12 pairs positive) |
| Ignition | 483, 35.4%, +0.127 (9/16 pairs positive) | - | - |
| Binary fade | 1,515 bets, 52.0%, -0.058/unit | 694, 39.9%, -0.318 | 178, 46.6%, -0.151 |

Consistency matters more than the pooled number: a rule that makes money in 9 of 12 symbols is
a rule; a rule that makes money in 31 of 62 pair-runs is a coin flip with a cost problem.

## Cost and payout stress

| Strategy | 0.00 ATR | 0.02 ATR | 0.05 ATR | 0.10 ATR |
|---|---|---|---|---|
| Pulse | +0.050 (PF 1.04) | +0.010 (PF 1.01) | -0.050 (PF 0.96) | -0.150 (PF 0.89) |
| Drive | +0.022 (PF 1.03) | -0.018 (PF 0.97) | -0.078 (PF 0.89) | -0.178 (PF 0.77) |
| ORB | +0.269 (PF 1.46) | +0.229 (PF 1.38) | +0.169 (PF 1.26) | +0.069 (PF 1.10) |
| FX session | +0.036 (PF 1.05) | -0.004 (PF 0.99) | -0.064 (PF 0.91) | -0.164 (PF 0.80) |
| Ignition | +0.146 (PF 1.16) | +0.106 (PF 1.11) | +0.046 (PF 1.05) | -0.054 (PF 0.95) |

Binary fade at 0.80 payout: -0.134 per unit staked (48.1% wins vs 55.6% break-even). At a 92%
payout it is still -0.077 (needs 52.1%). There is no payout at which this rule turns positive.

Only ORB survives a 10x cost assumption. That is the test that separates a rule with a real
horizon from one that is harvesting noise inside the spread.

## What was tried and rejected

These are kept because the negative results are the expensive part:

- **Tight targets for a high win rate** (0.8/1.2, 0.5/5.0 ATR): 46-59% win rates against 60%+
  parity, or 95%+ win rates with 91% parity and negative expectancy. Raising the win rate by
  shrinking the target raises parity at the same time.
- **Per-pair geometry re-selection** on the test slice: mean 71.1% win rate, but -0.56pp lift
  against the placebo and positive expectancy in only 41.7% of pairs. That is fitting the
  barrier to the sample.
- **Deeper z / RSI filters** (+0.174 ATR in train, -0.244 ATR out of sample): the classic
  overfit signature.
- **5-second candles**: no free feed provides them, so any sub-minute claim in this project
  would be fabricated.

## Reproduce

```bash
cd research/kaos_strategies
python run.py && python stress.py && python charts.py
```

`run.py` takes about 40 seconds. Seeds are fixed (`seed=11 + replication`), so the placebo is
reproducible.

## What to do next

1. **Paper-trade ORB and Ignition for 60 sessions** with the exact rules in SPECS.md, logging
   every skipped signal (the close-position filter is where discretion creeps in).
2. **Extend 5m history** to 2+ years before risking size. The current 83-day window is the
   binding constraint on every short-timeframe conclusion here.
3. **Do not deploy the binary rule.** If binary exposure is required commercially, present it as
   a distribution channel for the Pulse signal, not as an edge.
4. **Options needs a chain feed** (ORATS or a broker sandbox) before any claim is made. The
   structure rule is written; the measurement is not.
5. **Keep the placebo in the loop.** Every future rule should have to beat random entries on the
   same bars with the same direction mix before it gets a page on the site.
