# KAOS Trading Bot 1.4.5

## Page cleanup
- Removes the redundant Trading menu item.
- Dashboard remains the simple trading/start page.
- Strategy Builder has its own page.
- Charts, KAOS AI and Performance remain mutually-exclusive full pages.
- Trade History now routes to its own page.
- Risk Manager now routes to its own page.
- Settings remains its own page.
- Adds authoritative layout rules to stop old B32 sections from visually overlapping new pages.

## Cloud repair
Earlier fallback experiments could persist `https://tradingwithkaos.com` in `kaos_api_host`.
The real extension client defaults to `https://api.tradingwithkaos.com`.
1.4.5 performs a one-time migration back to the API subdomain without deleting login tokens,
user data, trading data, or Pocket Option state.

## Preserved
B32.24 execution, candle collection, Pocket Option bridge and strategy logic are unchanged.
