# Pocket Option edge research — supplied October 8 export

**Finding: no validated edge. No candidate was promoted and no live bot, hosting, payment or trading setting was changed.**

## Data and integrity

The supplied ZIP (`KAOS_ALL_DATA_2026-10-08T18-42-12.zip`) hashes to `b47526f23972c2f80312ce1ac2020798fc359b92fe3dfb7e4123f6e199131957`. The original export is kept outside Git because it also contains member settings and trade details. Only aggregate research results are committed.

There are **145,341 five-second OHLC bars across 30 markets**, separated by **135 gaps into 165 segments**. The export contains activity on September 27–28 and October 3–6/8, not uninterrupted coverage. After 300-bar segment-local warmup, 119,689 feature rows are usable. The small October 8 segments do not meet warmup. No missing bars are filled, no trade settles across a gap, and trades do not overlap within an asset.

The first inspection found an empty top-level trade list. A later inspection found **1,000 records inside `popupData.tradeRecords`**: 480 reported wins, 510 losses and 10 draws (48.48% of decided trades). Of these, 789 carry the export's broker-confirmation flag, which has not been independently verified. **506 outcomes disagree with stored entry/exit prices and direction**, including 415 flagged records. Account real/demo mode is missing. These inconsistent labels were excluded from model fitting. This finding does not establish whether the broker result or local snapshot is wrong; reconciliation needs actual broker order/settlement data.

Most candle `closeTs` values are the last observed tick (`ts+4000`) or the start itself rather than the bucket end. Research therefore treats the OHLC as completed only at the next contiguous bucket boundary, enters at that next open, and uses a later observed open as a settlement proxy. This is an assumption about the export's stated closed-candle source, not tick-level execution verification. Literal timestamps and reconstructed bucket completion are separately audited for the signature baseline.

## Frozen experiment

`plan.json` was written before running strategy selection. There are **36 candidates**: 27 fixed momentum, pullback, breakout, range-rejection and streak-fade rules, plus three fixed small XGBoost fits at three confidence thresholds. XGBoost learns only from the first 60% of distinct global feature timestamps. Labels crossing the development boundary are purged. Features use closed bars and no reported trade labels. The next 20% is validation; the last 20% is reserved for a single qualifying candidate. No parameter search or final-period fishing followed the failed validation.

Global clock-time boundaries (UTC):

- Development starts September 27, 2026, 02:22:40.
- Validation: October 5, 07:23:55 through 18:10:50.
- Reserved final period: October 5, 18:10:50 through October 6, 04:57:40.

These are timestamp-quantile splits, not calendar-day splits. The validation period has only one UTC day; the predefined minimum is three days plus 200 decided trades and positive expected return at an assumed 80% payout. **No candidate passed; the final candle replay was not evaluated.** Counts of historical exported trade records above are a separate integrity audit, not final-period candidate selection.

## Results

| Validation result | Wins / losses | Win rate | P&L at assumed 80% payout, one unit per trade |
|---|---:|---:|---:|
| Strongest rule: fade five same-color candles, 15-second expiry | 402 / 343 | 53.96% | -21.4 units |
| Current SR1.1 signature, reconstructed bucket completion | 185 / 182 | 50.41% | -34.0 units |

Signature SR1.1 had 7 additional ties. With literal exported close markers it produced zero trades, so those markers cannot be treated as conventional bucket-end timestamps. The accelerated baseline was checked at 18 windows, including actual signals, against the unchanged extension engine.

At 80% payout, break-even is **55.56%**. The strongest rule's Wilson 95% lower bound is **50.37%**, and its validation multiple-comparison-adjusted significance test does not pass. At 90% assumed payout the same rule shows +18.8 units, but the lower bound is below the 52.63% break-even rate. That is not reliable evidence of an edge. Payouts, slippage, entry delays, rejected orders and broker-side settlements are not modeled by these candle proxies. A delay stress test was not run because no candidate reached the validation gate; no execution-quality claim is made.

The full validation table, per-market summaries and payoff sensitivity are in `audit/validation.json`. `audit/result.json` records `no_validation_candidate`; `audit/selection.json` records no selection. There is no deployable trained model from this run.

## Reproduce

Install API scientific dependencies, then use the original ZIP privately:

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 python scripts/research_broker_edge.py /private/KAOS_ALL_DATA_2026-10-08T18-42-12.zip --out research/pocket_option_20261008/audit --baseline-input /tmp/kaos-baseline-candles.json
node scripts/research_signature_baseline.cjs /tmp/kaos-baseline-candles.json > research/pocket_option_20261008/audit/signature_baseline.json
python -m pytest apps/api/test_broker_edge_research.py -q
```

The runner records input/plan/code hashes. Baseline input includes only market candles and is not committed. Tests protect causal features, segment warmup, exact settlement, non-overlap, boundary purging and rejection of conflicting data. This research does not change the production strategy.

## What would justify another experiment

Reconcile broker-confirmed order IDs with actual direction, entry, expiration, settlement, real/demo mode and payout; preserve those fields at entry/settlement. Collect several weeks of continuous broker history across distinct days and assets. Freeze the next experiment before inspecting new outcomes. A strategy must first clear payout-aware validation, then an untouched chronological test, and then a prospective demo period. More tuning against this failed validation window would not create independent evidence.
