# Restore the gold website and research tools

Source: `restore-gold-brand-palette`, revision
`5a2bb75f9e22d0b9433699456f9f97dfc4a3afd1`.
The development deployment previously omitted that branch's changes.

This correction recovers its homepage source, gold/brown branding, stock and
crypto bubble maps, keyless market-data fallbacks, member news discovery and
filing fixes. Later member-shell CSS is reconciled to gold/brown so it cannot
reinstate blue backgrounds. Login, membership selection, commerce setup and
extension fixes on the development branch remain in place.

This is a targeted recovery of the website and research tools. It does not copy
the other branch's alternate Google login or credential-management implementation;
those overlap later development code and require separate reconciliation.

The cPanel backend package includes the two standalone news helper modules.
The activation wrapper allows the authenticated, entitled member news-refresh
endpoint; it does not enable arbitrary ingestion, payments or order endpoints.
No collector scheduler or background trading service is started.

Validation covers the API suite, release packaging and activation, real compiled
website routes with mocked accounts/feeds, the recovered homepage, gold theme,
bubble rendering, and mobile width. Live provider availability and the owner's
original hosting files are not established by these tests.

No hosting changes are made by committing this correction. Review the recovered
website before a further installation; do not repeat the previous deployment
command simply to inspect it.

## Owner-confirmed homepage reference

The owner subsequently confirmed the homepage in
`tradingwithkaos.com_2.2.0_EXACT_TARGET_COMPLETE_WEBSITE.zip` as the intended
homepage and bot design reference. The earlier gold branch alone did not recover
that hero. The approved `kaos-home-target.png` is now bundled with the React
homepage, with labeled navigation hotspots and separate readable mobile links.
Artwork figures are identified as illustrative. Current membership plans, login
and research tools are preserved; the archive's older backend and plan prices
are not installed.

Extension 1.7.24 uses the reference's Viking brand, black panels and gold controls.
The owner confirmed keeping the compact broker companion without internal
charts. No screenshot performance numbers are inserted into live
account statistics, and no order or authorization logic changes in this pass.

## Compact-companion homepage and broker roadmap

The owner then chose to keep broker-native charts and update the homepage instead
of bringing internal extension charts back. The current homepage therefore uses
the existing Viking banner and an actual extension capture from browser fixtures,
with current control descriptions in place of the old chart-filled bot artwork.
The original target artwork remains in Git but is no longer the landing hero.

The public broker section covers the union of the existing extension selector and
connector roadmap: Pocket Option, Coinbase, Kraken, Interactive Brokers, Alpaca,
OANDA, Tradier, tastytrade, Binance.US, Charles Schwab, and MetaTrader 4/5.
Only Pocket Option is described as supported extension trading. Coinbase is
labeled trading planned; remaining future trading connections are planned.
Research or connection groundwork is not advertised as active bot execution.
No new broker adapters or trading permissions are enabled by this website change.

Browser checks verify all 11 descriptions, a single supported badge, the actual
companion capture, links and mobile layout, plus the recovered member tools.
