# Stripe membership setup

Use Admin → Payments & payout setup (`/admin/commerce`). Select Stripe membership payments, choose Sandbox/test initially, and save the Payments secret key and Webhook signing secret in the private encrypted vault. Existing values are preserved when fields are left blank. Never paste secret keys into chat or commit them. Stripe Connect is separate, is not required for membership checkout, and does not become active by selecting affiliate payouts.

The application reads saved vault credentials per request. A successful Check API connection is a read-only account authentication check, not a successful checkout, webhook test or payout approval. Stripe billing readiness reports configured versus activated without returning credentials.

In the matching Stripe environment, create a webhook destination:

`https://api.tradingwithkaos.com/api/stripe/webhook`

Subscribe to checkout.session.completed, checkout.session.async_payment_succeeded, invoice.paid, invoice.payment_failed, customer.subscription.deleted, charge.refunded and charge.dispute.created. Store the destination-specific whsec_ signing secret in the same Stripe card. The API only processes a signed webhook after billing is explicitly activated. Current cPanel login-validation deployment blocks both checkout and webhook delivery; delivery retries may show 503 until a separately reviewed billing deployment is installed.

Saving credentials never activates checkout. KAOS_STRIPE_CHECKOUT_ENABLED must explicitly equal true, provider mode must match the key, membership payments must be selected and a signing secret must be present. KAOS_LOGIN_VALIDATION_MODE=true always blocks billing even if saved credentials exist. The current cPanel entry point sets that validation marker. Do not remove it merely to make a connection check pass. A billing-capable deployment and test validation remain separate work; this change does not enable either live or sandbox checkout on the current hosting.

Validate sandbox payments against a separate test database/accounts so test subscriptions cannot grant real member access or enter live affiliate accounting. Confirm the four plan amounts (Pro $29.95 monthly/$299.95 yearly; Ultimate $99.95 monthly/$995.95 yearly), signed delivery, retries, renewals, failed invoices, cancellation and refund reversals. Verify actual Stripe Checkout and customer portal configuration. Only then review a live deployment with the matching live keys and live webhook secret. Do not reuse sandbox Stripe customer/subscription IDs in live mode.

No payments, invoices, subscriptions, refunds, payouts or Stripe account settings were created by the repository tests. No real credential is present in the repository.
