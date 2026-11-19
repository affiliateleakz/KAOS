# KAOS longer-horizon research

This experiment follows the failed short-term spot/binary tests. It changes the economic structure: fewer entries, larger intended moves, trailing exits, and a separate weekly allocation strategy. It does not change fees to make prior losing rules appear profitable. **Research only: no website, extension, broker connection, real orders, or live permissions are changed.**

The plan was committed as `6ad4ff4` before evaluation. Twelve configurations were specified: eight hourly/four-hour swing configurations and four weekly momentum portfolios. Nothing is selected from confirmation after a validation failure.

## Data and boundaries

Checksum-verified public Binance spot hourly archives cover 2021–2025 for BTC, ETH, SOL, BNB, XRP, and ADA against USDT. There are 360 monthly archives and 43,808 observed hourly candles per pair. Missing exchange hours remain missing; candle/indicator history resets after gaps, and incomplete UTC aggregates are excluded.

2021–2022 supply historical context. Validation is 2023–2024. At most one configuration from each track advances to confirmation on the new BNB/XRP/ADA hourly series during 2025. The fixed universe is composed of surviving liquid crypto assets and is not survivorship-free. These assets share market regimes with previously studied BTC/ETH/SOL and daily histories. Several hundred hypotheses have already been explored across earlier studies; the within-round correction does not erase that accumulated research-selection bias. These are retrospective checks, never prospective proof.

The still-reserved September–October 2026 series and the reserved Pocket Option period remain unscored in this experiment. Confirmation is evaluated only after a selection file is written. Both 2023 and 2024 are broadly favorable crypto years, so a validation gain does not establish bear-market robustness.

## Swing rules and execution

A closed-bar trend breakout or EMA20 pullback/reclaim uses the prior experiment's causal EMA20/50/200 and Wilder ATR14 calculations. Two candle durations (one/four hours) and two initial stops (three/four ATR) produce eight configurations. There is no fixed profit target.

- Warm up on 250 continuous requested-timeframe candles. Enter at the next observed hourly open.
- Require initial stop distance at least 1% of the observed entry price. This fixed fee-budget filter was declared before replay.
- After each requested candle closes, raise the next hour's stop to the greater of the old stop and the highest close over twenty candles minus the chosen ATR multiple. Never apply a newly raised stop to the low of the same candle.
- A close below EMA50 or the preceding ten-candle low schedules an exit at the next observed hourly open. The already-active stop retains priority if the open gaps below it.
- Hold at most seven days. No overlapping positions or same-hour re-entry within an asset. Require the full holding horizon to fit within one continuous source segment and evaluation split.
- Stop gaps fill at the worse observed open. Stop fills within an hour are OHLC approximations; exact tick order and broker execution are not known.

Base cost is 10 bps fee plus 2 bps adverse slippage **per side**. Combined stress doubles both costs and delays entry by an hour. The actual fee tier, spread, fill quality, liquidity and broker availability can differ materially.

Swing P&L is expressed in original risk units (R), independently sized per trade. Summed R is **not** a return on a shared account, compounded profit, or a percentage/dollar gain. Fees can make a stopped trade lose more than one R. Always-long and EMA200 trend-long baselines use identical cost, fee-budget, stop, trailing, holding and position rules. Trade expectancy comparisons do not establish equal portfolio exposure or an executable income stream.

Validation needs 150 trades, 90 active UTC days, profit factor at least 1.15, four profitable markets, positive adjusted weekly-cluster lower bound, positive combined stress, and mean R per trade above both matched baselines. Confirmation requires 60 trades, 40 active days, profit factor at least 1.10, two profitable new markets, positive weekly lower bound, positive stress and both baseline comparisons. See the frozen plan for exact gates.

## Weekly momentum allocation

Four portfolios combine 20/60-day lookbacks with the strongest one/two eligible assets. Decisions occur at Monday 00:00 UTC using only completed Sunday daily candles. An eligible asset has a positive lookback return and price above EMA200, after 250 complete daily bars. Each slot receives at most 1/N of equity; unfilled slots stay in cash. There are no leverage, shorts, borrow or price stops.

The cash-and-fractional-quantity ledger pays costs on every buy and sell. Targets use pre-cost equity; buys are scaled to available cash after sells and all costs, so the simulation cannot spend nonexistent funds. Holdings are marked at observed hourly closes and flattened at the split's final observed close with exit costs. Validation positions do not carry into confirmation.

At a source discontinuity, the fallback liquidates at the **first later observed open**, including any adverse gap and transaction cost. It never claims an exit at a price observed before an unexpected gap. The next regular weekly rebalance can establish holdings again. Unobserved intragap drawdowns cannot be measured.

The matched benchmark uses equal weights over the same fixed universe and exactly the strategy's target gross exposure at each weekly rebalance, with the same costs/delay. Realized exposure can diverge between rebalances as asset prices move. A fully invested weekly equal-weight basket is also reported. Base costs are 12 bps per traded dollar on each buy or sell; stress is 24 bps plus a one-hour rebalance delay. Idle cash earns zero. Returns are USDT-denominated; interpreting them as dollars assumes a stable USDT/USD parity and ignores exchange/counterparty risks.

Selection requires a positive net return in each validation year, at least 52 weekly observations, maximum observed hourly-close drawdown no more than 25%, positive combined stress, a higher net return than the exposure-matched basket, and a positive adjusted four-week moving-block bootstrap lower bound on mean weekly excess return. Confirmation requires 40 weeks, positive return/stress/excess, drawdown no more than 25% and positive 95% lower excess-return bound. Boundary weeks may be partial. Maximum hourly-close drawdown understates unobserved intrahour extremes.

