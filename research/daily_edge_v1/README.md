# Daily strategy search: historically positive, not a dependable edge

**Finding:** a fixed daily breakout/trailing-stop candidate made a small historical profit after modeled costs, including doubled costs. It **failed the final confidence gate**. The stronger absolute-return benchmark was holding the same stock-ETF basket, with much greater exposure and drawdown. No future profit is guaranteed and no live strategy was installed.

## What was searched

Eight fixed daily hypotheses were frozen in `plan.json` and `strategy.py`: SMA200 trend, EMA50/200 cross, Donchian55/20, Donchian20/10, 22-day Chandelier breakout, monthly 10-period SMA, RSI2 bull pullback, and quiet-regime range fade. There was no grid of tuned thresholds.

There were **24 class/candidate combinations** across:

- Stock ETFs: SPY, QQQ, IWM and DIA.
- Spot crypto: BTC-USD and ETH-USD; no short funding/borrow assumed.
- Forex: EURUSD, GBPUSD, USDJPY and AUDUSD indicative quote pairs, tested both ways.

Daily quote history begins in 2006 for established instruments, 2014 for BTC and 2017 for ETH. In-window split events were disallowed; starting in 2006 excludes the earlier IWM split. These are fixed liquid instruments, not a survivorship-free historical universe. Source snapshots contain raw OHLC, reported gross cash dividends and hashes. FX prices are indicative, not executable quotes from a chosen broker.

**Validation/selection:** 2018–2020. Require at least 40 completed trades, positive net return at both base and doubled costs, and daily drawdown no more than 15%. Rank eligible class/candidate pairs by return divided by the larger of drawdown or 2%. Four combinations qualified; one choice was written before final evaluation.

**Reserved historical final:** 2021–2024, outside the 2025–2026 hourly data used for the earlier All-in-one test. This is a newly reserved historical test, not a prospective live experiment. No parameter changes or alternative candidate selection followed the final result.

## Selected rules: daily breakout with Chandelier exit

The chosen combination was `stocks / chandelier22_3atr`:

1. Long only. Completed daily close must be above SMA200 and above the previous 20 sessions’ highest high.
2. Enter at the next observed daily open; position risk uses prior completed ATR14.
3. Initial stop: three ATR below the actual entry fill. No fixed profit target.
4. After each completed bar, raise the next bar’s stop to the greater of its existing stop and the highest close over 22 sessions minus three ATR. Never apply a newly calculated trailing stop retroactively to that same candle’s low.
5. Also schedule an exit at the next open if the completed close loses the prior 10-session low or falls below SMA200. Gap stops use the worse observed open. No immediate same-bar reversal/reentry.
6. Risk 0.5% of the instrument sleeve’s realized equity; at most 1x gross notional at entry. Each instrument starts in a separate $10,000 sleeve. Fractional quantities are allowed; no leveraged or shared pooled account is assumed. Cash is not reallocated among sleeves and earns zero interest.

Modeling assumptions: stocks 1 bp adverse fill each side, zero commission and explicit gross cash dividends. Crypto 2 bp adverse fill plus 10 bp commission each side. Forex 0.5 bp adverse fill each side plus an assumed 2 bp/calendar-day holding cost; USDJPY P&L is converted to USD at exit. The stress test doubles these costs; zero stock commission remains zero. Nonzero brokerage commissions, particularly on small positions or historical accounts, can materially reduce or erase the small active profit. Taxes, real broker swap schedules, borrow, order rejection and liquidity are not modeled.

Daily OHLC stops use an approximate end-of-day timestamp when the exact intraday hit time is unknown. FX carry on intraday stopped positions can therefore be conservatively overstated. Final open positions are liquidated at the last actual close. Cash accounting reconciles to every closed trade, including modeled costs and dividends.

## Results

Validation return was **+1.97%**, with 63 trades. That was the selection information, not the final result.

| 2021–2024 result | Net return | Max daily drawdown | Trades |
|---|---:|---:|---:|
| Selected active candidate | +1.21% | 1.39% | 83 |
| Same candidate, doubled costs | +1.15% | 1.42% | 83 |
| Same ETFs, 1x initial buy-and-hold | +48.03% | 26.23% | 4 |
| Assumed idle cash, zero yield | 0.00% | 0.00% | 0 |

The active candidate’s net winning-trade rate was 39.76%, with profit factor 1.475. Its profit of about $483.07 on $40,000 represents only about 0.30% annually over four years under the assumptions. These figures are not a meaningful promised income stream.

**Exposure matters:** the active candidate averaged approximately 4.9% notional exposure on observed quote days; buy-and-hold averaged 97.8%. The return/drawdown comparison is not a claim of superior risk-adjusted performance or alpha. Cash yields on the uninvested portion were set to zero; no claim is made that the candidate beats Treasury bills, savings rates or an exposure-matched passive allocation.

The selected final weekly-block bootstrap interval spans roughly **-1.66% to +4.23%**. It crosses zero, so the preregistered confidence gate fails. The four ETFs are highly correlated. There are only four final years, historical quotes can be revised, and no strategy/broker has been forward-verified.

Per-ETF final results:

| ETF | Trades | Net return | Profit factor |
|---|---:|---:|---:|
| SPY | 22 | +2.87% | 2.362 |
| QQQ | 20 | +2.24% | 1.950 |
| IWM | 19 | -1.45% | 0.461 |
| DIA | 22 | +1.17% | 1.390 |

IWM lost money; it was not removed after the fact. Crypto candidates had some positive validation returns but failed the frozen eligibility requirements; none was subsequently promoted using final-period performance. No forex candidate qualified. The full 24-combination table is preserved, including losers.

## Conclusion and next action

The search found a **historically positive but economically weak active candidate**, not an established profitable trading bot. Buy-and-hold produced a much larger historical gain but also a roughly 26% daily drawdown and greater market exposure. That benchmark gain is not a guarantee of future stock returns or a result applicable to Pocket Option, forex, crypto or binary options.

Keep the candidate in research/paper testing. Do not tune it again on 2021–2024 and call the result fresh validation. A new strategy revision needs new reserved data and realistic forward fills. No production site, extension selector, trading permission or payment configuration changed in this experiment.

## Reproduce

The research ZIP includes normalized public snapshots, frozen rules, all validation results, the selected final ledger and manifests. It includes no personal account information or API key.

```bash
python scripts/collect_daily_edge_history.py --out data/daily_edge_v1 --cache /private/kaos-daily-source
python scripts/research_daily_edge.py --data data/daily_edge_v1 --out audit/reproduced-daily-edge
python -m pytest apps/api/test_daily_edge_research.py -q
```

Use the packaged normalized snapshots to reproduce the exact sample, since providers can revise data. `audit/provenance.json` records plan, rule, runner and input-manifest hashes. Validation selection is in `audit/selection.json`; the confidence failure is recorded in `audit/result.json`. Tests cover daily/monthly causality, next-open execution, gap stops, cash ledger reconciliation, passive benchmark accounting and trailing-stop timing.
