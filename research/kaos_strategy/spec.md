# KAOS Strategy v1 - specification

A single rule set that runs unchanged on any instrument and any candle size from 5 seconds
to 4 hours. Every parameter is expressed in **bars** or in **ATR units**, never in pips,
dollars, percentages or clock time, so nothing needs re-tuning when you move from a 5s
crypto chart to a 4h equity chart.

The module emits a neutral *intent* (side, entry reference, stop, target, expiry) and never
places an order. Platform adapters translate the intent.

---

## 1. Inputs

Closed candles only: `ts, open, high, low, close, volume` (volume is optional and unused by v1).
A bar is evaluated after it closes; the trade is filled at the **next bar's open**.

Derived per bar:

| Name | Definition | Purpose |
|---|---|---|
| `TR` | `max(high-low, |high-prev_close|, |low-prev_close|)` | true range |
| `ATR` | Wilder EMA of `TR`, length 14 (`alpha = 1/14`) | volatility unit for every bracket and cost |
| `EMA20`, `EMA50` | EMA of close | mean-reversion anchor and trend context |
| `RSI14` | Wilder RSI | stretch confirmation |
| `BB20` | 20-bar SMA ± 2 population SD | stretch confirmation |
| `ER20` | Kaufman efficiency ratio: `|close - close[20]| / Σ|close - close[i]|` over 20 bars, clipped to [0,1] | regime switch |
| `z` | `(close - EMA20) / ATR` | entry distance |
| `z_slow` | `(close - EMA50) / ATR` | knife guard |
| `er_slope` | `ER - ER[1]` | drive confirmation |

## 2. Regime

```
trend_up   : ER >= 0.30 and |z_slow| > 0.5 and EMA20 > EMA50     -> +1
trend_down : ER >= 0.30 and |z_slow| > 0.5 and EMA20 < EMA50     -> -1
range      : ER <= 0.28                                          ->  0
undecided  : everything else                                     -> no trade
```

The gap between 0.28 and 0.30 is deliberate dead space: the middle of the ER distribution is
where both engines lose. `|z_slow| > 0.5` stops a trend label from being printed when price is
sitting on its own slow mean.

## 3. PULSE - the mean-reversion engine (range regime)

Long when **all** hold:

```
regime == range
z      <= -1.0            # at least 1 ATR below EMA20
RSI    <= 42
close  <  BB lower
z_slow >  -2.0            # knife guard: not falling apart
```

Short is the mirror (`z >= +1.0`, `RSI >= 58`, `close > BB upper`, `z_slow < +2.0`).

**Brackets (validated):**

```
target = entry + 3.0 * ATR      (short: -)
stop   = entry - 5.0 * ATR      (short: +)
expiry = 24 bars, exit at close of bar 24 if neither level is touched
```

Reward:risk is 0.6:1. That is intentional - see §6.

## 4. DRIVE - the continuation engine (trend regime, optional)

Long when `regime == trend_up` and the bar pulls back into EMA20 and closes back above it
strongly (`low <= EMA20`, `close > EMA20`, `close > open`, `er_slope > 0`). Mirror for short.

```
target = entry + 1.6 * ATR
stop   = entry - 1.0 * ATR
expiry = 24 bars
```

**v1 ships with DRIVE disabled by default.** On 591 out-of-sample trades it produced
39.7% wins against 38.5% barrier parity and -0.003 ATR expectancy, i.e. no measurable edge.
It stays in the code because it is the natural home for a trend alpha once one is found.

## 5. Execution rules that are part of the strategy

1. One position per instrument; no pyramiding, no overlapping trades. A new signal is ignored
   while a position is open.
2. Fill at next bar open. A market order at bar close is not assumed.
3. If a bar contains both target and stop, assume the **stop** filled first.
4. A gap through the stop fills at the open, worse than the stop price.
5. Cost is charged in ATR units on entry and exit (`pnl = side*(exit-entry)/ATR - 2*cost`).
6. Position size: risk a fixed fraction `f` of equity per trade, `size = f*equity / (5.0*ATR)`,
   so every trade risks the same money regardless of instrument or timeframe.