Both bootstrap procedures use 5,000 samples and seed 619. Validation lower quantile is 0.05/12; confirmation uses 0.025. Blocks and correlated assets cannot supply independent future evidence. Positive results would justify prospective paper testing only.

## Reproduce and inspect

```bash
python scripts/collect_swing_history.py --out /private/hourly --cache /private/hourly-cache
python scripts/research_kaos_swing.py --data /private/hourly
python -m pytest -q scripts/tests/test_kaos_swing_research.py
```

Python requires numpy, pandas, scipy, and httpx. Raw downloaded arrays and archives remain outside Git. `provenance.json` identifies archives and local arrays with hashes and records the plan/engine/runner versions. Each track has complete validation results, a pre-confirmation selection file, and confirmation status. Selected final trades/equity paths are saved only if a candidate advances. `strategy.py` exposes no broker/order API; all trade records are research records.

## Results

Swing selection: **none**, confirmation evaluated: **False**, confirmation gate passed: **False**.

| Candle | Rule | Stop ATR | Trades | Net R | PF | Stress net R | Adjusted lower week mean R | Mean R/trade | Always-long mean R | Trend-long mean R | Eligible |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1h | breakout20 | 3 | 937 | 22.21 | 1.057 | -82.64 | -1.200 | 0.024 | -0.092 | -0.072 | False |
| 1h | breakout20 | 4 | 908 | 17.70 | 1.058 | -54.84 | -0.987 | 0.019 | -0.071 | -0.052 | False |
| 1h | pullback20 | 3 | 2371 | -69.69 | 0.892 | -312.53 | -2.483 | -0.029 | -0.092 | -0.072 | False |
| 1h | pullback20 | 4 | 2217 | -38.34 | 0.920 | -203.59 | -1.837 | -0.017 | -0.071 | -0.052 | False |
| 4h | breakout20 | 3 | 249 | 67.20 | 1.708 | 54.68 | -0.394 | 0.270 | -0.025 | 0.013 | False |
| 4h | breakout20 | 4 | 240 | 59.56 | 1.840 | 48.15 | -0.335 | 0.248 | -0.017 | 0.013 | False |
| 4h | pullback20 | 3 | 567 | 26.76 | 1.219 | -2.21 | -0.672 | 0.047 | -0.025 | 0.013 | False |
| 4h | pullback20 | 4 | 539 | 24.78 | 1.278 | 3.88 | -0.435 | 0.046 | -0.017 | 0.013 | False |

### Weekly momentum portfolios

Selection: **none**, confirmation evaluated: **False**, confirmation gate passed: **False**.

| Lookback | Slots | Validation return | Drawdown | Matched return | Fully invested return | Stress return | Adjusted lower weekly excess | Eligible |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| 20d | 1 | 120.82% | 49.54% | 117.33% | 532.28% | 89.27% | -1.037% | False |
| 20d | 2 | 212.20% | 44.13% | 102.45% | 532.28% | 179.79% | -0.491% | False |
| 60d | 1 | 284.62% | 48.95% | 133.68% | 532.28% | 215.74% | -0.468% | False |
| 60d | 2 | 163.58% | 57.65% | 103.75% | 532.28% | 136.36% | -0.585% | False |

Positive historical P&L is distinct from passing the full gate. No failed candidate is promoted using a different profitable metric. Passing verification tests confirms implementation invariants, not predictive accuracy or future profits.

## Additional older-regime robustness check

After observing a positive but unqualified four-hour breakout family in 2023–2024, a second plan (`backfill_plan.json`, committed as `53ac1d2`) froze **two unchanged configurations** on 2019–2022. This is an adaptive follow-up chosen using the first study, not a newly independent research hypothesis. No stop, indicator, fee or entry/exit rule was tuned.

2018–2020 hourly archives add past context. **38 unavailable archives** are recorded rather than invented, including periods before listings. **129 malformed/non-aligned hourly bars** are explicitly excluded and recorded in source metadata; their timestamps are not rounded. Gaps reset indicators and prevent crossing swing trades. The source collector now has offline checks for unavailable archives, rejected alignment and wrong checksums.

The follow-up gate requires at least 300 trades and 150 active dates, the unchanged original swing validation conditions, and a lower weekly-bootstrap mean above zero with a 14-way correction (12 original configurations plus 2 follow-ups). At most one setting could advance to the still-unscored 2025 BNB/XRP/ADA confirmation. No further backfill, parameter change or alternate selection follows these results in this round.

| 2019–2022 configuration | Trades | Active dates | Net R | PF | Combined-stress net R | Adjusted lower weekly mean R | Eligible |
|---|---:|---:|---:|---:|---:|---:|---|
| 14400:breakout20:3 | 162 | 114 | 31.64 | 1.569 | 25.37 | -0.247 | False |
| 14400:breakout20:4 | 157 | 111 | 22.58 | 1.499 | 18.80 | -0.232 | False |

Follow-up selection: **none**. Confirmation evaluated: **False**. Confirmation gate passed: **False**.

The four-hour breakout family made historical net gains in both evaluated periods and survived combined cost/entry-delay stress at both stop settings. That is a useful research finding, not a qualified live edge. The older sample is too small for the fixed gate and both settings have negative adjusted confidence bounds. Do not pool the periods post hoc, relax thresholds, or substitute the large portfolio returns to declare success. `backfill/paper_candidate.json` explicitly records the qualification status and disables execution.

Raw source arrays remain private workspace artifacts. Reproduce with:

```bash
python scripts/collect_swing_history.py --start-year 2018 --end-year 2020 --out /private/older-hourly --cache /private/hourly-cache
python scripts/research_swing_backfill.py --data /private/older-hourly /private/hourly
```
