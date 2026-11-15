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
