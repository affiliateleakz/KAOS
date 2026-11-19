# Visitor tracking exclusions and dashboard reset

Staff (admin, super_admin, moderator) traffic is excluded on both frontend and
API capture. The frontend waits for authentication to finish before recording
its first event. Once staff sign in, `kaos_analytics_owner_browser=1` is saved in
that browser's local storage; public-site browsing stays excluded after logout.
The marker is separate from visitor privacy opt-out. A different/unrecognized
browser cannot be identified as the owner until staff sign in there.

Existing historical events are not retroactively attributed to an owner account:
the tracker deliberately does not retain that identity. The reset control lets
the owner start the administrative traffic view from a clean baseline.

Admin → Visitors & Referrals → **Start visitor stats from now** is available only
to super-admin. After confirmation, it saves a shared admin report baseline in
settings. Page views, unique browsers, visits, clicks, sources, country summaries,
recent activity and new-account counts use the later of the chosen period start
and that baseline. Current trial/paid membership totals remain current counts.
The reset timestamp is shown on the dashboard and persists across reloads/users.
Filters are cleared on reset.

This operation does not delete visitor events, account acquisition/referral
attribution, affiliate click totals, commission records or memberships. Affiliate
reports continue their normal scope/period, independent of the admin reset.
A bounded reset history records actor and time. Existing event retention still
applies; no financial or database-wide purge is introduced.

Deploy the matching website/backend packages and restart Passenger. No extension
update is required. Existing owner-browser traffic disappears from the admin
view when the owner chooses the reset after installation; future staff capture
is excluded automatically. Four offline checks cover staff exclusion and reset
permissions/settings-only writes, with no database/provider calls.
