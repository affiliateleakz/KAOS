# KAOS Trading Bot 1.4.6

## Server / website authentication repair
1.4.x had removed the `cookies` permission, the `KAOS_IMPORT_WEB_SESSION` background route,
the Google website-session importer, and the public `setTokens` cloud method that importer needs.
Those pieces existed in the earlier working extension generation.

1.4.6 restores them. Startup and Retry now attempt to recover the authenticated
tradingwithkaos.com session before showing OFFLINE/LOGIN. The Google sign-in button is restored.

## Page repair
The existing functional Strategy Builder DOM is moved out of Charts into a dedicated
Strategy Builder host. It is not copied, so its existing controls/listeners/state are preserved.
Charts hides all Strategy Builder containers.

B32.24 trading logic, Pocket Option bridge, candle collection and Candidate 7B are unchanged.
