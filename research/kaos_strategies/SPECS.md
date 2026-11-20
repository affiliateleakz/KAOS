# Rule specifications

Every strategy is a function of closed candles only: a signal is decided on the close of bar `i`
and filled at the open of bar `i+1`. Nothing reads the current bar's high/low before deciding.

Notation: `ATR` is the 14-period Wilder ATR, `EMA20`/`EMA50` are exponential means, `RSI` is
14-period, `ER` is the 20-bar Kaufman efficiency ratio (net move / path travelled), and
`z = (close - EMA20) / ATR`.

Shared regime test (used by Pulse, Drive, Binary):

```
ER >= 0.30 and |z_slow| > 0.5 and EMA20 > EMA50   -> trend up
ER >= 0.30 and |z_slow| > 0.5 and EMA20 < EMA50   -> trend down
ER <= 0.28                                        -> range
otherwise                                         -> no trade
```

---

## 1. `pulse-range` - KAOS Pulse (range mean reversion)

**Assets:** crypto, FX, equities, binary. **Timeframes:** 1m, 5m, 15m, 1h, 4h.
**Exit:** 3.0 ATR target, 5.0 ATR stop, 24-bar time exit.

Long when, on the close:

```
regime == range
and z <= -1.0                       # at least 1 ATR below EMA20
and RSI <= 42
and close < lower Bollinger(20, 2.0)
and z_slow > -2.0                   # not a knife: price not >2 ATR from EMA50
```

Short is the mirror: `z >= +1.0`, `RSI >= 58`, `close > upper band`, `z_slow < +2.0`.

```
stop   = entry - 5.0 * ATR
target = entry + 3.0 * ATR
exit at close of bar 24 if neither is touched
```

Why 3/5 rather than 1/1: in a range you are paid for being right about the reversion, not for
being right quickly. The wide stop is what produces the 68.6% hit rate. It is also why the
expectancy is only +0.010 ATR - the two effects cancel.

**Per-class out of sample:** FX 72.7% WR / +0.175 ATR (17 pairs), equities 64.6% / +0.041
(25 pairs), crypto 65.4% / -0.073 (20 pairs). Crypto is where the rule fails: the sample is a
trending market and mean reversion fights it.

---

## 2. `drive-trend` - KAOS Drive (trend pullback)

**Assets:** crypto, FX, equities. **Timeframes:** 15m, 1h, 4h.
**Exit:** 1.6 ATR target, 1.0 ATR stop, 24-bar time exit.

```
regime == trend up
and low <= EMA20 <= close          # bar dipped into the mean and closed back above
and close > open
and ER slope > 0                   # the trend is strengthening, not decaying
```

Short mirror: `high >= EMA20 >= close`, `close < open`, ER slope > 0, trend down.

**Status: no edge.** 554 trades, 40.0% WR vs 38.5% parity, -0.023 ATR after costs. It ships
disabled, exactly as it did in v1, because the rule is coherent but the market does not pay for
it on these timeframes. Keeping it costs nothing and stops anyone re-inventing it.

---

## 3. `orb-equity` - KAOS ORB (US opening range breakout)

**Assets:** US equities. **Timeframes:** 5m, 15m. **Session:** 09:30-16:00 New York.
**Exit:** 2.0 ATR target, 1.0 ATR stop, 24-bar time exit.

```
range  = high/low of the first 3 bars of the cash session   (15m on 5m, 45m on 15m)
window = bars 3..38 of the session                            (one attempt per direction)
long   if close > range_high and close_position_in_bar > 0.6
short  if close < range_low  and close_position_in_bar < 0.4
```

`close_position = (close - low) / (high - low)`. Requiring a strong close filters the wick that
pokes the range and immediately fails. Only the first long and the first short of each session
are taken - after that the range is stale.

**Status: best candidate.** 279 trades, 39.8% WR vs 33.3% parity (+6.5pp, z = 2.23),
+0.229 ATR per trade, PF 1.38, 9 of 12 pairs positive. It is also the only rule that survives
10x the assumed cost (+0.069 ATR at 0.10 ATR per side). It does not clear the placebo at
p <= 0.05 (p = 0.21), and 83 days of 5m data is 60 sessions per symbol, so treat it as
paper-trade-ready rather than funded-account-ready.

---

## 4. `fx-session-breakout` - KAOS FX Session (London open)

