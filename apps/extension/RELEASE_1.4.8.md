# KAOS Trading Bot 1.4.8

## Build Strategy — structural fix
The actual `<div id="strategy-builder">` was the element still visible inside
`#terminal-live`. Earlier builds searched for the wrong wrapper classes.

1.4.8 removes that exact DOM block from `screen-chart` at build time and places it
inside a dedicated `kaos-build-strategy-page` under `screen-main`. This is no longer
a runtime CSS/mutation workaround.

The separate `terminal-strategies` catalog page is also removed from Charts.

## Charts — loading fix
The new sidebar's `route('charts')` bypassed the original `terminalShow()` function.
It switched screens but did not start the one-second `terminalRefresh` loop.

1.4.8 starts `terminalRefresh()` immediately and starts/restarts its timer whenever a
Charts/AI/Performance terminal route is entered. The timer is stopped when leaving
terminal pages.

Cloud/auth remains the 1.2.0 implementation restored in 1.4.7.
B32.24 trading/execution logic is unchanged.
