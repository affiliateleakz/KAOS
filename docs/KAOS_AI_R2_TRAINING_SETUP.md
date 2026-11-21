# KAOS Train AI — persistent R2 multi-market training (owner only)

## What the button actually trains

The **Train AI** control under **KAOS AI**, and **Train AI — All R2 Markets**
under **Backtests → KAOS R2 Research Lab**, queue a persistent research job.
The worker reads up to 5,000 completed, validated 1-minute R2 candles
for each of the 20 configured stock, ETF and crypto markets (from
`kaos_r2_market_audit.MARKETS`) and fits one independent chronological
OHLCV logistic research model per market.

Market history and derived candle features are the **only actual model
features**. The job reports source identity, training sample counts,
model validity, and data gaps. News/social/insider/short interest/options flow,
macros and observer features are visibly **not integrated**, not silently
assumed to have been trained. Forex/options/binary coverage is **not** yet
available in the configured training universe.

The button does not place paper or live orders and does not activate
the production KAOS AI inference engine.

## Install on existing cPanel (after PR merge and matching build)

The working KAOS Git checkout is `~/kaos-deploy-source`.
The existing Python Passenger app is at
`~/tradingwithkaos.com/backend`, with the cPanel virtualenv at
`~/virtualenv/tradingwithkaos.com/backend/3.11/bin/python`.
Review these paths before installing; do not paste credentials into chat.

1. From cPanel Terminal, verify the checkout is clean, then
   `git -C "$HOME/kaos-deploy-source" pull --ff-only origin main`.
2. Run
   `bash "$HOME/kaos-deploy-source/scripts/deploy-kaos-paper-api-cpanel.sh"`
   to install the new `kaos_ai_training_jobs.py` and route changes
   into the existing backend with backups and an API revision stamp.
3. Check `https://api.tradingwithkaos.com/api/health`.
4. Run
   `bash "$HOME/kaos-deploy-source/scripts/install-kaos-r2-train-cron-cpanel.sh"`.
   It checks for required R2/Mongo/owner settings, securely backs up the
   existing backend `.env`, adds
   `KAOS_R2_TRAIN_WORKER_ENABLED=1`, inserts ONE idempotent cPanel cron
   entry running `run-kaos-r2-training-worker-cpanel.sh` each minute,
   and requests a Passenger restart. Existing cron jobs are preserved.
   Inspect cPanel → Cron Jobs afterward to verify installation.
5. Deploy the matching compiled React member portal artifact using the
   *existing* revision-locked
   `deploy-isolated-kaos-portal-cpanel.sh` procedure. It must **not**
   overwrite the cinematic Viking homepage. Consult
   `docs/KAOS_PORTAL_PAPER_RELEASE_CANDIDATE.md`.

The **API** must be deployed before the website portal. Browser buttons
cannot run scheduled training until the cron is actually enabled on hosting.

## Verification

- Log into the KAOS owner account, open **KAOS AI**, click **Train AI**.
- The job should show **queued → running → completed** with per-market
  results. Each cron invocation processes at most two configured markets.
- Look at **Backtests → R2 Research Lab → KAOS AI Training Jobs** for
  source coverage and validation blockers.
- If the job is not advancing, inspect `~/kaos-r2-training-worker.log`
  locally. Do not send private keys, `.env` values or logs containing secrets.
- If R2 history is insufficient or not configured, the UI must show
  unavailable/insufficient history, not manufactured models.
- Research models must report chronological out-of-sample validation;
  strategy requirements remain at least 60% win rate and 12 signals/hour
  on qualifying untouched tests, not a promise of performance.

## Recoverability and isolation

The worker checkpoints every market in MongoDB and uses a lease to prevent
concurrent workers from modifying the same job. Expired leases are reclaimed
on future cron ticks. If archive reads or model fitting fail, the affected
market records an error and the job continues.

This worker does **not** auto-train on news/insider data because reliable
historical feature joins and source schemas are not connected yet. Do not
promote research results to order-execution authority without separate
model validation, source provenance review, out-of-sample trading tests,
broker fill verification and independent risk controls.

To pause future training, remove the marked cron entry
`KAOS_R2_RESEARCH_TRAINING_CRON_V1` and set
`KAOS_R2_TRAIN_WORKER_ENABLED=0` in backend `.env`, then restart
Passenger. This does not delete existing models or erase trading records.