**Assets:** FX. **Timeframes:** 5m, 15m. **Session:** 07:00-16:00 UTC.
**Exit:** 2.0 ATR target, 1.0 ATR stop, 24-bar time exit.

```
range  = high/low of the first 4 session bars   (20 minutes on 5m)
window = session bars 4..44
long   if close > range_high and close_position > 0.55
short  if close < range_low  and close_position < 0.45
first breakout per session per direction only
```

**Status: no edge.** 258 trades, 34.9% vs 33.3% parity, -0.004 ATR. The London range break is
real in the literature but it is not in this data at this cost. Note the sample: 5m FX history
is 83 days, and Yahoo FX candles are indicative rather than ECN, so the spread assumption is
generous.

---

## 5. `crypto-ignition` - KAOS Ignition (volatility expansion)

**Assets:** crypto. **Timeframes:** 5m, 15m, 1h, 4h.
**Exit:** 3.0 ATR target, 1.5 ATR stop, 24-bar time exit.

```
long  if close > highest high of prior 20 bars
      and ATR(14) / ATR(14) 20 bars ago >= 1.15      # expansion
      and (close - open) / (high - low) > 0.5        # dominant body
      and close > open
      and ER >= 0.20                                 # not a one-bar freak in chop
```

Short is the mirror through the 20-bar low.

Crypto trends are volatility events, not valuation events: the entry is the bar where range
expands and the close finishes near the extreme. The ER floor removes the majority of breakouts
that occur inside chop.

**Status: second candidate.** 483 trades, 35.4% WR vs 33.3% parity (+2.0pp, z = 0.91),
+0.106 ATR, PF 1.11, 9 of 16 pairs positive, p = 0.33. Survives 0.05 ATR per side, dies at 0.10.

---

## 6. `binary-fade` - KAOS Binary (range fade, fixed expiry)

**Assets:** binary options (Pocket Option and similar). **Timeframes:** 1m, 5m.
**Exit:** fixed 3-bar expiry. No stop, no target - the settlement price is the only thing that
matters.

```
regime == range
long  if z <= -1.0 and RSI <= 40
short if z >= +1.0 and RSI >= 60
settle at the close of the 3rd bar after entry
```

**Status: loses money.** 2,387 bets, 48.1% wins. Break-even at an 80% payout is 55.6%; at the
best payout Pocket Option advertises (92%) it is 52.1%. Expected loss per unit staked:
-0.230 at 60%, -0.134 at 80%, -0.077 at 92%. Crypto is the leastbad (52.0% wins), FX the worst
(39.9%).

The structural problem is not the signal: a binary has negative expectancy unless your win rate
beats `1/(1+payout)`, which is 52-62% depending on the broker's cut, and the payoff is
deliberately asymmetric. **Do not run this rule on a binary account.** If a binary venue must be
used, the only defensible version is to take the Pulse bracket signal and accept that the
expiry cuts the trade off before the target.

---

## 7. `options-credit` - KAOS Options (defined-risk premium)

**Assets:** options on liquid ETFs/equities (SPY, QQQ, large caps). **Decision timeframe:** 1h
close, held as a daily-style decision. **Platform:** tastytrade.

```
range regime (ER <= 0.28) and realised vol below its own 60-day median
    -> sell an iron condor: 35 DTE, short strikes at 0.18 delta, $5 wings
trend regime and rising realised vol
    -> buy a debit spread in the trend direction: 35 DTE, long 0.50 delta, short 0.25 delta
manage at 50% of max credit/profit, stop at 2x credit received, close at 21 DTE
```

**Status: not measured.** There is no options chain in the public data set, so no P&L is
claimed and none should be inferred. The rule is complete enough to execute and to forward-test
on a paper account; it is not evidence of an edge. Calling it validated would be dishonest, and
selling it as such would be worse.

---

## Position sizing and risk

The rules emit direction and brackets, not size. Size from risk per trade, not from conviction:

```
units = (account_equity * risk_pct) / (stop_distance_in_price)
```

With the 5 ATR Pulse stop, a 1% risk budget and ATR = 0.7% of price, that is roughly 0.28x
notional per trade. The ORB 1 ATR stop allows a larger position for the same risk - which is
part of why its expectancy per ATR translates into a better return per unit of risk.

Cap concurrent risk rather than counting positions: 3% of equity at risk across all open trades,
and skip new entries in a pair that already has one (the harness enforces the same rule, so the
backtest and the live book agree).
