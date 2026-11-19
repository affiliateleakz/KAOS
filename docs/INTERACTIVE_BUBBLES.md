# Interactive KAOS market bubbles

Reference reviewed: https://cryptobubbles.net/ (floating, draggable bubbles,
period-based performance, sizing modes, coin search and coin details). The KAOS
implementation uses its existing feeds and original SVG/physics code; it does
not embed or depend on that site's application, assets or market data.

## Behavior

- Up to 100 coins; performance, market-cap or 24-hour-volume sizing.
- Performance sizing uses absolute returns, so both large gainers and losers grow.
- Green/red bubbles show the selected period's reported gain/loss. Zero and
  unavailable returns are neutral; missing values are not converted to zero.
- 1h, 24h, 7d, 30d and 1y periods. Controls are disabled if no returned coin has
  data for that period. Coinbase's fallback only supplies 24h returns.
- Drag to move a bubble. Click or Enter/Space opens persistent asset details;
  source links open only after an explicit link click. Escape closes details.
- Search, top-coin range and a local browser watchlist filter the fetched snapshot.
  The watchlist survives reloads where local storage is available.
- Pause/resume motion. Reduced-motion preference starts paused and preference
  changes stop motion. Hidden/offscreen maps stop their animation loop.
- The shared renderer also supplies these interactions to the stock bubble map.

Bubble radii have minimum and maximum display sizes for readability and fit;
they are a visual comparison rather than an exact area ratio across all coins.
The plot has deterministic initialization, collision handling, bounded movement,
pointer capture and responsive SVG coordinates. It runs at at most about 30 fps,
updates positions directly instead of rendering the React tree each frame, and
has no server animation loop.

## Hosting and data

Changing timeframe, sizing, range, search or watchlist makes no new market API
request. There is no new automatic polling. Refresh uses the existing per-worker
90-second backend snapshot cache and ten-minute stale fallback. Month/year
returns are requested in the same CoinGecko market request. Provider availability,
rate limits and per-worker cold caches still affect loading. Snapshot timestamps
and stale-state text are displayed; this is not a tick-by-tick price feed.

No database migration, broker order, membership-policy or homepage change is
part of this work. No new JavaScript dependency was added.

## Validation

Pure simulation tests cover 100-coin bounds on mobile/desktop, deterministic
missing/zero-metric handling, equal-magnitude gain/loss sizing and drag collisions.
API tests cover longer return periods and preserving an actual zero return.
Browser fixtures cover drift/pause, dragging without opening a tab, keyboard
selection, sizing, periods, persistent watchlist, search/range, reduced motion,
provider fallbacks, mobile width and no extra API calls from local controls.
Fixtures do not prove live provider uptime or deploy files onto hosting.
