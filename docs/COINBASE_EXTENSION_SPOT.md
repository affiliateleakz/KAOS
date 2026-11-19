# Coinbase extension-run spot trading — 1.7.38

This release supersedes the dedicated-worker requirement **for new extension
sessions only**. Pocket Option's execution path is retained. AI training is
independent and is not started by this integration.

## What runs where

The KAOS app window fetches Coinbase public one-minute candles/tickers, evaluates
KAOS Spot Trend v1, and decides entries/exits. Its authenticated background relay
sends orders to KAOS. The backend retains encrypted CDP credentials and enforces
membership, consent, selected markets, exact amounts, exposure reservations,
no-short exits, stable order identities and exchange fill reconciliation.
No broker private key is returned to the extension. No Coinbase worker process
is needed for new extension sessions; the legacy worker ignores those sessions.

Keep the KAOS window open. Closing/reloading it stops extension decisions and
software exits. Reopening does not silently restart orders: Resume explicitly
arms the existing extension session with its saved settings. Browser suspension,
network failures and throttling can delay decisions even while the window is open.

## Controls and behavior

- Choose one distinct USD market per membership-limited market slot, up to four.
- Existing Trade Amount is USD per entry; the cap remains amount × market slots.
- Expiration is hidden for Coinbase. Martingale/Compounding must be off.
- Spot-specific editable defaults: stop loss 2%, take profit 4%, maximum entry
  spread 0.3%. These percentages are visible and confirmed before Start.
- Start creates an extension session with up to 12 hours of entry consent.
- Stop blocks new entries, while the armed open window continues exits.
- **Stop entries & close KAOS positions** explicitly requests market sells of
  verified KAOS holdings. It never adopts or sells unrelated Coinbase holdings.
- Pending/uncertain orders block further orders until reconciled. Deterministic
  identities prevent retrying a lost response as a new trade. Partial fills and
  inconsistent broker outcomes remain review states.
- Price exits continue with fresh quotes when candle history has a gap; missing
  candle history pauses entries. Missing quotes pause all decisions.
- Session P/L uses verified fill costs/fees and fresh bids. It excludes future
  exit fees/slippage until those fills arrive; it is an estimate, not a balance.
- These are **software exits, not exchange-native protective orders**. No stop
  remains running after browser closure. Software loss thresholds are not a
  guaranteed maximum loss.

## Strategy status

KAOS Spot Trend v1 is a distinct deterministic spot candidate, not binary SR1.1:
closed one-minute candles, EMA20 above EMA50 and a breakout above the previous
20-bar highs for entry; close below EMA20, explicit stop/take-profit, session risk
halt or explicit Close for exit. At least 60 genuine contiguous closed bars are
required. Quotes older than 15 seconds and stale candle histories are rejected.
The entry spread threshold is a liquidity filter, not a complete fee/profit model.
This candidate has **not been established profitable or live-validated**. Native
protective orders, confirm-each-entry mode and strategy performance evaluation
remain separate work; they are not advertised as implemented here.

## Install

Install matching extension 1.7.38 and the backend from this revision. Rebuild the
cPanel packages and activate the matching release, then run the cPanel virtualenv
Python with `scripts/cpanel_billing_runtime.py --enable-stripe --enable-trading`
and restart the Python application. Preserve the existing broker vault key.
Connect a Coinbase CDP account with View+Trade and Transfer disabled. No orders
are submitted by installation, connection, opening KAOS or loading markets.

Resolve legacy server-run sessions before starting a new extension session. Stop
the old worker after reconciling its holdings; it is not converted automatically.
New code is a development candidate: syntax/package checks do not demonstrate
live account execution. No real orders were sent during development. Automated
regression source is included; no new test suite was executed per the owner's
previous instruction.
