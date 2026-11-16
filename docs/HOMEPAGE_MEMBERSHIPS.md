# Homepage membership and product previews

The homepage loads prices, entitlements, affiliate rates and the commission hold from the public membership catalog. Free registration remains visible if that catalog is unavailable; paid prices and earnings are not invented on an outage.

The calculator rounds commission per qualifying payment before multiplying referrals, matching the accounting ledger. It distinguishes referral levels, membership tier, holds, and current payout availability. Enrollment or a free registration alone earns no commission.

Product previews are actual current KAOS components rendered with labeled local example data. Regenerate after a web build with `CHROME_BIN=/usr/bin/chromium node scripts/browser/capture_product.cjs`, then rebuild to include the images. No broker orders or real accounts are used. Existing Viking branding is retained; the old flat product poster is no longer rendered.

Extension 1.7.30 uses KAOS Strategy as the built-in display name. Legacy saved default metadata is normalized on read without changing engine IDs, parameters, or database records. Candidate model states in the training admin retain their technical meaning; they are not strategy names. Live execution and payment gates are unchanged.

The homepage also compares chart slots, devices, included tools and all three affiliate levels side by side. Each membership card shows direct-referral examples computed from current saved paid prices. A payout walkthrough distinguishes qualifying payment, commission recording, the configured hold and actual payout availability. These additions do not alter the hero artwork or product images and do not activate payouts.
