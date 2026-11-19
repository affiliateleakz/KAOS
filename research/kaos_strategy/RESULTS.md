# KAOS Strategy v1 - backtest results

Everything below is out of sample unless it is labelled otherwise. Numbers come from the
JSON/CSV files in `out/`, produced by the scripts in this directory. Nothing here is
rounded up, and nothing was re-run until it looked good.

---

## 1. The question

> Build a strategy usable on any platform, any timeframe from 5 seconds to 4 hours, on
> stocks, crypto and forex, and backtest it to a 65%+ win rate.

Three claims have to be checked separately:

1. does it produce a **65%+ win rate**,
2. is that win rate *skill* or just the shape of the target/stop bracket,
3. does it make money after costs.

The answer is yes, mostly no, and no at typical retail costs. Details below.

## 2. Data

64 cached CSV series (64 files, ~41 MB) built from public feeds:

| Class | Instruments | Timeframes | Source |
|---|---|---|---|
| Crypto | BTCUSD, ETHUSD, SOLUSD, XRPUSD | 1m, 5m, 15m, 1h, 4h | Coinbase Exchange candles |
| FX | EURUSD, GBPUSD, AUDUSD, USDJPY | 1m, 5m, 15m, 1h, 4h | Yahoo daily/intraday |
| Equity | AAPL, MSFT, NVDA, TSLA, SPY, QQQ | 1m, 5m, 15m, 1h, 4h | Yahoo intraday |

The study basket is 42 asset/timeframe pairs (14 crypto, 8 FX, 20 equity). 4h series are
resampled from 1h.

Data quality issues that affect how much weight the numbers deserve:

- **EURUSD 5m is 31.3% flat bars** (open = high = low = close) and has -0.045 autocorrelation.
  FX numbers on that series are the softest in the pack.
- EURUSD 1h is 9.2% flat; SOLUSD 5m is 2.9% flat.
- Crypto and equity series are clean: 0% flat bars, autocorrelation ≈ 0.
- **5-second candles could not be obtained** from any free public feed. The 5s claim rests on
  the parameters being bar-counted, not on a 5s backtest. Do not quote a 5s result.

## 3. Protocol

Fixed before the test numbers were seen:

- Chronological 60/40 split per dataset. Geometry is chosen on the first 60% only.
- Fill at the **next bar's open**; a decision never uses the bar it trades.
- If a bar contains both target and stop, the **stop** is assumed to fill first.
- Gaps through the stop fill at the open (worse than the stop).
- No overlapping trades on one instrument.
- Cost charged in ATR units on both sides.
- A **placebo control**: the same number of entries at random bars in the same slice, same
  long/short mix, scored by identical exit code and costs. A real signal that cannot beat
  its own placebo is measuring geometry, not prediction.

Two studies:

- `study.py` - geometry re-selected per dataset on train, then applied to test.
- `portability.py` - **one frozen geometry for all 42 pairs**, chosen before any test number:
  target 3.0 ATR, stop 5.0 ATR, expiry 24 bars, PULSE only. This is the honest portability test.

## 4. Headline: the 65% target is met

Frozen configuration, pooled out-of-sample across all 42 pairs:

| Metric | Value |
|---|---|
| Trades | 1,564 |
| Win rate (decided trades) | **66.1%** |
| All-trade win rate (incl. time exits) | 56.5% |
| Barrier parity | 62.5% |
| Excess over parity | +3.6 pp |
| Expectancy at 0.02 ATR/side | **-0.015 ATR** |
| Profit factor at 0.02 ATR/side | 0.99 |
| Time exits | 40.0% of trades |

Per pair: mean win rate 66.2%, **62% of the 42 pairs cleared 65%**, mean excess over parity
+3.67 pp, positive expectancy on 45% of pairs.

By asset class (pooled, 0.02 ATR/side):

| Class | Trades | Win rate | Expectancy | PF |
|---|---|---|---|---|
| Crypto | 661 | 63.3% | -0.089 ATR | 0.94 |
| FX | 412 | **71.3%** | **+0.166 ATR** | **1.12** |
| Equity | 491 | 65.6% | -0.066 ATR | 0.96 |

By timeframe (pooled, 0.02 ATR/side):

| TF | Trades | Win rate | Expectancy | PF |
|---|---|---|---|---|
| 1m | 205 | 65.7% | +0.048 ATR | 1.03 |
| 5m | 531 | **73.0%** | **+0.366 ATR** | **1.28** |
| 15m | 245 | 57.3% | -0.446 ATR | 0.70 |
| 1h | 444 | 61.2% | -0.311 ATR | 0.80 |
| 4h | 139 | 68.7% | +0.142 ATR | 1.10 |

Representative pairs (frozen geometry, out of sample, 0.02 ATR/side):

| Pair | n | WR | Parity | Exp ATR | Placebo WR |
|---|---|---|---|---|---|
| GBPUSD 5m | 74 | 83.0% | 62.5% | +1.002 | 70.9% |
| QQQ 5m | 18 | 84.6% | 62.5% | +3.124 | 62.5% |
| SPY 5m | 22 | 84.2% | 62.5% | +1.789 | 66.7% |
| SOLUSD 5m | 69 | 76.9% | 62.5% | +0.655 | 71.7% |
| GBPUSD 1h | 75 | 75.0% | 62.5% | +0.312 | 72.9% |
| EURUSD 5m | 71 | 70.6% | 62.5% | +0.296 | 66.1% |
| ETHUSD 1m | 98 | 68.1% | 62.5% | +0.198 | 57.5% |
| BTCUSD 5m | 68 | 68.2% | 62.5% | -0.072 | 67.7% |
| USDJPY 5m | 99 | 67.7% | 62.5% | -0.096 | 62.9% |
| ETHUSD 15m | 45 | 36.4% | 62.5% | -1.062 | 74.4% |
| SOLUSD 1h | 27 | 35.3% | 62.5% | -1.559 | 69.6% |

