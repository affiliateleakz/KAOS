# Extension usability improvements

## First pass: 1.7.23

The compact companion now uses a command center heading, a prominent current market,
selected navigation tabs and visible keyboard focus. Guidance changes with broker
availability, account type and the local bot control state.

Authorization alone is no longer displayed as proof that the broker is connected.
A successful minimal status response is required, and becomes unconfirmed after
15 seconds without a fresh response. A failed check clears the displayed market
and account type. This is a presentation state, not a stop command: a broker-side
bot may still be running. Stop remains available according to the existing local
control state. No strategy rules, order placement or membership gates changed.

Browser fixtures cover connection failure, recovery, stale status, navigation,
account labeling and Stop. These fixtures do not connect to a broker or place orders.

## Recommended next passes

1. Publish structured engine reasons in the minimal status response: waiting for
   real candles, risk limit reached, strategy conditions absent, or broker unavailable.
   Show actual engine reasons rather than inferring them from a connected status.
2. Group configuration into Strategy, Stake and Risk. Show the effective settings
   together before an explicit Start; distinguish saved settings from a running session.
3. Make trade history explain the setup, expiry and result using captured decision
   evidence. Separate observations and research scores from execution authority.
4. Evaluate strategy changes, including the uploaded AlphaBot trend-alignment rules,
   against the same recorded data, transaction assumptions and held-out periods.
   Compare drawdown, loss streaks and trade frequency as well as win rate before
   deciding whether to adopt a change.

The website remains a separate scope decision. Hosting installation, real broker
verification and trading performance are not established by these fixture tests.

### 1.7.29 — broker chart count on the Bot menu

The compact Bot tab exposes the existing 1–4 chart selector in the gold theme.
Only the server-provided chart allowance enables options; unknown plans default
to one chart. Selection persists and applies to the next explicit Start, whose
payload now sets multi-market mode from the selected companion count. The broker
scanner also caps its visible-market list to both that count and the plan limit.
This never starts the bot on selection or expands membership permissions.

“Show Pocket Option” focuses the broker tab instead of opening KAOS chart
canvases. The lightweight companion status includes only visible market names
for per-slot strategy binding, not candle arrays. Charts remain on the broker.