7. Binary-option platforms: use the same entries with a fixed expiry equal to the median time
   to target in bars, and require payout `p` such that `WR > 1/(1+p)`. At 0.80 payout the
   break-even hit rate is 55.6%; at 0.90 it is 52.6%.

## 6. Why the win rate is high, and why that is not the same as edge

For a driftless random walk with target `a` ATR and stop `b` ATR, the probability of touching
the target first is

```
parity = b / (a + b)
```

So a 3.0/5.0 bracket wins **62.5% of the time with no skill at all**. Any claimed win rate
must be quoted next to this number, and the honest score is `WR - parity`. The v1 evidence
pack reports exactly that, plus a random-entry placebo scored by identical exit code.

Consequence for the 65% target: with a 3.0/5.0 bracket you need only +2.5 pp of real excess to
print 65%. The study found +3.6 pp pooled, which is real but thin, and thinner than typical
retail spread - see `RESULTS.md` §6.

## 7. Platform adapters

| Platform | File | How it is expressed |
|---|---|---|
| Python / any exchange API | `strategy.py` (`evaluate`) | dict intent: side, price, atr, stop, target, expiry_bars |
| TradingView | `platforms/tradingview_kaos.pine` | Pine v5 `strategy()` with same indicators and brackets |
| MetaTrader 5 | `platforms/kaos_mt5.mq5` | EA: limit order with SL/TP, bar-counted expiry, fixed-fraction sizing |
| Pocket Option / binary | `strategy.py` (`binary_option_intent`) | call/put + expiry seconds, break-even table |
| Any REST broker | `platforms/live_runner.py` | polling loop, paper mode by default, intent printed as JSON |

Anything that can compute EMA, ATR, RSI, Bollinger and a 20-bar efficiency ratio can run this.
There is no machine learning model, no external data dependency and no look-ahead.

## 8. Timeframes

The rules are bar-counted, so the same numbers apply at 5s, 1m, 5m, 15m, 1h and 4h. What
changes is the wall-clock duration of a trade: `expiry_seconds = 24 * bar_seconds`.

Empirically (out-of-sample, frozen parameters):

| Timeframe | Trades | Win rate | Expectancy at 0.02 ATR/side |
|---|---|---|---|
| 1m | 205 | 65.7% | +0.048 ATR |
| 5m | 531 | 73.0% | +0.366 ATR |
| 15m | 245 | 57.3% | -0.446 ATR |
| 1h | 444 | 61.2% | -0.311 ATR |
| 4h | 139 | 68.7% | +0.142 ATR |

5m is the strongest slice and 15m/1h the weakest. That ordering was observed after the fact,
so treat it as a lead to re-test rather than a law. **5s itself is unverified**: no free public
feed serves 5-second candles, so the 5s claim rests on the bar-based parameterisation, not on
a backtest.

## 9. Parameters

```python
Params(
    er_len=20, er_range_max=0.28, er_trend_min=0.30,
    ema_fast=20, ema_slow=50, atr_len=14, rsi_len=14, bb_len=20, bb_sd=2.0,
    z_entry=1.0, rsi_pulse=42.0, knive_guard=2.0,
    tp_atr=3.0, sl_atr=5.0, max_bars=24,          # PULSE, validated
    dr_tp_atr=1.6, dr_sl_atr=1.0, dr_max_bars=24, # DRIVE, disabled by default
    mode="pulse",
)
```

`tp_atr/sl_atr/max_bars` in the dataclass default to 0.8/1.2/12, which is the settings the
first geometry sweep started from; the validated profile is 3.0/5.0/24 and is what
`platforms/` and `RESULTS.md` use. Set them explicitly.

## 10. Known limitations

- The excess over parity is smaller than realistic dealing costs on most venues.
- FX 5m is the only class/timeframe combination with comfortable positive expectancy;
  crypto 15m/1h is clearly negative.
- Time exits are ~40% of trades; they are counted in expectancy but not in the win rate.
- Free data has quality limits: EURUSD 5m is 31% flat bars, so its numbers are softer than
  BTCUSD's.
- No news filter, no session filter, no correlation cap across simultaneous positions.
