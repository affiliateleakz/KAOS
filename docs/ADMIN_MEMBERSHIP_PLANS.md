# Membership plan settings

Admin → Platform Settings → Membership Plans shows Free separately from the paid checkout plans. Its $0 price, one broker chart slot and one device come from the backend Free entitlements.

“Use current KAOS plans” loads the backend defaults into an unsaved draft: Pro $29.95/month or $299.95/year (4 chart slots, 3 devices) and Ultimate $99.95/month or $995.95/year (4 chart slots, 5 devices), with their current tools. This is useful when the database still contains retired monthly/yearly products or outdated entitlements. Review and select “Save Plans” to apply. Loading defaults never writes settings; saved custom prices are preserved until explicitly edited or replaced.

The editor displays dollar equivalents of whole-cent prices and the actual affiliate ledger rates. Free is not sent to paid checkout. Invalid amounts and duplicate/free paid-plan IDs are rejected by the server. Saving settings does not charge members or enable payments, payouts, or AI-controlled execution. Payment provider products must still match the configured prices before checkout can succeed.

Deploy both the web and backend packages for the new settings metadata and editor. No automatic database migration is performed.

Monthly/yearly IDs are distinct (`pro`, `ultimate`, `pro_yearly`, `ultimate_yearly`); annual billing preserves the same feature tier. Ultimate monthly is marked Recommended. The public billing toggle changes displayed prices, registration choice and affiliate payment examples together. Annual payments generate commissions on the actual annual amount once, not twelve assumed monthly payments. Existing subscriptions are not automatically repriced.
