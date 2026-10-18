# KAOS Trading Bot 1.5.1

## Charts
The chart renderer itself was intact. The reconnect path was not.

When an unpacked extension is updated while Pocket Option is already open, the old page can
retain `window.__poatBridge440` and `window.__poatContent137`. The previous self-heal simply
re-injected the JS files; both files immediately returned at those stale guards, so
GET_TERMINAL_SNAPSHOT never recovered until the Pocket Option tab was manually refreshed.

1.5.1 clears the stale MAIN-world bridge guard and isolated content guard, re-injects
`po-bridge.js` in MAIN world, then re-injects Candidate 7B + content.js. This recovery is
triggered immediately when Charts opens and is also retained as the empty-snapshot self-heal.

## Sidebar
Removed the stretched/cropped promotional artwork below View Mode and replaced it with a
compact contained KAOS brand card. No hero image is forced into the narrow sidebar.

B32.24 strategy/execution logic is unchanged.