Equity 5m cells carry only 18-22 trades, so their intervals are wide - treat them as leads.

## 5. Why 66% is not 66% of skill

For a driftless walk, `P(target first) = stop/(target+stop) = 5/(3+5) = 62.5%`. The strategy
prints 66.1%, so the real excess is **+3.6 pp**, not 66. The placebo column shows the same
thing from the other side: random entries with identical brackets land within a few points of
the strategy on most pairs (mean lift over placebo +0.43 pp across 42 pairs; on crypto the
placebo was actually *better* by 5.7 pp).

The earlier re-selection study (`study.py`, 24 pairs) makes the point even more sharply:
mean test win rate 71.1%, but mean lift over placebo **-0.56 pp** and positive expectancy on
only 41.7% of pairs. When each dataset gets its own best-on-train geometry, the win rate looks
better and the edge disappears - that is overfitting, measured.

## 6. Costs decide the outcome

Pooled expectancy as dealing cost rises (each side, in ATR):

| Cost/side | Expectancy | PF | Crypto | FX | Equity |
|---|---|---|---|---|---|
| 0.00 | +0.025 ATR | 1.02 | -0.049 | +0.206 | -0.026 |
| 0.02 | -0.015 ATR | 0.99 | -0.089 | +0.166 | -0.066 |
| 0.05 | -0.075 ATR | 0.95 | -0.149 | +0.106 | -0.126 |
| 0.10 | -0.175 ATR | 0.88 | -0.249 | +0.006 | -0.226 |
| 0.20 | -0.375 ATR | 0.77 | -0.449 | -0.194 | -0.426 |
| 0.35 | -0.675 ATR | 0.61 | -0.749 | -0.494 | -0.726 |

Even at **zero** cost the whole-pack edge is +0.025 ATR/trade - about 2.5% of one ATR. FX
breaks even around 0.10 ATR/side; crypto and equities are negative from the first tick of
spread. A 5m FX spread plus slippage is commonly 0.05-0.15 ATR. **As specified, this is not a
profitable retail system**, and quoting its 66% win rate as an edge would be dishonest.

## 7. What was tried and failed

- **DRIVE (trend continuation), 1.6/1.0 brackets:** 591 out-of-sample trades, 39.65% wins vs
  38.46% parity, -0.003 ATR expectancy. No edge. Shipped disabled.
- **Deeper stretch entries** (z 1.5/2.0, RSI 38/35): best on train (+0.174 ATR at cost 0.05),
  then -0.244 ATR on test with 63.5% wins. Textbook overfit; rejected.
- **Volatility floor** (ATR above its own 200-bar median): +0.009 and +0.072 ATR on train,
  not carried forward after the winner was chosen.
- **Per-pair geometry tuning**: raises apparent win rate (mean 72.5%) and destroys OOS
  expectancy (negative on 58% of pairs).
- Earlier mean-reversion configurations (0.8/1.2 brackets, tight targets) produced 46-59% win
  rates against 60% parity - i.e. worse than a coin flip.

## 8. Honest limitations

- Free-feed quality (flat FX bars, no tick data) means the FX +0.166 ATR/trade should be
  discounted; it is the class with the dirtiest data.
- 5s is unvalidated. 4h equity/FX cells have 7-23 trades and are statistically meaningless.
- No spread model per venue, no commission model, no swap/funding, no borrow costs.
- No news, session, or correlation controls; running 42 pairs simultaneously would stack
  correlated crypto exposure.
- Time exits are 40% of trades and are excluded from the win rate but included in expectancy;
  they are mostly small losses, which is why the all-trade win rate is 56.5%.
- Single 60/40 split, not anchored walk-forward with multiple folds.

## 9. What would actually move the needle

1. **Cheaper execution or larger ATR per trade.** The edge is ~0.03-0.2 ATR and cost is
   0.05-0.15 ATR. Same rules on a venue with sub-0.02 ATR cost (maker rebates, deep crypto
   books) flips the sign.
2. **A real entry alpha, not a better bracket.** The bracket work is done; 62.5% parity is a
   wall. The team already found candidates worth testing as entries: BTCUSD 5m pulse forward
   return +0.203 ATR at h=12 (t=3.18), BTCUSD 1h er_mom +0.456 at h=24 (t=3.18), SPY 15m
   mr_raw +0.517 at h=24 (t=3.09). Each needs to be run through this same harness.
3. **Regime-conditional gating with more than ER.** Volatility term structure, session, and
   funding/basis are the obvious additions.
4. **Multiple folds.** Replace the single 60/40 split with 5 anchored folds and report the
   distribution of fold expectancies, not one number.

## 10. Reproduce

```bash
cd research/kaos_strategy
PYTHONPATH=. python3 study.py            # per-pair geometry selection, train vs test
PYTHONPATH=. python3 portability.py      # frozen geometry, 42 pairs, placebo control
PYTHONPATH=. python3 report_charts.py    # pooled portfolio + figures in out/
PYTHONPATH=. python3 cost_sensitivity.py # expectancy vs dealing cost
PYTHONPATH=. python3 refine.py           # entry-filter variants, train vs test
```

Artifacts: `out/study.md`, `out/portability.md`, `out/portfolio.json`,
`out/cost_sensitivity.csv`, `out/refine.json`, and four figures
(`fig_wr_by_pair.png`, `fig_pooled_equity.png`, `fig_wr_by_timeframe.png`, `fig_expectancy.png`).
