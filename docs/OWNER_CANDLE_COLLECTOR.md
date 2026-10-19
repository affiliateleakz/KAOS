# KAOS Owner-Only Candle Collection Bot

Research-only archival service; **no live order submission, no automatic model training**.

## Who can access it
Set `KAOS_CANDLE_OWNER_USER_ID` to the **exact KAOS account user ID** for the owner. Do not use email or username as an access shortcut. The authenticated account must also have `admin` or `super_admin` role. Missing configuration denies everyone; other admins are denied. No collector endpoint is exposed to ordinary members.

Private endpoints:
- `GET /api/v1/owner/candles/status`
- `GET /api/v1/owner/candles/export?symbol=BTC-USD&seconds=60&limit=1000`

## What the worker does
Start a **separate long-running process** next to the API using the same MongoDB configuration:
```
export KAOS_CANDLE_OWNER_USER_ID="<exact owner KAOS user id>"
export KAOS_ENABLE_CANDLE_WORKER=true
cd apps/api
python candle_research_worker.py
```
It polls public Coinbase Exchange OHLCV each 60 seconds for BTC-USD, ETH-USD, and SOL-USD at 60-, 300- and 900-second granularities. Bars are stored only after they close, in `kaos_research_candles`. Compound key `symbol, seconds, ts` is unique, preventing duplication through repeated polling or restart. The process maintains last poll time and errors.

**The worker does not run automatically because code is merged.** Deployment must configure a supervised worker with restart policy and monitoring. Source availability, API quotas, changing terms, and process outages affect completeness. Coinbase candles represent Coinbase spot prices, not Pocket Option OTC prices, option premiums, or other brokers.

Training pipeline should later sample this dataset, explicitly label outcomes, preserve training/test chronology, and prohibit cross-market leakage. Market data without labeled outcomes is not itself trained AI. Check data-provider terms before redistributing or commercializing archived data.
